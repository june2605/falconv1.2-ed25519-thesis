"""Authentication retries reuse only worker-validated encrypted snapshots."""
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Event

import pytest

from desktop.vault_bridge import VaultBridge
from desktop.vault_worker import VaultWorker


class Dialogs:
    def __init__(self, path):
        self.path = path
        self.secret = "disposable authentication test password"
        self.files = self.passwords = 0
    def choose_file(self, *, creating):
        self.files += 1
        return self.path
    def password(self, *, creating):
        self.passwords += 1
        return self.secret
    def close(self):
        pass


@pytest.fixture
def native(tmp_path):
    worker = VaultWorker()
    worker.start()
    dialogs = Dialogs(tmp_path / "retry.hvault")
    bridge = VaultBridge(worker, trusted=lambda: True, dialogs=dialogs)
    try:
        yield bridge, worker, dialogs
    finally:
        bridge._close()
        assert worker.shutdown()


def result(reply):
    assert reply["ok"] is True, reply
    return reply["data"]


def wrong_password(bridge, dialogs):
    original = result(bridge.create_vault())["vault"]
    encrypted = dialogs.path.read_bytes()
    dialogs.secret = "not the password"
    assert bridge.unlock_vault()["error"]["code"] == "vault.unlock"
    state = result(bridge.get_vault_state())
    assert state["vault"] == original  # Authentication failure changes no confirmed metadata.
    assert state["vault"]["sessionId"] is None
    assert state["selectionId"]
    return original, encrypted, state["selectionId"]


def test_retry_reprompts_password_without_reselecting_and_preserves_keys(native):
    bridge, _, dialogs = native
    original, encrypted, selection = wrong_password(bridge, dialogs)
    files, passwords = dialogs.files, dialogs.passwords
    dialogs.secret = "disposable authentication test password"
    opened = result(bridge.unlock_vault(selection))
    assert opened["vault"]["state"] == "unlocked"
    assert opened["selectionId"] is None  # Successful authentication consumes the reference.
    assert dialogs.files == files and dialogs.passwords == passwords + 1
    for field in ["hybridKeyId", "ed25519PublicKey", "falconPublicKey"]:
        assert opened["vault"][field] == original[field]
    assert dialogs.path.read_bytes() == encrypted


def test_failed_unlock_in_fresh_context_returns_no_unauthenticated_key_metadata(native):
    bridge, worker, dialogs = native
    original = result(bridge.create_vault())["vault"]
    bridge._close()
    assert worker.shutdown()
    replacement = VaultWorker()
    replacement.start()
    other = VaultBridge(replacement, trusted=lambda: True, dialogs=dialogs)
    try:
        dialogs.secret = "incorrect password"
        assert other.unlock_vault()["error"]["code"] == "vault.unlock"
        state = result(other.get_vault_state())
        assert state["vault"] is None and state["selectionId"]
        assert original["hybridKeyId"] not in json.dumps(state)
        dialogs.secret = "disposable authentication test password"
        opened = result(other.unlock_vault(state["selectionId"]))["vault"]
        assert opened["hybridKeyId"] == original["hybridKeyId"]
    finally:
        other._close()
        replacement.shutdown()


def test_cancelled_retry_preserves_safe_state_and_cannot_create_session(native):
    bridge, _, dialogs = native
    original, encrypted, selection = wrong_password(bridge, dialogs)
    dialogs.secret = None
    cancelled = result(bridge.unlock_vault(selection))
    assert cancelled["cancelled"] is True and cancelled["vault"] == original
    assert cancelled["vault"]["sessionId"] is None
    assert dialogs.path.read_bytes() == encrypted


