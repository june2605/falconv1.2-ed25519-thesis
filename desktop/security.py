"""Pinned WebView2 transport/navigation restrictions; no privileged services."""
import json
import re
from threading import BoundedSemaphore
from urllib.parse import urlsplit

from .contracts import METHODS, failure


class NavigationPolicy:
    def __init__(self, address, paths):
        self.address = address
        self._origin = urlsplit(address)
        self._paths = frozenset(paths)

    def _path(self, url):
        try:
            parsed = urlsplit(url)
            if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
                    or parsed.port != self._origin.port or parsed.username is not None
                    or parsed.password is not None or parsed.query
                    or "\\" in url or any(ord(c) < 32 for c in url)):
                return None
            return parsed.path or "/"
        except (ValueError, TypeError):
            return None

    def navigation_allowed(self, url):
        return self._path(url) in ("/", "/index.html")

    def resource_allowed(self, url, method):
        path = self._path(url)
        return method in ("GET", "HEAD") and (path in self._paths or path == "/")


def decode_message(raw, source, policy):
    if type(raw) is not str or len(raw) > 4096 or not policy.navigation_allowed(source):
        return None
    try:
        def invalid_constant(_):
            raise ValueError()
        value = json.loads(raw, parse_constant=invalid_constant)
        if type(value) is not list or len(value) != 3:
            return None
        name, encoded, callback = value
        if (type(name) is not str or name not in METHODS or type(encoded) is not str
                or type(callback) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", callback)):
            return None
        args = json.loads(encoded, parse_constant=invalid_constant)
        if type(args) is not list or len(args) > 8:
            return None
        return name, args, callback
    except (ValueError, TypeError, RecursionError):
        return None


class NativeGuard:
    """Attach before first navigation; refuse startup if the pinned hooks fail.

    Filter native messages before pywebview's generic dispatcher, including its
    internal DOM/state/file-drop messages and dotted/private attribute lookups.
    At most eight bridge method executions are admitted concurrently. Framework
    response-marshalling threads may briefly outlive those method executions.
    """
    def __init__(self, window, bridge, policy):
        self._window, self._bridge, self._policy = window, bridge, policy
        self._slots = BoundedSemaphore(8)
        self._source = ""
        self._ready = False
        self.failed = False
        bridge._trusted = self.is_trusted
        bridge._on_complete = self._slots.release

    def is_trusted(self):
        # No COM/WebView2 calls from pywebview's bridge execution threads.
        return self._ready and self._policy.navigation_allowed(self._source)

    def close(self):
        self._ready = False
        self._source = ""

    def install(self):
        try:
            self._backend = self._window.native.browser
            self._view = self._backend.webview
            self._view.NavigationStarting += self._navigation
            self._view.NavigationCompleted += self._completed
            if self._view.CoreWebView2 is not None:
                self._secure_core()
            else:
                self._view.CoreWebView2InitializationCompleted += self._initialized
            from .runtime import fit_window_to_work_area
            fit_window_to_work_area(self._window.native)
        except Exception:
            self._fail()

    def _navigation(self, _, args):
        if not self._ready or not self._policy.navigation_allowed(str(args.Uri)):
            args.Cancel = True
        else:
            self._source = str(args.Uri)

    def _completed(self, *_):
        self._source = str(self._view.Source)

    def _initialized(self, _, args):
        if not args.IsSuccess:
            self._fail()
            return
        try:
            self._secure_core()
        except Exception:
            self._fail()

    def _secure_core(self):
        core = self._view.CoreWebView2
        # Remove framework handlers that could navigate/open a browser or invoke
        # its unrestricted dispatcher. This adapter is pinned to pywebview 6.2.1.
        self._view.WebMessageReceived -= self._backend.on_script_notify
        core.NewWindowRequested -= self._backend.on_new_window_request
        self._view.WebMessageReceived += self._message
        core.NewWindowRequested += self._popup
        core.FrameNavigationStarting += self._frame
        core.WebResourceRequested += self._resource
        core.DownloadStarting += self._download
        core.PermissionRequested += self._permission
        settings = core.Settings
        settings.AreDevToolsEnabled = False
        settings.AreDefaultContextMenusEnabled = False
        settings.AreBrowserAcceleratorKeysEnabled = False
        settings.AreDefaultScriptDialogsEnabled = False
        settings.AreHostObjectsAllowed = False
        self._ready = True

    def _message(self, sender, args):
        decoded = decode_message(str(args.WebMessageAsJson), str(args.Source), self._policy)
        if not self._ready or decoded is None:
            return
        name, _, callback = decoded
        self._source = str(args.Source)
        if not self._slots.acquire(blocking=False):
            # Both names and callback IDs were validated. Values are JSON encoded.
            reply = json.dumps({"value": json.dumps(failure("BUSY"))})
            script = (f"window.pywebview._returnValuesCallbacks[{json.dumps(name)}]"
                      f"[{json.dumps(callback)}]({reply})")
            self._view.CoreWebView2.ExecuteScriptAsync(script)
            return
        self._backend.on_script_notify(sender, args)

    def _popup(self, _, args):
        args.Handled = True  # No new view, browser, or navigation fallback.

    def _frame(self, _, args):
        args.Cancel = True

    def _download(self, _, args):
        args.Cancel = True

    def _permission(self, _, args):
        from Microsoft.Web.WebView2.Core import CoreWebView2PermissionState
        args.State = CoreWebView2PermissionState.Deny
        args.Handled = True

    def _resource(self, _, args):
        if not self._policy.resource_allowed(str(args.Request.Uri), str(args.Request.Method)):
            from System.IO import MemoryStream
            args.Response = self._view.CoreWebView2.Environment.CreateWebResourceResponse(
                MemoryStream(), 403, "Blocked", "Content-Length: 0\r\n")

    def _fail(self):
        self.failed = True
        self.close()
        # Never block before_show waiting for a not-yet-shown window.
        try:
            from System import Action
            self._window.native.BeginInvoke(Action(self._window.native.Close))
        except Exception:
            pass
