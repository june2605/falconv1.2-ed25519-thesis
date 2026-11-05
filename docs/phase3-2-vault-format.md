# Phase 3.2B.1: hybrid encrypted vault format v1

Implemented from the approved Phase 3.2A positional format on
`thesis/development`, starting at `0afe0ad`. This is an in-memory codec only.
The format is separate from PDF signature containers and from the existing
version-1 Python key representation. No PDF format or signing message changes.

## API and trust boundary

```python
from keygen import generate_hybrid_key_pair
from vault_crypto import seal_key_pair, unseal_key_pair

pair = generate_hybrid_key_pair()
encrypted_bytes = seal_key_pair(pair, password)  # password supplied locally
unlocked = unseal_key_pair(encrypted_bytes, password)
assert unlocked.key_pair == pair
assert unlocked.metadata.key_id == pair.key_id
```

Both public functions have exactly two arguments. Salt, nonce, UUID and KDF
parameters are not caller-selectable. Neither function reads or creates files,
directories, temporary files or plaintext key exports. Normal Python dependency
imports can load code from disk; that is not vault persistence.

`VaultMetadata` is a frozen, slotted dataclass containing a `UUID`,
`HybridPublicKey`, immutable salt bytes and immutable nonce bytes. Its
`format_version` property is 1 and `key_id` uses the existing public-tuple ID.
`UnsealedVault` is frozen/slotted and contains `key_pair` and `metadata`.
Its representation omits private material. Python immutability is not a secure
memory boundary or an unforgeable validation capability.

`vault_format.parse_vault()` returns a frozen `ParsedVault` with metadata,
original `header_bytes` and `encrypted_payload`. This result is **unauthenticated**
and must not authorize signing or identity decisions. Only successful
`unseal_key_pair()` authenticates the header and validates private keys. A valid
public ID proves neither key possession nor trusted signer identity.

## Exact header layout

All integer fields are unsigned, big-endian. Offsets are zero based, widths in
bytes. There is no alignment, optional field, delimiter, padding or text
normalization. Exactly one header and one encrypted payload are accepted.

| Offset | Width | Field | Required v1 value / encoding |
| --- | --- | --- | --- |
| 0 | 8 | magic | `b"HYBKVLT\x00"` |
| 8 | 2 | format version | 1 |
| 10 | 2 | header length | 1069 |
| 12 | 4 | encrypted payload length, including tag | 1347 |
| 16 | 16 | vault UUID | RFC-variant UUIDv4, standard `UUID.bytes`; never `bytes_le` |
| 32 | 2 | key-material version | 1 |
| 34 | 2 | Ed25519 algorithm ID | 1 = `ed25519` |
| 36 | 2 | Falcon algorithm ID | 2 = `falcon_512` |
| 38 | 2 | Ed25519 public encoding version | 1 = raw public bytes |
| 40 | 2 | Falcon public encoding version | 1 = binding raw public bytes |
| 42 | 2 | payload encoding version | 1 |
| 44 | 2 | password encoding ID | 1 = strict UTF-8, no normalization |
| 46 | 2 | KDF ID | 1 = Argon2id |
| 48 | 2 | Argon2 version | 19 (`0x0013`, Argon2 v1.3) |
| 50 | 4 | memory cost, KiB | 65536 |
| 54 | 4 | iterations | 3 |
| 58 | 4 | lanes | 4 |
| 62 | 2 | derived key length | 32 |
| 64 | 2 | AEAD ID | 1 = AES-256-GCM |
| 66 | 2 | nonce length | 12 |
| 68 | 2 | tag length | 16 |
| 70 | 2 | salt length | 16 |
| 72 | 2 | hybrid key ID scheme | 1 = existing `hybrid-v1` |
| 74 | 2 | Ed25519 public length | 32 |
| 76 | 2 | Falcon public length | 897 |
| 78 | 2 | hybrid ID digest length | 32 |
| 80 | 16 | salt | Fresh OS-random bytes |
| 96 | 12 | nonce | Fresh OS-random bytes |
| 108 | 32 | Ed25519 public key | Raw bytes |
| 140 | 897 | Falcon public key | Raw binding bytes |
| 1037 | 32 | hybrid ID digest | Raw SHA-256 digest; no prefix or hexadecimal text |

