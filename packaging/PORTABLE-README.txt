HybridSign 0.1.0 - Windows portable edition

Extract the complete folder to a local drive, then open HybridSign.exe.
Keep the files and subfolders together. The package includes its own
Python runtime.

Windows requirements
- Windows x64. The tested configuration is listed in the release record.
- Microsoft Edge WebView2 Evergreen Runtime 111 or later.
- Microsoft .NET Framework 4.6.2 or later.

Get missing runtimes from Microsoft. HybridSign does not install them.
Keep your encrypted vaults, PDFs and signing outputs in a separate folder
controlled by your Windows account on a fixed local NTFS drive. If Windows
refuses access, choose an appropriate folder. Keep the existing permissions
and security settings.

Open Key Vault to create or unlock a vault. Enter its password in the Windows
dialog. You need an unlocked vault to sign. After restart, unlock the same
vault to use its keys again. Keep a protected copy of the vault file and retain its password separately. HybridSign cannot recover a forgotten password.

HYBRID VALID means both signatures passed with the selected public keys.
Signer identity and signing time require separate evidence. The application
uses a custom PDF signature format. CMS, PAdES, FIPS 206 and reader support
remain unverified. The app has no accounts, telemetry or automatic updater.

The executable is unsigned. Compare SHA-256 values with the release record
from a trusted source. A matching checksum identifies the package. Follow the
security policy on your computer for unsigned software. Clean-machine and
SmartScreen acceptance are recorded separately from the release checks.
