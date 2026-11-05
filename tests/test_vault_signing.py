"""Managed signing integration; private keys stay in process memory."""

import base64
import builtins
import copy
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest
from nacl.signing import VerifyKey
from pqcrypto.sign import falcon_512

import keygen
import sign
import signing_io
import utils
import vault
import vault_crypto
import vault_io
from vault_format import VaultError
from verify import verify_bytes


PASSWORD = "disposable managed signing password"
NEW_PASSWORD = "different disposable signing password"


@pytest.fixture
def integration():
    return importlib.import_module("vault_signing")


@pytest.fixture(scope="module")
def material():
    return keygen.generate_hybrid_key_pair()


@pytest.fixture
def cheap_kdf(monkeypatch):
    """Only boundary/fault cases: actual AESGCM and native signatures remain real."""
    monkeypatch.setattr(vault_crypto, "_derive_key", lambda backend, password, salt:
                        hashlib.sha256(b"PUBLIC-MANAGED-TEST\x00" + password + salt).digest())


def managed(tmp_path, material):
    path = tmp_path / "signer.hvault"
    vault.create_vault(path, material, PASSWORD)
    return SimpleNamespace(path=path, handle=vault.unlock_vault(path, PASSWORD), material=material)


@pytest.fixture
def real_case(tmp_path, material):
    case = managed(tmp_path, material)
    try:
        yield case
    finally:
        vault.lock_vault(case.handle)


@pytest.fixture
def fast_case(tmp_path, material, cheap_kdf):
    case = managed(tmp_path, material)
    try:
        yield case
    finally:
        vault.lock_vault(case.handle)


def check(data, public):
    return verify_bytes(data, public.ed25519_public_key, public.falcon_public_key)


def assert_no_stages(directory):
    assert not list(directory.glob(".esign-*"))


def test_real_managed_signing_uses_original_pair_and_both_layers(
        integration, real_case, pdf_path, tmp_path, monkeypatch):
    output = tmp_path / "signed.pdf"
    original = real_case.path.read_bytes()
    pair = real_case.handle.key_pair
    native, seen = sign.sign_with_key_material, []

    def shared(source, destination, key_pair, **kwargs):
        assert key_pair is pair
        seen.append(True)
        return native(source, destination, key_pair, **kwargs)

    monkeypatch.setattr(sign, "sign_with_key_material", shared)
    result = integration.sign_vault_document(real_case.handle, pdf_path, output)
    assert len(result) == 11 and result[0] == output
    assert seen == [True]
    data = output.read_bytes()
    public = real_case.material.public_keys
    parsed = utils.parse_signature_pair(data)
    ed, falcon = parsed.ed25519, parsed.falcon
    ed_signature = bytes.fromhex(data[ed.contents_start:ed.contents_start + ed.signature_length].decode())
    ed_message = data[:ed.gap_start] + data[ed.gap_end:ed.marker_end]
    assert VerifyKey(public.ed25519_public_key).verify(ed_message, ed_signature) == ed_message
    fal_signature = bytes.fromhex(data[falcon.contents_start:falcon.contents_start + falcon.signature_length].decode())
    fal_message = data[:falcon.gap_start] + data[falcon.gap_end:falcon.marker_end]
    assert falcon_512.verify(public.falcon_public_key, hashlib.shake_256(fal_message).digest(64), fal_signature) is True
    assert check(data, public)[0] is True
    assert real_case.path.read_bytes() == original
    assert not real_case.handle.is_locked
    assert_no_stages(tmp_path)


@pytest.mark.parametrize("capacities", [(64, 752), (80, 1024), (128, 2048), (256, 4096)])
def test_real_managed_custom_capacities(integration, real_case, pdf_path, tmp_path, monkeypatch, capacities):
    monkeypatch.setattr(sign, "DEFAULT_SIGNATURE_CAPACITIES", capacities)
    output = tmp_path / "custom.pdf"
    integration.sign_vault_document(real_case.handle, pdf_path, output)
    data = output.read_bytes()
    parsed = utils.parse_signature_pair(data)
    assert (parsed.ed25519.capacity_bytes, parsed.falcon.capacity_bytes) == capacities
    assert check(data, real_case.material.public_keys)[0] is True