The header ends at offset 1069. The equivalent Python struct is
`>8sHHI16s9H3I9H16s12s32s897s32s`.

The digest is exactly the existing `hybrid_keys.hybrid_key_id()` digest:

```text
LP(x) = uint32_be(len(x)) || x
digest = SHA256(b"THESIS-HYBRID-KEY-ID-v1\x00"
               || LP(b"ed25519") || LP(ed25519_public_key)
               || LP(b"falcon_512") || LP(falcon_public_key))
key_id = "hybrid-v1:" + lowercase_hex(digest)
```

The parser recomputes this digest and compares it with `hmac.compare_digest()`.
This metadata hash does not change PDF digest construction.

## Exact private payload and ciphertext layout

Payload offsets are relative to the plaintext payload, before encryption.

| Offset | Width | Field | Required v1 value / encoding |
| --- | --- | --- | --- |
| 0 | 8 | magic | `b"HYBKEYS\x00"` |
| 8 | 2 | payload version | 1 |
| 10 | 2 | Ed25519 private encoding version | 1 = raw seed |
| 12 | 2 | Falcon private encoding version | 1 = binding raw secret |
| 14 | 2 | Ed25519 private seed length | 32 |
| 16 | 2 | Falcon private key length | 1281 |
| 18 | 32 | Ed25519 private seed | Original seed bytes |
| 50 | 1281 | Falcon private key | Original raw secret bytes |

Plaintext length is exactly 1331; struct `>8s5H32s1281s`. No private padding or
extra fields are accepted. AESGCM produces 1331 ciphertext bytes followed by
the full 16-byte tag. The vault is:

```text
file[0:1069]       original header, also the complete AEAD associated data
file[1069:2400]    ciphertext (1331 bytes)
file[2400:2416]    authentication tag (16 bytes)
```

Total vault length is **2416 bytes**. No trailing bytes are permitted.

## Cryptographic and password profile

