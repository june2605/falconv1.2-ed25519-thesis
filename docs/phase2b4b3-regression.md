# Phase 2B.4B.3: Streamlit upload and download hardening

Implemented in `D:\Final_Thesis_GitHub`, on `thesis/development`, starting from
`05cb7e0072460f7eed0adad49342483285a61770`. The initial working tree was clean.
Used the existing Python 3.11.9 `.venv`; no packages were installed or updated.

## Audit and changes

| Location | Inherited issue | Result |
| --- | --- | --- |
| `app.py`, verification branch, previously lines 241–250 | Three `NamedTemporaryFile(delete=False)` calls and success-only unlinking. Creation, write, key-read or verification errors could strand earlier files. | One `upload_directory()` context owns all three upload copies. `finally` cleanup runs on success and exceptions. No `delete=False` temporary files remain in the app. |
| `app.py`, signing branch | Phase 2B.4B.2 already used `TemporaryDirectory`, but cleanup diagnostics were hidden by generic exception-string handling. The UI trusted the returned live output without independently checking its download bytes. | Shared cleanup context with bounded retry and explicit failure reporting; verify a snapshot of the exact immutable bytes passed to the download widget. |
| `app.py`, key downloads, previously lines 142–148 | Open key-file handles were passed directly into Streamlit download widgets. | Read all four files into bytes and close their handles before creating any key download. Read/render failures are caught. |
| `app.py`, key-generation branch, previously lines 128–130 | Existing persistent keys were deleted before attempting generation, and errors escaped the UI. | Remove the preliminary deletion loop, catch generation errors and suppress key downloads for a failed generation in that run. The generator itself is unchanged and still writes persistent files. |
| `app.py`, errors and uploads | Raw exception strings were rendered, missing/empty input distinction was weak, and file extension filtering alone did not reject obvious non-PDF input. | Generic error categories, nonempty captured uploads, basic PDF-header validation and explicit missing-upload checks. Do not echo exception content or key material. |
| `README.md` | Instructions described the historical installer, Python 3.9+, unpinned installation and unsupported security assurances. | Document local Python 3.11 launch, observed dependency versions, Falcon public-key signing requirement, workflow, tests and operational limits. |

### Owned temporary data

Both operation branches capture browser upload bytes before creating disk
copies. Uploaded filenames are not used as filesystem paths. The signing
directory contains the source PDF, Ed25519 private seed, Falcon private/public
keys, signed output, derived Ed25519 public key and download snapshot. The
verification directory contains only its PDF and two public keys. Backend
transaction artifacts remain inside this owned operation directory.

All upload copies use `Path.write_bytes()`/`read_bytes()`, closing each handle
before signing, verification, publication, deletion or UI download. The app
passes immutable bytes to download widgets, including key downloads. The
download filename uses only the uploaded filename's basename.

`upload_directory()` uses `TemporaryDirectory` plus `try/finally`. Cleanup
finishes before success/results/download widgets are rendered. An ordinary
`OSError` during cleanup receives one immediate retry, without elevation or
unbounded waiting. If both attempts fail, the operation cannot offer a signed
download. Preserve any primary exception, annotate it with cleanup failure
information, and show a warning with the affected upload directory. Existing
backend cleanup exception notes also trigger a warning without exposing their
raw text. There is no directory-wide scavenger or deletion of user files.

Operation exceptions, including failures after writing either private-key
upload, leave no upload files when normal deletion is available. If the OS
persistently refuses deletion, files can remain: a context manager cannot
override Windows sharing permissions. Tests explicitly distinguish that limit
from ordinary failure-path cleanup rather than claiming unconditional removal.

### Signing and final download checks

The Falcon public-key upload remains mandatory and is passed as keyword-only
`pk_falcon=`. There is no filename discovery or four-argument fallback. Wrong
keys, invalid key lengths and backend errors prevent download. Ed25519's public
key is derived from the captured uploaded private seed, using the same algorithm.

After `sign_file()` returns, capture its output into bytes, write a closed
`download.pdf` snapshot, and run the unchanged strict `verify_file()` against
that snapshot with the derived Ed25519 and uploaded Falcon public keys. Only
`result[0] is True` authorizes a signed download. A partial/tampered output from
a faulty signer, a false/nonboolean verifier result, a read/verification error
or failed cleanup cannot expose that output through a download widget.
The download widget receives the same captured bytes that were checked.

Verification results similarly use the actual first boolean, never tuple
truthiness. Both successful and failed verification clean uploaded documents
and public-key copies before rendering feedback. The UI's former absolute
security wording was replaced with research-prototype and supplied-key wording.

## Modified files

- `app.py`: upload context, input checks, sanitized errors, cleanup diagnostics,
  safe key-download handles, guarded key-generation feedback, and download
  snapshot verification; remove success-only cleanup and preliminary key deletion.
- `tests/test_app_hardening.py`: new application workflow, failure-injection,
  closed-handle, cleanup ownership/scope, invalid-input and frozen-fixture tests.
