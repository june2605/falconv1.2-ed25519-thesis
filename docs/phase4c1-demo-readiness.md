# Phase 4C.1 — desktop demo readiness and QA

## Starting point and scope

Workspace `D:\Final_Thesis_GitHub`, branch `thesis/ui-demo`, clean HEAD
`c518598824e22759be508842a3d9a6410c29e188` were confirmed before editing.
Reviewed AGENTS.md, the Phase 3 key/vault/provenance records, Phase 4 UI/native
regression records and current desktop, signing, verification and UI boundaries.
The inherited baseline is 1633 Python passes / eight Windows symlink skips,
258 frontend passes and a successful TypeScript check/production build.

This phase adds demonstration assets, complete graphical QA and one confirmed
UI-state correction. It does not redesign screens, implement another signer,
change bridge methods, ownership, permissions, cryptographic algorithms, signed
messages, PDF/vault formats or public return contracts. No dependencies were
installed, EXE packaged, repository/worktree created, history changed, commit
made or push performed. Benchmark datasets and research results are untouched.

## Feature readiness matrix

“Tested” below means the recorded research-prototype conditions, not production
certification. Automated native interaction is not a human acceptance session.

| Feature | Readiness / evidence | Practical limit |
| --- | --- | --- |
| Launch built desktop | Actual Windows/WebView2 startup; restricted static server and bridge tested | Requires the existing supported Windows/runtime/environment and a built frontend |
| Generate hybrid keys | GUI creates one original Ed25519 + Falcon-512 pair in memory | No certified entropy/build audit or hardware key protection |
| Encrypted vault | Real GUI create, unlock, wrong-password retry, cancel and lock | Fixed-local-NTFS and restrictive ACL policy; no automatic permission repair |
| Public metadata / Hybrid Key ID | GUI public-details inspection; exact ID and public-key digest survive restart | An ID and vault authentication do not establish trusted signer identity |
| PDF signing | Actual native Open/Save, real signer, independent saved-file verification | Custom format; PDF contents are not rendered in the application |
| Existing output | Actual native overwrite rejection preserves predecessor; explicit Yes permits replacement | Choose an appropriate trusted output location; final race/power-loss limits remain |
| Hybrid verification | Real matching keys → VALID; edited copy/wrong keys/corrupted PDF → INVALID | Result describes selected bytes under selected keys, not ongoing file surveillance |
| Public verification while locked | Actual authenticated public snapshot still verifies after Lock | Snapshot provenance is labelled; no private signing authority is retained |
| Restart | New process starts with no unlocked vault, reselects/unlocks original and retains its ID | Vault catalogue and operation history are not persisted |
| Five screens / themes | Actual native light/dark captures plus full browser accessibility/layout tests | Human screen-reader and mixed-DPI monitor checks remain |
| Sidebar / ID controls / footers | Existing native four-state acceptance and browser dynamic-resize suites retained | Auto follows pointer/focus; Pin supplies persistent expansion |
| Active operations | Real duplicate prevention, busy Lock rejection and refused normal Close; existing worker/fault tests | No forced cancellation of an admitted native operation |
| Lost replies / unexpected errors | Existing service fault injection and browser reconciliation/uncertainty tests | No persistent job journal or crash-proof exactly-once execution |
| Password recovery / backup UI | Unavailable, explicitly disabled | Not implemented in this phase; do not promise recovery without key material |
| Accounts, trusted registry, timestamps, CMS/PAdES | Not implemented / not established | No compliance or legal-identity claim |

## Complete graphical journey and evidence

`tests/test_desktop_demo.py` launches **two separate real application processes**
using the production build, launcher, restricted bridge and original worker.
It uses fresh disposable credentials through stdin memory, never argv, environment
variables, JavaScript or report files. Test-control repr is redacted. Passwords
are entered into the actual, initially empty, masked native controls on their GUI
thread. Key generation, unlock, signing and locking assert original worker ownership.