@pytest.mark.parametrize("mutation", ["content", "append", "truncate", "padding", "range"])
def test_managed_signed_pdf_tampering_rejects(integration, fast_case, pdf_path, tmp_path, mutation):
    output = tmp_path / "signed.pdf"
    integration.sign_vault_document(fast_case.handle, pdf_path, output)
    data = output.read_bytes()
    if mutation == "content":
        data = data.replace(b"Phase 1", b"phase 1", 1)
    elif mutation == "append":
        data += b" "
    elif mutation == "truncate":
        data = data[:-1]
    elif mutation == "padding":
        offset = utils.parse_signature_pair(data).falcon.contents_end - 1
        data = data[:offset] + b"1" + data[offset + 1:]
    else:
        data = data.replace(b"ByteRange: [ 0000000000", b"ByteRange: [ 0000000001", 1)
    assert check(data, fast_case.material.public_keys)[0] is False


@pytest.mark.parametrize("invalid", ["locked", "none", "object", "uninitialized", "copied", "constructed", "subclass"])
def test_invalid_or_unissued_handles_reject_before_signer(integration, fast_case, pdf_path, tmp_path, monkeypatch, invalid):
    handle = fast_case.handle
    if invalid == "locked":
        vault.lock_vault(handle)
    elif invalid == "none":
        handle = None
    elif invalid == "object":
        handle = object()
    elif invalid == "uninitialized":
        handle = object.__new__(vault.UnlockedVault)
    elif invalid == "copied":
        handle = copy.copy(handle)
    elif invalid == "constructed":
        handle = vault.UnlockedVault(handle._result, vault_io.capture_vault(fast_case.path))
    elif invalid == "subclass":
        class Subclass(vault.UnlockedVault):
            pass
        handle = Subclass(handle._result, vault_io.capture_vault(fast_case.path))
    monkeypatch.setattr(sign, "sign_with_key_material", lambda *a, **kw: pytest.fail("Invalid handle reached signer"))
    with pytest.raises(VaultError):
        integration.sign_vault_document(handle, pdf_path, tmp_path / "never.pdf")
    assert_no_stages(tmp_path)


@pytest.mark.parametrize("field", ["_path", "_revision", "_result"])
def test_modified_handle_binding_rejects(integration, fast_case, pdf_path, tmp_path, monkeypatch, field):
    value = tmp_path / "other.hvault" if field == "_path" else "0" * 64 if field == "_revision" else object()
    setattr(fast_case.handle, field, value)
    monkeypatch.setattr(sign, "sign_with_key_material", lambda *a, **kw: pytest.fail("Modified binding reached signer"))
    with pytest.raises(VaultError):
        integration.sign_vault_document(fast_case.handle, pdf_path, tmp_path / "never.pdf")


def test_cross_thread_handle_rejected(integration, fast_case, pdf_path, tmp_path):
    outcomes = []

    def worker():
        try:
            integration.sign_vault_document(fast_case.handle, pdf_path, tmp_path / "never.pdf")
        except VaultError:
            outcomes.append("rejected")

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(10)
    assert not thread.is_alive() and outcomes == ["rejected"]
    assert not (tmp_path / "never.pdf").exists()


@pytest.mark.parametrize("context", ["process", "issuer"])
def test_cross_context_handle_rejects(integration, fast_case, pdf_path, tmp_path, monkeypatch, context):
    if context == "process":
        current_pid = os.getpid()
        monkeypatch.setattr(vault.os, "getpid", lambda: current_pid + 1)
    else:
        monkeypatch.setattr(vault, "_HANDLE_CONTEXT", object())
    with pytest.raises(vault.VaultHandleError):
        integration.sign_vault_document(fast_case.handle, pdf_path, tmp_path / "never.pdf")


