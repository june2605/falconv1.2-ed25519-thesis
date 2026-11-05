"""Native Windows security/locking integration is distinct from injected faults."""

import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import keygen
import vault_crypto
from vault_format import VaultError


PASSWORD = "disposable vault password only"
NEW_PASSWORD = "different disposable password only"


@pytest.fixture
def modules():
    return importlib.import_module("vault"), importlib.import_module("vault_io")


@pytest.fixture(scope="module")
def pair():
    return keygen.generate_hybrid_key_pair()


@pytest.fixture
def cheap_kdf(monkeypatch):
    """Fault/path tests only: no change to production profile or AEAD checks."""
    monkeypatch.setattr(vault_crypto, "_derive_key", lambda backend, password, salt:
                        hashlib.sha256(b"PUBLIC-TEST-DOUBLE\x00" + password + salt).digest())


def candidates(directory):
    return list(directory.glob(".hybrid-vault-candidate-*"))


@pytest.mark.parametrize("filename", ["NUL", "CON.txt", "file:stream", "file.", "file ",
                                      ".hybrid-vault-lock-user.lck", "bad?.hvault"])
def test_unsupported_windows_paths_before_encryption(modules, pair, tmp_path, monkeypatch, filename):
    api, vio = modules
    monkeypatch.setattr(api, "seal_key_pair", lambda *a: pytest.fail("Unsafe path reached encryption"))
    with pytest.raises(vio.VaultPathError):
        api.create_vault(tmp_path / filename, pair, PASSWORD)
    assert not candidates(tmp_path)


@pytest.mark.parametrize("operation", ["create", "unlock", "change", "export", "import"])
def test_directory_target_rejected(modules, pair, tmp_path, operation):
    api, vio = modules
    folder = tmp_path / "folder"
    folder.mkdir()
    with pytest.raises(vio.VaultPathError):
        if operation == "create":
            api.create_vault(folder, pair, PASSWORD)
        elif operation == "unlock":
            api.unlock_vault(folder, PASSWORD)
        elif operation == "change":
            api.change_vault_password(folder, PASSWORD, NEW_PASSWORD)
        elif operation == "export":
            api.export_encrypted_backup(folder, tmp_path / "new", PASSWORD)
        else:
            api.import_encrypted_backup(folder, tmp_path / "new", PASSWORD)


@pytest.mark.parametrize("operation", ["export", "import"])
@pytest.mark.parametrize("alias", ["same", "relative", "hardlink"])
def test_copy_aliases_rejected_and_source_preserved(modules, pair, tmp_path, cheap_kdf, monkeypatch, operation, alias):
    api, vio = modules
    source = tmp_path / "original.hvault"
    api.create_vault(source, pair, PASSWORD)
    before = source.read_bytes()
    target = source
    if alias == "relative":
        monkeypatch.chdir(tmp_path)
        target = Path(".") / "original.hvault"
    elif alias == "hardlink":
        target = tmp_path / "alias.hvault"
        os.link(source, target)  # Actual native hard link; no mock or skip.
    with pytest.raises(VaultError):
        getattr(api, operation + "_encrypted_backup")(source, target, PASSWORD)
    assert source.read_bytes() == before
    assert not candidates(tmp_path)


def test_hardlinked_source_and_password_change_reject(modules, pair, tmp_path, cheap_kdf):
    api, vio = modules
    source = tmp_path / "original.hvault"
    api.create_vault(source, pair, PASSWORD)
    alias = tmp_path / "alias.hvault"
    os.link(source, alias)
    original = source.read_bytes()
    for operation in (lambda: api.unlock_vault(source, PASSWORD),
                      lambda: api.change_vault_password(source, PASSWORD, NEW_PASSWORD)):
        with pytest.raises(vio.VaultPathError):
            operation()
    assert source.read_bytes() == alias.read_bytes() == original


