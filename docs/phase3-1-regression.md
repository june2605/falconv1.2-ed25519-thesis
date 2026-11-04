# Phase 3.1: in-memory hybrid key generation and signing foundation

Implemented on `thesis/development` in `D:\Final_Thesis_GitHub`, starting from
committed Phase 2 baseline `d444b59`. Initial working tree was clean. Used the
existing Python 3.11.9 environment without installing or updating dependencies.

## Scope and changed files

| File | Change |
| --- | --- |
| `hybrid_keys.py` | Minimal versioned public/private in-memory representations; exact types, identifiers, sizes, key correspondence, native self-tests and deterministic public tuple IDs. |
| `keygen.py` | New memory-only generator; make the legacy four-file generator an explicit plaintext-export wrapper with the same arguments and `None` return. |
| `sign.py` | Add memory-key signing using the existing captured-source signing core and transaction; preserve the path signer, required Falcon public key, timing tuple and legacy verification boundary. |
| `verify.py` | Add file verification with public-key bytes and pure document-bytes verification; extract the original shared verifier body without changing its parser/message/crypto/return operations. |
| `tests/test_key_material.py` | Model, identifiers, sizes, types, mismatches, native encodings, self-tests, redaction, generation and explicit legacy-export coverage. |
| `tests/test_memory_signing.py` | No-private-write instrumentation, inherited messages, byte-verifier boundaries, frozen signatures, custom capacities, aliases and signing/verification/I/O failure cleanup. |
| `README.md` | Show memory-key API usage and distinguish it from the legacy plaintext-key Streamlit workflow. |
| `docs/falcon-implementation-provenance.md` | Record installed artifacts, upstream lineage evidence and limits of any Falcon revision claim. |
| `docs/phase3-1-regression.md` | This representation, API, testing and compatibility record. |

No Argon2id, AES-GCM, encrypted vault, identity/enrollment/authentication service,
FastAPI, database, React or signature-container changes are implemented here.

## Version 1 representation

These frozen, slotted dataclasses contain immutable `bytes`. They are internal
Python values, not a serialized key format, secure enclave or vault.

`HybridPublicKey` contains:

| Field | Version 1 rule |
| --- | --- |
| `version` | Exact integer `1`; booleans/other versions rejected. |
| `ed25519_algorithm` | Exact string `ed25519`; no prehash variant or case normalization. |
| `falcon_algorithm` | Exact string `falcon_512`; no assumed specification revision or padded variant. |
| `ed25519_public_key` | Immutable bytes; size obtained from PyNaCl, currently 32. |
| `falcon_public_key` | Immutable bytes; size obtained from installed pqcrypto, currently 897. |

`HybridKeyPair` contains one `HybridPublicKey`, `ed25519_private_seed` (32-byte
raw seed) and `falcon_private_key` (the binding's raw encoding, currently 1281
bytes). The public object's version defines the whole representation. The
private fields are excluded from its default display; its custom repr shows
only the representation version and public tuple ID.

Public-only construction validates labels/types/sizes. It cannot establish
possession or identity. Pair construction and `validate_key_pair()` additionally
derive/compare the Ed25519 public key and perform both native signing tests.
Wrong sized/type inputs reject before private-key native calls. Bytearrays and
memoryviews are rejected rather than silently copied or normalized.

Each self-test uses a fresh 32-byte random context bound to the public ID and
the separate `THESIS-HYBRID-KEY-SELF-TEST-v1\0` domain. Ed25519 signs first;
Falcon's self-test message includes that Ed25519 signature. Test signature
sizes are checked and Falcon verification must return literal `True`.
These validation-only messages are **not** PDF messages or an enrollment protocol.
Falcon has no exposed public-key derivation API, so its correspondence is
checked with native sign/verify. Native self-test failures produce sanitized
`KeyMaterialError(ValueError)` messages, suppressing native exception chains.

