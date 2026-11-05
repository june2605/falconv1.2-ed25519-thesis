import json
from pathlib import Path
import socket
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from desktop.assets import BuildError, capture_build, make_server_type
from desktop.security import NavigationPolicy, decode_message
from desktop.launcher import default_build_path, main


@pytest.fixture
def build(tmp_path):
    root = tmp_path / "dist"
    root.mkdir()
    (root / "index.html").write_text('<!doctype html><script src="./assets/app.js"></script>')
    (root / "assets").mkdir()
    (root / "assets" / "app.js").write_text("/* trusted build fixture */")
    (root / "mark.svg").write_text("<svg/>")
    (root / "private.key").write_text("not a real key; must not be served")
    return root


def test_missing_build_and_default_path():
    with pytest.raises(BuildError, match="npm run build"):
        capture_build(Path("missing-build-for-desktop-test"))
    assert default_build_path().name == "dist"
    assert default_build_path().parent.name == "frontend"


def test_asset_snapshot_not_arbitrary_files_or_post_routes(build):
    snapshot = capture_build(build)
    assert set(snapshot.assets) == {"/index.html", "/assets/app.js", "/mark.svg"}
    server_type = make_server_type(snapshot)
    address, root, server = server_type.start_server([str(build / "index.html")], None)
    try:
        assert address.startswith("http://127.0.0.1:") and root == str(build.resolve())
        (build / "assets" / "app.js").write_text("mutated after capture")
        with urlopen(address + "assets/app.js", timeout=2) as response:
            assert response.read() == b"/* trusted build fixture */"
            assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
            assert response.headers["X-Content-Type-Options"] == "nosniff"
        for path in ["private.key", "../AGENTS.md", "%2e%2e/app.py", "assets/%2e%2e/private.key", "js_api/test", "index.html?x=1"]:
            with pytest.raises(HTTPError):
                urlopen(address + path, timeout=2)
        for request in [Request(address, data=b"{}"), Request(address, headers={"Host": "evil.test"}), Request(address, headers={"Origin": "https://evil.test"})]:
            with pytest.raises(HTTPError):
                urlopen(request, timeout=2)
    finally:
        server_type.close_all()
    assert not server.is_running
    assert not server._thread.is_alive()


def test_reparse_assets_are_rejected_without_creating_windows_symlinks(build, monkeypatch):
    import desktop.assets as module
    original = module._is_reparse
    monkeypatch.setattr(module, "_is_reparse", lambda path: path.name == "app.js" or original(path))
    with pytest.raises(BuildError):
        capture_build(build)


@pytest.mark.parametrize("url", ["https://example.test/", "file:///C:/Windows/win.ini", "data:text/html,evil", "javascript:alert(1)", "http://localhost:1234/index.html", "http://127.0.0.1:9999/index.html", "http://user@127.0.0.1:1234/index.html", "http://127.0.0.1:1234/other.html", "http://127.0.0.1:1234/index.html?evil=1", "http://127.0.0.1:bad/", ""])
def test_untrusted_navigation_rejected(url):
    policy = NavigationPolicy("http://127.0.0.1:1234/", {"/index.html", "/assets/app.js"})
    assert not policy.navigation_allowed(url)


def test_hash_routes_and_strict_resource_allowlist():
    policy = NavigationPolicy("http://127.0.0.1:1234/", {"/index.html", "/assets/app.js"})
    for path in ["index.html", "index.html#/sign", "index.html#/vault", "#main-content"]:
        assert policy.navigation_allowed("http://127.0.0.1:1234/" + path)
    assert policy.resource_allowed("http://127.0.0.1:1234/assets/app.js", "GET")
    assert not policy.navigation_allowed("http://127.0.0.1:1234/assets/app.js")
    assert not policy.resource_allowed("http://127.0.0.1:1234/assets/app.js", "POST")


@pytest.mark.parametrize("value", [None, {}, "not json", ["__class__.__init__", "[]", "123"], ["get_app_info", "[]", "');alert(1)//"], ["pywebviewEventHandler", "{}", "123"], ["pywebviewStateUpdate", "{}", "123"], ["get_app_info", "not json", "123"], ["get_app_info", "{}", "123"], ["get_app_info", "[]"], ["get_app_info", "[]", 1]])
def test_malformed_or_unapproved_transport_messages_are_not_dispatched(value):
    policy = NavigationPolicy("http://127.0.0.1:1234/", {"/index.html"})
    raw = value if isinstance(value, str) else json.dumps(value)
    assert decode_message(raw, "http://127.0.0.1:1234/index.html", policy) is None


def test_transport_origin_length_and_valid_message():
    policy = NavigationPolicy("http://127.0.0.1:1234/", {"/index.html"})
    raw = json.dumps(["get_app_info", "[]", "123456"])
    assert decode_message(raw, "http://127.0.0.1:1234/index.html#/settings", policy) == ("get_app_info", [], "123456")
    assert decode_message(raw, "https://evil.test/", policy) is None
    assert decode_message(" " * 4097, "http://127.0.0.1:1234/", policy) is None


