"""Desired validation rules that the inherited prototype does not yet satisfy."""

import hashlib
import re

import pytest
from pqcrypto.sign import falcon_512

from utils import (
    CONTENTS_PREFIX,
    SIG_LENGTH_REGEX,
    extract_byte_range_and_placeholder,
)
from verify import verify_file
from container_cases import make_container, replace_range


def test_modified_falcon_padding_must_be_rejected(signed_pdf, keys):
    data = signed_pdf.read_bytes()
    assert verify_file(signed_pdf, keys.pk_ed, keys.pk_falcon)[0] is True
    _, start, end = extract_byte_range_and_placeholder(data, 1)
    signature_length = int(SIG_LENGTH_REGEX.search(data, start, end).group(1))
    contents = data.index(CONTENTS_PREFIX, start, end) + len(CONTENTS_PREFIX)
    padding_start = contents + signature_length
    assert data[padding_start:padding_start + 1] == b"0"
    changed = data[:padding_start] + b"1" + data[padding_start + 1:]
    assert changed != data and len(changed) == len(data)
    signed_pdf.write_bytes(changed)
    assert verify_file(signed_pdf, keys.pk_ed, keys.pk_falcon)[0] is False


@pytest.mark.parametrize("sign_type", [0, 1], ids=["ed25519", "falcon"])
@pytest.mark.parametrize("malformed", ["out-of-bounds", "overlap", "nonzero-start", "empty-coverage"])
def test_malformed_byte_range_must_raise_value_error(sign_type, malformed):
    case = make_container(sign_type)
    assert extract_byte_range_and_placeholder(case.data, sign_type) == (
        list(case.byte_range), case.start, case.end,
    )
    ranges = {
        "out-of-bounds": (0, case.gap_start, case.end + 1000, 10),
        "overlap": (0, case.gap_start, case.gap_start - 1, 10),
        "nonzero-start": (1, case.gap_start - 1, case.gap_end, case.byte_range[3]),
        "empty-coverage": (0, 0, 0, 0),
    }
    expected = {
        "out-of-bounds": "byte_range.bounds",
        "overlap": "byte_range.overlap",
        "nonzero-start": "byte_range.start",
        "empty-coverage": "byte_range.empty",
    }
    with pytest.raises(ValueError) as error:
        extract_byte_range_and_placeholder(replace_range(case, ranges[malformed]), sign_type)
    assert error.value.code == expected[malformed]


def test_hybrid_must_reject_signed_out_of_bounds_falcon_range(signed_pdf, keys):
    data = signed_pdf.read_bytes()
    assert verify_file(signed_pdf, keys.pk_ed, keys.pk_falcon)[0] is True
    start = data.index(b"%%FALCON_PQ_SIG_START\n")
    end = data.index(b"%%FALCON_PQ_SIG_END\n", start)
    match = re.search(rb"ByteRange: \[ ([0-9]{10}) ([0-9]{10}) ([0-9]{10}) ([0-9]{10}) \]\n", data[start:end])
    assert match is not None
    byte_range = [int(group) for group in match.groups()]
    # An impossible second offset is signed with genuine test keys. The backend
    # must reject its structure independently of cryptographic validity.
    byte_range[2] = len(data) + 1000
    left, right = start + match.start(), start + match.end()
    data = data[:left] + b"ByteRange: [ %010d %010d %010d %010d ]\n" % tuple(byte_range) + data[right:]
    a, b, c, d = byte_range
    digest = hashlib.shake_256(data[a:a + b] + data[c:c + d] + data[c + d:]).digest(64)
    signature = falcon_512.sign(keys.sk_falcon.read_bytes(), digest)
    contents_start = data.index(b"Contents: <", start, end) + len(b"Contents: <")
    contents_end = data.index(b">\n", contents_start, end)
    payload = signature.hex().encode().ljust(contents_end - contents_start, b"0")
    assert len(payload) == contents_end - contents_start
    data = data[:contents_start] + payload + data[contents_end:]
    length = re.search(rb"SigLength: [0-9]{10}", data[start:end])
    assert length is not None
    left, right = start + length.start(), start + length.end()
    data = data[:left] + b"SigLength: %010d" % (len(signature) * 2) + data[right:]
    # Neither parsing, hashing nor embedding of this adversarial input uses
    # production helpers. Its genuine Falcon signature is a positive control.
    final_digest = hashlib.shake_256(data[a:a + b] + data[c:c + d] + data[c + d:]).digest(64)
    assert final_digest == digest
    assert falcon_512.verify(keys.pk_falcon.read_bytes(), final_digest, signature) is True
    assert data[:start] == signed_pdf.read_bytes()[:start]
    signed_pdf.write_bytes(data)
    with pytest.raises(ValueError) as error:
        extract_byte_range_and_placeholder(data, 1)
    assert error.value.code == "byte_range.bounds"
    result = verify_file(signed_pdf, keys.pk_ed, keys.pk_falcon)
    assert len(result) == 11 and result[0] is False
