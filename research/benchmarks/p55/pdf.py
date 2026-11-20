"""Research-only PDF comparators and public fixtures."""
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import re
import secrets

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey
from pqcrypto.sign import falcon_512

import sign
from keygen import generate_hybrid_key_pair
from signing_io import SigningPathError, SigningTransaction, capture_source, validate_signing_paths
import utils
import verify

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "demo_assets/sample-unsigned.pdf"
MIB = 1024**2
WORKLOADS = {
    "demo": (742, "2d94ba434bbbfda3ffcd78731f2e94146352e5dc7680dcd566d2ca0614a20639"),
    "1-MiB": (MIB, "568830f43d6be53c262a29d679ab97bb02afcd44418a839a10d26ece85ca6490"),
    "10-MiB": (10 * MIB, "34061f01468d32fa023756bfc0b225d703d31c2275a387cf68cc2139ad4cdec5"),
}
ED, FALCON, HYBRID = "Ed25519", "Falcon-512", "Hybrid"
METHODS = (ED, FALCON, HYBRID)
KINDS = {ED: 0, FALCON: 1}
TRAILER = re.compile(rb"startxref\n([0-9]+)\n%%EOF\n\Z")
NOT_EVALUATED = "NOT EVALUATED"
NOT_APPLICABLE = "NOT APPLICABLE"


class ResearchError(ValueError):
    """Stable public research failure code."""


def require(condition, code):
    if not condition:
        raise ResearchError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_fixture(data, size):
    require(len(data) == size and data.startswith(b"%PDF-1.4\n") and data.count(b"APPROVED") == 1,
            "fixture.header_size_or_text")
    utils.validate_unsigned_input(data)
    trailer = TRAILER.search(data)
    require(trailer is not None, "fixture.trailer")
    offset = int(trailer[1])
    entries = data[offset:trailer.start()].splitlines()
    require(entries[:3] == [b"xref", b"0 6", b"0000000000 65535 f "] and
            entries[8:] == [b"trailer", b"<< /Size 6 /Root 1 0 R >>"], "fixture.xref")
    for number, entry in enumerate(entries[3:8], 1):
        require(re.fullmatch(rb"[0-9]{10} 00000 n ", entry) is not None, "fixture.xref_entry")
        start = int(entry[:10])
        require(start < offset and data.startswith(f"{number} 0 obj\n".encode(), start), "fixture.object")
    streams = list(re.finditer(rb"/Length ([0-9]+) >>\nstream\n(.*?)endstream", data, re.DOTALL))
    require(len(streams) == 1 and len(streams[0][2]) == int(streams[0][1]), "fixture.stream")
    return trailer


def fixture(workload):
    """Port the approved deterministic builder without importing the Windows harness."""
    sample = SAMPLE.read_bytes()
    size, expected = WORKLOADS[workload]
    tail = validate_fixture(sample, WORKLOADS["demo"][0])
    data = sample
    if workload != "demo":
        old_offset = int(tail[1])
        for width in range(len(tail[1]), len(str(size)) + 1):
            padding = size - len(sample) - width + len(tail[1])
            new_offset = str(old_offset + padding).encode("ascii")
            if padding > 0 and len(new_offset) == width:
                break
        else:
            raise ResearchError("fixture.builder")
        blocks, remaining = divmod(padding, 72)
        comment = b"%" + b"p" * 70 + b"\n"
        end = b"%" + b"p" * (remaining - 2) + b"\n" if remaining >= 2 else b"\n" * remaining
        data = (sample[:old_offset] + comment * blocks + end + sample[old_offset:tail.start(1)] +
                new_offset + sample[tail.end(1):])
        validate_fixture(data, size)
    require(sha(data) == expected, "fixture.hash")
    return data


def primitive_input(size):
    label = f"HybridSign Phase 5.2A public message, {size} bytes".encode("ascii")
    return hashlib.shake_256(label).digest(size)


@dataclass(frozen=True)
class SingleKey:
    public: bytes
    private: bytes = field(repr=False)


