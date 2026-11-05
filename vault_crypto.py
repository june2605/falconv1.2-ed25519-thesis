"""In-memory vault v1 codec: Argon2id v19 + AES-256-GCM, no persistence.

Private bytes/passwords necessarily exist in Python/native memory; this module
does not promise zeroization, protection from a compromised process or recovery.
No fallback algorithm, caller-selected cost, salt or nonce is supported.
"""

from dataclasses import dataclass, field
import importlib
import secrets
from threading import BoundedSemaphore
from uuid import uuid4

from hybrid_keys import HybridKeyPair, HybridPublicKey, validate_key_pair
from vault_format import (
    ENCRYPTED_PAYLOAD_LENGTH, VaultBackendError, VaultBusyError,
    VaultKeyMaterialError, VaultMetadata, VaultPasswordError, VaultUnlockError,
    _decode_payload, _encode_payload, encode_header, parse_vault,
)


CRYPTOGRAPHY_VERSION = "50.0.2"
_KDF_SLOT = BoundedSemaphore(1)  # Fail fast, at most one 64 MiB KDF per process.


@dataclass(frozen=True, slots=True)
class _Backend:
    argon2id: type
    aesgcm: type
    invalid_tag: type


@dataclass(frozen=True, slots=True)
class UnsealedVault:
    """Authenticated metadata and a natively validated, immutable key pair."""

    key_pair: HybridKeyPair = field(repr=False)
    metadata: VaultMetadata


def _load_backend():
    """Fail closed on the pinned package/API. Native support is checked on use.

    Normal dependency imports may load code; there is no per-operation metadata
    file read and no filesystem storage of vault/password/private-key data.
    """
    try:
        package = importlib.import_module("cryptography")
        if package.__version__ != CRYPTOGRAPHY_VERSION:
            raise VaultBackendError()
        argon = importlib.import_module("cryptography.hazmat.primitives.kdf.argon2")
        aead = importlib.import_module("cryptography.hazmat.primitives.ciphers.aead")
        exceptions = importlib.import_module("cryptography.exceptions")
        return _Backend(argon.Argon2id, aead.AESGCM, exceptions.InvalidTag)
    except Exception:
        raise VaultBackendError() from None


def _encode_password(password, *, creating):
    if type(password) is not str or not password or len(password) > 1024:
        raise VaultPasswordError()
    try:
        encoded = password.encode("utf-8", errors="strict")
    except UnicodeError:
        raise VaultPasswordError() from None
    if len(encoded) > 1024 or (creating and len(password) < 15):
        raise VaultPasswordError()
    return encoded


def _derive_key(backend, encoded_password, salt):
    try:
        # cryptography's Argon2id API implements version 19 (RFC 9106 v1.3).
        kdf = backend.argon2id(salt=salt, length=32, iterations=3, lanes=4,
                              memory_cost=65536, ad=None, secret=None)
        key = kdf.derive(encoded_password)
        if type(key) is not bytes or len(key) != 32:
            raise VaultBackendError()
        return key
    except Exception:
        raise VaultBackendError() from None


def seal_key_pair(pair: HybridKeyPair, password: str) -> bytes:
    """Validate, encrypt and return one new 2416-byte vault, entirely in memory.

    A fresh independent OS-random salt, nonce and UUID are generated per call.
    Nonce/key collision avoidance relies on the OS RNG; no persistent registry
    or absolute uniqueness guarantee under RNG compromise is claimed.
    """
    encoded_password = _encode_password(password, creating=True)
    try:
        validate_key_pair(pair)
        plaintext = _encode_payload(pair)
    except Exception:
        raise VaultKeyMaterialError() from None
    backend = _load_backend()
    metadata = VaultMetadata(uuid4(), pair.public_keys, secrets.token_bytes(16), secrets.token_bytes(12))
    header = encode_header(metadata)
    if not _KDF_SLOT.acquire(blocking=False):
        raise VaultBusyError()
    try:
        key = _derive_key(backend, encoded_password, metadata.salt)
        try:
            encrypted = backend.aesgcm(key).encrypt(metadata.nonce, plaintext, header)
            if type(encrypted) is not bytes or len(encrypted) != ENCRYPTED_PAYLOAD_LENGTH:
                raise VaultBackendError()
        except Exception:
            raise VaultBackendError() from None
        return header + encrypted
    finally:
        _KDF_SLOT.release()


def unseal_key_pair(vault_bytes: bytes, password: str) -> UnsealedVault:
    """Authenticate original bytes, then reconstruct and self-test both keys.

    Public structure is rejected before backend loading/KDF. The creation-only
    password minimum is intentionally not applied when unlocking existing data.
    No private value is returned before authentication and correspondence checks.
    """
    parsed = parse_vault(vault_bytes)
    encoded_password = _encode_password(password, creating=False)
    backend = _load_backend()
    if not _KDF_SLOT.acquire(blocking=False):
        raise VaultBusyError()
    try:
        key = _derive_key(backend, encoded_password, parsed.metadata.salt)
        try:
            plaintext = backend.aesgcm(key).decrypt(
                parsed.metadata.nonce, parsed.encrypted_payload, parsed.header_bytes)
        except backend.invalid_tag:
            raise VaultUnlockError() from None
        except Exception:
            raise VaultBackendError() from None
    finally:
        _KDF_SLOT.release()
    try:
        seed, secret = _decode_payload(plaintext)
        public = parsed.metadata.public_keys
        # Constructors enforce identifiers, sizes, Ed derivation and both native
        # correspondence self-tests, including Falcon sign/verify. No keygen.
        public = HybridPublicKey(public.ed25519_public_key, public.falcon_public_key)
        pair = HybridKeyPair(public, seed, secret)
        if pair.key_id != parsed.metadata.key_id:
            raise VaultKeyMaterialError()
    except Exception:
        raise VaultKeyMaterialError() from None
    return UnsealedVault(pair, parsed.metadata)