Unlike earlier acceptance seams, this test drives the **actual Windows file
pickers**: native keyboard events enter public test filenames, native button
clicks accept Open/Save, and descendant Yes/No buttons handle overwrite prompts.
The driver validates foreground ownership, returned paths and decisions. It never
substitutes an accepted filename or changes production permissions/dialog policy.
This automation is tailored to the tested English Windows dialogs; human and
other-locale checks are still listed below.
The real-GUI tests require an unlocked interactive Windows desktop and foreground
window access; they are not headless CI evidence. Avoid competing keyboard/mouse
input while native automation is running.

The creator journey exercises:

1. Launch with no unlocked keys; open Key Vault.
2. Cancel native password creation, then create a new 2416-byte encrypted vault.
3. Reject a wrong password; Try Again uses a fresh masked prompt and the same
   validated selection, with no second file picker or generated key pair.
4. Unlock and inspect authenticated public metadata and the full public-key ID.
5. Visit all five screens in both themes with no horizontal overflow.
6. Cancel unsigned-PDF Open, then select the generated public sample and review.
7. Reject overwrite and cancel Save; existing output and source remain unchanged.
8. Confirm overwrite, submit duplicate clicks and observe exactly one signing
   engine call. Attempt Lock and normal Close during an observable active job;
   Lock rejects BUSY and the actual native close notice refuses shutdown.
9. Complete actual signing and independently verify the saved file from disk.
10. Choose a corrupted new signing input: the prior saved-success display clears.
11. Select the signed PDF and authenticated public keys; confirm HYBRID VALID.
12. Cancel another PDF selection: the old VALID clears.
13. Modify a separate copy (`APPROVED` → `REJECTED`, eight ASCII bytes each),
    preserving the original. The direct verifier and real GUI reject it.
14. Reject corrupted PDF bytes, wrong public keys and a malformed encrypted-vault
    source; clear the invalid source and recover through explicit selection.
15. Lock the vault, reject an obsolete session, cancel a password prompt and
    verify the original signed PDF again using only the existing public snapshot.
16. Close normally and check owned thread cleanup.

A second process confirms no unlocked vault/session is restored, opens the
original encrypted file, unlocks it through the actual native dialogs, and checks
the **same exact hybrid ID and public-key digest**, zero new key generations and
successful verification of the original signed output. Its final normal close
locks the recovered handle on the worker.

The primary vault is generated once; independently generated wrong/invalid-vault
fixtures are deliberately separate negative-test inputs, not recovery fallbacks.
Vault and PDF-stage writes are instrumented for raw/hex private fields and the
disposable password. The demo directory inventory admits only expected files and
the persistent lock sidecar; source and negative fixtures retain their hashes.
These checks do not imply that Python/native memory, paging or system dumps are
securely erased or universally monitored.

Public machine-readable records and important screens:

- [Creator journey](../frontend/qa/phase4c1/create-checks.json)
- [Fresh-process reopening](../frontend/qa/phase4c1/reopen-checks.json)
- [Created locked](../frontend/qa/phase4c1/created-locked.png)
- [Unlocked public metadata](../frontend/qa/phase4c1/create-public-details.png)
- [Review before signing](../frontend/qa/phase4c1/sign-review.png)
- [Actual saved, self-verified output](../frontend/qa/phase4c1/sign-completed.png)
- [Matching-key VALID](../frontend/qa/phase4c1/verify-valid.png)
- [Modified-copy INVALID](../frontend/qa/phase4c1/verify-tampered.png)
- [Public verification after Lock](../frontend/qa/phase4c1/locked-public-valid.png)
- [Fresh process has no unlocked vault](../frontend/qa/phase4c1/reopen-no-unlocked-vault.png)
- [Light/dark five-screen captures](../frontend/qa/phase4c1/)
- [Current four-window-state acceptance](../frontend/qa/phase4c1/window-states/)

