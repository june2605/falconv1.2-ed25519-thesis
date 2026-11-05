# Phase 3.2B.2: encrypted vault persistence and lifecycle

Implemented in `D:\Final_Thesis_GitHub`, on `thesis/development`, from
`7f6d19f34ec28aea6c18b6c8221737f43977c3e1`. Repository, branch, commit and clean
working tree were verified before changes. Used the existing Python 3.11.9 AMD64
environment without installing dependencies, committing or pushing.

## Scope and changed files

| File | Change |
| --- | --- |
| `vault_io.py` | New Windows/NTFS path policy, native protected-DACL creation and inspection, bounded snapshots, cooperative locks, revision guards, owned encrypted candidates and atomic publication. |
| `vault.py` | New managed handle and six public lifecycle operations; authenticate actual staged bytes and compare exact recovered material before publication. |
| `vault_crypto.py` | Extract the existing sealing body into one shared private helper and add `_reseal_key_pair()` for UUID preservation. Existing public signatures and cryptographic operations are retained. |
| `tests/test_vault_lifecycle.py` | Real-profile create/reopen/password-change/backup/restore, exact material recovery, wrong-password/tamper rejection, lock invalidation and destination preservation. |
| `tests/test_vault_io.py` | Native Windows ACL, hard-link, junction, sharing and process-lock tests; path/fault/race/cleanup/verification/revision tests and encrypted-only write instrumentation. |
| `docs/phase3-2b2-regression.md` | This API, filesystem policy, runtime, regression and risk record. |

`vault_format.py`, every pre-existing test/fixture/document, dependency declarations,
PDF algorithms/messages, signer/verifier, UI and demo are unchanged. No original
benchmark data was modified. No vault-based PDF signing or external architecture
was introduced.

## Public API

```python
from keygen import generate_hybrid_key_pair
from vault import (
    create_vault, unlock_vault, lock_vault, change_vault_password,
    export_encrypted_backup, import_encrypted_backup,
)

pair = generate_hybrid_key_pair()                  # in memory
metadata = create_vault(path, pair, password)       # destination must be absent
with unlock_vault(path, password) as unlocked:
    assert unlocked.key_pair == pair
    revision = unlocked.revision                  # SHA-256 of encrypted file bytes
    assert unlocked.metadata == metadata
# Context exit calls lock_vault(), including on ordinary caller exceptions.

metadata = change_vault_password(path, password, new_password,
                                 expected_revision=revision)
export_encrypted_backup(path, backup_path, new_password)
import_encrypted_backup(backup_path, restored_path, new_password)
```

| Operation | Arguments | Result / behavior |
| --- | --- | --- |
| `create_vault` | `(path, pair, password)` | `VaultMetadata`; explicitly supplied in-memory pair, create-only publication |
| `unlock_vault` | `(path, password)` | `UnlockedVault`; bounded capture, authentication, correspondence self-tests and post-KDF revision recheck |
| `lock_vault` | `(handle)` | `None`; idempotently invalidate managed access and drop its result reference |
| `change_vault_password` | `(path, old_password, new_password, *, expected_revision=None)` | `VaultMetadata`; authenticate original, reseal under new password and atomically replace the unchanged captured revision |
| `export_encrypted_backup` | `(vault_path, backup_path, password)` | `VaultMetadata`; authenticate, create an independent byte-identical encrypted backup and verify the staged copy |
| `import_encrypted_backup` | `(backup_path, vault_path, password)` | `VaultMetadata`; authenticate and restore an independent encrypted copy to an absent destination |

No operation discovers keys or generates replacement keys. Creation requires the
caller to supply a pair. Failed unlock/import never calls the key generator.
Export/import copy existing authenticated ciphertext, rather than encrypting
again with an existing nonce/key. Their source and destination are separate files,
never hard links. Existing destinations always reject, including a vault, backup
or unrelated file already occupying the requested name.

