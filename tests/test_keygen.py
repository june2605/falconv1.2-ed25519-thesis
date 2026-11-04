from nacl.signing import SigningKey, VerifyKey
from pqcrypto.sign import falcon_512


def test_generated_keys_have_expected_sizes_and_are_usable(keys):
    assert len(keys.sk_ed.read_bytes()) == 32
    assert len(keys.pk_ed.read_bytes()) == 32
    assert len(keys.sk_falcon.read_bytes()) == falcon_512.SECRET_KEY_SIZE == 1281
    assert len(keys.pk_falcon.read_bytes()) == falcon_512.PUBLIC_KEY_SIZE == 897

    message = b"Phase 1 key-generation regression"
    signing_key = SigningKey(keys.sk_ed.read_bytes())
    assert bytes(signing_key.verify_key) == keys.pk_ed.read_bytes()
    signature = signing_key.sign(message).signature
    assert VerifyKey(keys.pk_ed.read_bytes()).verify(message, signature) == message

    signature = falcon_512.sign(keys.sk_falcon.read_bytes(), message)
    assert falcon_512.verify(keys.pk_falcon.read_bytes(), message, signature) is True
    assert falcon_512.verify(keys.pk_falcon.read_bytes(), message + b"!", signature) is False


def test_generation_produces_independent_key_pairs(keys, key_factory):
    other = key_factory()
    assert keys.pk_ed.read_bytes() != other.pk_ed.read_bytes()
    assert keys.pk_falcon.read_bytes() != other.pk_falcon.read_bytes()
