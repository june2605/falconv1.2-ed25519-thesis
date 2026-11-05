"""One owned execution context and bounded FIFO; only fixed enum commands.

VaultWorker adds native-only sensitive input and owns managed handles. No
caller-supplied function or generic JavaScript-selected execution is accepted.
"""
from concurrent.futures import Future, TimeoutError
from dataclasses import dataclass, field
from enum import Enum
import math
from queue import Empty, Full, Queue
from threading import Event, RLock, Thread
from time import monotonic


class WorkerState(str, Enum):
    NEW = "new"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class Command(Enum):
    STATUS = "status"
    VAULT_STATE = "vault_state"
    VAULT_CREATE = "vault_create"
    VAULT_UNLOCK = "vault_unlock"
    VAULT_LOCK = "vault_lock"
    VAULT_SELECT = "vault_select"
    VAULT_RETRY_CHECK = "vault_retry_check"
    VAULT_FORGET_SELECTION = "vault_forget_selection"


class WorkerError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _timeout(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 5:
        raise WorkerError("INVALID_REQUEST")
    return value


@dataclass(frozen=True)
class _Request:
    command: Command
    deadline: float
    future: Future
    payload: object = field(default=None, repr=False)
    cancelled: Event = field(default_factory=Event, repr=False)


class Worker:
    def __init__(self, capacity=8):
        if type(capacity) is not int or not 1 <= capacity <= 64:
            raise ValueError("Invalid worker capacity")
        self._queue = Queue(maxsize=capacity)
        self._lock = RLock()
        self._ready, self._stop = Event(), Event()
        self._state = WorkerState.NEW
        self._thread = None
        self._sequence = 0
        self._cleanup_failed = False

    @property
    def state(self):
        with self._lock:
            return self._state

    def start(self, timeout=2.0):
        timeout = _timeout(timeout)
        with self._lock:
            if self._state is WorkerState.RUNNING:
                return
            if self._state is not WorkerState.NEW:
                raise WorkerError("UNAVAILABLE")
            self._state = WorkerState.STARTING
            self._thread = Thread(target=self._run, name="HybridSign-worker", daemon=False)
            self._thread.start()
        if not self._ready.wait(timeout):
            self._stop.set()
            with self._lock:
                self._state = WorkerState.FAILED
            raise WorkerError("TIMEOUT")
        if self.state is not WorkerState.RUNNING:
            raise WorkerError("UNAVAILABLE")

    def request(self, command, *, timeout=1.0):
        return self._request(command, timeout=timeout)

    def _request(self, command, *, timeout=1.0, payload=None):
        timeout = _timeout(timeout)
        if type(command) is not Command:
            raise WorkerError("INVALID_REQUEST")
        request = _Request(command, monotonic() + timeout, Future(), payload)
        with self._lock:
            if self._state is not WorkerState.RUNNING:
                raise WorkerError("UNAVAILABLE")
            try:
                self._queue.put_nowait(request)
            except Full:
                raise WorkerError("BUSY") from None
        try:
            return request.future.result(timeout)
        except TimeoutError:
            request.cancelled.set()
            request.future.cancel()  # Prevent execution if it has not started.
            raise WorkerError("TIMEOUT") from None

    def shutdown(self, timeout=2.0):
        timeout = _timeout(timeout)
        with self._lock:
            if self._state in (WorkerState.NEW, WorkerState.STOPPED):
                self._state = WorkerState.STOPPED
                return True
            self._state = WorkerState.STOPPING
            self._stop.set()
            thread = self._thread
        if thread:
            thread.join(timeout)
            if thread.is_alive():
                return False  # Never claim a running Python thread was killed.
        with self._lock:
            self._state = WorkerState.FAILED if self._cleanup_failed else WorkerState.STOPPED
        return not self._cleanup_failed

    def _begin_shutdown(self):
        """Revoke admission without joining or blocking the GUI closing event."""
        with self._lock:
            self._stop.set()
            if self._state in (WorkerState.RUNNING, WorkerState.STARTING):
                self._state = WorkerState.STOPPING

    def _handle(self, command, sequence):
        if command is Command.STATUS:
            return {"state": "running", "sequence": sequence}
        raise WorkerError("INVALID_REQUEST")

    def _dispatch(self, request, sequence):
        return self._handle(request.command, sequence)

    def _discard(self, request):
        pass

    def _finalize(self):
        pass

    def _run(self):
        try:
            with self._lock:
                if self._stop.is_set():
                    return
                self._state = WorkerState.RUNNING
                self._ready.set()
            while not self._stop.is_set():
                try:
                    request = self._queue.get(timeout=0.05)
                except Empty:
                    continue
                if not request.future.set_running_or_notify_cancel():
                    self._discard(request)
                    continue
                if monotonic() >= request.deadline:
                    request.future.set_exception(WorkerError("TIMEOUT"))
                    self._discard(request)
                    continue
                if self._stop.is_set():
                    request.future.set_exception(WorkerError("UNAVAILABLE"))
                    self._discard(request)
                    continue
                try:
                    self._sequence += 1
                    result = self._dispatch(request, self._sequence)
                    request.future.set_result(result)
                except WorkerError as error:
                    request.future.set_exception(WorkerError(error.code))
                except Exception:
                    request.future.set_exception(WorkerError("INTERNAL_ERROR"))
                finally:
                    self._discard(request)
        finally:
            try:
                self._finalize()
            except Exception:
                self._cleanup_failed = True  # Never log a cleanup traceback/locals.
            finally:
                self._settle_pending()

    def _settle_pending(self):
        with self._lock:
            self._state = WorkerState.FAILED if self._cleanup_failed else WorkerState.STOPPED
            while True:
                try:
                    pending = self._queue.get_nowait()
                except Empty:
                    break
                if not pending.future.done():
                    pending.future.set_exception(WorkerError("UNAVAILABLE"))
                self._discard(pending)
