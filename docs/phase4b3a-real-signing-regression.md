# Phase 4B.3A — real desktop PDF signing

## Scope and inherited baseline

Implemented in `D:\Final_Thesis_GitHub`, on `thesis/ui-demo`, starting from a
verified clean tree at `46611ad99c63871093545ca202a4d91888b6593b`. The inherited
baseline was 1570 passing Python tests, eight documented Windows symlink skips,
and 136 passing browser executions. AGENTS.md, the Phase 3 key/vault records,
Phase 4 UI/native/vault reports and current signing/verification code were reviewed.

This connects the approved three-step desktop UI to the existing managed signer.
It does not implement standalone verification UI, accounts, trusted identity,
password changes, backup/restore, a PDF renderer or a second signature engine.
The browser remains a labelled UI preview. No dependency installation, benchmark
change, repository/worktree creation, commit or push was performed.

## Architecture

```text
React: opaque document/vault/session/operation IDs and public metadata
  -> SigningBridge (nine explicitly exposed methods; native origin guard)
     -> NativeDialogs (Windows GUI thread: file Open/Save and password prompt)
     -> SigningWorker (the original single vault-owning execution thread)
        -> VaultService.require_session()
        -> SigningService (document/destination validation)
        -> vault_signing.sign_vault_document(handle, input, output)
           -> unchanged sign_with_key_material() / SigningTransaction
           -> Ed25519 -> Falcon-512 -> candidate self-verification -> os.replace()
        -> read actual saved PDF and verify_bytes() with captured public keys
     -> authoritative public operation state
```

The existing key/vault/PDF algorithms, signed-message construction, on-disk
formats and public signing/verification APIs are unchanged. In particular,
`sign_vault_document()`, `sign_with_key_material()`, `sign_file()` and both
11-element return contracts keep their previous behavior. Both frozen signatures,
custom capacities and all prior structural/padding/path tests remain in the suite.

The private managed handle stays on its issuing worker throughout authentication,
session validation and signing. `require_session()` checks the exact current
opaque IDs and calls the existing managed state validation before returning a
handle to a private owner-thread caller. The backend revalidates source, session
and protected storage; a disabled/enabled React button is not authorization.

The desktop document adapter adds a conservative fixed-local-NTFS policy to the
inherited transaction checks. It retains a checked path, file identity/revision,
SHA-256 selection fingerprint and public metadata. It opens an unsigned PDF
through a non-following Windows handle with read sharing only, checks it while
open and retains that handle throughout the core signing call. Ordinary competing
writes/deletion therefore fail while the signer recaptures the selected source.
No new cryptographic digest or PDF signed-message field is introduced.

## Native API

Protocol version remains 1. The production allowlist contains the existing six
metadata/vault methods plus exactly these three methods:

| Method | Validated input | Public result |
| --- | --- | --- |
| `choose_pdf()` | No arguments; trusted native Open dialog supplies the path privately | `{document, cancelled}`; document has `documentId`, basename `displayName`, `sizeBytes` |
| `sign_pdf(documentId, vaultId, sessionId, operationId)` | Exactly four 32-character lowercase hexadecimal IDs; native Save dialog supplies output privately | Current seven-field job snapshot; submission does not wait for signing |
| `get_signing_state(operationId?)` | Zero arguments for latest, or one valid opaque ID | Current snapshot; foreign/stale ID rejects |

The seven job fields are `operationId`, `state`, `document`, `outputName`,
`hybridKeyId`, `selfVerified`, and `errorCode`. No PDF bytes, full paths, password,
private key, encryption key, handle or timing tuple crosses the bridge. Public
metadata includes the existing public-key fields on the separate vault API.
Native exceptions become fixed error codes/messages; raw exception text is not
returned or logged. `pdfSigning=true`; `pdfVerification` and `accountRegistry`
remain false. There is no arbitrary dispatcher, Python callback or filesystem API.

Frontend validation recognizes only the exact previous two-/six-method profiles
or the new nine-method signing profile. Unknown fields/methods/capabilities and
malformed completions reject. Completed status requires literal
`selfVerified === true`, matching operation ID, output name and hybrid key ID.
Rebuild the frontend with the current shell; older strict frontends reject the
extended profile instead of silently accepting it.

## Operation lifecycle and timeout behavior

```text
idle -> preflight -> ready (native Save dialog)
ready -> cancelled (dialog cancelled; no engine admitted)
ready -> queued -> running -> completed
ready / queued / pre-engine validation -> failed
running after engine entry -> outcome-uncertain on any exception
```

One selected document and one latest job are retained in process memory. The
existing bounded FIFO remains capacity eight, but only one signing operation is
admitted at a time. The bridge reserves it before showing Save. Duplicate requests
with the same ID and arguments return its current state without another dialog or
signing call. Different arguments under the same ID reject. A different job while
active rejects. The UI also blocks duplicate clicks and preserves status across
route changes.

