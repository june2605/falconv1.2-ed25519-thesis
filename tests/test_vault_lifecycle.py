"""Lifecycle integration uses real Windows files, ACLs, and the approved KDF."""

import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from keygen import generate_hybrid_key_pair
from vault_crypto import unseal_key_pair
from vault_format import VaultUnlockError


PASSWORD = "disposable vault password only"
NEW_PASSWORD = "different disposable password only"


@pytest.fixture
def api():
    return importlib.import_module("vault")


@pytest.fixture(scope="module")
def pair():
    return generate_hybrid_key_pair()


@pytest.fixture
def saved(api, pair, tmp_path):
    path = tmp_path / "original.hvault"
    metadata = api.create_vault(path, pair, PASSWORD)
    return path, metadata


def assert_no_candidates(directory):
    assert not list(directory.glob(".hybrid-vault-candidate-*"))


def test_create_unlock_and_context_lock(api, pair, saved):
    path, metadata = saved
    assert len(path.read_bytes()) == 2416
    assert metadata.key_id == pair.key_id
    with api.unlock_vault(path, PASSWORD) as handle:
        assert handle.key_pair == pair
        assert handle.metadata == metadata
        assert handle.revision == hashlib.sha256(path.read_bytes()).hexdigest()
        assert not handle.is_locked
    assert handle.is_locked
    with pytest.raises(api.VaultLockedError):
        _ = handle.key_pair
    with pytest.raises(api.VaultLockedError):
        _ = handle.metadata
    with pytest.raises(api.VaultLockedError):
        handle.__enter__()
    api.lock_vault(handle)  # Idempotent.


def test_lock_after_exception_and_redacted_handle(api, pair, saved):
    path, _ = saved
    handle = api.unlock_vault(path, PASSWORD)
    copied_reference = handle.key_pair
    assert PASSWORD not in repr(handle)
    assert pair.ed25519_private_seed.hex() not in repr(handle)
    assert pair.falcon_private_key.hex() not in repr(handle)
    with pytest.raises(RuntimeError):
        with handle:
            raise RuntimeError("ordinary caller exception")
    assert handle.is_locked
    # Explicit limitation: lock cannot revoke copies already obtained by a caller.
    assert copied_reference == pair


def test_fresh_process_reopens_exact_material(api, pair, saved):
    path, _ = saved
    script = """
import json,sys
from vault import unlock_vault
control=json.loads(sys.stdin.read())
with unlock_vault(control['path'],control['password']) as unlocked:
    pair=unlocked.key_pair
    assert pair.ed25519_private_seed==bytes.fromhex(control['ed'])
    assert pair.falcon_private_key==bytes.fromhex(control['falcon'])
    assert pair.key_id==control['id']
print('fresh-process-recovery-passed')
"""
    # Private controls are passed through memory/stdin, never argv or disk.
    control = dict(path=str(path), password=PASSWORD, ed=pair.ed25519_private_seed.hex(),
                   falcon=pair.falcon_private_key.hex(), id=pair.key_id)
    result = subprocess.run([sys.executable, "-B", "-c", script], input=json.dumps(control),
                            text=True, capture_output=True, check=True)
    assert result.stdout.strip() == "fresh-process-recovery-passed"


def test_password_change_preserves_uuid_and_exact_keys(api, pair, saved):
    path, before = saved
    original = path.read_bytes()
    revision = hashlib.sha256(original).hexdigest()
    after = api.change_vault_password(path, PASSWORD, NEW_PASSWORD, expected_revision=revision)
    changed = path.read_bytes()
    assert len(changed) == len(original) == 2416
    assert after.vault_uuid == before.vault_uuid
    assert after.public_keys == before.public_keys == pair.public_keys
    assert after.key_id == before.key_id == pair.key_id
    assert after.salt != before.salt and after.nonce != before.nonce
    assert changed != original
    assert unseal_key_pair(changed, NEW_PASSWORD).key_pair == pair
    with pytest.raises(VaultUnlockError):
        api.unlock_vault(path, PASSWORD)
    with api.unlock_vault(path, NEW_PASSWORD) as handle:
        assert handle.key_pair == pair
    assert_no_candidates(path.parent)


