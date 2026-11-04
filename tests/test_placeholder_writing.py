"""Preparation and embedding must not patch source text or grow placeholders."""

import os

import pytest
from nacl.bindings import crypto_sign_BYTES
from pqcrypto.sign import falcon_512

from conftest import make_pdf
import sign
import utils
from verify import verify_file


@pytest.mark.parametrize("sign_type", [0, 1], ids=["ed25519", "falcon"])
def test_ordinary_placeholder_text_is_not_modified(tmp_path, sign_type):
    text = (utils.ZERO_BYTE_RANGE + b"SigLength: 0000000001\nContents: <00>\n" + utils.ZERO_BYTE_RANGE).decode("ascii")
    original = make_pdf(text)
    source, output = tmp_path / "source.pdf", tmp_path / "prepared.pdf"
    source.write_bytes(original)
    utils.prepare_file_with_placeholder(source, output, utils.DEFAULT_SIGNATURE_CAPACITIES[sign_type], sign_type)
    prepared = output.read_bytes()
    assert source.read_bytes() == original
    assert prepared[:len(original)] == original
    parsed = utils.parse_prepared_placeholder(prepared, sign_type)
    assert parsed.marker_start == len(original) and parsed.marker_end == len(prepared)


def test_signing_pdf_with_placeholder_like_content_remains_valid(keys, tmp_path):
    original = make_pdf((utils.ZERO_BYTE_RANGE + b"SigLength: 0000000010 Contents: <00>").decode("ascii"))
    source, output = tmp_path / "ordinary-text.pdf", tmp_path / "signed.pdf"
    source.write_bytes(original)
    sign.sign_file(source, output, keys.sk_ed, keys.sk_falcon)
    assert source.read_bytes() == original
    assert output.read_bytes().startswith(original)
    assert verify_file(output, keys.pk_ed, keys.pk_falcon)[0] is True


@pytest.mark.parametrize("capacity", [0, -1, True, False, 1.5, "128", None])
@pytest.mark.parametrize("sign_type", [0, 1])
def test_invalid_capacity_is_rejected_before_destination_write(tmp_path, capacity, sign_type):
    source, output = tmp_path / "source.pdf", tmp_path / "existing.pdf"
    original, sentinel = make_pdf("Capacity control"), b"Destination sentinel"
    source.write_bytes(original)
    output.write_bytes(sentinel)
    with pytest.raises(ValueError) as error:
        utils.prepare_file_with_placeholder(source, output, capacity, sign_type)
    assert error.value.code == "placeholder.capacity"
    assert source.read_bytes() == original and output.read_bytes() == sentinel


@pytest.mark.parametrize("capacity", [10**100, 4999999999])
@pytest.mark.parametrize("sign_type", [0, 1])
def test_oversized_dimensions_are_rejected_before_building(capacity, sign_type):
    with pytest.raises(ValueError) as error:
        utils.prepare_bytes_with_placeholder(b"%PDF-1.4\n", capacity, sign_type)
    assert error.value.code == "placeholder.capacity"


@pytest.mark.parametrize("sign_type", [-1, 2, True, 0.0, "0"])
def test_invalid_signature_type_cannot_select_or_overwrite_a_container(tmp_path, sign_type):
    source, output = tmp_path / "source.pdf", tmp_path / "existing.pdf"
    original, sentinel = make_pdf("Type control"), b"Destination sentinel"
    source.write_bytes(original)
    output.write_bytes(sentinel)
    with pytest.raises(ValueError) as error:
        utils.prepare_file_with_placeholder(source, output, 128, sign_type)
    assert error.value.code == "container.type"
    assert source.read_bytes() == original and output.read_bytes() == sentinel


def test_in_place_preparation_validation_failure_leaves_input_unchanged(tmp_path):
    source = tmp_path / "in-place.pdf"
    original = make_pdf("In-place helper control")
    source.write_bytes(original)
    with pytest.raises(ValueError):
        utils.prepare_file_with_placeholder(source, source, -1)
    assert source.read_bytes() == original


@pytest.mark.parametrize("capacity", [crypto_sign_BYTES - 1, crypto_sign_BYTES, crypto_sign_BYTES + 1])
def test_ed25519_placeholder_minimum_capacity(tmp_path, capacity):
    source, output = tmp_path / "source.pdf", tmp_path / "prepared.pdf"
    source.write_bytes(make_pdf("Ed capacity boundary"))
    if capacity < crypto_sign_BYTES:
        with pytest.raises(ValueError) as error:
            utils.prepare_file_with_placeholder(source, output, capacity, 0)
        assert error.value.code == "placeholder.capacity" and not output.exists()
    else:
        utils.prepare_file_with_placeholder(source, output, capacity, 0)
        assert utils.parse_prepared_placeholder(output.read_bytes()).capacity_bytes == capacity


