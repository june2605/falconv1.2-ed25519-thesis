"""Six explicitly exposed methods. Paths/passwords originate in native UI only."""
import re
from copy import deepcopy
from threading import Event, Lock, RLock

from .bridge import DesktopBridge
from .contracts import VAULT_CAPABILITIES, failure, success
from .vault_worker import VaultInput
from .worker import Command, WorkerError


class VaultBridge(DesktopBridge):
    def __init__(self, worker, *, trusted, dialogs=None):
        super().__init__(worker, trusted=trusted)
        self._dialogs = dialogs
        self._operation = Lock()
        self._closed = Event()
        self._status_lock = RLock()
        self._status = {"vault": None, "cancelled": False, "selectionId": None, "operation": "idle"}

    def get_capabilities(self, *args, **kwargs):
        return self._reply(VAULT_CAPABILITIES, args, kwargs)

    def get_vault_state(self, *args, **kwargs):
        return self._vault_reply(Command.VAULT_STATE, args, kwargs)

    def create_vault(self, *args, **kwargs):
        return self._vault_reply(Command.VAULT_CREATE, args, kwargs)

    def unlock_vault(self, *args, **kwargs):
        return self._vault_reply(Command.VAULT_UNLOCK, args, kwargs)

    def lock_vault(self, *args, **kwargs):
        return self._vault_reply(Command.VAULT_LOCK, args, kwargs)

    def _close(self):
        self._closed.set()
        self._worker._begin_shutdown()
        if self._dialogs is not None:
            self._dialogs.close()

    def _status_copy(self, *, cancelled=False):
        with self._status_lock:
            return {**deepcopy(self._status), "cancelled": cancelled}

    def _phase(self, operation):
        with self._status_lock:
            self._status["operation"] = operation

    def _remember(self, value):
        with self._status_lock:
            self._status.update(vault=deepcopy(value["vault"]), selectionId=value["selectionId"])

    def _read_state(self):
        self._remember(self._worker.vault_request(Command.VAULT_STATE))

    def _vault_reply(self, command, args, kwargs):
        acquired, value, password = False, None, None
        try:
            if kwargs or (command not in (Command.VAULT_LOCK, Command.VAULT_UNLOCK) and args):
                return failure("INVALID_REQUEST")
            if command is Command.VAULT_UNLOCK and (
                    len(args) > 1 or args and (type(args[0]) is not str or not re.fullmatch(r"[0-9a-f]{32}", args[0]))):
                return failure("INVALID_REQUEST")
            if command is Command.VAULT_LOCK:
                if len(args) != 2 or any(type(item) is not str or not re.fullmatch(r"[0-9a-f]{32}", item) for item in args):
                    return failure("INVALID_REQUEST")
                value = VaultInput(vault_id=args[0], session_id=args[1])
            if self._closed.is_set() or not self._trusted():
                return failure("UNAVAILABLE")
            acquired = self._operation.acquire(blocking=False)
            if not acquired:
                # Public cached state/progress only; no off-thread managed access.
                return success(self._status_copy()) if command is Command.VAULT_STATE else failure("BUSY")
            self._phase("reading-state")
            if command in (Command.VAULT_CREATE, Command.VAULT_UNLOCK):
                self._read_state()
                previous = self._status_copy()
                if previous["vault"] and previous["vault"]["state"] == "unlocked":
                    return failure("VAULT_ACTIVE")
                creating = command is Command.VAULT_CREATE
                retry = command is Command.VAULT_UNLOCK and bool(args)
                if retry:
                    prepared = self._worker.vault_request(Command.VAULT_RETRY_CHECK,
                                                          VaultInput(selection_id=args[0]))
                    self._remember(prepared)
                    path = None  # No frontend-provided or rediscovered filename.
                else:
                    self._phase("selecting-file")
                    path = self._dialogs.choose_file(creating=creating)
                if self._closed.is_set():
                    return failure("UNAVAILABLE")
                if not retry and path is None:
                    self._phase("idle")
                    return success(self._status_copy(cancelled=True))
                if not creating and not retry:
                    self._remember(self._worker.vault_request(Command.VAULT_SELECT, VaultInput(path=path)))
                self._phase("waiting-password")
                password = self._dialogs.password(creating=creating)
                if self._closed.is_set():
                    return failure("UNAVAILABLE")
                if password is None:
                    if not creating and not retry:
                        self._remember(self._worker.vault_request(Command.VAULT_FORGET_SELECTION))
                    self._phase("idle")
                    return success(self._status_copy(cancelled=True))
                value = (VaultInput(path=path, password=password) if creating else
                         VaultInput(selection_id=self._status_copy()["selectionId"], password=password))
                password = None
            self._phase({Command.VAULT_CREATE: "creating", Command.VAULT_UNLOCK: "unlocking",
                         Command.VAULT_LOCK: "locking", Command.VAULT_STATE: "reading-state"}[command])
            result = self._worker.vault_request(command, value)
            value = None  # Queue/worker owns clearing the submitted input.
            if self._closed.is_set() or not self._trusted():
                return failure("UNAVAILABLE")
            self._remember(result)
            self._phase("idle")
            return success(self._status_copy())
        except WorkerError as error:
            if acquired and not self._closed.is_set():
                try:
                    self._read_state()
                except Exception:
                    pass
            return failure(error.code)
        except Exception:
            return failure("INTERNAL_ERROR")
        finally:
            # Submitted requests clear their own payload on the owner thread.
            # Unsubmitted values contain reference IDs only or cancelled input.
            password = None
            if acquired:
                self._phase("idle")
                self._operation.release()
            if self._on_complete:
                try:
                    self._on_complete()
                except Exception:
                    pass
