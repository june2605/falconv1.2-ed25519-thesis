# Phase 2B.3: complete hybrid signature-pair verification

Implemented on 2026-11-05 (Asia/Bangkok) in `D:\Final_Thesis_GitHub`, starting
from `c4c968bb91fc2bdb55af9e184d07a02cfbc4d471` on `thesis/development`.
The existing `.venv` was used; no packages were installed or upgraded.

## Scope and modified files

| File | Change |
| --- | --- |
| `utils.py` | Add reserved marker names, unsigned-input preflight, the immutable `SignaturePair`, and whole-file `parse_signature_pair()` validation. Existing local parsing, metadata, digest and writer functions are unchanged. |
| `verify.py` | Parse both completed signatures as one pair before either hash/message helper or crypto verifier runs. Extract signatures from that validated pair's bounded spans rather than independently selecting the last occurrence of each type. |
| `sign.py` | Reject already-signed or marker-colliding input before opening keys, preparing placeholders or touching output. |
| `tests/test_container_parsing.py` | Intentionally revise the old repeated-signing success test to require rejection and unchanged input. Other local-parser tests remain unchanged. |
| `tests/test_signature_pair.py` | Add pair layout, framing, collisions, truncation, pre-crypto rejection, genuine-signature adversarial controls, and signer preflight regressions. |
| `docs/phase2b3-regression.md` | Record the policy, compatibility change, tests and residual risks. |

## Complete-pair policy

`parse_signature_pair()` requires exactly one occurrence of each of the four
reserved marker names in the entire original byte string. It then applies
the existing strict completed-container validators to both signatures.

The Ed25519 container must precede the Falcon container, and Ed25519's complete
end marker must end exactly where Falcon's start marker begins. Falcon's
complete end marker, including its final LF, must end at file EOF. There is
no permitted separator or suffix, even a space, CRLF, NUL, PDF update, extra
EOF marker or additional signature. Missing, duplicated, nested, crossing,
reordered and interleaved containers are rejected. Invalid later records never
cause fallback to an earlier signature pair.

The unchanged local ByteRange rules require each signed revision to end at
its own container boundary. Their first interval begins at byte zero and ends
at the local SigLength field. With adjacency enforced, Falcon's first interval
therefore includes the entire Ed25519 container. Ed25519 still covers only its
first-state revision. Custom Contents capacities remain derived from the
actual fields, with no new capacity restriction.

Validation errors use existing `SignatureFormatError(ValueError)` behavior
plus `pair.markers`, `pair.order`, `pair.adjacency`, `pair.trailing`, and
`input.reserved_marker` codes. Malformed input returns the public verifier's
11-element tuple beginning with `False`, before either crypto layer runs.
Shared pair-validation time is charged to the existing Ed25519 parse slot;
the Falcon parse slot measures its signature decoding. Tuple ordering and
the AND requirement for cryptographic verification are unchanged.

## Conservative reserved-marker policy

The following case-sensitive ASCII byte sequences are reserved anywhere:

```text
%%ED25519_PQ_SIG_START
%%ED25519_PQ_SIG_END
%%FALCON_PQ_SIG_START
%%FALCON_PQ_SIG_END
```

Reservation does not require a following LF. Bare names, CRLF forms and names
inside longer text such as `%%ED25519_PQ_SIG_START_EXAMPLE` count as collisions.
For signed files, each name must appear exactly once at its canonical container
position; local grammar still requires the exact complete markers with LF.
For unsigned signing input, no reserved name may appear at all.

This intentionally rejects otherwise valid PDF content containing literal
reserved text, even inside a harmless text stream or comment. The custom
format does not provide an escaping or explicit framing mechanism to resolve
that ambiguity. The code does not parse PDF semantics, normalize bytes,
rewrite metadata or strip old signatures to evade the policy.

## Regression execution

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

- Initial full baseline: **294 passed**.
- Before production edits, the targeted pair/container tests produced
  **83 failed, 116 passed**. This demonstrated absent pair validation,
  crypto calls on malformed structures, acceptance of genuine separated or
  repeated signatures, and missing signer preflight rejection.
- Final full suite: **395 passed in 9.21 seconds**, exit code 0, with no
  failures, xfails, xpasses or skips.

The result comprises 292 unrelated previous cases, the two explicitly revised
repeated-signing cases, and 101 new cases. Both frozen Phase 1 signed PDFs still
verify. New signing, valid custom capacities, independent signature-layer
failures, all completed-metadata and padding checks, and UI behavior pass.

The new tests independently construct and genuinely sign separated pairs,
repeated pairs and marker-colliding PDF content. They verify native signature
validity before expecting policy rejection. Other synthetic local controls
exercise structural failures without claiming cryptographic validity.
Spies prove malformed layouts and completed metadata are rejected before
either crypto verifier or message/digest helper is called. Signer tests cover
existing output preservation, missing output, and same-path repeat rejection.
Truncated repeated pairs are rejected without fallback.

All prior utility function bodies, including both message/digest helpers and
placeholder preparation/embedding, were checked against the baseline AST and
are unchanged. Unrelated regression modules and the frozen corpus are unchanged.
All 15 original benchmark/dataset hashes in `D:\Final_Thesis` still match the
Phase 1 snapshot. Historical Phase 1/2 records and project provenance were left
unchanged. No commit or push was performed.

## Compatibility and residual risks

Canonical single-pair legacy files, frozen fixtures and legitimate custom
capacities remain supported. Repeatedly signed files, separated pairs,
additional revisions and reserved-name collisions are now intentionally
rejected, including some files whose signatures are mathematically valid.
Producing another signature requires a trusted unsigned source; existing files
are never automatically stripped or repaired. Low-level local parsers still
support intermediate states and indexed containers; they do not establish
whole-file validity. Callers must use `verify_file()` or whole-pair validation.

The signing preflight is not an atomic input snapshot: the source is read again
by the inherited writer and could change between those operations. Writer
capacity checks, global zero-placeholder replacement, atomic output and failure
cleanup remain deferred. No source or output atomicity guarantee is added.
Key storage, identity/key-pair trust, dependency locking, memory usage and
remaining broad crypto error handling are unchanged.

Truncation within the required pair is rejected. A stateless verifier still
cannot distinguish a separately presented older valid single-pair document
from the latest version; rollback detection needs external trusted state.
The format remains custom. CMS, PAdES, FIPS 206 compliance and PDF-reader
interoperability have not been established.