@pytest.mark.parametrize("change", ["password", "ciphertext", "same_bytes_new_identity", "missing"])
def test_stale_handle_rejects_before_signer(integration, fast_case, pdf_path, tmp_path, monkeypatch, change):
    if change == "password":
        vault.change_vault_password(fast_case.path, PASSWORD, NEW_PASSWORD)
    elif change == "ciphertext":
        data = fast_case.path.read_bytes()
        fast_case.path.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
    elif change == "same_bytes_new_identity":
        backup = tmp_path / "replacement.hvault"
        vault.export_encrypted_backup(fast_case.path, backup, PASSWORD)
        os.replace(backup, fast_case.path)
    else:
        fast_case.path.rename(tmp_path / "moved.hvault")
    monkeypatch.setattr(sign, "sign_with_key_material", lambda *a, **kw: pytest.fail("Stale handle reached signer"))
    with pytest.raises(VaultError):
        integration.sign_vault_document(fast_case.handle, pdf_path, tmp_path / "never.pdf")
    assert_no_stages(tmp_path)


@pytest.mark.parametrize("storage", ["vault", "lock"])
@pytest.mark.parametrize("alias", ["exact", "relative", "case", "hardlink"])
def test_storage_output_aliases_reject(integration, fast_case, pdf_path, tmp_path, monkeypatch, storage, alias):
    protected = fast_case.path if storage == "vault" else vault_io.lock_file_path(fast_case.path)
    vault_before = fast_case.path.read_bytes()
    protected_before = protected.read_bytes()
    output = protected
    if alias == "relative":
        monkeypatch.chdir(tmp_path)
        output = Path(".") / protected.name
    elif alias == "case":
        output = Path(str(protected).upper())
    elif alias == "hardlink":
        output = tmp_path / "aliased-output.pdf"
        os.link(protected, output)
    with pytest.raises(VaultError):
        integration.sign_vault_document(fast_case.handle, pdf_path, output)
    assert fast_case.path.read_bytes() == vault_before
    assert protected.read_bytes() == protected_before
    assert_no_stages(tmp_path)


@pytest.mark.parametrize("storage", ["backup", "reserved_absent", "reserved_existing"])
def test_other_managed_storage_outputs_reject(integration, fast_case, pdf_path, tmp_path, storage):
    if storage == "backup":
        output = tmp_path / "backup-with-unusual-extension.bin"
        vault.export_encrypted_backup(fast_case.path, output, PASSWORD)
    else:
        output = tmp_path / ".hybrid-vault-candidate-reserved.tmp"
        if storage == "reserved_existing":
            output.write_bytes(b"unrelated reserved artifact")
    before = output.read_bytes() if output.exists() else None
    with pytest.raises(vault_io.VaultPathError):
        integration.sign_vault_document(fast_case.handle, pdf_path, output)
    assert output.read_bytes() == before if before is not None else not output.exists()
    assert_no_stages(tmp_path)


@pytest.mark.parametrize("fault", ["ed25519", "falcon", "stage", "candidate", "fsync", "verifier_false", "verifier_exception", "replace"])
@pytest.mark.parametrize("existing", [False, True])
def test_signing_failures_preserve_destination_and_release_lock(
        integration, fast_case, pdf_path, tmp_path, monkeypatch, fault, existing):
    output = tmp_path / "destination.pdf"
    if existing:
        output.write_bytes(b"existing destination")
    vault_before = fast_case.path.read_bytes()

    def fail(*a, **kw):
        raise OSError("SENSITIVE-INTERNAL-MARKER")

    if fault == "ed25519":
        monkeypatch.setattr(sign, "SigningKey", lambda *a: SimpleNamespace(sign=fail))
    elif fault == "falcon":
        native = falcon_512.sign
        monkeypatch.setattr(falcon_512, "sign", lambda key, message: fail() if len(message) == 64 else native(key, message))
    elif fault == "stage":
        monkeypatch.setattr(signing_io.SigningTransaction, "write_stage", fail)
    elif fault == "candidate":
        write = signing_io.SigningTransaction.write_candidate

        def partial(tx, data):
            write(tx, data[:7])
            fail()
        monkeypatch.setattr(signing_io.SigningTransaction, "write_candidate", partial)
    elif fault == "fsync":
        monkeypatch.setattr(signing_io.os, "fsync", fail)
    elif fault == "verifier_false":
        monkeypatch.setattr(sign, "verify_file_with_public_keys", lambda *a: (False,) + (0,) * 10)
    elif fault == "verifier_exception":
        monkeypatch.setattr(sign, "verify_file_with_public_keys", fail)
    else:
        monkeypatch.setattr(signing_io.os, "replace", fail)
    with pytest.raises(VaultError) as caught:
        integration.sign_vault_document(fast_case.handle, pdf_path, output)
    assert "SENSITIVE-INTERNAL-MARKER" not in str(caught.value)
    assert output.read_bytes() == b"existing destination" if existing else not output.exists()
    assert fast_case.path.read_bytes() == vault_before
    assert_no_stages(tmp_path)
    with vault_io.cooperative_locks([fast_case.path]):
        pass


