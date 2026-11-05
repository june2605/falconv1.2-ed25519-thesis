# Phase 4A — Professional desktop UI preview

## Scope and baseline

Implemented on `thesis/ui-demo` in `D:\Final_Thesis_GitHub`, starting from a clean
working tree at `e3bde802595fe4251cb1d67f27390564e2068cde` (`e3bde80`). No branch,
history, commit or push operation was performed. No worktree was created.

The inherited Python baseline was rerun using the existing `.venv`: **1441
passed, 8 skipped**, unchanged. No existing Python source, Python test,
cryptographic implementation, encrypted vault/PDF format or benchmark dataset
was modified. The eight skips require Windows Developer Mode or symlink privilege.
Only frontend npm dependencies were installed; no Python packages or browser
binaries were installed.

## Delivered behavior

- Persistent HybridSign navigation with five screens, breadcrumb, keyboard skip
  link, route focus and browser history. Desktop layouts target 1366×768 and
  1920×1080, with narrower responsive layouts.
- Dashboard with two actionable document cards, clearly labelled demo vault,
  inherited algorithm sequence and an initially empty activity list. Activity
  describes actual UI-preview interactions, not fabricated document processing.
- Signing workflow with drag/drop or file picker, metadata, locked/unlocked demo
  vault, prerequisites, loading, cancellation and a clearly labelled result.
  The paper preview is an illustration; no PDF is rendered or signed.
- Verification workflow with public-key selection placeholder, separate Ed25519
  and Falcon-512 example results, success/rejection/unreadable scenarios and
  expandable details. Mathematical validity and signer identity remain separate.
- Vault empty, locked and unlocked examples; validated naming, focus-contained
  dialogs, keyboard-accessible options menu, lock, public details, copy demo ID,
  password-change, encrypted-backup and restore entry points. Native requests
  report unavailable. No password field, private key or real vault operation.
- Working Light/Dark/System preferences and reduced-motion control; English
  language placeholder, version/about and preview reset. State resets on reload.
- Local Inter font, Lucide icons, Tailwind/Vite integration and one shared set
  of slate/indigo design tokens, borders, spacing, buttons and feedback states.

All simulated actions are explicitly labelled UI PREVIEW, DEMO or EXAMPLE.
The only export is a user-requested, labelled JSON preview summary with
`cryptographyPerformed: false` and `nativeBridgeConnected: false`. No unsigned,
incomplete, purportedly signed or purportedly verified PDF is offered for download.
No fake encrypted backups are generated.

## Exact commands and results

Commands run from `frontend/` unless noted. Final functional run: 2026-11-05,
Windows, Node **26.13.0**, npm **11.20.0**, installed Microsoft Edge
**156.0.4314.58**, three Playwright workers, no retries.

| Command | Result |
| --- | --- |
| `node --version` / `npm --version` | `v26.13.0` / `11.20.0`, inspected before selecting dependencies |
| `npm install --no-fund` | Frontend dependencies installed; exact versions pinned and lockfile created |
| `npm ls --depth=0` | All 17 direct dependency entries resolved without missing/invalid entries |
| `npm run typecheck` | Passed, exit 0, no TypeScript diagnostics |
| `npm run build` | Passed, exit 0; TypeScript check plus Vite 8.3.6 production build |
| `npm run test:e2e` | **64 passed in 42.8 s**, 0 failed, 0 skipped, 0 expected failures/unexpected passes |
| `npm run test:visual` | **2 passed in 5.3 s**; six captures per viewport, 12 PNG artifacts |
| `npm run dev` + installed Edge headless smoke | Vite ready in 345 ms on 127.0.0.1:5173; dashboard rendered, signing dropzone visible, no browser runtime/console errors |
| `npm audit --json` | Exit 0; **0 reported vulnerabilities** at inspection time |
| Root: `.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` | **1441 passed, 8 skipped in 71.11 s**, 0 failures, 0 xfails/xpasses |
| Root: `git diff --check` | Exit 0, no whitespace errors; only Git's existing CRLF-to-LF conversion notice for README |

Final production assets: JavaScript **371.52 kB** (**116.94 kB gzip**), CSS
**45.35 kB** (**9.87 kB gzip**), plus bundled font assets. Generated assets and
dependency installations are ignored, not added to source control.

