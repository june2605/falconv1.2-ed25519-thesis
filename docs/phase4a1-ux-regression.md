# Phase 4A.1 — Desktop UX refinement regression report

## Starting state and audit

2026-11-05, `D:\Final_Thesis_GitHub`, `thesis/ui-demo`, HEAD `e3bde80`.
The existing Phase 4A frontend and README changes were uncommitted when work
started. They were preserved and refined in place. No dependencies were added
or installed; no commits, pushes, worktrees or branch/history changes were made.

The [audit was written before production changes](phase4a1-ux-audit.md).
The original source/screenshots showed all signing steps expanded, 207 px
dropzones, large pre-selection illustrations, small 9–11 px text, repetitive
preview labels, low vault controls and a document-scrolling topbar.
Signing and verification actions began at y=836 and y=911 respectively on a
1366×768 viewport. The existing Dashboard composition was retained.

Before evidence: five original screenshots and `measurements.json` in
`frontend/qa/phase4a1/before/`. The original Phase 4A report and twelve original
`frontend/qa/screenshots/` captures remain unchanged.

## Changes to the workflows

### Sign Document

One step expands at a time: Choose PDF → Select vault → Review and sign.
Choosing a document advances to the vault step. Completed headings show concise
summaries and reopen for editing. Removing a document resets progression and
disables dependent steps. Step changes move keyboard focus to the active heading.
Demo unlock returns focus to Continue to review when that action replaces its opener.

The document dropzone is compact. Before selection, a small, truthful empty
state replaces the paper illustration. After selection, the right column keeps
an illustrative workspace, metadata and an expand dialog; it never renders or
uploads PDF content.

The shell owns the action footer, outside the main scrolling area. Back,
Continue, Preview unlock and review actions remain predictable at short heights.
**Sign PDF is disabled even with a selected document and demo-unlocked vault.**
Its visible explanation says the native signer is not connected. A separate
secondary Preview signing action rehearses UI state only. Its result explicitly
says no PDF was signed; it offers labelled JSON, never a signed PDF. The previous
illustrative output filename and signing-success check icon were removed from
the result presentation. No cryptographic success is simulated.

### Verify Signature

The compact document and public-key source fields stay together in the left
column. The right column shows concise layer states, an honest initial
No verification performed state and the separate identity disclosure.
Detailed result metadata and example controls use progressive disclosure.

**Verify PDF is disabled**, with a persistent native-unavailable explanation.
Selecting a file never populates pass/fail results. Explore example results
requires an explicit user action; each example remains labelled as such, with
independent Ed25519 and Falcon-512 states and no claimed cryptographic execution.
The user must still supply both filenames when exploring the public-file mode.
Mathematical validity, signer identity and unavailable signing time remain distinct.

### Key Vault

Name, algorithm pair, status and Unlock/Lock are at the top of the vault card.
The demo hybrid ID follows. Public details, password change, encrypted backup
and restore form a compact management group. The keyboard-accessible options
menu and empty state remain available. The side panel keeps concise local-key,
password, identity and recovery disclosures. No real password or private key is
requested, retained or displayed, and no vault operation is performed.

### Dashboard, Settings and shared layout

Dashboard keeps the approved two action cards, vault/algorithm row and truthful
empty activity. Copy is functional, typography is larger, spacing is tighter and
redundant page-level preview labels are removed. There are no fictional metrics.

Settings retains working Light/Dark/System, reduced motion, language placeholder
and reset. Theme miniatures are shorter and About is a compact panel with
expandable research limitations. The About dialog remains available globally.

Shared refinement tokens define 28–30 px page headings, 18 px section headings,
14 px body/control text, 12 px meaningful metadata and a 4 px spacing scale.
Tiny decorative text inside the paper illustration is not application metadata.
No typography is reduced to force pages to fit. A single main work area scrolls
beneath a stable 60 px topbar; the sidebar and task actions remain stable. Long
or expanded content can scroll naturally. Dialogs have viewport-relative bounds
and their own scrolling only while the background is modal/inert.

## Measured outcome at 1366×768

Coordinates are CSS pixels from the viewport top. Raw after measurements are
`frontend/qa/phase4a1/after/measurements.json`.

| Item | Before | After |
| --- | --- | --- |
| Dropzone | 207 px high | 78 px high |
| Sign next action / review action | Preview at y=836–877 | Choose PDF y=287–328; persistent review Sign PDF y=710–751, disabled |
| Verify action | Preview at y=911–952 | Persistent Verify PDF y=710–751, disabled |
| Vault unlock | y=655–693 | y=254–295 |
| Vault password change | y=767–805 | y=515–556 |
| Vault encrypted backup | y=767–805 | y=564–605 |
| Initial Dashboard / Vault / Settings | 909 / 902 / 849 px document heights | Main content equals its 708 px available height; no initial vertical overflow |
| Initial Sign / Verify | 997 / 1049 px document heights | Main content equals its 632 px available height above the action footer |