@pytest.mark.parametrize("change", ["vault", "lock_handle", "context", "late_output_alias"])
def test_managed_checks_repeat_after_candidate_verification(
        integration, fast_case, pdf_path, tmp_path, monkeypatch, change):
    output = tmp_path / "destination.pdf"
    if change != "late_output_alias":
        output.write_bytes(b"existing destination")
    before = fast_case.path.read_bytes()
    verify = sign.verify_file_with_public_keys
    reached = []

    def mutated(*args):
        result = verify(*args)
        assert result[0] is True
        reached.append(True)
        if change == "vault":
            fast_case.path.write_bytes(before[:-1] + bytes([before[-1] ^ 1]))
        elif change == "lock_handle":
            vault.lock_vault(fast_case.handle)
        elif change == "context":
            monkeypatch.setattr(vault, "_HANDLE_CONTEXT", object())
        else:
            os.link(fast_case.path, output)
        return result

    monkeypatch.setattr(sign, "verify_file_with_public_keys", mutated)
    with pytest.raises(VaultError):
        integration.sign_vault_document(fast_case.handle, pdf_path, output)
    assert reached == [True]
    assert output.read_bytes() == (before if change == "late_output_alias" else b"existing destination")
    if change != "vault":
        assert fast_case.path.read_bytes() == before
    assert_no_stages(tmp_path)


def test_no_plaintext_key_writes_or_logs(integration, real_case, pdf_path, tmp_path, monkeypatch, capsys, caplog):
    original_open, original_io, original_fdopen = builtins.open, io.open, os.fdopen
    writes = []

    class Writer:
        def __init__(self, stream):
            self.stream = stream

        def __getattr__(self, name):
            return getattr(self.stream, name)

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def write(self, data):
            writes.append(bytes(data))
            return self.stream.write(data)

    def opened(opener, file, mode="r", *args, **kwargs):
        stream = opener(file, mode, *args, **kwargs)
        return Writer(stream) if any(letter in mode for letter in "wax") else stream

    monkeypatch.setattr(builtins, "open", lambda *a, **kw: opened(original_open, *a, **kw))
    monkeypatch.setattr(io, "open", lambda *a, **kw: opened(original_io, *a, **kw))
    monkeypatch.setattr(os, "fdopen", lambda *a, **kw: opened(original_fdopen, *a, **kw))
    integration.sign_vault_document(real_case.handle, pdf_path, tmp_path / "signed.pdf")
    assert writes
    for data in writes:
        for secret in (real_case.material.ed25519_private_seed, real_case.material.falcon_private_key, PASSWORD.encode()):
            assert secret not in data and secret.hex().encode() not in data
    assert capsys.readouterr() == ("", "") and caplog.text == ""
    assert_no_stages(tmp_path)


