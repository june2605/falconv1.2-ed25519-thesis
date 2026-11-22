# HybridSign 0.1.0

HybridSign is a Windows research app for signing PDFs with Ed25519 and
Falcon-512. Ed25519 signs the first revision. Falcon-512 signs the next revision
with the Ed25519 signature included. Verification checks the complete pair
against the public keys you select. Signing keys are stored in an encrypted
vault on your computer. [Project provenance](docs/PROJECT_PROVENANCE.md)

## Windows requirements

- 64-bit Windows. The release was tested on Windows 11 Pro x64.
- Microsoft Edge WebView2 Evergreen Runtime 111 or later.
- Microsoft .NET Framework 4.6.2 or later.

Install any missing runtimes from Microsoft. The installer and portable build
require both runtimes. They include their Python runtime. [WebView2 downloads](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) · [.NET Framework downloads](https://dotnet.microsoft.com/en-us/download/dotnet-framework)

## Installation

- **Installer.** Use the approved `HybridSign-Setup-Phase4C2B-win-x64.exe` for
  your Windows account. Open **HybridSign** from the Start Menu. To uninstall,
  close the app after any signing finishes and use **Settings > Apps > Installed apps**.
- **Portable.** Extract the complete `HybridSign-Phase4C2A-win-x64-portable.zip`
  to a local folder and open `HybridSign.exe`. Keep its files and subfolders together.

The release packages are unsigned and distributed separately from the source.
Check their SHA-256 values against the release record obtained through a trusted
channel. A matching checksum identifies the package from that record. Publisher
authentication and clean-machine acceptance are separate checks.
[Release checksums and limitations](docs/phase4c3-final-release-review.md#release-integrity) · [Installer record](docs/phase4c2b-installer-release.md) · [Portable record](docs/phase4c2a-portable-packaging.md)

The instructions below use the labels in this source tree. The approved
installer and portable build still show the earlier labels listed in the demo
checklist. [Label differences](docs/thesis-demo-checklist.md#nhãn-trên-bản-phát-hành-và-bản-từ-mã-nguồn)

## First-time setup

Create a folder controlled by your Windows account on a fixed local NTFS drive.
Keep vaults and PDFs there, outside the app and source folders. Use the
[public sample PDF](demo_assets/sample-unsigned.pdf) to try the workflow.

## Create or unlock a vault

1. Open **Key Vault** and select **Create Vault**. Choose a new `.hvault` file
   and enter a password of at least 15 characters in the Windows dialog. The new
   vault is locked.
2. Select **Unlock Vault**, choose the file and enter its password. Confirm that
   the vault shows **Unlocked** before signing.
3. To end signing access, select **Lock Vault**. After restarting the app, open
   the same vault to recover the same key pair. Use **View full ID** to compare
   the Hybrid Key ID with a trusted record of the two public keys.

Keep the encrypted vault and its password. Password recovery, password changes
and in-app backup or restore are unavailable. Locking ends signing access, but
other copies of sensitive data may remain in process memory.
[Vault behavior](docs/phase4b2a-real-vault-regression.md)

## Sign a PDF

1. Open **Sign Document** and use **Choose PDF** to select an unsigned PDF of
   50 MiB or less.
2. Review the document and unlocked vault. Select **Continue to review** and
   then **Sign PDF**. Choose an output location in the Windows Save dialog.
   Windows asks before replacing an existing PDF.
3. Leave the app open while signing runs. **Signed PDF saved** appears after
   HybridSign checks both signatures and confirms the saved output.

If the signing status is unconfirmed, use **Check signing status** and inspect
the chosen save location. A signed PDF may already exist and an existing file
could be from an earlier operation. Verify the intended output before deciding
whether to start another signing operation. [Signing behavior](docs/phase4b3a-real-signing-regression.md)

## Verify a PDF

1. In **Verify Signature**, select **Choose signed PDF**.
2. Use **Choose encrypted vault** to read the public keys from a vault file
   without a password. HybridSign labels this source **UNAUTHENTICATED**. Compare
   the key ID with a trusted source before relying on the result. If the vault
   is already unlocked, select **Use unlocked vault keys**. The selected public
   keys stay available after locking.
3. Select **Verify PDF**. **HYBRID VALID** means both signatures passed with the
   selected keys. **HYBRID INVALID** means the pair was rejected. Check that
   you chose the correct file and keys. An interrupted or unconfirmed check
   does not report a cryptographic result. Use **Check verification status**
   if it appears.

Verification reads the PDF and leaves it unchanged. The Hybrid Key ID
identifies a public-key pair. Establishing who signed requires a separate,
trusted link between the keys and the signer. [Verification and key trust](docs/phase4b3b-real-verification-regression.md#public-key-source-trust)

## Troubleshooting

| If you see | What to check |
| --- | --- |
| Startup asks for WebView2 or .NET Framework | Install the required runtime from Microsoft and reopen HybridSign. |
| Vault will not unlock | Confirm the file and password. A damaged vault can also prevent unlocking. |
| Save location is refused | Choose a user-controlled local NTFS folder outside the app folder. Keep the input, output and vault as separate files. |
| PDF is refused | Use a nonempty PDF of 50 MiB or less. Signing takes an unsigned input. |
| Only demo results appear | Use the Windows app for real signing and verification. A regular browser shows the UI preview. |

## Known limitations

HybridSign uses a project-specific PDF signature format. CMS, PAdES, reader
interoperability and FIPS 206 conformance remain unverified. It does not
establish signer identity or trusted signing time. Input checks cover the file
envelope and signature format. The app does not render PDFs or inspect their
active content. [Security and format limits](docs/phase5-1a-signature-integrity-audit.md) · [Falcon implementation](docs/falcon-implementation-provenance.md)

## Development and research

To run the desktop app from source, use Windows x64, Python 3.11, the desktop
runtimes above and a Node.js version supported by the frontend. The tested
cryptographic profile uses `pqcrypto==0.3.4` and `PyNaCl==1.6.2`.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-portable.txt
Push-Location frontend
npm ci
npm run build
Pop-Location
.\.venv\Scripts\python.exe -m desktop.launcher
```

- [Frontend setup, preview and tests](frontend/README.md)
- [Thesis demonstration checklist](docs/thesis-demo-checklist.md) and [script](docs/thesis-demo-script-vi.md)
- [Benchmark protocol and evidence](docs/phase5-5c-cross-platform-main.md)
- [Thesis experimental chapter](docs/thesis-chapter-experiments-vi.md) and [discussion](docs/thesis-chapter-discussion-vi.md)
- [In-memory signing and public-key verification APIs](docs/phase3-1-regression.md)

Run Python regression tests in an environment with pytest installed.
Use a Windows desktop session for native dialog and WebView2 tests.

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

### Legacy Streamlit app

`app.py` is the inherited local research workflow. It also needs Streamlit
(`streamlit==1.66.1` in the tested setup). Run it on loopback to keep uploads
on this machine.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

The key generator writes persistent plaintext key files and can replace prior
keys. The signing screen requires the Ed25519 private seed, Falcon private
key and matching Falcon public key. The verification screen requires both
public keys. Upload cleanup and the path-based Python API have separate
regression records. [Legacy signing and cleanup](docs/phase2b4b3-regression.md) · [Path-based API](docs/phase2b4b2-regression.md)
