# Phase 4C.2B — Windows installer and release validation

Phase 4C.2B packages the validated HybridSign 0.1.0 portable application in an
Inno Setup installer. It began in a clean `D:\Final_Thesis_GitHub` on
`thesis/ui-demo` at `45f03b1e662b162826867410f0d57485b9f402f5`. The inherited
baseline was 1,661 Python passes, eight Windows symlink skips and 266 Playwright
passes. The installer uses the frozen one-folder application and its existing
native dialogs, cryptographic implementations, bridge, worker, storage policy
and format. [Phase 4C.2A portable release](phase4c2a-portable-packaging.md)

The review also used the inherited [native bridge](phase4b1-native-bridge-regression.md),
[vault](phase4b2a-real-vault-regression.md), [signing](phase4b3a-real-signing-regression.md),
[verification](phase4b3b-real-verification-regression.md) and
[desktop demo](phase4c1-demo-readiness.md) regression reports.

## Install and uninstall

1. Run `HybridSign-Setup-Phase4C2B-win-x64.exe` and review the information page.
2. Use `%LOCALAPPDATA%\Programs\HybridSign` or choose a dedicated folder on a
   fixed local drive. Fresh installation requires a new or empty folder. Choose
   the Desktop shortcut if desired. Setup also creates a Start Menu shortcut.
3. Start **HybridSign** from the Start Menu. Keep the encrypted vault and all
   PDFs in a separate trusted local NTFS folder under your control.
4. Finish active signing operations and close HybridSign normally. In **Settings
   → Apps → Installed apps**, select **HybridSign version 0.1.0 → Uninstall**.

