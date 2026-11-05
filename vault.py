"""Managed local encrypted vault lifecycle; no PDF signing/UI integration."""

from functools import wraps
import hmac
from threading import RLock

from hybrid_keys import HybridKeyPair
from vault_crypto import UnsealedVault, seal_key_pair, unseal_key_pair, _reseal_key_pair
from vault_format import VaultError, parse_vault
from vault_io import (
    VaultConflictError, VaultExistsError, VaultIOError, VaultPathError,
    VaultPermissionError, VaultTransaction, VaultVerificationError, capture_vault, check_path,
    cooperative_locks, recheck_snapshot, require_absent,
)


class VaultLockedError(VaultError):
    code = "vault.locked"
    message = "Managed vault handle is locked"


def _operation(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except VaultError:
            raise
        except Exception as error:
            kind = (VaultExistsError if isinstance(error, FileExistsError) else
                    VaultPermissionError if isinstance(error, PermissionError) else VaultIOError)
            safe = kind()
            # Preserve only fixed cleanup diagnostics, never native values/text.
            for note in getattr(error, "__notes__", ()):
                if "cleanup" in note.lower():
                    safe.add_note("Vault artifact cleanup failed; encrypted artifact may remain")
                elif "lock release" in note.lower():
                    safe.add_note("Vault lock release failed")
            raise safe from None
    return guarded


class UnlockedVault:
    """Revocable managed access, not secure erasure or revocation of copied bytes."""

    __slots__ = ("_result", "_mutex", "_path", "_revision")

    def __init__(self, result, snapshot):
        self._result = result
        self._mutex = RLock()
        self._path = snapshot.path
        self._revision = snapshot.revision

    @property
    def is_locked(self):
        with self._mutex:
            return self._result is None

    @property
    def path(self):
        return self._path

    @property
    def revision(self):
        return self._revision

    @property
    def key_pair(self):
        with self._mutex:
            if self._result is None:
                raise VaultLockedError()
            return self._result.key_pair

    @property
    def metadata(self):
        with self._mutex:
            if self._result is None:
                raise VaultLockedError()
            return self._result.metadata

    def __enter__(self):
        with self._mutex:
            if self._result is None:
                raise VaultLockedError()
        return self

    def __exit__(self, *args):
        lock_vault(self)
        return False

    def __repr__(self):
        return f"UnlockedVault(locked={self.is_locked})"


def _same_recovery(actual, pair, expected_uuid):
    return (type(actual) is UnsealedVault
            and type(actual.key_pair) is HybridKeyPair
            and actual.key_pair.public_keys == pair.public_keys
            and actual.key_pair.key_id == pair.key_id
            and hmac.compare_digest(actual.key_pair.ed25519_private_seed, pair.ed25519_private_seed)
            and hmac.compare_digest(actual.key_pair.falcon_private_key, pair.falcon_private_key)
            and actual.metadata.vault_uuid == expected_uuid)


def _publish(destination, encrypted, password, pair, metadata, *, previous=None, protected=()):
    def validate(data):
        actual = unseal_key_pair(data, password)
        return (_same_recovery(actual, pair, metadata.vault_uuid) is True
                and actual.metadata == metadata)

    with VaultTransaction(destination, previous=previous, protected=protected) as transaction:
        transaction.write_candidate(encrypted)
        transaction.verify(validate)
        transaction.publish()
    return metadata


@_operation
def create_vault(path, pair: HybridKeyPair, password: str):
    """Create only; the caller explicitly supplies already generated in-memory keys."""
    with cooperative_locks([path]) as (destination,):
        require_absent(destination)
        encrypted = seal_key_pair(pair, password)
        metadata = parse_vault(encrypted).metadata
        return _publish(destination, encrypted, password, pair, metadata)


@_operation
def unlock_vault(path, password: str) -> UnlockedVault:
    with cooperative_locks([path]) as (source,):
        captured = capture_vault(source)
        result = unseal_key_pair(captured.data, password)
        # Recheck after potentially expensive KDF/native validation.
        recheck_snapshot(captured)
        return UnlockedVault(result, captured)


def lock_vault(handle: UnlockedVault) -> None:
    if type(handle) is not UnlockedVault:
        raise VaultLockedError()
    with handle._mutex:
        handle._result = None


@_operation
def change_vault_password(path, old_password: str, new_password: str, *, expected_revision=None):
    """Authenticate and replace under a cooperative lock; preserve UUID and keys."""
    with cooperative_locks([path]) as (destination,):
        captured = capture_vault(destination)
        if expected_revision is not None and (
                type(expected_revision) is not str or expected_revision != captured.revision):
            raise VaultConflictError()
        original = unseal_key_pair(captured.data, old_password)
        encrypted = _reseal_key_pair(original.key_pair, new_password, original.metadata.vault_uuid)
        metadata = parse_vault(encrypted).metadata
        if (metadata.vault_uuid != original.metadata.vault_uuid
                or metadata.public_keys != original.metadata.public_keys
                or metadata.key_id != original.metadata.key_id
                or metadata.salt == original.metadata.salt
                or metadata.nonce == original.metadata.nonce):
            raise VaultVerificationError()
        return _publish(destination, encrypted, new_password, original.key_pair, metadata, previous=captured)


def _copy_encrypted(source_path, destination_path, password):
    source, destination = check_path(source_path), check_path(destination_path)
    if source.path == destination.path:
        raise VaultPathError()
    with cooperative_locks([source, destination]) as (source, destination):
        require_absent(destination)
        captured = capture_vault(source)
        original = unseal_key_pair(captured.data, password)
        return _publish(destination, captured.data, password, original.key_pair,
                        original.metadata, protected=(captured,))


@_operation
def export_encrypted_backup(vault_path, backup_path, password: str):
    """Authenticate then create an independent, byte-identical encrypted backup."""
    return _copy_encrypted(vault_path, backup_path, password)


@_operation
def import_encrypted_backup(backup_path, vault_path, password: str):
    """Authenticate then restore to an absent path; never replace existing keys."""
    return _copy_encrypted(backup_path, vault_path, password)
