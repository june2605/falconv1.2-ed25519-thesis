# Falcon–Ed25519 thesis prototype

Local Streamlit research application inherited from FALCON/eSign. Ed25519 signs
the first document revision; Falcon-512 signs the subsequent revision containing
that signature. Verification requires both layers and rejects bytes appended
after the final container. See [project provenance](docs/PROJECT_PROVENANCE.md).

The container format is custom. CMS, PAdES, FIPS 206 compliance and PDF-reader
interoperability have not been established. Historical prototype installers do
not contain the hardening in this source tree.

## Local Windows setup

### Phase 4B.3B Windows desktop, vault, signing and verification

HybridSign opens in a dedicated pywebview/WebView2 window. Key Vault now creates,
unlocks and locks real encrypted hybrid-key vaults, with file selection and masked
password entry in native Windows dialogs. Private keys stay in the Python worker;
React receives public metadata and opaque references only. Sign Document now saves
a real Ed25519 then Falcon-512 PDF using the authenticated vault on that same worker.
Standalone hybrid verification is connected as well. Password changes,
backups/restores and accounts remain unintegrated. Browser mode remains a UI preview.

From the existing Python 3.11 x64 environment:

```powershell
Set-Location D:\Final_Thesis_GitHub
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
Set-Location frontend
npm run build
Set-Location ..
.\.venv\Scripts\python.exe -m desktop.launcher
```

Use `npm ci` before building on a fresh frontend installation. The current
workspace already has its dependencies installed. The launcher serves only the
compiled frontend and requires no Vite server. It never downloads WebView2 or
falls back to a browser/legacy renderer. Install WebView2 Evergreen 111+ and
.NET Framework 4.6.2+ separately if missing; current supported updates are recommended.
See [native architecture, security limits and exact regression results](docs/phase4b1-native-bridge-regression.md).

On **Key Vault**, choose **Create Vault** and a new filename in an existing
trusted folder on a fixed local NTFS drive. Enter and confirm a password of at
least 15 characters in the Windows dialog. The encrypted vault is created locked.
Choose **Unlock Vault** to select and authenticate it; **Lock Vault** drops managed
access. Close/reopen the application and select the same file to recover the
original keys. Existing filenames are never overwritten. Unsupported storage or
broader/foreign ACLs reject without permission repair. Locking does not guarantee
memory erasure; lost passwords cannot be recovered here.

See [real-vault integration, exact tests and remaining limitations](docs/phase4b2a-real-vault-regression.md).
On **Sign Document**, choose an unsigned PDF through the Windows picker, select
your unlocked vault, continue to review, then choose **Sign PDF** and a native
Save location. Source overwrite, vault/sidecar aliases and unsafe paths reject.
Replacing an existing PDF requires native confirmation; unrelated non-PDF files
are not accepted as replacement targets. Input is limited to 50 MiB on the
conservative fixed-local-NTFS profile. This is envelope validation, not complete
PDF parsing or active-content inspection.

Signing runs as one tracked operation. Leave the application open until it
settles; active signing prevents normal window close and conflicting vault
operations. Completion means that the inherited signer verified both layers
before atomic publication and Python verified the saved bytes again. If the
status is uncertain, reconcile it and inspect the chosen output location before
retrying; there is no post-queue cancellation promise. No PDF bytes, paths,
passwords or private keys are passed through the JavaScript API.

See [real-signing architecture, Windows evidence and exact regression results](docs/phase4b3a-real-signing-regression.md).
On **Verify Signature**, choose a signed PDF and an encrypted `.hvault` through
Windows dialogs. Public metadata can be read without a password or private key.
It is shown as **UNAUTHENTICATED**. Alternatively, choose **Use authenticated vault**
after unlocking on Key Vault; that public snapshot stays usable after locking.
Authentication of a vault does not certify signer identity. Verify PDF reports
only **HYBRID VALID / HYBRID INVALID** for the complete pair under selected keys;
exceptions and changed inputs are failures, not invented layer results. A wrong
key pair also causes INVALID. Verification never rewrites the PDF or key source.

See [real-verification architecture, evidence and exact results](docs/phase4b3b-real-verification-regression.md).
Human Windows picker acceptance, physical DPI and screen-reader checks remain
manual. Browser mode stays entirely simulated; desktop verification has no example
results. Existing Python verifier APIs remain available separately.

### Phase 4A desktop UI preview

The separate [HybridSign frontend](frontend/README.md) is an interactive React
prototype with Dashboard, Sign Document, Verify Signature, Key Vault and Settings.
In a regular browser it is **not connected to Python**; all workflow results are
labelled UI previews. The native desktop above separately integrates local vaults and PDF signing.

```powershell
Set-Location D:\Final_Thesis_GitHub\frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Tested with Node 26.13.0 and npm 11.20.0.
The existing Streamlit application and Python setup below remain separate.

### Existing Python prototype

The regression environment uses Windows x64 and Python **3.11.9**, with
`pqcrypto==0.3.4` (including `pqcrypto.sign.falcon_512`), `PyNaCl==1.6.2`,
`streamlit==1.66.1` and `pytest==9.2.0`. These are observed tested versions,
not a complete dependency lock; `requirements.txt` remains unpinned.

From PowerShell, use the existing environment without activating it:

```powershell
Set-Location D:\Final_Thesis_GitHub
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "from pqcrypto.sign import falcon_512; print(falcon_512.PUBLIC_KEY_SIZE)"
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