`cryptography==50.0.2` is the required backend. `Argon2id` derives 32 bytes using
exactly version 19, 65536 KiB, 3 iterations, 4 lanes and the 16-byte public salt.
The API's optional secret and associated-data inputs are `None`. Every other
profile rejects before derivation, including cheaper profiles. There is no
algorithm fallback. The API implements Argon2 v1.3; its implementation is checked
against the [RFC 9106 section 5.3 vector](https://www.rfc-editor.org/rfc/rfc9106.html#section-5.3).
That primitive vector's small memory setting is never accepted as a vault profile.

AESGCM uses the resulting 32-byte key, the 12-byte nonce, the entire header as
AAD and a full 16-byte tag. Unlock passes the **original** `vault_bytes[:1069]`
to decryption; it never reserializes or normalizes AAD. The library's
[AESGCM API](https://cryptography.io/en/50.0.2/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM)
performs tag validation before this codec parses any decrypted material.

Creation obtains an independent random UUIDv4, 16-byte salt and 12-byte nonce
for every operation. Fresh salts separate derived keys; fresh nonces avoid
reuse with a derived key under the OS RNG assumption. Random generation cannot
give an absolute uniqueness guarantee under RNG compromise or statistical
collision. No fixed-randomness production API or persistent nonce registry exists.

Passwords must be exact Python `str` values, nonempty, encodable with strict
UTF-8 and at most 1024 encoded bytes. Unpaired surrogates reject. There is no
trimming, normalization or case folding; spaces and canonically equivalent
Unicode strings remain distinct. Creation additionally requires at least 15
Unicode code points. Unlock intentionally does not impose that creation minimum.
The length policy does not measure password entropy or prevent offline guessing.

A fail-fast, process-local semaphore permits at most one 64 MiB KDF at a time.
It is released after encryption/decryption, including failures. It is not a
vault-file lock, cross-process resource limit or protection against unlimited
sequential attempts. No filesystem locking is implemented in this phase.

## Validation order and errors

Unlock proceeds in this order:

1. Require exact immutable `bytes`. Reject above the defensive 4096-byte ceiling
   and reject every length except 2416, including truncation and appended data.
2. Check magic, versions, every fixed length/identifier, UUID version/variant,
   the exact KDF/AEAD profile, public key sizes and the recomputed hybrid ID.
3. Validate password encoding/size; load the exact approved backend.
4. Acquire the process KDF slot, derive, and authenticate/decrypt the original
   ciphertext, nonce and original complete header. Release the slot in `finally`.
5. Strictly parse authenticated payload bytes. Construct `HybridPublicKey` and
   `HybridKeyPair`; require Ed25519 seed/public correspondence and both existing
   native self-tests (including Falcon sign/verify), then compare the ID again.
6. Return a complete immutable `UnsealedVault`. Never return partial keys or
   generate replacement keys after failure.

These `VaultError(ValueError)` subclasses are defined in `vault_format.py`:

| Class | Stable code | Meaning |
| --- | --- | --- |
| `VaultFormatError` | `vault.format` | Bad input type/length, magic, version, structural encoding, UUID or public digest |
| `VaultProfileError` | `vault.profile` | Unsupported algorithm, KDF parameters, password encoding or ID scheme |
| `VaultUnlockError` | `vault.unlock` | Generic incorrect-password or damaged-vault authentication failure |
| `VaultKeyMaterialError` | `vault.key_material` | Invalid input pair or invalid authenticated private payload/correspondence/self-test |
| `VaultBackendError` | `vault.backend` | Missing/wrong package, unsupported native primitive, allocation or backend operation failure |
| `VaultPasswordError` | `vault.password` | Password type, UTF-8 or length policy failure |
| `VaultBusyError` | `vault.busy` | Another process-local KDF operation is running |

Messages are fixed and do not contain supplied values or native exception text.
AES-GCM `InvalidTag` maps to `vault.unlock: Incorrect password or damaged vault`,
without distinguishing wrong passwords from authenticated-data corruption.
Native exception chains are suppressed in displayed errors. No logging is done.
Malformed public structure may produce a format/profile error before authentication;
it must not be treated as authenticated information.

## Compatibility, limits and deferred work

The codec preserves both original private values, both public keys and the
existing hybrid ID. It uses the current 32/897/1281-byte encodings; a future
incompatible native encoding requires an explicit format/version migration.
It makes no Falcon specification-revision claim beyond the implementation
evidence in `falcon-implementation-provenance.md`.

The inherited PDF signer/verifier, strict parsing and padding rules, eleven-item
return tuples, path wrapper, in-memory signer, frozen signatures and custom
capacities are unchanged. This codec is not integrated into the UI or signing
workflow yet. The legacy plaintext-export workflow still exists and is not
automatically secured by adding this module.

Salt, nonce, UUID, both public keys and their ID are public and linkable. Encryption
does not enroll a signer, prove identity, prevent whole-vault substitution by a
party who knows the password, detect rollback, or provide revocation. Stolen vaults
permit offline password guessing. Lost passwords and lost key material are not
recoverable by this codec.

Plaintext seeds, Falcon secrets, passwords and derived keys exist in immutable
Python bytes, intermediate copies and native memory. Reliable zeroization,
locked memory, swap/crash-dump exclusion, malware protection and native-crash
containment are not provided. Exception objects/tracebacks can retain locals;
callers must not log locals or inspect suppressed contexts as user diagnostics.
The input ceiling cannot undo memory already allocated by a caller; a later file
reader must independently bound reads before constructing the input bytes.

Phase 3.2B.2 will address encrypted-only persistence, atomic publication, ACLs,
aliasing, filesystem races, process locks, password changes and backup/restore.
Phase 3.2B.3 will address local signing/UI integration and its end-to-end tests.
Authentication, trusted public-key enrollment, key lifecycle, server services and
databases remain separate future work. No FIPS, CMS, PAdES or production-security
compliance is claimed. Runtime and regression evidence is recorded in
`phase3-2b1-regression.md`.
