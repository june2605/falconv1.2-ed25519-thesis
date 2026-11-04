# Phase 2B.1: bounded containers and ByteRange validation

Implemented on 2026-11-05 (Asia/Bangkok), starting from Phase 1 commit
`990b946728821f775a423bbfd831ae2b5c8848be` on `thesis/development`.
The existing `.venv` was used without installing or upgrading dependencies.

## Scope and production changes

`utils.py` introduces `SignatureContainer`, `SignatureFormatError(ValueError)`
with structural error codes, and three separate parsing operations:

- `parse_signature_container()` validates local framing, field positions,
  hexadecimal Contents syntax and declared coverage.
- `parse_prepared_placeholder()` additionally requires an unfilled zero
  placeholder whose SigLength records capacity in bytes, as in the old writer.
- `parse_completed_signature()` instead interprets SigLength as a positive,
  even hexadecimal-character count that must fit entirely inside Contents.
  Native crypto verification still validates actual signatures. This operation
  does not check canonical zero padding or enforce algorithm-specific sizes.

The existing extraction functions retain their interfaces and use these
bounded operations. Missing fields cannot be recovered from later containers,
and a missing end marker cannot be borrowed across another container's marker.
Existing local positive/negative index selection is retained, with explicit
errors for unsupported types and out-of-range indices.

Let `h` be the start of SigLength, `g` the byte immediately after Contents' exact
closing `>\n`, and `e` the byte after the selected container's complete end
marker. Only `[0, h, g, e-g]` is accepted. Both intervals must be nonempty,
within the actual file and non-overlapping. Coverage must end at `e`, which
need not be file EOF at this stage. Decimal fields use the inherited exact
ten-digit ASCII representation, limiting encoded values to 9,999,999,999.
Bounds are checked before range-based message construction.

`sign.py` uses the prepared-state parser before signing each layer. Default
capacities (128 and 2048 bytes) are centralized in
`utils.DEFAULT_SIGNATURE_CAPACITIES`. Parsing derives actual capacity from
the bounded Contents field, so valid custom capacities are not forbidden.

The Ed25519 raw-message construction and Falcon SHAKE256 construction are
unchanged. `verify.py`, its 11-element tuple return contract, `app.py`, and
key generation are unchanged. This step does not enforce adjacency, single-pair
selection, canonical padding, an EOF policy or a global marker-collision policy.
The writer's global placeholder replacement and unchecked signature capacity
remain later hardening work.

## Tests and compatibility corpus

- `tests/test_integrity_weaknesses.py`: replaces the eight ambiguous parser
  xfails with otherwise well-formed control containers, individual range
  mutations and exact error-code assertions. Its two signed out-of-bounds
  cases now construct, hash and embed adversarial bytes without production
  parsing, digest or embedding helpers. The final bytes have a genuinely valid
  Falcon signature; rejection is asserted to be `byte_range.bounds`.
- `tests/container_cases.py`: independently constructs synthetic parser
  controls with correct positions, capacity, hexadecimal payload and coverage.
  Dummy signatures in parser-only controls are not claimed to be cryptographic
  signatures; integration cases use real keys and signatures.
- `tests/test_container_parsing.py`: adds signed/unsigned decimal syntax,
  integer bounds, exact gaps, revision boundaries, field placement, duplicate
  and missing fields, bounded signature lengths, cross-container framing,
  index selection, prepared/final states and compatibility coverage. It also
  checks that repeated hybrid signing remains accepted pending the later policy.
- `tests/fixtures/phase1-signatures.json`: two synthetic signed PDFs and public
  keys captured and verified with the unchanged Phase 1 production code before
  parser edits. This freezes old signatures rather than testing only newly
  generated output. It contains no private keys.

## Execution and outcomes

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Initial full baseline: **32 passed, 12 xfailed**.

Before production changes, the revised ten ByteRange cases produced
**10 failed, 2 xfailed** in the targeted integrity module. Every resolved
case failed because the old parser did not raise, while its valid control
was accepted. The two padding markers remained intact.

Final full suite: **160 passed, 2 xfailed**, exit code 0. No unexpected failures,
passes or skips. All 32 previously passing Phase 1 cases remain passing. All
eight parser xfails and both signed out-of-bounds xfails are now normal passing
tests. The remaining xfails are the two PDF variants of
`test_modified_falcon_padding_must_be_rejected`.

## Remaining risks and compatibility limits

Files with malformed ranges, noncanonical field widths/separators, misplaced
fields, nonhex Contents or signature lengths outside Contents are now rejected
even if the old permissive parser or native cryptography accepted them.
Original writer-produced valid single-pair signatures in the frozen corpus
still verify. Valid custom capacities and repeated signing remain supported;
acceptance does not imply that every historical signature has been evaluated.

Unused Falcon padding still permits undetected nonzero hexadecimal changes.
Global marker collisions, single-pair/order policy, canonical padding and full
writer hardening remain deferred. Identity/key-pair binding, key storage,
failure cleanup, PDF reader interoperability, memory usage and dependency
locking are unchanged. No CMS, PAdES or FIPS 206 compliance is claimed.

The original 15 benchmark/dataset files were checked against the Phase 1 SHA256
snapshot after implementation and were unchanged. The Phase 1 records and
original test fixtures were left unchanged. No commit or push was performed.
