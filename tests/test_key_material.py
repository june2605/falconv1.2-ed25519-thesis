"""Versioned in-memory keys; every private key here is freshly disposable."""

from dataclasses import FrozenInstanceError, replace
import hashlib
import importlib
import io
import builtins
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from nacl.signing import SigningKey
from pqcrypto.sign import falcon_512

import keygen


@pytest.fixture
def model():
    return importlib.import_module("hybrid_keys")


@pytest.fixture
def material(model):
    return keygen.generate_hybrid_key_pair()


def test_memory_generator_has_no_filesystem_operations(model, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("In-memory key generation attempted file I/O")

    import tempfile
    for target, name in ((builtins, "open"), (io, "open"), (Path, "write_bytes"),
                         (tempfile, "mkstemp"), (tempfile, "mkdtemp")):
        monkeypatch.setattr(target, name, forbidden)
    pair = keygen.generate_hybrid_key_pair()
    assert type(pair) is model.HybridKeyPair
    assert len(pair.ed25519_private_seed) == 32
    assert len(pair.falcon_private_key) == falcon_512.SECRET_KEY_SIZE
    assert bytes(SigningKey(pair.ed25519_private_seed).verify_key) == pair.public_keys.ed25519_public_key
    model.validate_key_pair(pair)


def test_legacy_generator_delegates_to_memory_generator(model, material, tmp_path, monkeypatch):
    generate = SimpleNamespace(count=0)

    def captured():
        generate.count += 1
        return material

    monkeypatch.setattr(keygen, "generate_hybrid_key_pair", captured)
    paths = [tmp_path / name for name in ("ed.pub", "ed.seed", "falcon.pub", "falcon.secret")]
    assert keygen.generate_keys(*paths) is None
    assert generate.count == 1
    assert [path.read_bytes() for path in paths] == [material.public_keys.ed25519_public_key,
        material.ed25519_private_seed, material.public_keys.falcon_public_key, material.falcon_private_key]


def test_independent_generation_and_safe_repr(model, material):
    other = keygen.generate_hybrid_key_pair()
    assert material.key_id != other.key_id
    assert material.public_keys != other.public_keys
    assert material.ed25519_private_seed != other.ed25519_private_seed
    assert material.falcon_private_key != other.falcon_private_key
    rendered = repr(material)
    assert material.key_id in rendered
    for secret in (material.ed25519_private_seed, material.falcon_private_key):
        assert repr(secret) not in rendered and secret.hex() not in rendered
    with pytest.raises(FrozenInstanceError):
        material.ed25519_private_seed = other.ed25519_private_seed


def test_id_uses_exact_domain_and_uint32_length_prefixes(model):
    ed = bytes(range(32))
    falcon = b"\x09" + bytes(i % 256 for i in range(896))
    fields = (b"ed25519", ed, b"falcon_512", falcon)
    preimage = b"THESIS-HYBRID-KEY-ID-v1\x00" + b"".join(len(value).to_bytes(4, "big") + value for value in fields)
    expected = "hybrid-v1:" + hashlib.sha256(preimage).hexdigest()
    assert expected == "hybrid-v1:4f6c8719d24379243002c5f1f71172570b5985784d4875539ebeaec30dea1f64"
    assert model.hybrid_key_id(ed, falcon) == expected
    public = model.HybridPublicKey(ed, falcon)
    assert public.key_id == expected
    assert model.hybrid_key_id(ed, falcon) == model.hybrid_key_id(bytes(ed), bytes(falcon))
    assert model.hybrid_key_id(ed[::-1], falcon) != expected
    assert model.hybrid_key_id(ed, falcon[:-1] + b"\x00") != expected
    assert expected != "hybrid-v1:" + hashlib.sha256(b"".join(fields)).hexdigest()


@pytest.mark.parametrize("version", [0, 2, True, "1", None])
def test_unsupported_versions_are_rejected(model, material, version):
    with pytest.raises(model.KeyMaterialError) as error:
        replace(material.public_keys, version=version)
    assert error.value.code == "key.version"


@pytest.mark.parametrize("field,value", [("ed25519_algorithm", "Ed25519"), ("ed25519_algorithm", "ed25519ph"),
    ("falcon_algorithm", "falcon_padded_512"), ("falcon_algorithm", "falcon_1024"),
    ("falcon_algorithm", "falcon-v1.2"), ("falcon_algorithm", None)])
def test_algorithm_identifiers_are_exact(model, material, field, value):
    with pytest.raises(model.KeyMaterialError) as error:
        replace(material.public_keys, **{field: value})
    assert error.value.code == "key.algorithm"


@pytest.mark.parametrize("field", ["ed25519_public_key", "falcon_public_key", "ed25519_private_seed", "falcon_private_key"])
@pytest.mark.parametrize("delta", [-1, 1])
def test_key_size_bounds_are_checked_before_native_crypto(model, material, field, delta):
    target = material.public_keys if "public" in field else material
    original = getattr(target, field)
    value = original[:-1] if delta == -1 else original + b"x"
    with patch.object(model, "SigningKey") as ed, patch.object(model.falcon_512, "sign") as falcon:
        with pytest.raises(model.KeyMaterialError) as error:
            replace(target, **{field: value})
        ed.assert_not_called()
        falcon.assert_not_called()
    assert error.value.code == "key.size"


@pytest.mark.parametrize("field", ["ed25519_public_key", "falcon_public_key", "ed25519_private_seed", "falcon_private_key"])
@pytest.mark.parametrize("kind", ["bytearray", "memoryview", "none", "string"])
def test_key_material_requires_immutable_bytes(model, material, field, kind):
    target = material.public_keys if "public" in field else material
    original = getattr(target, field)
    value = {"bytearray": lambda: bytearray(original), "memoryview": lambda: memoryview(original),
             "none": lambda: None, "string": lambda: original.hex()}[kind]()
    with pytest.raises(model.KeyMaterialError) as error:
        replace(target, **{field: value})
    assert error.value.code == "key.type"


@pytest.mark.parametrize("layer", ["ed25519", "falcon"])
def test_mismatched_public_and_private_keys_reject(model, material, layer):
    other = keygen.generate_hybrid_key_pair()
    public = replace(material.public_keys, **{
        "ed25519_public_key" if layer == "ed25519" else "falcon_public_key":
        other.public_keys.ed25519_public_key if layer == "ed25519" else other.public_keys.falcon_public_key})
    with pytest.raises(model.KeyMaterialError) as error:
        replace(material, public_keys=public)
    assert error.value.code == ("key.correspondence" if layer == "ed25519" else "key.self_test")


@pytest.mark.parametrize("fault", ["ed-signature", "ed-verify", "falcon-signature", "falcon-false", "falcon-nonboolean", "falcon-exception"])
def test_both_self_tests_fail_closed_with_sanitized_errors(model, material, monkeypatch, fault):
    secret_message = "native error with private data must not escape"
    if fault == "ed-signature":
        native = model.SigningKey
        monkeypatch.setattr(model, "SigningKey", lambda seed: SimpleNamespace(
            verify_key=native(seed).verify_key, sign=lambda message: SimpleNamespace(signature=b"x" * 64)))
    elif fault == "ed-verify":
        monkeypatch.setattr(model, "VerifyKey", lambda key: SimpleNamespace(
            verify=lambda *args: (_ for _ in ()).throw(ValueError(secret_message))))
    elif fault == "falcon-signature":
        monkeypatch.setattr(model.falcon_512, "sign", lambda *args: b"x" * (falcon_512.SIGNATURE_SIZE + 1))
    elif fault in ("falcon-false", "falcon-nonboolean"):
        monkeypatch.setattr(model.falcon_512, "verify", lambda *args: False if fault.endswith("false") else 1)
    else:
        monkeypatch.setattr(model.falcon_512, "sign", lambda *args: (_ for _ in ()).throw(RuntimeError(secret_message)))
    with pytest.raises(model.KeyMaterialError) as error:
        model.validate_key_pair(material)
    assert error.value.code == "key.self_test"
    assert secret_message not in str(error.value)
    assert error.value.__suppress_context__ is True


def test_generation_failure_returns_no_partial_pair_or_files(model, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(keygen.falcon_512, "generate_keypair", lambda: (_ for _ in ()).throw(OSError("rng failure")))
    with pytest.raises(OSError, match="rng failure"):
        keygen.generate_hybrid_key_pair()
    assert list(tmp_path.iterdir()) == []


def test_signing_validation_does_not_trust_a_bypassed_frozen_constructor(model, material):
    object.__setattr__(material.public_keys, "version", 2)
    with pytest.raises(model.KeyMaterialError) as error:
        model.validate_key_pair(material)
    assert error.value.code == "key.version"


@pytest.mark.parametrize("field", ["falcon_public_key", "falcon_private_key"])
def test_size_correct_invalid_falcon_encodings_fail_native_self_test(model, material, field):
    if field == "falcon_public_key":
        public = replace(material.public_keys, falcon_public_key=b"\x00" + material.public_keys.falcon_public_key[1:])
        changes = {"public_keys": public}
    else:
        changes = {field: b"\x00" + material.falcon_private_key[1:]}
    with pytest.raises(model.KeyMaterialError) as error:
        replace(material, **changes)
    assert error.value.code == "key.self_test"


def test_revalidation_uses_fresh_context_and_does_not_change_key_id(model, material, monkeypatch):
    native = model.falcon_512.sign
    messages = []

    def record(secret, message):
        messages.append(message)
        return native(secret, message)

    monkeypatch.setattr(model.falcon_512, "sign", record)
    original_id = material.key_id
    model.validate_key_pair(material)
    model.validate_key_pair(material)
    assert len(messages) == 2 and messages[0] != messages[1]
    assert all(message.startswith(b"THESIS-HYBRID-KEY-SELF-TEST-v1\x00falcon_512\x00") for message in messages)
    assert material.key_id == original_id


@pytest.mark.parametrize("value", [None, (), {}, b"not a model"])
def test_validation_rejects_non_model_objects(model, value):
    with pytest.raises(model.KeyMaterialError) as error:
        model.validate_key_pair(value)
    assert error.value.code == "key.type"