Screenshots capture owned application windows and public metadata, not plaintext
passwords/private keys or personal documents. No real user vault or signed private
document is included. The new journey runs at the default window size; the
existing real WebView2 test separately exercises default, maximized, restored and
minimum windows. The full suite runs both. Copied current window-state evidence
is separate from the preserved historical QA images.

## Confirmed problem and correction

`NativeSigningProvider.choose()` previously cleared the selected document on an
error but retained the prior completed job. Consequently, a failed new selection
could leave **Signed PDF saved** visible, disconnected from the new input state.
It also retained the old success while a new picker was pending or cancelled.

Four new Playwright cases first failed against that behavior. The correction
clears the visible old job and its UI operation reference when a new selection
attempt begins, using the existing generation guard against late responses.
The previous backend operation record and saved PDF are not deleted or rewritten.
Cancellation may preserve the previous safe document selection, but cannot carry
forward the old saved-success panel. Active/uncertain jobs still block new
selection; admission, reconciliation and uncertainty semantics are unchanged.
The new cases cover rejection, cancellation, malformed replies and a pending
chooser, with no automatic second signing call or native-diagnostic disclosure.

The native driver also encountered automation issues: synchronous SendKeys on
the owning modal thread, prefilling versus committing native filename controls,
nested confirmation button IDs, and ambiguous text matching between an accordion
heading and its inner Choose PDF button. These were corrected in the **private
test driver**, using asynchronous native input, actual buttons and accessible-name
precedence. Production dialog/overwrite/security policy was not weakened.

Full-suite runs also exposed native test timing races. The new driver now waits
for completed dialogs, focus-return state refresh and a **new** verification
operation ID, rather than accepting a preceding result with the same heading.
The inherited `desktop_vault_probe.py` likewise waits for a stable enabled button
before issuing a synthetic click. Its earlier click could hit a still-enabled
old React frame during a focus-triggered refresh and be ignored by the existing
operation gate. All original authentication, lock and stale-session assertions
remain. These are test-driver corrections; no production admission or locking
behavior was changed.

## Demo preparation

Use the existing environment; no dependency installation is needed in this
workspace. Before presentation day, build and validate once:

```powershell
Set-Location D:\Final_Thesis_GitHub\frontend
npm run typecheck
npm run build
Set-Location ..
.\.venv\Scripts\python.exe -B -m desktop.launcher
```

1. Use an existing trusted, user-owned folder on a fixed local NTFS drive, such
   as `D:\HybridSignDemo`. Avoid USB/network/OneDrive destinations and inherited
   foreign/broad vault permissions. Do not weaken ACLs to make a demo work.
2. Copy [sample-unsigned.pdf](../demo_assets/sample-unsigned.pdf) into that folder
   with Explorer. It is a generated 742-byte, single-page ASCII PDF containing
   `Decision: APPROVED`, with validated xref offsets and stream length. It contains
   no personal data or secrets; it is unrelated to original benchmark datasets.
3. Use fresh names such as `presentation-01.hvault`, `sample-signed.pdf` and
   `sample-tampered.pdf`. Keep vaults and actual outputs outside this repository.
   Existing vault filenames reject; choose a fresh name rather than deleting an
   old vault. Vault/sidecar and `demo-work/` ignore rules are additional Git hygiene,
   not secret detection. Never stage actual credentials or private material.
4. Choose and rehearse a disposable password meeting the native creation policy
   (15+ characters). Do not put it in this document, a shortcut, argv, environment,
   screen recording, slide or source code. Enter it only in the native dialog.
5. Create an Explorer shortcut (right-click Desktop → New → Shortcut) targeting
   `"D:\Final_Thesis_GitHub\.venv\Scripts\pythonw.exe" -B -m desktop.launcher`.
   Set **Start in** to `D:\Final_Thesis_GitHub`. Validate it before the presentation.
   This is a source-environment shortcut, not EXE packaging. Preflight with the
   console launcher first so missing-runtime/build errors are observable.