This is measured initial content, not a fixed-height requirement for every state.
Expanded examples/results, narrow layouts and scaled windows may scroll. The
action footer remains outside the scroll region; no content is hidden using
overflow clipping to manufacture a one-screen result.

## Verification and exact results

Environment: existing Node 26.13.0, npm 11.20.0, installed Edge 156.0.4314.58,
Windows and existing Python `.venv`. All browser tests use the production bundle,
three workers, no retries. No external API or native bridge is connected.

| Command | Result |
| --- | --- |
| `npm run typecheck` | Passed separately, exit 0, no TypeScript diagnostics |
| `npm run build` | Passed; strict TypeScript check and Vite 8.3.6 production build, exit 0 |
| `npm run test:e2e` | **80 passed (1.1m)**, 0 failed, 0 skipped, 0 xfails/xpasses |
| `npx playwright test tests/visual.spec.ts --reporter=list` | **2 passed in 7.3 s** after refining capture setup to select Light/Dark through the actual settings controls |
| Root: `.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` | **1441 passed, 8 skipped in 104.42 s**, 0 failures/xfails/xpasses |

Final JS: 372.81 kB (117.14 kB gzip); CSS: 63.23 kB (12.61 kB gzip), plus local
font assets. The original theme stays intact in `styles.css`; the small desktop
refinement layer in `desktop.css` centralizes the new density and layout rules.

All 64 earlier browser-test purposes remain: 48 workflow tests, 14 accessibility/
responsive tests and two visual capture tests. Assertions referencing changed
headings and expanded steps now follow the intentional new navigation. Signing
prerequisite assertions now also require the real Sign PDF action to stay disabled.
Verification examples must explicitly open their disclosure. No tests were
deleted, skipped, marked expected-failure or relaxed to permit genuine signing.

Sixteen new browser executions cover five desktop/effective viewport sizes,
expanded-step editing, independent examples, action visibility/hit testing after
scroll, readable metadata, both vault states and device-scale approximation.
New progression/reachability tests were added before production changes; the
initial progressive-step assertion failed against Phase 4A as expected.

Axe found no violations in the five audited light/dark screens and modal under
WCAG 2 A/AA and 2.1 AA tags. No rules/nodes are excluded. Reduced motion stabilizes
theme-color measurements; ordinary motion runs in workflow tests. Keyboard
checks preserve skip navigation, route focus, dialog containment/return, Escape
and menu navigation. The main scroll region is checked for horizontal overflow
as well as the document. This is not a formal accessibility certification.

The eight Python skips still require Windows Developer Mode or symlink privilege.
No Python source, tests, benchmark data, vault/PDF format, algorithm or API changed.

## Screenshots and actual visual review

Current captures: **40 PNGs** in `frontend/qa/phase4a1/after/`:

- All five initial screens in Light and Dark at both 1366×768 and 1920×1080: 20.
- Vault-selection/review signing states, example results, unlocked vault, native
  entry dialog and selected Dark preference at both sizes: 12.
- Sign review, Verify and Vault at 1280×720 and 1600×900: 6.
- Effective 1093×614 at deviceScaleFactor 1.25, one capture per test project: 2.

| View | Screenshot |
| --- | --- |
| Dashboard, 1366 Light | [Open](../frontend/qa/phase4a1/after/desktop-1366-dashboard-light.png) |
| Sign, 1366 Light | [Open](../frontend/qa/phase4a1/after/desktop-1366-sign-light.png) |
| Verify, 1366 Light | [Open](../frontend/qa/phase4a1/after/desktop-1366-verify-light.png) |
| Vault, 1366 Light | [Open](../frontend/qa/phase4a1/after/desktop-1366-vault-light.png) |
| Settings, 1366 Light | [Open](../frontend/qa/phase4a1/after/desktop-1366-settings-light.png) |
| Sign review, 1920 | [Open](../frontend/qa/phase4a1/after/desktop-1920-sign-ready.png) |
| Verify, 1920 Dark | [Open](../frontend/qa/phase4a1/after/desktop-1920-verify-dark.png) |
| Vault, 1920 | [Open](../frontend/qa/phase4a1/after/desktop-1920-vault-light.png) |
| Sign review, 1280×720 | [Open](../frontend/qa/phase4a1/after/1280x720-sign-review.png) |
| Scale approximation | [Open](../frontend/qa/phase4a1/after/desktop-1366-scale125-sign.png) |

Actual images were inspected, including before Sign/Verify, all five initial
1366 screens, review and dark states, 1280 task screens, 1600 Vault and scaling.
The controls have no accidental clipping/overlap in the checked states. Test
hit checks assert the action center is not covered by another element, including
after scrolling. At smaller heights, secondary content scrolls normally while
the action footer stays reachable. No horizontal overflow was detected at the
tested sizes, including the preserved 900/768/390 px checks.

`npm run test:visual` regenerates the 32 primary captures; the desktop UX tests
generate the other eight. Old captures are preserved. The images are visual QA
evidence, not automated pixel-diff baselines.

