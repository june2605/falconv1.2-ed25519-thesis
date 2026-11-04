# Phase 2B.4B.2: transactional signing and verified atomic publication

Implemented in `D:\Final_Thesis_GitHub` on `thesis/development`, starting from
`4208735fbd4924d9f5fbe838bf1ade28233b6c4f`. The existing Python 3.11.9 `.venv`
was used without dependency changes. The working tree was initially clean.

## API and protocol

The signing API now requires an explicit, keyword-only Falcon public-key path:

```python
sign_file(source, destination, ed_private, falcon_private, pk_falcon=falcon_public)
```

Calling with four arguments, or supplying the fifth argument positionally,
raises `TypeError`. There is no compatibility fallback, filename discovery,
or unverified signing path. The Ed25519 public key is derived from the captured
32-byte private seed. Falcon key sizes come from the installed implementation.
The final native verification establishes correspondence of the supplied
Falcon keys for this signature; it does not establish signer identity or trust.

Both existing public return tuples keep their eleven positions. Signing returns
the caller-supplied output path followed by the original ten phase timings.
`verify_file()` and its tuple contract are unchanged. Stage writes are included
in their corresponding preparation/embedding slots, but source/key capture,
public-key staging, final verification, cleanup, checks and publication are not
an end-to-end timing measurement. Replacement is deliberately excluded so no
clock call or other fallible I/O is needed after the commit operation.

The Ed25519 raw selected-byte message, Falcon's subsequent 64-byte SHAKE256
digest construction, capacities, ByteRanges and on-disk containers are unchanged.
`utils.py`, `verify.py` and the frozen Phase 1 corpus have unchanged Git-normalized
contents. Existing whole-pair, marker, metadata and padding policies remain.

## Transaction and recovery

1. Capture the source once, run unsigned-input preflight on those bytes, and
   validate paths without writing. Capture both private keys and the supplied
   Falcon public key once from regular-file handles, checking sizes before
   creating transaction artifacts. Signing never rereads the live source or keys.
2. Create an owned random working directory beside the destination. Source,
   Ed25519 placeholder, completed Ed25519 state, Falcon placeholder and public-key
   snapshots use exclusively created working files. Backend private-key captures
   remain in memory. Crypto input is always derived from the captured bytes,
   never an existing destination or a live source reopened later.
3. Create the final candidate with `tempfile.mkstemp()` in the destination
   directory. Use its original exclusive descriptor, check for short writes,
   flush, `os.fsync()` and close it. Temporary-name prefixes cannot match the
   final basename, even when the user chooses a temporary-looking output name.
4. Call the unchanged `verify_file()` on that actual staged candidate with the
   derived Ed25519 public-key snapshot and captured Falcon public-key snapshot.
   Require `result[0] is True`. A false tuple or non-boolean truthy first element
   cannot authorize publication. Empty/non-indexable results and verification
   exceptions abort the transaction too.
5. Remove all owned working files and the empty working directory before
   publication. Build the return tuple, recheck aliases against captured and
   current source/key identities and original caller paths, and require the
   resolved destination to remain the same. Check the destination fingerprint,
   parent identity and candidate fingerprint before committing.
6. Call `os.replace()` once. There is no copy/delete fallback, destination
   truncation, destination unlink, or destination backup/rollback sequence.
   Successful return performs no further filesystem cleanup or clock work.

Failures in crypto, embedding, staging, candidate creation/write/flush/fsync/
close, verification, final checks or replacement propagate. Before a successful
replace, an existing destination remains untouched by this signer; a missing
destination remains absent. A detected concurrent replacement of the destination
is preserved and causes rejection rather than being overwritten.

Cleanup attempts every recorded owned file and removes directories only with
`rmdir()`. It does not recursively remove unexpected entries or scan/delete
unrelated temporary files. Exclusive stage-name collisions never claim an
existing file. If cleanup is denied by the OS, publication is aborted; primary
errors retain their traceback and receive Python 3.11 exception notes describing
cleanup failures. Artifacts that cannot be removed remain for manual handling.
Permission errors are not hidden by chmod, retries with elevated rights, or a
non-atomic fallback. Windows destination handles denying delete sharing cause
replacement to fail while preserving the existing file.

## Exact changed files