def test_cli_missing_build_is_sanitized_before_gui_import(monkeypatch, capsys, tmp_path):
    import desktop.launcher as launcher
    monkeypatch.setattr(launcher, "default_build_path", lambda: tmp_path / "missing")
    assert main() == 1
    stderr = capsys.readouterr().err
    assert "npm run build" in stderr
    assert str(tmp_path) not in stderr and "Traceback" not in stderr


def test_idle_http_client_does_not_prevent_owned_server_shutdown(build):
    server_type = make_server_type(capture_build(build))
    address, _, server = server_type.start_server([str(build / "index.html")], None)
    port = int(address.split(":")[-1].rstrip("/"))
    connection = socket.create_connection(("127.0.0.1", port), timeout=2)
    try:
        connection.sendall(b"GET /index.html HTTP/1.1\r\n")  # Deliberately incomplete.
        start = time.monotonic()
        server_type.close_all()
        assert time.monotonic() - start < 3
        assert not server._thread.is_alive()
    finally:
        connection.close()
        server_type.close_all()


def test_launcher_pins_runtime_and_cleans_on_start_error(build, monkeypatch, capsys):
    import sys
    from types import SimpleNamespace
    from desktop import launcher
    from desktop.worker import Worker
    class Event:
        def __iadd__(self, callback):
            return self
    class Events:
        def __init__(self):
            self.initialized, self.closing = Event(), Event()
    class SpyWorker(Worker):
        instance = None
        def __init__(self):
            super().__init__()
            SpyWorker.instance = self
    called = {}
    def start(**kwargs):
        called.update(kwargs)
        raise OSError("C:/private/desktop-error")
    fake = SimpleNamespace(settings={}, create_window=lambda *a, **k: SimpleNamespace(events=Events()), start=start)
    monkeypatch.setitem(sys.modules, "webview", fake)
    monkeypatch.setattr(launcher, "default_build_path", lambda: build)
    monkeypatch.setattr(launcher, "require_runtime", lambda: "156.0.0.0")
    monkeypatch.setattr(launcher, "Worker", SpyWorker)
    assert launcher.main() == 1
    assert called["gui"] == "edgechromium" and called["debug"] is False
    assert called["http_server"] is True and called["private_mode"] is True
    assert fake.settings["ALLOW_DOWNLOADS"] is False
    assert fake.settings["REMOTE_DEBUGGING_PORT"] is None
    assert not SpyWorker.instance._thread.is_alive()
    stderr = capsys.readouterr().err
    assert "private" not in stderr and "Traceback" not in stderr


def test_server_bind_failure_does_not_register_a_partial_owner(build, monkeypatch):
    import desktop.assets as module
    class UnavailableServer:
        def __init__(self, *_):
            raise OSError("test bind failure")
    monkeypatch.setattr(module, "HTTPServer", UnavailableServer)
    server_type = make_server_type(capture_build(build))
    with pytest.raises(OSError, match="bind failure"):
        server_type.start_server([str(build / "index.html")], None)
    server_type.close_all()  # Must remain safe after partial startup.
    assert not server_type._instances


def test_server_thread_start_failure_closes_its_bound_socket(build, monkeypatch):
    import desktop.assets as module
    bound = []
    class RecordingServer(module.HTTPServer):
        def __init__(self, *args):
            super().__init__(*args)
            bound.append(self)
    class UnavailableThread(module.Thread):
        def start(self):
            raise RuntimeError("test thread startup failure")
    monkeypatch.setattr(module, "HTTPServer", RecordingServer)
    monkeypatch.setattr(module, "Thread", UnavailableThread)
    server_type = make_server_type(capture_build(build))
    try:
        with pytest.raises(RuntimeError, match="thread startup failure"):
            server_type.start_server([str(build / "index.html")], None)
        assert len(bound) == 1 and bound[0].socket.fileno() == -1
        server_type.close_all()
        assert not server_type._instances
    finally:
        for server in bound:
            server.server_close()


def test_launcher_stops_worker_even_if_server_cleanup_raises(build, monkeypatch, capsys):
    import sys
    from types import SimpleNamespace
    from desktop import launcher
    from desktop.worker import Worker
    class Event:
        def __iadd__(self, callback):
            return self
    class SpyWorker(Worker):
        instance = None
        def __init__(self):
            super().__init__()
            SpyWorker.instance = self
    def fail(*_, **__):
        raise OSError("C:/private/cleanup-error")
    fake = SimpleNamespace(settings={}, start=fail, create_window=lambda *a, **k:
                           SimpleNamespace(events=SimpleNamespace(initialized=Event(), closing=Event())))
    monkeypatch.setitem(sys.modules, "webview", fake)
    monkeypatch.setattr(launcher, "default_build_path", lambda: build)
    monkeypatch.setattr(launcher, "require_runtime", lambda: "156.0.0.0")
    monkeypatch.setattr(launcher, "Worker", SpyWorker)
    monkeypatch.setattr(launcher, "make_server_type", lambda _: SimpleNamespace(close_all=fail))
    try:
        assert launcher.main() == 1
        assert not SpyWorker.instance._thread.is_alive()
        stderr = capsys.readouterr().err
        assert "private" not in stderr and "Traceback" not in stderr
    finally:
        SpyWorker.instance.shutdown()
