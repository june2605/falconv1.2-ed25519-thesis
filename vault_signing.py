"""Controlled bridge from authenticated managed vault handles to the PDF core.

Only PDF intermediates are staged by the inherited signer. Vault passwords,
derived keys and decrypted private material are never written or logged here.
This is process/thread-bound access control for ordinary callers, not memory
isolation, trusted signer identity or protection from a compromised process.
"""

import os

import sign
from signing_io import SigningPathError, SigningProtection, SourceSnapshot
from vault import _managed_key_access, _operation, _validate_managed_handle
from vault_io import (VaultConflictError, VaultPathError, _native, check_path,
                      cooperative_locks, lock_file_path, recheck_snapshot)


class _StorageGuard:
    def __init__(self, handle, binding, output_path):
        self.handle = handle
        self.binding = binding
        self.output = check_path(output_path)
        self.lock = check_path(lock_file_path(binding.snapshot.checked), internal=True)
        self.vault_file = SourceSnapshot(binding.snapshot.path, binding.snapshot.data,
                                         binding.snapshot.path.stat())
        self.lock_file = SourceSnapshot(self.lock.path, b"", self.lock.path.stat())
        self.paths = (self.vault_file, binding.snapshot.checked.original,
                      self.lock_file, self.lock.original)

    def check(self, output_path):
        _validate_managed_handle(self.handle, self.binding)
        recheck_snapshot(self.binding.snapshot)
        self.lock.recheck()
        # Reopen for metadata/security only, with sharing compatible with the
        # actual LockFileEx owner. Never read locked byte zero of the sidecar.
        native = _native()
        handle = native.open(self.lock.path, lock=True)
        try:
            info = native.info(handle)
            if (info.size_high or info.size_low
                    or not os.path.samestat(self.lock_file.stat_info, self.lock.path.stat())):
                raise VaultConflictError()
        finally:
            native.close(handle)
        self.output.recheck()
        if check_path(output_path).path != self.output.path:
            raise VaultPathError()
        # Protect other vaults/backups without a filename-discovery or key
        # registry scheme. The magic is conservatively reserved at byte zero,
        # including malformed/unsupported vaults, regardless of extension.
        try:
            with self.output.path.open("rb") as stream:
                prefix = stream.read(8)
        except FileNotFoundError:
            return
        if prefix == b"HYBKVLT\x00":
            raise VaultPathError()


@_operation
def sign_vault_document(handle, input_path, output_path):
    """Return the inherited 11-element signing tuple for one managed operation.

    Require unlock-issued, same-process/thread/module-context access and an
    unchanged original vault revision. Retain the handle mutex and vault's
    cooperative lock through final PDF publication, with repeated guards.
    This operation leaves the caller's handle open; use its context manager or
    lock_vault() to invalidate it afterward.
    """
    try:
        with _managed_key_access(handle) as (binding, pair):
            with cooperative_locks([binding.snapshot.checked]):
                recheck_snapshot(binding.snapshot)
                guard = _StorageGuard(handle, binding, output_path)
                protection = SigningProtection(guard.paths, guard.check)
                return sign.sign_with_key_material(input_path, output_path, pair,
                                                   _protection=protection)
    except SigningPathError as error:
        safe = VaultPathError()
        if any("cleanup" in note.lower() for note in getattr(error, "__notes__", ())):
            safe.add_note("Signing temporary-file cleanup failed; PDF artifacts may remain")
        raise safe from None
