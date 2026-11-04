"""Characterize the inherited Ed25519-then-Falcon protocol with real crypto."""

import hashlib

import pytest
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from pqcrypto.sign import falcon_512

from sign import sign_file
from utils import (
    CONTENTS_PREFIX,
    SIG_MARKER_START,
    compute_sha512_digest_for_byte_range,
    compute_shake256_digest_for_byte_range,
    embed_signature_into_pdf,
    extract_byte_range_and_placeholder,
    extract_signature_hex_from_pdf,
)
from verify import verify_file


def layer_results(data, keys):
    """Verify the two layers separately so an AND regression cannot hide."""
    ed_range, _, _ = extract_byte_range_and_placeholder(data, 0)
    ed_signature = bytes.fromhex(extract_signature_hex_from_pdf(data, 0).decode())
    try:
        VerifyKey(keys.pk_ed.read_bytes()).verify(
            compute_sha512_digest_for_byte_range(data, ed_range), ed_signature
        )
        ed_ok = True
    except BadSignatureError:
        ed_ok = False
    fal_range, _, _ = extract_byte_range_and_placeholder(data, 1)
    fal_signature = bytes.fromhex(extract_signature_hex_from_pdf(data, 1).decode())
    fal_ok = falcon_512.verify(
        keys.pk_falcon.read_bytes(),
        compute_shake256_digest_for_byte_range(data, fal_range), fal_signature,
    )
    return ed_ok, fal_ok


def test_sign_and_verify_preserve_input_and_tuple_contract(pdf_path, pdf_bytes, keys, tmp_path):
    output = tmp_path / "roundtrip.pdf"
    signing_result = sign_file(pdf_path, output, keys.sk_ed, keys.sk_falcon, pk_falcon=keys.pk_falcon)
    assert isinstance(signing_result, tuple) and len(signing_result) == 11
    assert signing_result[0] == output
    assert pdf_path.read_bytes() == pdf_bytes
    assert output.read_bytes().startswith(pdf_bytes)

    result = verify_file(output, keys.pk_ed, keys.pk_falcon)
    assert isinstance(result, tuple) and len(result) == 11
    assert result[0] is True
    assert layer_results(output.read_bytes(), keys) == (True, True)


def test_signatures_cover_the_inherited_sequential_messages(signed_pdf, keys):
    data = signed_pdf.read_bytes()
    ed_range, _, ed_end = extract_byte_range_and_placeholder(data, 0)
    fal_range, fal_start, fal_end = extract_byte_range_and_placeholder(data, 1)
    a, b, c, d = ed_range
    ed_message = data[a:a + b] + data[c:c + d]
    assert a == 0 and c + d == ed_end == fal_start
    assert ed_message == compute_sha512_digest_for_byte_range(data, ed_range)
    assert len(ed_message) > 64  # Preserve raw-message Ed25519, not a new prehash.
    ed_signature = bytes.fromhex(extract_signature_hex_from_pdf(data, 0).decode())
    assert len(ed_signature) == 64
    assert VerifyKey(keys.pk_ed.read_bytes()).verify(ed_message, ed_signature) == ed_message

    a, b, c, d = fal_range
    assert a == 0 and b > ed_end and c + d == fal_end == len(data)
    assert data[:b].find(ed_signature.hex().encode()) != -1
    fal_message = data[a:a + b] + data[c:c + d] + data[c + d:]
    digest = hashlib.shake_256(fal_message).digest(64)
    assert digest == compute_shake256_digest_for_byte_range(data, fal_range)
    fal_signature = bytes.fromhex(extract_signature_hex_from_pdf(data, 1).decode())
    assert falcon_512.verify(keys.pk_falcon.read_bytes(), digest, fal_signature) is True


@pytest.mark.parametrize("alteration", ["content", "append", "truncate"])
def test_altered_document_is_rejected(signed_pdf, keys, alteration):
    data = signed_pdf.read_bytes()
    if alteration == "content":
        assert b"Phase 1" in data
        data = data.replace(b"Phase 1", b"phase 1", 1)
    elif alteration == "append":
        data += b"\n% Unapproved appended revision\n"
    else:
        data = data[:-20]
    signed_pdf.write_bytes(data)
    assert verify_file(signed_pdf, keys.pk_ed, keys.pk_falcon)[0] is False


@pytest.mark.parametrize("wrong_layer", ["ed25519", "falcon", "both"])
def test_incorrect_public_keys_are_rejected(signed_pdf, keys, key_factory, wrong_layer):
    other = key_factory()
    pk_ed = other.pk_ed if wrong_layer in ("ed25519", "both") else keys.pk_ed
    pk_falcon = other.pk_falcon if wrong_layer in ("falcon", "both") else keys.pk_falcon
    assert verify_file(signed_pdf, pk_ed, pk_falcon)[0] is False


@pytest.mark.parametrize("broken_layer", [0, 1], ids=["ed25519-only-invalid", "falcon-only-invalid"])
def test_failure_of_either_signature_layer_is_rejected(signed_pdf, keys, broken_layer):
    data = signed_pdf.read_bytes()
    start = data.index(SIG_MARKER_START[broken_layer])
    position = data.index(CONTENTS_PREFIX, start) + len(CONTENTS_PREFIX)
    replacement = b"0" if data[position:position + 1] != b"0" else b"1"
    data = data[:position] + replacement + data[position + 1:]

    if broken_layer == 0:
        # Ed25519 corruption also breaks Falcon. Re-sign only the outer layer
        # to prove the verifier rejects (invalid Ed25519, valid Falcon).
        byte_range, _, _ = extract_byte_range_and_placeholder(data, 1)
        signature = falcon_512.sign(
            keys.sk_falcon.read_bytes(), compute_shake256_digest_for_byte_range(data, byte_range)
        )
        data = embed_signature_into_pdf(data, signature, 1)

    expected = (False, True) if broken_layer == 0 else (True, False)
    assert layer_results(data, keys) == expected
    signed_pdf.write_bytes(data)
    assert verify_file(signed_pdf, keys.pk_ed, keys.pk_falcon)[0] is False


def test_unsigned_pdf_is_rejected(pdf_path, keys):
    assert verify_file(pdf_path, keys.pk_ed, keys.pk_falcon)[0] is False


@pytest.mark.parametrize("layer", ["ed25519", "falcon"])
def test_wrong_length_public_key_keeps_failure_tuple(signed_pdf, keys, tmp_path, layer):
    invalid_key = tmp_path / "invalid.key"
    invalid_key.write_bytes(b"invalid")
    result = verify_file(
        signed_pdf,
        invalid_key if layer == "ed25519" else keys.pk_ed,
        invalid_key if layer == "falcon" else keys.pk_falcon,
    )
    assert isinstance(result, tuple) and len(result) == 11
    assert result[0] is False