The frontend tests run against the production bundle through Vite preview at
127.0.0.1:4173. The 32 test definitions run in both viewport projects:

| Test file | Per viewport | Both viewports | Coverage |
| --- | ---: | ---: | --- |
| `tests/workspace.spec.ts` | 24 | 48 | Navigation, empty dashboard, visible main actions, file/header/size/drop validation, metadata removal, sign prerequisites/loading/result, JSON-only download, cancellation, native errors, vault create/lock/unlock/clear/restore, public details, all five verification examples, public-key filename prerequisites, appearance/system preference, reset, storage and network/runtime checks |
| `tests/accessibility.spec.ts` | 7 | 14 | Five light/dark page audits, modal audit and keyboard/focus/menu test, all five routes at 900/768/390 px without horizontal overflow |
| `tests/visual.spec.ts` | 1 | 2 | Six screenshot states per viewport |

Axe uses WCAG 2 A, WCAG 2 AA and WCAG 2.1 AA tags. No violations were detected
in the audited states. Low-contrast secondary text found during development was
corrected. Theme audits disable transitions using the supported reduced-motion
preference so they measure settled theme colors; ordinary motion/loading is
tested separately. No rules or nodes are excluded. This is not a formal
accessibility certification or a substitute for screen-reader user testing.

The oversized-file test constructs its synthetic File in browser memory because
Playwright's buffer upload is itself capped at 50 MB. No large disk fixture was
added. Other browser fixtures contain tiny synthetic document/header or public-
selection bytes; no private keys or original research documents are used.

## Visual review

Twelve screenshots are in `frontend/qa/screenshots/`. Captures use loaded local
fonts, remove transient toasts and start at scroll position zero. The native
dialog capture uses the actual viewport; other captures include full page content.
These are review artifacts, not pixel-comparison tests.

| State | 1366×768 | 1920×1080 |
| --- | --- | --- |
| Dashboard / initial empty activity | [Screenshot](../frontend/qa/screenshots/desktop-1366-dashboard.png) | [Screenshot](../frontend/qa/screenshots/desktop-1920-dashboard.png) |
| Sign / selected sample, unlocked demo | [Screenshot](../frontend/qa/screenshots/desktop-1366-sign-ready.png) | [Screenshot](../frontend/qa/screenshots/desktop-1920-sign-ready.png) |
| Verify / illustrative two-layer pass | [Screenshot](../frontend/qa/screenshots/desktop-1366-verify-example.png) | [Screenshot](../frontend/qa/screenshots/desktop-1920-verify-example.png) |
| Vault / unlocked demo | [Screenshot](../frontend/qa/screenshots/desktop-1366-vault.png) | [Screenshot](../frontend/qa/screenshots/desktop-1920-vault.png) |
| Native password-change entry | [Screenshot](../frontend/qa/screenshots/desktop-1366-native-entry.png) | [Screenshot](../frontend/qa/screenshots/desktop-1920-native-entry.png) |
| Settings / dark mode | [Screenshot](../frontend/qa/screenshots/desktop-1366-settings-dark.png) | [Screenshot](../frontend/qa/screenshots/desktop-1920-settings-dark.png) |

Visual inspection covered hierarchy, spacing, navigation, light/dark surfaces,
document workspace, separate result layers and dialog proportions. Both primary
dashboard cards are entirely above the fold at both requested desktop sizes;
automated bounding-box assertions enforce that. Some secondary content scrolls
at 1366×768. The 1920 layout centers a bounded content area rather than stretching
cards across the entire screen. No horizontal overflow was detected at the
additional tested narrower widths.

## Changed-file manifest

Existing file modified:

| File | Change |
| --- | --- |
| `README.md` | Added local frontend startup and explicit separation from the existing Streamlit/Python setup |

New files:

