"""Real encrypted-vault orchestration with Python-only dialog doubles."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from threading import Event, current_thread

import pytest

from desktop.vault_bridge import VaultBridge
from desktop.vault_worker import VaultWorker, VaultInput
from desktop.worker import Command, WorkerError
from hybrid_keys import hybrid_key_id
import vault
import vault_io


class Dialogs:
    def __init__(self, path, password="test-only vault password 123"):
        self.path, self.secret = path, password
        self.file_cancel = self.password_cancel = False
        self.calls = []
    def choose_file(self, *, creating):
        self.calls.append(("file", creating, current_thread()))
        return None if self.file_cancel else self.path
    def password(self, *, creating):
        self.calls.append(("password", creating, current_thread()))
        return None if self.password_cancel else self.secret
    def close(self):
        pass


@pytest.fixture
def native(tmp_path):
    worker = VaultWorker()
    worker.start()
    dialogs = Dialogs(tmp_path / "personal.hvault")
    bridge = VaultBridge(worker, trusted=lambda: True, dialogs=dialogs)
    try:
        yield bridge, worker, dialogs
    finally:
        bridge._close()
        assert worker.shutdown()


def data(reply):
    assert reply["ok"] is True, reply
    return reply["data"]


def test_real_create_reopen_original_public_keys_lock_and_repeated_cycles(native):
    bridge, worker, dialogs = native
    created = data(bridge.create_vault())["vault"]
    assert dialogs.path.stat().st_size == 2416
    assert created["state"] == "locked" and created["sessionId"] is None
    assert created["hybridKeyId"] == hybrid_key_id(bytes.fromhex(created["ed25519PublicKey"]),
                                                bytes.fromhex(created["falconPublicKey"]))
    encrypted = dialogs.path.read_bytes()
    for _ in range(3):
        opened = data(bridge.unlock_vault())["vault"]
        assert opened["state"] == "unlocked"
        for field in ["hybridKeyId", "ed25519PublicKey", "falconPublicKey"]:
            assert opened[field] == created[field]
        assert opened["sessionId"]
        locked = data(bridge.lock_vault(opened["vaultId"], opened["sessionId"]))["vault"]
        assert locked["state"] == "locked" and locked["sessionId"] is None
        assert bridge.lock_vault(opened["vaultId"], opened["sessionId"])["error"]["code"] == "STALE_SESSION"
    assert dialogs.path.read_bytes() == encrypted


def test_close_and_new_worker_reopens_existing_vault(native):
    bridge, worker, dialogs = native
    original = data(bridge.create_vault())["vault"]
    opened = data(bridge.unlock_vault())["vault"]
    bridge._close()
    assert worker.shutdown()
    replacement = VaultWorker()
    replacement.start()
    other = VaultBridge(replacement, trusted=lambda: True, dialogs=dialogs)
    try:
        assert data(other.get_vault_state())["vault"] is None
        recovered = data(other.unlock_vault())["vault"]
        assert recovered["hybridKeyId"] == original["hybridKeyId"]
        assert recovered["ed25519PublicKey"] == original["ed25519PublicKey"]
        assert recovered["falconPublicKey"] == original["falconPublicKey"]
        assert other.lock_vault(opened["vaultId"], opened["sessionId"])["error"]["code"] == "STALE_SESSION"
    finally:
        other._close()
        replacement.shutdown()


@pytest.mark.parametrize("cancel", ["file", "password"])
@pytest.mark.parametrize("operation", ["create_vault", "unlock_vault"])
def test_cancelled_dialog_has_no_success_and_no_file_changes(native, cancel, operation):
    bridge, _, dialogs = native
    if operation == "unlock_vault":
        data(bridge.create_vault())
    before = dialogs.path.read_bytes() if dialogs.path.exists() else None
    setattr(dialogs, cancel + "_cancel", True)
    result = data(getattr(bridge, operation)())
    assert result["cancelled"] is True
    assert (dialogs.path.read_bytes() if dialogs.path.exists() else None) == before
    assert not result["vault"] or result["vault"]["state"] == "locked"


def test_wrong_password_corruption_and_no_regeneration(native, monkeypatch):
    bridge, _, dialogs = native
    data(bridge.create_vault())
    before = dialogs.path.read_bytes()
    import desktop.vault_service as service
    monkeypatch.setattr(service, "generate_hybrid_key_pair", lambda: pytest.fail("regeneration"))
    dialogs.secret = "incorrect password"
    assert bridge.unlock_vault()["error"]["code"] == "vault.unlock"
    assert dialogs.path.read_bytes() == before
    dialogs.secret = "test-only vault password 123"
    data(bridge.unlock_vault())  # Explicit retry succeeds with original keys.
    opened = data(bridge.get_vault_state())["vault"]
    data(bridge.lock_vault(opened["vaultId"], opened["sessionId"]))
    changed = bytearray(before)
    changed[-1] ^= 1
    dialogs.path.write_bytes(changed)
    assert bridge.unlock_vault()["error"]["code"] == "vault.unlock"
    assert dialogs.path.read_bytes() == changed


def test_existing_destination_rejects_before_generation(native, monkeypatch):
    bridge, _, dialogs = native
    dialogs.path.write_bytes(b"preserve unrelated file")
    import desktop.vault_service as service
    monkeypatch.setattr(service, "generate_hybrid_key_pair", lambda: pytest.fail("unexpected generation"))
    assert bridge.create_vault()["error"]["code"] == "vault.exists"
    assert dialogs.path.read_bytes() == b"preserve unrelated file"


@pytest.mark.parametrize("fault", ["filesystem", "acl"])
def test_native_security_policy_fails_closed(native, monkeypatch, fault):
    bridge, _, dialogs = native
    native_io = vault_io._native()
    name = "validate_volume" if fault == "filesystem" else "validate_security"
    # The injected native check uses the same failure category as the real adapter.
    if not hasattr(native_io, name):
        name = "validate_acl"
    def fail(*_, **__):
        raise vault_io.VaultSecurityError()
    monkeypatch.setattr(native_io, name, fail)
    assert bridge.create_vault()["error"]["code"] == "vault.security"
    assert not dialogs.path.exists()


def test_all_key_and_managed_handle_operations_are_worker_owned(native, monkeypatch):
    bridge, worker, _ = native
    import desktop.vault_service as service
    seen = []
    for name in ["generate_hybrid_key_pair", "create_vault", "unlock_vault", "lock_vault"]:
        original = getattr(service, name)
        def record(*args, _original=original, _name=name, **kwargs):
            seen.append((_name, current_thread()))
            return _original(*args, **kwargs)
        monkeypatch.setattr(service, name, record)
    data(bridge.create_vault())
    data(bridge.unlock_vault())
    bridge._close()
    assert worker.shutdown()
    assert {name for name, _ in seen} == {"generate_hybrid_key_pair", "create_vault", "unlock_vault", "lock_vault"}
    assert all(thread is worker._thread for _, thread in seen)


def test_public_serialization_and_encrypted_only_writes(native, monkeypatch, capsys):
    bridge, _, dialogs = native
    import desktop.vault_service as service
    original = service.generate_hybrid_key_pair
    generated = []
    def record():
        pair = original()
        generated.append(pair)
        return pair
    monkeypatch.setattr(service, "generate_hybrid_key_pair", record)
    replies = [bridge.create_vault(), bridge.unlock_vault(), bridge.get_vault_state()]
    assert all(reply["ok"] for reply in replies)
    encoded = json.dumps(replies)
    assert dialogs.secret not in encoded and str(dialogs.path.parent) not in encoded
    assert "private" not in encoded and "handle" not in encoded
    pair = generated[0]
    for artifact in dialogs.path.parent.iterdir():
        stored = artifact.read_bytes()
        assert pair.ed25519_private_seed not in stored and pair.falcon_private_key not in stored
        assert pair.ed25519_private_seed.hex().encode() not in stored
        assert dialogs.secret.encode() not in stored
        assert not stored or len(stored) == 2416
    assert not capsys.readouterr().out
    assert not capsys.readouterr().err


@pytest.mark.parametrize("refs", [(None, None), ("x", "y"), ("0" * 32, "1" * 32), ({"path": "C:/bad"}, [])])
def test_invalid_forged_or_stale_references_cannot_lock_an_active_vault(native, refs):
    bridge, _, _ = native
    data(bridge.create_vault())
    actual = data(bridge.unlock_vault())["vault"]
    assert bridge.lock_vault(*refs)["ok"] is False
    assert data(bridge.get_vault_state())["vault"] == actual


@pytest.mark.parametrize("name", ["create_vault", "unlock_vault", "get_vault_state"])
def test_no_js_paths_passwords_kwargs_or_untrusted_calls(native, name):
    bridge, _, dialogs = native
    method = getattr(bridge, name)
    for args, kwargs in [((str(dialogs.path),), {}), ((), {"password": dialogs.secret}), (({},), {})]:
        assert method(*args, **kwargs)["error"]["code"] == "INVALID_REQUEST"
    assert not dialogs.calls
    bridge._trusted = lambda: False
    assert method()["error"]["code"] == "UNAVAILABLE"
    assert not dialogs.calls


def test_concurrent_prompts_are_fail_fast_and_shutdown_revokes_access(native):
    bridge, worker, dialogs = native
    entered, release = Event(), Event()
    original = dialogs.choose_file
    def blocked(**kwargs):
        entered.set()
        assert release.wait(3)
        return original(**kwargs)
    dialogs.choose_file = blocked
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(bridge.create_vault)
        assert entered.wait(1)
        assert bridge.unlock_vault()["error"]["code"] == "BUSY"
        bridge._close()
        release.set()
        assert pending.result()["ok"] is False
    assert worker.shutdown()
    assert not dialogs.path.exists()


def test_revision_change_invalidates_worker_session(native):
    bridge, _, dialogs = native
    data(bridge.create_vault())
    active = data(bridge.unlock_vault())["vault"]
    changed = bytearray(dialogs.path.read_bytes())
    changed[-1] ^= 1
    dialogs.path.write_bytes(changed)
    assert bridge.get_vault_state()["error"]["code"] == "vault.conflict"
    assert data(bridge.get_vault_state())["vault"]["state"] == "locked"
    assert bridge.lock_vault(active["vaultId"], active["sessionId"])["error"]["code"] == "STALE_SESSION"


def test_sensitive_request_repr_and_clear():
    value = VaultInput(path=Path("C:/private/path"), password="secret-password")
    assert "secret-password" not in repr(value) and "private/path" not in repr(value)
    value.clear()
    assert value.password is None and value.path is None


def test_explicit_six_method_api_and_exact_vault_capabilities(native):
    bridge, _, _ = native
    assert {name for name in dir(bridge) if not name.startswith("_")} == {
        "get_app_info", "get_capabilities", "get_vault_state", "create_vault", "unlock_vault", "lock_vault"}
    assert data(bridge.get_capabilities()) == {"nativeShell": True, "vaultOperations": True,
        "vaultCreate": True, "vaultUnlock": True, "vaultLock": True, "vaultPasswordChange": False,
        "vaultBackupRestore": False, "pdfSigning": False, "pdfVerification": False, "accountRegistry": False}
    assert data(bridge.get_vault_state()) == {"vault": None, "cancelled": False,
                                            "selectionId": None, "operation": "idle"}


@pytest.mark.parametrize("name", ["generate_hybrid_key_pair", "create_vault", "unlock_vault"])
def test_native_operation_faults_are_sanitized_and_preserve_destination(native, monkeypatch, name):
    bridge, _, dialogs = native
    import desktop.vault_service as service
    if name == "unlock_vault":
        data(bridge.create_vault())
    before = dialogs.path.read_bytes() if dialogs.path.exists() else None
    def fail(*_, **__):
        raise OSError("private secret password C:/sensitive/vault")
    monkeypatch.setattr(service, name, fail)
    result = bridge.unlock_vault() if name == "unlock_vault" else bridge.create_vault()
    assert result["error"]["code"] == "INTERNAL_ERROR"
    assert "sensitive" not in json.dumps(result)
    assert (dialogs.path.read_bytes() if dialogs.path.exists() else None) == before


@pytest.mark.parametrize("dialog", ["choose_file", "password"])
def test_dialog_exceptions_do_not_create_keys_or_files(native, monkeypatch, dialog):
    bridge, _, dialogs = native
    def fail(*_, **__):
        raise PermissionError("secret native dialog failure")
    monkeypatch.setattr(dialogs, dialog, fail)
    assert bridge.create_vault()["error"]["code"] == "INTERNAL_ERROR"
    assert not dialogs.path.exists()


def test_shutdown_locks_the_actual_managed_handle_on_its_owner(native, monkeypatch):
    bridge, worker, _ = native
    import desktop.vault_service as service
    handles, locks = [], []
    original_unlock, original_lock = service.unlock_vault, service.lock_vault
    def opened(*args):
        handle = original_unlock(*args)
        handles.append(handle)
        return handle
    def closed(handle):
        locks.append(current_thread())
        original_lock(handle)
    monkeypatch.setattr(service, "unlock_vault", opened)
    monkeypatch.setattr(service, "lock_vault", closed)
    data(bridge.create_vault())
    data(bridge.unlock_vault())
    assert not handles[0].is_locked
    bridge._close()
    assert worker.shutdown()
    assert handles[0].is_locked and locks == [worker._thread]


def test_timed_out_unlock_locks_late_handle_and_clears_password(native, monkeypatch):
    bridge, worker, dialogs = native
    import desktop.vault_service as service
    data(bridge.create_vault())
    entered, release = Event(), Event()
    original = service.unlock_vault
    handles = []
    def delayed(*args):
        handle = original(*args)
        handles.append(handle)
        entered.set()
        assert release.wait(2)
        return handle
    monkeypatch.setattr(service, "unlock_vault", delayed)
    value = VaultInput(path=dialogs.path, password=dialogs.secret)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(worker.vault_request, Command.VAULT_UNLOCK, value, timeout=0.5)
        assert entered.wait(1)
        with pytest.raises(WorkerError, match="TIMEOUT"):
            future.result()
        release.set()
    assert data(bridge.get_vault_state())["vault"]["state"] == "locked"
    assert handles[0].is_locked and value.password is None


def test_cooperative_lock_contention_cannot_bypass_vault_policy(native):
    bridge, _, dialogs = native
    data(bridge.create_vault())
    before = dialogs.path.read_bytes()
    with vault_io.cooperative_locks([dialogs.path]):
        assert bridge.unlock_vault()["error"]["code"] == "vault.file_locked"
    assert dialogs.path.read_bytes() == before
    assert data(bridge.unlock_vault())["vault"]["state"] == "unlocked"


def test_unsubmitted_secret_is_cleared_after_worker_shutdown():
    worker = VaultWorker()
    worker.shutdown()
    value = VaultInput(path="unused", password="do not retain this password")
    with pytest.raises(WorkerError, match="UNAVAILABLE"):
        worker.vault_request(Command.VAULT_UNLOCK, value)
    assert value.password is None


def test_closing_during_generation_stops_before_create_publication(native, monkeypatch):
    bridge, worker, dialogs = native
    import desktop.vault_service as service
    entered, release = Event(), Event()
    original = service.generate_hybrid_key_pair
    def delayed():
        pair = original()
        entered.set()
        assert release.wait(2)
        return pair
    monkeypatch.setattr(service, "generate_hybrid_key_pair", delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(bridge.create_vault)
        assert entered.wait(1)
        bridge._close()
        release.set()
        assert pending.result()["ok"] is False
    assert worker.shutdown()
    assert not dialogs.path.exists()


def test_worker_cleanup_failure_is_reported_without_uncaught_secret_exception(monkeypatch):
    import threading
    worker = VaultWorker()
    failures = []
    monkeypatch.setattr(threading, "excepthook", failures.append)
    def fail():
        raise RuntimeError("private cleanup diagnostic must not be logged")
    monkeypatch.setattr(worker, "_finalize", fail)
    worker.start()
    assert worker.shutdown() is False
    assert not worker._thread.is_alive()
    assert failures == []

