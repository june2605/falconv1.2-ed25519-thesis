"""Real profile integration plus isolated parser/AEAD faults (no KDF downgrades)."""

import builtins
from dataclasses import FrozenInstanceError, replace
import importlib
import inspect
import io
import os
from pathlib import Path
import tempfile
import threading

import pytest
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

import hybrid_keys
import keygen
from vault_cases import (INTEGER_FIELDS, NONCE, PASSWORD, SALT, TEST_AEAD_KEY,
                         change, flip, header, payload, public_digest, wire)


@pytest.fixture
def codec():
    return importlib.import_module("vault_crypto")


@pytest.fixture
def fmt():
    return importlib.import_module("vault_format")


@pytest.fixture(scope="module")
def pair():
    return keygen.generate_hybrid_key_pair()


@pytest.fixture
def cheap_kdf(codec, monkeypatch):
    """Only boundary tests use this; AES-GCM and key self-tests remain real."""
    calls = []

    def derive(backend, encoded_password, salt):
        calls.append((encoded_password, salt))
        return TEST_AEAD_KEY

    monkeypatch.setattr(codec, "_derive_key", derive)
    return calls


def authenticated_wire(pair, plain=None, aad=None):
    aad = header(pair.public_keys) if aad is None else aad
    plain = payload(pair) if plain is None else plain
    return aad + AESGCM(TEST_AEAD_KEY).encrypt(aad[96:108], plain, aad)


def test_real_round_trip_recovers_identical_material(codec, fmt, pair):
    data = codec.seal_key_pair(pair, PASSWORD)
    result = codec.unseal_key_pair(data, PASSWORD)
    assert len(data) == 2416
    assert result.key_pair == pair
    assert result.key_pair is not pair
    assert result.key_pair.key_id == pair.key_id == result.metadata.key_id
    assert fmt.encode_header(result.metadata) == data[:1069]
    assert data[1069:] != payload(pair)
    with pytest.raises(FrozenInstanceError):
        result.key_pair = pair
    assert pair.ed25519_private_seed.hex() not in repr(result)
    assert pair.falcon_private_key.hex() not in repr(result)


def test_real_independent_encryptions_fresh_randomness(codec, pair):
    first = codec.seal_key_pair(pair, PASSWORD)
    second = codec.seal_key_pair(pair, PASSWORD)
    for start, end in [(16, 32), (80, 96), (96, 108), (1069, 2416)]:
        assert first[start:end] != second[start:end]
    assert codec.unseal_key_pair(first, PASSWORD).key_pair == pair
    assert codec.unseal_key_pair(second, PASSWORD).key_pair == pair


def test_real_unicode_and_exact_password_semantics(codec, fmt, pair):
    password = "  Cafe\u0301 密碼🔑 test phrase  "
    data = codec.seal_key_pair(pair, password)
    assert codec.unseal_key_pair(data, password).key_pair == pair
    for wrong in (password.strip(), password.casefold(), password.replace("e\u0301", "é")):
        with pytest.raises(fmt.VaultUnlockError, match="vault.unlock"):
            codec.unseal_key_pair(data, wrong)


def test_real_wrong_password_generic_unlock_error(codec, fmt, pair):
    data = codec.seal_key_pair(pair, PASSWORD)
    with pytest.raises(fmt.VaultUnlockError) as caught:
        codec.unseal_key_pair(data, "wrong disposable password")
    assert str(caught.value) == "vault.unlock: Incorrect password or damaged vault"
    assert caught.value.__suppress_context__


@pytest.mark.parametrize("password", [None, b"x" * 15, 123, "", "x" * 1025,
                                      "🔑" * 257, "x" * 15 + "\ud800", "\udfff"])
@pytest.mark.parametrize("operation", ["seal", "unseal"])
def test_invalid_password_before_kdf(codec, fmt, pair, monkeypatch, password, operation):
    def forbidden(*args):
        pytest.fail("Invalid password reached KDF")
    monkeypatch.setattr(codec, "_derive_key", forbidden)
    with pytest.raises(fmt.VaultPasswordError):
        if operation == "seal":
            codec.seal_key_pair(pair, password)
        else:
            codec.unseal_key_pair(wire(pair.public_keys), password)


@pytest.mark.parametrize("password", ["x", "x" * 14, "🔑" * 14])
def test_creation_minimum_counts_code_points(codec, fmt, pair, password):
    with pytest.raises(fmt.VaultPasswordError):
        codec.seal_key_pair(pair, password)


