# Phase 3.2B.3: managed vault-based PDF signing

Implemented in `D:\Final_Thesis_GitHub` on `thesis/development`, from committed
Phase 3.2B.2 baseline `afdf80dbb786b5efa11f8cbcdc8a74c814ab4672`. The repository,
branch, latest commit and clean working tree were verified before editing.
The existing `.venv` was used. No dependencies were installed, benchmarks edited,
commits created or pushes performed.

The approved vault v1 layout and cryptographic profile remain those in
`phase3-2-vault-format.md`. Phase 2 and Phase 3 regression records were reviewed.
This step bridges authenticated vault unlock to the existing memory signer;
it introduces no second signature implementation, key regeneration, PDF/vault
format change, trusted identity, account service or frontend/backend architecture.

## Changed files and APIs

| File | Change |
| --- | --- |
| `vault_signing.py` | New controlled `sign_vault_document(handle, input_path, output_path)` boundary, storage protection and repeated managed-state/ACL/revision checks. |
| `vault_signing_cli.py` | New local interactive unlock/sign/verify/lock harness; no password argument, environment or echoed-input mode. |
| `vault.py` | Record authenticated handle issuance, process/thread/module context and captured encrypted revision in a weak registry; remove registrations on locking; generalize sanitized cleanup notes for both vault and PDF artifacts. |
| `vault_io.py` | Expose the canonical `lock_file_path()` helper and reuse it in the unchanged cooperative-locking scheme. |
| `signing_io.py` | Add internal immutable `SigningProtection` and an optional prepublication callback inside `SigningTransaction.publish()`. |
| `sign.py` | Add optional keyword-only `_protection=None` to `sign_with_key_material()`; pass protected paths and the guard to the existing transaction. |
| `tests/test_vault_signing.py` | Native API/process/thread integration, original-key use, independent signature-layer checks, storage aliases, stale contexts, faults, cleanup, capacities and legacy fixtures. |
| `tests/test_vault_signing_cli.py` | Real signing workflow with prompt doubles, password-channel/fallback checks, sanitized failures, locked handles and native noninteractive rejection. |
| `docs/phase3-2b3-regression.md` | This behavior, regression and limitation record. |

No pre-existing test or fixture was changed. `app.py`, `demo.py`, `utils.py`,
`verify.py`, `hybrid_keys.py`, `keygen.py`, `vault_crypto.py`, `vault_format.py`,
dependency declarations and historical regression documents are unchanged.
The Streamlit plaintext-upload prototype is not migrated or redesigned here.

```python
from vault import unlock_vault
from vault_signing import sign_vault_document
from verify import verify_file_with_public_keys

with unlock_vault(vault_path, password) as handle:
    result = sign_vault_document(handle, source_pdf, destination_pdf)
    assert len(result) == 11
    public = handle.metadata.public_keys
    assert verify_file_with_public_keys(destination_pdf,
        public.ed25519_public_key, public.falcon_public_key)[0] is True
# Managed key access is invalidated, including when an ordinary exception exits.
```

The bridge returns the unchanged eleven-element signing tuple: caller-supplied
output path followed by ten original timing slots. Unlock, managed guards, locks,
final verification and publication are not added to those cryptographic phase
measurements. The bridge leaves a caller-owned handle open after success or
ordinary signing failure; use the handle context manager or `lock_vault()`.

Existing three-argument `sign_with_key_material()` calls remain valid. Its new
underscore-prefixed context is an internal caller contract, not an authenticated
identity assertion or standalone access-control capability. The path-based
`sign_file(..., *, pk_falcon=...)`, all verifier APIs and their return contracts
remain unchanged.

## Handle validity, lifetime and concurrency

Only `unlock_vault()` registers an eligible handle after authentication, native
key correspondence self-tests and a post-unlock revision recheck. Registration
binds the actual result/key-pair object identities, original encrypted snapshot,
process ID, issuing `Thread` object and module-context token. A weak-key registry
does not keep an otherwise unreferenced handle alive. Registry values contain
encrypted bytes, public filesystem metadata and object/context identifiers;
they do not retain extra private-key objects, passwords or derived keys.

