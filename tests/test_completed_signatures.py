"""Completed metadata is checked on original bytes, before native verification."""

import pytest
from nacl.bindings import crypto_sign_BYTES
from pqcrypto.sign import falcon_512

from container_cases import make_container
from utils import (
    SignatureFormatError,
    compute_sha512_digest_for_byte_range,
    compute_shake256_digest_for_byte_range,
    embed_signature_into_pdf,
    extract_signature_hex_from_pdf,
    parse_completed_signature,
    parse_prepared_placeholder,
    parse_signature_container,
    prepare_file_with_placeholder,
)
from verify import verify_file


@pytest.fixture(params=[0, 1], ids=["ed25519", "falcon"])
def completed_case(request):
    case = make_container(request.param)
    parsed = parse_completed_signature(case.data, case.sign_type)
    assert parsed.signature_length == (128 if case.sign_type == 0 else 1300)
    return case


def set_length(case, value):
    """Modify only the excluded decimal count, preserving all offsets."""
    left = case.data.index(b"SigLength: ", case.gap_start) + len(b"SigLength: ")
    return case.data[:left] + b"%010d" % value + case.data[left + 10:]


@pytest.mark.parametrize("value", [0, 1, 127, 129, 9999999999])
def test_zero_odd_and_outside_capacity_lengths_are_rejected(completed_case, value):
    with pytest.raises(SignatureFormatError) as error:
        parse_completed_signature(set_length(completed_case, value), completed_case.sign_type)
    assert error.value.code == "metadata.length"


@pytest.mark.parametrize("value", [2, 126, 130, 256])
def test_ed25519_requires_exactly_128_hex_characters(value):
    case = make_container(0)
    assert parse_completed_signature(case.data).signature_length == 128
    with pytest.raises(SignatureFormatError) as error:
        parse_completed_signature(set_length(case, value))
    assert error.value.code == "metadata.signature_size"


def test_falcon_maximum_comes_from_installed_implementation(monkeypatch):
    case = make_container(1)
    assert parse_completed_signature(case.data, 1).signature_length == 1300
    # Prove the validator consults the binding rather than a copied 752 limit.
    monkeypatch.setattr(falcon_512, "SIGNATURE_SIZE", 649)
    with pytest.raises(SignatureFormatError) as error:
        parse_completed_signature(case.data, 1)
    assert error.value.code == "metadata.signature_size"


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_falcon_variable_length_metadata_at_implementation_limit(delta):
    case = make_container(1)
    length_bytes = falcon_512.SIGNATURE_SIZE + delta
    left = case.data.index(b"SigLength: ") + len(b"SigLength: ")
    payload = (b"ab" * length_bytes).ljust(case.contents_end - case.contents_start, b"0")
    data = case.data[:case.contents_start] + payload + case.data[case.contents_end:]
    data = data[:left] + b"%010d" % (length_bytes * 2) + data[left + 10:]
    if delta > 0:
        with pytest.raises(SignatureFormatError) as error:
            parse_completed_signature(data, 1)
        assert error.value.code == "metadata.signature_size"
    else:
        # Synthetic signatures exercise metadata only; native crypto is tested
        # independently with real signatures below and in the Phase 1 suite.
        assert parse_completed_signature(data, 1).signature_length == length_bytes * 2


def test_shortened_length_cannot_reclassify_signature_as_padding(completed_case):
    length = parse_completed_signature(completed_case.data, completed_case.sign_type).signature_length
    data = set_length(completed_case, length - 2)
    with pytest.raises(SignatureFormatError) as error:
        parse_completed_signature(data, completed_case.sign_type)
    expected = "metadata.signature_size" if completed_case.sign_type == 0 else "contents.padding"
    assert error.value.code == expected


@pytest.mark.parametrize("token", [
    b"-000000001", b"+000000128", b"128", b"0" * 11,
    b"00000128.0", b"00000 0128", b"0000000128 ", b"000000012\x00",
], ids=["negative", "positive-sign", "short", "long", "decimal-point", "embedded-space", "trailing-space", "nul"])
def test_siglength_requires_exact_unsigned_decimal_syntax(completed_case, token):
    case = completed_case
    left = case.data.index(b"SigLength: ") + len(b"SigLength: ")
    data = case.data[:left] + token + case.data[left + 10:]
    with pytest.raises(SignatureFormatError) as error:
        parse_completed_signature(data, case.sign_type)
    assert error.value.code == "metadata.placement"