def test_vault_lock_is_held_through_native_pdf_replacement(integration, real_case, pdf_path, tmp_path, monkeypatch):
    original = os.replace
    observed = []
    script = """
import sys
from vault_io import cooperative_locks,VaultLockError
try:
    with cooperative_locks([sys.argv[1]]):
        raise AssertionError('managed signer released vault lock too early')
except VaultLockError:
    print('locked')
"""

    def replace(source, destination):
        child = subprocess.run([sys.executable, "-B", "-c", script, str(real_case.path)],
                               text=True, capture_output=True, check=True, timeout=15)
        assert child.stdout.strip() == "locked"
        observed.append(True)
        return original(source, destination)

    monkeypatch.setattr(signing_io.os, "replace", replace)
    integration.sign_vault_document(real_case.handle, pdf_path, tmp_path / "signed.pdf")
    assert observed == [True]
    with vault_io.cooperative_locks([real_case.path]):
        pass


def test_concurrent_vault_operation_rejects_during_managed_signing(integration, fast_case, pdf_path, tmp_path, monkeypatch):
    verified = sign.verify_file_with_public_keys
    observed = []

    def concurrent(*args):
        with pytest.raises(vault_io.VaultLockError):
            vault.change_vault_password(fast_case.path, PASSWORD, NEW_PASSWORD)
        observed.append(True)
        return verified(*args)

    monkeypatch.setattr(sign, "verify_file_with_public_keys", concurrent)
    integration.sign_vault_document(fast_case.handle, pdf_path, tmp_path / "signed.pdf")
    assert observed == [True]


def test_managed_signing_preserves_captured_source(integration, fast_case, pdf_path, tmp_path, monkeypatch):
    original = pdf_path.read_bytes()
    validate = sign.validate_unsigned_input

    def altered(data):
        validate(data)
        pdf_path.write_bytes(b"changed after capture")

    monkeypatch.setattr(sign, "validate_unsigned_input", altered)
    output = tmp_path / "snapshot.pdf"
    integration.sign_vault_document(fast_case.handle, pdf_path, output)
    assert output.read_bytes().startswith(original)
    assert check(output.read_bytes(), fast_case.material.public_keys)[0] is True


def test_creator_process_exits_before_reopen_and_sign(integration, pdf_path, tmp_path):
    path, output = tmp_path / "process.hvault", tmp_path / "process-signed.pdf"
    creator = """
import json,sys
from keygen import generate_hybrid_key_pair
from vault import create_vault
p=json.loads(sys.stdin.read())
pair=generate_hybrid_key_pair()
create_vault(p['vault'],pair,p['password'])
print(json.dumps(dict(id=pair.key_id,ed=pair.public_keys.ed25519_public_key.hex(),falcon=pair.public_keys.falcon_public_key.hex())))
"""
    public = json.loads(subprocess.run([sys.executable, "-B", "-c", creator],
                        input=json.dumps(dict(vault=str(path), password=PASSWORD)), text=True,
                        capture_output=True, check=True, timeout=20).stdout)
    signer = """
import json,sys
from vault import unlock_vault
from vault_signing import sign_vault_document
from verify import verify_file_with_public_keys
p=json.loads(sys.stdin.read())
with unlock_vault(p['vault'],p['password']) as handle:
    assert handle.metadata.key_id==p['id']
    result=sign_vault_document(handle,p['source'],p['output'])
    assert len(result)==11
    assert verify_file_with_public_keys(p['output'],bytes.fromhex(p['ed']),bytes.fromhex(p['falcon']))[0] is True
assert handle.is_locked
print('reopened-signed-verified')
"""
    result = subprocess.run([sys.executable, "-B", "-c", signer],
                input=json.dumps(dict(vault=str(path), password=PASSWORD, source=str(pdf_path), output=str(output), **public)),
                text=True, capture_output=True, check=True, timeout=20)
    assert result.stdout.strip() == "reopened-signed-verified"
    assert verify_bytes(output.read_bytes(), bytes.fromhex(public["ed"]), bytes.fromhex(public["falcon"]))[0] is True
    assert_no_stages(tmp_path)


