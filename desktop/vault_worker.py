"""Fixed native-only vault commands, sharing the existing worker owner/queue."""
from dataclasses import dataclass, field

from .worker import Command, Worker, WorkerError


@dataclass(repr=False)
class VaultInput:
    path: object = field(default=None, repr=False)
    password: str | None = field(default=None, repr=False)
    vault_id: str | None = None
    session_id: str | None = None
    selection_id: str | None = None

    def clear(self):
        self.path = self.password = None  # Reference release, not secure erasure.


class VaultWorker(Worker):
    def __init__(self, capacity=8):
        super().__init__(capacity)
        self._vaults = None

    def vault_request(self, command, payload=None, *, timeout=5.0):
        if type(command) is not Command or command not in (
                Command.VAULT_STATE, Command.VAULT_CREATE, Command.VAULT_UNLOCK, Command.VAULT_LOCK,
                Command.VAULT_SELECT, Command.VAULT_RETRY_CHECK, Command.VAULT_FORGET_SELECTION):
            raise WorkerError("INVALID_REQUEST")
        if payload is not None and type(payload) is not VaultInput:
            raise WorkerError("INVALID_REQUEST")
        try:
            return self._request(command, timeout=timeout, payload=payload)
        except WorkerError as error:
            # A running request owns its payload until it has finished. Clearing
            # it from a caller thread could race a KDF; _discard handles that case.
            if error.code != "TIMEOUT" and payload is not None:
                payload.clear()
            raise

    def _dispatch(self, request, sequence):
        if request.command is Command.STATUS:
            return super()._dispatch(request, sequence)
        from .vault_service import VaultService
        from vault_format import VaultError
        if self._vaults is None:
            self._vaults = VaultService()
        def cancelled():
            return request.cancelled.is_set() or self._stop.is_set()
        try:
            if cancelled():
                raise WorkerError("UNAVAILABLE")
            return self._vaults.execute(request.command, request.payload, cancelled)
        except VaultError as error:
            raise WorkerError(error.code) from None

    def _discard(self, request):
        if type(request.payload) is VaultInput:
            request.payload.clear()
        if request.cancelled.is_set() and request.command is Command.VAULT_UNLOCK and self._vaults is not None:
            try:
                self._vaults.lock_active()
            except Exception:
                self._cleanup_failed = True
                self._stop.set()

    def _finalize(self):
        if self._vaults is not None:
            try:
                self._vaults.close()
            finally:
                self._vaults = None