Open `http://127.0.0.1:8501` in a local browser. If setting up a **new** environment
instead, these commands install the observed top-level versions:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install pqcrypto==0.3.4 PyNaCl==1.6.2 streamlit==1.66.1 pytest==9.2.0
```

PyInstaller is listed for inherited packaging but is unnecessary for the local
Streamlit workflow. Desktop packaging and the inherited browser watcher are not
validated by the regression suite; start Streamlit directly as above.

## Generate, sign and verify

1. In **QUẢN LÝ KHÓA**, generate and download all four raw key files:
   `ed25519_pub.key`, `ed25519_priv.key`, `falcon_pub.key`, `falcon_priv.key`.
   The inherited generator writes persistent plaintext files in the working
   directory and can overwrite prior keys. Keep needed keys backed up privately.
2. In **KÝ SỐ TÀI LIỆU**, upload an unsigned PDF, the **Ed25519 private seed**,
   **Falcon private key**, and the **matching Falcon public key**. That public
   key is mandatory for final verification; the Ed25519 public key is derived
   from its private seed. An incorrect Falcon public key prevents download.
3. Download the signed PDF only after both cryptographic checks succeed. The
   backend stages, fsyncs and verifies its candidate before atomic replacement;
   the UI also checks a snapshot of the exact bytes supplied for download.
4. In **XÁC THỰC TÀI LIỆU**, upload the signed PDF and both corresponding public
   keys. Altered content, malformed containers, noncanonical padding, truncation,
   appended bytes or wrong public keys produce rejection.

The public signing API requires a keyword-only Falcon public-key path:

```python
from sign import sign_file
from verify import verify_file

result = sign_file("source.pdf", "signed.pdf", "ed25519_priv.key",
                   "falcon_priv.key", pk_falcon="falcon_pub.key")
valid, *_ = verify_file(result[0], "ed25519_pub.key", "falcon_pub.key")
```

There is no four-argument fallback. Both public functions retain their
11-element return tuples. Inspect the verifier's first boolean, not tuple
truthiness. Signing rejects source/key destination aliases, already-signed
input and reserved marker collisions; it never strips old signatures.

## Phase 3.1 in-memory foundation

The new Python APIs keep private-key material in memory and share the inherited
PDF protocol and atomic publication logic:

```python
from keygen import generate_hybrid_key_pair
from sign import sign_with_key_material
from verify import verify_bytes

pair = generate_hybrid_key_pair()  # Generates and validates both pairs; no files.
result = sign_with_key_material("source.pdf", "signed.pdf", pair)
with open(result[0], "rb") as document:
    report = verify_bytes(document.read(), pair.public_keys.ed25519_public_key,
                          pair.public_keys.falcon_public_key)
assert report[0] is True
```

PDF stages still use owned temporary files; the memory-key signer creates no
key files. `pair.key_id` identifies the ordered public-key tuple, not a trusted
identity. This is an in-memory foundation, not encrypted storage or a memory
isolation boundary. The Streamlit UI and legacy `generate_keys()` export still
use plaintext key files. See [Phase 3.1](docs/phase3-1-regression.md) and the
[Falcon provenance investigation](docs/falcon-implementation-provenance.md).

## Operational limits

- Run this prototype locally. Streamlit uploads reach its Python process;
  exposing that process remotely would send private keys to the remote server.
  This is not a browser-side cryptography or multi-user key-storage system.
- Upload copies are isolated in owned temporary directories and cleaned before
  results/downloads, on success and ordinary exceptions. One cleanup retry handles
  a transient OS failure. Persistent permission/sharing denial is reported with
  the affected upload directory and prevents a signed download. Stop using the
  affected directory and remove leftovers after resolving the denial.
- Process termination, power loss and native crashes can leave temporary files.
  Cleanup is not secure erasure; Streamlit/browser upload and download buffers
  can retain bytes in memory. Generated working-directory keys are intentionally
  persistent and are not temporary upload artifacts.
- Atomic replacement provides visibility on supported filesystems, not a
  power-loss durability guarantee. Path/fingerprint checks do not eliminate
  concurrent filesystem races. Use trusted local directories and suitable ACLs.
- Upload validation checks for nonempty data and a PDF header. It does not fully
  parse PDF syntax, render documents, detect active content or establish signer
  identity. Public keys must come from a trusted source. Key generation remains
  non-transactional; a failed regeneration can leave partial persistent keys.

## Regression tests

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Tests use small synthetic PDFs and disposable keys, including both frozen
Phase 1 signatures. Original benchmark data is neither required nor changed.
Eight native symlink cases skip on the current Windows environment because
Developer Mode/symlink privilege is unavailable (error 1314); native hard-link
and Windows file-sharing cases run normally. No elevation is required for the
rest of the suite.

The launch command enables Python UTF-8 mode because redirected Streamlit CLI
help/output can otherwise fail under Windows legacy console encodings.

See [Phase 2B.4B.3 regression results](docs/phase2b4b3-regression.md) for exact
counts, fault coverage and remaining limits. Earlier phases are recorded in
[docs/](docs/).