def test_native_windows_dacl_at_creation_and_after_rename(modules, pair, tmp_path):
    """Independent PowerShell Get-Acl inspects actual files, not mocked ACL data."""
    api, vio = modules
    path = tmp_path / "restricted.hvault"
    api.create_vault(path, pair, PASSWORD)
    api.change_vault_password(path, PASSWORD, NEW_PASSWORD)
    script = """
$a=Get-Acl -LiteralPath $env:VAULT_ACL_TEST_PATH
$owner=$a.GetOwner([System.Security.Principal.SecurityIdentifier]).Value
$aces=@($a.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier]) | ForEach-Object {
    @{sid=$_.IdentityReference.Value; rights=[int]$_.FileSystemRights; inherited=$_.IsInherited; type=[int]$_.AccessControlType}
})
@{owner=$owner; protected=$a.AreAccessRulesProtected; aces=$aces; user=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value} | ConvertTo-Json -Compress -Depth 4
"""
    env = dict(os.environ, VAULT_ACL_TEST_PATH=str(path))
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                            env=env, text=True, capture_output=True, check=True)
    acl = json.loads(result.stdout)
    assert acl["owner"] == acl["user"]
    assert acl["protected"] is True
    assert len(acl["aces"]) == 2
    assert {entry["sid"] for entry in acl["aces"]} == {acl["user"], "S-1-5-18"}
    assert all(entry["rights"] == 0x1F01FF and not entry["inherited"] and entry["type"] == 0
               for entry in acl["aces"])


def test_acl_checked_before_first_candidate_write(modules, pair, tmp_path, monkeypatch, cheap_kdf):
    api, vio = modules
    native = vio._native()
    validated, writes = [], []
    validate = native.validate_security
    write = vio._write_candidate_bytes

    def checked(handle):
        validate(handle)
        validated.append(handle)

    def writing(handle, data):
        import msvcrt
        assert msvcrt.get_osfhandle(handle.fileno()) in validated
        writes.append(data)
        return write(handle, data)

    monkeypatch.setattr(native, "validate_security", checked)
    monkeypatch.setattr(vio, "_write_candidate_bytes", writing)
    api.create_vault(tmp_path / "new.hvault", pair, PASSWORD)
    assert len(writes) == 1 and len(writes[0]) == 2416


def test_native_cooperative_lock_blocks_other_process(modules, pair, tmp_path):
    api, vio = modules
    path = tmp_path / "original.hvault"
    api.create_vault(path, pair, PASSWORD)
    original = path.read_bytes()
    script = """
import sys
from vault_io import cooperative_locks,VaultLockError
try:
    with cooperative_locks([sys.argv[1]]):
        raise AssertionError('concurrent lock was granted')
except VaultLockError:
    print('lock-conflict-detected')
"""
    with vio.cooperative_locks([path]):
        result = subprocess.run([sys.executable, "-B", "-c", script, str(path)],
                                text=True, capture_output=True, check=True)
    assert result.stdout.strip() == "lock-conflict-detected"
    assert path.read_bytes() == original
    # Released OS handle permits a subsequent process/local operation.
    with vio.cooperative_locks([path]):
        pass
    sidecars = list(tmp_path.glob(".hybrid-vault-lock-*.lck"))
    assert len(sidecars) == 1 and sidecars[0].read_bytes() == b""


@pytest.mark.parametrize("fault", ["create", "write", "short_write", "flush", "fsync", "close", "verify",
                                   "verify_false", "publish", "capture", "fdopen"])