@pytest.mark.parametrize("password", ["🔑" * 15, "x" * 1024, "🔑" * 256])
def test_password_valid_boundaries(codec, pair, cheap_kdf, password):
    assert codec.unseal_key_pair(codec.seal_key_pair(pair, password), password).key_pair == pair
    assert cheap_kdf[0][0] == password.encode("utf-8")


def test_unlock_does_not_enforce_creation_minimum(codec, pair, cheap_kdf):
    assert codec.unseal_key_pair(authenticated_wire(pair), "x").key_pair == pair
    assert cheap_kdf == [(b"x", SALT)]


def test_real_unlock_of_short_password_vault(codec, pair):
    aad = header(pair.public_keys)
    key = Argon2id(salt=SALT, length=32, iterations=3, lanes=4,
                  memory_cost=65536).derive(b"x")
    data = aad + AESGCM(key).encrypt(NONCE, payload(pair), aad)
    assert codec.unseal_key_pair(data, "x").key_pair == pair


def test_exact_private_payload_encoding(codec, pair):
    encoded = codec._encode_payload(pair)
    assert len(encoded) == 1331
    assert encoded[:18] == bytes.fromhex("4859424b4559530000010001000100200501")
    assert encoded[18:50] == pair.ed25519_private_seed
    assert encoded[50:1331] == pair.falcon_private_key
    assert encoded == payload(pair)
    assert codec._decode_payload(encoded) == (pair.ed25519_private_seed, pair.falcon_private_key)


@pytest.mark.parametrize("bad", [None, bytearray(1331), b"", b"x" * 1330, b"x" * 1332])
def test_payload_requires_exact_bytes_length(codec, fmt, bad):
    with pytest.raises(fmt.VaultKeyMaterialError):
        codec._decode_payload(bad)


@pytest.mark.parametrize("offset,width,value,profile", INTEGER_FIELDS)
def test_bad_header_before_backend_or_kdf(codec, fmt, monkeypatch, offset, width, value, profile):
    def forbidden():
        pytest.fail("Invalid public header reached cryptographic backend")
    monkeypatch.setattr(codec, "_load_backend", forbidden)
    with pytest.raises(fmt.VaultError):
        codec.unseal_key_pair(change(wire(), offset, (value + 1).to_bytes(width, "big")), PASSWORD)


@pytest.mark.parametrize("bad", [None, bytearray(wire()), b"", wire()[:-1], wire() + b"x",
                                  b"x" * 4097, flip(wire(), 1037)])
def test_bad_input_before_backend(codec, fmt, monkeypatch, bad):
    monkeypatch.setattr(codec, "_load_backend", lambda: pytest.fail("Malformed input reached backend"))
    with pytest.raises(fmt.VaultFormatError):
        codec.unseal_key_pair(bad, PASSWORD)


@pytest.mark.parametrize("offset", [16, 31, 80, 95, 96, 107, 1069, 1734, 2399, 2400, 2407, 2415])
def test_authenticated_regions_reject_mutation(codec, fmt, pair, cheap_kdf, monkeypatch, offset):
    data = flip(authenticated_wire(pair), offset)
    monkeypatch.setattr(codec, "_decode_payload", lambda _: pytest.fail("Unauthenticated payload parsed"))
    with pytest.raises(fmt.VaultUnlockError):
        codec.unseal_key_pair(data, PASSWORD)


def test_recomputed_public_id_cannot_bypass_aad(codec, fmt, pair, cheap_kdf):
    data = authenticated_wire(pair)
    aad = flip(data[:1069], 108)
    aad = change(aad, 1037, public_digest(aad[108:140], aad[140:1037]))
    with pytest.raises(fmt.VaultUnlockError):
        codec.unseal_key_pair(aad + data[1069:], PASSWORD)


def test_original_aad_not_reconstructed(codec, fmt, pair, cheap_kdf, monkeypatch):
    data = authenticated_wire(pair)
    monkeypatch.setattr(fmt, "encode_header", lambda _: pytest.fail("AAD reconstructed"))
    monkeypatch.setattr(codec, "encode_header", lambda _: pytest.fail("AAD reconstructed"))
    backend = codec._load_backend()
    recorded = []

    class InspectAES:
        def __init__(self, key):
            self.aes = AESGCM(key)

        def decrypt(self, nonce, cipher, aad):
            recorded.append(aad)
            return self.aes.decrypt(nonce, cipher, aad)

    monkeypatch.setattr(codec, "_load_backend", lambda: replace(backend, aesgcm=InspectAES))
    assert codec.unseal_key_pair(data, PASSWORD).key_pair == pair
    assert recorded == [data[:1069]]