The controlled signer rejects:

- Locked, uninitialized, wrong-type or subclass handles.
- Manually constructed or copied handles, even with otherwise valid key material.
- Handles used from another thread/process/module context.
- Modified internal result/path/revision bindings.
- Deleted, moved, replaced, re-encrypted or modified vault revisions, including
  byte-identical replacement files with a different filesystem identity.

The conservative context policy requires unlocking in the worker thread that
will sign. A worker can unlock its own handle and sign normally. No handle
transfer API is introduced. Existing public `key_pair`/`metadata` accessors retain
their Phase 3.2B.2 behavior; the new context policy applies to managed signing.
Ordinary Python internals and already copied key references are not protected
from a compromised process.

The operation holds the handle mutex and the vault's existing exclusive,
fail-fast cooperative lock through native PDF replacement. Password changes,
other managed signing attempts and cooperating lifecycle operations on that
vault cannot proceed concurrently. Signing does not keep the vault's data handle
open continuously; it reuses bounded, ACL-validated captures and revision hashes.
The lock sidecar remains persistent and empty, with the Phase 3.2B.2 permissions.

A concurrent `lock_vault()` from another thread waits for an in-flight operation
on that handle to finish; it is not a cancellation mechanism. Same-thread
reentrant invalidation is detected by the final guard and prevents publication.
Locking drops managed access and registration, without guaranteed Python/native
memory zeroization or revocation of previously obtained references.

## Protected paths and publication boundary

The integration supplies captured and live protected paths for the active vault
and its exact canonical lock file, including the original requested vault path.
The shared signer repeats its normal relative/canonical/identity alias checks.
The managed output policy additionally:

- Applies the existing fixed-local-NTFS path policy, rejecting observed reparse/
  symlink/junction ancestors, unsupported namespaces/volumes and hard-linked
  existing destinations.
- Reserves `.hybrid-vault-` basenames, including absent lock/candidate-style names.
- Refuses to replace any existing file beginning with `b"HYBKVLT\x00"`, regardless
  of filename extension, header validity or whether its vault was opened here.
  This conservatively protects recognizable other vaults and encrypted backups.

These output restrictions are new managed-boundary policy; the default direct
memory signer retains its previous behavior. The magic check is a bounded
eight-byte read, not discovery/decryption of key filenames. Reserved names and
magic can reject otherwise benign user-selected output files. There is no global
inventory of arbitrary backup locations: unregistered files whose magic has been
destroyed cannot be recognized as backups by this heuristic. Known active vault
and lock paths remain protected by path/identity even if their contents change.

At preflight and inside final transaction publication, the guard revalidates
handle provenance/context, the original vault snapshot/revision/ACL, lock-file
path/identity/ACL/empty size, output path and existing output magic. Lock metadata
is queried through a compatible native handle; the locked byte-zero region is
never read. Security inspection does not release or replace the actual lock owner.

The last guard executes **inside `SigningTransaction.publish()`**, after actual
candidate verification and working-file cleanup, before the existing final
parent/destination/candidate checks and sole `os.replace()`. Tests modifying
the vault or invalidating the handle at transaction entry reject; a check only
before calling `publish()` was insufficient and was moved into that boundary.

All inherited signing steps remain:

1. Capture the source once; use only those bytes for unsigned-input preflight
   and both signature messages.
2. Revalidate the recovered original in-memory pair, without private-key files.
3. Use the same Ed25519 first-revision message and subsequent Falcon-512 SHAKE256
   construction, with the complete Ed25519 container included.
4. Use the same owned PDF stages and exclusive destination-directory candidate,
   preserving container capacities, lengths, ByteRanges and strict padding/pair
   validation.
5. Flush, fsync and close the candidate. Verify that actual staged file using
   captured public bytes and require literal `result[0] is True`.
6. Clean working files, apply protected-path/state checks and atomically replace
   the PDF destination once. There is no private/public key-file export on this
   memory-signing route.