@pytest.mark.parametrize("operation", ["create", "change", "export", "import"])
def test_prepublication_faults_preserve_files_and_clean_owned_candidates(
        modules, pair, tmp_path, monkeypatch, cheap_kdf, fault, operation):
    api, vio = modules
    source = tmp_path / "source.hvault"
    api.create_vault(source, pair, PASSWORD)
    before = source.read_bytes()
    target = source if operation == "change" else tmp_path / "destination.hvault"

    def fail(*args, **kwargs):
        raise OSError("INTERNAL-SENSITIVE-MARKER")

    if fault == "create":
        monkeypatch.setattr(vio, "_create_candidate", fail)
    elif fault == "write":
        def partial(handle, data):
            handle.write(data[:17])
            fail()
        monkeypatch.setattr(vio, "_write_candidate_bytes", partial)
    elif fault == "short_write":
        monkeypatch.setattr(vio, "_write_candidate_bytes", lambda handle, data: handle.write(data[:17]))
    elif fault == "flush":
        monkeypatch.setattr(vio, "_flush_candidate", fail)
    elif fault == "fsync":
        monkeypatch.setattr(vio.os, "fsync", fail)
    elif fault == "close":
        opened = vio._open_candidate_fd

        class CloseFailure:
            def __init__(self, stream):
                self.stream = stream

            def __getattr__(self, name):
                return getattr(self.stream, name)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.stream.close()
                fail()

        monkeypatch.setattr(vio, "_open_candidate_fd", lambda fd: CloseFailure(opened(fd)))
    elif fault == "verify":
        monkeypatch.setattr(vio.VaultTransaction, "verify", fail)
    elif fault == "verify_false":
        monkeypatch.setattr(api, "_same_recovery", lambda *args: False)
    elif fault == "publish":
        monkeypatch.setattr(vio, "_publish_atomic", fail)
    elif fault == "capture":
        capture = vio.capture_vault
        monkeypatch.setattr(vio, "capture_vault", lambda p, **kw: fail() if kw.get("internal") else capture(p, **kw))
    else:
        monkeypatch.setattr(vio, "_open_candidate_fd", fail)
    with pytest.raises(VaultError) as caught:
        if operation == "create":
            api.create_vault(target, pair, PASSWORD)
        elif operation == "change":
            api.change_vault_password(source, PASSWORD, NEW_PASSWORD)
        elif operation == "export":
            api.export_encrypted_backup(source, target, PASSWORD)
        else:
            api.import_encrypted_backup(source, target, PASSWORD)
    assert "INTERNAL-SENSITIVE-MARKER" not in str(caught.value)
    assert source.read_bytes() == before
    if target != source:
        assert not target.exists()
    assert not candidates(tmp_path)


def test_actual_candidate_authentication_before_single_publication(modules, pair, tmp_path, monkeypatch, cheap_kdf):
    api, vio = modules
    published, seen = [], []
    publish = vio._publish_atomic
    unseal = api.unseal_key_pair

    def verified(data, password):
        assert not published
        staged = candidates(tmp_path)
        assert len(staged) == 1
        # An exclusive open proves the writer has closed its native Windows handle.
        with staged[0].open("r+b") as f:
            assert f.read() == data
        seen.append(data)
        return unseal(data, password)

    def commit(source, destination, *, replace):
        assert len(seen) == 1
        published.append((source, destination, replace))
        return publish(source, destination, replace=replace)

    monkeypatch.setattr(api, "unseal_key_pair", verified)
    monkeypatch.setattr(vio, "_publish_atomic", commit)
    path = tmp_path / "new.hvault"
    api.create_vault(path, pair, PASSWORD)
    assert len(published) == 1 and published[0][2] is False
    assert path.read_bytes() == seen[0]


@pytest.mark.parametrize("mutation", ["candidate", "source", "destination_appears", "destination_replaced"])
def test_revision_rechecks_detect_changes_after_verification(modules, pair, tmp_path, monkeypatch, cheap_kdf, mutation):
    api, vio = modules
    source = tmp_path / "source.hvault"
    api.create_vault(source, pair, PASSWORD)
    before = source.read_bytes()
    destination = tmp_path / "backup.hvault"
    original_publish = vio.VaultTransaction.publish
    external = b"external writer must survive"

    def changed(tx):
        if mutation == "candidate":
            data = tx.candidate.read_bytes()
            tx.candidate.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
        elif mutation == "source":
            source.write_bytes(before[:-1] + bytes([before[-1] ^ 1]))
        elif mutation == "destination_appears":
            destination.write_bytes(external)
        else:
            source.write_bytes(external)
        return original_publish(tx)

    monkeypatch.setattr(vio.VaultTransaction, "publish", changed)
    with pytest.raises(VaultError):
        if mutation == "destination_replaced":
            api.change_vault_password(source, PASSWORD, NEW_PASSWORD)
        else:
            api.export_encrypted_backup(source, destination, PASSWORD)
    if mutation == "destination_appears":
        assert destination.read_bytes() == external
    else:
        assert not destination.exists()
    if mutation == "destination_replaced":
        assert source.read_bytes() == external
    assert not candidates(tmp_path)


