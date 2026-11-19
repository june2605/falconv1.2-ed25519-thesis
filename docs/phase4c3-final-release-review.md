# Phase 4C.3 — HybridSign 0.1.0 final release review

## Scope

The review started from a clean `D:\Final_Thesis_GitHub` worktree on
`thesis/ui-demo` at `5dff14e54c2909ce2ab3bcdd05940ec07fb5d51d`. The
preceding baseline was two full passes of 1,666 Python cases with eight
Windows symlink skips and 266 Playwright cases. The environment is Windows
11 Pro x64 25H2 (build 26200.9974), Python 3.11.9, WebView2 Evergreen
157.0.4341.60 and .NET Framework 4.8.09221 (Release 533509).
[Repository rules](../AGENTS.md) · [Local setup](../README.md) ·
[Inherited research provenance](PROJECT_PROVENANCE.md) ·
[Prior release regression](phase4c2b-installer-release.md#phase-4c2b1--final-release-regression-stabilization)

The thesis source descends from FALCON/eSign baseline `0f3b513`, with the
lightweight repository migrated at `39821b0`. The original history,
benchmark datasets and research attribution remain in the provenance record.
The original study's citation has its own version, distinct from the desktop
product version 0.1.0. [Original research citation](../CITATION.cff)

The previous Streamlit and browser UI-preview workflows are separate from
the packaged desktop. This review uses the existing approved Windows
binaries, the current source regression suite and the generated public demo
PDF. The documentation and one confirmed native test-driver fix are the
only source changes. Cryptographic code, the cryptographic formats,
application UI, packaging configuration and benchmark data were kept as approved.

## Desktop architecture and observed data flow

| Boundary | Responsibility and evidence |
| --- | --- |
| Packaged entry and host | `packaging/entrypoint.py` calls `desktop.launcher.main()`. The launcher captures the compiled static assets via `desktop.assets.capture_build()` and serves them from an ephemeral loopback address. `desktop.runtime.require_runtime()` checks prerequisites. It starts pywebview with EdgeChromium, disables debugging and uses native startup messages in the frozen build. [Entry point](../packaging/entrypoint.py) · [Launcher](../desktop/launcher.py) · [Runtime](../desktop/runtime.py) |
| React renderer | `App.tsx` selects native routes and providers from advertised capabilities. `NativeVault`, `NativeSignDocument` and `NativeVerifySignature` display native replies, basenames, public metadata, opaque IDs and asynchronous operation states. The regular browser routes use a labelled preview service. [Routes](../frontend/src/App.tsx) · [Preview service](../frontend/src/services/demo.ts) |
| Native bridge and GUI | `NavigationPolicy`, `decode_message()` and `NativeGuard` constrain local origins, static resources and permitted bridge methods. `VerificationBridge` extends the signing and vault bridges. `NativeDialogs` owns Windows file pickers and masked password controls on the GUI thread. JavaScript receives no plaintext password, filesystem path, private key or PDF bytes through these operations. [Guard](../desktop/security.py) · [Bridge](../desktop/verification_bridge.py) · [Dialogs](../desktop/dialogs.py) |
| Local worker and domain code | `VerificationWorker` extends the signing/vault worker on a bounded queue. The Python worker thread in the desktop process owns managed handles, snapshots, operation IDs and access to the core crypto functions. There is no remote signing service. [Worker](../desktop/verification_worker.py) · [Queue and owner lifecycle](../desktop/worker.py) |

| User operation | Implementation path and result |
| --- | --- |
| 1. Generate two pairs | **Create Vault** enters `VaultService.execute(VAULT_CREATE)`. It checks for a fresh destination and calls `generate_hybrid_key_pair()` once. PyNaCl generates Ed25519, and `pqcrypto.sign.falcon_512` generates Falcon. `validate_key_pair()` checks algorithms, lengths, correspondence and native self-tests. [Service](../desktop/vault_service.py) · [Generation](../keygen.py) · [Validation](../hybrid_keys.py) |
| 2. Protect the private keys | `vault.create_vault()` calls the in-memory sealing codec and publishes a checked encrypted vault through `vault_io`. Argon2id derives 32 bytes using a random salt (64 MiB, 3 iterations, 4 lanes). AES-256-GCM encrypts the private payload with a fresh nonce and authenticates the header as associated data. New-vault creation ends locked. [Vault lifecycle](../vault.py) · [Encryption](../vault_crypto.py) · [Vault format](phase3-2-vault-format.md) |
| 3. Unlock | **Unlock Vault** opens a native picker and a masked native password dialog. `VaultService` validates the selection and calls `vault.unlock_vault()`. `unseal_key_pair()` authenticates the original header and ciphertext before accepting recovered key material. Only then does the worker install an unlocked handle/session. Wrong-password retry leaves the vault locked and uses a fresh password prompt for the checked selection. [Vault bridge](../desktop/vault_bridge.py) · [Service](../desktop/vault_service.py) · [Authentication regression](phase4b2a-real-vault-regression.md) |
| 4. Sign with the recovered keys | `SigningService.run()` rechecks the selected unsigned PDF snapshot, output approval and vault session. `sign_vault_document()` holds cooperative vault storage guards during `sign_with_key_material()`. `sign._sign_captured()` signs Ed25519 then Falcon. Temporary signing stages contain PDF data. The signer creates no plaintext private-key files. [Signing service](../desktop/signing_service.py) · [Managed signing](../vault_signing.py) · [Shared signer](../sign.py) |
| 5. Save checked output | `SigningTransaction` writes the staged candidate in the destination directory, flushes, fsyncs and closes it. The signer requires a literal true from verification of the candidate and rechecks aliases, identity and vault storage before `os.replace()`. The service reopens the published file for another check before reporting **Signed PDF saved**. An uncertain outcome calls for reconciliation and inspection of the destination. [Atomic transaction](../signing_io.py) · [Signing regression](phase4b3a-real-signing-regression.md) |
| 6. Select the matching public keys | **Use authenticated vault** snapshots public keys from the authenticated handle. **Choose encrypted vault** reads its public header without a password and labels the source **UNAUTHENTICATED**. Structural checks and recomputing the ID do not authenticate the header. The desktop workflow selects these vault sources. The Python API also supports public-key bytes and separate public-key files. [Key selection](../desktop/verification_worker.py) · [Verification service](../desktop/verification_service.py) |
| 7. Verify | `VerificationService.run()` checks the selected PDF and key-source revisions, then calls `verify_bytes()`. `utils.parse_signature_pair()` validates the custom container structure, and `verify._verify_document()` runs both cryptographic checks with the selected public keys. The page reports one hybrid result. [Parser](../utils.py) · [Verifier](../verify.py) · [Native result](../frontend/src/pages/NativeVerifySignature.tsx) |
| 8. Reject changed bytes | An independent signed-PDF copy changes `APPROVED` to `REJECTED` and fails under the same keys. The unchanged signed file fails with the independent wrong-key vault. Parser regressions also reject altered padding/metadata, reordered containers, truncation and appended bytes. [Modified file evidence](../frontend/qa/phase4c2b/packaged-tampered.png) · [Wrong-key evidence](../frontend/qa/phase4c2b/packaged-wrong-keys.png) · [Completed metadata](phase2b2-regression.md) · [Pair structure](phase2b3-regression.md) |
| 9. Lock | `VaultService.lock_active()` calls `vault.lock_vault()`, clears the managed private-key session and retains allowed public display data. Signing is no longer available from that session. The existing public verification snapshot can still verify, while its selected revision remains usable. [Lock implementation](../desktop/vault_service.py) · [Lock and sign evidence](../frontend/qa/phase4c2b/installer-checks.json) |
| 10. Reopen and unlock | Normal shutdown closes bridge/worker resources and locks managed access. The next process starts with no unlocked vault. Picking and unlocking the same file recovers the original key pair, yields the same Hybrid Key ID and verifies the earlier signed PDF. This was exercised both on desktop restart and after the validated installer lifecycle. [Source journey test](../tests/test_desktop_demo.py) · [Reinstall evidence](../frontend/qa/phase4c2b/reinstalled-original-signature-valid.png) |

The [actual installed-EXE report](../frontend/qa/phase4c2b/installer-checks.json)
records successful Open/Save, real sign, matching-key verification,
modification and wrong-key rejection, and original-vault recovery. It also
records loaded `python311.dll`, Falcon, libsodium and cryptography native
modules under the installed `_internal` directory, driven by external
Windows UI Automation without bundled test hooks or remote debugging.
Playwright uses browser and mocked-bridge coverage for UI state. The native
pytest journeys and EXE evidence cover actual cryptographic execution.

## Cryptographic claims and scope

1. **Ed25519** signs the raw concatenation of the two covered ByteRange
   slices in the first revision. The inherited function
   `compute_sha512_digest_for_byte_range()` returns the joined bytes, despite
   its name. No separate application-level SHA-512 prehash is applied before
   calling PyNaCl. Ed25519's own algorithm processing still applies.
2. **Falcon-512** signs a 64-byte SHAKE256 digest calculated by the
   application from the second revision's covered bytes. This includes the
   complete Ed25519 container. The digest helper includes any bytes after
   the second specified interval in its input construction. The strict
   completed pair requires that interval to end at the file boundary,
   leaving no extra bytes in a valid file.
3. **Hybrid validity** requires both signatures to verify under the selected
   pair and requires exact container boundaries. Each container excludes its
   own signature field area. The parser enforces canonical metadata,
   hexadecimal and ASCII zero padding, including unused Falcon padding.
   This rejects changes in that region even though Falcon's message omits it.
   The verifier returns a single Boolean followed by ten timings. **HYBRID
   INVALID** is a rejection of the pair. Failures to read or complete the
   operation have separate UI states. No independent per-algorithm pass/fail
   is exposed. A single result concerns the bytes captured for that operation.
   [Signing code](../sign.py) · [Message and parser code](../utils.py) · [Verification code](../verify.py)
4. **Hybrid Key ID** is `hybrid-v1:` plus SHA-256 over
   `THESIS-HYBRID-KEY-ID-v1\0` followed by four length-prefixed fields, in order
   `ed25519`, Ed25519 public bytes, `falcon_512`, Falcon public bytes. Each
   prefix is a four-byte unsigned big-endian length. The ID identifies the
   ordered pair and can be checked through a separate trusted channel.
   The signed PDF contains no authenticated signer identity, Hybrid Key ID or
   trusted timestamp. Even successful vault authentication establishes only
   local access and integrity under that vault password. An unauthenticated
   vault header's ID can be internally consistent with an untrusted key source.
   [ID function](../hybrid_keys.py) · [Verification trust labels](phase4b3b-real-verification-regression.md)
5. **Falcon provenance.** The pinned binary uses the PQClean clean
   `falcon_512` binding in `pqcrypto==0.3.4`. The previously investigated
   source lineage is labelled `20211101` with PQClean patches. The matching
   binary and lineage evidence do not establish reproducible native builds,
   validated Falcon v1.2 conformance or FIPS 206 certification.
   [Provenance investigation](falcon-implementation-provenance.md) ·
   [Pinned PQClean metadata](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/META.yml)

The container is research-specific. There is no established CMS, PAdES or
Adobe signature-panel interoperability or evidence of legal identity.
Envelope rules are intentionally conservative (including reserved-marker
rejection and a 50 MiB desktop input limit). They do not parse or vet all PDF
content. Encrypted local storage depends on the password and filesystem
permissions. Offline guessing, a compromised process, side channels, paging
and crash dumps are outside the guarantees. Locking releases managed access
without guaranteed memory erasure. Atomic publication on the supported local
profile is distinct from power-loss durability, and filesystem races remain.
[Capacity and coverage](phase2b3-regression.md) ·
[Vault limits](phase3-2-vault-format.md) ·
[Publication guarantees](phase2b4b2-regression.md)

## Demo kit and user experience

Use the [742-byte public sample](../demo_assets/sample-unsigned.pdf). Its
checked SHA-256 is
`2d94ba434bbbfda3ffcd78731f2e94146352e5dc7680dcd566d2ca0614a20639`.
The [preparation and machine checklist](thesis-demo-checklist.md) is the
reproduction procedure for a presenter-owned disposable vault, signed and
altered PDF copies and a separate wrong-key vault. Presenter credentials
are entered only in the native dialog, and generated artifacts go in a
private fixed-local-NTFS folder outside the repository and application.
Use the [4:45 Vietnamese script](thesis-demo-script-vi.md) with the approved
Start Menu shortcut or portable EXE. The [Vietnamese technical Q&A](thesis-technical-qa-vi.md)
contains committee answers and computed summaries of the preserved historical CSV
values. They are measurements of the inherited prototype. Desktop latency was
not benchmarked here.

Reviewed the native page source, the recorded five-screen light/dark
screens, and desktop/browser workflow coverage. Existing controls and labels
remain in place.

| Screen or behavior | Review |
| --- | --- |
| Dashboard | **Desktop Connected** plus local vault state and workflow actions distinguish native use from the separate **UI PREVIEW**. Dashboard does not present a cryptographic result on startup. [Dashboard](../frontend/qa/phase4c1/light-dashboard.png) |
| Sign Document | Choose → review → native Save labels match the script. Busy and uncertain states have distinct messaging. The native journey retains the repeated-click/normal-close gates, and prior browser regressions check that a changed or cancelled picker selection clears old success. The PDF area shows metadata rather than rendering active content. [Review](../frontend/qa/phase4c1/sign-review.png) · [Signing state assertions](../frontend/tests/native-signing.spec.ts) |
| Verify Signature | Explicit Verify action, matching-name and key-source display, aggregate VALID/INVALID, and identity/trust notice. Key reselection clears old results. Full ID expands/collapses and Copy copies exactly the full value, with brief accessible status. [Result](../frontend/qa/phase4c2b/packaged-valid.png) · [Key ID assertions](../frontend/tests/key-id-interactions.spec.ts) |
| Key Vault | Native masked password and file pickers, clear Locked/Unlocked states, error retry or reselect, public details. Password change, backup and restore are disabled in the desktop UI. [Unlocked details](../frontend/qa/phase4c1/create-public-details.png) · [Authentication assertions](../frontend/tests/vault-auth-ux.spec.ts) |
| Settings | Light/Dark/System, reduced motion and a labelled collapsible research-limitations panel. Settings controls and five-screen layout have automated keyboard and theme coverage. [Light](../frontend/qa/phase4c1/light-settings.png) · [Dark](../frontend/qa/phase4c1/dark-settings.png) |
| Sidebar, window sizes and keyboard | Auto responds to hover and keyboard focus. Manual toggle and Pin remain available with the existing width rules. The real Windows tests cover default, maximized, restored and minimum window states. Browser tests cover narrower viewports, keyboard focus, Escape and desktop reflow. [Sidebar interactions](../frontend/tests/sidebar-navigation-id.spec.ts) · [Keyboard checks](../frontend/tests/accessibility.spec.ts) · [Installed minimum-size capture](../frontend/qa/phase4c2b/packaged-sidebar-minimum.png) |
| Startup/errors | The frozen entry emits a native, sanitized prerequisite/build error. Missing-runtime and missing-assets behavior has regression evidence. Clean-system and projector checks remain pending. [Startup evidence](../frontend/qa/phase4c2a/startup-checks.json) |

## Release integrity

Read-only checks verified 138/138 files (33,970,399 bytes) in the portable
folder and the corresponding ZIP entries, plus the ZIP's two expected
manifest/checksum entries and archive CRC. The installer payload manifest,
portable manifest and tracked approved manifest agree. TypeScript and Vite
used the established build. All 12 freshly built frontend files match the
approved payload hashes. The recorded checksums and sizes of both documented
portable and installed acceptance captures also matched (30 files in each
record). All 15 original benchmark/dataset hashes match the Phase 1 baseline.
The public sample matches its Git blob and the sample hash in installed
acceptance. [Approved portable manifest](../frontend/qa/phase4c2a/release-manifest.json) ·
[Phase 1 benchmark hashes](phase1-baseline.json)

| Artifact | SHA-256 |
| --- | --- |
| `HybridSign-Setup-Phase4C2B-win-x64.exe` | `7e1dc008c8238a8df93ca8c5cbc75db11a5b8fe77b09ed708ab0daf7ab89d8ae` |
| Portable `HybridSign.exe`, also shipped by Setup | `1fa00d14171336bfcd8a16aabff776e3905946f5bb15bb6f389cd81c1322bfdc` |
| `HybridSign-Phase4C2A-win-x64-portable.zip` | `6f6364e0c53921aa0370e75def1b07e4e36d0b52739563058d778db3c447a293` |

Use Setup from `dist/installer-validated/` and the ZIP from `dist/portable/`.
Setup's hash equals the hash in the installed lifecycle record, whose
installed payload audit matched every file against the approved manifest.
The installed executable thereby corresponds to the validated portable
payload. The audit did not reinstall over any user's application. The
frozen EXE and Setup were neither rebuilt nor modified in this review.
The approved application/build inputs have no changes from the portable
release through this review. Setup uses the approved Phase 4C.2B installer configuration.

The per-user installer uses an enumerated payload, a Start Menu shortcut
and optional Desktop shortcut. It checks x64 Windows and the external WebView2
Evergreen 111+ and .NET Framework 4.6.2+ prerequisites. Setup does not fetch them.
Servicing refuses active HybridSign and changed/unsafe managed files. The
uninstall log and guards preserve unrelated files. Verified prior acceptance
covered same-version reinstall, real Settings uninstall, intact vault/PDF
artifacts and key reuse. The portable and installer-side third-party notice
files match the approved payload. The included notice inventory still needs
full redistribution review, including inherited materials, exact WebView2 SDK,
runtime redistribution and packages without separate notice text. `Get-AuthenticodeSignature` reports `NotSigned` for both the EXE and Setup. Matching checksums identify bytes
and do not authenticate a publisher. [Installer configuration](../packaging/HybridSign.iss) ·
[Installer lifecycle and notices](phase4c2b-installer-release.md) ·
[Windows Settings evidence](../frontend/qa/phase4c2b/windows-installed-apps-checks.json) ·
[Microsoft WebView2 distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution)

## Regression results and test-driver correction

The established runner, `tests/run_release_regressions.py --rounds 1`,
executes TypeScript, Vite, full pytest, then full Playwright. No competing
GUI automation was launched. The native pytest cases obtain the Windows
session mutex and Playwright uses its standard headless projects. No new skips, xfails or relaxed assertions were introduced.

The first fresh Python run found a startup timeout in
`tests/test_desktop_demo.py::test_real_desktop_create_sign_verify_tamper_lock_and_restart`.
The stage was `create / startup`, with zero completed dialogs. The 135-second
watchdog traced the background `loaded` callback through `window.on_top = True`
to pywebview's `winforms.set_on_top()` writing the WinForms `TopMost` property.
The owning GUI loop was live, and the crypto worker was waiting on its queue.
The unchanged outer 150-second limit reported failure. The installed launcher
does not perform that cross-thread mutation. This trace localizes the hang to
the test-only property write. The internal WinForms wait chain remains unknown.

`tests/desktop_demo_probe.py` now sets the same test-only topmost behavior as
an argument to window creation. The pinned WinForms implementation applies
it during construction on the owning GUI thread. The real dialogs, startup
conditions, crypto/overwrite/recovery assertions and timeouts are unchanged.
[Demo test driver](../tests/desktop_demo_probe.py) · [Sequential runner](../tests/run_release_regressions.py) ·
[WinForms UI-thread guidance](https://learn.microsoft.com/en-us/dotnet/desktop/winforms/controls/how-to-make-thread-safe-calls)

| Validation | First run | Full run after test-driver fix |
| --- | --- | --- |
| TypeScript check | Passed, exit 0 | Passed, exit 0 |
| Production frontend build | Passed, exit 0 | Passed, exit 0 |
| Full Python | 1,665 passed, 1 failed, 8 skipped in 347.82 s | **1,666 passed, 0 failed, 8 skipped in 243.27 s** |
| Full Playwright | 266 passed, 0 failed or skipped in 4.1 min | **266 passed, 0 failed or skipped in 4.0 min** |

There were zero xfails or xpasses. The eight skips in each Python run are
the existing Windows symlink cases requiring Developer Mode or symlink
privilege. The full Python suite includes the portable and installer
payload regressions. The two runs and their individual exit codes are
recorded locally in `tmp/release-regression-b6cajgnx/` and
`tmp/release-regression-9d7eokl1/`. The post-fix full native source run
confirmed matching-key acceptance, modified-file and wrong-key rejection,
lock and cross-process recovery of the original key pair.

The approved portable EXE also passed a fresh two-process GUI replay after the
sequential suites finished (25 recorded checkpoints). It loaded Python, Falcon,
libsodium and cryptography from the copied payload. It generated a disposable
encrypted vault and an independent wrong-key vault, signed the public sample,
accepted the matching pair, rejected the modified copy and wrong keys, and
verified using public material after locking. Unlock after restart returned
the same ID. An independent check of the saved bytes reproduced all three
decisions and verified that `tampered.pdf` is exactly the signed file with
`APPROVED` replaced by `REJECTED`. Both signed versions are 5,368 bytes.
The copied payload still matches all 138 manifest entries. The same local
log directory holds `phase4c3-integrity.json` and `phase4c3-portable-replay.json`.

The replay retained the public sample copy, signed PDFs and encrypted test
vaults in `%LOCALAPPDATA%\Temp\HybridSign-Phase4C3-c39f3x7u\documents`,
outside both the repository and the application copy. The probe generated
a disposable password in memory and did not retain it. For verification-only
rehearsal, select `signed.pdf` or `tampered.pdf` and read the public header of
`original.hvault` or `wrong.hvault` with **Choose encrypted vault**. For live
unlock/signing, prepare a separate presenter-owned kit under a password the
presenter knows using the checklist.

## Readiness and remaining acceptance

| Category | Status |
| --- | --- |
| **A — Implemented and tested** | Local vault creation, authentication, recovery of the original key pair, managed lock, Ed25519 → Falcon signing, atomic verified output, matching-key VALID, changed and wrong-key INVALID, five-screen desktop UI, portable launch and per-user installation/uninstallation under the recorded Windows 11 setup. |
| **B — Implemented, human acceptance pending** | Actual presentation laptop/account, projector and physical DPI, mouse/keyboard and assistive technology, native dialog placement, runtime availability, offline rehearsal, exact kit/password readiness and the presenter-driven run. [Machine checklist](thesis-demo-checklist.md) |
| **C — Not implemented in this desktop release** | Accounts, trusted key registry and identity, signer authorization/revocation, trusted timestamps, password recovery, desktop backup/restore/change-password UI, updates and telemetry. |
| **D — Research and release limits** | Custom signature format, restricted local NTFS, unauthenticated public header when read without unlock, no guaranteed memory erasure or resistance to local process compromise, no demonstrated production/FIPS/CMS/PAdES/Adobe signature-panel compliance, unsigned release and pending redistribution review. Clean Windows VM acceptance **NOT RUN**. |

| Intended use | Recommendation |
| --- | --- |
| Local thesis demonstration | Ready on the validated local configuration. The actual defense laptop and presenter rehearsal remain pending. |
| Portable Windows demonstration | Suitable on the validated Windows configuration. Use the full folder and finish the presentation machine checklist before the defense. |
| Installed Windows demonstration | Suitable on the validated Windows configuration. Use the checksummed per-user Setup and rehearse Start Menu launch and the file workflow on the defense machine. |
| Wider public distribution | Hold. Clean supported Windows testing, redistribution-rights review and an approved publisher-signing and distribution process are still open. |

The four new deliverables are this report, [live script](thesis-demo-script-vi.md),
[setup and contingency checklist](thesis-demo-checklist.md) and
[Vietnamese technical Q&A](thesis-technical-qa-vi.md). The single modified
existing file is `tests/desktop_demo_probe.py`. No dependencies were installed,
no commit or push was made, and the original sample and benchmark data were
preserved.