6. Rehearse Explorer Copy/Rename and Notepad Open/Save for the modified copy.
   Enable filename extensions. Open a copy of the **signed** PDF in Notepad,
   replace only `APPROVED` with `REJECTED`, and save as the same `.pdf` in
   ASCII-compatible UTF-8. Keep the original signed PDF untouched. Native
   verification of the controlled byte edit is automated; a human Notepad
   rehearsal on the presentation machine remains required.
7. Start in Light mode, choose a comfortable window size, and Pin the sidebar
   if persistent navigation is preferable. Maximize first if the default window
   is below the existing Pin width threshold. Check the projector, native dialog
   placement and readable full-ID controls. No PowerShell is needed on stage.

## 3–5 minute live script

| Time | Action / expected screen | Explanation |
| --- | --- | --- |
| 0:00–0:20 | Open the shortcut; Dashboard shows Desktop Connected | “This is a local research prototype. Private signing operations stay on this computer.” |
| 0:20–1:10 | Key Vault → Create Vault, fresh filename, native password/confirmation → Locked; Unlock the same file → Unlocked | “Both key pairs are generated in memory. Private material is encrypted with password-derived Argon2id and AES-256-GCM storage.” |
| 1:10–1:25 | Inspect Hybrid Key ID / Public key details | “This identifies the public-key pair. It does not certify a person's legal identity.” |
| 1:25–2:05 | Sign Document → sample-unsigned.pdf → Continue to review → Sign PDF → new output → Signed PDF saved | “Ed25519 signs first; Falcon-512 covers the subsequent state containing that signature. Both layers are checked before completed publication.” |
| 2:05–2:35 | Show the output in Explorer. Verify Signature → signed output → Use authenticated vault → Verify PDF → HYBRID VALID | “The actual saved bytes verify under this public-key pair.” |
| 2:35–3:20 | Explorer copies signed output to sample-tampered.pdf; Notepad replaces APPROVED with REJECTED and saves | “We change the document copy, not the keys or original signed file.” |
| 3:20–3:40 | Select the edited copy; same public keys → Verify PDF → HYBRID INVALID | “The controlled document modification is detected. Wrong keys can also cause INVALID; this demo deliberately kept the keys unchanged.” |
| 3:40–4:05 | Lock on Key Vault. Reselect original signed PDF and verify again → VALID | “Verification uses public keys and still works when private signing access is locked.” |
| 4:05–4:45 | Close, reopen shortcut → no unlocked vault; Unlock the original file; show unchanged full ID | “The original pair is recovered after restart. No replacement key is generated on unlock.” |
| 4:45–5:00 | State the limitations below | “No trusted signer identity or timestamp is established. This custom format is not claimed to be CMS/PAdES or production-certified.” |

Keep the native window open until an operation settles. If communication is
uncertain, reconcile that same operation and inspect/verify the chosen output;
do not click repeatedly or announce success. On an error, show the real result
and use the rehearsed recovery path. If the disposable password is lost, there is
no recovery claim: an explicitly new demo vault requires repeating signing and
matching-key verification, not treating old signatures as belonging to new keys.

## Operation-safety evidence and recovery limits

| Scenario | Evidence / required response |
| --- | --- |
| Repeated clicks / page switching | New real journey submits twice but observes one signing call; existing browser/service tests retain active jobs across routes |
| Stale IDs / sessions | New native obsolete Lock session rejects; existing worker/service tests cover foreign/changed selection and operation IDs |
| Lock / Close during admitted work | Real BUSY Lock and acknowledged native close-refusal notice; existing verification tests cover the shared active gate |
| Cancel / wrong password | Actual Open/password/overwrite rejection and explicit retry; no replacement generation or false completion |
| Existing output failure | Real No/Cancel preserves predecessor; existing transaction faults cover fsync, verifier, replace and postpublish failures |
| Wrong keys / corrupted PDF / malformed vault | New native UI rejects each with no carried-over VALID; existing tests add malformed metadata, ByteRange/padding and revision changes |
| Unexpected errors / lost replies | Existing Python fault injection and frontend uncertainty/reconciliation cases; no fabricated success or automatic resubmission |
| Restart / shutdown | Actual second-process unlock retains ID and verifies original output; normal shutdown cleans owned worker resources |
| Forced kill / power loss / native hang | Not a clean recovery guarantee. No persistent operation journal; inspect and verify outputs before retrying. Manual/disruptive testing deferred |