def test_cleanup_failure_is_reported_without_unowned_deletion(modules, pair, tmp_path, monkeypatch, cheap_kdf):
    api, vio = modules
    unrelated = tmp_path / "unowned.tmp"
    unrelated.write_bytes(b"must remain")

    def failed_cleanup(*args):
        raise PermissionError("SENSITIVE-CLEANUP-DETAIL")

    with monkeypatch.context() as patcher:
        patcher.setattr(vio, "_remove_owned", failed_cleanup)
        patcher.setattr(vio, "_publish_atomic", lambda *a, **kw: (_ for _ in ()).throw(OSError("failure")))
        with pytest.raises(VaultError) as caught:
            api.create_vault(tmp_path / "new.hvault", pair, PASSWORD)
    assert "SENSITIVE-CLEANUP-DETAIL" not in str(caught.value)
    assert any("cleanup" in note.lower() for note in caught.value.__notes__)
    assert not (tmp_path / "new.hvault").exists()
    assert unrelated.read_bytes() == b"must remain"
    assert len(candidates(tmp_path)) == 1
    # Owned encrypted artifact retained under injected denial; pytest owns teardown.


def test_no_plaintext_persistence_across_all_operations(modules, pair, tmp_path, monkeypatch, cheap_kdf):
    api, vio = modules
    writes = []
    write = vio._write_candidate_bytes
    monkeypatch.setattr(vio, "_write_candidate_bytes", lambda handle, data: (writes.append(data), write(handle, data))[1])
    source, backup, restored = (tmp_path / name for name in ("source.hvault", "backup.hvault", "restored.hvault"))
    api.create_vault(source, pair, PASSWORD)
    api.export_encrypted_backup(source, backup, PASSWORD)
    api.import_encrypted_backup(backup, restored, PASSWORD)
    api.change_vault_password(source, PASSWORD, NEW_PASSWORD)
    assert len(writes) == 4 and all(len(data) == 2416 and data[:8] == b"HYBKVLT\x00" for data in writes)
    for data in writes + [p.read_bytes() for p in tmp_path.iterdir()]:
        for secret in (pair.ed25519_private_seed, pair.falcon_private_key, PASSWORD.encode(), NEW_PASSWORD.encode()):
            assert secret not in data and secret.hex().encode("ascii") not in data
    assert not candidates(tmp_path)


def test_required_security_failure_remains_security_error(modules, pair, tmp_path, monkeypatch):
    api, vio = modules

    def denied(*args):
        raise vio.VaultSecurityError()

    monkeypatch.setattr(vio._native(), "validate_volume", denied)
    with pytest.raises(vio.VaultSecurityError):
        api.create_vault(tmp_path / "new.hvault", pair, PASSWORD)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("fault", ["identity", "fd_conversion"])
def test_native_handle_setup_failure_cleans_created_candidate(modules, pair, tmp_path, monkeypatch, cheap_kdf, fault):
    api, vio = modules
    native = vio._native()

    def fail(*args):
        raise OSError("HANDLE-SETUP-FAILED")

    monkeypatch.setattr(native, "identity" if fault == "identity" else "fd", fail)
    with pytest.raises(VaultError):
        api.create_vault(tmp_path / "new.hvault", pair, PASSWORD)
    assert not candidates(tmp_path)
    assert not (tmp_path / "new.hvault").exists()