Error codes are `key.version`, `key.algorithm`, `key.type`, `key.size`,
`key.correspondence` and `key.self_test`. Memory signing repeats validation;
there is no trusted cached-success flag. Fresh self-tests do not change the ID.
They do not prove entropy quality, prevent native-library faults, or establish
a trusted signer identity.

## Deterministic hybrid ID

For `LP(x) = uint32_be(len(x)) || x`, compute:

```text
preimage = b"THESIS-HYBRID-KEY-ID-v1\x00"
         || LP(b"ed25519") || LP(ed25519_public_key)
         || LP(b"falcon_512") || LP(falcon_public_key)

key_id = "hybrid-v1:" + lowercase_hex(SHA256(preimage))
```

Public values are raw bytes; labels are the exact ASCII above. Ordering,
domain and length widths are fixed. Private keys, identities, timestamps,
dependency versions and PDF capacities do not enter the identifier. Version 1
rejects other version/algorithm inputs. The ID is computed, not accepted as an
unverified stored field. This new metadata hash does not alter any PDF digest.

The regression vector uses synthetic public-size byte strings, not a claim of
valid key possession: Ed bytes `00..1f`; Falcon byte `09` followed by 896 bytes
whose value at index `i` is `i % 256`. Its ID is:

```text
hybrid-v1:4f6c8719d24379243002c5f1f71172570b5985784d4875539ebeaec30dea1f64
```

## APIs and private-key handling

```python
pair = keygen.generate_hybrid_key_pair()
result = sign.sign_with_key_material(source_path, destination_path, pair)
public = pair.public_keys
result = verify.verify_file_with_public_keys(pdf_path,
    public.ed25519_public_key, public.falcon_public_key)
result = verify.verify_bytes(pdf_bytes,
    public.ed25519_public_key, public.falcon_public_key)
```

The new generator has no file I/O. It creates both algorithm pairs and validates
the complete object before returning it. If generation/validation fails, no
partial pair is returned and no key files are created.

`sign_with_key_material()` captures a regular source file once, applies the
existing unsigned-input preflight and source/output path checks, validates the
pair, and delegates to `_sign_captured()`. It writes only owned intermediate
PDFs and the completed candidate, with no private or public key files. Final
verification reads the actual staged file with captured public-key bytes after
flush/fsync/close. It requires `result[0] is True`, cleans working files before
commit, rechecks paths and delegates to the unchanged `os.replace()` transaction.
No clock work or filesystem cleanup occurs after publication.

`sign_file(input, output, sk_ed, sk_falcon, *, pk_falcon=...)` retains its exact
public API. It captures/protects supplied file paths and delegates to the same
signing core. It retains its established public-key-file verification adapter
and fault-injection boundary; those temporary files contain public bytes only.
Legacy key size checks and final document self-verification continue to establish
whether its captured private/public material corresponds. The legacy path is
not forced through new pre-sign key self-tests that would change its established
error precedence. Both paths use the same actual PDF crypto implementation.

`generate_keys(pk_ed, sk_ed, pk_falcon, sk_falcon)` still explicitly exports four
plaintext files and returns `None`. It now obtains a fully generated/validated
memory pair before the first write. This reduces generation-time partial export
but does not make the four-file export atomic on subsequent I/O errors.

`verify_file()` retains its three path arguments and delegates to
`verify_file_with_public_keys()`. The latter and `verify_bytes()` share
`_verify_document()`. Its parser/message/crypto/result body is AST-identical to
the baseline verifier, excluding the new explanatory docstring.

All sign/verify interfaces retain eleven tuple positions. Pure bytes verification
reports zero in the I/O slot; wrong public-key lengths return the eleven-element
false tuple. The new bytes APIs require exact immutable bytes and raise
`TypeError` for other types. Filesystem errors in file APIs still propagate.
Timing slots retain their phase ordering, not a promise of identical numbers or
end-to-end duration. In particular, key construction/revalidation self-tests
are extra work outside the signing phase timings.

## Preserved protocol and compatibility

