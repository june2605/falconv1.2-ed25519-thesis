"""One bounded in-process signing job, executed on the existing vault thread.

Signing never uses Future.result(timeout). Status remains queryable independently
of the execution queue; elapsed time cannot cancel or misclassify publication.
"""
from concurrent.futures import Future
from copy import deepcopy
from queue import Full
import secrets
from threading import RLock

from .vault_worker import VaultWorker
from .worker import Command, WorkerError, WorkerState, _Request

ACTIVE = ('ready', 'queued', 'running')


class SigningWorker(VaultWorker):
    def __init__(self, capacity=8):
        super().__init__(capacity)
        self._jobs_lock = RLock()
        self._job = None
        self._signer = None

    def sign_busy(self):
        with self._jobs_lock: return self._job is not None and self._job['public']['state'] in ACTIVE

    def signing_state(self, operation_id=None):
        with self._jobs_lock:
            if operation_id is not None and (self._job is None or self._job['public']['operationId'] != operation_id):
                raise WorkerError('STALE_OPERATION')
            return deepcopy(self._job['public']) if self._job else {
                'operationId': None, 'state': 'idle', 'document': None, 'outputName': None,
                'hybridKeyId': None, 'selfVerified': False, 'errorCode': None}

    def reserve(self, args, document, key_id):
        with self._jobs_lock:
            if self._job and self._job['public']['operationId'] == args[3]:
                if self._job['args'] != args: raise WorkerError('INVALID_REQUEST')
                return self.signing_state()
            if self.sign_busy(): raise WorkerError('BUSY')
            self._job = {'args': args, 'choice': None, 'public': {
                'operationId': args[3], 'state': 'ready', 'document': document,
                'outputName': None, 'hybridKeyId': key_id, 'selfVerified': False, 'errorCode': None}}
            return self.signing_state()

    def duplicate(self, args):
        with self._jobs_lock:
            if self._job and self._job['public']['operationId'] == args[3]:
                if self._job['args'] != args: raise WorkerError('INVALID_REQUEST')
                return self.signing_state()
        return None

    def settle(self, state, error=None):
        with self._jobs_lock:
            self._job['public'].update(state=state, errorCode=error)

    def fail_unqueued(self, error):
        with self._jobs_lock:
            if self._job and self._job['public']['state'] == 'ready':
                self.settle('failed', error)

    def enqueue(self, choice):
        with self._lock, self._jobs_lock:
            if self._state is not WorkerState.RUNNING or not self._job or self._job['public']['state'] != 'ready':
                raise WorkerError('UNAVAILABLE')
            self._job['choice'] = choice
            self._job['public']['state'] = 'queued'
            request = _Request(Command.PDF_SIGN, float('inf'), Future())
            try: self._queue.put_nowait(request)
            except Full:
                self.settle('failed', 'BUSY')
                raise WorkerError('BUSY') from None
        return self.signing_state()

    def pdf_request(self, command, payload):
        if self.sign_busy(): raise WorkerError('BUSY')
        if command not in (Command.PDF_SELECT, Command.PDF_CHECK): raise WorkerError('INVALID_REQUEST')
        return self._request(command, payload=payload, timeout=5)

    def vault_request(self, *args, **kwargs):
        if self.sign_busy(): raise WorkerError('BUSY')
        return super().vault_request(*args, **kwargs)

    def _dispatch(self, request, sequence):
        if request.command not in (Command.PDF_SELECT, Command.PDF_CHECK, Command.PDF_SIGN):
            return super()._dispatch(request, sequence)
        if self._signer is None:
            from .signing_service import SigningService
            self._signer = SigningService()
        if request.command is Command.PDF_SELECT:
            return self._signer.select(request.payload, secrets.token_hex(16))
        if request.command is Command.PDF_CHECK:
            doc_id, vault_id, session_id, _ = request.payload
            if self._vaults is None: raise WorkerError('STALE_SESSION')
            self._vaults.require_session(vault_id, session_id)
            return self._signer.require_document(doc_id)
        called = False
        def started():
            nonlocal called
            called = True
        with self._jobs_lock:
            self._job['public']['state'] = 'running'
            args, choice = self._job['args'], self._job['choice']
        try:
            name = self._signer.run(self._vaults, args, choice, started)
            with self._jobs_lock:
                self._job['public'].update(outputName=name, selfVerified=True)
                self.settle('completed')
        except Exception:
            self.settle('outcome-uncertain' if called else 'failed', 'SIGN_UNCERTAIN' if called else 'SIGN_FAILED')
        finally:
            with self._jobs_lock: self._job['choice'] = None
        return self.signing_state()

    def shutdown(self, timeout=2.0):
        if self.sign_busy(): return False  # No implicit cancellation or stop signal.
        return super().shutdown(timeout)

    def _begin_shutdown(self):
        if not self.sign_busy(): super()._begin_shutdown()