def test_native_junction_parent_is_rejected(modules, pair, tmp_path, cheap_kdf):
    """Actual Windows reparse point, with no symlink privilege requirement."""
    api, vio = modules
    directory = tmp_path / "real"
    directory.mkdir()
    source = directory / "source.hvault"
    api.create_vault(source, pair, PASSWORD)
    before = source.read_bytes()
    junction = tmp_path / "junction"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(directory)],
                   capture_output=True, text=True, check=True)
    for operation in (lambda: api.create_vault(junction / "new.hvault", pair, PASSWORD),
                      lambda: api.unlock_vault(junction / source.name, PASSWORD),
                      lambda: api.change_vault_password(junction / source.name, PASSWORD, NEW_PASSWORD),
                      lambda: api.export_encrypted_backup(source, junction / "backup.hvault", PASSWORD)):
        with pytest.raises(vio.VaultPathError):
            operation()
    assert source.read_bytes() == before
    assert not (directory / "new.hvault").exists()


def test_reparse_file_attribute_rejected_mocked_branch(modules, pair, tmp_path, monkeypatch):
    """File-symlink branch simulation; native parent junction coverage is separate."""
    from types import SimpleNamespace
    api, vio = modules
    target = tmp_path / "existing.hvault"
    target.write_bytes(b"unrelated content")
    lstat = Path.lstat

    def reparse(path, *args, **kwargs):
        info = lstat(path, *args, **kwargs)
        if path == target:
            return SimpleNamespace(st_mode=info.st_mode, st_nlink=1, st_file_attributes=0x400)
        return info

    monkeypatch.setattr(Path, "lstat", reparse)
    with pytest.raises(vio.VaultPathError):
        api.unlock_vault(target, PASSWORD)
    assert target.read_bytes() == b"unrelated content"


def test_native_broadened_acl_is_rejected(modules, pair, tmp_path, cheap_kdf):
    import ctypes as ct
    from ctypes import wintypes as wt
    api, vio = modules
    path = tmp_path / "vault.hvault"
    api.create_vault(path, pair, PASSWORD)
    before = path.read_bytes()
    # DACL-only native mutation avoids PowerShell Set-Acl requesting the
    # unavailable SeSecurityPrivilege for audit/SACL sections. No elevation.
    security = ct.WinDLL("advapi32", use_last_error=True)
    void, pvoid = ct.c_void_p, ct.POINTER(ct.c_void_p)
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wt.LPCWSTR, wt.DWORD, pvoid, void]
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wt.BOOL
    security.GetSecurityDescriptorDacl.argtypes = [void, ct.POINTER(wt.BOOL), pvoid, ct.POINTER(wt.BOOL)]
    security.GetSecurityDescriptorDacl.restype = wt.BOOL
    security.SetNamedSecurityInfoW.argtypes = [wt.LPWSTR, ct.c_int, wt.DWORD, void, void, void, void]
    security.SetNamedSecurityInfoW.restype = wt.DWORD
    descriptor, dacl, present, defaulted = void(), void(), wt.BOOL(), wt.BOOL()
    sddl = f"D:P(A;;FA;;;{vio._native().user_sid})(A;;FA;;;SY)(A;;FR;;;WD)"
    assert security.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, ct.byref(descriptor), None)
    try:
        assert security.GetSecurityDescriptorDacl(descriptor, ct.byref(present), ct.byref(dacl), ct.byref(defaulted))
        assert security.SetNamedSecurityInfoW(str(path), 1, 0x80000004, None, None, dacl, None) == 0
    finally:
        vio._native().kernel.LocalFree(descriptor)
    for operation in (lambda: api.unlock_vault(path, PASSWORD),
                      lambda: api.change_vault_password(path, PASSWORD, NEW_PASSWORD),
                      lambda: api.export_encrypted_backup(path, tmp_path / "backup.hvault", PASSWORD)):
        with pytest.raises(vio.VaultSecurityError):
            operation()
    assert path.read_bytes() == before


