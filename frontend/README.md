# HybridSign UI and Windows signing — Phase 4B.3B

The approved Phase 4A.1 UI runs in a browser or in the Phase 4B.1 Windows desktop
shell. Desktop Key Vault connects real encrypted-vault creation, unlock, lock and
authenticated public metadata. File selection and masked password entry use
Python-controlled Windows dialogs; passwords/private keys never enter React.
Desktop **Sign Document** now calls the existing managed Python signer and saves
a real PDF. **Verify Signature** checks the actual complete signature pair with
selected public keys. Password change and backup/restore remain unintegrated.
Browser document workflows remain DEMO / EXAMPLE.

Phase 4A.1 refines the existing design with progressive signing steps, persistent
task actions, compact panels and readable typography. See the
[pre-implementation audit](../docs/phase4a1-ux-audit.md) and the current
[refinement report](../docs/phase4a1-ux-regression.md). The original
[Phase 4A report](../docs/phase4a-ui-regression.md) is retained as historical evidence.

## Start locally

For a native Windows window, build this frontend with `npm run build`, then run
`.\.venv\Scripts\python.exe -m desktop.launcher` from the repository root.
Install the pinned `requirements-desktop.txt` packages into that existing Python
environment first. The launcher uses `dist/` and does not require Vite to run.
See [the real-vault regression report](../docs/phase4b2a-real-vault-regression.md)
for Windows prerequisites and vault limitations. See the
[real-signing report](../docs/phase4b3a-real-signing-regression.md) for the current
signing lifecycle, disk verification and Windows evidence. The
[current verification report](../docs/phase4b3b-real-verification-regression.md)
describes the fourteen-method profile and public-source trust model.

The browser development workflow remains:

Tested on Windows with Node **26.13.0**, npm **11.20.0** and installed Microsoft
Edge. Use a Node release supported by the `engines` field in `package.json`.
The Vite server listens only on the loopback address by default.

