"""Real in-memory signing, byte verification and transaction failure coverage."""

import base64
import builtins
import importlib
import io
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from nacl.signing import VerifyKey
from pqcrypto.sign import falcon_512

import keygen
import sign
import signing_io
import utils
import verify


@pytest.fixture
def material():
    importlib.import_module("hybrid_keys")
    return keygen.generate_hybrid_key_pair()


def check(data, material):
    public = material.public_keys
    return verify.verify_bytes(data, public.ed25519_public_key, public.falcon_public_key)


def test_memory_signing_writes_no_private_keys(pdf_path, material, tmp_path, monkeypatch):
    original_open, original_io = builtins.open, io.open
    writes = []

    class Writer:
        def __init__(self, handle):
            self.handle = handle

        def __getattr__(self, name):
            return getattr(self.handle, name)

        def __enter__(self):
            self.handle.__enter__()
            return self

        def __exit__(self, *args):
            return self.handle.__exit__(*args)

        def write(self, data):
            writes.append(bytes(data))
            return self.handle.write(data)

    def opened(opener, file, mode="r", *args, **kwargs):
        handle = opener(file, mode, *args, **kwargs)
        return Writer(handle) if any(letter in mode for letter in "wax") else handle

    monkeypatch.setattr(builtins, "open", lambda *a, **kw: opened(original_open, *a, **kw))
    monkeypatch.setattr(io, "open", lambda *a, **kw: opened(original_io, *a, **kw))
    output = tmp_path / "memory.pdf"
    result = sign.sign_with_key_material(pdf_path, output, material)
    assert len(result) == 11 and result[0] == output
    assert check(output.read_bytes(), material)[0] is True
    assert writes
    for secret in (material.ed25519_private_seed, material.falcon_private_key):
        assert not any(secret in data or secret.hex().encode("ascii") in data for data in writes)
    assert set(tmp_path.iterdir()) == {pdf_path, output}


def test_pure_bytes_verification_has_no_filesystem_access(pdf_path, material, tmp_path, monkeypatch):
    output = tmp_path / "signed.pdf"
    sign.sign_with_key_material(pdf_path, output, material)
    data = output.read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("Byte verification attempted file I/O")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(io, "open", forbidden)
    result = check(data, material)
    assert result[0] is True and len(result) == 11
    assert result[9] == 0


@pytest.mark.parametrize("capacities", [(64, 752), (80, 1024), (128, 2048), (256, 4096)])
def test_memory_signing_preserves_protocol_and_custom_capacities(pdf_path, material, tmp_path, monkeypatch, capacities):
    import hashlib

    monkeypatch.setattr(sign, "DEFAULT_SIGNATURE_CAPACITIES", capacities)
    output = tmp_path / "custom.pdf"
    sign.sign_with_key_material(pdf_path, output, material)
    data = output.read_bytes()
    pair = utils.parse_signature_pair(data)
    assert (pair.ed25519.capacity_bytes, pair.falcon.capacity_bytes) == capacities
    ed, falcon = pair.ed25519, pair.falcon
    ed_message = data[:ed.gap_start] + data[ed.gap_end:ed.marker_end]
    ed_signature = bytes.fromhex(data[ed.contents_start:ed.contents_start + ed.signature_length].decode())
    assert VerifyKey(material.public_keys.ed25519_public_key).verify(ed_message, ed_signature) == ed_message
    fal_message = data[:falcon.gap_start] + data[falcon.gap_end:falcon.marker_end] + data[falcon.marker_end:]
    fal_signature = bytes.fromhex(data[falcon.contents_start:falcon.contents_start + falcon.signature_length].decode())
    assert ed.marker_end == falcon.marker_start and falcon.marker_end == len(data)
    assert falcon_512.verify(material.public_keys.falcon_public_key, hashlib.shake_256(fal_message).digest(64), fal_signature) is True
    assert check(data, material)[0] is True


@pytest.mark.parametrize("mutation", ["content", "append", "truncate", "padding", "range"])
def test_byte_verifier_preserves_strict_rejection(pdf_path, material, tmp_path, mutation):
    output = tmp_path / "signed.pdf"
    sign.sign_with_key_material(pdf_path, output, material)
    data = output.read_bytes()
    if mutation == "content":
        data = data.replace(b"Phase 1", b"phase 1", 1)
    elif mutation == "append":
        data += b" "
    elif mutation == "truncate":
        data = data[:-1]
    elif mutation == "padding":
        position = utils.parse_signature_pair(data).falcon.contents_end - 1
        data = data[:position] + b"1" + data[position + 1:]
    else:
        data = data.replace(b"ByteRange: [ 0000000000", b"ByteRange: [ 0000000001", 1)
    result = check(data, material)
    assert len(result) == 11 and result[0] is False


