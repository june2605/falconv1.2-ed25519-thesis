# Phase 3.2B.1: in-memory encrypted vault regression record

Implemented in `D:\Final_Thesis_GitHub` on `thesis/development`, starting from
`0afe0ad5ca3685602a4ede0004406f8764694146`. The working tree was initially clean.
Only the approved in-memory codec was implemented. No package installation,
commit, push, historical dataset edit or existing-test weakening was performed.

## Files

| File | Change |
| --- | --- |
| `vault_format.py` | New strict positional v1 serializer/parser, immutable public metadata, exact payload encoding and sanitized exception taxonomy. |
| `vault_crypto.py` | New two-argument seal/unseal APIs, exact approved backend/profile, native pair validation, original-header authentication and process-local KDF resource gate; no persistence. |
| `requirements.txt` | Record only the approved new dependency pin `cryptography==50.0.2`; existing declarations unchanged. This is not a full environment lock. |
| `tests/vault_cases.py` | Independent public-format controls, raw positional mutation helpers and disposable-pair payload assembly; no stored private-key fixture. |
| `tests/test_vault_format.py` | Exact sizes, offsets, endianness, immutable types, UUIDs, profile/length/identifier/digest rejection and metadata validation. |
| `tests/test_vault_crypto.py` | Real-profile integration, authenticated mutations, password boundaries, native correspondence checks, primitive vectors, backend faults, resource cleanup and no-file-I/O instrumentation. |
| `docs/phase3-2-vault-format.md` | Complete frozen v1 binary specification, validation/error rules, API, compatibility and security limits. |
| `docs/phase3-2b1-regression.md` | This runtime, test and scope record. |

`hybrid_keys.py`, `keygen.py`, `sign.py`, `signing_io.py`, `utils.py`, `verify.py`,
`app.py`, `demo.py`, all pre-existing tests and both frozen Phase 1 signature
fixtures are unchanged. No unavoidable compatibility edits were needed.

## Dependency and runtime validation

The approved dependency was already installed. No installer was run and no
dependency was upgraded or added to the environment during this phase.

| Component | Observed value |
| --- | --- |
| Interpreter | Existing `.venv`, CPython 3.11.9, AMD64 |
| Platform | Windows-10-10.0.26200-SP0 |
| cryptography | 50.0.2 |
| Linked OpenSSL | OpenSSL 4.0.3 29 Sep 2026 |
| cffi | 2.1.1 |
| PyNaCl | 1.6.2 |
| pqcrypto | 0.3.4 |
| pytest | 9.2.0 |

Before implementation, a real Argon2id derivation at 65536 KiB, 3 iterations,
4 lanes, 32-byte output and 16-byte salt succeeded (68.911 ms), followed by
successful real AESGCM encryption/decryption and full-tag length validation.
Unsupported implementations would have stopped this work, without a fallback.

A later five-derivation local probe measured **62.229, 61.934, 58.629, 58.985,
59.293 ms**, median **59.293 ms**. AESGCM round trips also succeeded. These are
local functional/timing observations using public disposable probe inputs,
not a cross-device performance guarantee, security certification or modification
of the inherited benchmarks. No password, derived key or private value was
printed by the probes.

The loader requires the exact pinned package/API. Production operations perform
the actual approved derivation and AEAD operation; native unsupported/allocation
failures reject without algorithm switching or returning a partial result.
Malformed public inputs reject before loading the backend or invoking the KDF.

## Test-first evidence and results

Tests were added before the two production modules. The initial bounded red run
stopped after two expected `ModuleNotFoundError` setup errors for the absent
`vault_format` module. After implementation, the first 219 new cases passed.
Review added 23 more payload/backend/native-validation cases without changing
existing tests, for **242 new passing cases**.

