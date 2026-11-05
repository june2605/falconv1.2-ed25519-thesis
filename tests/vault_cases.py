"""Independent public wire controls; no private-key fixtures or production codec helpers."""

import hashlib
import struct
from uuid import UUID


PASSWORD = "disposable test password only"
UUID_BYTES = UUID("00010203-0405-4607-8809-0a0b0c0d0e0f").bytes
SALT = bytes(range(16))
NONCE = bytes(range(16, 28))
TEST_AEAD_KEY = bytes(range(32))  # Public primitive-boundary test key, not a vault secret.

# offset, width, canonical integer, profile field (otherwise format field)
INTEGER_FIELDS = (
    (8, 2, 1, False), (10, 2, 1069, False), (12, 4, 1347, False),
    (32, 2, 1, False), (34, 2, 1, True), (36, 2, 2, True),
    (38, 2, 1, False), (40, 2, 1, False), (42, 2, 1, False),
    (44, 2, 1, True), (46, 2, 1, True), (48, 2, 19, True),
    (50, 4, 65536, True), (54, 4, 3, True), (58, 4, 4, True),
    (62, 2, 32, True), (64, 2, 1, True), (66, 2, 12, False),
    (68, 2, 16, False), (70, 2, 16, False), (72, 2, 1, True),
    (74, 2, 32, False), (76, 2, 897, False), (78, 2, 32, False),
)


def public_digest(ed, falcon):
    fields = (b"ed25519", ed, b"falcon_512", falcon)
    encoded = b"THESIS-HYBRID-KEY-ID-v1\x00"
    for value in fields:
        encoded += struct.pack(">I", len(value)) + value
    return hashlib.sha256(encoded).digest()


def header(public=None):
    ed = bytes(range(32)) if public is None else public.ed25519_public_key
    falcon = (b"\x09" + bytes(i % 256 for i in range(896))
              if public is None else public.falcon_public_key)
    data = bytearray(1069)
    data[:8] = b"HYBKVLT\x00"
    for offset, width, value, _ in INTEGER_FIELDS:
        data[offset:offset + width] = value.to_bytes(width, "big")
    data[16:32] = UUID_BYTES
    data[80:96] = SALT
    data[96:108] = NONCE
    data[108:140] = ed
    data[140:1037] = falcon
    data[1037:1069] = public_digest(ed, falcon)
    return bytes(data)


def wire(public=None):
    return header(public) + b"\x00" * 1347  # Parser-only control; NOT authenticated.


def payload(pair):
    return (b"HYBKEYS\x00" + struct.pack(">5H", 1, 1, 1, 32, 1281)
            + pair.ed25519_private_seed + pair.falcon_private_key)


def change(data, offset, replacement):
    return data[:offset] + replacement + data[offset + len(replacement):]


def flip(data, offset):
    return change(data, offset, bytes([data[offset] ^ 1]))