## Changed files in this refinement

These are changes relative to the pre-existing, uncommitted Phase 4A work.

| File | Change |
| --- | --- |
| `frontend/src/App.tsx` | Stable shell/main scrolling and action-footer host; reduce repeated status copy |
| `frontend/src/main.tsx` | Load the desktop refinement styles after the preserved theme |
| `frontend/src/desktop.css` (new) | Shared type/spacing tokens, density, shell/footer and responsive rules |
| `frontend/src/components/TaskFooter.tsx` (new) | Controlled portal into shell-owned persistent actions |
| `frontend/src/components/WorkflowStep.tsx` (new) | Accessible expandable signing steps and summaries |
| `frontend/src/components/DocumentPicker.tsx` | Compact copy; decorative PDF icon is hidden from assistive text |
| `frontend/src/components/DocumentPreview.tsx` | Compact empty state; illustration only after selection |
| `frontend/src/components/ui.tsx` | Focus fallback when demo unlock replaces the dialog opener |
| `frontend/src/pages/SignDocument.tsx` | Progressive workflow, persistent navigation and disabled real signing |
| `frontend/src/pages/VerifySignature.tsx` | Compact fields, example disclosure, separate layers and disabled real verification |
| `frontend/src/pages/KeyVault.tsx` | Top-level Unlock/Lock and compact management/security groups |
| `frontend/src/pages/Dashboard.tsx` | Functional copy and less redundant preview messaging; preserve composition |
| `frontend/src/pages/Settings.tsx` | Compact About and limitations disclosure; preserve all preferences |
| `frontend/tests/helpers.ts` | Shared example disclosure and review navigation |
| `frontend/tests/workspace.spec.ts` | Adapt prior assertions to intentional copy/progression; preserve test purposes |
| `frontend/tests/accessibility.spec.ts` | Exercise new progression/disclosure and check main-area overflow |
| `frontend/tests/visual.spec.ts` | Light/dark, initial/workflow/dialog captures; retain original artifacts |
| `frontend/tests/desktop-ux.spec.ts` (new) | Reachability, progression, examples, metadata and scale regressions |
| `frontend/README.md` | Current usage, architecture, counts and capture locations |
| `frontend/qa/phase4a1/before/` (new) | Five PNGs and measured starting-state JSON |
| `frontend/qa/phase4a1/after/` (new) | Forty PNGs and measured final-state JSON |
| `docs/phase4a1-ux-audit.md` (new) | Pre-implementation audit and decisions |
| `docs/phase4a1-ux-regression.md` (new) | This report |

## Remaining limitations

This is a frontend-only prototype. Native signing/verification/vault operations,
PDF rendering, trusted identity, authentication and databases remain unimplemented.
The current shallow PDF/header and public-key filename selection checks cannot
establish that a PDF is signed, keys match or signatures are valid. Example
outputs make no claim about the selected document.

The 125% test is browser viewport/DPR emulation, not physical Windows DPI or
pywebview/WebView2 testing. No OS display setting was changed. Physical high-DPI
monitors, screen readers and other browsers/platforms remain unverified. At small
or scaled heights, expanded or long content may need ordinary main-area scrolling;
the design intentionally preserves readability and reachable actions.

Private-key operations remain outside JavaScript. No compliance, legal identity,
secure memory erasure or compromised-device resistance is claimed. Dependencies,
bridge contracts, Python public APIs and the inherited cryptographic protocol
are unchanged.

## Final pre-commit visual cleanup

The approved layout and design system were preserved. Settings now shows a
downward chevron beside Research limitations, with an upward state when open
and hover feedback. Existing native `details` keyboard behavior is retained;
regression assertions exercise Enter/Space expansion and the meaningful content.

Dashboard was measured before and after this cleanup at 1366×768: the main
area has `clientHeight = scrollHeight = 708` px, with no bottom overflow.
No spacing, typography or card-size reduction was needed. Its signing card now
explicitly describes the demo workflow, and its vault footer always states that
no keys are loaded. The vault security panel labels local signing as future
native integration. UI PREVIEW and DEMO indicators remain in place.

Files changed in this cleanup: `frontend/src/pages/Settings.tsx`,
`frontend/src/desktop.css`, `frontend/src/pages/Dashboard.tsx`,
`frontend/src/pages/KeyVault.tsx`, `frontend/tests/workspace.spec.ts` and this
report. Existing QA captures under `frontend/qa/phase4a1/after/` were regenerated.
All five final 1366 light-mode screenshots were visually reviewed, as was the
expanded Settings disclosure. Its chevron rotation was also checked directly.

Final commands: `npm run typecheck` passed; `npm run build` passed;
`npm run test:e2e` completed with **80 passed (1.1m)**, **0 failed, 0 skipped,
0 xfails/xpasses**. The suite includes the existing accessibility checks.
No dependencies or Python modules changed; Python tests were not rerun for this
frontend-only cleanup. No commit or push was performed.
