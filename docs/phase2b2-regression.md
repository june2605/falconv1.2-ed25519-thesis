# Phase 2B.2: completed metadata and canonical padding

Implemented on 2026-11-05 (Asia/Bangkok), starting from
`f421879751a74677545d8a08a841903aa72c05dc` on `thesis/development`.
Used the existing `.venv`; no dependencies were installed or upgraded.

## Changes

| File | Purpose |
| --- | --- |
| `utils.py` | Extend only the completed-signature validator with algorithm size limits, lowercase signature hex and ASCII zero padding checks. Import size constants from the already installed crypto dependencies. |
| `tests/test_integrity_weaknesses.py` | Remove the final two padding xfails without changing their test bodies. |
| `tests/test_completed_signatures.py` | Add precise metadata, size, syntax, casing, padding and real-signature integration tests. |
| `docs/phase2b2-regression.md` | Record behavior, validation results, compatibility and remaining scope. |

## Validation rules

`parse_completed_signature()` continues to use Phase 2B.1's bounded parser.
That parser requires the exact `SigLength: ` label, ten unsigned ASCII decimal
digits and LF, immediately followed by the exact Contents field. Signs,
alternative spacing, short/long fields, unexpected metadata and invalid hex
are rejected. The declared ranges must still match the selected container.

For completed signatures, SigLength is a hexadecimal-character count. It must
be positive, even and entirely within the selected Contents capacity.

- Ed25519 requires exactly 128 characters, derived from PyNaCl's
  `crypto_sign_BYTES == 64`.
- Falcon-512 remains variable-length. Its decoded signature may not exceed
  the installed binding's `falcon_512.SIGNATURE_SIZE` (752 bytes with the
  validated `pqcrypto==0.3.4`). The maximum is consulted from the implementation,
  not copied into the production validator. No arbitrary fixed Falcon length
  or invented minimum is imposed. Native verification checks the actual
  encoding, consumed signature length and cryptographic validity.
- Counted signature characters must be lowercase ASCII hexadecimal.
- Every remaining Contents character must be ASCII `0` (0x30). Empty unused
  capacity is allowed. The check covers the entire bounded padding interval.

The validator reads the original bytes using bounded matching and counting.
It does not lowercase, trim, normalize, repair or rewrite the input. Structural
errors remain `SignatureFormatError(ValueError)`, with existing error codes
and the new `metadata.signature_size`, `contents.case` and `contents.padding`
codes. Native verification remains necessary; parsing success alone does not
establish a valid signature.

Prepared placeholders retain their separate validation and their inherited
byte-capacity length convention. Capacity is still derived from Contents,
so legitimate smaller/larger custom capacities remain supported.

## Tests and results

Command:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Initial full baseline: **160 passed, 2 xfailed**.

Before changing production code, the targeted integrity/completed-signature
tests produced **42 failed, 90 passed**. Failures demonstrated the missing
algorithm length checks, uppercase acceptance and nonzero padding acceptance,
including the two original padding cases.

Final full suite: **294 passed in 5.60 seconds**, exit code 0, with no failures,
xfails, xpasses or skips. All original 12 Phase 1 xfail cases are normal passing
tests, and all 160 previously passing Phase 2B.1 cases remain passing.

Coverage includes:

- Zero, odd, negative, signed, oversized and inconsistent signature lengths;
  Ed25519 sizes around its required count; Falcon sizes below, at and above
  the installed maximum, with synthetic metadata controls clearly separated
  from real crypto tests.
- First/middle/last signature casing and padding mutations, invalid bytes,
  whitespace, CRLF, NULs and unexpected metadata.
- Every unused Falcon padding position for each of two real signed PDFs.
- Real Falcon metadata changes whose original signature and digest remain
  cryptographically valid, proving the canonical metadata checks are required.
- Increased/decreased declared Falcon boundaries: native verification rejects
  counted zero-padding extensions and truncated signatures.
- Real hybrid round trips with custom capacities `(64, Falcon maximum)`,
  `(80, 1024)` and `(256, 4096)`, including no unused Ed25519 padding.
- Verification leaves rejected files byte-for-byte unchanged.
- Existing frozen Phase 1 signatures, new signing, independent layer failures,
  repeated signing and UI regression tests remain passing.

The signing, verification and embedding functions, both message/digest helpers,
prepared-placeholder parsing and previous passing test modules are unchanged.
The frozen compatibility JSON and all 15 original benchmark/dataset hashes
were checked and remain unchanged. No commit or push was performed.

## Compatibility and remaining risks

Canonical old signatures and legitimate custom capacities continue to verify.
Files with uppercase signature text, nonzero unused padding, unsupported sizes
or noncanonical metadata are now rejected even if their decoded signature
could previously verify. No existing file is rewritten to make it acceptable.
Compatibility is demonstrated by the frozen corpus and generated tests, not
every historical file.

This phase adds canonical validation to bytes excluded by the inherited
signature ranges; it does not add those bytes to the signed messages. Ed25519
still signs the first state, followed by Falcon over the unchanged SHAKE256
construction. `verify_file()` retains its 11-element return contract.

Single-pair/order policy, global marker collisions, final revision/rollback
semantics and writer hardening remain deferred. Key/identity trust, key storage,
failure cleanup, dependency locking, large-file memory behavior and PDF reader
interoperability are unchanged. The custom format has not been established as
CMS, PAdES or FIPS 206 compliant.