Prepublication failures preserve an existing PDF destination and never rewrite
the active encrypted vault or lock file. Ordinary errors clean owned PDF stages
and candidates when the OS permits. Denied cleanup retains a sanitized note;
it must not imply that leftover PDF artifacts are encrypted. No unowned object
is deleted to recover from a path change. Native lock-release errors after commit
report that publication may have completed; no rollback or absent-output promise
is made. Callers must inspect the destination before retrying in that case.

## Local CLI/test harness

Run in an interactive local Windows terminal:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m vault_signing_cli
```

It requests the vault path, prompts for the password, unlocks, requests unsigned
PDF and output paths, calls the controlled signer, verifies the completed file
with the recovered public keys, and locks the handle before printing success.
The signer already authenticated the staged candidate before publication; the
CLI's subsequent check is an additional observation, not a rollback transaction.
An external alteration/read failure after commit suppresses CLI success and asks
the user to inspect the destination rather than deleting or restoring it.

Only `--help`/`-h` are accepted as arguments. Other argument values are not echoed
or processed. There is no password flag, environment-variable credential source,
private-key export or key-generation fallback. Paths use ordinary prompts;
password input uses the standard library's
[getpass](https://docs.python.org/3.11/library/getpass.html) with no echo.
Noninteractive stdin rejects before password entry, and `GetPassWarning` is
promoted to an error so the library cannot fall back to potentially echoed input.
The local password reference is dropped after unlock; this is not secure erasure.

All failures use fixed feedback without native exception text, passwords,
private material or traceback locals. Cleanup notes trigger a generic manual-review
message. Input, signing, final verification and even success-message failures
still close managed access. No GUI, browser, PDF rendering or complete PDF syntax/
active-content validation is introduced; inherited unsigned-marker validation
and strict custom-signature parsing remain the document-policy boundary.

## Regression evidence

Tests were written before production changes. The initial red run stopped after
two expected missing-module setup errors. Initial integration/CLI coverage passed
146 cases. Further tests preceded the final publication-hook placement and
preservation of sanitized cleanup diagnostics. All pre-existing tests are unchanged.
Final coverage adds **167 passing cases**.

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

| Run | Passed | Failed/errors | Skipped | Xfailed | Xpassed | pytest time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Clean Phase 3.2B.2 baseline | 1274 | 0 | 8 | 0 | 0 | 48.24 s |
| Complete final suite | **1441** | **0** | **8** | **0** | **0** | **64.47 s** |

The eight skips are unchanged at `tests/test_signing_io.py:22`: native Windows
file-symlink creation requires Developer Mode or symlink privilege. No new skip,
xfail or xpass exists and no elevation/environment change was attempted.

End-to-end evidence includes:

- One creator process generates the pair in RAM and publishes the encrypted
  vault, returning only public keys/ID. That process exits. A separate process
  unlocks the vault, signs each tiny valid PDF fixture and verifies using those
  original public keys, then locks the handle. No private keys cross the process
  test boundary. Disposable password controls use stdin memory, not argv/env/logs;
  this API test is separate from the CLI's required interactive terminal mode.
- A spy requires the existing memory signer to receive the **same recovered pair
  object**, and independent native verification checks both Ed25519 and Falcon
  against the original public keys and explicit selected-message construction.
- Content mutations, appended bytes, truncation, padding and ByteRange changes
  reject. Both frozen Phase 1 signatures remain valid. Managed custom capacities
  `(64, 752)`, `(80, 1024)`, `(128, 2048)` and `(256, 4096)` sign and verify.
- Exact/relative/case aliases and actual hard links to both the active vault
  and lock file reject. Actual native output-parent junction aliases reject.
  Recognizable backups with unusual extensions and reserved storage names reject.
  Changes after candidate verification and at transaction publication entry are
  detected; original vault/external writer bytes are preserved.
- Native Windows integration launches another process during actual PDF
  replacement; it cannot acquire the vault lock. Cooperating password changes
  also fail during signing, and locks can be acquired afterward. A worker that
  unlocks its own context signs successfully; transferring another thread's
  handle rejects. Process/context rejection branches are also explicitly tested.
- The lock-file ACL guard is fault-injected specifically after successful
  candidate verification, proving that inspection repeats before publication.
  Actual Windows ACL enforcement/broadening tests from Phase 3.2B.2 still run;
  the injected late-check test is not claimed as an independent native ACL attack.
- Both algorithm failures, stage/partial candidate writes, fsync, verifier false/
  exceptions, replacement failure, stale vaults and invalid handle states preserve
  destinations and release locks. Cleanup-denial and post-commit close failures
  have explicit retained-artifact/possible-commit assertions.
- Write instrumentation covers Python path and descriptor writes. PDF stages
  contain no raw/hex private seed, Falcon secret or vault password. No key files
  are created and normal operations log no values. Source snapshot consistency
  is tested through mutation of the live unsigned source after capture.
- CLI tests use prompt doubles with actual vault/sign/verify operations and
  assert final handle locking, generic errors and no secret output. Separate
  tests check `getpass` usage, no-echo fallback refusal, argument rejection and
  native noninteractive process refusal. `--help` was also executed successfully.

Boundary/fault tests use isolated password/salt-dependent KDF doubles to reduce
cost, with actual AESGCM, hybrid self-tests, PDF cryptography and Windows I/O.
Real-profile round trips, custom capacities, creator/reopener process tests and
CLI integration remain separate. Production Argon2id parameters are unchanged;
no cheaper profile or fixed-randomness production API was added.

AST comparisons confirm `sign_file()` and the entire shared `_sign_captured()`
function, including its signature, are identical to the committed baseline.
`capture_source()` and `validate_signing_paths()` are also AST-identical.
All **15** original dataset hashes match the Phase 1 snapshot in a read-only
audit of `D:\Final_Thesis`.

## Windows limitations and residual risks

- Vault storage and managed outputs retain the fixed-local-Windows-NTFS policy.
  Broader/foreign ACLs, unsupported volumes, reparse parents and multi-link
  storage reject. No ACL/locking bypass, cross-device permission migration or
  new file-permission architecture is introduced. Native tests run on the existing
  Windows x64/Python 3.11.9 environment with cryptography 50.0.2, PyNaCl 1.6.2,
  pqcrypto 0.3.4 and pytest 9.2.0.
- Automated CLI tests do not constitute manual observation of echo behavior in
  every real IDE/terminal or packaged desktop. An actual interactive terminal is
  required; redirected stdin and unsuitable IDE consoles fail closed. No browser
  or pywebview validation is claimed.
- Handle context checks and a weak registry are ordinary process safeguards.
  Private values remain available through the existing memory APIs; malicious
  Python, debuggers, malware, administrators, paging or crash dumps can expose
  them. Locking cannot erase copies or revoke previously obtained references.
- Cooperative locking is not a hostile-filesystem transaction. Snapshot/hash/
  identity/ACL rechecks reduce observed races, but cannot provide atomic CAS
  against a noncooperator racing the final checks/rename. Different vaults do not
  share a global PDF-output lock; original destination-race limits remain.
  Protected parent-directory provisioning remains outside this phase.
- Atomic replacement is not guaranteed power-loss durability. Process/native
  crashes or persistent sharing/permission denial can leave owned PDF artifacts
  and empty persistent sidecars. There is no automatic scavenger or rollback
  after successful commit, and temporary PDFs may contain sensitive document data.
- The standalone memory/path signers remain available for legacy use; they cannot
  infer vault provenance. Callers requiring managed storage/context guarantees
  must use `sign_vault_document()`. The Streamlit legacy private-upload workflow
  remains unchanged and is not made vault-based by this integration.
- Public tuple IDs and successful verification do not establish trusted signer
  identity, account ownership, enrollment, expiration or revocation. Offline vault
  password guessing, rollback, whole-vault substitution and recovery limits remain.
  No FIPS, CMS, PAdES or production-security compliance is claimed.
