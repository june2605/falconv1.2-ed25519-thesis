# Phase 4B.3B — real native hybrid PDF verification

## Scope and starting state

Workspace `D:\Final_Thesis_GitHub`, branch `thesis/ui-demo`, clean starting HEAD
`331a6b62de5f2a6a8a324c5de76a2d68f8737728` were confirmed before editing.
AGENTS.md, relevant Phase 3 key/vault trust and storage records, Phase 4 UI/native
security records, the Phase 4B.3A report and the current implementation/tests were
reviewed. The baseline was independently rerun: **1597 Python passed, 8 existing
Windows symlink-privilege skips in 133.29 seconds**. The inherited frontend
baseline was 152 executions; all remain in the final full frontend suite.

Only native verification and its UI/worker/public-key selection boundary are added.
There is no new verification engine, identity/account service, key serialization,
vault/PDF format, cryptographic algorithm or signed-message construction. Existing
crypto APIs and their eleven-element tuples are unchanged. No packages were
installed, datasets copied/changed, worktrees created, commits made or pushes run.

## Architecture

```text
Verify Signature (real native capability only)
  -> VerificationBridge: five explicit methods; IDs and public metadata only
     -> NativeDialogs: Windows PDF / encrypted-vault file selection
     -> VerificationWorker: extends the same original vault-owning worker
        -> VerificationService: bounded immutable PDF + public-key snapshots
        -> verify.verify_bytes(snapshot.data, Ed25519 public, Falcon public)
     <- authoritative overall result and selected-source provenance
```

`VerificationService.run()` is the only new adapter calling the inherited
`verify_bytes()`. It does not parse signature containers or construct digests.
It requires the actual eleven-element tuple and a literal boolean first element.
Only `True` produces `valid`; `False` produces `invalid`. Outer exceptions,
contract errors or changed inputs produce `failed` with no boolean result.
Timing values are never interpreted as layer results. The UI therefore shows
**HYBRID VALID / HYBRID INVALID**, algorithms and hybrid key ID, and explicitly
states that individual layer statuses are not exposed.

The signed-document path uses `locked_pdf(..., unsigned=False)`, retaining the
existing native restrictions: supported PDF header/extension, regular file on
fixed local NTFS, no links/reparse points/hardlinks, and a bounded size of 50 MiB
plus the inherited 65536-byte signed-file allowance. It deliberately does not run
unsigned-input marker rejection or require unsigned terminal EOF. Unsigned,
truncated or malformed containers with a readable PDF envelope reach the strict
inherited verifier and are rejected there. A bad header, empty/oversized file or
unsafe path is a selection/read failure, never a valid result.

Selection retains checked path, file identity/revision, SHA-256 content fingerprint
and safe name/size. Execution recaptures and compares the same selected revision.
The original Windows read-sharing handle remains open throughout verification,
denying ordinary writes/delete. The verifier receives immutable bytes. Public-key
source revision/identity is rechecked before and after cryptographic verification.
No PDF, vault or public-key source bytes are modified. Public-only verification
does not create a cooperative lock sidecar or repair ACLs.

## Public-key source trust

| Source | Validation and scope | UI provenance |
| --- | --- | --- |
| Currently authenticated vault | Exact owner-thread vault/session IDs; existing managed binding, ACL/revision and cooperative-lock checks; capture must equal the authenticated encrypted revision | `vault-authenticated`: **Authenticated at selection** |
| Native-selected encrypted vault | Existing `capture_vault()` and `parse_vault()` validate exact v1 length/header/profile, algorithm IDs, public-key encodings/sizes and hybrid-v1 ID consistency; no KDF, decryption or password | `unauthenticated-metadata`: **UNAUTHENTICATED** |

Both sources retain only encrypted snapshot bytes and immutable public keys in
the verification adapter. An authenticated public snapshot remains usable after
locking the vault: no managed handle/private key is needed for verification.
The encrypted revision must still match when used. Selecting public keys does
not unlock or replace the signing vault, create a pair, or change its session.
The managed handle is never transferred off its original thread.

**Authentication is not identity certification.** An authenticated header proves
local vault authentication at selection, not legal identity or registry trust.
A parsed public ID only identifies a tuple. An attacker can replace an
unauthenticated header, its keys and its recomputed ID. A signature can then be
mathematically valid under attacker-supplied keys; the UI never treats that as a
trusted signer binding. Password-free metadata cannot authenticate the ciphertext
tag or prove private-key possession. A regression deliberately corrupts the tag
while preserving public metadata: public verification still works and remains
UNAUTHENTICATED. Full vault validation would require an explicit authenticated
unlock; verification never silently attempts it.

The existing public-key model validates immutable types, algorithm/version fields,
sizes and deterministic IDs; it does not prove key ownership or every native
encoding property at selection. Actual signature verification uses the native
algorithms through the inherited verifier. No new decoder or possession test is
introduced.

## Native bridge and lifecycle

The current strict profile has **14 allowlisted methods**: the previous nine plus:

| Method | Input | Public output |
| --- | --- | --- |
| `choose_verification_pdf()` | No arguments; native Open | `{document, cancelled}` |
| `choose_verification_keys()` | No arguments; native encrypted-vault Open | `{keySource, cancelled}` |
| `use_authenticated_vault_keys(vaultId, sessionId)` | Two opaque IDs, no password | `{keySource, cancelled}` |
| `verify_pdf(documentId, keySourceId, operationId)` | Three opaque IDs | Current job snapshot; returns after admission, not crypto completion |
| `get_verification_state(operationId?)` | Latest or one opaque ID | Authoritative job snapshot; stale/foreign ID rejects |

All IDs are exactly 32 lowercase hexadecimal characters. JavaScript never supplies
paths or PDF bytes and receives no native objects, keys, passwords, raw exceptions
or full filesystem paths. Document metadata has `documentId`, basename
`displayName`, `sizeBytes`. Key metadata has `keySourceId`, safe `displayName`,
`hybridKeyId`, `trust`. Job metadata has exactly `operationId`, `state`, `document`,
`keySource`, `hybridValid`, `errorCode`. There are no independent algorithm booleans.

The capability has `pdfVerification=true`; accounts remain false. The exact old
2/6/9-method profiles remain recognized by the frontend; the existing signing and
vault adapters can also operate under the exact new profile. A desktop profile
without verification now shows an unavailable state, **never simulated results**.
Only browser UI Preview retains the original examples. Native origin/resource,
navigation, popup, download, permission, CSP and bounded-dispatch restrictions are
unchanged. The guard's fixed method allowlist is extended explicitly, not made
generic. Older strict frontend builds reject the expanded profile: rebuild the
bundle with the current shell.

```text
idle / inputs selected (UI ready)
  -> ready -> queued -> running -> valid | invalid | failed
```

The worker retains one latest verification record in addition to its existing
latest signing record, with one shared active-operation gate and the existing
bounded queue (capacity eight). Same operation ID + same arguments returns its
record; changed arguments under that ID reject. Different active jobs reject.
Signing, vault mutations and new selections cannot interfere with verification,
and active signing blocks verification. Native metadata/status remains queryable.
Both commands run on the single existing owner thread.