@pytest.mark.parametrize("sign_type,size", [(0, crypto_sign_BYTES), (1, falcon_512.SIGNATURE_SIZE), (1, 650)])
@pytest.mark.parametrize("extra_capacity", [0, 1, 16])
def test_exact_fit_and_custom_capacity_preserve_layout(tmp_path, sign_type, size, extra_capacity):
    source, output = tmp_path / "source.pdf", tmp_path / "prepared.pdf"
    original = make_pdf("Embedding boundary")
    source.write_bytes(original)
    capacity = size + extra_capacity
    utils.prepare_file_with_placeholder(source, output, capacity, sign_type)
    prepared = output.read_bytes()
    before = utils.parse_prepared_placeholder(prepared, sign_type)
    signature = b"\xab" * size
    embedded = utils.embed_signature_into_pdf(prepared, signature, sign_type)
    after = utils.parse_completed_signature(embedded, sign_type)
    assert len(embedded) == len(prepared)
    assert embedded[:len(original)] == original
    assert before.byte_range == after.byte_range
    assert (before.marker_start, before.marker_end) == (after.marker_start, after.marker_end)
    assert utils.extract_signature_hex_from_pdf(embedded, sign_type) == signature.hex().encode()


def test_one_byte_falcon_capacity_overflow_is_explicit(tmp_path):
    source, output = tmp_path / "source.pdf", tmp_path / "prepared.pdf"
    source.write_bytes(make_pdf("Falcon capacity boundary"))
    utils.prepare_file_with_placeholder(source, output, falcon_512.SIGNATURE_SIZE - 1, 1)
    prepared = output.read_bytes()
    with pytest.raises(ValueError) as error:
        utils.embed_signature_into_pdf(prepared, b"\xab" * falcon_512.SIGNATURE_SIZE, 1)
    assert error.value.code == "signature.capacity"
    assert output.read_bytes() == prepared


@pytest.mark.parametrize("sign_type,size", [(0, 0), (0, 63), (0, 65), (1, 0), (1, falcon_512.SIGNATURE_SIZE + 1)])
def test_signature_algorithm_size_is_checked_before_embedding(tmp_path, sign_type, size):
    source, output = tmp_path / "source.pdf", tmp_path / "prepared.pdf"
    source.write_bytes(make_pdf("Signature size control"))
    utils.prepare_file_with_placeholder(source, output, utils.DEFAULT_SIGNATURE_CAPACITIES[sign_type], sign_type)
    prepared = output.read_bytes()
    with pytest.raises(ValueError) as error:
        utils.embed_signature_into_pdf(prepared, b"\xab" * size, sign_type)
    assert error.value.code == "signature.size"
    assert output.read_bytes() == prepared


def test_byte_builder_does_not_reuse_an_existing_target_marker(tmp_path):
    original = make_pdf("No marker collision")
    source, output = tmp_path / "source.pdf", tmp_path / "prepared.pdf"
    source.write_bytes(original)
    utils.prepare_file_with_placeholder(source, output)
    prepared = output.read_bytes()
    with pytest.raises(ValueError) as error:
        utils.prepare_bytes_with_placeholder(prepared)
    assert error.value.code == "placeholder.marker"


@pytest.mark.parametrize("signature_type", [bytes, bytearray, memoryview])
def test_safe_bytes_like_signatures_remain_supported(tmp_path, signature_type):
    source, output = tmp_path / "source.pdf", tmp_path / "prepared.pdf"
    source.write_bytes(make_pdf("Bytes-like signature"))
    utils.prepare_file_with_placeholder(source, output)
    result = utils.embed_signature_into_pdf(output.read_bytes(), signature_type(b"\xab" * 64))
    assert utils.parse_completed_signature(result).signature_length == 128


def test_file_wrapper_marker_rejection_does_not_overwrite(tmp_path):
    source, output = tmp_path / "source.pdf", tmp_path / "output.pdf"
    original = make_pdf("Literal %%ED25519_PQ_SIG_START")
    sentinel = b"Do not overwrite on marker rejection"
    source.write_bytes(original)
    output.write_bytes(sentinel)
    with pytest.raises(ValueError) as error:
        utils.prepare_file_with_placeholder(source, output)
    assert error.value.code == "placeholder.marker"
    assert source.read_bytes() == original and output.read_bytes() == sentinel


def test_file_wrapper_rejects_hidden_hard_link_alias(tmp_path):
    source, output = tmp_path / "source.pdf", tmp_path / "alias.pdf"
    original = make_pdf("Hidden helper alias")
    source.write_bytes(original)
    os.link(source, output)
    with pytest.raises(ValueError) as error:
        utils.prepare_file_with_placeholder(source, output)
    assert error.value.code == "path.alias"
    assert source.read_bytes() == output.read_bytes() == original
