# Phase 5.1 — Research audit and thesis foundation

**Research topic** — “Nghiên cứu sơ đồ chữ ký số lai kháng lượng tử giữa Falcon v1.2 và Ed25519”

This audit records the evidence available on 19 November 2026. The
HybridSign checkout started clean on `thesis/ui-demo` at `1c95c77`.
The inherited checkout at `D:\Final_Thesis` is on `thesis/development`
at `39821b0`. The original inherited commit is `0f3b513`. The project
inherits the signature order, messages and custom PDFs from FALCON/eSign.
Subsequent thesis development added strict parsing, verified atomic signing,
in-memory key handling, a local encrypted vault and a Windows desktop.
[Repository rules](../AGENTS.md) · [Provenance](PROJECT_PROVENANCE.md) ·
[Inherited citation](../CITATION.cff) · [Desktop baseline](phase4c3-final-release-review.md)

## Main findings

- **Verified implementation.** The Windows CPython 3.11.9 environment
  uses PyNaCl 1.6.2 for pure Ed25519 and `pqcrypto` 0.3.4's
  `falcon_512` module for Falcon-512. Both local Python wrappers and
  their native extensions match the corresponding published Windows
  wheels. The Falcon wheel's attestation fields point to the pinned
  source lineage recorded below.
- **Verified behavior.** The PDF verifier checks one adjacent nested pair
  and requires both cryptographic checks. The inner Ed25519 message is
  raw selected bytes. The outer Falcon message is an application-level
  64-byte SHAKE256 digest covering the entire completed Ed25519 container.
  Rejection is established for the tested content, length, metadata and
  key mutations. Source review found a native padded-encoding compatibility
  rule that limits claims about detecting every possible final-byte change.
  [Construction and limits](phase5-1-implementation-evidence.md)
- **Verified data inventory.** All ten inherited CSVs and five input PDFs
  match their Phase 1 SHA-256 entries. Exactly 100 rows appear in each CSV.
  Historical stage clocks, input labels and desktop acceptance measure
  different scopes. Historical hardware and dependency versions for the
  recorded CSV runs could not be established. The file labelled 50 MB is
  larger than the desktop signing limit.
  [Data audit and experiment plan](phase5-1-experiment-gap-analysis.md)
- **Research interpretation.** The thesis can support a source-level
  description, functional correctness for the tested profile and a
  reproducible future comparison. Full Falcon v1.2 conformance, formal
  post-quantum security of this composition, robust signer identity and
  standalone performance comparisons remain unestablished.
  [Claim-to-evidence matrix](phase5-1-thesis-traceability.md)

## Research motivation