@pytest.mark.parametrize("change", ["bytes", "identity", "missing"])
def test_changed_selection_rejects_before_retry_password_dialog(native, change):
    bridge, _, dialogs = native
    _, encrypted, selection = wrong_password(bridge, dialogs)
    if change == "bytes":
        changed = bytearray(encrypted)
        changed[-1] ^= 1
        dialogs.path.write_bytes(changed)
    elif change == "identity":
        # Move only our fixture; no original dataset or user file is deleted.
        dialogs.path.rename(dialogs.path.with_suffix(".moved"))
        dialogs.path.write_bytes(encrypted)
    else:
        dialogs.path.rename(dialogs.path.with_suffix(".moved"))
    previous = dialogs.passwords
    reply = bridge.unlock_vault(selection)
    assert reply["ok"] is False
    assert reply["error"]["code"] == "vault.conflict"
    assert dialogs.passwords == previous
    assert result(bridge.get_vault_state())["selectionId"] is None


def test_forged_and_consumed_selection_ids_do_not_prompt(native):
    bridge, _, dialogs = native
    _, _, selection = wrong_password(bridge, dialogs)
    previous = dialogs.passwords
    assert bridge.unlock_vault("0" * 32)["error"]["code"] == "STALE_SELECTION"
    assert dialogs.passwords == previous
    dialogs.secret = "disposable authentication test password"
    active = result(bridge.unlock_vault(selection))["vault"]
    result(bridge.lock_vault(active["vaultId"], active["sessionId"]))
    assert bridge.unlock_vault(selection)["error"]["code"] == "STALE_SELECTION"


def test_readonly_progress_during_password_and_crypto_has_no_sensitive_fields(native, monkeypatch):
    bridge, _, dialogs = native
    original = result(bridge.create_vault())["vault"]
    entered, release = Event(), Event()
    password = dialogs.password
    def waiting(**kwargs):
        entered.set()
        assert release.wait(3)
        return password(**kwargs)
    monkeypatch.setattr(dialogs, "password", waiting)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(bridge.unlock_vault)
        assert entered.wait(1)
        status = result(bridge.get_vault_state())
        assert status["operation"] == "waiting-password"
        assert status["vault"] == original and status["selectionId"]
        assert dialogs.secret not in json.dumps(status)
        assert str(dialogs.path) not in json.dumps(status)
        release.set()
        active = result(pending.result())["vault"]
    result(bridge.lock_vault(active["vaultId"], active["sessionId"]))
    monkeypatch.setattr(dialogs, "password", password)
    import desktop.vault_service as service
    original_unlock = service.unlock_vault
    entered.clear()
    release.clear()
    def decrypting(*args):
        entered.set()
        assert release.wait(3)
        return original_unlock(*args)
    monkeypatch.setattr(service, "unlock_vault", decrypting)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(bridge.unlock_vault)
        assert entered.wait(1)
        status = result(bridge.get_vault_state())
        assert status["operation"] == "unlocking" and status["vault"]["state"] == "locked"
        assert dialogs.secret not in json.dumps(status)
        release.set()
        assert result(pending.result())["vault"]["state"] == "unlocked"


@pytest.mark.parametrize("check", ["validate_volume", "validate_security"])
def test_retry_never_bypasses_storage_or_acl_checks(native, monkeypatch, check):
    import vault_io
    bridge, _, dialogs = native
    _, _, selection = wrong_password(bridge, dialogs)
    prompts = dialogs.passwords
    def reject(*_):
        raise vault_io.VaultSecurityError()
    with monkeypatch.context() as patch:
        patch.setattr(vault_io._native(), check, reject)
        assert bridge.unlock_vault(selection)["error"]["code"] == "vault.security"
    assert dialogs.passwords == prompts
    assert result(bridge.get_vault_state())["selectionId"] is None


def test_cross_worker_selection_reference_is_not_a_path_or_key_capability(native):
    bridge, _, dialogs = native
    _, _, selection = wrong_password(bridge, dialogs)
    other_worker = VaultWorker()
    other_worker.start()
    other = VaultBridge(other_worker, trusted=lambda: True, dialogs=dialogs)
    try:
        previous = dialogs.passwords
        assert other.unlock_vault(selection)["error"]["code"] == "STALE_SELECTION"
        assert dialogs.passwords == previous
    finally:
        other._close()
        other_worker.shutdown()
