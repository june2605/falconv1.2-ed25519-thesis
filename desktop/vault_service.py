"""Worker-private selection/managed handle. No GUI, logging or secret export."""
from copy import deepcopy
import hmac
from pathlib import Path
import secrets
from threading import current_thread

from keygen import generate_hybrid_key_pair
from vault import create_vault, unlock_vault, lock_vault, _managed_key_access
from vault_crypto import _encode_password
from vault_io import (check_path, require_absent, cooperative_locks, recheck_snapshot,
                      capture_vault, VaultConflictError)

from .worker import Command, WorkerError


class VaultService:
    def __init__(self):
        self._owner = current_thread()
        self._handle = None
        self._public = None
        self._pending = None  # Encrypted snapshot only; never authenticated metadata.
        self._selection_id = None

    def _check_owner(self):
        if current_thread() is not self._owner:
            raise WorkerError("UNAVAILABLE")

    def require_session(self, vault_id, session_id):
        self._check_owner()
        if (self._handle is None or self._public is None
                or self._public['vaultId'] != vault_id or self._public['sessionId'] != session_id):
            raise WorkerError('STALE_SESSION')
        self.state()  # Provenance, ACL, revision and cooperative locking checks.
        return self._handle  # Private Python caller on the same owner only.

    def _select(self, path, metadata, handle=None):
        public = metadata.public_keys
        self._public = {"vaultId": secrets.token_hex(16),
                        "sessionId": secrets.token_hex(16) if handle is not None else None,
                        "displayName": Path(path).stem[:80],
                        "state": "unlocked" if handle is not None else "locked",
                        "hybridKeyId": metadata.key_id,
                        "ed25519PublicKey": public.ed25519_public_key.hex(),
                        "falconPublicKey": public.falcon_public_key.hex(),
                        "formatVersion": metadata.format_version,
                        "algorithms": {"ed25519": "Ed25519", "falcon512": "Falcon-512"}}
        self._handle = handle

    def state(self):
        self._check_owner()
        if self._handle is not None:
            try:
                with _managed_key_access(self._handle) as (binding, _):
                    with cooperative_locks([binding.snapshot.checked]):
                        recheck_snapshot(binding.snapshot)
            except Exception:
                self.lock_active()
                raise
        return {"vault": deepcopy(self._public), "cancelled": False,
                "selectionId": self._selection_id}

    def _forget_selection(self):
        self._pending = self._selection_id = None

    def _checked_selection(self, selection_id):
        if (self._pending is None or type(selection_id) is not str
                or not hmac.compare_digest(selection_id, self._selection_id)):
            raise WorkerError("STALE_SELECTION")
        try:
            with cooperative_locks([self._pending.checked]):
                recheck_snapshot(self._pending)
            return self._pending
        except Exception:
            self._forget_selection()
            raise

    def lock_active(self):
        self._check_owner()
        self._forget_selection()
        handle, self._handle = self._handle, None
        try:
            if handle is not None:
                lock_vault(handle)
        finally:
            if self._public is not None:
                self._public["state"], self._public["sessionId"] = "locked", None

    def close(self):
        try:
            self.lock_active()
        finally:
            self._public = None

    def execute(self, command, value, cancelled):
        self._check_owner()
        if command is Command.VAULT_STATE:
            return self.state()
        if command is Command.VAULT_FORGET_SELECTION:
            self._forget_selection()
            return self.state()
        if command is Command.VAULT_LOCK:
            if (value is None or self._handle is None or self._public is None
                    or not hmac.compare_digest(value.vault_id or "", self._public["vaultId"])
                    or not hmac.compare_digest(value.session_id or "", self._public["sessionId"])):
                raise WorkerError("STALE_SESSION")
            self.lock_active()
            return self.state()
        if self._handle is not None:
            raise WorkerError("VAULT_ACTIVE")
        if command is Command.VAULT_SELECT:
            self._forget_selection()
            if value is None or value.path is None:
                raise WorkerError("INVALID_REQUEST")
            with cooperative_locks([value.path]) as (source,):
                self._pending = capture_vault(source)
                self._selection_id = secrets.token_hex(16)
            return self.state()
        if command is Command.VAULT_RETRY_CHECK:
            self._checked_selection(value.selection_id if value else None)
            return self.state()
        if value is None or type(value.password) is not str:
            raise WorkerError("INVALID_REQUEST")
        creating = command is Command.VAULT_CREATE
        if not creating and command is not Command.VAULT_UNLOCK:
            raise WorkerError("INVALID_REQUEST")
        _encode_password(value.password, creating=creating)
        selected = self._checked_selection(value.selection_id) if value.selection_id is not None else None
        path = selected.checked if selected is not None else check_path(value.path)
        if creating:
            self._forget_selection()
            require_absent(path)  # Reject existing files before key generation.
            pair = generate_hybrid_key_pair()  # Once, no retry/regeneration.
            if cancelled():
                raise WorkerError("UNAVAILABLE")
            metadata = create_vault(path, pair, value.password)
            pair = None
            if cancelled():
                raise WorkerError("TIMEOUT")  # Publication may already have completed.
            self._select(path.path, metadata)
        else:
            handle = unlock_vault(path, value.password)
            try:
                if cancelled():
                    raise WorkerError("UNAVAILABLE")
                if selected is not None:
                    # The authenticated handle must describe the selected file,
                    # not a different revision observed between the two checks.
                    with _managed_key_access(handle) as (binding, _):
                        if (binding.snapshot.fingerprint != selected.fingerprint
                                or binding.snapshot.revision != selected.revision):
                            raise VaultConflictError()
                        with cooperative_locks([selected.checked]):
                            recheck_snapshot(selected)
                self._forget_selection()
                self._select(path.path, handle.metadata, handle)
            except BaseException:
                lock_vault(handle)
                raise
        return self.state()
