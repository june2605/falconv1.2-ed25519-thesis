# Phase 1 regression baseline

Recorded on 2026-11-04 (Asia/Bangkok). Inherited commit:
`0f3b513205463dd1766c45e9b9e364d92c2de882` (`Update CITATION.cff`).
The working tree initially contained only the user-provided, untracked
`AGENTS.md`; it was read and left unchanged.

`phase1-baseline.json` records all 45 installed distributions, the Windows x64
platform, inherited source SHA256 hashes, and SHA256 hashes for all 15 tracked
benchmark CSVs and input datasets. It describes the environment as observed,
not a newly resolved dependency lock or a list of packages needed at runtime.

| Dependency | Observed version |
| --- | --- |
| CPython | 3.11.9 |
| pqcrypto | 0.3.4 |
| PyNaCl | 1.6.2 |
| Streamlit | 1.66.1 |
| pytest | 9.2.0 |
| cffi | 2.1.1 |

PyInstaller is declared by the inherited requirements but is not installed.
No packages were installed or upgraded for Phase 1. No Git commit or push was
performed.

## Changes

| File | Purpose |
| --- | --- |
| `app.py` | Unpack the first element of `verify_file()` before choosing the validity message. The tuple return contract is unchanged. |
| `pytest.ini` | Limit discovery to `tests/`, expose repository modules, and make unexpected xfail passes fail the suite. |
| `tests/conftest.py` | Generate two small one-page PDFs with a catalog, page tree, Helvetica resource, length-delimited content stream, xref table and trailer. Generate fresh keys and signed documents in pytest temporary directories. |
| `tests/test_keygen.py` | Check raw key sizes, Ed25519 key correspondence, real signing/verification, and independent key pairs. |
| `tests/test_hybrid.py` | Test round trips, tuple interfaces, unchanged input, independent protocol verification, altered files, incorrect keys, unsigned files and failure of either layer. |
| `tests/test_app_verification.py` | Execute the actual `app.py` verification branch with simulated Streamlit controls, real uploaded bytes and the real verifier; check valid and invalid messages. |
| `tests/test_integrity_weaknesses.py` | Strict expected-failure tests for Falcon padding and malformed ByteRange acceptance. |
| `docs/phase1-baseline.json` | Record the inherited commit, source/dataset hashes and installed versions before the UI edit. |
| `docs/phase1-regression.md` | Record scope, test commands, outcomes and unresolved issues. |

The only production behavior change is the UI boolean handling. `keygen.py`,
`sign.py`, `verify.py`, and `utils.py` remain byte-for-byte unchanged. No React,
FastAPI, PostgreSQL, launcher, packaging or benchmark changes were made.

## Test execution and outcomes

Use the existing environment from the repository root:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Before editing `app.py`, running `tests/test_app_verification.py` produced
**2 failed, 2 passed**. The altered document returned a tuple whose first
element was `False`, but the UI called `st.success()` for each PDF fixture.
The valid-document controls passed. This demonstrated the defect before its
fix, rather than merely asserting Python tuple truthiness in isolation.

After the fix, the full suite produced **32 passed, 12 xfailed in 2.84 seconds**,
with exit code 0, no skips and no unexpected passes. The 12 expected failures
represent three unresolved issues:

| Desired behavior not yet implemented | Cases |
| --- | ---: |
| Reject a change to unused Falcon signature padding | 2 PDF fixtures |
| Reject out-of-bounds, overlapping, nonzero-start and empty ByteRanges during parsing | 4 malformed ranges x 2 algorithms = 8 |
| Reject an out-of-bounds Falcon ByteRange even when genuine keys sign that malformed state | 2 PDF fixtures |

The latter integration test uses real signatures: a malformed second offset
falls beyond EOF, a new Falcon signature is embedded, and the inherited
verifier still accepts the document. This distinguishes missing structural
validation from ordinary rejection of a changed, stale signature.

Strict xfails are outstanding security work, not successful security checks.
Fixing one will produce an unexpected-pass failure until its xfail marker is
removed and the new behavior reviewed. The parser tests expect `ValueError`
as the future validation interface; production parser behavior was not changed.

The suite independently verifies the preserved protocol: ordinary Ed25519
over the selected first-state bytes, followed by Falcon-512 over a 64-byte
SHAKE256 digest of the state containing the Ed25519 signature. A dedicated
case corrupts Ed25519 and re-signs Falcon, proving that a valid outer signature
cannot compensate for a failed inner signature. Another case keeps Ed25519
valid while corrupting Falcon. Both are rejected.

PDFs, private keys and signed files are created only in pytest temporary
directories. No private keys or signed test documents are added to the
repository. Original `benchmark/` and `data_test/` files are never used by the
suite. This is not a PDF reader interoperability or browser rendering test;
Streamlit controls are simulated, but application branching and cryptography
execute normally.

## Unresolved work

1. Enforce canonical ByteRanges, bounded signature lengths, container ordering
   and pairing, and final-state coverage. Reject noncanonical Falcon padding.
   Preserve compatibility deliberately when introducing those rules.
2. Generated keys still use shared plaintext working-directory files; key
   replacement is not atomic. Trusted identity and hybrid key-pair binding
   remain absent.
3. Application temporary files can remain after exceptions. Signing still
   writes intermediate states directly to the destination.
4. Placeholder collisions, unchecked signature capacity and broad exception
   handling remain. These do not yet all have dedicated regression tests.
5. `requirements.txt` remains unpinned. The recorded environment supports
   reproduction, but a dependency lock still needs separate validation.
6. The format remains custom appended trailers. CMS, PAdES, FIPS 206 and PDF
   reader interoperability have not been established; the UI's absolute
   security/integrity wording remains unsupported.
7. Repeated-signature policy, launcher behavior, encrypted PDFs, failure-path
   cleanup and large-file memory/benchmark accuracy need later coverage.

Baseline SHA256 verification after the test run confirmed all 15 original
benchmark/dataset files and all inherited source files except the intentional
`app.py` edit were unchanged.