def generate_single(method):
    if method == ED:
        key = SigningKey.generate()
        return SingleKey(bytes(key.verify_key), key.encode())
    if method == FALCON:
        return SingleKey(*falcon_512.generate_keypair())
    raise ResearchError("key.algorithm")


def algorithm_signer(method, key):
    if method == ED:
        signing_key = SigningKey(key.private)
        return lambda message: signing_key.sign(message).signature
    if method == FALCON:
        return lambda message: falcon_512.sign(key.private, message)
    raise ResearchError("key.algorithm")


def algorithm_verifier(method, public):
    if method == ED:
        require(type(public) is bytes and len(public) == 32, "key.size")
        key = VerifyKey(public)

        def check(message, signature):
            try:
                return key.verify(message, signature) == message
            except BadSignatureError:
                return False

        return check
    if method == FALCON:
        require(type(public) is bytes and len(public) == falcon_512.PUBLIC_KEY_SIZE, "key.size")
        return lambda message, signature: falcon_512.verify(public, message, signature) is True
    raise ResearchError("key.algorithm")


def valid_signature_size(method, signature):
    return type(signature) is bytes and (
        len(signature) == 64 if method == ED else 0 < len(signature) <= falcon_512.SIGNATURE_SIZE
    )


def bind_single_key(method, key):
    """Fresh, algorithm-specific correspondence and sign/verify self-test."""
    size = 32 if method == ED else falcon_512.SECRET_KEY_SIZE
    require(type(key) is SingleKey and type(key.private) is bytes and len(key.private) == size, "key.size")
    if method == ED:
        signing_key = SigningKey(key.private)
        require(bytes(signing_key.verify_key) == key.public, "key.correspondence")
        signer = lambda message: signing_key.sign(message).signature
    else:
        signer = algorithm_signer(method, key)
    check = algorithm_verifier(method, key.public)
    challenge = b"HybridSign research key validation v1\0" + method.encode() + b"\0" + key.public + secrets.token_bytes(32)
    signature = signer(challenge)
    require(valid_signature_size(method, signature) and check(challenge, signature), "key.self_test")
    return signer


def parse_single(data, method):
    kind = KINDS[method]
    expected = (utils.SIG_MARKER_START[kind][:-1], utils.SIG_MARKER_END[kind][:-1])
    if any(data.count(marker) != int(marker in expected) for marker in utils.RESERVED_SIGNATURE_MARKERS):
        raise utils.SignatureFormatError("single.markers", "Expected only the requested single container")
    container = utils.parse_completed_signature(data, kind, 0)
    if container.marker_end != len(data):
        raise utils.SignatureFormatError("single.trailing", "Container must end at EOF")
    return container


def message_for(data, container):
    if container.sign_type == 0:
        return utils.compute_sha512_digest_for_byte_range(data, container.byte_range)
    return utils.compute_shake256_digest_for_byte_range(data, container.byte_range)


def detached(data, container):
    return bytes.fromhex(data[container.contents_start:container.contents_start + container.signature_length].decode("ascii"))


def native_check(data, container, public):
    return algorithm_verifier(METHODS[container.sign_type], public)(
        message_for(data, container), detached(data, container))


def verify_single_bytes(data, method, public):
    try:
        container = parse_single(data, method)
    except utils.SignatureFormatError:
        return False
    return native_check(data, container, public)


def verify_single_file(path, method, public):
    return verify_single_bytes(Path(path).read_bytes(), method, public)


def sign_single_file(source, output, method, key):
    kind = KINDS[method]
    requested_source = Path(source).absolute()
    snapshot = capture_source(requested_source)
    utils.validate_unsigned_input(snapshot.data)
    requested_output = Path(output).absolute()
    protected = (requested_source,)
    destination = validate_signing_paths(snapshot, requested_output, protected_paths=protected)
    signer = bind_single_key(method, key)
    with SigningTransaction(destination) as transaction:
        transaction.write_stage("source.pdf", snapshot.data)
        prepared = utils.prepare_bytes_with_placeholder(snapshot.data, utils.DEFAULT_SIGNATURE_CAPACITIES[kind], kind)
        transaction.write_stage("prepared.pdf", prepared)
        container = utils.parse_prepared_placeholder(prepared, kind)
        completed = utils.embed_signature_into_pdf(prepared, signer(message_for(prepared, container)), kind)
        candidate = transaction.write_candidate(completed)
        require(verify_single_file(candidate, method, key.public) is True, "candidate.verify")
        transaction.mark_verified()
        transaction.cleanup_working()
        if validate_signing_paths(snapshot, requested_output, protected_paths=protected) != transaction.destination:
            raise SigningPathError("path.changed", "Destination resolved to a different path during signing")
        transaction.publish()
    return output