Commands use `-B` and disable pytest's cache provider:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_vault_format.py tests/test_vault_crypto.py
```

| Run | Passed | Failed / errors | Skipped | Xfailed | Xpassed | pytest time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline before changes | 903 | 0 | 8 | 0 | 0 | 35.09 s |
| Final new-code suite | 242 | 0 | 0 | 0 | 0 | 1.69 s |
| Complete final suite | **1145** | **0** | **8** | **0** | **0** | **37.22 s** |

The eight skips are the existing Windows symlink-privilege checks at
`tests/test_signing_io.py:22`. This environment cannot create those links without
Developer Mode or the symlink privilege. No new test is skipped and no new xfail
or xpass exists. Those filesystem tests were not weakened or reclassified.

The complete suite retains all 903 existing passing test purposes, including
frozen legacy signatures, custom capacities, strict pair/ByteRange/padding rules,
atomic publication/failure cleanup, in-memory signing, UI handling and all
eleven-item return contracts.

All **15** original dataset SHA-256 hashes in `docs/phase1-baseline.json` were
rechecked against `D:\Final_Thesis` and matched. Only streaming reads were used;
none of the original benchmark/PDF datasets was modified or copied here.

## Coverage and isolation

- The independent header control uses explicit offsets and unsigned big-endian
  writes, separate from the production struct. Every fixed integer has valid
  controls and rejection cases. Tests cover exact 1069/1331/1347/2416 lengths,
  exact public/private positions, UUID standard bytes, ID digest encoding,
  malformed lengths/types, truncation, trailing data and the defensive ceiling.
- Parser faults cover wrong algorithms, encodings, versions, profile lengths,
  Argon2 version, zero/nearby/extreme costs, invalid UUIDs and inconsistent IDs.
  Backend-loading spies prove public-header rejection occurs before KDF work.
- Real Argon2id/AESGCM integration recovers both identical private keys, both
  public keys and the unchanged ID. Separate encryptions have fresh UUID/salt/
  nonce/ciphertext. Real wrong-password and Unicode trim/case/normalization
  differences reject. A manually encrypted real-profile one-character-password
  vault demonstrates that unlock does not impose the creation minimum.
- Password tests check exact `str`, strict UTF-8, surrogates, empty strings,
  code-point creation minimum and 1024-byte limits with multibyte boundaries.
- AES-GCM tests mutate the UUID, salt, nonce, first/middle/last ciphertext and
  tag positions. A changed public key with recomputed public ID still fails AAD
  authentication. A spy requires the exact original header as AAD; no header
  serializer is allowed on unlock. Decrypted-payload parsing must not run after
  a failed authentication tag.
- Authenticated malformed payload fields and mixed real private keys reject.
  Both native signature self-tests are required, including failures of Ed25519
  sign/verify and Falcon sign/verify. An input pair modified after construction
  is revalidated on sealing. No unlock failure generates replacement keys.
- Fault injection covers missing/wrong backend, initialization, derivation,
  encrypt/decrypt, unsupported algorithms, memory allocation and unexpected
  native exceptions, as well as wrong derived-key/ciphertext sizes and types.
  Fixed sanitized errors suppress displayed native chains. Passwords, private
  bytes and derived keys are absent from errors and captured logs/output.
- A real-profile seal/unseal test forbids Python file open/read/write,
  `os.open`/`os.mkdir` and tempfile creation after dependency imports. No codec
  operation performs filesystem I/O. Keys used by tests are generated in RAM
  and are not committed/exported as fixtures.
- The process-local gate rejects a concurrent operation without a second KDF
  and releases its permit after an injected failure.

Most malformed parser/AEAD boundary tests replace only the private KDF helper
with a public deterministic test key. AESGCM tag processing and native hybrid
key self-tests remain real. Backend-failure tests inject deliberately failing
classes only in their own cases. These doubles do not expose a cheaper profile
or fixed-randomness parameter in either public API. Full real-profile cases
remain separate, and production validation is never disabled.

Primitive known-answer tests use:

- [RFC 9106 section 5.3](https://www.rfc-editor.org/rfc/rfc9106.html#section-5.3)
  for Argon2id v19, including the vector's optional secret and associated data.
  Its 32 KiB cost is a primitive-test input, not an accepted vault profile.
- AES-256-GCM specification cases 13/14, as preserved in the upstream
  [BoringSSL vector file](https://boringssl.googlesource.com/boringssl/+/e8c862cf1421/crypto/cipher/test/aes_256_gcm_tests.txt),
  for empty and single-block plaintext with a 96-bit nonce/full tag.
- The official [NIST AES-GCM example document](https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Standards-and-Guidelines/documents/examples/AES_GCM.pdf),
  GCM-AES256 Example 4, for encryption and decryption with nonempty AAD.

These tests are implementation evidence, not cryptographic module certification.

## Compatibility and deferred security work

The codec accepts exactly the approved v1 2416-byte format and only its fixed
Argon2id/AES-256-GCM profile. Other versions/profiles require a separate explicit
migration; there is no silent permissive reader. It preserves original key fields
and IDs exactly. Existing PDF bytes, algorithms, digest/message construction,
on-disk containers and public signer/verifier contracts are unaffected.

This phase does **not** save a vault or integrate one into signing/UI flows.
Phase 3.2B.2 persistence, encrypted-only temporaries, atomic writes, ACLs,
alias checks, cross-process file locking, password changes, encrypted backup/
restore and crash recovery remain deferred. Phase 3.2B.3 signing/UI integration
and its end-to-end tests also remain deferred. No frontend, backend, authentication,
identity enrollment, revocation/rotation service or database was introduced.

Residual risks include offline guessing of stolen ciphertext, inadequate user
password entropy, public-key/UUID linkability, no trusted signer identity, whole-
vault replacement/rollback, OS RNG compromise, native-code faults and compromised
clients. Python/native plaintext copies and tracebacks are not securely erased;
swap, crash dumps and hostile debuggers are not excluded. The KDF gate is only
process-local and does not prevent sequential guessing or multi-process resource
exhaustion. No recovery without the password/key material and no FIPS, CMS,
PAdES or production-security compliance is promised. See the format document
for the full trust and memory-handling limits.
