import hashlib 
import re 
from dataclasses import dataclass
from typing import Tuple, List

from nacl.bindings import crypto_sign_BYTES
from pqcrypto.sign import falcon_512

SIG_MARKER_START = [b"%%ED25519_PQ_SIG_START\n", b"%%FALCON_PQ_SIG_START\n"]
SIG_MARKER_END = [b"%%ED25519_PQ_SIG_END\n", b"%%FALCON_PQ_SIG_END\n"]

BYTE_RANGE_TEMPLATE = b"ByteRange: [ %010d %010d %010d %010d ]\n"
ZERO_BYTE_RANGE = BYTE_RANGE_TEMPLATE % (0, 0, 0, 0)
SIG_LEN=b"SigLength: %010d"
SIG_LEN_SUFFIX = b"\n"
SIG_LENGTH_REGEX = re.compile(rb"SigLength:\s*(\d{1,20})")
CONTENTS_PREFIX = b"Contents: <"
CONTENTS_SUFFIX = b">\n"
DEFAULT_SIGNATURE_CAPACITIES = (128, 2048)

_BYTE_RANGE_REGEX = re.compile(
    rb"ByteRange: \[ ([0-9]{10}) ([0-9]{10}) ([0-9]{10}) ([0-9]{10}) \]\n"
)
_SIG_LENGTH_LINE_REGEX = re.compile(rb"SigLength: ([0-9]{10})\n")
_HEX_CONTENTS_REGEX = re.compile(rb"[0-9a-fA-F]+")
_LOWERCASE_SIGNATURE_REGEX = re.compile(rb"[0-9a-f]+")