def to_single(pair, method):
    if method == ED:
        return SingleKey(pair.public_keys.ed25519_public_key, pair.ed25519_private_seed)
    if method == FALCON:
        return SingleKey(pair.public_keys.falcon_public_key, pair.falcon_private_key)
    raise ResearchError("key.algorithm")


def sign_document(source, destination, method, pair):
    if method == HYBRID:
        result = sign.sign_with_key_material(source, destination, pair)
        require(type(result) is tuple and len(result) == 11 and result[0] == destination, "hybrid.sign_contract")
        return result[0]
    return sign_single_file(source, destination, method, to_single(pair, method))


def hybrid_result(result):
    require(type(result) is tuple and len(result) == 11 and type(result[0]) is bool, "hybrid.verify_contract")
    return result[0]


def publics(pair):
    return pair.public_keys.ed25519_public_key, pair.public_keys.falcon_public_key


def verify_document(path, method, public):
    if method == HYBRID:
        return hybrid_result(verify.verify_file_with_public_keys(path, *public))
    return verify_single_file(path, method, public[KINDS[method]])


def covered_edit(data):
    require(data.count(b"APPROVED") == 1, "control.content_anchor")
    return data.replace(b"APPROVED", b"REJECTED", 1)


def assess(data, method, public):
    states = [NOT_APPLICABLE, NOT_APPLICABLE] if method != HYBRID else [NOT_EVALUATED] * 2
    if method != HYBRID:
        states[KINDS[method]] = NOT_EVALUATED
    try:
        if method == HYBRID:
            pair = utils.parse_signature_pair(data)
            containers = (pair.ed25519, pair.falcon)
        else:
            containers = (parse_single(data, method),)
    except utils.SignatureFormatError as error:
        structure = error.code
    else:
        structure = "valid"
        for container in containers:
            index = container.sign_type
            states[index] = native_check(data, container, public[index])
    overall = (hybrid_result(verify.verify_bytes(data, *public)) if method == HYBRID else
               (states[KINDS[method]] is True))
    return {"structure": structure, "ed25519": states[0], "falcon": states[1], "valid": overall}


def control_cases(data, method, keys, wrong):
    public = publics(keys)
    incorrect = publics(wrong)
    yield "C0", data, public, True
    yield "C1", covered_edit(data), public, False
    if method in (ED, HYBRID):
        yield "C2", data, (incorrect[0], public[1]), False
    if method in (FALCON, HYBRID):
        yield "C3", data, (public[0], incorrect[1]), False


def generated_keys():
    pair = generate_hybrid_key_pair()
    wrong = generate_hybrid_key_pair()
    require(all(a != b for a, b in zip(publics(pair), publics(wrong), strict=True)), "key.unexpected_duplicate")
    return pair, wrong


def sizes(data, input_size, method):
    if method == HYBRID:
        pair = utils.parse_signature_pair(data)
        containers = (pair.ed25519, pair.falcon)
    else:
        containers = (parse_single(data, method),)
    result = {"input_bytes": input_size, "output_bytes": len(data), "growth_bytes": len(data) - input_size}
    for container in containers:
        name = ("ed", "falcon")[container.sign_type]
        native = container.signature_length // 2
        capacity = container.capacity_bytes
        length = container.marker_end - container.marker_start
        result.update({f"{name}_native_bytes": native, f"{name}_capacity_bytes": capacity,
                       f"{name}_padding_ascii_bytes": (capacity - native) * 2,
                       f"{name}_metadata_bytes": length - 2 * capacity,
                       f"{name}_container_bytes": length})
    return result