Verification is internally queued with no short execution deadline or
`Future.result(timeout)` wait. A job lasting more than five seconds still reports
its actual result. Selection and ID preflight retain the existing five-second
short-request bound; a timeout there cannot establish a cryptographic result.
Status reads use the locked public record outside the execution queue. React polls
at most one read at a time, every 200 ms while active/uncertain, with a two-second
status-read bound. Lost submission/status replies lead to an **outcome not
confirmed** UI state and reconciliation of the same ID, never automatic retry or
an invented VALID/INVALID. Explicit failed jobs can be retried deliberately.
Route changes preserve the current operation. Starting another selection clears
the old visible result, including on Cancel.

The authoritative read-only worker does not need a terminal `outcome-uncertain`
classification: caught execution exceptions are `failed`. Communication loss is
uncertain from the caller's perspective until status is reconciled. Normal close
and shutdown refuse while a signing/verification job is active, without setting a
cancel/stop signal. Native calls are not forcibly interruptible; an indefinite
native hang still needs external termination. Bounds concern admission/state,
not a guaranteed maximum native runtime. No cross-restart operation journal or
exactly-once guarantee is introduced. A terminal result describes a captured
revision, not ongoing surveillance of the file.

## Regression evidence

The initial Python regression failed on the absent verification module before
production changes. The seven initial frontend scenarios failed on the missing
native workflow/capability. New Windows GUI coverage also preceded its driver.
An early malformed-container fixture incorrectly searched for CMS-style
`/ByteRange`; its control assertion caught that it was unchanged. It was corrected
to mutate the actual inherited `ByteRange:` field. No cryptographic assertion was
removed or marked xfail.

New Python cases cover real Phase 4B.3A signing, the actual original pair, tampered,
unsigned/truncated/malformed PDFs, independently wrong Ed25519/Falcon/both keys,
unauthenticated metadata, authenticated snapshots after lock, invalid header and
profile fields, damaged ciphertext trust semantics, cancellation, stale/foreign
IDs, changed/replaced PDF/vault, size/header/hardlink rejection, verifier exceptions,
bad tuple contracts, duplicate jobs, conflicts in both directions, pinned Windows
handles, lost admission replies, a 5.2-second job and shutdown refusal. Every old
signing/vault/core regression remains; native capability assertions intentionally
change nine to fourteen exact methods and verification false to true. The old
signing-profile frontend assertion is strengthened to forbid example verification
in desktop mode.

Seven new Playwright scenarios execute at both existing desktop viewports (14
executions), covering actual native response shapes, untrusted/authenticated-source
messaging, overall valid/invalid/failure, lost replies, malformed completions,
Cancel, repeated clicks, conflicting operations and route-persistent results.
Existing browser examples, preview isolation and old capability tests remain.

### Actual Windows applications

`tests/test_desktop_verification_native.py` prepares a disposable encrypted vault
and real PDF through `sign_vault_document()` in a closed managed context. A separate
actual WebView2 application then checks the valid PDF, an altered copy and a wrong
vault source, cancels another selection, and closes cleanly. It has **no unlocked
managed session** and fails if a password is requested. It inspects authoritative
native booleans as well as UI headings, compares all input hashes and directory
entries, and verifies that no artifacts or source changes occurred.

As with prior Phase 4B probes, **file acceptance uses a private Python-only
GUI-thread selection seam**, not a production/debug bridge or browser-provided
path. The real production Windows picker is opened and cancelled. Attempts to
automate OS Open acceptance were unreliable; the final driver retains controlled
selection and documents this limit. An early driver also closed its owner as soon
as the prior result was cleared, before the modal picker finished; it now waits
for actual dialog completion and re-enabled controls before closing. This fixes
the test driver without weakening production dialog or verification checks.
No successful human picker-acceptance session is claimed.

### Requested Downloads files

An additional visible Windows application check used these existing files in
Downloads, without copying either document or the vault into the repository:

| File / source | Existing verifier and desktop result |
| --- | --- |
| `Le nouveau Taxi! 1-signed.pdf` with `thesis-demo-01.hvault` public metadata | **HYBRID VALID** |
| `Le nouveau Taxi! 1-tampered.pdf` with that source | **HYBRID INVALID** |
| Original signed PDF with a disposable unrelated encrypted vault | **HYBRID INVALID** |
| Cancel another PDF selection | **No verification performed** |

Both PDFs are 34,004,166 bytes; the vault is 2416 bytes. The independent direct
`verify_bytes()` calls also returned literal True/False respectively with tuple
length eleven. The real desktop checks retained UNAUTHENTICATED source status,
requested no password, compared unchanged input hashes, detected no created
artifacts in their directories, and stopped owned threads on close. This is an
automated visible native check using the same selection seam, not a claim that a
human manually accepted the Windows picker. Manual acceptance remains below.

Reviewed owned-window captures show metadata/results only, never rendered PDF
contents or plaintext keys/passwords:

- [Downloads valid](../frontend/qa/phase4b3b/downloads-valid.png)
- [Downloads tampered](../frontend/qa/phase4b3b/downloads-tampered.png)
- [Downloads wrong keys](../frontend/qa/phase4b3b/downloads-wrong-keys.png)
- [Disposable valid](../frontend/qa/phase4b3b/disposable-valid.png)
- [Disposable tampered](../frontend/qa/phase4b3b/disposable-tampered.png)
- [Disposable wrong keys](../frontend/qa/phase4b3b/disposable-wrong-keys.png)
- [Downloads public check record](../frontend/qa/phase4b3b/downloads-checks.json)
- [Disposable public check record](../frontend/qa/phase4b3b/disposable-checks.json)
- [Fourteen-method native shell record](../frontend/qa/phase4b3b/native-checks.json)