- `README.md`: local setup, required public key, workflow and limitations.
- `docs/phase2b4b3-regression.md`: this record.

`sign.py`, `signing_io.py`, `verify.py`, `utils.py`, `keygen.py`, `demo.py`,
every previously tracked test, and the frozen compatibility corpus are unchanged
(checked against Git-normalized contents). Both public eleven-element return
contracts, Ed25519 → Falcon message construction, algorithms, digests, container
format, capacity rules, padding and whole-pair validation are preserved.
Phase 2B.4B.2 atomic publication remains intact. No external architecture or
key-management subsystem was introduced.

## Test execution

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Initial full baseline: **632 passed, 8 skipped** in **19.87 seconds**.

Tests preceded production behavior changes. The initial targeted UI run had
**15 failures**, demonstrating verifier-exception leaks, missing PDF checks,
download of incomplete/tampered signer output, open key-download handles and
unhandled key-generation permission errors. All previously passing tests are
preserved without changes or weakened assertions.

The application integration tests execute the actual app with simulated
Streamlit widgets, real key generation and native cryptography:

1. Generate all four keys and download closed byte payloads.
2. Upload an unsigned valid synthetic PDF and its three signing keys.
3. Sign and verify both layers before offering the PDF download.
4. Verify that download with both public keys.
5. Tamper with document content and require rejection.

Both PDF fixtures complete that workflow. Both frozen Phase 1 signatures also
pass through the actual UI verification branch. Existing custom-capacity and
all cryptographic/structural security regressions remain covered unchanged.

Fault injection covers temporary-directory creation, upload reads, early and
late writes, output reads, real Ed25519/Falcon backend failures, generic signing
and verification failures, permission errors, invalid download-verifier results,
transient/permanent cleanup denial and success/download/error widget failures.
Handle instrumentation delegates to real Windows operations and asserts closed
handles before signing, verification, replacement, deletion and download.
Missing and empty uploads, wrong keys, malformed metadata, padding mutation,
truncation and trailing bytes all reject without exposing signed output.

The permanent-denial tests intentionally demonstrate retained owned files and
visible diagnostics; they then lift the injected denial and remove only their
own fixtures. Ordinary operation/UI exceptions and successfully retried cleanup
leave no uploaded private-key artifacts. If the UI's own error renderer fails,
it may propagate a framework error, but cleanup has already run.

Final full suite: **757 passed, 0 failed, 8 skipped, 0 xfailed, 0 xpassed** in
**43.00 seconds**, exit code 0. All 632 previous passing cases remain passing;
the new module contributes 125 passing cases.

All eight skips are the unchanged native Windows symlink integration cases.
Windows returned privilege error 1314; Developer Mode or symlink privilege is
required to run them. No elevation or environment changes were attempted.
Native hard-link and Windows destination-sharing tests pass, and deterministic
link/path checks remain covered. Those checks do not replace the skipped native
symlink integration, which remains a platform-validation limitation.

All fifteen original benchmark/dataset SHA256 values in `D:\Final_Thesis` match
the Phase 1 record. No original data is used by the integration tests. The
existing demo test also remains confined to its disposable synthetic dataset.

## Compatibility and platform limits

- No signature-format or public signing/verifying API changes. Canonical legacy
  signatures, custom capacities and strict atomic signing remain compatible.
  The UI now rejects empty uploads and files without a versioned PDF header and
  newline at byte zero; permissive PDF readers may accept some files this
  conservative UI check rejects. Direct signing/verifying API behavior is unchanged.
- Header validation is not a complete PDF parser, renderer, active-content
  detector or certificate/identity validator. Signer identity and hybrid key
  ownership still require trusted external key provenance.
- Tests simulate Streamlit controls; they are application/crypto integration
  tests, not browser automation, PDF-viewer interoperability or packaged-desktop
  validation. Local Streamlit CLI options were checked in the installed version.
  CLI help failed when redirected under a legacy Windows encoding; the README
  launch uses Python `-X utf8`, which avoids that encoding failure.
- Persistent permission/sharing denial, abrupt process death, native crashes
  and power loss can leave owned temporary files. No secure erasure or in-memory
  key zeroization is claimed; browser/Streamlit buffers can retain bytes.
- Generated keys remain persistent plaintext working-directory files. The
  unchanged generator can overwrite keys and is not a transaction across four
  files. Failed regeneration can leave partial/mixed persistent keys; this phase
  suppresses same-run downloads after failure, not a future rerun's key lifecycle.
- The prototype must run locally: remote Streamlit deployment would send private
  uploads to the server. Multi-user isolation, authentication, key storage,
  dependency locking and resource limits remain deferred.
- Atomic replacement concerns visibility on supported filesystems, not power-loss
  durability. Existing path/fingerprint and verification/publication race limits
  remain; the UI's snapshot verification likewise assumes a trusted temporary
  directory and does not defeat a hostile process able to rewrite it during checks.
- The custom format has no established CMS, PAdES or FIPS 206 compliance.

No dependencies were installed, original datasets changed, or commits/pushes made.