```powershell
Set-Location D:\Final_Thesis_GitHub\frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. Dependencies are already installed in the current
workspace; `npm ci` is for reproducing the installation from the lockfile.
Browser development does not require Python or Streamlit to be running.

To check and serve the production bundle:

```powershell
npm run typecheck
npm run build
npm run preview
```

The production preview is at **http://127.0.0.1:4173**. `dist/` is generated and
ignored. It is not an installed Windows application or a production server.

## Try the interface

In native mode, **Key Vault** and the Dashboard summary show actual Python state,
not the demo card. Create chooses an absent `.hvault` file on fixed local NTFS
and confirms a 15+ character password through the native dialog. Creation leaves
the vault locked. Unlock selects/authenticates an existing file; Lock invalidates
its session. Only one selection is active per window. Close/reopen and select
the same file to recover its original public keys/ID. No inventory is persisted.
Existing destination files, unsafe storage and unsuitable ACLs reject without
overwrite or permission repair. Password change, backup and restore are disabled.

The following browser-preview steps remain available. The signing demo uses a
separate simulated vault even in native mode and cannot use/authorize real keys.

1. Start on Dashboard. Both action cards navigate to their workflows. Activity
   is initially empty and records only actions actually previewed this session.
2. On Sign Document, choose a local PDF or use the illustrative sample. Completed
   steps collapse; preview unlocking the demo vault, then **Continue to review**.
   Earlier headings reopen steps for editing. The real **Sign PDF** action is
   disabled. **Preview signing** is a separate UI rehearsal with loading and
   JSON-only results. No PDF is signed.
3. On Verify Signature, choose a file and public-key source. The real **Verify
   PDF** action is disabled. Open **Explore example results** to request an example.
   The Ed25519 and Falcon-512 example results are independent. The identity
   section always distinguishes mathematical validity from trusted identity.
4. On Key Vault, explore create, unlock, lock, public details, password change,
   encrypted backup and restore dialogs. The options menu can clear the demo
   card to show the empty state. No file is deleted or changed.
5. In Settings, switch Light/Dark/System, reduce motion, inspect the language
   placeholder and about dialog, or reset the demo vault and activity.

Privileged native-request buttons give an explicit unavailable message. No real vault
password inputs exist. **Download preview summary** exports labelled JSON,
never a PDF, encrypted vault or purported cryptographic verification report.
These JSON downloads remain browser-only; the native shell blocks downloads and
disables those controls once connected.

## Structure and boundaries

| Path | Responsibility |
| --- | --- |
| `src/App.tsx` | Persistent sidebar, breadcrumb, hash navigation and page focus |
| `src/pages/` | Dashboard, signing, verification, vault and settings screens |
| `src/components/` | Shared controls, accessible Radix dialogs/menu, progressive steps, shell-owned task footer, PDF picker and illustrative preview |
| `src/styles.css` | Preserved Phase 4A theme, Tailwind entry and component styles |
| `src/desktop.css` | Phase 4A.1 type/spacing tokens, density, stable shell, responsive layout and action-bar refinements |
| `src/models.ts` | Explicit preview-only models, separate signature-layer states |
| `src/state/workspace.tsx` | In-memory demo vault, activity, preferences and notifications |
| `src/services/demo.ts` | Centralized asynchronous UI adapter, lightweight selection checks, JSON summary export |
| `src/native/contracts.ts` | Future allowlisted native boundary, types only; native requests currently always fail explicitly |
| `src/native/desktop.ts`, `status.tsx` | Exact metadata/vault capability profiles, bounded readiness/validation and runtime status context |
| `src/native/vault.tsx` | Exact public-only native vault contract, error handling and real state separate from the demo |
| `src/components/NativeVault.tsx` | Native vault card, Dashboard summary and public-key details using the existing design |
| `src/hooks.ts` | Hash routing and cancellable preview operations |
| `tests/` | Production-browser workflow, accessibility and visual capture tests |
| `qa/screenshots/` | Preserved original Phase 4A captures |
| `qa/phase4a1/` | Before/after measurements and current desktop, dark, workflow and scale captures |

The custom design system uses locally bundled Inter, Lucide icons, slate/white
surfaces and an indigo accent. Radix supplies dialog focus containment and menu
keyboard handling. Tailwind is integrated through its Vite plugin; component
styles and shared tokens are in `styles.css` and `desktop.css`. No remote fonts or backend HTTP APIs
are required. Hash routing avoids adding a router dependency and uses a relative
Vite base for future desktop packaging.

### Native integration and preview separation

`NativeBridgeV1` is an illustrative, versioned command boundary, not an existing
implementation or a change to the Python APIs. It uses opaque document, vault
and session references. It contains no password/private-key parameters, raw
Python execution, arbitrary callable names or general filesystem operations.
`requireNativeBridge()` deliberately throws; the preview does not probe for a
bridge or silently fall back from a failed native operation to a demo result.

Phase 4B.2A extends the dedicated Python worker with four fixed vault commands.
Managed handles are issued/used/locked on that thread; only opaque references and
authenticated public metadata reach React. The original six-method vault profile accepts
no JavaScript paths or passwords. Native Windows file/password dialogs run on the
GUI thread. The existing vault filesystem/ACL/locking/atomic-create rules remain.
Close locks active access; this does not guarantee secure memory erasure.
Phase 4B.3A adds exactly `choose_pdf()`,
`sign_pdf(documentId, vaultId, sessionId, operationId)` and
`get_signing_state(operationId?)`. The signing profile has nine allowlisted
methods; metadata/vault-only profiles remain recognized explicitly. JavaScript
never supplies paths, PDF bytes, passwords or keys. The Sign Document page uses
Windows Open/Save dialogs and the currently authenticated native vault. Review
shows metadata only; there is no PDF renderer.

The same dedicated worker calls `sign_vault_document()`, preserving the original
transaction and key ownership. One job can be ready, queued or running. Native
status survives route changes and lost submission responses; reconciliation
reads the same operation ID without automatically resubmitting. Signing does
not use the five-second metadata deadline. No cancellation is offered after
queueing; normal close and conflicting vault operations are refused while active.
Only a self-verified, saved PDF is reported completed. Unknown outcomes require
reconciliation and inspection. The in-process record does not survive application
termination. Native browser downloads remain blocked.

Phase 4B.3B adds five explicit verification methods. Choose a signed PDF and
an encrypted vault through native Windows dialogs, or use the currently
authenticated vault public snapshot. Password-free metadata is UNAUTHENTICATED;
locally authenticated metadata is labelled Authenticated at selection. Neither
certifies signer identity. Verification needs no private key or unlocked vault.
Its result is only HYBRID VALID / HYBRID INVALID under the selected public pair;
no individual-layer result is inferred from timing slots. Read-only verification
shares the operation gate, owner thread, bounded admission and reconciliation
model with signing. A failed/unknown operation never becomes a mathematical result.
Legacy desktop profiles lacking verification show an unavailable view; examples
are confined to regular browser UI Preview.

### Browser-preview data and security limits

- Demo data and preferences exist only in React memory. No `localStorage`,
  `sessionStorage`, IndexedDB, cookies or service worker are used by this app.
- PDF selection checks extension, nonempty size, a 50 MiB limit and the first
  five header bytes. This is **not** full PDF validation or signature parsing.
  Only file metadata is retained; the PDF input is cleared after selection.
- Public-key selection retains filenames only in React. The browser file input
  holds its selection while mounted; contents are not read or validated.
- The sample document is illustrative metadata, not a file or signed fixture.
  The paper illustration is labelled and never presents actual PDF contents.
- The `demo:` key identifier is visibly a placeholder, not a generated hybrid-v1
  identifier. No real public or private key material is generated or displayed.
- No authentication, identity registry, trusted signing time, key lifecycle,
  cryptographic algorithm, vault format or signature format is implemented in React.
- This browser preview makes no production security or compliance claim.
  Browser behavior does not validate a pywebview installation or native worker.

## Validation

```powershell
npm run typecheck
npm run build
npm run test:e2e
npm audit
```

Playwright uses the installed **Microsoft Edge** (`channel: 'msedge'`) at
1366×768 and 1920×1080. The test server serves the **production build** on
127.0.0.1:4173, so rebuild before testing changed source. Three workers, no
retries. An existing server on that port must serve this same build.

Tests cover navigation/history/focus, file validation/drop, vault states and
dialogs, form validation, loading/cancellation, each example verification
scenario, JSON-only downloads, unavailable native requests, in-memory state,
local-only requests and browser errors. Axe checks all five screens in light
and dark against WCAG 2 A/AA and 2.1 AA tags with transitions disabled for
settled-color measurements; normal motion runs in workflow tests. Keyboard
tests cover skip navigation, dialog focus trap/return, Escape and the vault menu.
Narrower layouts are checked at 900, 768 and 390 px.

Phase 4A.1 adds action reachability, hit testing, readable metadata and progress
tests at 1280×720, 1366×768, 1600×900, 1920×1080 and 1093×614. A separate browser
context at deviceScaleFactor 1.25 approximates the last viewport at 125% scaling;
it does not test physical Windows DPI configuration. All **80** existing tests
remain; Phase 4B.1 adds **22** metadata/readiness browser executions. Phase 4B.2A
adds **20** real-state contract/UI executions plus **14** authentication-UX
executions. Phase 4B.3A adds **16** signing executions for **152** total. Phase 4B.3B adds **14** verification
executions for **166** total.
Real Windows GUI validation is in `tests/test_desktop_native.py` under Python
pytest, separate from these browser mocks.
`tests/test_desktop_vault_native.py` additionally drives two actual desktop
processes, masked native dialogs, wrong-password rejection, locking and original-
key recovery. Save/Open cancellation is automated; human file-choice acceptance
and physical multi-monitor/high-DPI behavior still need manual review.
`tests/test_desktop_signing_native.py` also signs through two real Windows
application processes with the original recovered keys, independently verifies
both saved PDFs, rejects tampering and checks that no private-key files appear.

`npm run test:visual` generates 32 current screenshots in `qa/phase4a1/after/`.
The desktop UX tests add six 1280/1600 captures and two scaling captures, for
40 current screenshots in the full suite. Original Phase 4A captures are retained.
These are visual-review
artifacts, not pixel-diff baselines. Generated HTML reports, traces, test downloads
and failure screenshots are ignored under `playwright-report/` and `test-results/`.
No browser download was needed on this workstation. A machine without Edge
needs a locally available supported browser or an explicit test configuration
change; browser installation is not performed automatically.

See [the real-vault regression report](../docs/phase4b2a-real-vault-regression.md)
for current results, changed files and platform limitations, and
[the refinement report](../docs/phase4a1-ux-regression.md) for earlier visual QA.

## Exact dependencies

All frontend direct versions are pinned; `package-lock.json` records resolved
transitive packages. Frontend dependencies are unchanged in Phase 4B.1. Python
desktop dependencies are separately pinned in `../requirements-desktop.txt`.

| Dependency | Version | Role |
| --- | --- | --- |
| `react`, `react-dom` | 19.3.1 | UI |
| `typescript` | 5.9.3 | Strict static checks |
| `vite` | 8.3.6 | Build/dev server |
| `@vitejs/plugin-react` | 6.2.1 | React integration |
| `tailwindcss`, `@tailwindcss/vite` | 4.3.4 | CSS integration |
| `lucide-react` | 1.69.0 | Icons |
| `@radix-ui/react-dialog` | 1.3.1 | Accessible dialogs |
| `@radix-ui/react-dropdown-menu` | 2.2.1 | Accessible menu |
| `@fontsource/inter` | 5.3.0 | Local font assets |
| `@types/react`, `@types/react-dom` | 19.3.0 | React type declarations |
| `@types/node` | 26.6.6 | Tooling type declarations |
| `@playwright/test` | 1.64.1 | Browser testing |
| `@axe-core/playwright` | 4.14.0 | Automated accessibility checks |
