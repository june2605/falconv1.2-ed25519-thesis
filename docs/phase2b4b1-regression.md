# Phase 2B.4B.1: path safety, source capture and bounded construction

Implemented in `D:\Final_Thesis_GitHub` from committed baseline
`f10b15af4b310374388256c8ea3647733e857fc9` on `thesis/development`.
Scope follows the approved Phase 2B.4A design supplied in the conversation,
restricted to this incremental step. No separate 2B.4A file was present in
`docs/`. The existing `.venv` was used without installing dependencies.

## Changed files

| File | Purpose |
| --- | --- |
| `signing_io.py` | Read-only regular-file capture, observed-change detection, canonical destination validation, source/key identity protection and unsafe destination rejection. |
| `sign.py` | Use the same captured bytes for unsigned preflight and signing; validate source/key destination aliases; assemble and validate intermediate bytes in memory before the first destination write. |
| `utils.py` | Validate placeholder arguments and predicted field widths, construct only the appended trailer by known offsets, and validate signature sizes/capacity before bounded embedding. Preserve explicit in-place low-level preparation while rejecting hidden aliases through distinct paths. |
| `tests/test_signing_io.py` | Path, hard-link, symlink, captured-source, permission, key-file protection and destination-preservation regressions. |
| `tests/test_placeholder_writing.py` | Ordinary placeholder-text collisions, invalid dimensions, exact fits, one-byte overflow, bytes-like signatures and layout preservation regressions. |
| `docs/phase2b4b1-regression.md` | Record scope, compatibility, test results and deferred guarantees. |

All 395 existing cases and their test modules are unchanged. `verify.py`,
`app.py`, `demo.py`, key generation and the frozen Phase 1 corpus are unchanged.
Both public 11-element return contracts are preserved; `sign_file()` still
accepts its existing four arguments and does not require a Falcon public key.

## Implemented behavior

`capture_source()` resolves the source, requires a regular file and reads one
file handle once. Its immutable `SourceSnapshot` records the captured bytes
and file identity. Before/after handle metadata and captured length are checked
for observed changes. `sign_file()` checks reserved markers on those exact
bytes and never reopens the live source or destination for signing input.
Later external changes to the live source do not change the captured bytes.

`validate_signing_paths()` compares canonical names and filesystem identities.
It rejects source/output equivalence and hard-link aliases, and protects all
explicitly supplied key paths. The current signer supplies its two private-key
paths; the reusable helper also accepts public-key paths, tested independently.
No new public-key argument was added to the signer.

Destination symlinks/reparse points, directories, dangling links, Windows device
names and alternate-data-stream destinations are rejected. Permission/stat
errors propagate rather than being treated as evidence of distinct paths.
Distinct normal destinations are allowed, and output safety is rechecked
immediately before the final write. Existing signed-input rejection keeps its
Phase 2B.3 error precedence, including already-signed same-path inputs.

`prepare_bytes_with_placeholder()` validates integer signature types, positive
integer capacities, Ed25519's 64-byte minimum, and the ten-digit wire bounds
before allocation. Booleans are not accepted as integers. It computes the new
trailer's offsets directly from the captured prefix length and fixed field
lengths. Source bytes are never searched for a replacement target. Existing
markers for the selected algorithm are rejected to prevent target ambiguity.
Ordinary ByteRange/SigLength/Contents/zero-template text is allowed unchanged.

The file wrapper constructs all bytes before opening output. Identical
input/output arguments continue to request its legacy explicit in-place
operation, required by existing custom-capacity callers. Distinct paths that
alias the source are rejected. The public signer rejects all source/output
aliases regardless of this low-level compatibility exception.

Embedding uses validated container spans, requires exactly 64 Ed25519 bytes
or a positive Falcon length within the installed implementation maximum, and
checks both encoded length and actual Contents capacity before replacement.
Oversize signatures raise `signature.size` or `signature.capacity`; they never
expand the document. Successful embedding checks exact file length, canonical
completed metadata and unchanged ByteRange/container offsets. Safe bytes,
bytearray and memoryview signature inputs remain supported through a captured
bytes copy. Custom capacities below Falcon's maximum remain usable when the
actual signature fits.

The signer now finishes all construction and signature-capacity validation
before opening the destination. Ed25519 and Falcon intermediate states are
held in memory. This is deliberately not a temporary-file transaction or
atomic publication implementation. Ed25519's I/O timing slot now covers its
in-memory embedding work; final writing remains in Falcon's I/O slot. Existing
phase timings are not end-to-end safety/workflow measurements.

## Test execution

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Baseline: **395 passed**.

Tests were written before their production changes. The initial targeted run
demonstrated alias overwrites, source rereads, source-text replacement, invalid
dimensions and unchecked signature growth. Oversized-dimension tests were
subsequently moved to the byte-builder entry point so they do not exercise a
large allocation in the unsafe baseline file helper. Further tests preceded
the nonregular-source, Windows stream-path and hidden-helper-alias guards.

Final full suite: **499 passed, 0 failed, 8 skipped, 0 xfailed, 0 xpassed in
10.74 seconds**, exit code 0. The 395 original cases pass unchanged. The new
tests contribute 104 passes and eight capability skips.

All eight skips are native symlink integration cases: four source/destination
symlink-alias cases and four dangling/unrelated destination-link cases. Windows
returned privilege error 1314, requiring Developer Mode or symlink-creation
privilege. No elevation or environment changes were attempted. Native hard-link
tests pass; deterministic link-resolution and link-metadata branch tests also
pass. These do not replace real symlink integration, which remains to be run
in a suitably enabled Windows environment.

The suite covers changed live sources after preflight, observed mutation during
capture, private/public key aliases, read-only capture, permission failures,
existing/missing destination preservation on new validation failures, ordinary
placeholder-like PDF text, invalid dimensions, algorithm size boundaries,
exact fits, one-byte overflow, custom capacities and unchanged offsets.

Six valid default/custom prepared and embedded layouts were compared directly
with the committed baseline using fixed signature bytes and were byte-identical.
Both digest/message helper bodies and all existing parser/pair-policy bodies
are AST-identical. Frozen legacy verification and real new/custom-capacity
round trips remain covered by the unchanged existing suite. All 15 original
benchmark/dataset hashes in `D:\Final_Thesis` match the Phase 1 snapshot.

## Deferred requirements and security limits

Phase 2B.4B.2 still owns temporary-file signing stages, atomic publication,
preservation on write/fsync/replace failures, exception cleanup, and completed
cryptographic verification before publication. Its Falcon public-key API and
Streamlit/demo updates are not implemented here. No commit or push was made.

Current preservation guarantees apply to rejection by the new validation, not
arbitrary I/O failures: the final destination is still opened with `wb`, so a
failed/partial write can truncate an existing destination. The explicit
low-level in-place wrapper likewise has no atomic-write guarantee. No rollback,
backup or partial transaction was introduced to imply otherwise.

Path checks and their final recheck are not atomic against a hostile process
replacing paths, hard links or directories afterward. Metadata checks detect
observed changes during capture but are not an OS-enforced immutable snapshot.
They cannot exclude carefully concealed concurrent writes. Full-file memory
amplification and very large wire-valid allocation requests remain resource
risks. Key/identity trust, final cryptographic self-verification, existing UI
temporary-file leaks, dependency locking, rollback detection and PDF-reader
interoperability remain outside this step. No CMS, PAdES or FIPS 206 compliance
is claimed.
