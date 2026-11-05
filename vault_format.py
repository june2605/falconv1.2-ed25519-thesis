"""Strict positional hybrid-vault v1 format, with no filesystem operations.

Parsed public metadata is UNTRUSTED until vault_crypto authenticates the original
header. Its public-key ID identifies a tuple, not a trusted signer identity.
Wire sizes are frozen independently of future native-library encoding changes.
"""

from dataclasses import dataclass, field
import hmac
import struct
from uuid import RFC_4122, UUID

from hybrid_keys import HybridPublicKey, KeyMaterialError


FORMAT_VERSION = 1
HEADER_LENGTH = 1069
PAYLOAD_LENGTH = 1331
ENCRYPTED_PAYLOAD_LENGTH = 1347
VAULT_LENGTH = 2416
MAX_INPUT_LENGTH = 4096
_HEADER = struct.Struct(">8sHHI16s9H3I9H16s12s32s897s32s")
_PAYLOAD = struct.Struct(">8s5H32s1281s")


class VaultError(ValueError):
    """Stable public category/message; never accepts raw native exception text."""

    code = "vault.error"
    message = "Vault operation failed"

    def __init__(self):
        super().__init__(f"{self.code}: {self.message}")


class VaultFormatError(VaultError):
    code = "vault.format"
    message = "Invalid vault format"


class VaultProfileError(VaultError):
    code = "vault.profile"
    message = "Unsupported vault cryptographic profile"


class VaultUnlockError(VaultError):
    code = "vault.unlock"
    message = "Incorrect password or damaged vault"


class VaultKeyMaterialError(VaultError):
    code = "vault.key_material"
    message = "Invalid hybrid key material"


class VaultBackendError(VaultError):
    code = "vault.backend"
    message = "Required cryptographic backend unavailable or failed"


class VaultPasswordError(VaultError):
    code = "vault.password"
    message = "Password does not satisfy the encoding or length policy"


class VaultBusyError(VaultError):
    code = "vault.busy"
    message = "Another vault derivation is in progress"


@dataclass(frozen=True, slots=True)
class VaultMetadata:
    """Public, non-secret metadata; authenticity is established only by unseal."""

    vault_uuid: UUID
    public_keys: HybridPublicKey
    salt: bytes
    nonce: bytes

    def __post_init__(self):
        _validate_metadata(self)

    @property
    def format_version(self):
        return FORMAT_VERSION

    @property
    def key_id(self):
        return self.public_keys.key_id


@dataclass(frozen=True, slots=True)
class ParsedVault:
    """Structurally validated, still UNAUTHENTICATED; contains no private bytes."""

    metadata: VaultMetadata
    header_bytes: bytes = field(repr=False)
    encrypted_payload: bytes = field(repr=False)


def _validate_metadata(metadata):
    if (type(metadata.vault_uuid) is not UUID or metadata.vault_uuid.version != 4
            or metadata.vault_uuid.variant != RFC_4122):
        raise VaultFormatError()
    if (type(metadata.salt) is not bytes or len(metadata.salt) != 16
            or type(metadata.nonce) is not bytes or len(metadata.nonce) != 12
            or type(metadata.public_keys) is not HybridPublicKey):
        raise VaultFormatError()
    public = metadata.public_keys
    try:
        HybridPublicKey(public.ed25519_public_key, public.falcon_public_key,
                        version=public.version, ed25519_algorithm=public.ed25519_algorithm,
                        falcon_algorithm=public.falcon_algorithm)
        if len(public.ed25519_public_key) != 32 or len(public.falcon_public_key) != 897:
            raise VaultFormatError()
    except KeyMaterialError:
        raise VaultFormatError() from None


def encode_header(metadata: VaultMetadata) -> bytes:
    """Canonical creation serializer; never used to reconstruct unlock AAD."""
    if type(metadata) is not VaultMetadata:
        raise VaultFormatError()
    _validate_metadata(metadata)
    public = metadata.public_keys
    digest = bytes.fromhex(metadata.key_id.removeprefix("hybrid-v1:"))
    return _HEADER.pack(
        b"HYBKVLT\x00", FORMAT_VERSION, HEADER_LENGTH, ENCRYPTED_PAYLOAD_LENGTH,
        metadata.vault_uuid.bytes,
        1, 1, 2, 1, 1, 1, 1, 1, 19,
        65536, 3, 4,
        32, 1, 12, 16, 16, 1, 32, 897, 32,
        metadata.salt, metadata.nonce,
        public.ed25519_public_key, public.falcon_public_key, digest)


def parse_vault(vault_bytes: bytes) -> ParsedVault:
    """Reject all invalid public structure/profiles before any password KDF.

    The defensive ceiling is not a file-reading API. The caller already owns
    these immutable bytes; only exactly 2416 bytes are accepted for version 1.
    """
    if type(vault_bytes) is not bytes:
        raise VaultFormatError()
    if len(vault_bytes) > MAX_INPUT_LENGTH or len(vault_bytes) != VAULT_LENGTH:
        raise VaultFormatError()
    header_bytes = vault_bytes[:HEADER_LENGTH]
    values = _HEADER.unpack(header_bytes)
    format_fields = {
        0: b"HYBKVLT\x00", 1: 1, 2: HEADER_LENGTH, 3: ENCRYPTED_PAYLOAD_LENGTH,
        5: 1, 8: 1, 9: 1, 10: 1, 19: 12, 20: 16, 21: 16,
        23: 32, 24: 897, 25: 32,
    }
    if any(values[index] != expected for index, expected in format_fields.items()):
        raise VaultFormatError()
    profile_fields = {
        6: 1, 7: 2, 11: 1, 12: 1, 13: 19, 14: 65536, 15: 3, 16: 4,
        17: 32, 18: 1, 22: 1,
    }
    if any(values[index] != expected for index, expected in profile_fields.items()):
        raise VaultProfileError()
    try:
        public = HybridPublicKey(values[28], values[29])
        metadata = VaultMetadata(UUID(bytes=values[4]), public, values[26], values[27])
    except KeyMaterialError:
        raise VaultFormatError() from None
    expected_digest = bytes.fromhex(metadata.key_id.removeprefix("hybrid-v1:"))
    if not hmac.compare_digest(values[30], expected_digest):
        raise VaultFormatError()
    return ParsedVault(metadata, header_bytes, vault_bytes[HEADER_LENGTH:])


def _encode_payload(pair) -> bytes:
    """Internal, RAM-only plaintext; caller must validate correspondence first."""
    seed, secret = pair.ed25519_private_seed, pair.falcon_private_key
    if (type(seed) is not bytes or len(seed) != 32
            or type(secret) is not bytes or len(secret) != 1281):
        raise VaultKeyMaterialError()
    return _PAYLOAD.pack(b"HYBKEYS\x00", 1, 1, 1, 32, 1281, seed, secret)


def _decode_payload(plaintext: bytes) -> tuple[bytes, bytes]:
    """Internal; called only after successful AES-GCM authentication."""
    if type(plaintext) is not bytes or len(plaintext) != PAYLOAD_LENGTH:
        raise VaultKeyMaterialError()
    values = _PAYLOAD.unpack(plaintext)
    if values[:6] != (b"HYBKEYS\x00", 1, 1, 1, 32, 1281):
        raise VaultKeyMaterialError()
    return values[6], values[7]
