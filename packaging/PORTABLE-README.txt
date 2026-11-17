HybridSign - Falcon-512 + Ed25519 thesis research prototype

Keep this complete folder together. Double-click HybridSign.exe.
Python, Node.js and npm are NOT required on the target computer.

External prerequisites (not downloaded or installed by HybridSign):
- Windows x64; tested Windows build and runtimes are in the release manifest.
- Microsoft Edge WebView2 Evergreen Runtime 111 or newer.
- Microsoft .NET Framework 4.6.2 or newer.

Extract/copy to an ordinary local folder before launching. Store all encrypted
vaults, PDFs and signing outputs in a separate trusted user-owned fixed local
NTFS folder, outside this application folder. Never weaken filesystem ACLs.
Do not run as Administrator merely to bypass a denied operation.

Signing requires an authenticated unlocked vault. Passwords are entered in native
Windows dialogs. Restart never restores unlocked signing access. Losing the vault
or its password can mean losing signing access: no password recovery is provided.

HYBRID VALID describes both mathematical signatures under the selected keys.
Trusted signer identity, trusted timestamps, CMS/PAdES/FIPS compliance and general
PDF reader interoperability are NOT established. This is not production-certified.
No updater, telemetry, accounts or backend service is included.

The executable is unsigned. SHA-256 checksums detect mismatched artifacts but do
not authenticate the publisher. Verify the complete release through a trusted
channel. Windows SmartScreen/antivirus behavior and clean-machine compatibility
require separate acceptance; never disable security software to launch this app.
