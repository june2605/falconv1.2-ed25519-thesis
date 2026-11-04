import hashlib 
import re 
from dataclasses import dataclass
from typing import Tuple, List

from nacl.bindings import crypto_sign_BYTES
from pqcrypto.sign import falcon_512

SIG_MARKER_START = [b"%%ED25519_PQ_SIG_START\n", b"%%FALCON_PQ_SIG_START\n"]
SIG_MARKER_END = [b"%%ED25519_PQ_SIG_END\n", b"%%FALCON_PQ_SIG_END\n"]
# Reserve the complete marker names even without LF, including names embedded
# in PDF content. This is deliberately stricter than local container parsing.
RESERVED_SIGNATURE_MARKERS = tuple(marker[:-1] for marker in SIG_MARKER_START + SIG_MARKER_END)

BYTE_RANGE_TEMPLATE = b"ByteRange: [ %010d %010d %010d %010d ]\n"
ZERO_BYTE_RANGE = BYTE_RANGE_TEMPLATE % (0, 0, 0, 0)
SIG_LEN=b"SigLength: %010d"
SIG_LEN_SUFFIX = b"\n"
SIG_LENGTH_REGEX = re.compile(rb"SigLength:\s*(\d{1,20})")
CONTENTS_PREFIX = b"Contents: <"
CONTENTS_SUFFIX = b">\n"
DEFAULT_SIGNATURE_CAPACITIES = (128, 2048)
MAX_DECIMAL_VALUE = 9999999999

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


@dataclass(frozen=True)
class SignaturePair:
    ed25519: SignatureContainer
    falcon: SignatureContainer


def validate_unsigned_input(pdf_bytes: bytes) -> None:
    """Reject signing any reserved marker name, regardless of its PDF meaning."""
    if any(marker in pdf_bytes for marker in RESERVED_SIGNATURE_MARKERS):
        raise SignatureFormatError("input.reserved_marker", "Input is already signed or contains a reserved signature marker")


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


def parse_signature_pair(pdf_bytes: bytes) -> SignaturePair:
    """Validate exactly one completed Ed25519 -> Falcon pair ending at EOF.

    Local parsers remain available for prepared/intermediate revisions. Only
    this whole-file validator enforces global marker cardinality and pairing.
    It does not normalize input or decide cryptographic signature validity.
    """
    if any(pdf_bytes.count(marker) != 1 for marker in RESERVED_SIGNATURE_MARKERS):
        raise SignatureFormatError("pair.markers", "Expected exactly one occurrence of each reserved marker name")
    ed25519 = parse_completed_signature(pdf_bytes, 0, 0)
    falcon = parse_completed_signature(pdf_bytes, 1, 0)
    if ed25519.marker_start >= falcon.marker_start:
        raise SignatureFormatError("pair.order", "Ed25519 must precede Falcon")
    if ed25519.marker_end != falcon.marker_start:
        raise SignatureFormatError("pair.adjacency", "Falcon must immediately follow the Ed25519 container")
    if falcon.marker_end != len(pdf_bytes):
        raise SignatureFormatError("pair.trailing", "No bytes may follow the final Falcon container")
    # Local ByteRanges already end at their own containers and start at zero.
    # Adjacency therefore places the complete Ed25519 container in Falcon's
    # first covered interval, and keeps the Ed25519 revision boundary intact.
    return SignaturePair(ed25519, falcon)


