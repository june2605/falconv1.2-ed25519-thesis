"""Local framing, exact coverage and prepared/final metadata boundaries."""

import base64
import json
from pathlib import Path

import pytest

from container_cases import make_container, replace_range
from sign import sign_file
from utils import (
    DEFAULT_SIGNATURE_CAPACITIES,
    SignatureFormatError,
    embed_signature_into_pdf,
    extract_byte_range_and_placeholder,
    extract_signature_hex_from_pdf,
    parse_completed_signature,
    parse_prepared_placeholder,
    parse_signature_container,
    prepare_file_with_placeholder,
)
from verify import verify_file


@pytest.fixture(params=[0, 1], ids=["ed25519", "falcon"])
def container_case(request):
    case = make_container(request.param)
    # Every malformed-input test begins with a known structurally valid control.
    parsed = parse_completed_signature(case.data, case.sign_type)
    assert parsed.byte_range == case.byte_range
    assert parsed.marker_start == case.start and parsed.marker_end == case.end
    return case


@pytest.mark.parametrize("field", range(4), ids=["first-offset", "first-length", "second-offset", "second-length"])
@pytest.mark.parametrize("token", [b"-000000001", b"+000000001", b"00000000x1", b"1", b"9" * 5000],
                         ids=["negative", "positive-sign", "nondecimal", "short-field", "oversized-integer"])
def test_byte_range_requires_fixed_width_unsigned_decimal(container_case, field, token):
    case = container_case
    fields = [b"%010d" % value for value in case.byte_range]
    fields[field] = token
    line = b"ByteRange: [ " + b" ".join(fields) + b" ]\n"
    line_end = case.data.index(b"\n", case.byte_range_start) + 1
    data = case.data[:case.byte_range_start] + line + case.data[line_end:]
    with pytest.raises(SignatureFormatError) as error:
        parse_signature_container(data, case.sign_type)
    assert error.value.code == "byte_range.syntax"


@pytest.mark.parametrize("mutation", ["first-end-before-gap", "first-end-inside-gap", "second-inside-gap", "second-after-gap", "no-gap"])
def test_range_must_exclude_exactly_its_own_gap(container_case, mutation):
    case = container_case
    first, length, second, tail = case.byte_range
    ranges = {
        "first-end-before-gap": (first, length - 1, second, tail),
        "first-end-inside-gap": (first, length + 1, second, tail),
        "second-inside-gap": (first, length, second - 1, tail + 1),
        "second-after-gap": (first, length, second + 1, tail - 1),
        "no-gap": (first, length, length, case.end - length),
    }
    with pytest.raises(SignatureFormatError) as error:
        parse_signature_container(replace_range(case, ranges[mutation]), case.sign_type)
    assert error.value.code == "byte_range.gap"


@pytest.mark.parametrize("delta", [-1, 1])
def test_coverage_ends_at_selected_container_not_file_eof(container_case, delta):
    case = container_case
    first, length, second, tail = case.byte_range
    # A suffix makes both altered endpoints in bounds: only coverage is wrong.
    data = replace_range(case, (first, length, second, tail + delta)) + b"later revision bytes"
    with pytest.raises(SignatureFormatError) as error:
        parse_signature_container(data, case.sign_type)
    assert error.value.code == "byte_range.coverage"
    # Global EOF policy is deliberately deferred; local parsing stops at e.
    assert parse_signature_container(case.data + b"later revision bytes", case.sign_type).marker_end == case.end


@pytest.mark.parametrize("field", range(4))
def test_largest_encodable_integer_is_checked_against_file_bounds(container_case, field):
    values = list(container_case.byte_range)
    values[field] = 9999999999
    with pytest.raises(SignatureFormatError) as error:
        parse_signature_container(replace_range(container_case, values), container_case.sign_type)
    assert error.value.code == "byte_range.bounds"


@pytest.mark.parametrize("mutation,expected", [
    ("missing-length", "metadata.placement"),
    ("missing-contents", "metadata.placement"),
    ("duplicate-range", "metadata.placement"),
    ("duplicate-length", "metadata.placement"),
    ("moved-range", "byte_range.syntax"),
    ("unclosed-contents", "contents.syntax"),
    ("duplicate-contents", "contents.syntax"),
    ("nonhex-contents", "contents.syntax"),
    ("odd-contents", "contents.syntax"),
    ("field-after-contents", "contents.syntax"),
])
def test_fields_have_exact_positions_within_container(container_case, mutation, expected):
    case = container_case
    data = case.data
    if mutation == "missing-length":
        data = data.replace(b"SigLength:", b"NotLength:", 1)
    elif mutation == "missing-contents":
        data = data.replace(b"Contents: <", b"NoField!: <", 1)
    elif mutation == "duplicate-range":
        line = data[case.byte_range_start:case.gap_start]
        data = data[:case.gap_start] + line + data[case.gap_start:]
    elif mutation == "duplicate-length":
        data = data[:case.gap_start] + b"SigLength: 0000000128\n" + data[case.gap_start:]
    elif mutation == "moved-range":
        data = data[:case.byte_range_start] + b"\n" + data[case.byte_range_start:]
    elif mutation == "unclosed-contents":
        data = data[:case.contents_end] + b"!\n" + data[case.gap_end:]
    elif mutation == "duplicate-contents":
        data = data[:case.contents_start] + b"Contents: <" + data[case.contents_start:]
    elif mutation == "nonhex-contents":
        data = data[:case.contents_start] + b"z" + data[case.contents_start + 1:]
    elif mutation == "odd-contents":
        data = data[:case.contents_start] + data[case.contents_start + 1:]
    else:
        data = data[:case.gap_end] + b"SigLength: 0000000002\n" + data[case.gap_end:]
    with pytest.raises(SignatureFormatError) as error:
        extract_signature_hex_from_pdf(data, case.sign_type)
    assert error.value.code == expected