## Full validation results

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -rs -p no:cacheprovider
Set-Location frontend
npm run typecheck
npm run build
npm run test:e2e
```

| Check | Result |
| --- | --- |
| Full Python suite, including actual Windows GUI coverage | **1632 passed, 8 skipped in 156.60 seconds**; 0 failed, 0 xfailed, 0 xpassed |
| Full frontend suite on the final bundle | **166 passed (1.9 minutes)**; 0 failed/skipped/expected failures/unexpected passes |
| TypeScript (`npm run typecheck`, also run by build) | Passed, exit 0 |
| Production build | Passed, exit 0 |
| Whitespace/diff checks | `git diff --check` passed |

The increase is 34 service/worker/bridge cases plus one actual Windows application
case, and seven frontend scenarios at two viewports. All 1597 prior Python test
purposes and 152 prior frontend executions remain green. A final markup-only
spacing follow-up reused the existing button-row/detail-panel classes; the build,
full frontend suite and actual native GUI checks were rerun on that bundle.
The final isolated Windows verification test passed in **8.88 seconds**, followed
by the successful additional Downloads application check. The earlier full
frontend run also passed all 166 executions in 1.8 minutes.

The eight Windows symlink-privilege skips are inherited unchanged; no GUI,
verification or hardlink test is skipped. The environment remains Windows x64,
Python 3.11.9, pqcrypto 0.3.4, PyNaCl 1.6.2, cryptography 50.0.2, pywebview 6.2.1,
pythonnet 3.2.1, Node 26.13.0/npm 11.20.0 and installed Microsoft Edge 156.
Physical high-DPI/multi-monitor behavior, screen readers, Linux/macOS and hostile
filesystem/power-failure behavior have not been validated by these checks.

## Changed-file manifest

| File(s) | Change |
| --- | --- |
| `desktop/verification_service.py` | Read-only PDF/public snapshots, revision checks and sole inherited-verifier call |
| `desktop/verification_worker.py` | Explicit bounded admission, shared owner/active gate, independent status and overall terminal result |
| `desktop/verification_bridge.py` | Five native-only verification methods with strict ID/argument validation |
| `desktop/vault_service.py` | Owner-thread authenticated encrypted/public snapshot helper; no handle transfer |
| `desktop/worker.py` | Five fixed internal verification enum commands |
| `desktop/contracts.py` | Explicit method allowlist, verification capability/errors and typed public source/result shapes |
| `desktop/dialogs.py` | Signed-PDF Open policy/title and truthful shared active-operation close notice |
| `desktop/launcher.py` | Instantiate the extended verification bridge/worker on the same architecture |
| `frontend/src/native/verification.tsx` | Strict response validation, selection/provenance, overall results and reconciliation context |
| `frontend/src/native/desktop.ts` | Exact fourteen-method profile alongside old profiles |
| `frontend/src/native/signing.tsx`, `main.tsx` | Recognize new bridge profile, provider wiring and cross-operation busy gating |
| `frontend/src/pages/NativeVerifySignature.tsx`, `VerifySignature.tsx` | Real native page; unavailable desktop fallback; examples confined to browser preview |
| `frontend/src/App.tsx`, `pages/Dashboard.tsx`, `pages/Settings.tsx`, `components/VaultDialogs.tsx`, `components/NativeVault.tsx`, `pages/NativeSignDocument.tsx` | Accurate capabilities, limitations and shared-operation copy |
| `tests/test_desktop_verification.py` | New actual-engine service/worker/bridge, trust, concurrency and fault cases |
| `tests/test_desktop_verification_native.py`, `tests/desktop_verification_probe.py` | Real Windows read-only result checks, source privacy, actual cancellation and screenshots |
| `tests/test_desktop_native.py`, `tests/desktop_native_probe.py` | Exact expanded allowlist/capability assertion and new current evidence directory; guard/navigation purposes preserved |
| `frontend/tests/native-verification.spec.ts` | Seven scenarios at two viewports |
| `frontend/tests/native-signing.spec.ts` | Additional desktop-no-examples assertion under the old signing-only profile |
| `frontend/qa/phase4b3b/` | The nine linked public records/screenshots plus `native-dashboard.png` |
| `README.md`, `frontend/README.md` | Current verification workflow, source trust and lifecycle limits |
| `docs/phase4b3b-real-verification-regression.md` | This report |

Historical QA artifacts are preserved. `verify.py`, `sign.py`, `signing_io.py`,
`utils.py`, `hybrid_keys.py`, `vault.py`, `vault_crypto.py`, `vault_format.py`,
`vault_io.py`, benchmark/frozen fixtures and dependency manifests are unchanged.

## Manual reproduction and remaining scope

1. Build with `npm run build` in `frontend`; run
   `.\.venv\Scripts\python.exe -m desktop.launcher` at repository root.
2. On Verify Signature use the actual Windows **Choose signed PDF** dialog, then
   **Choose encrypted vault**. Select the matching `.hvault`; no password should
   be requested. Check that source status says UNAUTHENTICATED.
3. Click Verify PDF and confirm the overall result, document name and hybrid ID.
   Repeat with the two Downloads filenames above. Cancel a picker and check that
   no result is carried over to imply verification of a new selection.
4. Select a disposable unrelated vault and confirm INVALID under those keys.
   Do not interpret INVALID as proof of tampering rather than wrong keys.
5. Optionally unlock a disposable vault on Key Vault, then choose **Use authenticated
   vault**. Check Authenticated at selection. Lock it and verify again: public
   verification must still work, while private signing access is locked.
6. During an observable active operation, try another job, vault mutation and normal
   Close. Wait for the actual result; reconcile communication loss without
   automatic resubmission. Retry failed reads explicitly after selecting again.
7. Independently check the output with `verify_file_with_public_keys()` and require
   tuple element zero to be literal True. Use nonsensitive files and never copy
   user PDFs, passwords or keys into repository evidence.

The inherited verifier intentionally returns only one boolean plus timings and
maps some internal parsing/native exceptions to False. The adapter cannot attribute
which layer failed or distinguish every underlying rejection cause without a
separately approved diagnostic API. A caught outer/native-adapter exception is
failed, not INVALID; a frontend timeout never sets either boolean.

Snapshot/path rechecks cannot defeat a malicious local process or hostile
filesystem performing changes between checks. Results are not perpetual file
integrity guarantees. No secret-memory isolation/guaranteed zeroization, malware
resistance, trusted identity, revocation/registry freshness, trusted signing time,
legal certification, FIPS/Falcon-revision certification, CMS/PAdES or production
security claim is introduced. The custom signed PDFs still contain no authenticated
identity or hybrid key ID. Future trusted verification needs an independent key
binding/trust policy; vault authentication alone does not supply it.

## Phase 4B.3B.1 — responsive desktop UI and result polish

### Starting state and scope

Implemented on `thesis/ui-demo` at unchanged HEAD `331a6b6`. The working tree
already contained the completed, uncommitted Phase 4B.3B implementation documented
above. That work was preserved. The starting regression record was 1632 Python
passed with eight Windows symlink-privilege skips and 166 frontend passed.

This incremental step changes presentation and tests only. Cryptographic engines,
formats, native method allowlists, worker ownership, path/ACL checks, session
behavior and public API contracts were not edited in this step. Existing backend
changes visible against HEAD belong to the preceding uncommitted Phase 4B.3B.
No dependencies, commits, pushes or history changes were introduced.

### Root causes

- Workflow layouts stayed in two columns until a **window** width of 820 pixels,
  although the expanded sidebar consumed 208–252 pixels plus page padding. The
  1100/1177 restored sizes consequently left narrow cards despite ample vertical
  scrolling space.
- Several grids had minimum-width tracks while inner flex children retained their
  intrinsic widths. Long identifiers, notices and action groups competed with
  labels inside those tracks.
- Full 74-character public IDs were always rendered inside right-aligned detail
  cells. Line wrapping consumed several rows without providing a direct copy or
  accessible full-value disclosure on the result page.
- Adjacent buttons used unconstrained flex wrapping. Their rows and alignment
  varied with text length and available card width.
- The action footer was already outside the scroll region, which was retained.
  Its long duplicate description and nonshrinking action groups nevertheless used
  excessive height at compact widths/heights. The Reduce motion switch also had
  a 19-pixel actual hit target, despite its surrounding row being larger.
- Resizing could move an active main-area control below the visible scroll area;
  there was no focused-control adjustment for that layout transition.

### Layout and scrolling strategy

The existing theme, typography, cards, sidebar and fixed shell are retained.
`responsive.css`, imported after the existing theme/refinement sheets, is a small
presentation layer rather than a replacement design system.

| Condition | Behavior |
| --- | --- |
| Usable `.page-container` content width below **960 px** | Workflow, vault, settings and both Dashboard grids become one column; wide views retain their existing two-column proportions |
| Content width below **500 px** | Vault tool actions stack, decorative paper is hidden, narrow setting rows can wrap |
| Existing viewport threshold **980 px** | Sidebar still collapses to icons; navigation has its own overflow safety rather than clipping |
| Action-host width below **900 px** | Keep title/actions in one compact row and hide only the repeated explanatory paragraph |
| Action-host width below **520 px** | Title and actions use separate rows; buttons use a consistent responsive grid |
| Window height at most **700 px**, above the existing small-mobile range | Compact footer padding and hide its repeated explanatory paragraph |

The page and action host use named inline-size CSS containers, so breakpoints
measure their actual available width after the sidebar. `min-width: 0` on grid
and flex children plus wrapping labels prevents horizontal overflow. Adjacent
button groups use equal responsive grid tracks with consistent 10-pixel gaps;
they stack when their minimum practical widths no longer fit. Important labels
and controls remain present and retain their disabled/operation guards.

The main text remains 14 pixels and metadata 12 pixels. Standard buttons retain
40-pixel targets; copy/disclosure controls are at least 36 pixels high. The switch
keeps its original visual track while gaining a 44×32 target. Fonts and cards
were not shrunk to force content into a single viewport.

`main` remains the single document scroll container; body scrolling stays off.
The footer is a flex sibling below it, not an overlay. Main content has explicit
bottom padding and scroll padding/margins, and its scrollbar ends above the
footer. Vertical scrolling is expected at the minimum size and after disclosures.
The DOM reading/tab order is unchanged when grids stack. Route navigation retains
the existing heading focus/scroll reset. On resize, only an active interactive
control inside main is scrolled the minimum distance needed to remain visible;
headings/background content do not trigger a reset or an arbitrary jump to top.

### Compact public ID

`HybridKeyId` presents the unchanged prefix/first eight digest characters/ellipsis/
last eight characters. It supplies **Copy full ID** and a native keyboard-operated
**View full ID** disclosure. The full original value remains selectable, focusable
and readable when expanded; it is not restricted to a hover tooltip.

Copy writes the original `value` directly, never the abbreviated text. A status
region confirms success. If Clipboard API access fails, the disclosure opens and
offers selection/manual copying. No native permission or bridge capability was
added. Changing the displayed value clears prior copy feedback/disclosure state.
The shared component is used in native verification, native signing review/result,
and native vault/details views. IDs, algorithm results and trust data are not
reconstructed or modified.

HYBRID VALID, HYBRID INVALID, failure, UNAUTHENTICATED metadata and Authenticated
at selection retain their distinct meanings. Signer identity remains explicitly
unestablished. Desktop results stay native; browser examples stay UI Preview.

### Test-first coverage and actual Windows checks

New responsive/ID regressions were added before the UI changes. They initially
failed on the old two-column layout and absent compact-ID component. The new
Windows-state test likewise failed before its probe extension. No prior test
purpose was removed, skipped or converted to expected failure. The new geometry
scan deliberately excludes existing `sr-only` inputs: those are intentionally
nonvisual accessible controls, not clipped visible UI.

Twenty new frontend scenarios run under both existing projects (40 executions):

- All five native screens at **960×600, 1100×700, 1177×740, 1280×800, 1366×768,
  1440×900 and 1920×1080**, in light and dark, including signing review and a
  completed verification result.
- Grid transitions based on measured content width, no horizontal/text/control
  overflow, practical hit targets, unobscured control centers after scrolling,
  persistent footer geometry and unchanged navigation focus.
- Live resizing through the sizes in both directions, retained control focus,
  scroll ownership, route changes/reset and preserved completed result.
- Exact full-ID copy with a nonrepeating identifier, keyboard activation and
  disclosure, visible full value and denied-clipboard recovery.
- Separate invalid/failure results, authenticated-source language and browser
  Preview isolation while resizing all pages.
- Automated native-page WCAG A/AA name/contrast checks in both themes and small/
  large layouts. These supplement, rather than claim to replace, human screen
  reader testing.

The real WebView2 test uses a disposable encrypted vault and a real hybrid-signed
PDF. After verifying it, the same actual window is left at default size, maximized,
restored and moved to its unchanged native minimum. Every state checks retained
VALID, active-control visibility, no horizontal overflow and main/footer separation.
The original tampered/wrong-key/cancel and unchanged-input/cleanup checks then still
run. Selection acceptance uses the existing private GUI-thread test seam; actual
picker cancellation is exercised. No user documents or passwords are used.

The recorded renderer sizes from this Windows run are below; they are CSS pixels
inside the WebView, not outer-window or screenshot pixels. The existing minimum
configuration remains 960×600 in the launcher. Window chrome/system scaling explain
why its renderer is smaller; the native frame metrics are retained in the JSON.

| Native window state | Renderer | Columns | Sidebar |
| --- | --- | --- | --- |
| Default | 1266×763 | 2 | Expanded |
| Maximized | 1536×794 | 2 | Expanded |
| Restored | 1266×763 | 2 | Expanded |
| Minimum | 946×563 | 1 | Icons |

Dedicated responsive evidence is separate from the historical tracked Phase 4A/4B
images. The existing uncommitted Phase 4B.3B native QA is also refreshed by its
normal full-suite probes to show the current UI:

- [All 70 light/dark screen captures](../frontend/qa/phase4b3b1/)
- [1177×740 native-profile verification](../frontend/qa/phase4b3b1/1177x740-light-verify.png)
- [960×600 native-profile signing review](../frontend/qa/phase4b3b1/960x600-light-sign.png)
- [Default actual WebView2 window](../frontend/qa/phase4b3b1/native/verify-default.png)
- [Maximized actual WebView2 window](../frontend/qa/phase4b3b1/native/verify-maximized.png)
- [Restored actual WebView2 window](../frontend/qa/phase4b3b1/native/verify-restored.png)
- [Minimum actual WebView2 window](../frontend/qa/phase4b3b1/native/verify-minimum.png)
- [Minimum window scrolled to the result and public ID](../frontend/qa/phase4b3b1/native/verify-minimum-result.png)
- [Native geometry, focus, verification and unchanged-input record](../frontend/qa/phase4b3b1/native/responsive-checks.json)

The native folder additionally includes result-focused captures for the other
three window states and the original valid/tampered/wrong-key sequence. Screenshots
were inspected at restored, minimum and maximized sizes; no PDF content or secrets
are rendered in them.

### Exact files changed for this polish step

This list is incremental to the already-uncommitted Phase 4B.3B manifest above:

| File(s) | UI/test change |
| --- | --- |
| `frontend/src/responsive.css` | New container-based reflow, safe inner sizing, button grids, footer density, scroll margins and switch hit target |
| `frontend/src/components/HybridKeyId.tsx` | New compact/exact-copy/full-value disclosure component with keyboard/manual-copy support |
| `frontend/src/components/NativeVault.tsx` | Reuse the ID component in the native card and public-details dialog |
| `frontend/src/pages/NativeSignDocument.tsx` | Reuse the ID component in review and completed result |
| `frontend/src/pages/NativeVerifySignature.tsx` | Reuse the ID component and concise equivalent selection instructions |
| `frontend/src/App.tsx` | Resize handling keeps an active main-area control in view |
| `frontend/src/main.tsx` | Load the presentation layer after the existing styles |
| `frontend/tests/support/native-responsive-host.ts` | Public-only 14-method UI contract fixture; no production API |
| `frontend/tests/responsive-native.spec.ts` | Twenty responsive/keyboard/trust/preview/accessibility scenarios at both projects |
| `tests/test_desktop_responsive_native.py` | New actual Windows window-state/geometry verification test |
| `tests/desktop_verification_probe.py` | Optional test-only native window-state exercise and separate evidence directory; original checks preserved |
| `frontend/qa/phase4b3b1/` | Current responsive screenshots and native public check record |
| `frontend/qa/phase4b3b/disposable-valid.png`, `disposable-tampered.png`, `disposable-wrong-keys.png`, `disposable-checks.json`, `native-dashboard.png`, `native-checks.json` | Existing uncommitted native QA refreshed by the unchanged full-suite probes; Downloads evidence was not rerun or changed |
| `docs/phase4b3b-real-verification-regression.md` | This separate Phase 4B.3B.1 section |

### Exact results and limitations

| Validation | Result |
| --- | --- |
| Full frontend suite | **206 passed (3.1 minutes)**; 0 failed, 0 skipped, 0 expected failures/unexpected passes |
| Full Python suite | **1633 passed, 8 skipped in 243.97 seconds**; 0 failed, 0 xfailed, 0 xpassed |
| TypeScript check | Passed, exit 0, also included in build |
| Production build | Passed, exit 0 |
| Focused new responsive browser suite before full validation | **20 passed (25.9 seconds)** in the primary project |
| Focused actual WebView2 window-state test before full validation | **1 passed in 10.89 seconds** |
| Final focused live-resize/focus assertions at both projects | **2 passed in 4.5 seconds** |
| `git diff --check` | Passed |

All 166 prior frontend executions and 1632 prior Python test purposes remain
green. The increases are 40 responsive browser executions and one actual native
window-state test. The existing dependency/runtime environment is unchanged.

For manual review, launch the built desktop application, verify a nonsensitive PDF,
then restore/maximize and drag the window down to its existing minimum. Scroll the
single main area to the result, activate View full ID with Enter/Space, and copy
the full value. Resize while a main-area button is focused; it should stay in
view. Navigate through all five screens in both themes. Small windows should
scroll vertically; the footer should remain usable and never cover controls.

The inherited eight Windows symlink-privilege skips remain documented; no responsive
or real GUI test is skipped. OS clipboard access can be denied and uses the visible
manual-copy fallback. Copy accuracy is checked at the Clipboard API boundary;
cross-application clipboard behavior and physical screen-reader use remain manual.
Native window-state evidence is from one Windows workstation/monitor configuration;
mixed-DPI monitor transfers and every physical scaling configuration are not
claimed. Larger exact CSS viewports and both themes are covered by installed-Edge
tests. Content deliberately scrolls at small sizes. A compact ID is a presentation
of public-key data, never proof of signer identity or new trust/security compliance.

### Phase 4B.3B.1 correction — Hybrid Key ID interaction feedback

The initial shared component kept its copy confirmation indefinitely in a flex
child spanning a separate row. Its disclosure also kept the View full ID label
when open. This small correction changes only that component's interaction and
presentation; the previous responsive behavior and all native/cryptographic
boundaries remain intact.

- Successful copying temporarily replaces the visible copy-button label with
  **Full ID copied.** and a check icon. It resets after **2000 ms**. Repeated
  clicks cancel the prior timer and start a fresh duration after the latest
  clipboard write succeeds.
- The button reserves the natural width of both labels using an invisible CSS
  sizing element. There is no separate visible success row or copy-induced
  component/button size change. Its accessible name stays **Copy full ID**.
- An always-present, visually hidden, polite/atomic status region announces the
  result. Repeated successful requests update its child so feedback can be
  announced again. The button's changing visual label is not announced twice.
- The native details summary changes to **Hide full ID** while expanded. Pointer
  or keyboard activation collapses it and restores **View full ID**. The full
  original value stays focusable, selectable and readable when requested.
- A changed public-pair ID resets expansion and feedback and cancels the old
  timer. Unmount also cancels the timer. Per-request generations ignore clipboard
  success or failure that arrives after a newer copy, changed ID or unmount.
- Clipboard denial opens the full value and places manual-copy instructions
  inside that expanded area. It does not create a permanent compact-row message
  or change native permission policy. Every write still receives the original
  full identifier, without abbreviation or normalization.

Exact incremental files:

| File | Change |
| --- | --- |
| `frontend/src/components/HybridKeyId.tsx` | Two-second feedback lifecycle, cleanup/stale-response guards, in-button confirmation, accessible announcements and View/Hide labels |
| `frontend/src/responsive.css` | Stable label-width sizing; error instructions remain with the expanded value instead of a separate success row |
| `frontend/tests/key-id-interactions.spec.ts` | Six new scenarios, executed under both existing browser projects |
| `frontend/tests/support/native-responsive-host.ts` | Test-only ability to select a different public-key pair; the production bridge is unchanged |
| `docs/phase4b3b-real-verification-regression.md` | This correction record |

The new regressions were written first and all six initially failed against the
old component. They cover exact full-ID copy, two-second expiry, repeat-click
duration restart, unchanged copy-button/component geometry at all seven target
sizes, keyboard and pointer View/Hide interaction, resetting on a new pair,
late clipboard resolution/rejection, and timer cleanup on unmount/remount.
Controlled browser time avoids slow or timing-sensitive wall-clock sleeps.
All previous responsive, trust/status and verification tests are retained.

| Validation | Result |
| --- | --- |
| Full frontend suite | **218 passed (3.0 minutes)**; 0 failed/skipped/expected failures/unexpected passes |
| Full Python suite | **1633 passed, 8 skipped in 241.38 seconds**; 0 failed, 0 xfailed, 0 xpassed |
| Focused new interaction suite, both projects | **12 passed in 9.8 seconds** |
| TypeScript check | Passed, exit 0 |
| Production build | Passed, exit 0 |
| `git diff --check` | Passed |

All 206 prior frontend executions and all 1633 Python tests remain green. The
eight Python skips are the unchanged Windows symlink-privilege cases. The final
frontend run includes the pointer Hide check: its initial test selector assumed
a button role for the native HTML summary; the locator was corrected while
retaining the explicit Hide label and collapse assertions. Copied/expanded UI
states were also visually inspected using nonsensitive public test metadata.

These are UI and test changes only. Protected source fingerprints confirm that
the Python engines, native bridge/worker, vault/session/path behavior and frontend
native adapters are unchanged from the start of this correction. No dependencies
were installed, commits made or pushes performed. Existing public QA images are
preserved; the new layout assertions test both visible-feedback and expired states
without changing the approved screenshot baseline. Clipboard and physical screen
reader limitations described above still apply.

### Phase 4B.3B.1 — Smart Collapsible Desktop Sidebar

This increment starts from the existing uncommitted verification, responsive UI
and key-ID feedback work on `thesis/ui-demo`, HEAD `331a6b6`. Its starting baseline
is 218 frontend executions and 1633 Python tests, with eight Windows symlink
privilege skips. Those earlier changes and their evidence are preserved. This
increment changes the shell presentation and test drivers only; the existing
cryptographic engines, native adapters/contracts, workers, vault lifecycle, file
security controls and public return contracts are unchanged.

#### State model and layout

`SmartSidebar` owns a single navigation tree and explicit in-memory modes:

| Mode | Wide window | Narrow window |
| --- | --- | --- |
| Auto (initial/default) | Docked, 250 CSS px | Compact, 72 CSS px |
| Compact (manual collapse or unpin) | Compact; temporary expansion available | Compact; temporary expansion available |
| Pinned | Docked, 250 CSS px | Pin preference is dormant; compact with temporary expansion available |

The Auto control returns to responsive behavior. Pin/Unpin is available only when
there is sufficient space; it is disabled in a narrow window and during the
resize quiet period. A dormant pin resumes when sufficient width returns. Manual
preferences survive route changes for the mounted application session. Nothing
is written to localStorage, sessionStorage, native settings or a vault.

The initial expansion threshold is **1340 CSS px**. Once wide, the shell stays
wide until its actual layout width is **1280 CSS px or less**. These thresholds
provide hysteresis instead of oscillating at one breakpoint. The lower boundary
allows roughly 250 px sidebar + 48 px page insets + 17 px scrollbar + the existing
960 px two-column content threshold. The entry boundary provides additional
room. Decisions use the app shell's available CSS width, rather than outer
Windows coordinates; the native run below records the observed scaling.

Following visual review, expansion always reserves space beside the page. Both
temporary and pinned expansion use the same shared sidebar width for the panel
and workspace margin. Their synchronized **200 ms** transitions keep content,
the header and action footer outside the sidebar throughout opening and closing.
This intentionally allows responsive content reflow while the width changes,
rather than covering page content. At narrower sizes the page becomes one column.
Both the system reduced-motion preference and the existing application
reduced-motion setting suppress animation. Navigation rows
keep the same height and vertical positions while the panel expands, preventing
a pointer from moving to a different route during the delay.

#### Interaction and accessibility

- A fine, hover-capable pointer opens the compact panel after **140 ms**. Leaving
  schedules collapse after **220 ms**, provided pointer and focus are both
  outside. Moving into the expanded panel cancels the pending close. Explicit
  dismissal suppresses immediate reopening until the pointer leaves.
- Resizing cancels pending hover timers and imposes a **180 ms** quiet period.
  Pin/toggle controls are temporarily disabled. Rapid enter/leave and resize
  sequences cannot apply an old pending hover expansion.
- Expand/Collapse works without hover. Keyboard focus on a compact navigation
  link reveals its label; focus inside the temporary panel keeps it usable.
  Escape dismisses temporary expansion. Focus on a control that will disappear
  returns to the visible toggle; focus on a navigation icon stays on that link.
  Route changes retain the existing heading-focus behavior.
- Each link keeps an accessible name and `aria-current="page"`. The toggle
  exposes its expanded state and controlled navigation; pin/Auto expose pressed
  state. Compact controls have named tooltips rendered outside the sidebar's
  scrolling region. The connection dot has the full connection description as
  its accessible name, and About remains available in either mode.
- Coarse/touch pointers use the explicit controls and do not trigger hover
  opening. All hover/resize timers and document/media listeners are removed on
  unmount. Escape handling defers to an open DOM dialog.

The same five routes, active styling, providers and footer host remain in place.
Sidebar state changes do not remount native vault, signing or verification
providers. DOM dialogs remain above the sidebar (content z-index 51, backdrop 50,
tooltip 40, sidebar 20); no native dialog, window ownership or window-topmost
behavior changes.

#### Test-first coverage and review evidence

Initial tests failed against the old sidebar before production changes. Nine new
Playwright scenarios run under both existing projects. They exercise all seven
requested sizes (960×600, 1100×700, 1177×740, 1280×800, 1366×768, 1440×900 and
1920×1080), dynamic hysteresis, delayed expansion/leave behavior, stable navigation
targets, main/header/footer non-overlap throughout both transitions, restored
compact geometry and retained scroll position, manual and dormant-pin behavior,
keyboard focus and Escape, reduced motion, a real coarse-pointer browser context,
rapid pointer/resize sequences, both themes, all routes and one navigation tree.
Public-only contract fixtures retain an unlocked vault, selected signing PDF,
review step, active signing job and completed verification result across sidebar
changes. Existing preview/security/trust/navigation tests remain intact.

The existing real Windows responsive test is extended, rather than replaced. It
still prepares a disposable vault/PDF, signs with recovered keys, verifies valid,
tampered and wrong-key inputs, cancels a real Windows PDF picker, and checks input
hashes, absence of artifacts and worker cleanup. At each window state it now
also expands/collapses, checks reserved page space, drives actual Windows cursor
events through WebView2 for hover/leave, and checks the retained result. Pin and
unpin are exercised at the wide state. Private Python file-acceptance seams
remain test-only; there is no JavaScript or production debug API.

| Actual Windows state | Observed CSS viewport | Auto sidebar | Content columns |
| --- | --- | --- | --- |
| Default | 1266×763 | Compact | 2 |
| Maximized | 1536×794 | Docked | 2 |
| Restored | 1266×763 | Compact | 2 |
| Minimum | 946×563 | Compact | 1 |

The observed WebView2 `devicePixelRatio` is **1.25**; WinForms reports DeviceDpi
96. Both are recorded rather than treating either as proof of every Windows DPI
configuration. All four states retain the result, visible focus and usable
footer, with no horizontal overflow or content hidden behind an expanded panel.

- [Three representative before captures](../frontend/qa/phase4b3b1-sidebar/before/)
- [Light/dark compact, docked and temporarily expanded captures](../frontend/qa/phase4b3b1-sidebar/after/)
- [Real default/maximized/restored/minimum WebView2 captures](../frontend/qa/phase4b3b1-sidebar/native/)
- [Native geometry, pointer and verification check record](../frontend/qa/phase4b3b1-sidebar/native/responsive-checks.json)

Representative light/dark and real Windows captures were visually reviewed.
Older QA evidence is preserved separately; rerunning screenshot-producing tests
does not replace the approved historical images in this change.

#### Incremental file manifest

| File | Change in this increment |
| --- | --- |
| `frontend/src/components/SmartSidebar.tsx` | Single stateful sidebar, shared navigation definition, delayed expansion, controls, focus and tooltip handling |
| `frontend/src/sidebar.css` | Shared 72/250 px panel/workspace width, synchronized transitions, stable navigation rows and reduced-motion styling |
| `frontend/src/App.tsx` | Use the sidebar with existing connection descriptions and breadcrumb routes; provider placement is unchanged |
| `frontend/src/main.tsx` | Import sidebar styles after the existing responsive layer |
| `frontend/tests/sidebar.spec.ts` | Nine new sidebar scenarios, executed in both existing projects |
| `frontend/tests/support/native-responsive-host.ts` | Optional active-signing fixture state; existing default fixture behavior retained |
| `tests/test_desktop_responsive_native.py` | Extend existing four-state native assertions to sidebar behavior |
| `tests/desktop_verification_probe.py` | Optional sidebar checks, native cursor driving and separate evidence destination |
| `frontend/qa/phase4b3b1-sidebar/` | Before/after browser and current native evidence; no keys, passwords or document contents |
| `docs/phase4b3b-real-verification-regression.md` | This incremental regression record |

#### Final validation and limitations

| Validation | Final result |
| --- | --- |
| Full frontend suite | **236 passed (3.7 minutes)**; 0 failed, 0 skipped, 0 expected failures/unexpected passes |
| Full Python suite | **1633 passed, 8 skipped in 279.39 seconds**; 0 failed, 0 xfailed, 0 xpassed |
| Focused sidebar and inherited bridge-status suite | **20 passed in 15.7 seconds** in the primary browser project |
| Actual Windows four-state sidebar/verification test | Passed in the full Python suite, including manual and actual-pointer space-reservation checks |
| TypeScript check | Passed, exit 0; also included in production build |
| Production build | Passed, exit 0 |
| `git diff --check` and new-file whitespace checks | Passed |

All 218 prior frontend executions and 1633 Python test purposes remain green.
The increase is 18 executions from nine sidebar scenarios in the two existing
browser projects. The overlap regression was first demonstrated against the
temporary-overlay draft, then fixed by sharing the panel/workspace width. Tests
sample both transitions to reject content overlap, and check expanded action
access at each compact target size. Inherited native bridge-status descriptions
are retained, including the disconnected and shell-only states.

Forty protected engine/native implementation fingerprints match the start of
this increment. The earlier uncommitted QA directories and tracked historical
QA files are preserved; current evidence uses only the new sidebar folder.
Branch and HEAD remain `thesis/ui-demo` / `331a6b6`.

The behavior has been tested on one Windows workstation/monitor and installed
Edge/WebView2. Mixed-DPI monitor transfers, every physical display scale and
physical screen-reader behavior remain manual follow-up. Native hover tests move
the Windows pointer and therefore require an interactive, unobstructed desktop.
The existing eight symlink-privilege skips remain unchanged. Temporary expansion
intentionally resizes the available workspace; responsive cards can change
column count during the transition. Narrow windows still scroll vertically.
Manual sidebar preferences intentionally reset when the application restarts.
This presentation change establishes no new signer identity or cryptographic
security assurance. No dependencies, commits or pushes are introduced.

#### Auto control follow-up — retained expansion and visible state

The Auto action previously reset the mode and immediately dismissed the panel.
Its pressed state had no visible styling, and a pointer-focused button could
subsequently prevent mouse-leave collapse. This follow-up makes the control a
real toggle, visibly labelled **Auto on** / **Auto off**, with a filled purple
on state, a neutral off state and matching `aria-pressed`. A fixed button width
prevents its label change from moving adjacent controls. The compact toggle's
tooltip also names the current Auto state.

Changing Auto preserves the open panel and its focus. At compact widths, Auto on
keeps it expanded while the pointer is inside, then applies the existing 220 ms
leave delay. A mouse click no longer counts as keyboard focus that holds the
panel open indefinitely. Actual keyboard focus (`:focus-visible`) still keeps
it usable; Escape restores focus to the visible toggle before hiding controls.
Auto off disables pointer-driven opening and closing. Manual Expand/Collapse,
outside dismissal, navigation, keyboard access and Escape remain available.
Pin selects manual mode and switches Auto off; enabling Auto restores the
existing responsive policy. Wide windows still dock by default under that
policy. Manually collapsing a sidebar can retain Auto on for later hover use.
No preference is persisted and the shared-width, non-overlapping page layout is
unchanged.

Four new Playwright scenarios were written before production changes and first
failed against the prior control. They check visible/accessibility states,
fixed sizing and distinct styling, retained expansion on activation, the exact
leave-delay boundary, reopening on hover, disabled pointer automation when off,
manual controls and keyboard activation/focus/Escape. Controlled time avoids
timing-sensitive sleeps. All existing sidebar scenarios remain, with only the
Auto control's accessible-name selector updated. The native driver likewise
uses the new name, explicitly restores Auto on and drives a real leave to return
to compact rest. After native resize it parks the cursor over main content so
the measurement does not inadvertently begin with the pointer over the sidebar.
The focused actual four-state Windows test passed in **23.93 seconds**.

Incremental files in this follow-up:

| File | Change |
| --- | --- |
| `frontend/src/components/SmartSidebar.tsx` | Explicit Auto on/off flag, retain expansion, pointer/keyboard focus distinction and state-aware tooltip |
| `frontend/src/sidebar.css` | Stable Auto button sizing and distinct on/off styling |
| `frontend/tests/sidebar-auto.spec.ts` | Four new scenarios, run in both browser projects |
| `frontend/tests/sidebar.spec.ts` | Preserve existing keyboard assertion under the clearer accessible name |
| `tests/desktop_verification_probe.py` | Restore Auto deterministically and position the real pointer before native measurements |
| `frontend/qa/phase4b3b1-sidebar/` | Current sidebar captures, including separate `auto/on.png` and `auto/off.png` |
| `docs/phase4b3b-real-verification-regression.md` | This follow-up record |

| Final follow-up validation | Result |
| --- | --- |
| Full frontend suite | **244 passed (3.3 minutes)**; 0 failed, 0 skipped, 0 expected failures/unexpected passes |
| Full Python suite | **1633 passed, 8 skipped in 209.48 seconds**; 0 failed, 0 xfailed, 0 xpassed |
| Focused sidebar and Auto suite | **13 passed in 12.7 seconds** in the primary project |
| Focused actual Windows four-state test | **1 passed in 23.93 seconds**; also passes in the full Python suite |
| TypeScript check and production build | Passed, exit 0 |
| Diff and incremental whitespace checks | Passed |

All 236 prior frontend executions and all 1633 Python tests remain green. The
eight new executions come from four Auto scenarios under the two existing
browser projects. The eight skips are the unchanged Windows symlink-privilege
cases. The light/dark expanded captures and explicit Auto on/off captures were
visually reviewed. Forty protected cryptographic/native implementation files
match their starting fingerprints. Historical QA and earlier uncommitted work
are preserved. No dependencies, commits or pushes are introduced. Existing
single-workstation/DPI and physical screen-reader limitations still apply.

### Phase 4B.3B.1 — navigation, immediate Auto activation and stationary ID toggle

This correction starts from the preceding **244 frontend passed / 1633 Python
passed, 8 Windows symlink skips** state on `thesis/ui-demo`, HEAD `331a6b6`.
It implements the subsequently requested interaction semantics. Earlier results
above are historical milestones; this section describes the current behavior.

#### Causes and corrected behavior

`SmartSidebar` previously called `dismiss()` from navigation links and a
`useEffect([page])`. Both could clear temporary expansion despite the pointer
remaining inside. Separately, its `mode`, `autoEnabled` and `temporary` values
allowed conflicting policies: wide Auto was treated as docked, unpinning selected
manual mode, and enabling Auto from outside did not arm a close timer.

The sidebar now has one **mode** (`auto`, `pinned`, `manual`) and one **open**
value. Pointer presence, keyboard focus and pending timers are tracked separately.
Auto's on/off indicator is derived from mode, rather than independently stored.
Navigation links and route updates do not dismiss the sidebar. The same component
and single navigation tree remain mounted while page content changes.

| Mode / event | Current behavior |
| --- | --- |
| Auto, pointer enters | Expand after the existing 140 ms hover delay on a fine pointer |
| Auto, navigation while pointer stays inside | Keep expanded through every route change |
| Auto, pointer leaves | Collapse after 220 ms if keyboard focus is also outside |
| Auto, pointer re-enters before close | Cancel the pending close |
| Enable Auto or unpin while inside | Stay expanded; the next leave starts normal collapse |
| Enable Auto or unpin while outside | Arm the close immediately; no preliminary manual Collapse is needed |
| Pinned with sufficient width | Keep expanded; Unpin returns directly to Auto |
| Manual | Preserve explicit open/closed state; pointer movement does not automate it |
| Escape in an expanded, unpinned panel | Close explicitly and preserve visible focus; suppress immediate reopening until a genuine leave/entry |

**Intentional policy correction:** Auto now follows pointer/keyboard presence at
every supported width. It no longer stays expanded solely because a window is
wide. Pin provides persistent expansion. The existing 1340/1280 px hysteresis
continues to govern pin availability and a dormant pin when resizing. Unpin is
available even when the window has become narrow, so it cannot trap the user in
an inactive pinned state. These revise earlier wide-Auto and disabled-Unpin test
expectations to match the approved correction, while retaining their responsive
and narrow-window safety assertions.

Mode changes, explicit dismissal, resize and unmount cancel outdated hover
timers. Resize keeps the 180 ms quiet period, cancels pending opening, and
reconciles a currently open Auto panel after the quiet period. Focus on controls
that might be hidden is restored before resize disables the toggle. Keyboard
focus still holds Auto open; pointer focus does not hold it indefinitely. Coarse
pointers retain explicit controls. Shared 72/250 px panel/workspace widths,
synchronized 200 ms transitions, reduced motion, themes and action footers remain.
The sidebar continues to reserve space beside page content.

The old `HybridKeyId` used a native details/summary element. Opening it changed
its flex basis to a full row and changed its summary label to Hide full ID,
moving the control away from Copy. `HybridKeyId()` now renders one actual button
labelled **View full ID** in a shared, nonwrapping control container with Copy.
The label and reserved button width stay constant. Only the chevron rotates;
`aria-expanded` exposes state and `aria-controls` identifies a unique, hidden or
visible region below the row. Enter, Space and pointer activation use the same
controlled toggle. Full text remains focusable/selectable and exact.

Two browser layout effects also needed protection: scroll anchoring could move
the entire row vertically, and the first vertical scrollbar could shift both
controls horizontally. Workspace screens containing a Hybrid Key ID now disable
automatic scroll anchoring and reserve a stable scrollbar gutter. Existing
explicit focus/scroll behavior still works. Responsive wrapping may place the
abbreviated ID above the control group when space requires it; expanding details
does not reposition either control. Existing exact-copy, two-second feedback,
repeat-click restart, stale-response guards, value-change reset and cleanup remain.

#### Regression evidence

Seven new Playwright scenarios run under both existing browser projects. The
initial six scenarios produced **5 failures and 1 pass** against the prior
implementation, demonstrating the navigation, unpin/mode and ID-control defects
while preserving the already-correct re-entry cancellation. Coverage includes:

- Every route with the pointer inside, across 960×600, 1100×700, 1280×800,
  1366×768, 1440×900 and 1920×1080, using actual dynamic resizing.
- The 219/220 ms leave boundary, repeated re-entry, unpin inside/outside,
  enabling Auto from manual mode while outside, stale-timer cancellation and
  subsequent hover without a preliminary Collapse.
- Existing unlocked-vault, selected-PDF, signing-job and verification provider
  state. The inherited screen-local signing accordion still chooses its normal
  initial step on remount; this phase does not alter that functional flow.
- Repeated Enter/Space/pointer ID toggles with unchanged absolute button and
  Copy rectangles, a constant visible label, changed chevron direction, exact
  full ID, linked accessible region and exact clipboard argument at every size.
- A viewport fitted to collapsed content so expansion first requires a vertical
  scrollbar, checking unchanged control positions across that boundary.

Existing key-ID tests now target the real button and assert its expanded state
instead of expecting a changing summary label. Existing sidebar tests retain
their purposes under the explicit Auto/Pin policy above. Prior preview, native
contract, workflow, accessibility, clipboard and security tests remain.

The actual Windows probe drives real cursor clicks through all five sidebar
routes at default, maximized, restored and minimum window states. It checks
navigation retention, delayed collapse/re-entry, Auto activation inside/outside,
unpinning in both pointer positions when pinning is available, fixed ID-control
rectangles in both states and exact full public IDs. The maximized check exposed
the scrollbar-induced horizontal shift before the gutter fix. The completed
four-state probe then passed in **29.83 seconds**. Its original real signing
setup, valid/tampered/wrong-key verification, real picker cancellation,
unchanged-input hashes, no-artifact and worker cleanup assertions remain intact.
Captures wait for a WebView2 compositor frame after DOM acceptance.

Observed CSS viewports remain 1266×763, 1536×794, 1266×763 and 946×563;
`devicePixelRatio` is 1.25 and WinForms reports DeviceDpi 96. Auto rests compact
in all four. Pinning is deliberately unavailable at the narrow states, recorded
as inapplicable pin checks rather than adding test skips. The maximized state
exercises both unpin cases. There are still two content columns at default,
maximized and restored size, and one at minimum size.

- [Current light/dark and ID-toggle screenshots](../frontend/qa/phase4b3b1-interactions/)
- [Actual Windows acceptance captures](../frontend/qa/phase4b3b1-interactions/native/)
- [Native navigation, mode, ID and verification check record](../frontend/qa/phase4b3b1-interactions/native/responsive-checks.json)

#### Changed files in this correction

| File | Change |
| --- | --- |
| `frontend/src/components/SmartSidebar.tsx` | Coherent three-mode state, route-independent expansion, immediate mode reconciliation and safe timers/focus |
| `frontend/src/components/HybridKeyId.tsx` | One stable View full ID button, shared control group and uniquely linked expandable region |
| `frontend/src/responsive.css` | Stable control row, chevron state, scrollbar gutter and scroll-anchor protection |
| `frontend/tests/sidebar-navigation-id.spec.ts` | Seven new navigation/mode/ID-layout scenarios |
| `frontend/tests/sidebar.spec.ts` | Explicit current Auto/Pin policy, preserved responsive assertions and current captures |
| `frontend/tests/key-id-interactions.spec.ts` | Stable-label button selectors and explicit expanded-state assertions; previous copy/reset/cleanup checks retained |
| `frontend/tests/responsive-native.spec.ts` | Existing keyboard/copy/error test targets the actual disclosure button |
| `tests/desktop_verification_probe.py` | Actual Windows pointer acceptance for all three fixes, state/geometry evidence and compositor-aware captures |
| `tests/test_desktop_responsive_native.py` | Require all new acceptance flags and current Auto/Pin policy |
| `frontend/qa/phase4b3b1-interactions/` | Separate current evidence; earlier captures remain preserved |
| `docs/phase4b3b-real-verification-regression.md` | This correction record |

| Final validation | Result |
| --- | --- |
| Full frontend suite | **258 passed (4.6 minutes)**; 0 failed, 0 skipped, 0 expected failures/unexpected passes |
| Full Python suite | **1633 passed, 8 skipped in 325.52 seconds**; 0 failed, 0 xfailed, 0 xpassed |
| Focused sidebar/navigation/ID/copy suite before the gutter correction | **25 passed in 26.8 seconds** in the primary project |
| Focused scrollbar-boundary regression, both projects | **2 passed in 3.4 seconds** |
| Focused actual Windows four-state acceptance | **1 passed in 29.83 seconds**; the compositor-aware probe also passes in the full suite |
| TypeScript check | Passed, exit 0; also included in the production build |
| Production build | Passed, exit 0 |
| Diff and incremental whitespace checks | Passed |

All 244 prior frontend test purposes remain valid under the explicitly revised
Auto/Pin and fixed-label policy. The increase is 14 executions from seven new
scenarios across both existing browser projects. All 1633 Python test purposes
remain green. The eight skips are the existing Windows symlink-privilege cases;
there are no new skips or expected failures. Current light/dark browser captures
and real default/maximized/restored/minimum captures were visually reviewed.
Forty protected engine/native implementation fingerprints match the start of
this correction. Earlier QA evidence and pre-existing uncommitted work are
preserved. Branch and HEAD remain `thesis/ui-demo` / `331a6b6`.

The existing one-workstation/monitor, mixed-DPI and physical screen-reader
limitations remain. Native tests require an interactive desktop and move the
Windows pointer. File acceptance remains a private Python GUI-thread test seam;
real file-picker cancellation is still exercised. Browser clipboard accuracy is
tested at its API boundary. No new trust, compliance or cryptographic-security
claim follows from these presentation changes. Cryptographic engines, vault/PDF
formats, bridge methods, worker ownership, permissions, authentication and public
return contracts are unchanged. No packages, commits or pushes are introduced.