The installer uses per-user permissions, registry and shortcuts. Its Application
ID is `{3699C4A8-8612-4F01-BB26-F014797A9CBE}`. Installed Apps shows `HybridSign
thesis project` as descriptive publisher metadata. The Windows executable and
installer are unsigned, so Windows can report an unknown publisher or display
a SmartScreen prompt, depending on origin, reputation and policy. Use a trusted
distribution channel and follow local policy for unsigned software. Checksums
check artifact bytes. Authenticode publisher authentication is a separate step.
[Microsoft SmartScreen guidance](https://support.microsoft.com/en-gb/office/protect-my-pc-from-viruses)

The existing startup minimums are Windows x64, WebView2 Evergreen 111 and
.NET Framework 4.6.2. Setup reads the standard registry views and stops with
Microsoft download guidance if it cannot confirm either prerequisite. Install
missing runtimes separately from Microsoft. The installed app rechecks runtime
availability at startup. The external runtimes are separate from the bundled
WebView2 SDK loader and assemblies. [WebView2 Evergreen](https://developer.microsoft.com/microsoft-edge/webview2/) · [.NET Framework downloads](https://dotnet.microsoft.com/download/dotnet-framework)

## Build and payload

Test host was Windows 11 Pro x64 build `10.0.26200`, with Python 3.11.9,
Node 26.13.0, npm 11.20.0, WebView2 Evergreen `157.0.4341.60` and .NET
Framework `4.8.09221` (Release `533509`). The already installed compiler was
Inno Setup 6.7.1, as reported by its compiler engine and uninstall metadata.
The compiler's Authenticode status was Valid. `ISCC.exe` SHA-256 was
`eb6f4410c8db367a5f74127e8025ad2ccacc0afabbe783959d237df3050f97fb`.
The compiler reported its non-commercial profile. No compiler or dependency
installation, PATH change or elevation was needed.

```powershell
Set-Location D:\Final_Thesis_GitHub
.\.venv\Scripts\python.exe -B packaging\build-installer.py `
  --iscc 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' `
  --payload dist\portable\HybridSign `
  --output dist\installer-validated
```

Use an existing compatible Inno Setup compiler and the exact Phase 4C.2A folder.
The full `HybridSign` directory from the approved portable ZIP also works as
`--payload`. Do not hand-edit a manifest to accept a rebuilt or modified payload.
Choose a fresh output directory for each build. The build stages verified files
in a new ignored `build/installer-*` directory and compiles the official `.iss`.
The staging directory retains the generated includes and compiler log for review.
The installer and checksum, manifest and notices are written to the ignored
output directory. Reproduction fixes the inputs and procedure. It does not
promise a byte-identical installer across runs or compiler versions.

`build-installer.py` checks the complete payload file set, individual sizes and
SHA-256 values against the tracked Phase 4C.2A manifest. It rejects reparse
points, hard links, missing files, changed bytes and additional files. It copies
into a fresh staging directory and rehashes every staged file before generating
one Inno Setup `[Files]` entry per approved file. The entries use the existing
one-folder layout, original icon and complete license notices.

The **138 files, 33,970,399 bytes** include Python 3.11 and the existing Falcon,
libsodium, cryptography, pythonnet and x64 CLR bindings. They include the WebView2
SDK assemblies, x64 native loader, pywebview metadata and all compiled React
assets. The whitelist excludes vaults, keys, PDFs, development environments,
source history, tests, data and screenshots. The portable ZIP's SHA-256 remains
`6f6364e0c53921aa0370e75def1b07e4e36d0b52739563058d778db3c447a293`.
Its CRC and all 138 approved file hashes were verified again.

## Ownership, running sessions and user files

Setup uses the Inno uninstall log to remove only its payload and shortcuts.
There are no wildcard file entries, recursive delete rules, data migrations or
registration of PDF associations. The installer uses no services, scheduled
tasks, startup entries, system PATH changes, firewall changes or runtime downloads.
The frozen application continues to reject new vault and signed PDF destinations
inside its application folder.

Fresh setup refuses an occupied target. Same-version reinstall requires the
registered path and checks all existing managed payload names for byte and path
integrity before proceeding. A registered differing version or path is refused.
Uninstall checks managed paths before and after its confirmation boundary. If a
managed file has unexpected bytes or a reparse point, the operation stops.
Missing managed files may be repaired by reinstalling the same release. Unknown
extra files are left alone. If files remain after uninstall, inspect the folder
in Explorer and move user documents and vaults to safe storage before removing
an empty leftover folder. There is no automatic cleanup of unknown files.

Setup and uninstall use a read-only Windows process snapshot. They refuse
servicing when an executable named `HybridSign.exe` is running or the scan
fails, including portable copies with that name. Immediately before changing
files, Setup or uninstall opens the existing executable for write access with
read sharing denied. Windows rejects the handle while the executable image is
mapped, and a held handle blocks normal launches. Setup releases it when it
reaches the executable, after the dependencies. Uninstall allows deletion and
holds it through removal. The lock needs no write to executable contents.
Installer-driven closing and restart are disabled. Users finish signing and
close the app themselves. These checks cover the normal installed executable
path. They do not guard against an administrator or a hostile process that
renames, moves or replaces files during servicing. [Inno Setup CloseApplications](https://jrsoftware.org/ishelp/topic_setup_closeapplications.htm) · [Inno Setup uninstall log](https://jrsoftware.org/ishelp/topic_setup_uninstalllogmode.htm)

The application still uses local Argon2id/AES-GCM vault operations, native
password dialogs, the fixed bridge allowlist and EdgeChromium origin guards,
an immutable static loopback snapshot and one worker owning vault handles.
Ed25519 still signs first, Falcon-512 signs the following state and both must
verify. Original NTFS ACL and path checks and atomic publication remain in the
approved binary. Restart begins without unlocked key access. Signature validity
under selected keys does not establish signer identity, authorization at a
trusted time or any PAdES, CMS or FIPS certification.

## Redistribution review

- The complete Phase 4C.2A `THIRD-PARTY-NOTICES.txt` and package metadata/license
  directories accompany the payload. The notice covers available Python,
  Python packages, npm dependencies and fonts. Review upstream notices for
  distributions whose wheel lacks separate text, including `proxy_tools`.
- PyInstaller documents the bootloader's distribution exception. Retain the
  existing notices and verify the redistributed dependency terms independently.
  [PyInstaller license](https://pyinstaller.org/en/stable/license.html)
- Microsoft documents deployment of the loader and managed WebView2 assemblies.
  Verify the exact SDK version and redistribution terms from its NuGet package,
  and the Visual C++ runtime redistribution terms, before external release.
  .NET and the WebView2 browser runtime are installed separately by the recipient.
  [Microsoft WebView2 distribution](https://learn.microsoft.com/microsoft-edge/webview2/concepts/distribution)
- The installed Inno compiler is used for the academic project. The compiler
  is excluded from the distribution. Review commercial terms if the use changes.
  Before public release, confirm redistribution rights for the inherited icon and
  prototype code, and record the upstream notice audit. [Inno Setup licensing](https://jrsoftware.org/inno-setup/purchase)

## Acceptance and release evidence

The validated installer is `dist/installer-validated/HybridSign-Setup-Phase4C2B-win-x64.exe`.
Intermediate builds are local review artifacts. Use the checksum below to
identify the exact tested release.

| Artifact | Size and SHA-256 |
| --- | --- |
| `HybridSign-Setup-Phase4C2B-win-x64.exe` | 13,483,887 bytes · `7e1dc008c8238a8df93ca8c5cbc75db11a5b8fe77b09ed708ab0daf7ab89d8ae` |
| `HybridSign.exe` from the approved payload | 4,267,288 bytes · `1fa00d14171336bfcd8a16aabff776e3905946f5bb15bb6f389cd81c1322bfdc` |
| Complete installer payload | 138 files · 33,970,399 bytes · individual SHA-256 values in `payload-manifest.json` |
| `THIRD-PARTY-NOTICES.txt` | 192,333 bytes · matches the approved portable release |

The installer uses the compiler's 32-bit GUI stub in x64 installation mode,
with x64 Windows enforced. The installed application executable is AMD64. Both
PE files use the GUI subsystem and an `asInvoker` manifest. The setup artifact
has version `0.1.0.0` and the installed product uses `0.1.0`.

| Automated lifecycle scenario | Observed result |
| --- | --- |
| Fresh interactive wizard, disposable per-user path with spaces and `đ` | Exit 0. Non-elevated token, current-user uninstall entry, all 138 payload hashes match |
| Direct EXE, Start Menu and optional Desktop shortcuts | Each launched the actual installed GUI. The later reinstall created the Start Menu shortcut with Desktop unchecked |
| Window sizes and appearance | Default 1600×1000, maximized 1938×1038, restored 1600×1000, minimum 1200×750 physical pixels. Five screens, sidebar controls and both themes exercised |
| Native vault and PDF workflow | Masked native password controls, real Open and Save dialogs, same ID on restart, VALID for original, INVALID for modified copy and wrong keys |
| Public verification and restart | Verification succeeds while locked and with public-only metadata. Start Menu relaunch starts locked and signs and verifies again after unlocking the original vault |
| Installed library loading | Python, Falcon, libsodium and cryptography loaded from installed `_internal` paths rather than the repository environment |
| Setup or uninstall while an installed signing operation awaits Save | Exit 7 for Setup and 1 for uninstall, expected refusals. The original process stayed open, its files matched and the admitted signing operation completed |
| Changed managed file | Both servicing paths refused and preserved the test PDF placed at a managed filename. The disposable README was then restored |
| Same-version in-place reinstall | Exit 0. Reinstalled payload hashes matched and extra files remained |
| Uninstall and occupied folder check | Exit 0. All application files and shortcuts removed. Six external vault/PDF files and two extras inside the folder retained their SHA-256 hashes. Fresh Setup refused the now-occupied folder |
| Reinstall after uninstall | Exit 0 at a fresh path. Original vault unlocked with the same key ID and the original PDF verified VALID. Final uninstall exited 0 with user files intact |
| Separate Windows Installed apps click-through | A new fixture appeared in Settings. The real menu and confirmation opened uninstall, which reported success. The registry entry, both shortcuts and all application files were absent afterward |

The installed-EXE probe uses external Windows UI Automation and OS input, with
no bundled hooks or browser debugging. Its disposable password stays in memory.
It signed a 742-byte public sample into a 5,368-byte PDF. It modified an independent
copy and checked that the original source checksum stayed fixed. The 2,416-byte
encrypted vault was reopened after reinstall without key regeneration.

- [Wizard information](../frontend/qa/phase4c2b/setup-information.png) · [Setup completed](../frontend/qa/phase4c2b/setup-complete.png)
- [Installed VALID](../frontend/qa/phase4c2b/packaged-valid.png) · [Tampered INVALID](../frontend/qa/phase4c2b/packaged-tampered.png) · [Wrong keys INVALID](../frontend/qa/phase4c2b/packaged-wrong-keys.png)
- [Installed minimum window](../frontend/qa/phase4c2b/packaged-sidebar-minimum.png) · [Original signature valid after reinstall](../frontend/qa/phase4c2b/reinstalled-original-signature-valid.png)
- [Windows uninstall confirmation](../frontend/qa/phase4c2b/windows-uninstall-confirmation.png) · [Uninstall completed](../frontend/qa/phase4c2b/windows-uninstall-complete.png)
- [Lifecycle evidence](../frontend/qa/phase4c2b/installer-checks.json) · [Artifact evidence](../frontend/qa/phase4c2b/artifact-checks.json) · [Windows Settings evidence](../frontend/qa/phase4c2b/windows-installed-apps-checks.json)

To repeat the installed-EXE automation, run the command below using two empty,
disposable folders on an interactive Windows desktop. The harness refuses an
existing matching uninstall entry or shortcut and uses the registered uninstaller
only for its own fixtures.

```powershell
.\.venv\Scripts\python.exe -B tests\installer_probe.py `
  dist\installer-validated\HybridSign-Setup-Phase4C2B-win-x64.exe `
  'C:\path\to\empty-app-test-folder' 'D:\path\to\empty-test-documents' `
  frontend\qa\phase4c2b
```

An initial build used WMI to find running processes. A later trial demonstrated
an intermittent WMI/COM failure even when the application was closed. It failed
closed. The final build uses the Windows process snapshot and executable guard
described above. One build attempt rejected a script pointer type unavailable
in the installed 32-bit engine. The final binding matches that engine.
The wizard driver corrected an assumption about the versioned display name and
switched to invoking real accessible buttons after a foreground miss. The final
artifact passed the full test and separate Settings uninstall. The Settings success window needed a
second observation after the first UIA wait timed out. The registered entry and
files were confirmed removed after acknowledging the actual success dialog.

## Regression results

| Validation | Passed | Failed | Skipped | Details |
| --- | ---: | ---: | ---: | --- |
| Latest full Python suite | 1,664 | 2 | 8 | 216.79s. Zero xfails or xpasses. Includes five passing installer payload regressions |
| Initial full Python suite | 1,665 | 1 | 8 | 358.89s. The inherited desktop demo subprocess timed out |
| Isolated inherited demo follow-up | 1 | 1 | 0 | 20.96s. Native creation did not settle |
| Final isolated native replay | 3 | 0 | 0 | 61.92s. Both previously failing GUI cases and the sample PDF integrity test passed |
| Full Playwright suite | 265 | 1 | 0 | 4.1 min. One existing desktop-1920 sidebar resize assertion failed |
| Isolated desktop-1920 sidebar replay | 3 | 0 | 0 | 6.0s. Three repetitions with one worker |
| TypeScript check | 1 | 0 | 0 | Exit 0 |
| Production frontend build | 1 | 0 | 0 | Exit 0. All 12 compiled asset hashes match the approved portable release |
| Final installer build and inventory checks | 1 | 0 | 0 | Inno Setup exit 0. Installer SHA-256 and 138 payload hashes match |
| Actual installed-EXE and lifecycle automation | 1 | 0 | 0 | Passed all lifecycle assertions, including expected refusals |
| Separate Windows Settings uninstall | 1 | 0 | 0 | Registration, native confirmation, success dialog and cleanup verified |
| Portable ZIP and approved payload | 1 | 0 | 0 | Correct archive hash and CRC. All 138 file hashes match |
| Original research benchmark files | 15 | 0 | 0 | All SHA-256 values match the recorded baseline |

The two latest failures are `test_real_desktop_create_sign_verify_tamper_lock_and_restart`
in `tests/test_desktop_demo.py` and `test_real_webview_default_maximized_restored_and_minimum`
in `tests/test_desktop_responsive_native.py`. The former did not reach the
locked-vault state after the native Save dialog returned no selection. The latter
did not observe sidebar expansion after a synthetic OS pointer movement in the
default window. Both passed on the final isolated replay with the original
assertions. The installed EXE independently exercised native Save, vault creation
and sidebar expansion successfully. The timing failures have no confirmed cause,
and the full-suite results still include them. In Playwright, `frontend/tests/sidebar.spec.ts:157`
did not return to `data-expanded="false"` within the resize test's assertion
window. The same assertion passed three isolated repetitions. The full Playwright
result still records the failure. All eight Python skips are the existing Windows
symlink privilege cases. The clean-machine and manual matrix contains 11
scenarios not run.

## Clean Windows and manual acceptance matrix

| Environment or scenario | Status |
| --- | --- |
| Clean Windows 11 x64 VM | NOT RUN. No clean VM available |
| Clean supported Windows 10 x64 | NOT RUN. No clean VM available |
| Missing WebView2 on a disposable OS | NOT RUN. Primary runtime and registry left intact |
| Missing or outdated .NET Framework | NOT RUN. Primary runtime and registry left intact |
| Separate standard-user account | NOT RUN. Current account used with its non-elevated token |
| Multiple physical DPI settings or mixed monitors | NOT RUN. Four window sizes exercised on the current desktop |
| Non-English Windows locale | NOT RUN. Test automation uses English dialog captions |
| Offline launch with networking disabled | NOT RUN |
| Authenticode and downloaded-file SmartScreen behavior | NOT RUN. Build is unsigned |
| Distinct-version upgrade | NOT RUN. Only the approved 0.1.0 payload is available |
| Human installation and screen reader | NOT RUN. Automation exercised the real wizard, native dialogs and Windows Settings click-through |

Before distributing beyond this thesis review, complete the clean-machine
matrix and rights review. Validate installer behavior for a genuinely distinct
compatible version before allowing in-place upgrades. When a legitimate
publisher and certificate have been approved, sign the final artifacts and
repeat downloaded-file acceptance with the resulting publisher identity.

## Changed files

| Path | Change |
| --- | --- |
| `.gitignore` | Allow only the official `.iss` in source control |
| `README.md` | Installation, prerequisites and uninstall guidance |
| `packaging/HybridSign.iss` | Per-user Windows x64 installer and servicing checks |
| `packaging/INSTALLER-INFO.txt` | Wizard information, prerequisites and storage instructions |
| `packaging/build-installer.py` | Pinned portable payload validation, staging, compiler invocation and release metadata |
| `tests/test_installer_payload.py` | Build rejection and staging regressions |
| `tests/installer_probe.py` | External installer and installed-app acceptance |
| `frontend/qa/phase4c2b/` | Screenshots and public acceptance evidence, including the per-file capture manifest |
| `docs/phase4c2b-installer-release.md` | Installer release report |

The capture manifest records the evidence files and their SHA-256 values.
Screenshots displaying local account details or profile paths are kept out of
source control. Historical QA files regenerated during the test runs were restored.
[Capture manifest](../frontend/qa/phase4c2b/capture-manifest.json)

## Phase 4C.2B.1 — Final release regression stabilization

The starting commit was `45f03b1` on `thesis/ui-demo`. The worktree already held
the uncommitted Phase 4C.2B installer and release evidence. This follow-up changes
external tests and this report. The existing installer was the artifact under
review. The findings below distinguish what the original traces establish from
conditions they did not record.

### Original failures

| Test | Failure trace and actual result | Assessment |
| --- | --- | --- |
| `tests/test_desktop_demo.py::test_real_desktop_create_sign_verify_tamper_lock_and_restart` | In the initial full run, `_run` reached `subprocess.TimeoutExpired` at the existing 150-second limit. In the second, `_run` at line 47 received exit 1. The child reported two `vault-save` attempts with `accepted=false`, no filename confirmation and `generatedPairs=0`. The expected state was a created, locked vault after the second Save. | Real Windows Save and password dialogs. The child continued after a picker that had failed to confirm selection, so the later Locked check hid the earlier failure. The application's refusal to generate a pair after a cancelled selection was correct. The first timeout and the original foreground owner cannot be attributed from the captured logs. |
| `tests/test_desktop_responsive_native.py::test_real_webview_default_maximized_restored_and_minimum` | The parent assertion at line 31 received exit 1 from the WebView2 probe. `sidebar_check` at line 154 timed out in `wait` at line 100 while waiting for `data-expanded='true'` after moving the Windows cursor toward the sidebar in the default window. The signed PDF had already validated and the default viewport checks had passed. | Real Windows pointer and WebView2. The old driver treated moving the cursor as sufficient and used a fixed delay after leaving the sidebar. It recorded neither foreground ownership nor delivery of the pointer transition to WebView2. No evidence establishes an application defect or a particular competing window in that run. |
| `[desktop-1920] tests/sidebar.spec.ts:157 › rapid pointer transitions and resizing do not leave a stale hover panel` | The assertion at line 170 expected `data-expanded='false'` after 500 ms of virtual time. The browser continued reporting `data-expanded='true'` and `data-resizing='true'` during the five-second assertion. | Headless Edge with a mocked native host. It uses browser input, independent of Windows desktop focus. The resize had been committed by the time of the assertion, but its timer had not settled on the frozen clock. The old test advanced time without confirming resize delivery. This is consistent with the resize handler running late relative to the clock advance. The initial log does not contain the exact event timestamps. |

Original traces are in local `tmp/phase4c2b-python.txt`,
`tmp/phase4c2b-python-final.txt`, `tmp/phase4c2b-demo-followup.txt` and
`tmp/phase4c2b-frontend.txt`. Python and Playwright were started sequentially in
the Phase 4C.2B validation runner. Pytest was single-process, and the three
Playwright workers each used headless Edge. The two Windows probes shared the
interactive desktop with other Windows processes, so independent user input or
focus changes remained possible. The logs do not establish any such interference.
No `HybridSign.exe` window or test-owned Python process was present at preflight.
Background WebView2 processes were left alone. Each of the six native pytest
cases has its own probe process and the document cases use pytest temporary
directories. The old shared `tmp/phase4c1-progress.json` was a diagnostic file
only. No collision between vault/PDF paths, install directories or test data was
observed.

### Test corrections and reproduction

- `tests/desktop_demo_probe.py` now waits for the exact modal to acquire foreground
  before sending filename input. It also waits for the asynchronous Alt+N focus
  transition to reach an Edit child. After exact filename confirmation it posts
  one activation to the native button. The actual picker still returns the
  selected path. The caller checks acceptance, path and automation errors before
  continuing, including when the password dialog is subsequently cancelled.
  Bounded failures record the input phase, owner/foreground relationship and
  edit focus. [Microsoft foreground restrictions](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow)
- `tests/test_desktop_demo.py` retains child output on the existing hard timeout.
  The child emits its progress into that process's file-backed output and emits
  a thread dump at 135 seconds. The hard 150-second limit is unchanged. An inner
  native or pywebview call can block independently of a Python polling deadline,
  so that outer limit remains useful. Progress no longer depends on a shared
  diagnostic path.
- `tests/desktop_verification_probe.py` obtains physical coordinates from the
  actual WebView client window under a temporary test-thread DPI context. It
  checks foreground, moves the real cursor and waits for the browser's pointer
  event near the intended CSS position. The next move proceeds after acknowledgment
  of the previous one. The resize check waits for settled UI state. The original
  geometry, focus, signature results, sidebar controls and native cancellation
  assertions still run. [Microsoft DPI context](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setthreaddpiawarenesscontext)
- `frontend/tests/sidebar.spec.ts` installs the virtual clock before app load.
  It keeps the clock paused until the app reports receipt of the real resize,
  advances the original 500 ms, confirms resize completion and retains the exact
  collapsed and overflow assertions. [Playwright Clock](https://playwright.dev/docs/clock)
- `tests/conftest.py` supplies a Windows session mutex requested by the six
  visible native pytest cases. Cooperative pytest processes cannot send desktop
  input concurrently. The separate acquisition limit accounts for the longest
  owning test's two 150-second child limits. Failure to obtain the mutex or an
  abandoned owner is reported as a failure. It does not control arbitrary GUI
  applications or manual installer QA.
- `tests/run_release_regressions.py` records direct process exit codes and
  separate logs. It runs TypeScript and the production build, then Python and
  Playwright in that order for each round. It runs the requested suites without
  filters, retries or a Playwright worker override. Wait for separate manual or
  packaged-GUI automation to finish before using the runner.

A diagnostic-only run of the original native probes passed three tests in
61.61 seconds. The original browser case passed 24 executions across both
projects and three workers in 25.2 seconds. Those attempts did not reproduce the
sporadic failures. The changed picker probe passed its two focused tests in
32.61 seconds and the changed native pointer probe passed in 27.44 seconds.
These are supporting diagnostics, separate from the full-suite outcome.

A controlled check with the rebuilt frontend delayed resize delivery until
after the 500 ms clock advance. It reproduced `data-resizing='true'` and
`data-expanded='true'`, matching the original failure. With resize delivery
acknowledged before the same advance, both values became `false`. This
establishes the event ordering that can cause the browser assertion to fail.
The original run did not record when that event was delivered.

### Follow-up file manifest

| File | Change |
| --- | --- |
| `frontend/tests/sidebar.spec.ts` | Wait for resize acknowledgment before advancing virtual time |
| `tests/desktop_demo_probe.py` | Wait for real picker input readiness and report failed selection before advancing |
| `tests/desktop_verification_probe.py` | Verify native foreground and delivered pointer transitions |
| `tests/test_desktop_demo.py` | Preserve child diagnostics on timeout and acquire the shared desktop |
| `tests/conftest.py` | Mutex fixture for native desktop tests |
| `tests/test_desktop_native.py`, `tests/test_desktop_responsive_native.py`, `tests/test_desktop_signing_native.py`, `tests/test_desktop_vault_native.py`, `tests/test_desktop_verification_native.py` | Acquire the shared desktop before each real GUI probe |
| `tests/run_release_regressions.py` | Repeatable sequential release checks |
| `docs/phase4c2b-installer-release.md` | This follow-up report |

### Full-suite results

```powershell
.\.venv\Scripts\python.exe -B tests\run_release_regressions.py --rounds 2
```

| Round | Python | Playwright |
| --- | --- | --- |
| 1 | 1666 passed, 8 skipped, 0 failed in 228.34 s | 266 passed, 0 failed or skipped in 3.9 min |
| 2 | 1666 passed, 8 skipped, 0 failed in 236.12 s | 266 passed, 0 failed or skipped in 4.0 min |

Both rounds covered the same tests, including the installer and portable
payload regressions. There were zero xfails or xpasses. All eight Python skips
were the existing Windows symlink cases that require Developer Mode or symlink
privilege. TypeScript checking and the production build also passed. All six
commands exited with status 0. The per-command logs and exit codes are in the
local `tmp/release-regression-oi62k596/` directory.

### Artifact integrity and release scope

All 138 portable files match the approved manifest and the corresponding ZIP
entries. Its CRC and SHA-256 pass. The 12 freshly rebuilt frontend files match
the bundled values exactly. All 15 benchmark SHA-256 values match the Phase 1
record. The setup checksum matches the sidecar and the installed-EXE lifecycle
acceptance record. The application and Setup still contain no Authenticode
signature.

| Artifact | SHA-256 |
| --- | --- |
| `HybridSign-Setup-Phase4C2B-win-x64.exe` | `7e1dc008c8238a8df93ca8c5cbc75db11a5b8fe77b09ed708ab0daf7ab89d8ae` |
| `HybridSign.exe` | `1fa00d14171336bfcd8a16aabff776e3905946f5bb15bb6f389cd81c1322bfdc` |
| Approved portable ZIP | `6f6364e0c53921aa0370e75def1b07e4e36d0b52739563058d778db3c447a293` |

The build inputs remain the approved application and packaging configuration.
Only external tests and documentation changed, so there is no replacement
portable payload or installer to accept. The original installed-app evidence
continues to identify the exact Setup bytes above. Vault formats, PDF formats,
signing semantics and application storage checks come from that same payload.
Clean Windows VM validation remains **NOT RUN**. These local GUI results do not
cover disconnected desktops, other DPI configurations or competing manual input.

### Commit readiness

The two passing rounds and matching release hashes support committing the
installer and test harness as the local thesis release baseline on
`thesis/ui-demo`. Clean-machine acceptance and Authenticode signing remain
open for wider distribution.