class SignatureFormatError(ValueError):
    """An invalid local container, with a stable structural error code."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class SignatureContainer:
    sign_type: int
    marker_start: int
    marker_end: int
    byte_range: Tuple[int, int, int, int]
    gap_start: int
    gap_end: int
    contents_start: int
    contents_end: int
    signature_length: int

    @property
    def capacity_bytes(self) -> int:
        return (self.contents_end - self.contents_start) // 2


def _container_bounds(pdf_bytes: bytes, sign_type: int, index: int) -> Tuple[int, int]:
    if type(sign_type) is not int or sign_type not in (0, 1):
        raise SignatureFormatError("container.type", "Unsupported signature type")
    if type(index) is not int:
        raise SignatureFormatError("container.index", "Signature index must be an integer")

    containers = []
    pos = 0
    while True:
        start = pdf_bytes.find(SIG_MARKER_START[sign_type], pos)
        if start == -1:
            break
        body_start = start + len(SIG_MARKER_START[sign_type])
        end = pdf_bytes.find(SIG_MARKER_END[sign_type], body_start)
        if end == -1:
            raise SignatureFormatError("container.boundary", "Missing signature end marker")
        # A missing end may not be borrowed from a later container of either
        # algorithm. This is local framing, not a global single-pair policy.
        for marker in SIG_MARKER_START + SIG_MARKER_END:
            if pdf_bytes.find(marker, body_start, end) != -1:
                raise SignatureFormatError("container.boundary", "Another marker interrupts the container")
        end += len(SIG_MARKER_END[sign_type])
        containers.append((start, end))
        pos = end

    if not containers:
        raise SignatureFormatError("container.missing", "No signature container found")
    if not -len(containers) <= index < len(containers):
        raise SignatureFormatError("container.index", "Signature index out of bounds")
    return containers[index]


def _validate_byte_range(container: SignatureContainer, file_length: int) -> None:
    first, first_length, second, second_length = container.byte_range
    for offset, length in ((first, first_length), (second, second_length)):
        if offset > file_length or length > file_length - offset:
            raise SignatureFormatError("byte_range.bounds", "Declared interval is outside the file")
    if first_length == 0 or second_length == 0:
        raise SignatureFormatError("byte_range.empty", "Both covered intervals must be nonempty")
    if first != 0:
        raise SignatureFormatError("byte_range.start", "Coverage must start at byte zero")
    if first + first_length > second:
        raise SignatureFormatError("byte_range.overlap", "Covered intervals overlap")
    if first + first_length != container.gap_start or second != container.gap_end:
        raise SignatureFormatError("byte_range.gap", "Excluded interval does not match this signature gap")
    if second + second_length != container.marker_end:
        raise SignatureFormatError("byte_range.coverage", "Coverage must end at this container's boundary")


def parse_signature_container(pdf_bytes: bytes, sign_type: int = 0, index: int = -1) -> SignatureContainer:
    """Parse bounded layout and ByteRange, without treating placeholders as signatures.

    Both prepared and completed states share this layout. Capacity is derived
    from Contents; global pairing, marker collisions and zero padding are not
    policies enforced by this local parser.
    """
    start, end = _container_bounds(pdf_bytes, sign_type, index)
    body_start = start + len(SIG_MARKER_START[sign_type])
    body_end = end - len(SIG_MARKER_END[sign_type])
    byte_range_match = _BYTE_RANGE_REGEX.match(pdf_bytes, body_start, body_end)
    if byte_range_match is None:
        raise SignatureFormatError("byte_range.syntax", "Expected four fixed-width unsigned decimal fields")
    gap_start = byte_range_match.end()
    length_match = _SIG_LENGTH_LINE_REGEX.match(pdf_bytes, gap_start, body_end)
    if length_match is None:
        raise SignatureFormatError("metadata.placement", "SigLength must immediately follow ByteRange")
    prefix_start = length_match.end()
    if not pdf_bytes.startswith(CONTENTS_PREFIX, prefix_start, body_end):
        raise SignatureFormatError("metadata.placement", "Contents must immediately follow SigLength")
    contents_start = prefix_start + len(CONTENTS_PREFIX)
    contents_end = body_end - len(CONTENTS_SUFFIX)
    if (contents_end < contents_start
            or pdf_bytes[contents_end:body_end] != CONTENTS_SUFFIX):
        raise SignatureFormatError("contents.syntax", "Contents must close immediately before its end marker")
    if ((contents_end - contents_start) % 2
            or _HEX_CONTENTS_REGEX.fullmatch(pdf_bytes, contents_start, contents_end) is None):
        raise SignatureFormatError("contents.syntax", "Contents must be an even, nonempty hexadecimal field")
    container = SignatureContainer(
        sign_type, start, end, tuple(int(value) for value in byte_range_match.groups()),
        gap_start, body_end, contents_start, contents_end, int(length_match.group(1)),
    )
    _validate_byte_range(container, len(pdf_bytes))
    return container


def parse_prepared_placeholder(pdf_bytes: bytes, sign_type: int = 0, index: int = -1) -> SignatureContainer:
    """Validate the writer's temporary state: length is capacity in bytes."""
    container = parse_signature_container(pdf_bytes, sign_type, index)
    payload = pdf_bytes[container.contents_start:container.contents_end]
    if container.signature_length != container.capacity_bytes or payload.strip(b"0"):
        raise SignatureFormatError("placeholder.state", "Expected an unfilled placeholder and byte capacity")
    return container


def parse_completed_signature(pdf_bytes: bytes, sign_type: int = 0, index: int = -1) -> SignatureContainer:
    """Validate completed metadata and canonical Contents on the original bytes.

    Falcon signatures are variable-length: the binding provides an upper bound,
    while native verification checks the actual encoding and cryptographic
    validity. Prepared placeholders use their separate parsing path.
    """
    container = parse_signature_container(pdf_bytes, sign_type, index)
    if (container.signature_length <= 0 or container.signature_length % 2
            or container.signature_length > container.contents_end - container.contents_start):
        raise SignatureFormatError("metadata.length", "Signature hex length is outside its Contents field")
    if container.sign_type == 0:
        if container.signature_length != crypto_sign_BYTES * 2:
            raise SignatureFormatError("metadata.signature_size", "Ed25519 requires exactly 128 signature hex characters")
    elif container.signature_length // 2 > falcon_512.SIGNATURE_SIZE:
        raise SignatureFormatError("metadata.signature_size", "Falcon signature exceeds the installed implementation's maximum")

    signature_end = container.contents_start + container.signature_length
    if _LOWERCASE_SIGNATURE_REGEX.fullmatch(pdf_bytes, container.contents_start, signature_end) is None:
        raise SignatureFormatError("contents.case", "Signature hex must be lowercase ASCII")
    padding_length = container.contents_end - signature_end
    if pdf_bytes.count(b"0", signature_end, container.contents_end) != padding_length:
        raise SignatureFormatError("contents.padding", "Unused Contents capacity must contain only ASCII zero padding")
    return container