`UnlockedVault` uses slots and an in-process `RLock`. `key_pair`, `metadata` and
context entry reject with `VaultLockedError` after locking. `is_locked`, `path`
and `revision` remain available as non-secret state. The representation reports
only locked status. The handle retains no password. Locking drops its managed
reference, but cannot revoke key references already obtained by a caller, erase
Python/native memory, prevent direct access to Python internals, or automatically
invalidate other handles/processes. No signing method is added to the handle.

## Format and password-change compatibility

The encrypted wire format remains exactly the approved **2416-byte v1** format:
1069-byte original header, 1331-byte ciphertext and full 16-byte tag. Algorithm
IDs, key encodings, public ID, Argon2id v19 profile (65536 KiB / 3 / 4 / 32 bytes),
AES-256-GCM, strict UTF-8 and password limits are unchanged.

Public `seal_key_pair(pair, password)` remains a two-argument in-memory API that
creates a fresh UUID. `_reseal_key_pair(pair, password, vault_uuid)` is a private
lifecycle helper sharing the same sealing body; it provides no salt/nonce or
cost injection. Password changes preserve the authenticated original UUID,
public keys, hybrid ID and exact seed/Falcon-secret bytes, with fresh salt and
nonce. The lifecycle layer rejects a changed UUID/public tuple or repeated salt
or nonce before staging. It then verifies exact recovery from the actual candidate.
The new password must satisfy the existing creation policy; the old password
uses the existing unlock policy. Re-entering the same password still reseals;
old-password rejection applies when a different new password is selected.

Backups retain the source's password and UUID. Changing the live vault password
does not change or invalidate existing backups, copies or already-unlocked keys.
This is password re-encryption, not signing-key rotation or revocation.

## File ownership, permissions and supported paths

This adapter supports **fixed local Windows NTFS volumes with persistent ACLs**.
Other platforms, network/mapped-remote/removable volumes, FAT/exFAT/ReFS and
unsupported namespace/path types fail closed. This is a conservative initial
profile, not a claim that those other filesystems cannot support secure storage.
No POSIX permission emulation or broad-ACL fallback is used.

