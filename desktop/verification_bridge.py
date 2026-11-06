"""Five explicit public-only verification operations; no password or path arguments."""
from .contracts import VERIFICATION_CAPABILITIES, failure, success
from .signing_bridge import SigningBridge, valid_id
from .worker import Command, WorkerError


class VerificationBridge(SigningBridge):
    def get_capabilities(self, *args, **kwargs):
        return self._public_reply(VERIFICATION_CAPABILITIES, args, kwargs)

    def _verification_selection(self, command, args, kwargs):
        acquired = False
        try:
            expected = 2 if command is Command.VERIFY_AUTH_KEYS else 0
            if kwargs or len(args) != expected or any(not valid_id(value) for value in args):
                return failure('INVALID_REQUEST')
            if self._closed.is_set() or not self._trusted(): return failure('UNAVAILABLE')
            if self._busy(): return failure('BUSY')
            acquired = self._operation.acquire(False)
            if not acquired: return failure('BUSY')
            if expected: payload = args
            elif command is Command.VERIFY_SELECT_PDF: payload = self._dialogs.choose_verification_pdf()
            else: payload = self._dialogs.choose_file(creating=False)
            field = 'document' if command is Command.VERIFY_SELECT_PDF else 'keySource'
            if payload is None: return success({field: None, 'cancelled': True})
            if self._closed.is_set(): return failure('UNAVAILABLE')
            return success({field: self._worker.verification_request(command, payload), 'cancelled': False})
        except WorkerError as error: return failure(error.code)
        except Exception: return failure('VERIFY_IO')
        finally:
            if acquired: self._operation.release()
            self._complete()

    def choose_verification_pdf(self, *args, **kwargs):
        return self._verification_selection(Command.VERIFY_SELECT_PDF, args, kwargs)

    def choose_verification_keys(self, *args, **kwargs):
        return self._verification_selection(Command.VERIFY_SELECT_KEYS, args, kwargs)

    def use_authenticated_vault_keys(self, *args, **kwargs):
        return self._verification_selection(Command.VERIFY_AUTH_KEYS, args, kwargs)

    def verify_pdf(self, *args, **kwargs):
        acquired = False
        try:
            if kwargs or len(args) != 3 or any(not valid_id(value) for value in args): return failure('INVALID_REQUEST')
            if self._closed.is_set() or not self._trusted(): return failure('UNAVAILABLE')
            duplicate = self._worker.verification_duplicate(args)
            if duplicate is not None: return success(duplicate)
            if self._busy(): return failure('BUSY')
            acquired = self._operation.acquire(False)
            if not acquired: return failure('BUSY')
            document, source = self._worker.verification_request(Command.VERIFY_CHECK, args[:2])
            return success(self._worker.enqueue_verification(args, document, source))
        except WorkerError as error: return failure(error.code)
        except Exception: return failure('VERIFY_UNCERTAIN')
        finally:
            if acquired: self._operation.release()
            self._complete()

    def get_verification_state(self, *args, **kwargs):
        try:
            if kwargs or len(args) > 1 or any(not valid_id(value) for value in args): return failure('INVALID_REQUEST')
            if self._closed.is_set() or not self._trusted(): return failure('UNAVAILABLE')
            return success(self._worker.verification_state(args[0] if args else None))
        except WorkerError as error: return failure(error.code)
        except Exception: return failure('INTERNAL_ERROR')
        finally: self._complete()