@pytest.mark.parametrize("layer", ["ed25519", "falcon"])
def test_wrong_public_keys_fail_byte_verification(pdf_path, material, tmp_path, layer):
    output = tmp_path / "signed.pdf"
    sign.sign_with_key_material(pdf_path, output, material)
    other = keygen.generate_hybrid_key_pair().public_keys
    own = material.public_keys
    result = verify.verify_bytes(output.read_bytes(),
        other.ed25519_public_key if layer == "ed25519" else own.ed25519_public_key,
        other.falcon_public_key if layer == "falcon" else own.falcon_public_key)
    assert result[0] is False


@pytest.mark.parametrize("fault", ["ed25519", "falcon", "stage", "candidate", "fsync", "verifier-false", "verifier-exception", "replace"])
@pytest.mark.parametrize("existing", [False, True])
def test_memory_signing_failures_preserve_destination_and_cleanup(pdf_path, material, tmp_path, monkeypatch, fault, existing):
    output = tmp_path / "preserved.pdf"
    if existing:
        output.write_bytes(b"previous destination")
    failure = OSError("injected " + fault)

    def fail(*args, **kwargs):
        raise failure

    if fault == "ed25519":
        monkeypatch.setattr(sign, "SigningKey", lambda seed: type("Broken", (), {"sign": fail})())
    elif fault == "falcon":
        native = falcon_512.sign
        monkeypatch.setattr(falcon_512, "sign", lambda key, message: fail() if len(message) == 64 else native(key, message))
    elif fault == "stage":
        write = signing_io.SigningTransaction.write_stage

        def partial(tx, name, data):
            write(tx, name, data[:3])
            fail()

        monkeypatch.setattr(signing_io.SigningTransaction, "write_stage", partial)
    elif fault == "candidate":
        write = signing_io.SigningTransaction.write_candidate

        def partial(tx, data):
            write(tx, data[:7])
            fail()

        monkeypatch.setattr(signing_io.SigningTransaction, "write_candidate", partial)
    elif fault == "fsync":
        monkeypatch.setattr(os, "fsync", fail)
    elif fault == "verifier-false":
        monkeypatch.setattr(sign, "verify_file_with_public_keys", lambda *args: (False,) + (0,) * 10)
    elif fault == "verifier-exception":
        monkeypatch.setattr(sign, "verify_file_with_public_keys", fail)
    else:
        monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(ValueError if fault == "verifier-false" else OSError):
        sign.sign_with_key_material(pdf_path, output, material)
    assert output.read_bytes() == b"previous destination" if existing else not output.exists()
    assert not list(tmp_path.glob(".esign-*"))


def test_memory_candidate_is_closed_fsynced_and_verified_before_single_replace(pdf_path, material, tmp_path, monkeypatch):
    output = tmp_path / "signed.pdf"
    events = []
    fsync, replace = os.fsync, os.replace
    original_verify = verify.verify_file_with_public_keys

    def sync(fd):
        events.append("fsync")
        return fsync(fd)

    def verify_candidate(candidate, ed, falcon):
        assert events == ["fsync"]
        assert type(ed) is type(falcon) is bytes
        with open(candidate, "r+b"):
            pass
        result = original_verify(candidate, ed, falcon)
        assert result[0] is True
        events.append("verify")
        return result

    def publish(candidate, destination):
        assert events == ["fsync", "verify"]
        assert not list(tmp_path.glob(".esign-work-*"))
        events.append("replace")
        return replace(candidate, destination)

    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(sign, "verify_file_with_public_keys", verify_candidate)
    monkeypatch.setattr(os, "replace", publish)
    sign.sign_with_key_material(pdf_path, output, material)
    assert events == ["fsync", "verify", "replace"]


@pytest.mark.parametrize("alias", ["same", "relative", "hardlink"])
def test_memory_signer_rejects_source_aliases(pdf_path, material, tmp_path, monkeypatch, alias):
    original = pdf_path.read_bytes()
    output = pdf_path
    if alias == "relative":
        monkeypatch.chdir(tmp_path)
        output = Path("./original.pdf")
    elif alias == "hardlink":
        output = tmp_path / "link.pdf"
        os.link(pdf_path, output)
    with pytest.raises(ValueError) as error:
        sign.sign_with_key_material(pdf_path, output, material)
    assert error.value.code == "path.alias"
    assert pdf_path.read_bytes() == original


def test_memory_signer_checks_original_snapshot_only(pdf_path, material, tmp_path, monkeypatch):
    original = pdf_path.read_bytes()
    validate = sign.validate_unsigned_input

    def modify_after_check(data):
        validate(data)
        pdf_path.write_bytes(b"changed live input")

    monkeypatch.setattr(sign, "validate_unsigned_input", modify_after_check)
    output = tmp_path / "snapshot.pdf"
    sign.sign_with_key_material(pdf_path, output, material)
    assert output.read_bytes().startswith(original)
    assert check(output.read_bytes(), material)[0] is True