@pytest.mark.parametrize("offset", [0, 7, 8, 10, 12, 14, 16])
def test_authenticated_bad_payload_metadata(codec, fmt, pair, cheap_kdf, offset):
    with pytest.raises(fmt.VaultKeyMaterialError):
        codec.unseal_key_pair(authenticated_wire(pair, flip(payload(pair), offset)), PASSWORD)


@pytest.mark.parametrize("layer", ["ed25519", "falcon"])
def test_authenticated_mixed_private_keys_reject(codec, fmt, pair, cheap_kdf, layer):
    other = keygen.generate_hybrid_key_pair()
    plain = payload(pair)
    if layer == "ed25519":
        plain = change(plain, 18, other.ed25519_private_seed)
    else:
        plain = change(plain, 50, other.falcon_private_key)
    with pytest.raises(fmt.VaultKeyMaterialError):
        codec.unseal_key_pair(authenticated_wire(pair, plain), PASSWORD)


@pytest.mark.parametrize("layer", ["ed_sign", "ed_verify", "falcon_sign", "falcon_verify"])
def test_unsealed_keys_must_pass_both_native_self_tests(codec, fmt, pair, cheap_kdf, monkeypatch, layer):
    data = authenticated_wire(pair)

    def fail(*args, **kwargs):
        raise RuntimeError("NATIVE-SENSITIVE-MARKER")

    if layer == "ed_sign":
        native = hybrid_keys.SigningKey

        class FailingSigner:
            def __init__(self, seed):
                self.verify_key = native(seed).verify_key

            sign = fail

        monkeypatch.setattr(hybrid_keys, "SigningKey", FailingSigner)
    elif layer == "ed_verify":
        monkeypatch.setattr(hybrid_keys, "VerifyKey", lambda _: type("Verifier", (), {"verify": fail})())
    elif layer == "falcon_sign":
        monkeypatch.setattr(hybrid_keys.falcon_512, "sign", fail)
    else:
        monkeypatch.setattr(hybrid_keys.falcon_512, "verify", lambda *args: False)
    with pytest.raises(fmt.VaultKeyMaterialError) as caught:
        codec.unseal_key_pair(data, PASSWORD)
    assert "NATIVE-SENSITIVE-MARKER" not in str(caught.value)


def test_modified_model_revalidated_before_sealing(codec, fmt, pair, monkeypatch):
    other = keygen.generate_hybrid_key_pair()
    object.__setattr__(other, "ed25519_private_seed", pair.ed25519_private_seed)
    monkeypatch.setattr(codec, "_load_backend", lambda: pytest.fail("Mixed model reached encryption"))
    with pytest.raises(fmt.VaultKeyMaterialError):
        codec.seal_key_pair(other, PASSWORD)


def test_unlock_never_generates_replacement_keys(codec, fmt, pair, cheap_kdf, monkeypatch):
    monkeypatch.setattr(keygen, "generate_hybrid_key_pair", lambda: pytest.fail("Replacement keys generated"))
    with pytest.raises(fmt.VaultUnlockError):
        codec.unseal_key_pair(flip(authenticated_wire(pair), 2415), PASSWORD)


@pytest.mark.parametrize("operation", ["seal", "unseal"])
def test_backend_missing_sanitized(codec, fmt, pair, monkeypatch, operation):
    original = importlib.import_module

    def unavailable(name):
        if name.startswith("cryptography"):
            raise ImportError("INTERNAL-SENSITIVE-MARKER")
        return original(name)

    monkeypatch.setattr(codec.importlib, "import_module", unavailable)
    with pytest.raises(fmt.VaultBackendError) as caught:
        if operation == "seal":
            codec.seal_key_pair(pair, PASSWORD)
        else:
            codec.unseal_key_pair(wire(pair.public_keys), PASSWORD)
    assert "INTERNAL-SENSITIVE-MARKER" not in str(caught.value)
    assert caught.value.__suppress_context__


def test_wrong_backend_version_rejects(codec, fmt, pair, monkeypatch):
    import cryptography
    monkeypatch.setattr(cryptography, "__version__", "50.0.1")
    with pytest.raises(fmt.VaultBackendError):
        codec.seal_key_pair(pair, PASSWORD)