def _validate_placeholder_arguments(placeholder_len: int, type_sign: int) -> None:
    if type(type_sign) is not int or type_sign not in (0, 1):
        raise SignatureFormatError("container.type", "Unsupported signature type")
    if (type(placeholder_len) is not int or placeholder_len <= 0
            or placeholder_len > MAX_DECIMAL_VALUE // 2):
        raise SignatureFormatError("placeholder.capacity", "Capacity must be positive integer bytes within the wire bounds")
    if type_sign == 0 and placeholder_len < crypto_sign_BYTES:
        raise SignatureFormatError("placeholder.capacity", "Ed25519 capacity must fit its 64-byte signature")


def prepare_bytes_with_placeholder(original: bytes, placeholder_len: int = DEFAULT_SIGNATURE_CAPACITIES[0], type_sign: int = 0) -> bytes:
    """Append a trailer using known offsets; never search or patch source bytes."""
    _validate_placeholder_arguments(placeholder_len, type_sign)
    if not isinstance(original, bytes):
        raise SignatureFormatError("input.type", "Captured source must be immutable bytes")
    if any(marker[:-1] in original for marker in (SIG_MARKER_START[type_sign], SIG_MARKER_END[type_sign])):
        raise SignatureFormatError("placeholder.marker", "Source already contains the target signature marker")

    length_line = SIG_LEN % placeholder_len + SIG_LEN_SUFFIX
    gap_start = len(original) + len(SIG_MARKER_START[type_sign]) + len(ZERO_BYTE_RANGE)
    gap_end = gap_start + len(length_line) + len(CONTENTS_PREFIX) + placeholder_len * 2 + len(CONTENTS_SUFFIX)
    byte_range = (0, gap_start, gap_end, len(SIG_MARKER_END[type_sign]))
    if any(value > MAX_DECIMAL_VALUE for value in byte_range):
        raise SignatureFormatError("placeholder.capacity", "Predicted ByteRange exceeds its fixed-width fields")

    container = (
        SIG_MARKER_START[type_sign] + BYTE_RANGE_TEMPLATE % byte_range
        + length_line + CONTENTS_PREFIX + b"0" * (placeholder_len * 2)
        + CONTENTS_SUFFIX + SIG_MARKER_END[type_sign]
    )
    return original + container


def prepare_file_with_placeholder(input_path: str, output_path: str, placeholder_len: int = DEFAULT_SIGNATURE_CAPACITIES[0], type_sign : int = 0) -> None:
    """Legacy file wrapper; intentional in-place preparation remains supported.

    Identical input/output arguments explicitly request the legacy in-place
    operation. Hidden aliases through distinct paths are rejected. Construction
    finishes before opening output, but write failures are not atomic.
    """
    from signing_io import capture_source, validate_signing_paths

    _validate_placeholder_arguments(placeholder_len, type_sign)
    snapshot = capture_source(input_path)
    destination = snapshot.path if input_path == output_path else validate_signing_paths(snapshot, output_path)
    prepared = prepare_bytes_with_placeholder(snapshot.data, placeholder_len, type_sign)
    with open(destination, "wb") as f:
        f.write(prepared)
    

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
    container = parse_signature_container(pdf_bytes, sign_type, index)
    if not isinstance(signature, (bytes, bytearray, memoryview)):
        raise SignatureFormatError("signature.type", "Signature must be bytes-like")
    signature = bytes(signature)
    if (sign_type == 0 and len(signature) != crypto_sign_BYTES
            or sign_type == 1 and not 0 < len(signature) <= falcon_512.SIGNATURE_SIZE):
        raise SignatureFormatError("signature.size", "Signature size is invalid for the selected algorithm")
    hex_len = len(signature) * 2
    if hex_len > MAX_DECIMAL_VALUE or hex_len > container.contents_end - container.contents_start:
        raise SignatureFormatError("signature.capacity", "Signature does not fit its fixed-width Contents capacity")

    gap = (
        SIG_LEN % hex_len + SIG_LEN_SUFFIX + CONTENTS_PREFIX
        + signature.hex().encode("ascii")
        + b"0" * (container.contents_end - container.contents_start - hex_len)
        + CONTENTS_SUFFIX
    )
    embedded = pdf_bytes[:container.gap_start] + gap + pdf_bytes[container.gap_end:]
    if len(embedded) != len(pdf_bytes):
        raise SignatureFormatError("signature.layout", "Embedding must preserve exact file length")
    completed = parse_completed_signature(embedded, sign_type, index)
    if (completed.byte_range != container.byte_range
            or (completed.marker_start, completed.marker_end) != (container.marker_start, container.marker_end)):
        raise SignatureFormatError("signature.layout", "Embedding changed container offsets")
    return embedded

def extract_signature_hex_from_pdf(pdf_bytes: bytes, sign_type: int = 0 ,index: int = -1) -> bytes:
    container = parse_completed_signature(pdf_bytes, sign_type, index)
    return pdf_bytes[container.contents_start:container.contents_start + container.signature_length]