## Security and claim boundaries

- **Cryptographic validity:** both inherited signature layers validate under the
  selected public keys. Ed25519 signs the first revision; Falcon covers the
  inherited SHAKE256-based message over the state containing Ed25519. No algorithm,
  digest or signed-message construction was changed here.
- **Signer identity:** not established. A Hybrid Key ID is a public tuple ID;
  authenticated vault metadata is not a legal-identity certificate. Public-only
  vault metadata remains explicitly unauthenticated when selected that way.
- **Time:** no trusted timestamp or authenticated signing-time proof is embedded.
- **Format:** inherited custom trailers, not a CMS/PAdES implementation or claim
  of standard PDF-reader signature-panel interoperability. Input envelope checks
  do not constitute complete PDF parsing or active-content inspection.
- **Falcon:** use “Falcon-512 through pqcrypto 0.3.4's PQClean clean binding;
  investigated source lineage labelled 20211101 with PQClean patches.” See
  [implementation evidence](falcon-implementation-provenance.md). Do not equate a
  package version with verified Falcon-v1.2 conformance, FN-DSA/FIPS certification
  or an independently reproducible native build.
- **Key storage:** existing Argon2id (64 MiB, 3 iterations, 4 lanes) and
  AES-256-GCM vault v1 remain. Offline guessing, lost passwords, whole-vault
  replacement/rollback and compromised devices are residual risks. Locking is
  not guaranteed Python/.NET/native memory zeroization or malware resistance.
- **Files/processes:** cooperative locking, protected DACLs, source capture,
  staged self-verification and atomic replacement remain. Atomic replacement
  is not power-loss durability or an atomic defense against every hostile race.
  OS-denied cleanup or forced termination can leave plaintext PDF stages.

## Remaining human acceptance requirements

No separate human interaction session is claimed. Before the thesis presentation:

- [ ] Run the Explorer shortcut on the actual presentation account and machine.
- [ ] Complete Open/Save, overwrite Yes/No, Escape/Cancel and password validation
  manually, including the Windows UI language used on stage.
- [ ] Rehearse the Notepad edit and confirm the edited copy is INVALID while the
  original remains VALID under the same keys. Check filename/encoding handling.
- [ ] Check projector placement, Windows 100/125/150% scaling, mixed-DPI monitor
  transfers, focus rings, Tab/Enter/Space/Escape and a physical screen reader.
- [ ] Test intended NTFS demo-folder permissions without ACL repair/elevation.
- [ ] Rehearse safe error recovery; do not rely on EXE packaging, password recovery,
  backup/restore, accounts or a persistent operation history.

Automated native dialogs, screenshots, browser accessibility checks and one
physical workstation are useful evidence, not completion of these human checks.

## Exact changed-file manifest

| File | Change |
| --- | --- |
| `frontend/src/native/signing.tsx` | Clear stale visible completion/operation reference at new PDF selection start |
| `frontend/tests/native-signing.spec.ts` | Four new selection-result regressions, retaining prior scenarios |
| `tests/test_desktop_demo.py` | Public sample validation and two-process native journey assertions |
| `tests/desktop_demo_probe.py` | Test-only real dialog/UI driver, safety/ownership/privacy instrumentation and public QA records |
| `tests/desktop_vault_probe.py` | Wait for a stable enabled control after native modal focus return; keep all inherited assertions |
| `demo_assets/sample-unsigned.pdf` | Generated 742-byte public ASCII PDF fixture |
| `demo_assets/README.md` | Sample provenance, safe copy/tamper instructions and limits |
| `.gitignore` | Ignore vaults, known sidecars and disposable demo-work folder |
| `README.md` | Link demo preparation, public sample and no-console-on-stage instructions |
| `frontend/qa/phase4c1/` | Public native workflow/theme/window-state captures and JSON evidence |
| `docs/phase4c1-demo-readiness.md` | This readiness matrix, results, script and limitations |