def prepare_file_with_placeholder(input_path: str, output_path: str, placeholder_len: int = DEFAULT_SIGNATURE_CAPACITIES[0], type_sign : int = 0) -> None:
    with open(input_path, "rb") as f:
        original = f.read()
    
    hex_placeholder = b"0" * (placeholder_len*2)

    container = (
        SIG_MARKER_START[type_sign] +
        ZERO_BYTE_RANGE + 
        SIG_LEN % placeholder_len +
        SIG_LEN_SUFFIX +
        CONTENTS_PREFIX +
        hex_placeholder +
        CONTENTS_SUFFIX +
        SIG_MARKER_END[type_sign]
    )

    combined = original + container

    start1 = 0
    len1 = combined.rfind(SIG_LEN[:10])
    start2 = combined.find(CONTENTS_PREFIX, len1) + len(CONTENTS_PREFIX) + placeholder_len*2 + len(CONTENTS_SUFFIX)
    len2 = len(combined) - start2

    byte_range = BYTE_RANGE_TEMPLATE % (start1, len1, start2, len2)

    patched = combined.replace(ZERO_BYTE_RANGE, byte_range, 1)

    with open(output_path, "wb") as f:
        f.write(patched)
    

def extract_byte_range_and_placeholder(pdf_bytes: bytes, sign_type: int = 0, index: int = -1) -> Tuple[List[int], int, int]:
    container = parse_signature_container(pdf_bytes, sign_type, index)
    return list(container.byte_range), container.marker_start, container.marker_end

def compute_sha512_digest_for_byte_range(pdf_bytes: bytes, byte_range: List[int]) -> bytes:
    offset1, length1, offset2, length2 = byte_range
    
    part1 = pdf_bytes[offset1: offset1 + length1]
    part2 = pdf_bytes[offset2: offset2 + length2]

    message = part1+part2
    return message

def compute_shake256_digest_for_byte_range(pdf_bytes: bytes, byte_range: List[int], digest_len = 64) -> bytes:
    offset1, length1, offset2, length2 = byte_range
    
    part1 = pdf_bytes[offset1: offset1 + length1]
    part2 = pdf_bytes[offset2: offset2 + length2]

    message = part1+part2+pdf_bytes[offset2+length2:]
    shake = hashlib.shake_256(message)
    return shake.digest(digest_len)

def embed_signature_into_pdf(pdf_bytes: bytes, signature: bytes,sign_type: int = 0 ,index: int = -1) -> bytes:
    _, maker_start, maker_end = extract_byte_range_and_placeholder(pdf_bytes, sign_type, index)
    
    contents_start = pdf_bytes.find(CONTENTS_PREFIX, maker_start, maker_end)
    contents_end = pdf_bytes.find(CONTENTS_SUFFIX, contents_start, maker_end)

    hex_len= contents_end-(contents_start + len(CONTENTS_PREFIX))

    sig_hex = signature.hex().encode()

    padded_sig = sig_hex + b"0" * (hex_len - len(sig_hex))

    pdf_bytes = (
        pdf_bytes[:contents_start+len(CONTENTS_PREFIX)] +
        padded_sig +
        pdf_bytes[contents_end:]
    )

    sig_len_str = SIG_LEN % len(sig_hex)

    template = SIG_LENGTH_REGEX.search(pdf_bytes, maker_start, maker_end)
    if template:
        start = template.start()
        end = template.end()

        pdf_bytes = (
            pdf_bytes[:start] +
            sig_len_str +
            pdf_bytes[end:]
        )
    
    return pdf_bytes

def extract_signature_hex_from_pdf(pdf_bytes: bytes, sign_type: int = 0 ,index: int = -1) -> bytes:
    container = parse_completed_signature(pdf_bytes, sign_type, index)
    return pdf_bytes[container.contents_start:container.contents_start + container.signature_length]
