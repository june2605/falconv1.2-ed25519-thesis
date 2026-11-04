
# Falcon-Ed25519 Thesis Project

## Project objective
Develop a research-grade hybrid digital signature application
for PDF documents using Falcon-512 and Ed25519.

The project inherits the existing FALCON/eSign research prototype.
Preserve the original research behavior until it has been audited
and covered by regression tests.

## Technology
- Python 3.11 for cryptography and PDF processing.
- React, TypeScript, HTML and CSS for the frontend.
- pywebview for the Windows desktop application.
- FastAPI for backend services.
- PostgreSQL for server-side data.
- SQLite for local application data when necessary.
- pytest for automated tests.

## Cryptographic requirements
- Ed25519 signs the first PDF state.
- Falcon signs the subsequent state containing the Ed25519 signature.
- Hybrid verification requires both signatures to be valid.
- Public keys must be linked to a trusted signer identity and key pair.
- Private keys and signing operations remain on the client.
- Reject modifications after the final Falcon signature.
- Never claim FIPS 206, CMS or PAdES compliance without evidence.

## Development rules
- Analyze existing code before modifying it.
- Do not rewrite the cryptographic implementation without justification.
- Add regression tests before changing signing or verification behavior.
- Never commit private keys, passwords or sensitive documents.
- Make small, reviewable changes.
- Do not push directly to main.
- Ask before deleting files or changing repository history.
- After each change, report modified files and test results.
