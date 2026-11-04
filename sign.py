from pqcrypto.sign import falcon_512
from nacl.signing import SigningKey
from utils import *
import time
from pathlib import Path
from signing_io import SigningPathError, SigningTransaction, capture_source, validate_signing_paths
from verify import verify_file

from utils import prepare_file_with_placeholder

def sign_file(input_path: str, output_path: str, sk_ed: str, sk_falcon: str, *, pk_falcon: str):
    """Sign a captured source, verify its staged pair, then atomically replace output.

    The Falcon public key is explicit; Ed25519's is derived from its seed.
    The inherited 11-element timing tuple is unchanged. Its phase timings
    exclude key capture, final verification, transaction checks and publication;
    they are not an end-to-end workflow measurement.
    """
    requested_source = Path(input_path).absolute()
    snapshot = capture_source(requested_source)
    validate_unsigned_input(snapshot.data)
    # Keep the caller's path as well as the resolved destination for the final
    # alias check (a parent link may have been retargeted in the meantime).
    requested_output = Path(output_path).absolute()
    key_paths = tuple(Path(path).absolute() for path in (sk_ed, sk_falcon, pk_falcon))
    destination = validate_signing_paths(snapshot, requested_output, protected_paths=key_paths)
    captured_keys = tuple(capture_source(path) for path in key_paths)
    sk1, sk2, pk2 = (key.data for key in captured_keys)
    for label, data, size in (
        ("Ed25519 private seed", sk1, 32),
        ("Falcon private key", sk2, falcon_512.SECRET_KEY_SIZE),
        ("Falcon public key", pk2, falcon_512.PUBLIC_KEY_SIZE),
    ):
        if len(data) != size:
            raise ValueError(f"Invalid {label}: received {len(data)} bytes, expected {size}")
    protected_paths = captured_keys + key_paths + (requested_source,)
    validate_signing_paths(snapshot, requested_output, protected_paths=protected_paths)
    with SigningTransaction(destination) as transaction:
        return _sign_captured(snapshot, output_path, requested_output, protected_paths, transaction, sk1, sk2, pk2)


def _sign_captured(snapshot, output_path, requested_output, protected_paths, transaction, sk1, sk2, pk2):
    transaction.write_stage("source.pdf", snapshot.data)
    #====================
    # sign ed25519
    #====================

    start_parse = time.time()
    pdf_bytes = prepare_bytes_with_placeholder(snapshot.data, DEFAULT_SIGNATURE_CAPACITIES[0])
    transaction.write_stage("ed25519-prepared.pdf", pdf_bytes)

    byte_range = parse_prepared_placeholder(pdf_bytes).byte_range

    time_parse_ed25519 = time.time() - start_parse

    start_hash = time.time()
    digest = compute_sha512_digest_for_byte_range(pdf_bytes, byte_range)
    time_hash_ed25519 = time.time() - start_hash


    sk = SigningKey(sk1)
    start_crypto = time.time()
    signature = sk.sign(digest).signature
    # print("kích thước chữ ký ed25519: ", len(signature))
    # print("thơi gian ký ed25519 ",time.time()-start_sign_ed25519)
    time_crypto_ed25519 = time.time() - start_crypto

    start_io = time.time()
    signed_pdf_bytes = embed_signature_into_pdf(pdf_bytes, signature)
    transaction.write_stage("ed25519-signed.pdf", signed_pdf_bytes)
    time_io_ed25519 = time.time() - start_io

    time_total_ed25519 = (
    time_parse_ed25519
    + time_hash_ed25519
    + time_crypto_ed25519
    + time_io_ed25519
    )

    #===================
    # sign falcon
    #===================

    start_parse = time.time()
    pdf_bytes = prepare_bytes_with_placeholder(signed_pdf_bytes, DEFAULT_SIGNATURE_CAPACITIES[1], 1)
    transaction.write_stage("falcon-prepared.pdf", pdf_bytes)

    byte_range = parse_prepared_placeholder(pdf_bytes, 1).byte_range
    time_parse_falcon = time.time() - start_parse

    start_hash = time.time()
    digest = compute_shake256_digest_for_byte_range(pdf_bytes, byte_range)
    time_hash_falcon = time.time() - start_hash

    start_crypto = time.time()
    signature = falcon_512.sign(sk2, digest)
    time_crypto_falcon = time.time() - start_crypto
    # print("kích thước chữ ký falcon: ", len(signature))
    # print("thơi gian ký falcon ",time.time()-start_sign_falcon)

    start_io = time.time()
    signed_pdf_bytes = embed_signature_into_pdf(pdf_bytes, signature, 1)
    candidate = transaction.write_candidate(signed_pdf_bytes)
    time_io_falcon = time.time() - start_io

    ed_public = transaction.write_stage("ed25519-public.key", bytes(sk.verify_key))
    falcon_public = transaction.write_stage("falcon-public.key", pk2)
    # Verify the actual closed, fsynced staged file, using only captured keys.
    # A nonempty false-result tuple, or an integer equal to True, is not success.
    result = verify_file(candidate, ed_public, falcon_public)
    if result[0] is not True:
        raise ValueError("Hybrid signature self-verification failed")
    transaction.mark_verified()
    transaction.cleanup_working()
    time_total_falcon = (
    time_parse_falcon
    + time_hash_falcon
    + time_crypto_falcon
    + time_io_falcon
    )

    signing_result = (
    output_path,

    # Ed25519
    time_parse_ed25519,
    time_hash_ed25519,
    time_crypto_ed25519,
    time_io_ed25519,
    time_total_ed25519,

    # Falcon
    time_parse_falcon,
    time_hash_falcon,
    time_crypto_falcon,
    time_io_falcon,
    time_total_falcon
    )
    checked_destination = validate_signing_paths(snapshot, requested_output, protected_paths=protected_paths)
    if checked_destination != transaction.destination:
        raise SigningPathError("path.changed", "Destination resolved to a different path during signing")
    # Prepare the return value before commit: no clocks, reads or cleanup after
    # replacement may turn a completed publication into a reported I/O failure.
    transaction.publish()
    return signing_result