@pytest.mark.parametrize("operation", ["unlock", "change", "export", "import"])
def test_wrong_password_preserves_files_and_generates_no_keys(api, saved, tmp_path, monkeypatch, operation):
    import keygen
    path, _ = saved
    original = path.read_bytes()
    target = tmp_path / "new.hvault"
    monkeypatch.setattr(keygen, "generate_hybrid_key_pair", lambda: pytest.fail("Replacement key generation"))
    with pytest.raises(VaultUnlockError):
        if operation == "unlock":
            api.unlock_vault(path, "wrong password")
        elif operation == "change":
            api.change_vault_password(path, "wrong password", NEW_PASSWORD)
        elif operation == "export":
            api.export_encrypted_backup(path, target, "wrong password")
        else:
            api.import_encrypted_backup(path, target, "wrong password")
    assert path.read_bytes() == original
    assert not target.exists()
    assert_no_candidates(tmp_path)


@pytest.mark.parametrize("offset", [0, 80, 96, 1069, 1734, 2400, 2415])
def test_tampered_disk_vault_rejects(api, saved, tmp_path, offset):
    from vault_format import VaultError
    path, _ = saved
    tampered = bytearray(path.read_bytes())
    tampered[offset] ^= 1
    path.write_bytes(tampered)
    with pytest.raises(VaultError):
        api.unlock_vault(path, PASSWORD)
    assert path.read_bytes() == bytes(tampered)
    assert_no_candidates(tmp_path)


def test_backup_restore_and_password_change_leave_backup_independent(api, pair, saved, tmp_path):
    path, original_metadata = saved
    original = path.read_bytes()
    backup = tmp_path / "backup.hvault"
    restored = tmp_path / "restored.hvault"
    exported = api.export_encrypted_backup(path, backup, PASSWORD)
    imported = api.import_encrypted_backup(backup, restored, PASSWORD)
    assert exported == imported == original_metadata
    assert path.read_bytes() == backup.read_bytes() == restored.read_bytes() == original
    assert os.stat(path).st_ino != os.stat(backup).st_ino != os.stat(restored).st_ino
    api.change_vault_password(path, PASSWORD, NEW_PASSWORD)
    assert backup.read_bytes() == restored.read_bytes() == original
    with api.unlock_vault(restored, PASSWORD) as unlocked:
        assert unlocked.key_pair == pair
    assert_no_candidates(tmp_path)


@pytest.mark.parametrize("operation", ["create", "export", "import"])
def test_existing_destinations_never_overwritten(api, pair, saved, tmp_path, operation):
    from vault_io import VaultExistsError
    source, _ = saved
    destination = tmp_path / "existing.hvault"
    destination.write_bytes(b"pre-existing destination must survive")
    original = source.read_bytes()
    with pytest.raises(VaultExistsError):
        if operation == "create":
            api.create_vault(destination, pair, PASSWORD)
        elif operation == "export":
            api.export_encrypted_backup(source, destination, PASSWORD)
        else:
            api.import_encrypted_backup(source, destination, PASSWORD)
    assert destination.read_bytes() == b"pre-existing destination must survive"
    assert source.read_bytes() == original
    assert_no_candidates(tmp_path)


def test_stale_expected_revision_rejects(api, saved):
    from vault_io import VaultConflictError
    path, _ = saved
    before = path.read_bytes()
    with pytest.raises(VaultConflictError):
        api.change_vault_password(path, PASSWORD, NEW_PASSWORD, expected_revision="0" * 64)
    assert path.read_bytes() == before


@pytest.mark.parametrize("new_password", ["short", "", "x" * 1025, "\ud800" * 15])
def test_invalid_new_password_preserves_original(api, saved, new_password):
    from vault_format import VaultPasswordError
    path, _ = saved
    before = path.read_bytes()
    with pytest.raises(VaultPasswordError):
        api.change_vault_password(path, PASSWORD, new_password)
    assert path.read_bytes() == before
    assert_no_candidates(path.parent)


@pytest.mark.parametrize("operation", ["unlock", "change", "import"])
def test_missing_vault_never_generates_keys(api, tmp_path, monkeypatch, operation):
    import keygen
    from vault_format import VaultError
    monkeypatch.setattr(keygen, "generate_hybrid_key_pair", lambda: pytest.fail("Replacement key generation"))
    missing = tmp_path / "missing.hvault"
    with pytest.raises(VaultError):
        if operation == "unlock":
            api.unlock_vault(missing, PASSWORD)
        elif operation == "change":
            api.change_vault_password(missing, PASSWORD, NEW_PASSWORD)
        else:
            api.import_encrypted_backup(missing, tmp_path / "restored.hvault", PASSWORD)
    assert not missing.exists()
