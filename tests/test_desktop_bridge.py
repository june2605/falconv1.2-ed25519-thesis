import inspect
import json

import pytest

from desktop.bridge import DesktopBridge
from desktop.worker import Worker


@pytest.fixture
def bridge():
    worker = Worker()
    worker.start()
    try:
        yield DesktopBridge(worker, trusted=lambda: True)
    finally:
        worker.shutdown()


def test_only_two_approved_public_methods(bridge):
    public = {name for name in dir(bridge) if not name.startswith("_")}
    assert public == {"get_app_info", "get_capabilities"}
    assert all(inspect.ismethod(getattr(bridge, name)) for name in public)
    for name in ["signDocument", "createVault", "verifyDocument", "execute", "dispatch", "worker"]:
        assert not hasattr(bridge, name)


def test_exact_public_metadata_and_capabilities(bridge):
    assert bridge.get_app_info() == {"ok": True, "protocolVersion": 1, "data": {
        "applicationName": "HybridSign", "applicationVersion": "0.1.0",
        "runtime": "pywebview-edgechromium", "desktopStatus": "connected"}}
    expected = {"nativeShell": True, "vaultOperations": False, "pdfSigning": False,
                "pdfVerification": False, "accountRegistry": False}
    assert bridge.get_capabilities() == {"ok": True, "protocolVersion": 1, "data": expected}
    value = bridge.get_capabilities()
    value["data"]["pdfSigning"] = True
    assert bridge.get_capabilities()["data"] == expected
    encoded = json.dumps([bridge.get_app_info(), bridge.get_capabilities()])
    for forbidden in ["password", "private", "handle", "thread", "worker", "C:\\", ".venv"]:
        assert forbidden not in encoded


@pytest.mark.parametrize("args", [(None,), ({},), (1,), (True,), ("secret",), ([],), (1, 2)])
@pytest.mark.parametrize("name", ["get_app_info", "get_capabilities"])
def test_invalid_requests_have_fixed_errors(bridge, args, name):
    result = getattr(bridge, name)(*args)
    assert result == {"ok": False, "protocolVersion": 1, "error": {
        "code": "INVALID_REQUEST", "message": "Invalid desktop request."}}
    assert "secret" not in json.dumps(result)


def test_wrong_context_shutdown_faults_and_kwargs_are_sanitized(bridge, monkeypatch):
    assert bridge.get_app_info(unexpected="secret")["error"]["code"] == "INVALID_REQUEST"
    bridge._trusted = lambda: False
    assert bridge.get_app_info()["error"]["code"] == "UNAVAILABLE"
    bridge._trusted = lambda: True
    def fail(*_):
        raise RuntimeError("C:/private/password.key")
    monkeypatch.setattr(bridge._worker, "_handle", fail)
    reply = bridge.get_capabilities()
    assert reply["error"]["code"] == "INTERNAL_ERROR"
    assert "private" not in json.dumps(reply)
    bridge._worker.shutdown()
    assert bridge.get_app_info()["error"]["code"] == "UNAVAILABLE"