@pytest.mark.parametrize("field", ["ed25519_private_seed", "falcon_private_key"])
def test_revalidation_rejects_modified_key_object_before_staging(pdf_path, material, tmp_path, field):
    object.__setattr__(material, field, b"bad")
    with patch.object(signing_io.tempfile, "mkdtemp") as create:
        with pytest.raises(ValueError):
            sign.sign_with_key_material(pdf_path, tmp_path / "never.pdf", material)
        create.assert_not_called()


@pytest.mark.parametrize("index", [0, 1])
def test_frozen_phase1_signatures_verify_with_bytes_keys(tmp_path, index):
    cases = json.loads((Path(__file__).parent / "fixtures/phase1-signatures.json").read_text())["cases"]
    case = cases[index]
    data, ed, falcon = [base64.b64decode(case[name], validate=True) for name in
                       ("pdf_base64", "ed25519_public_base64", "falcon_public_base64")]
    result = verify.verify_bytes(data, ed, falcon)
    assert result[0] is True and len(result) == 11
    path = tmp_path / "legacy.pdf"
    path.write_bytes(data)
    assert verify.verify_file_with_public_keys(path, ed, falcon)[0] is True


@pytest.mark.parametrize("field", ["document", "ed", "falcon"])
@pytest.mark.parametrize("kind", ["mutable", "string", "none"])
def test_byte_api_rejects_nonbytes_without_normalizing(material, field, kind):
    values = {"document": b"%PDF-1.4\n", "ed": material.public_keys.ed25519_public_key,
              "falcon": material.public_keys.falcon_public_key}
    original = values[field]
    values[field] = bytearray(original) if kind == "mutable" else original.hex() if kind == "string" else None
    with pytest.raises(TypeError):
        verify.verify_bytes(values["document"], values["ed"], values["falcon"])


@pytest.mark.parametrize("field", ["ed", "falcon"])
@pytest.mark.parametrize("delta", [-1, 1])
def test_byte_api_invalid_key_lengths_keep_failure_tuple_without_opening_file(material, tmp_path, field, delta):
    values = {"ed": material.public_keys.ed25519_public_key, "falcon": material.public_keys.falcon_public_key}
    original = values[field]
    values[field] = original[:-1] if delta == -1 else original + b"x"
    expected = (False,) + (0,) * 10
    assert verify.verify_bytes(b"", values["ed"], values["falcon"]) == expected
    assert verify.verify_file_with_public_keys(tmp_path / "missing.pdf", values["ed"], values["falcon"]) == expected


def test_byte_api_rejects_structure_before_either_crypto_verifier(material):
    with patch.object(verify, "VerifyKey") as ed, patch.object(falcon_512, "verify") as falcon:
        result = check(b"%PDF-1.4\n%%FALCON_PQ_SIG_START\n", material)
    assert result[0] is False and len(result) == 11
    ed.assert_not_called()
    falcon.assert_not_called()


def test_memory_and_legacy_signers_have_identical_selected_messages(pdf_path, keys, tmp_path, monkeypatch):
    model = importlib.import_module("hybrid_keys")
    material = model.HybridKeyPair(model.HybridPublicKey(keys.pk_ed.read_bytes(), keys.pk_falcon.read_bytes()),
                                   keys.sk_ed.read_bytes(), keys.sk_falcon.read_bytes())
    native_ed = sign.compute_sha512_digest_for_byte_range
    native_falcon = sign.compute_shake256_digest_for_byte_range
    messages = {"ed": [], "falcon": []}

    def ed_message(*args):
        value = native_ed(*args)
        messages["ed"].append(value)
        return value

    def falcon_message(*args):
        value = native_falcon(*args)
        messages["falcon"].append(value)
        return value

    monkeypatch.setattr(sign, "compute_sha512_digest_for_byte_range", ed_message)
    monkeypatch.setattr(sign, "compute_shake256_digest_for_byte_range", falcon_message)
    legacy, memory = tmp_path / "legacy.pdf", tmp_path / "memory.pdf"
    sign.sign_file(pdf_path, legacy, keys.sk_ed, keys.sk_falcon, pk_falcon=keys.pk_falcon)
    sign.sign_with_key_material(pdf_path, memory, material)
    for values in messages.values():
        assert len(values) == 2 and values[0] == values[1]
    left, right = legacy.read_bytes(), memory.read_bytes()
    boundary = utils.parse_signature_pair(left).ed25519.marker_end
    assert left[:boundary] == right[:boundary]
    assert check(left, material)[0] is check(right, material)[0] is True