`utils.py`, `signing_io.py`, `app.py`, `demo.py`, all previously tracked tests
and frozen fixtures are unchanged (checked against Git-normalized contents).
Ed25519 still signs selected raw first-revision bytes. Falcon still signs the
existing 64-byte SHAKE256 construction over the state containing Ed25519.
The ID and self-test domains never enter the PDF. Strict ByteRanges, completed
metadata, pair/order/EOF rules, marker collisions, capacities and canonical
padding are unchanged. New tests independently verify those raw messages and
compare the actual selected messages between path and memory signers.

Both frozen Phase 1 signatures verify through the legacy and bytes-key APIs.
Real custom-capacity signing covers `(64, 752)`, `(80, 1024)`, `(128, 2048)`
and `(256, 4096)`. Source aliases, observed destination/candidate changes, I/O
and replacement failures retain Phase 2 transaction behavior.

## Regression results

Command:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Initial baseline: **757 passed, 8 skipped in 48.23 seconds**.

Tests preceded production changes. The first targeted run produced **2 failed,
3 errors** because the new model/generation API and bytes verifier did not yet
exist. The initial completed targeted suite passed 123 cases; the full suite
then passed 880 cases plus the existing eight skips. Further boundary, encoding,
revalidation and exact-message comparisons increased the new coverage to 146.

Final full suite: **903 passed, 0 failed, 8 skipped, 0 xfailed, 0 xpassed in
51.78 seconds**, exit code 0. All 757 previous cases pass unchanged.

The eight skips are the existing native Windows symlink tests: error 1314
requires Developer Mode/symlink privilege. No elevation or environment change
was attempted. Native hard-link and Windows destination-sharing tests pass;
the skipped native symlink coverage remains a platform limitation.

New tests deny all file operations during memory generation and pure bytes
verification. Signing tests intercept Python file writes (including descriptor
writes) and check that neither raw nor hex private material is written. They
exercise mismatched/malformed key material, both self-tests, strict input
types/lengths, wrong public keys, structural rejection before native verification,
valid/tampered documents, source snapshots/aliases, fault cleanup and publication
ordering. Existing comprehensive Phase 2 fault tests run without modification.

All fifteen original dataset/benchmark SHA256 values in `D:\Final_Thesis` match
the Phase 1 record. Test keys/documents are generated only as disposable fixtures.
The ID vector is public-size synthetic data; no private key fixture was added.

## Falcon revision evidence and remaining risks

See [Falcon implementation provenance](falcon-implementation-provenance.md).
The installed wrapper/native files match the official pqcrypto 0.3.4 wheel.
The investigated source lineage identifies PQClean's clean implementation as
20211101 with PQClean patches; the official Falcon specification is labelled
v1.2. This distinction does not justify an independently verified v1.2
conformance, reproducible-build, FIPS 206, CMS, PAdES or production-security claim.

Private material is still plaintext in Python/native memory. A frozen dataclass
and redacted repr are not isolation or guaranteed zeroization; explicit field
access, serialization, debugger/local-variable capture, memory dumps, paging,
native copies or a compromised process can expose it. No encryption or secure
storage is introduced. The Streamlit UI remains the existing plaintext-upload
prototype and has not migrated to the new API in this step.

The memory signer knows the source path, not the origins of supplied key bytes.
It cannot protect an unprovided vault/key-storage path from being chosen as its
output. The legacy wrapper still protects all supplied key-file paths; future
vault/caller boundaries must provide their own protected-storage policy.

Self-tests establish usable correspondence, not entropy, identity, enrollment,
revocation or a complete malicious-key/native-code audit. Full-file PDF stages
still use memory/disk. OS-denied cleanup, native crashes and abrupt termination
can leave owned PDF artifacts, and atomic replacement is not power-loss
durability or a complete defense against hostile filesystem races.

Dependencies remain unpinned by requirements.txt; this work uses the recorded
installed binding. A future implementation/encoding change requires explicit
compatibility review and, where appropriate, a new representation/algorithm
identifier. The public tuple ID is not an implementation-build fingerprint.

No dependencies were installed, original datasets modified, commits created or
pushes performed. Encrypted storage and signer-identity work remain later phases.
