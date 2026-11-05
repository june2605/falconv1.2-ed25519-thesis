"""Format controls are built independently of the production serializer."""

from dataclasses import FrozenInstanceError, replace
import importlib
from uuid import UUID

import pytest

from vault_cases import INTEGER_FIELDS, NONCE, SALT, UUID_BYTES, change, flip, header, wire


@pytest.fixture
def fmt():
    return importlib.import_module("vault_format")


def test_exact_format_and_original_aad(fmt):
    parsed = fmt.parse_vault(wire())
    assert (fmt.HEADER_LENGTH, fmt.PAYLOAD_LENGTH, fmt.ENCRYPTED_PAYLOAD_LENGTH,
            fmt.VAULT_LENGTH) == (1069, 1331, 1347, 2416)
    assert parsed.header_bytes == header()
    assert len(parsed.encrypted_payload) == 1347
    assert parsed.metadata.vault_uuid.bytes == UUID_BYTES
    assert parsed.metadata.salt == SALT
    assert parsed.metadata.nonce == NONCE
    assert parsed.metadata.key_id == (
        "hybrid-v1:4f6c8719d24379243002c5f1f71172570b5985784d4875539ebeaec30dea1f64")
    assert fmt.encode_header(parsed.metadata) == header()


@pytest.mark.parametrize("offset,width,value,profile", INTEGER_FIELDS)
def test_all_integer_fields_exact_big_endian(fmt, offset, width, value, profile):
    encoded = fmt.encode_header(fmt.parse_vault(wire()).metadata)
    assert encoded[offset:offset + width] == value.to_bytes(width, "big")


@pytest.mark.parametrize("offset,width,value,profile", INTEGER_FIELDS)
@pytest.mark.parametrize("replacement", [0, 65535])
def test_every_fixed_header_integer_rejects(fmt, offset, width, value, profile, replacement):
    error = fmt.VaultProfileError if profile else fmt.VaultFormatError
    with pytest.raises(error):
        fmt.parse_vault(change(wire(), offset, replacement.to_bytes(width, "big")))


@pytest.mark.parametrize("offset,values", [
    (50, [1, 65535, 65537, 2**32 - 1]), (54, [1, 2, 4, 2**32 - 1]),
    (58, [1, 3, 5, 2**32 - 1]),
])
def test_only_approved_kdf_profile(fmt, offset, values):
    for value in values:
        with pytest.raises(fmt.VaultProfileError):
            fmt.parse_vault(change(wire(), offset, value.to_bytes(4, "big")))


@pytest.mark.parametrize("bad", [None, "vault", bytearray(wire()), memoryview(wire()), 1])
def test_requires_exact_immutable_bytes(fmt, bad):
    with pytest.raises(fmt.VaultFormatError):
        fmt.parse_vault(bad)


def test_bytes_subclass_rejected(fmt):
    class CustomBytes(bytes):
        pass
    with pytest.raises(fmt.VaultFormatError):
        fmt.parse_vault(CustomBytes(wire()))


@pytest.mark.parametrize("size", [0, 1, 1068, 1069, 1347, 2415, 2417, 4096, 4097, 1048576])
def test_exact_total_length_no_trailing_bytes(fmt, size):
    with pytest.raises(fmt.VaultFormatError):
        fmt.parse_vault((wire() + b"\x00" * max(0, size - 2416))[:size])


@pytest.mark.parametrize("uuid_bytes", [
    b"\x00" * 16,
    UUID("00010203-0405-1607-8809-0a0b0c0d0e0f").bytes,
    UUID("00010203-0405-4607-0809-0a0b0c0d0e0f").bytes,
    UUID_BYTES[::-1],
])
def test_only_standard_rfc_uuid4(fmt, uuid_bytes):
    with pytest.raises(fmt.VaultFormatError):
        fmt.parse_vault(change(wire(), 16, uuid_bytes))


@pytest.mark.parametrize("offset", [0, 7, 108, 139, 140, 1036, 1037, 1068])
def test_invalid_magic_or_public_id(fmt, offset):
    with pytest.raises(fmt.VaultFormatError):
        fmt.parse_vault(flip(wire(), offset))


def test_parser_results_and_metadata_immutable(fmt):
    parsed = fmt.parse_vault(wire())
    with pytest.raises(FrozenInstanceError):
        parsed.header_bytes = b""
    with pytest.raises(FrozenInstanceError):
        parsed.metadata.salt = b""
    with pytest.raises(FrozenInstanceError):
        parsed.metadata.public_keys.ed25519_public_key = b""


@pytest.mark.parametrize("field,value", [
    ("vault_uuid", "not-a-uuid"), ("salt", b"x" * 15),
    ("salt", bytearray(SALT)), ("nonce", b"x" * 13), ("public_keys", None),
])
def test_invalid_metadata_cannot_be_serialized(fmt, field, value):
    with pytest.raises(fmt.VaultFormatError):
        fmt.encode_header(replace(fmt.parse_vault(wire()).metadata, **{field: value}))
