# Phase 5.1A — Hybrid signature integrity boundary audit

The workspace started clean on `thesis/ui-demo` at `1a88095`. The audit
uses the existing Windows Python 3.11 environment and `pqcrypto==0.3.4`.
The loaded Falcon extension's SHA-256 is
`ad5983a68922b01d84332ee800e16b55f001d1353ef62b32efd8d5d1216da237`,
matching the Phase 5.1 wheel evidence. Production source and the release
binaries were preserved.
[Research audit](phase5-1-research-audit.md) ·
[Implementation evidence](phase5-1-implementation-evidence.md) ·
[Experiment gaps](phase5-1-experiment-gap-analysis.md) ·
[Thesis traceability](phase5-1-thesis-traceability.md)

**Finding.** The pinned native verification source accepts a wider set of
signature encodings than the compressed representation produced by the
signer. The application constrains the PDF layout, hex syntax and padding,
and delegates native encoding acceptance to that verifier. This is a
source-level canonicalization gap. An alternate final PDF that verifies
under the original keys without a new signature was **not demonstrated**.
The executed controls establish rejection for their particular mutations.
[Native format source](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/clean/pqclean.c) ·
[PDF completion rules](../utils.py#L164) · [Verifier](../verify.py#L48)

## Exact signed messages

Let `P` be the captured PDF, `E` the completed Ed25519 revision, and `F`
the completed hybrid file. Thus `E = P || C_E` and `F = E || C_F`. For a
container `i`, let `g0_i` be the first byte of the `SigLength` line,
`g1_i` the first byte of the end marker and `end_i` the exclusive
container end. The accepted ByteRange is
`(0, g0_i, g1_i, end_i - g1_i)`. Byte slices below are half-open.

| Layer | Exact input at the native API | Coverage |
| --- | --- | --- |
| Ed25519 | `E[0:g0_E] \|\| E[g1_E:end_E]` | The original PDF, Ed25519 start marker and ByteRange, and the Ed25519 end marker. The layer omits its own signature-storage gap and terminates before the Falcon container. |
| Falcon-512 | `SHAKE256(F[0:g0_F] \|\| F[g1_F:end_F] \|\| F[end_F:]).digest(64)` | The original PDF and the entire completed Ed25519 container, plus the Falcon start marker, ByteRange and end marker. The Falcon gap is excluded. The suffix term is empty for an accepted pair, whose Falcon end must coincide with EOF. |

The inherited name `compute_sha512_digest_for_byte_range()` is misleading.
It returns the concatenated ByteRange bytes. Pure Ed25519 applies its
own internal hashing, with no application-level SHA-512 prehash.
`compute_shake256_digest_for_byte_range()` does apply SHAKE256 before
passing its 64-byte result to Falcon's native signing or verification API.
The signer calculates these inputs over the corresponding prepared
revisions. Embedding only fills each gap at the known offsets and
preserves length, so the verifier sees the same messages on the completed
revision. The whole-pair parser runs before native verification and
requires both exact ranges, adjacency and final EOF. The verifier's
11-element result starts with the conjunction of the two cryptographic
checks after structural validation.
[Signer](../sign.py#L74) · [Range validation](../utils.py#L102) ·
[Pair validation](../utils.py#L190) · [Message functions](../utils.py#L267) ·
[Embedding](../utils.py#L286) · [Verification](../verify.py#L48)

## Outer Falcon gap

The gap spans the fixed-width `SigLength` line and the entire
`Contents: <…>` line, including their line endings. The start/end markers
and the ByteRange line lie outside it. Default reserved Falcon capacity is
2,048 bytes before hex encoding. The detached native signature uses the
actual encoded length, bounded by the binding's 752-byte maximum. The
completed `SigLength` value counts **hex characters**, while the
writer's prepared state uses byte capacity. The two states have separate
parse paths.

| Field | Cryptographic role | Structural validation | Canonicality and variability |
| --- | --- | --- | --- |
| `ByteRange` | Covered by the Falcon message | Four ten-digit unsigned fields. Intervals must start at zero, fit the data, be nonempty and nonoverlapping, skip exactly the parsed gap, and end at their container boundary. | Exact ASCII grammar. Changing coverage of an existing file cannot be justified by pointing the parser at a different gap. |
| `SigLength` | The line itself is outside the Falcon message. Its value determines the native signature buffer. | Fixed-width unsigned ASCII, positive, even, within hex capacity and within the installed native byte limit. | One textual spelling per integer. The bound alone does not establish a unique native encoding. Length legitimately varies across newly signed files. |
| Declared signature hex | The decoded bytes are passed to native verification. The storage text is outside the native message. | Lowercase ASCII hex of the declared size. The native library checks its interpretation against the public key and message. | Canonical hex for a chosen byte buffer. Native representation uniqueness is a separate property. |
| Unused `Contents` space | Excluded from the Falcon message and not passed as unused padding to native verification. | All bytes after the declared signature portion must be ASCII zero. | Fixed for the parsed declaration and field span. This proves that remaining fill is canonical under that declaration. |
| Gap field syntax and delimiters | The `SigLength` and `Contents` syntax within the gap is outside the message. | Exact placement, prefixes, close and LF delimiters. | Syntax does not permit relaxed whitespace or line endings. |
| Container markers and end of file | Falcon markers are covered. The Ed25519 container, including its gap, is covered by Falcon. | Exact names and LF, one adjacent Ed25519 → Falcon pair, and no additional bytes after it. | No separator or trailing revision is allowed by this profile. |

The native verifier interprets the encoded signature before checking the
mathematics. Its compatibility parsing is broader than the encoding emitted
by the native signer. Consequently, “lowercase hex of bounded length with
zero fill” establishes properties of PDF storage and leaves a distinct
native encoding invariant unresolved.
[Format and limits](../utils.py#L9) ·
[Prepared and completed parsers](../utils.py#L155) ·
[PQClean API](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/clean/api.h) ·
[Native verification source](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/clean/pqclean.c)

## Method and observed results

The new tests signed the tracked 742-byte public sample once with a fresh
in-memory hybrid key pair. The signed file was created in an owned pytest
temporary directory outside the repository. The fixture retained the
public keys and captured bytes for assertions. The covered-byte cases
derive from the same baseline and make no further signing call. The tests
independently reconstruct the messages from the parsed interval endpoints,
observe both native results and assert the first Boolean of `verify_bytes()`.
Existing structural controls add coverage of malformed metadata, geometry
and final EOF. Some are parser-only synthetic inputs. Where an existing test
spies on the verification entry points, “not called” is an observed
short-circuit. It is distinct from a native false result.
[New fixture and baseline control](../tests/test_signature_integrity_boundary.py#L18) ·
[Native boundary cases](../tests/test_signature_integrity_boundary.py#L60) ·
[Structural short-circuit assertions](../tests/test_signature_pair.py#L63)

| Category and control | Bytes changed | Structural result | Native Falcon result | Hybrid result | Expected versus observed |
| --- | --- | --- | --- | --- | --- |
| Untouched public sample, one run | No | Pair accepted | True | True | Matched. Ed25519 also independently verified. |
| Public PDF text, one same-size edit | Yes | Same parsed structure | False | False | Matched. The Ed25519 message and Falcon prehash changed. Both native checks rejected. |
| Ed25519 signature field, one same-size edit | Yes | Same parsed structure | False | False | Matched. The Ed25519 message was unchanged and its signature verification failed. The outer prehash changed. The same detached Falcon signature was used. |
| Falcon ByteRange syntax and gap coverage | Yes | Rejected | Not called in paired short-circuit tests. Parser-only tests do not exercise native verification. | False in paired cases | Matched. Existing cases cover noncanonical fields and out-of-profile range boundaries. |
| Falcon `SigLength` malformed, zero, odd or out of bounds | Yes for mutation cases | Rejected | An existing control checks the original detached signature separately with the unchanged prehash and obtains True. No result is inferred for a signature parsed from rejected input. | False for full-file cases | Matched. This is a structural failure. |
| Falcon signature hex syntax or case | Yes | Rejected for invalid characters and noncanonical case | Not reached in the full-file rejection path | False for full-file cases | Matched. Parser-only grammar cases have no hybrid result. |
| Falcon detached signature bytes, native invalid-signature control | Yes | Local completed-container checks accepted | False | False | Matched. Independent Ed25519 verification still succeeded. |
| Unused Falcon padding | Yes | Rejected | Not called in the spied structural cases | False for full-file cases | Matched. First, middle and last positions covered by full-file controls. The parser-only sweep tests one nonzero substitution at each unused position in its two fixtures. |
| Delimiter/line syntax inside the gap | Yes | Rejected in synthetic containers | Not evaluated in parser-only cases | Not evaluated in parser-only cases | Matched. Covers noncanonical whitespace, inserted metadata and line endings. |
| Appended bytes and truncation | Yes | Rejected | Not called in paired short-circuit tests | False | Matched. Eight suffix and nine truncation cases, plus the real-signature append/truncate regressions. |
| Alternate native representation preserving cryptographic meaning | No variant executed | No observation | No observation | No observation | Source review only. End-to-end acceptance remains unconfirmed. |

The table reports the outcomes asserted by the specified test cases. Its
rows group related controls and can overlap. They do not form a statistical
estimate of acceptance over all mutations. Relevant assertions are in
[hybrid tests](../tests/test_hybrid.py) ·
[range parsing tests](../tests/test_container_parsing.py) ·
[completed metadata tests](../tests/test_completed_signatures.py) ·
[whole-pair tests](../tests/test_signature_pair.py).

### Raw test counts

| Selected file or test group | Passed |
| --- | ---: |
| New public-sample baseline and two covered edits | 3 |
| Existing hybrid round trips, original message coverage, document changes, mismatched keys, individual failures and tuple contracts | 26 |
| ByteRange syntax and exact-gap controls, plus the two frozen Phase 1 PDFs | 52 |
| Signature metadata limits, exact syntax, invalid hex, padding cases and custom-capacity round trips | 77 |
| Pair acceptance, trailing bytes, truncation, coverage and metadata short-circuit controls | 25 |
| **Total** | **183** |

The final focused run took **6.58 s** and exited 0. There were zero failures,
errors, skips, xfails or xpasses. Fresh canonical outputs, both frozen
Phase 1 fixtures and the selected custom-capacity round trips passed.
The complete Python and GUI suites were outside this focused run.

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider `
  tests/test_signature_integrity_boundary.py `
  tests/test_hybrid.py `
  tests/test_container_parsing.py::test_byte_range_requires_fixed_width_unsigned_decimal `
  tests/test_container_parsing.py::test_range_must_exclude_exactly_its_own_gap `
  tests/test_container_parsing.py::test_frozen_phase1_single_pair_signatures_still_verify `
  tests/test_completed_signatures.py::test_zero_odd_and_outside_capacity_lengths_are_rejected `
  tests/test_completed_signatures.py::test_falcon_maximum_comes_from_installed_implementation `
  tests/test_completed_signatures.py::test_siglength_requires_exact_unsigned_decimal_syntax `
  tests/test_completed_signatures.py::test_invalid_signature_characters_are_rejected `
  tests/test_completed_signatures.py::test_noncanonical_metadata_inside_the_gap_is_rejected `
  tests/test_completed_signatures.py::test_every_unused_falcon_padding_position_is_checked `
  tests/test_completed_signatures.py::test_real_hybrid_rejects_falcon_padding_mutations `
  tests/test_completed_signatures.py::test_real_falcon_metadata_is_rejected_without_rewriting `
  tests/test_completed_signatures.py::test_real_custom_capacity_hybrid_roundtrips `
  tests/test_signature_pair.py::test_valid_pair_has_one_ordered_adjacent_revision `
  tests/test_signature_pair.py::test_any_trailing_bytes_are_rejected_before_crypto `
  tests/test_signature_pair.py::test_truncation_never_falls_back_to_an_incomplete_pair `
  tests/test_signature_pair.py::test_pair_validation_preserves_local_revision_coverage `
  tests/test_signature_pair.py::test_completed_metadata_is_checked_before_either_crypto_layer
```

## Impact assessment

The tested edits to covered PDF content and the Ed25519 signature field
were detected. The tested metadata, padding and envelope failures were
also rejected. The source finding is a **potential representation
malleability issue for the signed artifact**. If two accepted forms were
established, the concern would be uniqueness of the outer signature
container's serialized bytes. An exact artifact digest used for retention,
deduplication or chain-of-custody could differ while the same mathematical
signature was accepted. The present audit provides no evidence of signing
different covered PDF content, obtaining private keys or forging a
signature. It also provides no proof that all final-byte changes reject.
Trusted keys and signer identity remain separate from this boundary.

## Proposed remediation for review

1. **Specify the native encoding policy.** Define the compressed detached
   encoding emitted by the pinned signer as the strict application
   profile. Use a reviewed strict decoder or native interface that
   reports exact input consumption and enforces the canonical encoding
   of the decoded signature. With a validated deterministic encoder,
   exact byte equality to its re-encoding provides a check. Require the
   declared hex count to match the full accepted canonical byte buffer
   and retain the existing exact syntax and padding checks. The native
   mathematical verification must still succeed. The algorithm, prehash,
   signed bytes and public result tuple can be preserved. Rejecting by a
   single guessed length or trimming zero bytes would confuse legitimate
   compressed outputs with encoding policy.
2. **Inventory compatibility before enforcing.** First check the two
   frozen Phase 1 fixtures, canonical outputs from the pinned writer
   and custom-capacity signatures against the proposed policy. Catalogue
   any supported legacy signatures produced by external tools. The test
   suite establishes compatibility for its fixtures under today's code.
   A stricter verifier could change the result for other on-disk
   signatures. Agree on a migration policy before changing any default.
   Any legacy verification mode should be explicit and label its
   weaker byte-canonicality guarantee. Preserve original bytes and
   verification records. A trusted full-file digest may separately
   protect the identity of a previously archived artifact.
3. **Require reviewable acceptance evidence.** For an implementation
   phase, use upstream/reference vectors for the proposed encoding,
   validate bounded consumption and exact canonical forms, and verify
   cryptographic agreement on canonical inputs across supported builds.
   Confirm that strict checks happen before hybrid acceptance, and that
   both historical fixtures, newly signed outputs, approved custom
   capacities and existing rejection cases still pass. Record any intended
   legacy compatibility change and obtain approval before modifying the
   signer or verifier.

**Thesis wording** — “Bộ kiểm tra của HybridSign xác nhận cả hai chữ ký
trên các vùng byte đã quy định và từ chối các trường hợp thay đổi đã kiểm
thử. Container Falcon ngoài cùng chứa một vùng lưu chữ ký nằm ngoài
thông điệp ký của chính nó. Các kiểm tra cấu trúc và thử nghiệm hiện có
chưa xác lập tính duy nhất của biểu diễn byte đối với toàn bộ tệp.”

## Changed files and artifact checks

- `tests/test_signature_integrity_boundary.py` adds the public-sample
  baseline and two covered-change tests. Existing tests were unedited.
- `docs/phase5-1a-signature-integrity-audit.md` records the audit and
  proposes the compatibility review.

The public sample SHA-256 matches the Phase 4C.3 reference
`2d94ba434bbbfda3ffcd78731f2e94146352e5dc7680dcd566d2ca0614a20639`.
The portable EXE and Setup hashes also match that release record. No
key material, signed fixtures, benchmark data or release binaries were
added to Git. No commit or push was made.
[Release hashes](phase4c3-final-release-review.md#release-integrity)
