"""Check covered bytes on one real signature of the public demo PDF."""

import hashlib
from pathlib import Path

import pytest
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from pqcrypto.sign import falcon_512

from keygen import generate_hybrid_key_pair
from sign import sign_with_key_material
from utils import parse_signature_pair
from verify import verify_bytes


@pytest.fixture(scope="module")
def signed_public_sample(tmp_path_factory):
    source = Path(__file__).resolve().parents[1] / "demo_assets" / "sample-unsigned.pdf"
    original = source.read_bytes()
    output = tmp_path_factory.mktemp("signature-boundary") / "signed.pdf"
    key_pair = generate_hybrid_key_pair()
    sign_with_key_material(source, output, key_pair)
    assert source.read_bytes() == original
    return original, output.read_bytes(), key_pair.public_keys


def covered_bytes(data, container):
    first, first_length, second, second_length = container.byte_range
    return data[first:first + first_length] + data[second:second + second_length]


def detached_signature(data, container):
    start = container.contents_start
    end = start + container.signature_length
    return bytes.fromhex(data[start:end].decode("ascii"))


def test_public_sample_verifies_under_both_original_messages(signed_public_sample):
    original, signed, keys = signed_public_sample
    pair = parse_signature_pair(signed)
    assert signed[:pair.ed25519.marker_start] == original
    assert pair.ed25519.marker_end == pair.falcon.marker_start
    assert pair.falcon.marker_end == len(signed)
    assert pair.falcon.gap_start > pair.ed25519.marker_end

    message_ed25519 = covered_bytes(signed, pair.ed25519)
    signature_ed25519 = detached_signature(signed, pair.ed25519)
    assert VerifyKey(keys.ed25519_public_key).verify(message_ed25519, signature_ed25519) == message_ed25519

    digest_falcon = hashlib.shake_256(covered_bytes(signed, pair.falcon)).digest(64)
    signature_falcon = detached_signature(signed, pair.falcon)
    assert falcon_512.verify(keys.falcon_public_key, digest_falcon, signature_falcon) is True

    result = verify_bytes(signed, keys.ed25519_public_key, keys.falcon_public_key)
    assert len(result) == 11 and result[0] is True


@pytest.mark.parametrize("region", ["pdf-content", "ed25519-signature"])
def test_covered_changes_fail_hybrid_verification(signed_public_sample, region):
    original, signed, keys = signed_public_sample
    pair = parse_signature_pair(signed)
    if region == "pdf-content":
        assert original.count(b"APPROVED") == 1
        edited = original.replace(b"APPROVED", b"REJECTED", 1)
        changed = edited + signed[len(original):]
    else:
        position = pair.ed25519.contents_start
        replacement = b"1" if signed[position:position + 1] == b"0" else b"0"
        changed = signed[:position] + replacement + signed[position + 1:]

    assert changed != signed and len(changed) == len(signed)
    assert parse_signature_pair(changed) == pair
    message_ed25519 = covered_bytes(changed, pair.ed25519)
    signature_ed25519 = detached_signature(changed, pair.ed25519)
    original_message_ed25519 = covered_bytes(signed, pair.ed25519)
    original_signature_ed25519 = detached_signature(signed, pair.ed25519)
    assert (message_ed25519 != original_message_ed25519) is (region == "pdf-content")
    assert (signature_ed25519 != original_signature_ed25519) is (region == "ed25519-signature")
    with pytest.raises(BadSignatureError):
        VerifyKey(keys.ed25519_public_key).verify(message_ed25519, signature_ed25519)

    digest_falcon = hashlib.shake_256(covered_bytes(changed, pair.falcon)).digest(64)
    assert digest_falcon != hashlib.shake_256(covered_bytes(signed, pair.falcon)).digest(64)
    signature_falcon = detached_signature(signed, pair.falcon)
    assert detached_signature(changed, pair.falcon) == signature_falcon
    assert falcon_512.verify(keys.falcon_public_key, digest_falcon, signature_falcon) is False
    result = verify_bytes(changed, keys.ed25519_public_key, keys.falcon_public_key)
    assert len(result) == 11 and result[0] is False
