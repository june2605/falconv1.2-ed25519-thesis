import importlib.metadata
import sys
from types import SimpleNamespace

import pytest

from desktop import runtime
from desktop.runtime import StartupError


def test_installed_windows_prerequisites():
    version = runtime.require_runtime()
    assert int(version.split('.')[0]) >= 111


def test_unsupported_platform_and_architecture(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(StartupError, match="Windows x64"):
        runtime.require_runtime()
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(runtime.struct, "calcsize", lambda _: 4)
    with pytest.raises(StartupError, match="Windows x64"):
        runtime.require_runtime()


def test_unpinned_and_missing_dependencies(monkeypatch):
    monkeypatch.setattr(importlib.metadata, "version", lambda _: "0.0.0")
    with pytest.raises(StartupError, match="pinned"):
        runtime.require_runtime()
    def missing(_):
        raise importlib.metadata.PackageNotFoundError()
    monkeypatch.setattr(importlib.metadata, "version", missing)
    with pytest.raises(StartupError, match="requirements-desktop"):
        runtime.require_runtime()


def test_missing_and_malformed_runtime_registry_are_clear(monkeypatch):
    import winreg
    original_open = winreg.OpenKey
    def missing(hive, path, *args):
        if "EdgeUpdate" in path:
            raise FileNotFoundError()
        return original_open(hive, path, *args)
    monkeypatch.setattr(winreg, "OpenKey", missing)
    with pytest.raises(StartupError, match="WebView2 Evergreen Runtime"):
        runtime.require_runtime()
    monkeypatch.setattr(winreg, "OpenKey", original_open)
    original_query = winreg.QueryValueEx
    monkeypatch.setattr(winreg, "QueryValueEx", lambda key, name: ("110.0.0.0", 1) if name == "pv" else original_query(key, name))
    with pytest.raises(StartupError, match="111 or later"):
        runtime.require_runtime()
    monkeypatch.setattr(winreg, "QueryValueEx", lambda key, name: (None, 1) if name == "pv" else original_query(key, name))
    with pytest.raises(StartupError, match="WebView2 Evergreen Runtime"):
        runtime.require_runtime()
    monkeypatch.setattr(winreg, "QueryValueEx", lambda *_: (0, 1))
    with pytest.raises(StartupError, match=".NET Framework"):
        runtime.require_runtime()


def test_native_transport_filters_before_framework_dispatch():
    import json
    from desktop.security import NativeGuard, NavigationPolicy
    calls, replies = [], []
    bridge = SimpleNamespace()
    policy = NavigationPolicy("http://127.0.0.1:1234/", {"/index.html"})
    guard = NativeGuard(SimpleNamespace(), bridge, policy)
    guard._ready = True
    guard._backend = SimpleNamespace(on_script_notify=lambda *_: calls.append(True))
    guard._view = SimpleNamespace(CoreWebView2=SimpleNamespace(ExecuteScriptAsync=replies.append))
    def message(name, source="http://127.0.0.1:1234/index.html"):
        return SimpleNamespace(WebMessageAsJson=json.dumps([name, "[]", "123"]), Source=source)
    for name in ["__class__", "get_app_info.__globals__", "pywebviewStateUpdate", "pywebviewEventHandler", "execute"]:
        guard._message(None, message(name))
    guard._message(None, message("get_app_info", "https://evil.test/"))
    assert calls == []
    for _ in range(8):
        guard._message(None, message("get_app_info"))
    assert len(calls) == 8
    guard._message(None, message("get_app_info"))
    assert len(calls) == 8 and 'BUSY' in replies[0]
    bridge._on_complete()
    guard._message(None, message("get_capabilities"))
    assert len(calls) == 9
    guard.close()
    guard._message(None, message("get_app_info"))
    assert len(calls) == 9 and not guard.is_trusted()


def test_native_navigation_popup_download_and_frame_cancellation():
    from desktop.security import NativeGuard, NavigationPolicy
    guard = NativeGuard(SimpleNamespace(), SimpleNamespace(), NavigationPolicy("http://127.0.0.1:1234/", {"/index.html"}))
    guard._ready = True
    args = SimpleNamespace(Uri="https://evil.test/", Cancel=False, Handled=False)
    guard._navigation(None, args)
    assert args.Cancel
    args.Cancel = False
    guard._download(None, args)
    assert args.Cancel
    args.Cancel = False
    guard._frame(None, args)
    assert args.Cancel
    guard._popup(None, args)
    assert args.Handled