@pytest.mark.parametrize("next_type", [0, 1], ids=["next-ed25519", "next-falcon"])
def test_missing_end_cannot_borrow_a_later_container(container_case, next_type):
    case = container_case
    truncated = case.data[:case.gap_end]
    following = make_container(next_type, prefix=truncated)
    # Supply the missing end after the next complete container as well.
    own_end = case.data[case.gap_end:]
    data = following.data + own_end
    with pytest.raises(SignatureFormatError) as error:
        extract_signature_hex_from_pdf(data, case.sign_type, 0)
    assert error.value.code == "container.boundary"


@pytest.mark.parametrize("declared_length", [0, 1, 1000000])
def test_completed_signature_length_cannot_escape_contents(container_case, declared_length):
    case = container_case
    left = case.data.index(b"SigLength: ") + len(b"SigLength: ")
    data = case.data[:left] + b"%010d" % declared_length + case.data[left + 10:]
    following = make_container(1 - case.sign_type, prefix=data)
    with pytest.raises(SignatureFormatError) as error:
        extract_signature_hex_from_pdf(following.data, case.sign_type)
    assert error.value.code == "metadata.length"


@pytest.mark.parametrize("index", [-3, 2, True, 0.0])
def test_invalid_indices_raise_explicit_errors(container_case, index):
    case = container_case
    following = make_container(case.sign_type, prefix=case.data)
    with pytest.raises(SignatureFormatError) as error:
        parse_signature_container(following.data, case.sign_type, index)
    assert error.value.code == "container.index"


@pytest.mark.parametrize("sign_type", [-1, 2, True, "0"])
def test_unsupported_signature_types_raise_explicit_errors(sign_type):
    with pytest.raises(SignatureFormatError) as error:
        parse_signature_container(b"", sign_type)
    assert error.value.code == "container.type"


def test_multiple_containers_keep_local_index_selection(container_case):
    case = container_case
    following = make_container(case.sign_type, prefix=case.data)
    for index in (0, -2):
        assert extract_byte_range_and_placeholder(following.data, case.sign_type, index) == (
            list(case.byte_range), case.start, case.end,
        )
    for index in (1, -1):
        assert extract_byte_range_and_placeholder(following.data, case.sign_type, index) == (
            list(following.byte_range), following.start, following.end,
        )


@pytest.mark.parametrize("sign_type", [0, 1], ids=["ed25519", "falcon"])
@pytest.mark.parametrize("custom_capacity", [False, True], ids=["default-capacity", "custom-capacity"])
def test_prepared_and_completed_states_use_distinct_length_conventions(
    pdf_path, tmp_path, sign_type, custom_capacity,
):
    output = tmp_path / "placeholder.pdf"
    capacity = DEFAULT_SIGNATURE_CAPACITIES[sign_type] + (16 if custom_capacity else 0)
    prepare_file_with_placeholder(pdf_path, output, capacity, sign_type)
    data = output.read_bytes()
    prepared = parse_prepared_placeholder(data, sign_type)
    assert prepared.capacity_bytes == prepared.signature_length == capacity

    signature = b"\xab" * (64 if sign_type == 0 else 650)
    completed_bytes = embed_signature_into_pdf(data, signature, sign_type)
    completed = parse_completed_signature(completed_bytes, sign_type)
    assert completed.byte_range == prepared.byte_range
    assert completed.capacity_bytes == capacity
    assert completed.signature_length == len(signature) * 2
    assert extract_signature_hex_from_pdf(completed_bytes, sign_type) == signature.hex().encode()
    with pytest.raises(SignatureFormatError) as error:
        parse_prepared_placeholder(completed_bytes, sign_type)
    assert error.value.code == "placeholder.state"


_LEGACY_CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "phase1-signatures.json").read_text(encoding="utf-8")
)["cases"]


@pytest.mark.parametrize("case", _LEGACY_CASES, ids=lambda case: case["name"])
def test_frozen_phase1_single_pair_signatures_still_verify(case, tmp_path):
    pdf, pk_ed, pk_falcon = (tmp_path / name for name in ("legacy.pdf", "ed.key", "falcon.key"))
    pdf.write_bytes(base64.b64decode(case["pdf_base64"], validate=True))
    pk_ed.write_bytes(base64.b64decode(case["ed25519_public_base64"], validate=True))
    pk_falcon.write_bytes(base64.b64decode(case["falcon_public_base64"], validate=True))
    result = verify_file(pdf, pk_ed, pk_falcon)
    assert isinstance(result, tuple) and len(result) == 11 and result[0] is True


def test_repeated_hybrid_signing_is_rejected_by_phase2b3(signed_pdf, keys, tmp_path):
    # Intentional Phase 2B.3 policy change: the earlier phases allowed history.
    output = tmp_path / "signed-again.pdf"
    original = signed_pdf.read_bytes()
    with pytest.raises(SignatureFormatError) as error:
        sign_file(signed_pdf, output, keys.sk_ed, keys.sk_falcon, pk_falcon=keys.pk_falcon)
    assert error.value.code == "input.reserved_marker"
    assert not output.exists()
    assert signed_pdf.read_bytes() == original