The individual QA filenames, byte counts and SHA-256 values are listed in the
[capture manifest](../frontend/qa/phase4c1/manifest.json), excluding that manifest
itself. It describes this recorded run, not a reproducibility claim for random
disposable keys or future screenshots. Historical Phase 4A/4B QA captures are
restored unchanged; this phase's captures have their own directory.

## Exact regression results

| Check | Final outcome |
| --- | --- |
| `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` | **1635 passed, 8 skipped in 229.45s**; 0 failed, 0 xfailed, 0 xpassed |
| `npm run test:e2e` | **266 passed in 3.7 minutes**; 0 failed, 0 skipped |
| `npm run typecheck` | Passed (`tsc --noEmit`, exit 0) |
| `npm run build` | Passed, including TypeScript; Vite completed in 615ms |
| Focused existing-vault + new native journey tests | **3 passed in 47.93s** |
| New real desktop create/reopen reports | Both passed; original pair/ID retained, VALID / modified-copy INVALID / locked-public VALID confirmed |
| Native default / maximized / restored / minimum window acceptance | Passed; current public record copied under `window-states/` |
| Baseline production-source hashes | 65 of 66 audited files byte-identical; only `frontend/src/native/signing.tsx` differs |
| Recorded original benchmark SHA-256 values | **15 matched, 0 changed, 0 missing**, read-only comparison with `docs/phase1-baseline.json` and original dataset files |

There are two new Python tests and four new Playwright cases executed in two
frontend projects (+8 executions). Every inherited test purpose remains; no
assertion was weakened or test marked skipped to obtain these results.
Earlier full development runs each reported 1 failure / 1634 passes / 8 skips:
the new native driver timed out in one run, and the inherited vault driver's
synthetic Lock click raced focus refresh in another. The driver corrections
described above were followed by the focused three-test run and the final full
green run. Those earlier runs are not counted as successful validations.

The generated public sample is 742 bytes, SHA-256
`2d94ba434bbbfda3ffcd78731f2e94146352e5dc7680dcd566d2ca0614a20639`.
The recorded native journey produced a 5368-byte signed PDF and a 2416-byte
encrypted vault. Creator/reopener records agree on both the public-key digest
and encrypted-vault hash; original signature verification still succeeds after
reopening. Disposable encrypted vaults and actual signed outputs remain in local
test storage, outside the tracked public QA directory.

Observed local environment: Python 3.11.9, pytest 9.2.0, pqcrypto 0.3.4,
PyNaCl 1.6.2, cryptography 50.0.2, pywebview 6.2.1, pythonnet 3.2.1,
WebView2 156.0.4314.58, Node 26.13.0 and npm 11.20.0. These are the tested
installed versions, not a claim that other combinations have been validated.

The eight inherited skips require Windows symlink privileges/Developer Mode.
They remain documented skips, not successful symlink tests. Real hard-link,
path-safety and the remaining filesystem regressions remain in the full suite.

## Recommendations for Phase 4C.2

1. Complete and record the human presentation-machine checklist, especially
   Notepad, native picker locale, projector/mixed-DPI and screen-reader behavior.
2. Freeze a reproducible dependency/build manifest and define a separately
   approved Windows packaging/installer smoke test. No EXE is produced here.
3. Specify operation-journal/restart reconciliation requirements before changing
   uncertainty semantics. Do not promise cancellation, rollback or exactly-once
   signing across process death without a reviewed design and failure tests.
4. Keep trusted identity/enrollment, timestamp and standard signature-format work
   in separately reviewed compatibility/security phases. Preserve current legacy
   signatures and public contracts until explicit migration approval.