Ed25519 relies on the difficulty of elliptic-curve discrete logarithms.
Under the sufficiently capable quantum-computer model, Shor's algorithm
provides a polynomial-time approach to discrete logarithms. Falcon uses a
different lattice-based construction and is studied as a post-quantum
candidate under its own assumptions. Requiring both layers motivates
evaluating a hybrid transition design. It supplies no experiment or proof
that the application as a whole resists quantum or classical attacks.
[Shor's discrete-logarithm algorithm](https://arxiv.org/abs/quant-ph/9508027) ·
[Falcon v1.2](https://falcon-sign.info/falcon.pdf) ·
[Hybrid signature security properties](https://www.rfc-editor.org/rfc/rfc9955.html)

## Ed25519 implementation

RFC 8032 §5.1 defines Ed25519 over edwards25519, with a 32-byte secret seed,
32-byte encoded public key, and 64-byte signature (encoded `R || S`).
Its algorithm internally uses SHA-512. PyNaCl `SigningKey(seed)` derives
the native key pair via libsodium `crypto_sign_seed_keypair`. The portable
form stored by HybridSign is the 32-byte seed. The native libsodium
secret-key representation includes the seed and public key and is 64
bytes. `SigningKey.sign(message).signature` extracts the detached part
of the single-part signing call. `VerifyKey.verify(message, sig)` uses
the matching single-part verification. These calls use pure Ed25519.
The application supplies the covered bytes directly and does not select
Ed25519ph or Ed25519ctx. Standard Ed25519 signatures are deterministic for
a fixed seed and exact message. Generation of the seed uses library
randomness. [RFC 8032 §5.1 and §7.1](https://www.rfc-editor.org/rfc/rfc8032.html#section-5.1) ·
[Libsodium signing APIs](https://doc.libsodium.org/public-key_cryptography/public-key_signatures) ·
[PyNaCl 1.6.2 signing source](https://github.com/pyca/pynacl/blob/1.6.2/src/nacl/signing.py) ·
[Key generation](../keygen.py) · [Signature construction](../sign.py)

The installed `nacl/signing.py` and `nacl/_sodium.pyd` match the published
`pynacl-1.6.2-cp38-abi3-win_amd64.whl` by byte comparison. The local
native extension's SHA-256 is
`57822e7aed944269943bcb855fc14560a5b6ae38869de4e3d00c380a5119ecc7`,
also recorded in the approved payload manifest. PyNaCl's tagged changelog
reports bundled libsodium **1.0.20-stable, 31 December 2025 build**. That
version is from the identified upstream release record. The installed
extension did not expose a Windows `sodium_version_string` symbol through
the direct DLL lookup used in this audit.
[PyNaCl 1.6.2 distribution](https://pypi.org/project/PyNaCl/1.6.2/) ·
[Tagged changelog](https://github.com/pyca/pynacl/blob/1.6.2/CHANGELOG.rst) ·
[Approved runtime manifest](../frontend/qa/phase4c2a/release-manifest.json)

## Falcon implementation and version boundaries

| Evidence layer | Confirmed finding and scope |
| --- | --- |
| Algorithm specification | The authors' document is **Falcon specification v1.2**, 1 October 2020. It describes a GPV hash-and-sign construction over NTRU lattices with fast Fourier sampling. Falcon-512 uses ring degree 512 (`logn = 9`), modulus 12,289 and squared norm bound 34,034,726. Its designers target NIST security category 1. That target is separate from validation of a binary. [Specification, §§3.9–3.13 and Table 3.3](https://falcon-sign.info/falcon.pdf) |
| Python package and identifier | `pqcrypto==0.3.4`, `pqcrypto.sign.falcon_512`, and the `PQCLEAN_FALCON512_CLEAN` CFFI entry points in `falcon_512.cp311-win_amd64.pyd`. The similarly named padded variant is a different binding and is not the application's signer. [PyPI release metadata](https://pypi.org/pypi/pqcrypto/0.3.4/json) · [Application call sites](../keygen.py) |
| Published binary | The official wheel `pqcrypto-0.3.4-cp311-cp311-win_amd64.whl` hashes to `36ec272e32d24cd137fd937bf218d0c86f4b0d5d17ed26828708e1a71b667380`. Installed wrapper SHA-256 `ef1acb5f04592c0c8bea1f11b32478216cf499d66d27f91232094daee23d2f4b`. Native SHA-256 `ad5983a68922b01d84332ee800e16b55f001d1353ef62b32efd8d5d1216da237`. Its native digest also matches the approved desktop payload entry. The wheel was downloaded into memory, hashed and read as an archive to compare the two installed files. [Wheel metadata](https://pypi.org/pypi/pqcrypto/0.3.4/json) · [Desktop manifest](../frontend/qa/phase4c2a/release-manifest.json) |
| Source lineage | The PyPI statement subject matches the exact filename and SHA-256 above. The published certificate fields identify `backbone-hq/pqcrypto` commit `4d35e96a3a921f6a0907fcbce31f441c11e2de8d`. At that commit, the PQClean gitlink points to `2cc64716044832eea747234ddbffc06746ab815d`, the workflow checks out submodules, and `compile.py` selects the `clean` variant. These fields were inspected. The attestation signature, certificate chain and transparency evidence were not independently verified, and no native binary was rebuilt. [PyPI attestation](https://pypi.org/integrity/pqcrypto/0.3.4/pqcrypto-0.3.4-cp311-cp311-win_amd64.whl/provenance) · [Pinned workflow](https://github.com/backbone-hq/pqcrypto/blob/4d35e96a3a921f6a0907fcbce31f441c11e2de8d/.github/workflows/ci.yml) · [Pinned compiler script](https://github.com/backbone-hq/pqcrypto/blob/4d35e96a3a921f6a0907fcbce31f441c11e2de8d/compile.py) · [Gitlink](https://api.github.com/repos/backbone-hq/pqcrypto/contents/pqclean?ref=4d35e96a3a921f6a0907fcbce31f441c11e2de8d) |
| PQClean revision label | The clean source metadata says **20211101 with PQClean patches**. The authors separately describe a 1 November 2021 external implementation PRNG-helper fix and state that PQClean and the NIST API, vectors and associated benchmarks were unaffected by that particular issue. The date is implementation lineage. Matching dates and sizes cannot establish equivalence across the v1.2 spec and all build/API behavior. [Pinned PQClean metadata](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/META.yml) · [Authors' implementation notice](https://falcon-sign.info/) |
| FN-DSA and compliance | The NIST project page consulted for this audit lists Falcon as selected and FIPS 206 as in development. FN-DSA is the standardization work based on Falcon, with changes discussed by NIST. A submission spec, a Python wheel, a future or published standard revision, tested conformance and independent module validation are distinct evidence. No such conformance or certification is asserted for HybridSign. [NIST process status](https://csrc.nist.gov/projects/post-quantum-cryptography/post-quantum-cryptography-standardization) · [NIST IR 8413](https://csrc.nist.gov/pubs/ir/8413/upd1/final) · [NIST FN-DSA presentation](https://csrc.nist.gov/presentations/2025/fips-206-fn-dsa-falcon) |

### Native encodings and known-answer evidence

- The pinned binding has a **897-byte public key**, **1,281-byte private
  key** and **752-byte maximum** detached-signature buffer. The public
  encoding contains a header and packed polynomial `h`. The private
  encoding contains a header and encoded polynomials `f, g, F`.
  The detached signature is a format byte (`0x39`), 40-byte nonce and
  the compressed polynomial. The native signer reports the actual length.
  Falcon's native hash-to-point uses the nonce and message. For this
  application the native message is already a separate 64-byte SHAKE256
  digest of covered file bytes. The pinned C wrapper also has a distinct
  attached-signature API, outside the project's signing path.
  [API header](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/clean/api.h) ·
  [Native wrapper and encodings](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/clean/pqclean.c)
- The specification's Table 3.3 lists `sbytelen = 666` for its
  fixed-length Falcon-512 encoding. The deployed detached signer has a
  variable-length encoding. The 752-byte API bound, the spec's 666-byte
  field and the PDF's 2,048-byte reserved Falcon capacity describe
  different objects. The pinned compressed verifier includes a specific
  padded compatibility case. This is one concrete point for a future
  spec-to-source and test-vector comparison.
  [Falcon specification §§3.11, 3.13](https://falcon-sign.info/falcon.pdf) ·
  [Pinned decoder](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/clean/pqclean.c#L228-L247)
- RFC 8032 §7.1 publishes Ed25519 vectors, and tagged PyNaCl has upstream
  signing-vector tests. No dedicated local RFC 8032 vector check was
  identified in HybridSign. The pinned PQClean metadata lists
  `nistkat-sha256` and `testvectors-sha256` for Falcon-512. These hashes
  were checked as source metadata only. Its NIST KAT harness uses controlled
  test randomness with the attached API, so those hashes cannot be used as
  a byte-for-byte oracle for a freshly generated detached PDF signature.
  No Falcon KAT regeneration or independent detached interoperability run
  was performed. [RFC 8032 vectors](https://www.rfc-editor.org/rfc/rfc8032.html#section-7.1) ·
  [PyNaCl vector tests](https://github.com/pyca/pynacl/blob/1.6.2/tests/test_signing.py) ·
  [PQClean KAT harness](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/test/crypto_sign/nistkat.c) ·
  [PQClean expected hashes](https://github.com/PQClean/PQClean/blob/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/META.yml)
- Local evidence comprises native key self-tests, two fixed Phase 1 PDF
  fixtures and newly generated round trips with both signature layers.
  Separate vault tests implement published Argon2id and AES-GCM test
  vectors. Those test different primitives and establish no Falcon claim.
  [Layer tests](../tests/test_hybrid.py) · [Frozen fixture tests](../tests/test_container_parsing.py) ·
  [Vault primitive tests](../tests/test_vault_crypto.py#L454) ·
  [Earlier Falcon provenance](falcon-implementation-provenance.md)

**Thesis wording** — “Luận văn trình bày Falcon theo đặc tả v1.2. Nguyên mẫu
sử dụng Falcon-512 qua binding PQClean clean trong pqcrypto 0.3.4. Dấu vết
mã nguồn của bản cài đặt được đối chiếu tới bản PQClean có nhãn 20211101
kèm các bản vá. Phép đối chiếu và kiểm thử chức năng chưa xác lập tuân thủ
đầy đủ đặc tả v1.2 hay FIPS 206.”

A stronger conformance claim would require a named target specification
and profile, a reviewed mapping of key generation, sampling, hashing,
parameter and encoding rules and patches, and valid and invalid vectors
against an independent implementation using the same exact representation.
A reproducible native build or independently verified attestation would
strengthen the binary-to-source link. Interoperability, side-channel
evaluation and standards validation have separate acceptance criteria.

## Validation and remaining academic decisions

On the existing Windows x64 .venv, the following existing, non-GUI test
subset passed **748 tests in 48.41 s**, with zero failed, skipped, xfailed
or xpassed. It includes malformed ranges and padding, order, both layers,
wrong keys, native key and vault checks, original-key recovery, frozen
signatures and the actual verifier through its desktop service.

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_hybrid.py tests/test_container_parsing.py tests/test_completed_signatures.py tests/test_signature_pair.py tests/test_key_material.py tests/test_vault_crypto.py tests/test_vault_signing.py tests/test_desktop_verification.py
```

This audit did not repeat the GUI release suite. Its separate Phase 4C.3
baseline is 1,666 pytest passes and eight Windows symlink skips, 266
Playwright passes and a successful portable replay. Source, sample and
dataset hashes were verified read-only. No dependencies or new performance
measurements were added. The 742-byte [public sample](../demo_assets/sample-unsigned.pdf)
matches the Phase 4C.3 digest
`2d94ba434bbbfda3ffcd78731f2e94146352e5dc7680dcd566d2ca0614a20639`.
The [frozen fixture file](../tests/fixtures/phase1-signatures.json) has
checkout SHA-256 `72b82ae5013248a727803d6c56338905ccd989c1f321f0e927173bc1a4457aa0`.
Its Git blob is identical in both checkouts.
[Release test evidence](phase4c3-final-release-review.md#regression-results-and-test-driver-correction)

The next academic decisions are whether the supervisor expects a claim about
a specific interoperable Falcon encoding, which performance comparison
boundaries constitute the thesis experiment, and which evidence must be
retained. No university-specific structure, rubric or approved outline was
found in the inspected workspaces. The recommended chapter structure and
claims awaiting evidence are recorded separately.
[Phase 5.2 protocol](phase5-1-experiment-gap-analysis.md#phase-52-protocol) ·
[Thesis structure](phase5-1-thesis-traceability.md#proposed-chapter-structure)
