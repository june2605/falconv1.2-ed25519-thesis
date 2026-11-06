"""Verification runs on the existing vault thread, with independent public status."""
from concurrent.futures import Future
from copy import deepcopy
from queue import Full

from vault_format import VaultError
from vault_io import capture_vault
from .signing_worker import SigningWorker, ACTIVE
from .worker import Command, WorkerError, WorkerState, _Request

SELECT = (Command.VERIFY_SELECT_PDF, Command.VERIFY_SELECT_KEYS, Command.VERIFY_AUTH_KEYS, Command.VERIFY_CHECK)


class VerificationWorker(SigningWorker):
    def __init__(self, capacity=8):
        super().__init__(capacity)
        self._verification = None
        self._verifier = None

    def sign_busy(self):
        with self._jobs_lock:
            return super().sign_busy() or self._verification is not None and self._verification['public']['state'] in ACTIVE

    def verification_state(self, operation_id=None):
        with self._jobs_lock:
            if operation_id is not None and (self._verification is None or self._verification['args'][2] != operation_id):
                raise WorkerError('STALE_OPERATION')
            return deepcopy(self._verification['public']) if self._verification else {
                'operationId': None, 'state': 'idle', 'document': None, 'keySource': None,
                'hybridValid': None, 'errorCode': None}

    def verification_request(self, command, payload=None):
        if self.sign_busy(): raise WorkerError('BUSY')
        if command not in SELECT: raise WorkerError('INVALID_REQUEST')
        return self._request(command, payload=payload, timeout=5)

    def verification_duplicate(self, args):
        with self._jobs_lock:
            if self._verification and self._verification['args'][2] == args[2]:
                if self._verification['args'] != args: raise WorkerError('INVALID_REQUEST')
                return self.verification_state()
        return None

    def enqueue_verification(self, args, document, source):
        with self._lock, self._jobs_lock:
            if self.sign_busy(): raise WorkerError('BUSY')
            if self._state is not WorkerState.RUNNING: raise WorkerError('UNAVAILABLE')
            self._verification = {'args': args, 'public': {
                'operationId': args[2], 'state': 'ready', 'document': document,
                'keySource': source, 'hybridValid': None, 'errorCode': None}}
            try:
                self._verification['public']['state'] = 'queued'
                self._queue.put_nowait(_Request(Command.PDF_VERIFY, float('inf'), Future()))
            except Full:
                self._verification['public'].update(state='failed', errorCode='BUSY')
                raise WorkerError('BUSY') from None
        return self.verification_state()

    def _dispatch(self, request, sequence):
        if request.command not in (*SELECT, Command.PDF_VERIFY): return super()._dispatch(request, sequence)
        if self._verifier is None:
            from .verification_service import VerificationService
            self._verifier = VerificationService()
        try:
            if request.command is Command.VERIFY_SELECT_PDF: return self._verifier.select_pdf(request.payload)
            if request.command is Command.VERIFY_SELECT_KEYS:
                return self._verifier.select_keys(capture_vault(request.payload))
            if request.command is Command.VERIFY_AUTH_KEYS:
                if self._vaults is None: raise WorkerError('STALE_SESSION')
                snapshot = self._vaults.authenticated_public_snapshot(*request.payload)
                return self._verifier.select_keys(snapshot, authenticated=True)
            if request.command is Command.VERIFY_CHECK: return self._verifier.check_ids(*request.payload)
        except VaultError as error: raise WorkerError(error.code) from None
        except OSError: raise WorkerError('VERIFY_IO') from None
        with self._jobs_lock:
            self._verification['public']['state'] = 'running'
            args = self._verification['args']
        try:
            result = self._verifier.run(*args[:2])
            with self._jobs_lock:
                self._verification['public'].update(state='valid' if result else 'invalid', hybridValid=result)
        except Exception as error:
            code = error.code if isinstance(error, (WorkerError, VaultError)) else 'VERIFY_FAILED'
            with self._jobs_lock:
                self._verification['public'].update(state='failed', errorCode=code, hybridValid=None)
        return self.verification_state()