@pytest.mark.parametrize("position", ["first", "middle", "last"])
def test_uppercase_signature_is_rejected_without_normalization(completed_case, position):
    case = completed_case
    length = parse_completed_signature(case.data, case.sign_type).signature_length
    offsets = {"first": 0, "middle": length // 2, "last": length - 1}
    at = case.contents_start + offsets[position]
    # Synthetic controls use only a/b, so every position has a case mutation.
    changed = case.data[:at] + case.data[at:at + 1].upper() + case.data[at + 1:]
    assert changed != case.data
    with pytest.raises(SignatureFormatError) as error:
        extract_signature_hex_from_pdf(changed, case.sign_type)
    assert error.value.code == "contents.case"


@pytest.mark.parametrize("value", [b"g", b" ", b"\t", b"\r", b"\x00", b"\xff"])
def test_invalid_signature_characters_are_rejected(completed_case, value):
    case = completed_case
    data = case.data[:case.contents_start] + value + case.data[case.contents_start + 1:]
    with pytest.raises(SignatureFormatError) as error:
        parse_completed_signature(data, case.sign_type)
    assert error.value.code == "contents.syntax"


@pytest.mark.parametrize("position", ["first", "middle", "last"])
@pytest.mark.parametrize("value", [b"1", b"a", b"A", b" ", b"\x00", b"\xff"])
def test_unused_capacity_requires_ascii_zero_at_all_boundaries(completed_case, position, value):
    case = completed_case
    parsed = parse_completed_signature(case.data, case.sign_type)
    start = parsed.contents_start + parsed.signature_length
    offsets = {"first": start, "middle": (start + parsed.contents_end) // 2, "last": parsed.contents_end - 1}
    at = offsets[position]
    assert case.data[at:at + 1] == b"0"
    changed = case.data[:at] + value + case.data[at + 1:]
    with pytest.raises(SignatureFormatError) as error:
        parse_completed_signature(changed, case.sign_type)
    expected = "contents.padding" if value in (b"1", b"a", b"A") else "contents.syntax"
    assert error.value.code == expected


@pytest.mark.parametrize("mutation,expected", [
    ("tab-after-colon", "metadata.placement"),
    ("crlf-length", "metadata.placement"),
    ("extra-metadata", "metadata.placement"),
    ("space-before-signature", "contents.syntax"),
    ("space-before-close", "contents.syntax"),
    ("crlf-close", "contents.syntax"),
])
def test_noncanonical_metadata_inside_the_gap_is_rejected(completed_case, mutation, expected):
    case = completed_case
    if mutation == "tab-after-colon":
        changed = case.data.replace(b"SigLength: ", b"SigLength:\t", 1)
    elif mutation == "crlf-length":
        at = case.data.index(b"\n", case.gap_start)
        changed = case.data[:at] + b"\r\n" + case.data[at + 1:]
    elif mutation == "extra-metadata":
        changed = case.data[:case.gap_start] + b"Algorithm: other\n" + case.data[case.gap_start:]
    elif mutation == "space-before-signature":
        changed = case.data[:case.contents_start] + b" " + case.data[case.contents_start + 1:]
    elif mutation == "space-before-close":
        changed = case.data[:case.contents_end - 1] + b" " + case.data[case.contents_end:]
    else:
        changed = case.data[:case.contents_end] + b">\r\n" + case.data[case.gap_end:]
    with pytest.raises(SignatureFormatError) as error:
        parse_completed_signature(changed, case.sign_type)
    assert error.value.code == expected


@pytest.mark.parametrize("position", ["first", "middle", "last"])
def test_real_hybrid_rejects_falcon_padding_mutations(signed_pdf, keys, position):
    original = signed_pdf.read_bytes()
    falcon = parse_completed_signature(original, 1)
    ed = parse_completed_signature(original, 0)
    start = falcon.contents_start + falcon.signature_length
    offsets = {"first": start, "middle": (start + falcon.contents_end) // 2, "last": falcon.contents_end - 1}
    at = offsets[position]
    changed = original[:at] + b"1" + original[at + 1:]
    assert compute_sha512_digest_for_byte_range(original, ed.byte_range) == compute_sha512_digest_for_byte_range(changed, ed.byte_range)
    assert compute_shake256_digest_for_byte_range(original, falcon.byte_range) == compute_shake256_digest_for_byte_range(changed, falcon.byte_range)
    signed_pdf.write_bytes(changed)
    result = verify_file(signed_pdf, keys.pk_ed, keys.pk_falcon)
    assert len(result) == 11 and result[0] is False
    assert signed_pdf.read_bytes() == changed  # Verification must not repair bytes.


def test_every_unused_falcon_padding_position_is_checked(signed_pdf):
    original = signed_pdf.read_bytes()
    parsed = parse_completed_signature(original, 1)
    start = parsed.contents_start + parsed.signature_length
    assert start < parsed.contents_end
    for at in range(start, parsed.contents_end):
        changed = original[:at] + b"1" + original[at + 1:]
        with pytest.raises(SignatureFormatError) as error:
            parse_completed_signature(changed, 1)
        assert error.value.code == "contents.padding", at - start


@pytest.mark.parametrize("mutation,expected", [
    ("uppercase-signature", "contents.case"),
    ("length-tab", "metadata.placement"),
    ("zero-length", "metadata.length"),
    ("negative-length", "metadata.placement"),
    ("odd-length", "metadata.length"),
    ("nul-padding", "contents.syntax"),
])
def test_real_falcon_metadata_is_rejected_without_rewriting(signed_pdf, keys, mutation, expected):
    original = signed_pdf.read_bytes()
    assert verify_file(signed_pdf, keys.pk_ed, keys.pk_falcon)[0] is True
    parsed = parse_completed_signature(original, 1)
    signature_end = parsed.contents_start + parsed.signature_length
    signature_hex = original[parsed.contents_start:signature_end]
    signature = bytes.fromhex(signature_hex.decode("ascii"))
    left = original.index(b"SigLength: ", parsed.gap_start) + len(b"SigLength: ")
    if mutation == "uppercase-signature":
        changed = original[:parsed.contents_start] + signature_hex.upper() + original[signature_end:]
    elif mutation == "length-tab":
        changed = original[:left - 1] + b"\t" + original[left:]
    elif mutation == "nul-padding":
        changed = original[:signature_end] + b"\x00" + original[signature_end + 1:]
    else:
        token = {
            "zero-length": b"0000000000",
            "negative-length": b"-000000001",
            "odd-length": b"%010d" % (parsed.signature_length + 1),
        }[mutation]
        changed = original[:left] + token + original[left + 10:]
    assert changed != original and len(changed) == len(original)
    digest = compute_shake256_digest_for_byte_range(changed, parsed.byte_range)
    assert digest == compute_shake256_digest_for_byte_range(original, parsed.byte_range)
    assert falcon_512.verify(keys.pk_falcon.read_bytes(), digest, signature) is True
    with pytest.raises(SignatureFormatError) as error:
        parse_completed_signature(changed, 1)
    assert error.value.code == expected
    signed_pdf.write_bytes(changed)
    result = verify_file(signed_pdf, keys.pk_ed, keys.pk_falcon)
    assert len(result) == 11 and result[0] is False
    assert signed_pdf.read_bytes() == changed


@pytest.mark.parametrize("delta", [-2, 2])
def test_real_falcon_declared_boundary_changes_are_rejected(signed_pdf, keys, delta):
    original = signed_pdf.read_bytes()
    parsed = parse_completed_signature(original, 1)
    left = original.index(b"SigLength: ", parsed.gap_start) + len(b"SigLength: ")
    count = parsed.signature_length + delta
    changed = original[:left] + b"%010d" % count + original[left + 10:]
    a, b, c, d = parsed.byte_range
    signature = bytes.fromhex(changed[parsed.contents_start:parsed.contents_start + count].decode("ascii"))
    digest = compute_shake256_digest_for_byte_range(changed, (a, b, c, d))
    assert falcon_512.verify(keys.pk_falcon.read_bytes(), digest, signature) is False
    signed_pdf.write_bytes(changed)
    result = verify_file(signed_pdf, keys.pk_ed, keys.pk_falcon)
    assert len(result) == 11 and result[0] is False
    assert signed_pdf.read_bytes() == changed


@pytest.mark.parametrize("capacities", [(64, falcon_512.SIGNATURE_SIZE), (80, 1024), (256, 4096)],
                         ids=["minimum-ed-and-falcon-max", "smaller-custom", "larger-custom"])
def test_real_custom_capacity_hybrid_roundtrips(pdf_path, tmp_path, keys, capacities):
    from nacl.signing import SigningKey

    output = tmp_path / "custom.pdf"
    prepare_file_with_placeholder(pdf_path, output, capacities[0], 0)
    data = output.read_bytes()
    ed = parse_prepared_placeholder(data, 0)
    message = compute_sha512_digest_for_byte_range(data, ed.byte_range)
    signature = SigningKey(keys.sk_ed.read_bytes()).sign(message).signature
    assert len(signature) == crypto_sign_BYTES
    output.write_bytes(embed_signature_into_pdf(data, signature, 0))

    prepare_file_with_placeholder(output, output, capacities[1], 1)
    data = output.read_bytes()
    falcon = parse_prepared_placeholder(data, 1)
    digest = compute_shake256_digest_for_byte_range(data, falcon.byte_range)
    signature = falcon_512.sign(keys.sk_falcon.read_bytes(), digest)
    output.write_bytes(embed_signature_into_pdf(data, signature, 1))
    completed = output.read_bytes()
    assert parse_completed_signature(completed, 0).capacity_bytes == capacities[0]
    assert parse_completed_signature(completed, 1).capacity_bytes == capacities[1]
    assert verify_file(output, keys.pk_ed, keys.pk_falcon)[0] is True
