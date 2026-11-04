from pqcrypto.sign import falcon_512
from nacl.signing import VerifyKey
from utils import *
import time


def verify_file(pdf_path: str, pk_ed: str, pk_falcon: str):
    
    with open(pk_ed, "rb") as f:
        pk1 = f.read()

    with open(pk_falcon, "rb") as f:
        pk2 = f.read()

    return verify_file_with_public_keys(pdf_path, pk1, pk2)


def _public_key_lengths_valid(pk1, pk2):
    if type(pk1) is not bytes or type(pk2) is not bytes:
        raise TypeError("Public keys must be immutable bytes")
    return len(pk1) == 32 and len(pk2) == falcon_512.PUBLIC_KEY_SIZE


def verify_file_with_public_keys(pdf_path, pk_ed: bytes, pk_falcon: bytes):
    """Verify the actual file using public bytes, with the legacy 11 slots."""
    if not _public_key_lengths_valid(pk_ed, pk_falcon):
        return (False,) + (0,) * 10
    start_io = time.time()
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    time_io = time.time() - start_io
    return _verify_document(pdf_bytes, pk_ed, pk_falcon, time_io)


def verify_bytes(pdf_bytes: bytes, pk_ed: bytes, pk_falcon: bytes):
    """No filesystem access; return the same 11 slots, with I/O time zero.

    A true first element proves both signatures under supplied public keys,
    not signer identity or registry trust. Mutable buffers are not normalized.
    """
    if type(pdf_bytes) is not bytes:
        raise TypeError("Document must be immutable bytes")
    if not _public_key_lengths_valid(pk_ed, pk_falcon):
        return (False,) + (0,) * 10
    return _verify_document(pdf_bytes, pk_ed, pk_falcon, 0)


def _verify_document(pdf_bytes, pk1, pk2, time_io):
    """Shared inherited parser/message/crypto flow for all verification APIs."""
    ok_ed = False
    ok_falcon = False

    # Validate both completed containers and their global topology before
    # either algorithm receives a message. Shared pair validation is charged
    # to the existing Ed25519 parse slot; Falcon's parse slot covers decoding.
    try:
        start_parse_ed = time.time()
        pair = parse_signature_pair(pdf_bytes)
        byte_range_ed = pair.ed25519.byte_range
        sig_hex_ed = pdf_bytes[
            pair.ed25519.contents_start:
            pair.ed25519.contents_start + pair.ed25519.signature_length
        ]
        signature_ed = bytes.fromhex(sig_hex_ed.decode())
        time_parse_ed = time.time() - start_parse_ed

    except ValueError:
        time_parse_ed = time.time() - start_parse_ed
        return (False,
                time_parse_ed, 0, 0, time_parse_ed,
                0, 0, 0, 0,
                time_io, time_io + time_parse_ed)

    start_parse_falcon = time.time()
    byte_range_falcon = pair.falcon.byte_range
    sig_hex_falcon = pdf_bytes[
        pair.falcon.contents_start:
        pair.falcon.contents_start + pair.falcon.signature_length
    ]
    # The pair parser has already required bounded ASCII hexadecimal here.
    signature_falcon = bytes.fromhex(sig_hex_falcon.decode())
    time_parse_falcon = time.time() - start_parse_falcon

    try:
        start_hash_ed = time.time()
        digest_ed = compute_sha512_digest_for_byte_range(pdf_bytes, byte_range_ed)
        time_hash_ed = time.time() - start_hash_ed

    except:
        time_hash_ed = 0
        ok_ed = False
    try:
        pk = VerifyKey(pk1)
        start_crypto_ed = time.time()

        pk.verify(digest_ed, signature_ed)
        time_crypto_ed = time.time() - start_crypto_ed
        ok_ed = True
    except:
        time_crypto_ed = 0
        ok_ed = False

    time_total_ed = (
        time_parse_ed +
        time_hash_ed +
        time_crypto_ed
    )

    # Hash
    try:
        start_hash_falcon = time.time()

        digest_falcon = compute_shake256_digest_for_byte_range(
            pdf_bytes,
            byte_range_falcon
        )

        time_hash_falcon = (
            time.time() - start_hash_falcon
        )

    except Exception:
        time_hash_falcon = 0
        ok_falcon = False

    # Pure Crypto Verify
    try:
        start_crypto_falcon = time.time()

        ok_falcon = falcon_512.verify(
            pk2,
            digest_falcon,
            signature_falcon
        )

        time_crypto_falcon = (
            time.time() - start_crypto_falcon
        )

    except Exception:
        time_crypto_falcon = 0
        ok_falcon = False

    time_total_falcon = (
        time_parse_falcon +
        time_hash_falcon +
        time_crypto_falcon
    )

    time_total_verify = (
        time_io +
        time_total_ed +
        time_total_falcon
    )

    return (
        ok_ed and ok_falcon,

        # Ed25519
        time_parse_ed,
        time_hash_ed,
        time_crypto_ed,
        time_total_ed,

        # Falcon
        time_parse_falcon,
        time_hash_falcon,
        time_crypto_falcon,
        time_total_falcon,

        # Workflow
        time_io,
        time_total_verify
    )
    