@pytest.mark.parametrize("stage", ["argon_init", "argon_derive", "aes_init", "encrypt", "decrypt"])
@pytest.mark.parametrize("error", [UnsupportedAlgorithm, MemoryError, RuntimeError])
def test_runtime_backend_failures_no_fallback(codec, fmt, pair, monkeypatch, stage, error):
    backend = codec._load_backend()
    calls = []

    def fail():
        calls.append(stage)
        raise error("INTERNAL-SENSITIVE-MARKER")

    class Argon:
        def __init__(self, **kwargs):
            if stage == "argon_init":
                fail()

        def derive(self, password):
            if stage == "argon_derive":
                fail()
            return TEST_AEAD_KEY

    class AES:
        def __init__(self, key):
            if stage == "aes_init":
                fail()

        def encrypt(self, *args):
            fail()

        def decrypt(self, *args):
            fail()

    monkeypatch.setattr(codec, "_load_backend", lambda: replace(backend, argon2id=Argon, aesgcm=AES))
    with pytest.raises(fmt.VaultBackendError) as caught:
        if stage == "decrypt":
            codec.unseal_key_pair(authenticated_wire(pair), PASSWORD)
        else:
            codec.seal_key_pair(pair, PASSWORD)
    assert calls == [stage]
    assert "INTERNAL-SENSITIVE-MARKER" not in str(caught.value)
    assert caught.value.__suppress_context__


def test_exact_argon_api_profile(codec, pair, monkeypatch):
    backend = codec._load_backend()
    seen = []

    class Argon:
        def __init__(self, **kwargs):
            seen.append(kwargs)

        def derive(self, password):
            assert password == PASSWORD.encode("utf-8")
            return TEST_AEAD_KEY

    monkeypatch.setattr(codec, "_load_backend", lambda: replace(backend, argon2id=Argon))
    data = codec.seal_key_pair(pair, PASSWORD)
    assert seen == [dict(salt=data[80:96], length=32, iterations=3, lanes=4,
                         memory_cost=65536, ad=None, secret=None)]


@pytest.mark.parametrize("invalid_key", [None, bytearray(32), b"", b"x" * 31, b"x" * 33])
def test_backend_must_return_exact_aes256_key(codec, fmt, pair, monkeypatch, invalid_key):
    backend = codec._load_backend()

    class Argon:
        def __init__(self, **kwargs):
            pass

        def derive(self, password):
            return invalid_key

    monkeypatch.setattr(codec, "_load_backend", lambda: replace(backend, argon2id=Argon))
    with pytest.raises(fmt.VaultBackendError):
        codec.seal_key_pair(pair, PASSWORD)


@pytest.mark.parametrize("encrypted", [None, bytearray(1347), b"", b"x" * 1346, b"x" * 1348])
def test_backend_must_return_exact_ciphertext_and_tag(codec, fmt, pair, cheap_kdf, monkeypatch, encrypted):
    backend = codec._load_backend()

    class AES:
        def __init__(self, key):
            pass

        def encrypt(self, *args):
            return encrypted

    monkeypatch.setattr(codec, "_load_backend", lambda: replace(backend, aesgcm=AES))
    with pytest.raises(fmt.VaultBackendError):
        codec.seal_key_pair(pair, PASSWORD)


def test_no_filesystem_access_real_profile(codec, pair, monkeypatch):
    codec._load_backend()  # Dependency import is startup work, not codec persistence.

    def forbidden(*args, **kwargs):
        pytest.fail("Vault codec attempted filesystem I/O")

    for target, name in [(builtins, "open"), (io, "open"), (os, "open"), (os, "mkdir"),
                         (Path, "open"), (Path, "read_bytes"), (Path, "write_bytes"),
                         (tempfile, "mkstemp"), (tempfile, "mkdtemp")]:
        monkeypatch.setattr(target, name, forbidden)
    assert codec.unseal_key_pair(codec.seal_key_pair(pair, PASSWORD), PASSWORD).key_pair == pair