Signing uses an internally queued fixed enum command and never calls
`Future.result(timeout)` for that command. Its internal deadline is infinite;
elapsed wall time cannot cancel or misclassify a publication. Short selection and
session preflight requests retain the existing bounded worker deadline. These
checks cannot publish a PDF. Status reads access only a locked public record,
independently of the busy execution queue. Frontend status reads are bounded to
two seconds, at most one at a time, polled every 200 ms while active/uncertain.
Human file/password dialogs have no artificial JavaScript deadline.

React creates the operation ID before submission. A lost/malformed response causes
read-only reconciliation of that same ID, never automatic resubmission. A status
read timeout does not declare cancellation or absence of output. An explicit
pre-admission error remains recoverable. A dropped reply after enqueue cannot
change a running job to failed. Terminal engine failures are conservatively
uncertain because a managed lock-release/storage error can occur after replacement.

Normal window close is refused while ready/queued/running, with a native notice.
Worker shutdown returns false without setting the stop flag for an active job.
Vault create/unlock/lock and PDF reselection reject while signing is active;
read-only vault state uses the last confirmed public cache. Once settled, the
normal owner-thread shutdown locks managed access and stops owned threads.
There is no cancellation API after queueing.

This bounds admission and retained state, **not engine runtime**. A stuck native
I/O call cannot safely be forcibly killed in the owning Python thread. Forced
termination or power failure can lose the in-memory record and leave an uncertain
outcome or temporary PDFs. There is no persistent job journal or cross-process
exactly-once guarantee. After restart, inspect the chosen output with the existing
Python verifier before explicitly retrying. Only the latest operation is retained;
old IDs cease to be known when a new operation replaces that record.

## File and key security

- Selection requires `.pdf`, nonempty bounded input (50 MiB), a supported header,
  `startxref`/terminal EOF envelope and no inherited reserved-marker collisions.
  This is not complete PDF parsing, rendering, active-content validation or a
  guarantee that every malformed PDF is detected.
- Input and output use the conservative fixed-local-NTFS, no link/reparse/hardlink
  path policy. Ordinary PDF files need not have vault DACLs. Vault storage keeps
  the existing stricter ACL, cooperative locking and revision policy.
- Windows Save has `OverwritePrompt=True`. A private fingerprint is captured at
  FileOk and checked again before entering the signer. No overwrite is inferred
  merely from a suggested filename. Cancelling the dialog queues nothing.
- Output must be a PDF filename. Replacing an existing file additionally requires
  its `%PDF-` header. This conservatively refuses encrypted vaults or raw key
  material renamed `.pdf`, as well as arbitrary unrelated files. It does not
  recognize all possible secret-bearing files; users must still choose an
  appropriate trusted output location.
- Source, active vault and lock-sidecar aliases reject. The unchanged managed
  signer protects its storage paths and repeats relevant checks immediately
  before publication. Destination revision/candidate identity checks and the sole
  `os.replace()` commit remain intact; there is no copy/delete fallback.
- The inherited transaction captures source bytes, uses owned temporary PDFs,
  checks capacities, flushes/fsyncs/closes the candidate, verifies both layers,
  cleans work files and atomically replaces the destination. Exceptions before
  publication preserve an existing destination. Ordinary failure cleanup owns
  only its own artifacts. No private-key temporary files are added.
- After return, Python checks the tuple contract and rereads the actual saved
  file under a read-sharing handle. It verifies with captured public keys and
  requires `result[0] is True` before marking completed. Postpublication failures
  never produce a fake success or an assertion that no file exists.

Atomic replacement is not a guarantee of power-loss durability. Noncooperating
filesystem changes between checks/replace and later changes to a saved file remain
possible; no hostile-filesystem compare-and-swap guarantee is claimed. PDF
intermediates are plaintext documents. Temporary-file cleanup and reference/control
clearing do not guarantee secure deletion or Python/.NET memory zeroization.
Compromised same-user processes/malware, OS paging and stolen unlocked process
memory remain outside this prototype's protection.

## Test-first work and Windows evidence

New regressions were added before production behavior. Initial failures were the
absent signing modules and absent functional native Sign PDF workflow. Tests then
exercised the real managed engine, not a replacement cryptographic implementation.
An additional hardlink test was corrected to expect rejection during preflight
before Save: adding a second link also invalidates the selected source's storage
profile. Its source/output preservation assertions remain.

