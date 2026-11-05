"""Explicit native PDF selection, idempotent submission and status reconciliation."""
import re

from .contracts import SIGNING_CAPABILITIES, APP_INFO, failure, success
from .vault_bridge import VaultBridge
from .worker import Command, WorkerError


def valid_id(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{32}', value) is not None


class SigningBridge(VaultBridge):
    def _busy(self):
        return hasattr(self._worker, 'sign_busy') and self._worker.sign_busy()

    def _public_reply(self, data, args, kwargs):
        try:
            if args or kwargs: return failure('INVALID_REQUEST')
            if self._closed.is_set() or not self._trusted(): return failure('UNAVAILABLE')
            return success(data)
        except Exception: return failure('INTERNAL_ERROR')
        finally: self._complete()

    def get_app_info(self, *args, **kwargs):
        return self._public_reply(APP_INFO, args, kwargs)

    def get_capabilities(self, *args, **kwargs):
        return self._public_reply(SIGNING_CAPABILITIES, args, kwargs)

    def _complete(self):
        if self._on_complete:
            try: self._on_complete()
            except Exception: pass

    def _close(self):
        if self._busy(): return False
        super()._close()

    def _vault_reply(self, command, args, kwargs):
        if self._busy():
            if command is Command.VAULT_STATE: return self._public_reply(self._status_copy(), args, kwargs)
            return self._public_reply_error('BUSY')
        return super()._vault_reply(command, args, kwargs)

    def _public_reply_error(self, code):
        self._complete()
        return failure(code)

    def choose_pdf(self, *args, **kwargs):
        acquired = False
        try:
            if args or kwargs: return failure('INVALID_REQUEST')
            if self._closed.is_set() or not self._trusted(): return failure('UNAVAILABLE')
            if self._busy(): return failure('BUSY')
            acquired = self._operation.acquire(False)
            if not acquired: return failure('BUSY')
            path = self._dialogs.choose_pdf()
            if self._closed.is_set(): return failure('UNAVAILABLE')
            if path is None: return success({'document': None, 'cancelled': True})
            return success({'document': self._worker.pdf_request(Command.PDF_SELECT, path), 'cancelled': False})
        except WorkerError as error: return failure(error.code)
        except Exception: return failure('PDF_INVALID')
        finally:
            if acquired: self._operation.release()
            self._complete()

    def get_signing_state(self, *args, **kwargs):
        try:
            if kwargs or len(args) > 1 or any(not valid_id(value) for value in args): return failure('INVALID_REQUEST')
            if self._closed.is_set() or not self._trusted(): return failure('UNAVAILABLE')
            return success(self._worker.signing_state(args[0] if args else None))
        except WorkerError as error: return failure(error.code)
        except Exception: return failure('INTERNAL_ERROR')
        finally: self._complete()

    def sign_pdf(self, *args, **kwargs):
        acquired, reserved = False, False
        try:
            if kwargs or len(args) != 4 or any(not valid_id(value) for value in args): return failure('INVALID_REQUEST')
            if self._closed.is_set() or not self._trusted(): return failure('UNAVAILABLE')
            duplicate = self._worker.duplicate(args)
            if duplicate is not None: return success(duplicate)
            if self._busy(): return failure('BUSY')
            acquired = self._operation.acquire(False)
            if not acquired: return failure('BUSY')
            document = self._worker.pdf_request(Command.PDF_CHECK, args)
            self._read_state()
            self._worker.reserve(args, document, self._status_copy()['vault']['hybridKeyId'])
            reserved = True
            choice = self._dialogs.choose_pdf_output(document['displayName'].rsplit('.', 1)[0] + '-signed.pdf')
            if choice is None:
                self._worker.settle('cancelled')  # No engine was queued.
                return success(self._worker.signing_state())
            return success(self._worker.enqueue(choice))
        except WorkerError as error:
            if reserved: self._worker.fail_unqueued(error.code)
            return failure(error.code)
        except Exception:
            if reserved: self._worker.fail_unqueued('SIGN_FAILED')
            return failure('SIGN_UNCERTAIN' if reserved and self._busy() else 'SIGN_FAILED')
        finally:
            if acquired: self._operation.release()
            self._complete()