@pytest.mark.parametrize("operation", ["create", "export", "import"])
def test_create_only_native_rename_rejects_last_moment_destination(modules, pair, tmp_path, monkeypatch, cheap_kdf, operation):
    api, vio = modules
    source, destination = tmp_path / "source.hvault", tmp_path / "new.hvault"
    api.create_vault(source, pair, PASSWORD)
    original = source.read_bytes()
    publish = vio._publish_atomic

    def racing(candidate, target, *, replace):
        assert replace is False
        target.write_bytes(b"last moment external destination")
        return publish(candidate, target, replace=replace)

    monkeypatch.setattr(vio, "_publish_atomic", racing)
    with pytest.raises(vio.VaultExistsError):
        if operation == "create":
            api.create_vault(destination, pair, PASSWORD)
        elif operation == "export":
            api.export_encrypted_backup(source, destination, PASSWORD)
        else:
            api.import_encrypted_backup(source, destination, PASSWORD)
    assert destination.read_bytes() == b"last moment external destination"
    assert source.read_bytes() == original
    assert not candidates(tmp_path)


def test_native_open_handle_denies_password_change_replacement(modules, pair, tmp_path, cheap_kdf):
    api, vio = modules
    path = tmp_path / "vault.hvault"
    api.create_vault(path, pair, PASSWORD)
    before = path.read_bytes()
    handle = vio._native().open(path)  # Actual read-sharing handle denies delete sharing.
    try:
        with pytest.raises(vio.VaultPermissionError):
            api.change_vault_password(path, PASSWORD, NEW_PASSWORD)
    finally:
        vio._native().close(handle)
    assert path.read_bytes() == before
    assert not candidates(tmp_path)


def test_nonboolean_candidate_validation_cannot_publish(modules, pair, tmp_path, monkeypatch, cheap_kdf):
    api, vio = modules
    monkeypatch.setattr(api, "_same_recovery", lambda *args: (False, "truthy tuple"))
    with pytest.raises(vio.VaultVerificationError):
        api.create_vault(tmp_path / "new.hvault", pair, PASSWORD)
    assert not (tmp_path / "new.hvault").exists()
    assert not candidates(tmp_path)


def test_fsync_then_closed_candidate_then_verify_then_publish(modules, pair, tmp_path, monkeypatch, cheap_kdf):
    api, vio = modules
    events = []
    fsync, unseal, publish = os.fsync, api.unseal_key_pair, vio._publish_atomic

    def flushed(fd):
        fsync(fd)
        events.append("fsync")

    def verified(data, password):
        assert events == ["fsync"]
        fd = vio._native().open(candidates(tmp_path)[0], delete=True)
        vio._native().close(fd)
        events.append("verify")
        return unseal(data, password)

    def committed(*args, **kwargs):
        assert events == ["fsync", "verify"]
        result = publish(*args, **kwargs)
        events.append("publish")
        return result

    monkeypatch.setattr(vio.os, "fsync", flushed)
    monkeypatch.setattr(api, "unseal_key_pair", verified)
    monkeypatch.setattr(vio, "_publish_atomic", committed)
    api.create_vault(tmp_path / "new.hvault", pair, PASSWORD)
    assert events == ["fsync", "verify", "publish"]


@pytest.mark.parametrize("fault", ["uuid", "salt", "nonce"])
def test_password_change_rejects_lost_identity_or_reused_randomness(modules, pair, tmp_path, monkeypatch, cheap_kdf, fault):
    from dataclasses import replace
    from uuid import uuid4
    from vault_format import encode_header, parse_vault
    api, vio = modules
    path = tmp_path / "vault.hvault"
    original_metadata = api.create_vault(path, pair, PASSWORD)
    before = path.read_bytes()
    reseal = api._reseal_key_pair

    def wrong_identity(key_pair, password, vault_uuid):
        # UUID mismatch remains a fully authenticated valid vault.
        if fault == "uuid":
            return reseal(key_pair, password, uuid4())
        # Re-encrypt using controlled metadata inside this test only; no new
        # production salt/nonce injection is introduced.
        data = reseal(key_pair, password, vault_uuid)
        parsed = parse_vault(data)
        bad_metadata = replace(parsed.metadata, **{fault: getattr(original_metadata, fault)})
        aad = encode_header(bad_metadata)
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        derived = vault_crypto._derive_key(None, password.encode(), bad_metadata.salt)
        return aad + AESGCM(derived).encrypt(bad_metadata.nonce, vault_crypto._encode_payload(key_pair), aad)

    monkeypatch.setattr(api, "_reseal_key_pair", wrong_identity)
    with pytest.raises(vio.VaultVerificationError):
        api.change_vault_password(path, PASSWORD, NEW_PASSWORD)
    assert path.read_bytes() == before
    assert not candidates(tmp_path)