@pytest.mark.parametrize("index", [0, 1])
def test_frozen_phase1_signatures_remain_valid(integration, index):
    cases = json.loads((Path(__file__).parent / "fixtures/phase1-signatures.json").read_text())["cases"]
    case = cases[index]
    data, ed, falcon = [base64.b64decode(case[field], validate=True) for field in
                       ("pdf_base64", "ed25519_public_base64", "falcon_public_base64")]
    assert verify_bytes(data, ed, falcon)[0] is True


def test_worker_can_unlock_its_own_context_and_sign(integration, fast_case, pdf_path, tmp_path):
    result = []
    output = tmp_path / "worker.pdf"

    def worker():
        with vault.unlock_vault(fast_case.path, PASSWORD) as own:
            result.append(integration.sign_vault_document(own, pdf_path, output))
        assert own.is_locked

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(15)
    assert not thread.is_alive() and len(result) == 1 and len(result[0]) == 11
    assert check(output.read_bytes(), fast_case.material.public_keys)[0] is True


def test_lock_file_acl_check_repeats_before_publication(integration, fast_case, pdf_path, tmp_path, monkeypatch):
    output = tmp_path / "preserved.pdf"
    output.write_bytes(b"previous destination")
    native = vault_io._native()
    lock_handle = native.open(vault_io.lock_file_path(fast_case.path), lock=True)
    try:
        identity = native.identity(lock_handle)
    finally:
        native.close(lock_handle)
    validate, verify = native.validate_security, sign.verify_file_with_public_keys
    late, rejected = [False], []

    def security(handle):
        if late[0] and native.identity(handle) == identity:
            rejected.append(True)
            raise vault_io.VaultSecurityError()
        return validate(handle)

    def verified(*args):
        result = verify(*args)
        assert result[0] is True
        late[0] = True
        return result

    monkeypatch.setattr(native, "validate_security", security)
    monkeypatch.setattr(sign, "verify_file_with_public_keys", verified)
    with pytest.raises(vault_io.VaultSecurityError):
        integration.sign_vault_document(fast_case.handle, pdf_path, output)
    assert rejected == [True]
    assert output.read_bytes() == b"previous destination"
    assert_no_stages(tmp_path)


def test_cooperative_lock_conflict_blocks_signer(integration, fast_case, pdf_path, tmp_path, monkeypatch):
    monkeypatch.setattr(sign, "sign_with_key_material", lambda *a, **kw: pytest.fail("Lock bypass reached signer"))
    with vault_io.cooperative_locks([fast_case.path]):
        with pytest.raises(vault_io.VaultLockError):
            integration.sign_vault_document(fast_case.handle, pdf_path, tmp_path / "never.pdf")
    assert not (tmp_path / "never.pdf").exists()


def test_no_key_regeneration_on_unlock_or_sign_failure(integration, fast_case, pdf_path, tmp_path, monkeypatch):
    monkeypatch.setattr(keygen, "generate_hybrid_key_pair", lambda *a: pytest.fail("Replacement key generation"))
    with pytest.raises(VaultError):
        vault.unlock_vault(fast_case.path, "wrong password")
    vault.lock_vault(fast_case.handle)
    with pytest.raises(VaultError):
        integration.sign_vault_document(fast_case.handle, pdf_path, tmp_path / "never.pdf")
    assert not (tmp_path / "never.pdf").exists()


def test_native_junction_output_alias_rejected(integration, fast_case, pdf_path, tmp_path):
    junction = tmp_path / "storage-junction"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(tmp_path)],
                   text=True, capture_output=True, check=True, timeout=10)
    original = fast_case.path.read_bytes()
    with pytest.raises(vault_io.VaultPathError):
        integration.sign_vault_document(fast_case.handle, pdf_path, junction / fast_case.path.name)
    assert fast_case.path.read_bytes() == original