Creation uses native [CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
(`CREATE_NEW`) with a non-inheritable handle and
an explicit security descriptor in `SECURITY_ATTRIBUTES`, **before any bytes are
written**. The protected DACL has exactly two explicit allow entries: the current
process user's SID and LocalSystem (`S-1-5-18`), both `FILE_ALL_ACCESS`. Owner must
be the current user. Inherited ACEs, extra trustees, unknown ACE types/flags,
different rights, missing/unprotected/null DACLs and security-query failures
reject. There is no create-then-chmod/ACL window or automatic permission repair.
Administrators are not explicitly granted an ACE; administrative/kernel powers
and same-user malware remain outside this protection.

Handle-based `GetSecurityInfo()` validates the actual descriptor on created and
reopened candidate/vault/backup/lock files. Native file information checks disk
file type, reparse/directory attributes and a single hard link. Only owner/DACL
security information is requested, not audit/SACL privileges. Existing encrypted
input files must meet this same restrictive policy, not just contain valid bytes.

Paths reject devices, UNC/device namespaces, drive-relative names, alternate
streams, wildcard/control characters, reserved names, trailing spaces/dots,
directories and all observed reparse/symlink components. Every existing ancestor
is inspected, including junctions. Relative paths are canonicalized, with original
names and parent identities retained for rechecking. Existing files with link
count other than one reject; password changes cannot leave an old hard-link alias.
The internal `.hybrid-vault-` basename prefix is reserved to keep user destinations
disjoint from lock and random candidate names. No missing parent directories are
created implicitly.

**Filesystem compatibility limitation:** manually saved codec bytes, backups
copied with inherited/broader ACLs, files owned by another Windows SID, USB media
and network shares may be rejected even though the in-memory v1 codec can decrypt
their contents. There is no automatic ACL migration or cross-device permission
repair in this phase. Restoring under a different account/device requires a
separately reviewed permission/import workflow; do not interpret codec portability
as implemented filesystem portability.

## Snapshot, publication and recovery

1. Validate paths and volume; acquire ordered cooperative locks for every source
   and destination. Reject existing create-only destinations before encryption.
2. Capture an existing source using a read-only native handle denying writer and
   delete sharing. Check regular type/link count/security, require 2416 bytes,
   read at most 2417, compare before/after metadata and current path identity,
   and validate public format before KDF work. Retain immutable encrypted bytes,
   SHA-256 revision, identity and timestamp/size fingerprint.
3. Authenticate the captured source when applicable. Seal/reseal entirely in RAM;
   only encrypted bytes can reach candidate writing. No private/password/derived-key
   file or plaintext temporary payload is created.
4. Exclusively create a random candidate beside the destination using the strict
   native descriptor. Check its actual ACL before its first write. Record ownership
   immediately; if identity lookup or CRT-handle conversion fails, delete by the
   still-owned exclusive raw handle and close it.
5. Reject short writes; flush, `os.fsync()` and close the candidate. Reopen that
   actual file, revalidate security/identity/format, and call the existing unsealer
   on those bytes. Require a literal boolean `True` from the recovery comparison:
   both exact private values, both public keys, original ID, UUID and expected
   metadata must match. Truthy tuples and abnormal verifier results cannot publish.
6. Recheck original paths and ancestor identities, protected source revisions,
   original destination identity/revision or required absence, and candidate
   fingerprint/hash after verification. Permission or verification uncertainty
   rejects. `expected_revision`, when supplied for password change, must match
   the captured encrypted revision before decryption too.
7. Invoke [MoveFileExW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw)
   once within the destination directory, with flags zero
   for create-only operations, or only `MOVEFILE_REPLACE_EXISTING` for password
   changes. No `COPY_ALLOWED`, copy/delete fallback, destination truncation,
   destination unlink or backup/rollback rewrite is used. Native create-only
   publication still rejects a destination appearing after the final absence check.
8. Release lock handles. No candidate cleanup is needed after successful rename.

Same-volume NTFS rename provides the intended completed-file publication boundary
for ordinary operation. Candidate fsync is **not** a guarantee of directory-entry
durability, crash/power-loss recovery, storage-controller behavior or remote
completion semantics. No power-loss durability claim or directory-fsync guarantee
is made, and remote filesystems are outside the supported profile.

| Failure | Recovery / visible state |
| --- | --- |
| Wrong password, malformed/tampered bytes, missing source | No generated/replacement keys or new vault; source preserved |
| Existing destination or input/output alias | Existing vault/backup/unrelated destination preserved |
| ACL/permission/sharing/type failure | Fail closed; no permission downgrade or elevated retry |
| Create/identity/fd-conversion/write/flush/fsync/close failure | Previous vault preserved; attempt owned candidate cleanup with closed handles |
| Candidate authentication/recovery/revision failure | No publication; preserve original/protected files |
| Native rename failure or last-moment create-only collision | Previous/external destination preserved; remove owned candidate when permitted |
| Concurrent observed source/destination/path/candidate change | Reject; do not overwrite the external writer's data |
| Cleanup denied | Preserve the primary sanitized error and add a fixed cleanup note; encrypted/empty owned artifact may remain |
| Candidate pathname replaced by an unowned object | Refuse deletion; retain a cleanup diagnostic, never delete the unowned replacement |
| Lock release error after publication | Report that publication may have completed; inspect/reopen before retrying, with no rollback claim |
| Abrupt termination/native crash/power loss | Cleanup may not run; encrypted partial candidates/empty lock files can remain; no automatic scavenger or rollback |

Cleanup operates only on recorded owned candidates. It opens a non-following,
exclusive delete-capable handle, checks actual file identity/security and marks
that handle for deletion. It does not recursively delete directories, glob/remove
temporary-looking user files, or delete source/backup/destination files. Native
permission/sharing denial cannot be overridden; retained encrypted artifacts need
explicit operator handling rather than a risky directory-wide cleanup.

## Concurrency and error boundaries

Each canonical target has a deterministic empty `.hybrid-vault-lock-<hash>.lck`
sidecar with the same restrictive ACL.
[LockFileEx](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-lockfileex)
locks byte zero exclusively
with `LOCKFILE_FAIL_IMMEDIATELY`. Ordered acquisition supports source/destination
operations without waiting indefinitely. Native handles are not inheritable and
deny delete sharing for sidecars. Closing handles releases locks after ordinary
errors or process exit.

Lock files are **persistent coordination objects**, not leaked temporary vaults.
They are never automatically unlinked, avoiding deletion/recreation of a lock
inode while another process holds it. Unexpected existing sidecar ACLs, types,
hard links, reparse attributes or nonzero contents reject without alteration.

Locks coordinate only clients using these functions and canonical path policy.
An unlocked handle holds no lifetime file lock. Revision hashes/fingerprints detect
observed conflicts, not atomic compare-and-swap against a hostile noncooperator.
An attacker able to change directories/ACLs or write as the same user can still
race the final check/rename, substitute complete vaults, deny service or roll back
old ciphertext. Parent-directory ACL hardening/provisioning is not implemented;
use trusted directories. The hash is not an authenticated persistent revision
ledger or a cross-device rollback detector.

Existing codec errors remain unchanged. Added sanitized `VaultError` categories:

| Class | Code |
| --- | --- |
| `VaultIOError` | `vault.io` |
| `VaultPathError` | `vault.path` |
| `VaultSecurityError` | `vault.security` |
| `VaultExistsError` | `vault.exists` |
| `VaultPermissionError` | `vault.permission` |
| `VaultLockError` | `vault.file_locked` |
| `VaultConflictError` | `vault.conflict` |
| `VaultVerificationError` | `vault.verification` |
| `VaultLockedError` (managed handle) | `vault.locked` |

Public lifecycle boundaries suppress displayed native exception context and
replace unexpected ordinary exceptions with fixed messages; they do not echo
paths, passwords, native diagnostics or key bytes. Fixed cleanup/lock notes are
preserved. Callers should display those notes and must not log traceback locals
or suppressed exception contexts, which Python can retain. KeyboardInterrupt/
SystemExit are not converted to ordinary errors; context cleanup still attempts
to run. OS/native process termination cannot guarantee cleanup.

## Test-first development and execution

Tests preceded production modules: the initial red run stopped after two expected
`ModuleNotFoundError` setup errors for the absent `vault` module. The first
implementation passed 96 cases. Further test-first cases exposed and resolved
raw-handle setup cleanup, security-category remapping, UUID/randomness invariant
checking and unexpected-verifier exception sanitization. No pre-existing test was
edited or weakened. The final phase adds **129 passing cases**.

Command:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

| Run | Passed | Failed/errors | Skipped | Xfailed | Xpassed | pytest time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Clean committed baseline | 1145 | 0 | 8 | 0 | 0 | 38.33 s |
| Final complete suite | **1274** | **0** | **8** | **0** | **0** | **47.86 s** |

All eight skips remain at `tests/test_signing_io.py:22`: native Windows file-symlink
tests require Developer Mode or symlink privilege. No new skip, xfail or xpass is
introduced. No elevation/environment changes were attempted.

Native Windows integration evidence, distinct from mocks:

- Actual protected DACL/owner/rights are independently inspected by PowerShell
  `Get-Acl` after creation and password-change publication; the exact user/System
  entries, rights, protection and lack of inherited ACEs are asserted.
- Actual DACL broadening with the DACL-only Windows security API causes unlock,
  password change and export to reject. PowerShell `Set-Acl` requested unavailable
  `SeSecurityPrivilege` during test setup; no elevation/fallback was used. Native
  owner/DACL-only APIs require no SACL privilege and perform the final test.
- Actual hard-link aliases and actual directory junction/reparse parents reject.
  The file-reparse-attribute branch is separately simulated; that mock is not
  claimed as native file-symlink integration. The eight historical symlink skips
  still limit that coverage.
- Actual `LockFileEx` contention is checked in separate Python processes, including
  a real attempted password change while another process owns the lock. Subsequent
  acquisition succeeds after handle release. The sidecar remains empty/stable.
- A fresh Python process reopens the vault and compares both original private
  values and public ID. Disposable controls/passwords travel through stdin memory,
  never argv or a plaintext fixture/export file.
- Actual Windows open handles denying delete sharing block password-change rename,
  preserve the old bytes and permit owned-candidate cleanup after failure.
- Real-profile lifecycle tests recover identical keys, change passwords with
  preserved UUID/keys and fresh salt/nonce, reject old/wrong passwords/tampering,
  and export/restore independent encrypted copies.

Fault/path tests use real Windows files/ACL/rename handling but isolated test
doubles for injected failures. Many replace only the private KDF helper with a
password/salt-dependent public test derivation to reduce cost; real AESGCM and
native hybrid self-tests remain active. This does not add a production cheaper
profile or fixed-randomness API. Other tests deliberately inject writer, fsync,
close, native handle setup, verifier, ACL, cleanup and publication faults.

Coverage includes on-disk header/ciphertext/tag tampering, exact private/public
recovery, missing files, existing destinations, stale revisions,
source/candidate/destination mutation, last-moment native no-replace collisions,
nonboolean/abnormal verification, false key recovery, loss of UUID, salt/nonce
reuse, unowned replacement cleanup refusal and post-commit lock-close diagnostics.
Ordered instrumentation requires fsync, closed-handle reopen/authentication and
one publication. Encrypted-only write instrumentation spans all four writing
operations; no plaintext secret bytes/passwords appear in written artifacts.
Permanent-denial and hostile-retarget tests explicitly demonstrate retained
artifacts; pytest owns their disposable teardown.

## Environment, unchanged behavior and residual risks

Observed environment: CPython 3.11.9 AMD64, `cryptography==50.0.2`,
`PyNaCl==1.6.2`, `pqcrypto==0.3.4`, `pytest==9.2.0`. Native tests use the local
Windows pytest temporary filesystem on C:. Read-only volume probes also confirmed
C: and D: are fixed local NTFS with persistent ACL support. This is not validation
of all Windows versions, storage drivers or filesystem profiles. No dependencies
were installed and the environment is not claimed to be fully locked.

All **1145** previous passing cases remain green, including the frozen Phase 1
signatures, custom capacities, whole-pair/ByteRange/padding validation and atomic
PDF publication/failure tests. Existing `_load_backend`, `_encode_password`,
`_derive_key` and `unseal_key_pair` are AST-identical to the committed baseline.
The encoder/parser and both public PDF eleven-element contracts are unchanged.
All **15** original dataset hashes match `docs/phase1-baseline.json` in a read-only
audit of `D:\Final_Thesis`.

Application-created storage contains encrypted vault bytes and empty coordination
files only. Passwords, derived keys and plaintext private values still exist in
Python/native memory and may be retained by copies, tracebacks, OS paging, dumps
or compromised processes; guaranteed zeroization or exclusion from OS-managed
disk is not provided. Offline guessing, weak password choices, public-key/UUID
linkability, native crashes, privileged/same-user attackers, whole-vault
substitution and rollback remain security limits. No password/key recovery is
possible without usable password/key material or an independently usable backup.

Vault-based signing/UI integration remains Phase 3.2B.3. Cross-device permission
migration, directory provisioning, persistent revision/rollback ledgers, trusted
signer identity/enrollment, revocation/rotation, authentication, React/FastAPI/
databases and production deployment remain separate future work. No FIPS, CMS,
PAdES or production-security compliance is claimed.