@pytest.mark.parametrize("fault", ["candidate_tag", "wrong_pair", "verifier_exception", "verifier_none"])
def test_cryptographic_gate_rejects_actual_candidate_faults(modules, pair, tmp_path, monkeypatch, cheap_kdf, fault):
    api, vio = modules
    path = tmp_path / "new.hvault"
    if fault == "candidate_tag":
        write = vio._write_candidate_bytes
        monkeypatch.setattr(vio, "_write_candidate_bytes", lambda stream, data:
                            write(stream, data[:-1] + bytes([data[-1] ^ 1])))
    elif fault == "wrong_pair":
        other = keygen.generate_hybrid_key_pair()
        seal = api.seal_key_pair
        monkeypatch.setattr(api, "seal_key_pair", lambda ignored, password: seal(other, password))
    elif fault == "verifier_none":
        monkeypatch.setattr(api, "unseal_key_pair", lambda *args: None)
    else:
        def fail(*args):
            raise RuntimeError("SENSITIVE-VERIFIER-MARKER")
        monkeypatch.setattr(api, "unseal_key_pair", fail)
    with pytest.raises(VaultError) as caught:
        api.create_vault(path, pair, PASSWORD)
    assert PASSWORD not in str(caught.value)
    assert pair.ed25519_private_seed.hex() not in str(caught.value)
    assert "SENSITIVE-VERIFIER-MARKER" not in str(caught.value)
    assert not path.exists()
    assert not candidates(tmp_path)


@pytest.mark.parametrize("operation", ["unlock", "change", "export", "import"])
def test_source_revision_is_rechecked_after_kdf(modules, pair, tmp_path, monkeypatch, cheap_kdf, operation):
    api, vio = modules
    source, target = tmp_path / "vault.hvault", tmp_path / "target.hvault"
    api.create_vault(source, pair, PASSWORD)
    before = source.read_bytes()
    unseal = api.unseal_key_pair
    externally_modified = before[:-1] + bytes([before[-1] ^ 1])

    def changed(data, password):
        result = unseal(data, password)
        source.write_bytes(externally_modified)
        return result

    monkeypatch.setattr(api, "unseal_key_pair", changed)
    with pytest.raises(vio.VaultConflictError):
        if operation == "unlock":
            api.unlock_vault(source, PASSWORD)
        elif operation == "change":
            api.change_vault_password(source, PASSWORD, NEW_PASSWORD)
        elif operation == "export":
            api.export_encrypted_backup(source, target, PASSWORD)
        else:
            api.import_encrypted_backup(source, target, PASSWORD)
    assert source.read_bytes() == externally_modified
    assert not target.exists()
    assert not candidates(tmp_path)


def test_cleanup_never_deletes_replaced_candidate_path(modules, pair, tmp_path, monkeypatch, cheap_kdf):
    api, vio = modules
    unrelated, moved = tmp_path / "unrelated.tmp", tmp_path / "owned-encrypted-retained.tmp"
    unrelated.write_bytes(b"unowned data")
    retargeted_state = []

    def retargeted(tx, validator):
        try:
            tx.candidate.rename(moved)
            os.link(unrelated, tx.candidate)
        except OSError as error:
            retargeted_state.append(("failed", getattr(error, "winerror", None)))
            raise
        retargeted_state.append(("replaced", None))
        raise OSError("injected external candidate replacement")

    monkeypatch.setattr(vio.VaultTransaction, "verify", retargeted)
    with pytest.raises(VaultError) as caught:
        api.create_vault(tmp_path / "new.hvault", pair, PASSWORD)
    assert retargeted_state == [("replaced", None)]
    assert unrelated.read_bytes() == b"unowned data"
    assert candidates(tmp_path)[0].read_bytes() == b"unowned data"
    assert moved.read_bytes()[:8] == b"HYBKVLT\x00"
    assert any("cleanup" in note.lower() for note in caught.value.__notes__)


