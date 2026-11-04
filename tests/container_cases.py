"""Test-only container construction, independent of production parsing/writing."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ContainerCase:
    data: bytes
    sign_type: int
    start: int
    end: int
    gap_start: int
    gap_end: int
    byte_range_start: int
    contents_start: int
    contents_end: int
    byte_range: tuple[int, int, int, int]


def make_container(sign_type, prefix=b"%PDF-1.4\n% synthetic parser control\n", capacity=None):
    start_marker, end_marker = (
        (b"%%ED25519_PQ_SIG_START\n", b"%%ED25519_PQ_SIG_END\n"),
        (b"%%FALCON_PQ_SIG_START\n", b"%%FALCON_PQ_SIG_END\n"),
    )[sign_type]
    capacity = (128, 2048)[sign_type] if capacity is None else capacity
    template = b"ByteRange: [ %010d %010d %010d %010d ]\n"
    # Plausible final signature lengths; cryptographic validity is tested in
    # integration cases. All other control-container fields are well-formed.
    signature = b"ab" * (64 if sign_type == 0 else 650)
    metadata = b"SigLength: %010d\nContents: <" % len(signature)
    payload = signature + b"0" * (capacity * 2 - len(signature))
    start = len(prefix)
    byte_range_start = start + len(start_marker)
    gap_start = byte_range_start + len(template % (0, 0, 0, 0))
    contents_start = gap_start + len(metadata)
    contents_end = contents_start + len(payload)
    gap_end = contents_end + len(b">\n")
    byte_range = (0, gap_start, gap_end, len(end_marker))
    data = prefix + start_marker + template % byte_range + metadata + payload + b">\n" + end_marker
    return ContainerCase(data, sign_type, start, len(data), gap_start, gap_end,
                         byte_range_start, contents_start, contents_end, byte_range)


def replace_range(case, values):
    """Change only the fixed-width ByteRange field in a valid control."""
    line_end = case.data.index(b"\n", case.byte_range_start) + 1
    replacement = b"ByteRange: [ %010d %010d %010d %010d ]\n" % tuple(values)
    return case.data[:case.byte_range_start] + replacement + case.data[line_end:]