`tests/test_desktop_signing.py` covers actual signing with the authenticated public
pair, source/vault preservation, locked/stale sessions, invalid IDs/PDF envelopes,
already-signed input, changed selection, Open/Save cancellation, protected
destinations, confirmed existing-PDF replacement, native approval revision changes,
source handle sharing, hardlink aliases, fsync/verifier/replace faults, postpublish
verification failure, duplicate jobs, conflicting operations, thread ownership,
safe shutdown refusal, lost admission reply and a 5.2-second real signing job.
Raw diagnostic text is checked absent from public responses. Existing core tests
continue to cover legacy fixtures, capacities, padding and transactional failures.

Eight new Playwright scenarios run at both 1366×768 and 1920×1080 (16 executions).
They check the three steps, exact four-ID request, confirmed completion, locked
session, picker cancellation, lost reply reconciliation, uncertain publication,
rapid repeated clicks, route persistence, blocked vault operations, preflight
recovery and malformed completion. Existing browser-preview and six-method vault
tests retain their previous security purposes.

`tests/test_desktop_signing_native.py` starts two actual Windows/WebView2
applications. The first creates a disposable vault; the second reopens it without
generating another pair. Both use actual masked WinForms password controls and the
real authenticated vault worker, navigate Sign Document, select a nonsensitive
generated PDF and sign it. Native file acceptance is supplied through a Python-only
test seam on the GUI thread; this adds no production/debug bridge. Existing real
vault picker opening/cancellation is also exercised. Human PDF picker acceptance
and overwrite-confirmation interaction remain manual checks.

For each process the test independently reads and verifies the saved PDF with the
existing Python verifier and captured public pair, rejects altered signed bytes,
compares original PDF/encrypted-vault bytes, checks directory additions and
instruments stage/candidate writes for raw/hex private keys and test password.
Only the expected signed PDF is added. An artificial 1.5-second wrapper delay
makes an active job observable; a real native close event is refused, then actual
signing completes. The close-notice handler is acknowledged by a GUI-thread test
double so automated execution does not stall on a modal notice. Both processes
release managed access and stop owned threads on normal final close.

Public machine-readable evidence and reviewed owned-window captures:

- [Creator evidence](../frontend/qa/phase4b3a/vault-create-checks.json)
- [Reopener evidence](../frontend/qa/phase4b3a/vault-reopen-checks.json)
- [Review before native Save](../frontend/qa/phase4b3a/signing-review.png)
- [Confirmed completed signing](../frontend/qa/phase4b3a/signing-completed.png)
- [Current native shell checks](../frontend/qa/phase4b3a/native-checks.json)

The evidence contains only disposable public keys/IDs and public outcomes, not
passwords, private keys, source PDFs or full paths. Historical screenshots and
regression evidence are retained unchanged; new current evidence lives in
`frontend/qa/phase4b3a/`.

## Exact validation results

