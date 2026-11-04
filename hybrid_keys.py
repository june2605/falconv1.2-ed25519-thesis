"""Version 1 in-memory material, not a vault, identity assertion or wire format.

The Ed25519 private value is a 32-byte seed. Falcon values are the raw encodings
accepted by pqcrypto.sign.falcon_512; that identifier makes no revision claim.
Private bytes are intentionally accessible to local Python crypto operations.
Frozen dataclasses and redacted repr do not provide memory isolation/zeroization.
"""

from dataclasses import dataclass, field
import hashlib
import secrets

from nacl.bindings import crypto_sign_PUBLICKEYBYTES, crypto_sign_SEEDBYTES, crypto_sign_BYTES
from nacl.signing import SigningKey, VerifyKey
from pqcrypto.sign import falcon_512


KEY_MATERIAL_VERSION = 1
ED25519_ALGORITHM = "ed25519"
FALCON_ALGORITHM = "falcon_512"
_ID_DOMAIN = b"THESIS-HYBRID-KEY-ID-v1\x00"
_SELF_TEST_DOMAIN = b"THESIS-HYBRID-KEY-SELF-TEST-v1\x00"


class KeyMaterialError(ValueError):
    """Stable validation code and message without private values/native errors."""

    def __init__(self, code, message):
        self.code = code
        super().__init__(f"{code}: {message}")


def _require_bytes(value, size, name):
    if type(value) is not bytes:
        raise KeyMaterialError("key.type", f"{name} must be immutable bytes")
    if len(value) != size:
        raise KeyMaterialError("key.size", f"{name} must contain {size} bytes")


def _validate_public(ed, falcon, version, ed_algorithm, falcon_algorithm):
    if type(version) is not int or version != KEY_MATERIAL_VERSION:
        raise KeyMaterialError("key.version", "Unsupported key-material version")
    if (type(ed_algorithm) is not str or ed_algorithm != ED25519_ALGORITHM
            or type(falcon_algorithm) is not str or falcon_algorithm != FALCON_ALGORITHM):
        raise KeyMaterialError("key.algorithm", "Unsupported algorithm identifier")
    _require_bytes(ed, crypto_sign_PUBLICKEYBYTES, "Ed25519 public key")
    _require_bytes(falcon, falcon_512.PUBLIC_KEY_SIZE, "Falcon public key")


def hybrid_key_id(ed25519_public_key, falcon_public_key, *, version=KEY_MATERIAL_VERSION,
                  ed25519_algorithm=ED25519_ALGORITHM, falcon_algorithm=FALCON_ALGORITHM):
    """Hash domain || LP(Ed algorithm) || LP(Ed public) || LP(Falcon algorithm)
    || LP(Falcon public), where LP uses a four-byte unsigned big-endian length.

    This identifies a public tuple; it does not prove possession or identity.
    No private key, container capacity or dependency version enters the ID.
    """
    _validate_public(ed25519_public_key, falcon_public_key, version, ed25519_algorithm, falcon_algorithm)
    fields = (ed25519_algorithm.encode("ascii"), ed25519_public_key,
              falcon_algorithm.encode("ascii"), falcon_public_key)
    encoded = _ID_DOMAIN + b"".join(len(value).to_bytes(4, "big") + value for value in fields)
    return "hybrid-v1:" + hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class HybridPublicKey:
    ed25519_public_key: bytes
    falcon_public_key: bytes
    version: int = field(default=KEY_MATERIAL_VERSION, kw_only=True)
    ed25519_algorithm: str = field(default=ED25519_ALGORITHM, kw_only=True)
    falcon_algorithm: str = field(default=FALCON_ALGORITHM, kw_only=True)

    def __post_init__(self):
        _validate_public(self.ed25519_public_key, self.falcon_public_key, self.version,
                         self.ed25519_algorithm, self.falcon_algorithm)

    @property
    def key_id(self):
        return hybrid_key_id(self.ed25519_public_key, self.falcon_public_key, version=self.version,
                             ed25519_algorithm=self.ed25519_algorithm, falcon_algorithm=self.falcon_algorithm)


@dataclass(frozen=True, slots=True, repr=False)
class HybridKeyPair:
    public_keys: HybridPublicKey
    ed25519_private_seed: bytes = field(repr=False)
    falcon_private_key: bytes = field(repr=False)

    def __post_init__(self):
        validate_key_pair(self)

    @property
    def key_id(self):
        return self.public_keys.key_id

    def __repr__(self):
        return f"HybridKeyPair(version={self.public_keys.version}, key_id={self.key_id!r})"


def validate_key_pair(pair):
    """Revalidate structure, correspondence and fresh domain-separated self-tests.

    No validation-success flag is trusted. Falcon has no exposed public-key
    derivation API, so its correspondence is checked through native sign/verify.
    This is not a proof of identity, entropy quality or complete native safety.
    """
    if type(pair) is not HybridKeyPair or type(pair.public_keys) is not HybridPublicKey:
        raise KeyMaterialError("key.type", "Expected a versioned hybrid key pair")
    public = pair.public_keys
    _validate_public(public.ed25519_public_key, public.falcon_public_key, public.version,
                     public.ed25519_algorithm, public.falcon_algorithm)
    _require_bytes(pair.ed25519_private_seed, crypto_sign_SEEDBYTES, "Ed25519 private seed")
    _require_bytes(pair.falcon_private_key, falcon_512.SECRET_KEY_SIZE, "Falcon private key")
    try:
        signing_key = SigningKey(pair.ed25519_private_seed)
        derived_public = bytes(signing_key.verify_key)
    except Exception:
        raise KeyMaterialError("key.self_test", "Ed25519 key initialization failed") from None
    if derived_public != public.ed25519_public_key:
        raise KeyMaterialError("key.correspondence", "Ed25519 seed and public key do not correspond")
    try:
        context = public.key_id.encode("ascii") + b"\x00" + secrets.token_bytes(32)
        ed_message = _SELF_TEST_DOMAIN + b"ed25519\x00" + context
        ed_signature = signing_key.sign(ed_message).signature
        if type(ed_signature) is not bytes or len(ed_signature) != crypto_sign_BYTES:
            raise ValueError("Invalid Ed25519 self-test signature")
        if VerifyKey(public.ed25519_public_key).verify(ed_message, ed_signature) != ed_message:
            raise ValueError("Ed25519 self-test failed")
        falcon_message = _SELF_TEST_DOMAIN + b"falcon_512\x00" + context + ed_signature
        falcon_signature = falcon_512.sign(pair.falcon_private_key, falcon_message)
        if type(falcon_signature) is not bytes or not 0 < len(falcon_signature) <= falcon_512.SIGNATURE_SIZE:
            raise ValueError("Invalid Falcon self-test signature")
        if falcon_512.verify(public.falcon_public_key, falcon_message, falcon_signature) is not True:
            raise ValueError("Falcon self-test failed")
    except Exception:
        raise KeyMaterialError("key.self_test", "Hybrid key correspondence/self-test failed") from None
