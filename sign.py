from pqcrypto.sign import falcon_512
from nacl.signing import SigningKey
from utils import *
import time
from signing_io import capture_source, validate_signing_paths

from utils import prepare_file_with_placeholder

def sign_file(input_path: str, output_path: str, sk_ed: str, sk_falcon: str) :
    # The exact immutable snapshot checked here is used for both signatures.
    snapshot = capture_source(input_path)
    validate_unsigned_input(snapshot.data)
    protected_paths = (sk_ed, sk_falcon)
    destination = validate_signing_paths(snapshot, output_path, protected_paths=protected_paths)

    with open(sk_ed, "rb") as k:
        sk1 = k.read()
    
    with open(sk_falcon, "rb") as k:
        sk2 = k.read()

    if len(sk1) != 32:
        raise ValueError(f"Khóa Ed25519 không hợp lệ! Nhận được {len(sk1)} bytes, yêu cầu 32 bytes.")

    if len(sk2) != 1281:
        raise ValueError(f"Khóa Falcon không hợp lệ! Nhận được {len(sk2)} bytes, yêu cầu 1281 bytes.")
    #====================
    # sign ed25519
    #====================

    start_parse = time.time()
    pdf_bytes = prepare_bytes_with_placeholder(snapshot.data, DEFAULT_SIGNATURE_CAPACITIES[0])

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
    # All construction/capacity checks finish before the first destination write.
    # This is still a non-atomic write; publication safety belongs to 2B.4B.2.
    validate_signing_paths(snapshot, destination, protected_paths=protected_paths)
    with open(destination, "wb") as f:
        f.write(signed_pdf_bytes)
    time_io_falcon = time.time() - start_io
    time_total_falcon = (
    time_parse_falcon
    + time_hash_falcon
    + time_crypto_falcon
    + time_io_falcon
    )

    return (
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