| File | Change |
| --- | --- |
| `signing_io.py` | Owned staging/candidate lifecycle, fsync/close, cleanup, fingerprint guards and sole atomic replace; extend alias checks to captured key identities and current source identity. |
| `sign.py` | Required keyword-only Falcon public key, captured key validation, staged sequential signing, derived Ed25519 public key and final cryptographic verification before publication. |
| `app.py` | Add Falcon public-key upload for signing and pass it explicitly; use a managed upload directory with closed handles, including no pre-opened destination. |
| `demo.py` | Pass its already-generated Falcon public-key path explicitly. |
| `tests/conftest.py` | Supply the required Falcon public key in the signed-PDF fixture. |
| `tests/test_container_parsing.py` | Required signing keyword only. |
| `tests/test_hybrid.py` | Required signing keyword only. |
| `tests/test_placeholder_writing.py` | Required signing keyword only. |
| `tests/test_signature_pair.py` | Required signing keyword only. |
| `tests/test_signing_io.py` | Required signing keyword only. |
| `tests/test_transactional_signing.py` | Transaction ordering, failure injection, key snapshots, aliases, cleanup ownership, native Windows handles, custom capacities and publication guards. |
| `tests/test_signing_callers.py` | Execute real UI signing with correct/incorrect/missing Falcon public keys and one real demo iteration using a tiny disposable PDF. |
| `docs/phase2b4b2-regression.md` | This implementation, compatibility, validation and risk record. |

AST comparisons confirm the six existing test/fixture modules retain identical
assertions and purposes after removing only the new signing keyword. No previous
security assertion or expected policy has been relaxed.

## Regression execution

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Initial full baseline: **499 passed, 8 skipped** in 10.12 seconds.

Tests preceded behavior changes. The initial public-key/verification-gate run
produced **14 failures**, demonstrating the absent required API and publication
without self-verification. UI tests produced **6 failures, 2 passes** before its
signing branch was updated, including leaked uploads after errors. Additional
red runs preceded the original-path alias recheck, candidate-change guard,
removal of post-publication clock work and disjoint temporary-name prefixes.

Final full suite: **632 passed, 0 failed, 8 skipped, 0 xfailed, 0 xpassed** in
**19.31 seconds**, exit code 0.
All 499 previous passing cases remain passing; 133 new cases pass. The eight
skips are unchanged native symlink capability cases: Windows error 1314 requires
Developer Mode or symlink privilege. No elevation or environment changes were
attempted. Native hard-link and native Windows destination-sharing tests pass;
deterministic path-retargeting tests supplement, but do not replace, native
symlink integration.

Fault injection covers both crypto layers (exceptions and size-valid invalid
signatures), incorrect/invalid public keys, key-read errors, workspace and
candidate creation, partial/short writes, flush/fsync/close/fdopen errors,
verification false/nonboolean results and exceptions, disk-candidate corruption,
replacement errors, cleanup denial, unowned entries and exclusive collisions.
Tests require destination preservation, owned cleanup, closed candidate handles,
fsync before verification and exactly one publication after actual verification.
They also cover captured-key changes, captured/current aliases, destination
changes, candidate mutation after verification and Ed25519 key derivation
without adjacent public-key discovery.

Both frozen Phase 1 signatures still verify. Real new default/custom-capacity
hybrid signatures verify, including `(64, 752)`, `(80, 1024)` and `(256, 4096)`.
All fifteen original benchmark/dataset SHA256 values in `D:\Final_Thesis` match
the Phase 1 record. The demo regression creates its own directories and tiny
PDF under pytest's temporary directory; it never runs the original benchmark.

## Compatibility and residual risks

- Existing canonical signed PDFs, frozen fixtures, legitimate custom capacities
  and the cryptographic protocol remain compatible. The deliberate Python API
  break requires external signing callers to provide `pk_falcon=`; no four-argument
  fallback exists. Streamlit signing now requires that public-key upload too.
- Atomic replacement concerns visibility of the completed file on supported
  filesystems. Candidate `fsync()` is not a guarantee of power-loss durability
  for the replacement directory entry. No portable directory fsync, Windows
  write-through rename guarantee or remote-filesystem durability claim is made.
- Path/identity/fingerprint rechecks reduce observed races but are not locks,
  atomic compare-and-swap or a defense against an attacker able to change paths,
  directory/reparse targets, candidate/public-key files or metadata between
  checks, verification and replace. Use trusted directories and suitable ACLs.
  Remote filesystem errors can also have ambiguous completion semantics.
- Abrupt process death, power loss, native crashes and denied cleanup can leave
  owned artifacts. There is no automatic directory-wide scavenger or rollback
  after successful publication. Exception notes preserve cleanup diagnostics;
  the existing UI's generic exception rendering does not display those notes.
- Replacement uses the candidate's metadata/permissions, not an in-place write
  preserving all attributes, ACLs, alternate streams or other hard links to an
  old destination. Windows ACL policy and secure erasure are deferred. Upload
  private keys still exist temporarily in the existing local Streamlit workflow;
  the signing backend does not make additional private-key file copies.
- Key identity/trust, storage, dependency locking, full-file memory/disk resource
  limits, rollback detection and PDF reader interoperability remain deferred.
  Shared key-generation files and verification-branch UI cleanup are unchanged.
  Low-level file-preparation helpers remain non-transactional; callers needing
  publication guarantees must use `sign_file()`.
- The format remains custom; no CMS, PAdES or FIPS 206 compliance is claimed.

No dependencies, original datasets, historical regression records or Git history
were changed. No commit or push was performed.
