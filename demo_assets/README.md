# Public thesis sample

`sample-unsigned.pdf` is a generated 742-byte, single-page ASCII PDF. It contains
no personal information, keys, credentials or benchmark data. Its text is:

```text
HybridSign thesis demonstration
Decision: APPROVED
Public sample - no personal data.
```

Copy it to your disposable demo folder before signing. Save the signed output
under a different name. To demonstrate modification, copy that **signed** output
and replace the single `APPROVED` with `REJECTED`; both are eight ASCII bytes.
Keep the original signed file intact. Verification of the edited copy must fail
under the same public-key pair that accepts the original.

The GUI regression generates the changed copy locally and checks the actual
native verification result. The presentation script describes an equivalent
Notepad edit using Windows GUI controls, to rehearse before presenting. Notepad
must retain the `.pdf` filename and ASCII-compatible UTF-8 encoding. This sample
has no binary bytes that require conversion, but external editors can still
change line endings or encoding; any such change is also a modification.

The test validates the file's ASCII content, object/xref offsets and stream
length. This is a demonstration fixture, not a PDF conformance test suite.
Signature containers remain the project's inherited custom format; no
CMS/PAdES or general PDF-reader signature compatibility is implied.

See [Phase 4C.1 demo readiness](../docs/phase4c1-demo-readiness.md) for preparation,
the live script, evidence and remaining manual checks. Do not store real vaults
or signed personal documents in this directory.
