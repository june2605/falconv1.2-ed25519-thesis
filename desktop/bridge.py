"""The js_api object has exactly two approved public methods."""
from .contracts import APP_INFO, CAPABILITIES, failure, success
from .worker import Command, WorkerError


class DesktopBridge:
    def __init__(self, worker, *, trusted):
        self._worker = worker
        self._trusted = trusted
        self._on_complete = None

    def get_app_info(self, *args, **kwargs):
        return self._reply(APP_INFO, args, kwargs)

    def get_capabilities(self, *args, **kwargs):
        return self._reply(CAPABILITIES, args, kwargs)

    def _reply(self, data, args, kwargs):
        try:
            if args or kwargs:
                return failure("INVALID_REQUEST")
            if not self._trusted():
                return failure("UNAVAILABLE")
            self._worker.request(Command.STATUS)
            return success(data)
        except WorkerError as error:
            return failure(error.code)
        except Exception:
            return failure("INTERNAL_ERROR")
        finally:
            if self._on_complete:
                try:
                    self._on_complete()
                except Exception:
                    pass  # Never let framework exception serialization leak context.