def test_cooperating_process_cannot_change_password_while_locked(modules, pair, tmp_path):
    api, vio = modules
    path = tmp_path / "vault.hvault"
    api.create_vault(path, pair, PASSWORD)
    before = path.read_bytes()
    code = """
import json,sys
from vault import change_vault_password
from vault_io import VaultLockError
p=json.loads(sys.stdin.read())
try:
    change_vault_password(p['path'],p['old'],p['new'])
except VaultLockError:
    print('password-write-blocked')
else:
    raise AssertionError('concurrent password write succeeded')
"""
    with vio.cooperative_locks([path]):
        child = subprocess.run([sys.executable, "-B", "-c", code],
                               input=json.dumps(dict(path=str(path), old=PASSWORD, new=NEW_PASSWORD)),
                               text=True, capture_output=True, check=True)
    assert child.stdout.strip() == "password-write-blocked"
    assert path.read_bytes() == before


def test_inherited_or_unprotected_acl_rejects_existing_encrypted_file(modules, pair, tmp_path, cheap_kdf):
    api, vio = modules
    path = tmp_path / "manually-saved.hvault"
    encrypted = api.seal_key_pair(pair, PASSWORD)
    path.write_bytes(encrypted)  # Valid codec bytes, ordinary inherited Windows ACL.
    with pytest.raises(vio.VaultSecurityError):
        api.unlock_vault(path, PASSWORD)
    assert path.read_bytes() == encrypted


def test_candidate_acl_failure_is_closed_and_removed_before_any_write(modules, pair, tmp_path, monkeypatch, cheap_kdf):
    api, vio = modules
    created = vio._create_candidate

    def denied(*args):
        raise vio.VaultSecurityError()

    def protected(destination):
        monkeypatch.setattr(vio._native(), "validate_security", denied)
        return created(destination)

    monkeypatch.setattr(vio, "_create_candidate", protected)
    monkeypatch.setattr(vio, "_write_candidate_bytes", lambda *a: pytest.fail("Write before verified DACL"))
    with pytest.raises(vio.VaultSecurityError):
        api.create_vault(tmp_path / "new.hvault", pair, PASSWORD)
    assert not candidates(tmp_path)
    assert not (tmp_path / "new.hvault").exists()


def test_lock_release_error_after_commit_does_not_claim_rollback(modules, pair, tmp_path, monkeypatch, cheap_kdf):
    api, vio = modules
    path = tmp_path / "new.hvault"
    native = vio._native()
    close, publish = native.close, vio._publish_atomic
    published = [False]

    def commit(*args, **kwargs):
        result = publish(*args, **kwargs)
        published[0] = True
        return result

    def release(handle):
        close(handle)
        if published[0]:
            raise OSError("SENSITIVE-CLOSE-MARKER")

    with monkeypatch.context() as patcher:
        patcher.setattr(vio, "_publish_atomic", commit)
        patcher.setattr(native, "close", release)
        with pytest.raises(vio.VaultIOError) as caught:
            api.create_vault(path, pair, PASSWORD)
    assert any("publication may have completed" in note.lower() for note in caught.value.__notes__)
    assert "SENSITIVE-CLOSE-MARKER" not in str(caught.value)
    assert path.exists() and not candidates(tmp_path)
    with api.unlock_vault(path, PASSWORD) as handle:
        assert handle.key_pair == pair


def test_stale_handle_revision_cannot_authorize_second_password_change(modules, pair, tmp_path):
    api, vio = modules
    path = tmp_path / "vault.hvault"
    api.create_vault(path, pair, PASSWORD)
    with api.unlock_vault(path, PASSWORD) as handle:
        revision = handle.revision
    api.change_vault_password(path, PASSWORD, NEW_PASSWORD, expected_revision=revision)
    current = path.read_bytes()
    with pytest.raises(vio.VaultConflictError):
        api.change_vault_password(path, NEW_PASSWORD, PASSWORD, expected_revision=revision)
    assert path.read_bytes() == current