def test_no_secrets_in_errors_or_logs(codec, fmt, pair, cheap_kdf, monkeypatch, capsys, caplog):
    def fail(_):
        raise RuntimeError(PASSWORD + pair.ed25519_private_seed.hex() + TEST_AEAD_KEY.hex())

    monkeypatch.setattr(codec, "_decode_payload", fail)
    with pytest.raises(fmt.VaultKeyMaterialError) as caught:
        codec.unseal_key_pair(authenticated_wire(pair), PASSWORD)
    output = str(caught.value) + repr(caught.value) + repr(capsys.readouterr()) + caplog.text
    for secret in [PASSWORD, pair.ed25519_private_seed.hex(), pair.falcon_private_key.hex(), TEST_AEAD_KEY.hex()]:
        assert secret not in output
    assert caught.value.__suppress_context__


def test_invalid_pair_rejected_before_encryption(codec, fmt, monkeypatch):
    monkeypatch.setattr(codec, "_load_backend", lambda: pytest.fail("Invalid pair reached encryption"))
    with pytest.raises(fmt.VaultKeyMaterialError):
        codec.seal_key_pair(object(), PASSWORD)


def test_no_public_fixed_randomness_parameters(codec):
    assert list(inspect.signature(codec.seal_key_pair).parameters) == ["pair", "password"]
    assert list(inspect.signature(codec.unseal_key_pair).parameters) == ["vault_bytes", "password"]


def test_kdf_slot_fail_fast_and_released_after_failure(codec, fmt, pair, monkeypatch):
    started, release = threading.Event(), threading.Event()
    result = []

    def blocked(*args):
        started.set()
        assert release.wait(5)
        raise fmt.VaultBackendError()

    monkeypatch.setattr(codec, "_derive_key", blocked)

    def worker():
        try:
            codec.unseal_key_pair(authenticated_wire(pair), PASSWORD)
        except fmt.VaultBackendError:
            result.append("rejected")

    thread = threading.Thread(target=worker)
    thread.start()
    try:
        assert started.wait(5)
        with pytest.raises(fmt.VaultBusyError):
            codec.unseal_key_pair(authenticated_wire(pair), PASSWORD)
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive()
    assert result == ["rejected"]
    assert codec._KDF_SLOT.acquire(blocking=False)
    codec._KDF_SLOT.release()


def test_official_rfc9106_argon2id_vector():
    """RFC 9106 section 5.3; low-cost vector is NOT an accepted vault profile."""
    actual = Argon2id(salt=b"\x02" * 16, length=32, iterations=3, lanes=4,
                     memory_cost=32, secret=b"\x03" * 8, ad=b"\x04" * 12).derive(b"\x01" * 32)
    assert actual.hex() == "0d640df58d78766c08c037a34a8b53c9d01ef0452d75b65eb52520e96b01e659"


@pytest.mark.parametrize("plain,cipher,tag", [
    ("", "", "530f8afbc74536b9a963b4f1c4cb738b"),
    ("00" * 16, "cea7403d4d606b6e074ec5d3baf39d18", "d0d1c8a799996bf0265b98b5d48ab919"),
])
def test_official_aes256_gcm_vectors(plain, cipher, tag):
    """GCM specification appendix B, test cases 13/14 (AES-256, 96-bit IV)."""
    aes = AESGCM(b"\x00" * 32)
    expected = bytes.fromhex(cipher + tag)
    assert aes.encrypt(b"\x00" * 12, bytes.fromhex(plain), b"") == expected
    assert aes.decrypt(b"\x00" * 12, expected, b"") == bytes.fromhex(plain)


def test_official_nist_aes256_gcm_with_aad_vector():
    """NIST AES_GCM.pdf, GCM-AES256 Example #4, pages 24-26 (zero based)."""
    key = bytes.fromhex("feffe9928665731c6d6a8f9467308308" * 2)
    nonce = bytes.fromhex("cafebabefacedbaddecaf888")
    aad = bytes.fromhex(
        "3ad77bb40d7a3660a89ecaf32466ef97f5d3d58503b9699de785895a96fdbaaf"
        "43b1cd7f598ece23881b00e3ed0306887b0c785e27e8ad3f8223207104725dd4")
    plain = bytes.fromhex(
        "d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a72"
        "1c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b391aafd255")
    expected = bytes.fromhex(
        "522dc1f099567d07f47f37a32a84427d643a8cdcbfe5c0c97598a2bd2555d1aa"
        "8cb08e48590dbb3da7b08b1056828838c5f61e6393ba7a0abcc9f662898015ad"
        "c06d76f31930fef37acae23ed465ae62")
    assert AESGCM(key).encrypt(nonce, plain, aad) == expected
    assert AESGCM(key).decrypt(nonce, expected, aad) == plain