| File | Purpose |
| --- | --- |
| `frontend/.gitignore` | Ignore dependencies, builds and test runtime artifacts |
| `frontend/package.json` | Exact dependency pins, Node range and scripts |
| `frontend/package-lock.json` | Reproducible npm resolution |
| `frontend/index.html` | Accessible language/title/viewport entry |
| `frontend/public/mark.svg` | Original HybridSign mark |
| `frontend/tsconfig.json` | Strict TypeScript/no-unused checks |
| `frontend/vite.config.ts` | React/Tailwind, relative asset base, loopback-oriented local workflow |
| `frontend/playwright.config.ts` | Installed Edge, production test server and two desktop projects |
| `frontend/src/main.tsx` | React/provider entry and locally bundled Inter |
| `frontend/src/App.tsx` | Application shell, sidebar, breadcrumb, route focus and footer |
| `frontend/src/models.ts` | Explicit preview-only public models |
| `frontend/src/hooks.ts` | Routing and abortable preview task state |
| `frontend/src/styles.css` | Shared tokens, components, themes, motion and responsive rules |
| `frontend/src/state/workspace.tsx` | In-memory vault, activity, preferences and notifications |
| `frontend/src/services/demo.ts` | Central demo behavior, PDF selection metadata and labelled JSON export |
| `frontend/src/native/contracts.ts` | Types-only future allowlist and explicit native-unavailable error |
| `frontend/src/components/ui.tsx` | Shared buttons, badges, notices, dialogs, focus restoration and toasts |
| `frontend/src/components/DocumentPicker.tsx` | Local picker/dropzone, errors and stale-selection cancellation |
| `frontend/src/components/DocumentPreview.tsx` | Honest illustrative document workspace and expanded dialog |
| `frontend/src/components/VaultDialogs.tsx` | Vault entry points, validation and native-unavailable feedback |
| `frontend/src/pages/Dashboard.tsx` | Main document actions, vault/algorithm cards and session activity |
| `frontend/src/pages/SignDocument.tsx` | Three-step signing UI preview |
| `frontend/src/pages/VerifySignature.tsx` | Scenario controls, independent layers and trust distinction |
| `frontend/src/pages/KeyVault.tsx` | Vault states, menu, public metadata and lifecycle entry points |
| `frontend/src/pages/Settings.tsx` | Theme, motion, language, about and preview reset |
| `frontend/tests/helpers.ts` | Shared browser navigation, sample and unlock helpers |
| `frontend/tests/workspace.spec.ts` | Functional production-browser regressions |
| `frontend/tests/accessibility.spec.ts` | Axe, keyboard and responsive checks |
| `frontend/tests/visual.spec.ts` | Presentation capture generation |
| `frontend/qa/screenshots/*.png` | The twelve individually linked visual artifacts above |
| `frontend/README.md` | Setup, demo guide, architecture, exact dependency table and native-boundary limitations |
| `docs/phase4a-ui-regression.md` | This report |

## Remaining limits and next integration boundary

The UI intentionally performs no cryptographic operation and is not a substitute
for the Python regression results. A valid-looking example result never proves
anything about the selected PDF. Header/extension checks are lightweight frontend
validation, not PDF parsing. Public-key files are not validated, only selected.

The future native bridge is types only, versioned and allowlisted. No JavaScript
path to arbitrary Python execution exists here. Native integration still needs
a dedicated worker, opaque-reference validation, process/thread-scoped handle
mapping, native password/save dialogs, lifecycle cleanup and an explicit error
protocol. It must preserve the existing managed vault signer, strict verifier,
captured source, protected paths, fsync/self-verification and atomic publication.
Demo-unlocked state must never become native authorization.

Private keys, real vault passwords and derived encryption keys are neither
requested nor handled. No claim is made about guaranteed Python memory erasure
or resistance to a compromised local process. Trusted signer identity, signing
timestamps, accounts, key enrollment and revocation remain outside this phase.
No FIPS, CMS, PAdES, legal identity or production-security compliance is claimed.

Only installed Edge headless was exercised. pywebview/WebView2 packaging, native
Windows shell drag/drop, browser download integration, physical high-DPI displays,
screen readers, Firefox, Safari and other operating systems were not validated.
No native worker, backend service, authentication or database was implemented.
The npm audit result is a point-in-time advisory check, not a security proof.

## Start for review

```powershell
Set-Location D:\Final_Thesis_GitHub\frontend
npm run dev
```

Open **http://127.0.0.1:5173**. Use `npm ci` first on a fresh installation.