def test_late_vault_magic_output_is_not_overwritten(integration, fast_case, pdf_path, tmp_path, monkeypatch):
    output = tmp_path / "ordinary.pdf"
    output.write_bytes(b"previous destination")
    encrypted = fast_case.path.read_bytes()
    verify = sign.verify_file_with_public_keys

    def changed(*args):
        result = verify(*args)
        output.write_bytes(encrypted)
        return result

    monkeypatch.setattr(sign, "verify_file_with_public_keys", changed)
    with pytest.raises(vault_io.VaultPathError):
        integration.sign_vault_document(fast_case.handle, pdf_path, output)
    assert output.read_bytes() == encrypted
    assert_no_stages(tmp_path)


def test_registry_does_not_keep_unreferenced_handles_alive(fast_case):
    import gc
    import weakref
    second = vault.unlock_vault(fast_case.path, PASSWORD)
    ref = weakref.ref(second)
    del second
    gc.collect()
    assert ref() is None


@pytest.mark.parametrize("change", ["vault", "lock_handle"])
def test_guards_execute_inside_final_publication_boundary(integration, fast_case, pdf_path, tmp_path, monkeypatch, change):
    output = tmp_path / "preserved.pdf"
    output.write_bytes(b"previous destination")
    publish = signing_io.SigningTransaction.publish
    entered = []

    def changed(tx):
        entered.append(True)
        if change == "vault":
            encrypted = fast_case.path.read_bytes()
            fast_case.path.write_bytes(encrypted[:-1] + bytes([encrypted[-1] ^ 1]))
        else:
            vault.lock_vault(fast_case.handle)
        return publish(tx)

    monkeypatch.setattr(signing_io.SigningTransaction, "publish", changed)
    with pytest.raises(VaultError):
        integration.sign_vault_document(fast_case.handle, pdf_path, output)
    assert entered == [True]
    assert output.read_bytes() == b"previous destination"
    assert_no_stages(tmp_path)


def test_path_failure_keeps_sanitized_cleanup_diagnostic(integration, fast_case, pdf_path, tmp_path, monkeypatch):
    output = tmp_path / "late-alias.pdf"
    verify = sign.verify_file_with_public_keys
    cleanup = signing_io.SigningTransaction._cleanup

    def alias(*args):
        result = verify(*args)
        os.link(fast_case.path, output)
        return result

    def denied(tx, *, working_only=False):
        if working_only:
            return cleanup(tx, working_only=True)
        raise PermissionError("SENSITIVE-CLEANUP-INTERNAL")

    monkeypatch.setattr(sign, "verify_file_with_public_keys", alias)
    monkeypatch.setattr(signing_io.SigningTransaction, "_cleanup", denied)
    with pytest.raises(VaultError) as caught:
        integration.sign_vault_document(fast_case.handle, pdf_path, output)
    assert any("cleanup" in note.lower() for note in getattr(caught.value, "__notes__", ()))
    assert "SENSITIVE-CLEANUP-INTERNAL" not in str(caught.value)
    assert output.read_bytes() == fast_case.path.read_bytes()
    assert len(list(tmp_path.glob(".esign-candidate-*"))) == 1


def test_postpublication_lock_release_error_reports_possible_commit(integration, fast_case, pdf_path, tmp_path, monkeypatch):
    output = tmp_path / "published.pdf"
    native = vault_io._native()
    close, replace = native.close, os.replace
    committed = [False]

    def published(*args):
        result = replace(*args)
        committed[0] = True
        return result

    def release(handle):
        close(handle)
        if committed[0]:
            raise OSError("SENSITIVE-LOCK-CLOSE")

    with monkeypatch.context() as patcher:
        patcher.setattr(signing_io.os, "replace", published)
        patcher.setattr(native, "close", release)
        with pytest.raises(vault_io.VaultIOError) as caught:
            integration.sign_vault_document(fast_case.handle, pdf_path, output)
    assert any("publication may have completed" in note.lower() for note in caught.value.__notes__)
    assert "SENSITIVE-LOCK-CLOSE" not in str(caught.value)
    assert check(output.read_bytes(), fast_case.material.public_keys)[0] is True
    assert_no_stages(tmp_path)