Final full-suite results are recorded below after execution. Commands use the
existing environment and installed Microsoft Edge, with no package installation:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -rs -p no:cacheprovider
Set-Location frontend
npm run typecheck
npm run build
npm run test:e2e
```

| Check | Result |
| --- | --- |
| Full Python suite, including the real native GUI tests | **1597 passed, 8 skipped in 186.47 s**; 0 failed, 0 xfailed, 0 xpassed |
| Full frontend suite | **152 passed (2.0 min)**; 0 failed/skipped/expected failures/unexpected passes |
| TypeScript check (`npm run typecheck`, also invoked by build) | Passed, exit 0 |
| Production build (`npm run build`) | Passed, exit 0 |
| `git diff --check` | Passed |

The increase is 26 Python service/worker/bridge cases plus one two-process native
GUI case, and eight frontend scenarios at two viewports. All 1570 prior Python
test purposes and all 136 prior browser executions remain green. The initial
focused two-process signing GUI run also passed independently in 18.16 seconds.
Each final recorded signed PDF is 5242 bytes (the generated nonsensitive fixture
plus inherited signature containers); creator/reopener public keys and hybrid ID
match, with generated-pair counts respectively one and zero.

The eight inherited skips are the same Windows symlink-privilege cases; they do
not skip real GUI, hardlink, PDF signing or vault operations. Platform evidence is
Windows x64, Python 3.11.9, pqcrypto 0.3.4, PyNaCl 1.6.2, cryptography 50.0.2,
pywebview 6.2.1/pythonnet 3.2.1, Node 26.13.0/npm 11.20.0 and installed Edge 156.
No Linux/macOS, network/removable volume, physical high-DPI/multi-monitor,
screen-reader, native-hang or power-failure validation is claimed.

## Changed-file manifest

| File(s) | Change |
| --- | --- |
| `desktop/pdf_io.py` | Bounded PDF capture, Windows read sharing, selection fingerprint and private native output-approval token |
| `desktop/signing_service.py` | Owner-thread document/session/destination validation, unchanged managed signer call and actual saved-file verification |
| `desktop/signing_worker.py` | One asynchronous signing lifecycle on the existing worker, idempotent admission, independent public status and shutdown refusal |
| `desktop/signing_bridge.py` | Three explicit signing methods, native dialogs, opaque-ID validation, busy admission and public metadata/status |
| `desktop/worker.py` | Three fixed internal PDF enum commands; short request semantics unchanged |
| `desktop/vault_service.py` | Private owner-thread `require_session()` validation |
| `desktop/contracts.py` | Signing capability, fixed error messages and typed public document/job shapes |
| `desktop/dialogs.py` | GUI-owned PDF Open/Save, native overwrite approval and active-close notice |
| `desktop/launcher.py` | Production signing bridge/worker and active-operation close refusal |
| `frontend/src/native/signing.tsx` | Strict public contract, route-persistent document/job, duplicate prevention and read-only reconciliation |
| `frontend/src/native/desktop.ts` | Exact nine-method signing capability profile alongside existing profiles |
| `frontend/src/native/vault.tsx`, `main.tsx` | Provider wiring and conflicting vault-operation inhibition |
| `frontend/src/pages/NativeSignDocument.tsx`, `SignDocument.tsx` | Real three-step desktop signing and confirmed result; separate unchanged demo workflow |
| `frontend/src/App.tsx`, `pages/Dashboard.tsx`, `pages/Settings.tsx`, `components/NativeVault.tsx`, `components/VaultDialogs.tsx` | Accurate signing availability, preview separation and limitations text |
| `tests/test_desktop_signing.py` | New worker/service/bridge real-engine and fault regressions |
| `tests/test_desktop_signing_native.py`, `desktop_vault_probe.py` | Two-process actual Windows signing, independent disk checks, cleanup/privacy and close behavior |
| `tests/test_desktop_native.py`, `desktop_native_probe.py` | Intentional nine-method capability assertions and lazy PDF-import boundary; original guard/navigation assertions retained |
| `frontend/tests/native-signing.spec.ts` | Eight frontend scenarios at two viewports |
| `frontend/qa/phase4b3a/` | New public GUI screenshots and JSON evidence |
| `README.md`, `frontend/README.md` | Current native signing workflow, setup, lifecycle and limits |
| `docs/phase4b3a-real-signing-regression.md` | This report |

Cryptographic modules, dependency manifests/lockfiles, benchmark fixtures and
previous regression tests outside the explicitly updated native capability/probe
assertions are unchanged.

## Manual reproduction

1. From the repository's existing environment, run `npm run build` in `frontend`,
   then `.\.venv\Scripts\python.exe -m desktop.launcher` at repository root.
   No Vite development server is needed by the native application.
2. Create a disposable encrypted vault on trusted fixed local NTFS; enter a new
   test-only password in the masked native dialog. Unlock it. Do not use sensitive
   documents or credentials for a screenshot/demo session.
3. On Sign Document choose a small unsigned PDF through Windows Open. Confirm
   its name/size, select the unlocked vault and continue to review. Click Sign PDF,
   choose a different PDF output and accept Save. Try cancelling Save first;
   there should be no queued signing job or completed result.
4. Wait for Signed PDF saved, actual filename, Ed25519 + Falcon-512, hybrid key
   ID and completed self-verification. Independently verify the file using
   `verify_file_with_public_keys()` with the authenticated vault's public keys;
   require tuple element zero to be literal `True`. Change a signed byte in a
   separate disposable copy and verify rejection. Preserve the original input.
5. Repeat with a disposable existing PDF and inspect the Windows overwrite prompt.
   Cancel confirmation, then explicitly accept in a later attempt. Try source,
   vault and lock-file destinations: protected files must remain unchanged.
6. During an observable active operation, try a second Sign, vault Lock and normal
   window Close. No second operation or cancellation should occur. Reconcile any
   uncertain status rather than automatically retrying.
7. Close normally after settling, reopen the original vault and confirm the same
   hybrid ID. Browser mode must still display UI PREVIEW and demo-only results;
   Verify Signature remains an example workflow in this phase.

## Remaining security scope

This proves local signing under the recorded test conditions. It does not prove a
trusted signer identity, signing authorization by an account, trusted signing time,
revocation/registry status, legal certification, CMS/PAdES/PDF-reader compatibility,
FIPS compliance or a particular Falcon revision beyond the implementation
provenance already documented. No such metadata is appended to signed PDFs.
It does not protect a compromised frontend/native process or malicious same-user
software, nor offer guaranteed secret zeroization. The existing cooperative-lock,
ACL, vault rollback/offline-guessing, custom-format and filesystem-race limitations
remain. Standalone verification UI and trusted identity are separate future work.
