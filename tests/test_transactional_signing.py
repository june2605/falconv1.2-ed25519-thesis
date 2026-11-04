"""Fault injection uses only disposable PDFs, keys and destinations."""

import ctypes
import inspect
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import sign
import signing_io
from verify import verify_file


def invoke(source, output, keys, *, public_key=None):
    return sign.sign_file(source, output, keys.sk_ed, keys.sk_falcon,
                          pk_falcon=keys.pk_falcon if public_key is None else public_key)


def assert_clean(folder):
    assert not list(folder.glob(".esign-*"))


def test_falcon_public_key_is_required_keyword_only(pdf_path, keys, tmp_path):
    parameter = inspect.signature(sign.sign_file).parameters.get("pk_falcon")
    assert parameter is not None
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        sign.sign_file(pdf_path, tmp_path / "missing-public.pdf", keys.sk_ed, keys.sk_falcon)
    with pytest.raises(TypeError):
        sign.sign_file(pdf_path, tmp_path / "positional.pdf", keys.sk_ed, keys.sk_falcon, keys.pk_falcon)


@pytest.mark.parametrize("validity", [False, 1, None])
@pytest.mark.parametrize("existing", [False, True])
def test_only_literal_true_verifier_result_can_publish(pdf_path, keys, tmp_path, monkeypatch, validity, existing):
    output = tmp_path / "destination.pdf"
    if existing:
        output.write_bytes(b"previous destination")
    calls = []

    def reject(*args):
        calls.append(args)
        return (validity,) + (0,) * 10

    monkeypatch.setattr(sign, "verify_file", reject, raising=False)
    with patch.object(os, "replace") as replace:
        with pytest.raises(ValueError, match="self-verification"):
            invoke(pdf_path, output, keys)
        replace.assert_not_called()
    assert len(calls) == 1
    assert output.read_bytes() == b"previous destination" if existing else not output.exists()
    assert_clean(tmp_path)


@pytest.mark.parametrize("fault", ["ed25519", "falcon", "stage", "candidate", "flush", "fsync", "verifier", "replace"])
@pytest.mark.parametrize("existing", [False, True])
def test_faults_preserve_destination_and_clean_owned_files(pdf_path, keys, tmp_path, monkeypatch, fault, existing):
    output = tmp_path / "destination.pdf"
    source = pdf_path.read_bytes()
    if existing:
        output.write_bytes(b"previous destination")
    failure = OSError("injected " + fault)

    def fail(*args, **kwargs):
        raise failure

    if fault == "ed25519":
        monkeypatch.setattr(sign, "SigningKey", lambda seed: SimpleNamespace(sign=fail))
    elif fault == "falcon":
        monkeypatch.setattr(sign.falcon_512, "sign", fail)
    elif fault == "stage":
        original = signing_io.SigningTransaction.write_stage

        def partial_stage(tx, name, data):
            original(tx, name, data[:7])
            fail()

        monkeypatch.setattr(signing_io.SigningTransaction, "write_stage", partial_stage)
    elif fault in ("candidate", "flush"):
        fdopen = signing_io.os.fdopen

        class BrokenWriter:
            def __init__(self, handle):
                self.handle = handle

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.handle.close()

            def write(self, data):
                if fault == "candidate":
                    self.handle.write(data[:7])
                    fail()
                return self.handle.write(data)

            def flush(self):
                fail()

            def fileno(self):
                return self.handle.fileno()

        monkeypatch.setattr(signing_io.os, "fdopen", lambda *args, **kwargs: BrokenWriter(fdopen(*args, **kwargs)))
    elif fault == "fsync":
        monkeypatch.setattr(signing_io.os, "fsync", fail)
    elif fault == "verifier":
        monkeypatch.setattr(sign, "verify_file", fail)
    else:
        monkeypatch.setattr(signing_io.os, "replace", fail)
    with pytest.raises(OSError) as error:
        invoke(pdf_path, output, keys)
    assert error.value is failure
    assert pdf_path.read_bytes() == source
    assert output.read_bytes() == b"previous destination" if existing else not output.exists()
    assert_clean(tmp_path)


def test_wrong_falcon_public_key_never_publishes(pdf_path, keys, key_factory, tmp_path):
    output = tmp_path / "destination.pdf"
    output.write_bytes(b"previous destination")
    with pytest.raises(ValueError, match="self-verification"):
        invoke(pdf_path, output, keys, public_key=key_factory().pk_falcon)
    assert output.read_bytes() == b"previous destination"
    assert_clean(tmp_path)


@pytest.mark.parametrize("key_name,size", [("sk_ed", 31), ("sk_falcon", 1280), ("pk_falcon", 896)])
def test_invalid_key_sizes_reject_before_staging(pdf_path, keys, tmp_path, key_name, size):
    getattr(keys, key_name).write_bytes(b"x" * size)
    output = tmp_path / "destination.pdf"
    output.write_bytes(b"previous destination")
    with patch.object(signing_io.tempfile, "mkdtemp") as create:
        with pytest.raises(ValueError):
            invoke(pdf_path, output, keys)
        create.assert_not_called()
    assert output.read_bytes() == b"previous destination"


@pytest.mark.parametrize("hard_link", [False, True])
def test_falcon_public_key_destination_is_protected(pdf_path, keys, tmp_path, hard_link):
    original = keys.pk_falcon.read_bytes()
    output = keys.pk_falcon
    if hard_link:
        output = tmp_path / "public-alias.pdf"
        os.link(keys.pk_falcon, output)
    with pytest.raises(ValueError) as error:
        invoke(pdf_path, output, keys)
    assert error.value.code == "path.alias"
    assert keys.pk_falcon.read_bytes() == original
    assert_clean(tmp_path)


def test_actual_closed_fsynced_candidate_is_verified_then_published_once(pdf_path, keys, tmp_path, monkeypatch):
    output = tmp_path / "destination.pdf"
    output.write_bytes(b"previous destination")
    events, handles, candidates, stages = [], [], [], []
    fdopen, fsync, replace = os.fdopen, os.fsync, os.replace
    mkstemp = signing_io.tempfile.mkstemp
    stage = signing_io.SigningTransaction.write_stage

    def record_stage(tx, name, data):
        path = stage(tx, name, data)
        stages.append((path, data))
        assert path.parent != output.parent
        assert output.read_bytes() == b"previous destination"
        return path

    def exclusive_candidate(*args, **kwargs):
        assert Path(kwargs["dir"]) == output.parent
        result = mkstemp(*args, **kwargs)
        candidates.append(Path(result[1]))
        return result

    def record_handle(*args, **kwargs):
        handle = fdopen(*args, **kwargs)
        handles.append(handle)
        return handle

    def record_sync(fd):
        events.append("fsync")
        return fsync(fd)

    def verify_candidate(candidate, pk_ed, pk_falcon):
        assert Path(candidate) == candidates[0] and Path(candidate) != output
        assert handles and all(handle.closed for handle in handles)
        assert events == ["fsync"]
        assert Path(pk_ed).read_bytes() == keys.pk_ed.read_bytes()
        assert Path(pk_falcon).read_bytes() == keys.pk_falcon.read_bytes()
        # Reopening for writing would fail on Windows if an exclusive writer leaked.
        with open(candidate, "r+b"):
            pass
        assert Path(candidate).read_bytes().startswith(pdf_path.read_bytes())
        result = verify_file(candidate, pk_ed, pk_falcon)
        assert result[0] is True
        events.append("verified")
        return result

    def publish(candidate, destination):
        assert events == ["fsync", "verified"]
        assert not any(path.exists() for path, _ in stages)
        assert Path(destination) == output
        assert output.read_bytes() == b"previous destination"
        events.append("replace")
        return replace(candidate, destination)

    monkeypatch.setattr(signing_io.SigningTransaction, "write_stage", record_stage)
    monkeypatch.setattr(signing_io.tempfile, "mkstemp", exclusive_candidate)
    monkeypatch.setattr(signing_io.os, "fdopen", record_handle)
    monkeypatch.setattr(signing_io.os, "fsync", record_sync)
    monkeypatch.setattr(sign, "verify_file", verify_candidate)
    monkeypatch.setattr(signing_io.os, "replace", publish)
    result = invoke(pdf_path, output, keys)
    assert result[0] == output and len(result) == 11
    assert all(isinstance(value, (int, float)) and value >= 0 for value in result[1:])
    assert events == ["fsync", "verified", "replace"]
    assert len(candidates) == 1
    assert len(stages) >= 6
    assert keys.sk_ed.read_bytes() not in [data for _, data in stages]
    assert keys.sk_falcon.read_bytes() not in [data for _, data in stages]
    assert verify_file(output, keys.pk_ed, keys.pk_falcon)[0] is True
    assert_clean(tmp_path)


def test_verification_reads_disk_candidate_not_memory(pdf_path, keys, tmp_path, monkeypatch):
    output = tmp_path / "destination.pdf"
    output.write_bytes(b"previous destination")

    def corrupt_then_verify(candidate, pk_ed, pk_falcon):
        path = Path(candidate)
        data = path.read_bytes()
        path.write_bytes(b"!" + data[1:])
        return verify_file(path, pk_ed, pk_falcon)

    monkeypatch.setattr(sign, "verify_file", corrupt_then_verify)
    with pytest.raises(ValueError, match="self-verification"):
        invoke(pdf_path, output, keys)
    assert output.read_bytes() == b"previous destination"
    assert_clean(tmp_path)


def test_keys_are_captured_once_and_live_key_changes_do_not_change_signing(pdf_path, keys, key_factory, tmp_path, monkeypatch):
    alternate = key_factory()
    originals = {name: getattr(keys, name).read_bytes() for name in ("sk_ed", "sk_falcon", "pk_falcon")}
    public_ed = tmp_path / "original-ed-public.key"
    public_falcon = tmp_path / "original-falcon-public.key"
    public_ed.write_bytes(keys.pk_ed.read_bytes())
    public_falcon.write_bytes(originals["pk_falcon"])
    prepare = sign.prepare_bytes_with_placeholder
    capture = sign.capture_source
    captured = []

    def record_capture(path):
        captured.append(Path(path).resolve())
        return capture(path)

    def mutate_live_keys(*args, **kwargs):
        for name in originals:
            getattr(keys, name).write_bytes(getattr(alternate, name).read_bytes())
        return prepare(*args, **kwargs)

    monkeypatch.setattr(sign, "capture_source", record_capture)
    monkeypatch.setattr(sign, "prepare_bytes_with_placeholder", mutate_live_keys)
    output = tmp_path / "captured.pdf"
    invoke(pdf_path, output, keys)
    assert sorted(captured) == sorted([pdf_path.resolve()] + [getattr(keys, name).resolve() for name in originals])
    assert verify_file(output, public_ed, public_falcon)[0] is True
    assert_clean(tmp_path)


@pytest.mark.parametrize("target", ["source", "sk_ed", "sk_falcon", "pk_falcon"])
def test_aliases_introduced_after_verification_are_rejected(pdf_path, keys, tmp_path, monkeypatch, target):
    output = tmp_path / "destination.pdf"
    protected = pdf_path if target == "source" else getattr(keys, target)
    original = protected.read_bytes()

    def introduce_alias(candidate, pk_ed, pk_falcon):
        result = verify_file(candidate, pk_ed, pk_falcon)
        assert result[0] is True
        os.link(protected, output)
        return result

    monkeypatch.setattr(sign, "verify_file", introduce_alias)
    with pytest.raises(ValueError) as error:
        invoke(pdf_path, output, keys)
    assert error.value.code == "path.alias"
    assert protected.read_bytes() == original and output.read_bytes() == original
    assert_clean(tmp_path)


def test_captured_key_identity_stays_protected_after_key_path_replacement(pdf_path, keys, tmp_path, monkeypatch):
    output = tmp_path / "destination.pdf"
    old_key_alias = tmp_path / "original-public.key"
    os.link(keys.pk_falcon, old_key_alias)
    original = old_key_alias.read_bytes()

    def replace_key_path(candidate, pk_ed, pk_falcon):
        result = verify_file(candidate, pk_ed, pk_falcon)
        replacement = tmp_path / "replacement.key"
        replacement.write_bytes(b"x" * len(original))
        os.replace(replacement, keys.pk_falcon)
        os.link(old_key_alias, output)
        return result

    monkeypatch.setattr(sign, "verify_file", replace_key_path)
    with pytest.raises(ValueError) as error:
        invoke(pdf_path, output, keys)
    assert error.value.code == "path.alias"
    assert old_key_alias.read_bytes() == original
    assert_clean(tmp_path)


@pytest.mark.parametrize("capacities", [(64, 752), (80, 1024), (256, 4096)])
def test_transaction_preserves_valid_custom_capacities(pdf_path, keys, tmp_path, monkeypatch, capacities):
    monkeypatch.setattr(sign, "DEFAULT_SIGNATURE_CAPACITIES", capacities)
    output = tmp_path / "custom.pdf"
    invoke(pdf_path, output, keys)
    pair = sign.parse_signature_pair(output.read_bytes())
    assert (pair.ed25519.capacity_bytes, pair.falcon.capacity_bytes) == capacities
    assert verify_file(output, keys.pk_ed, keys.pk_falcon)[0] is True
    assert_clean(tmp_path)


@pytest.mark.skipif(os.name != "nt", reason="Native Windows sharing-mode regression")
def test_windows_open_destination_handle_blocks_replace_without_damage(pdf_path, keys, tmp_path):
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                  wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    output = tmp_path / "locked.pdf"
    output.write_bytes(b"previous destination")
    # GENERIC_READ, FILE_SHARE_READ|FILE_SHARE_WRITE (without FILE_SHARE_DELETE), OPEN_EXISTING.
    handle = kernel.CreateFileW(str(output), 0x80000000, 3, None, 3, 0x80, None)
    assert handle != wintypes.HANDLE(-1).value, ctypes.get_last_error()
    try:
        with pytest.raises(PermissionError):
            invoke(pdf_path, output, keys)
        assert output.read_bytes() == b"previous destination"
        assert_clean(tmp_path)
    finally:
        assert kernel.CloseHandle(handle)


@pytest.mark.parametrize("fault", ["workspace-create", "candidate-create", "fdopen", "short-write", "close"])
def test_additional_io_failures_abort_without_publication(pdf_path, keys, tmp_path, monkeypatch, fault):
    output = tmp_path / "preserved.pdf"
    output.write_bytes(b"previous destination")
    failure = OSError("injected " + fault)
    raw_fds = []

    def fail(*args, **kwargs):
        raise failure

    if fault == "workspace-create":
        monkeypatch.setattr(signing_io.tempfile, "mkdtemp", fail)
    elif fault == "candidate-create":
        monkeypatch.setattr(signing_io.tempfile, "mkstemp", fail)
    elif fault == "fdopen":
        def fail_fdopen(fd, *args, **kwargs):
            raw_fds.append(fd)
            fail()

        monkeypatch.setattr(signing_io.os, "fdopen", fail_fdopen)
    else:
        fdopen = signing_io.os.fdopen

        class BrokenWriter:
            def __init__(self, handle):
                self.handle = handle

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.handle.close()
                if fault == "close":
                    fail()

            def write(self, data):
                return self.handle.write(data[:-1] if fault == "short-write" else data)

            def flush(self):
                self.handle.flush()

            def fileno(self):
                return self.handle.fileno()

        monkeypatch.setattr(signing_io.os, "fdopen", lambda *a, **kw: BrokenWriter(fdopen(*a, **kw)))
    with patch.object(os, "replace") as publish:
        with pytest.raises(OSError):
            invoke(pdf_path, output, keys)
        publish.assert_not_called()
    assert output.read_bytes() == b"previous destination"
    for fd in raw_fds:
        with pytest.raises(OSError):
            os.fstat(fd)
    assert_clean(tmp_path)


def test_key_read_error_preserves_destination_before_staging(pdf_path, keys, tmp_path, monkeypatch):
    output = tmp_path / "preserved.pdf"
    output.write_bytes(b"previous destination")
    original_open = Path.open

    def deny_key(path, *args, **kwargs):
        if path == keys.pk_falcon:
            raise PermissionError("key read denied")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny_key)
    with patch.object(signing_io.tempfile, "mkdtemp") as create:
        with pytest.raises(PermissionError, match="key read denied"):
            invoke(pdf_path, output, keys)
        create.assert_not_called()
    assert output.read_bytes() == b"previous destination"


@pytest.mark.parametrize("primary_error", [False, True])
def test_unowned_workspace_entries_are_never_deleted(pdf_path, keys, tmp_path, monkeypatch, primary_error):
    original_stage = signing_io.SigningTransaction.write_stage
    foreign = []
    failure = RuntimeError("original signing failure")
    output = tmp_path / "preserved.pdf"
    output.write_bytes(b"previous destination")

    def insert_foreign(tx, name, data):
        path = original_stage(tx, name, data)
        if not foreign:
            extra = tx.workspace / "unowned.txt"
            extra.write_bytes(b"do not delete")
            foreign.append(extra)
            if primary_error:
                raise failure
        return path

    monkeypatch.setattr(signing_io.SigningTransaction, "write_stage", insert_foreign)
    with patch.object(os, "replace") as publish:
        with pytest.raises(RuntimeError if primary_error else OSError) as error:
            invoke(pdf_path, output, keys)
        publish.assert_not_called()
    if primary_error:
        assert error.value is failure
        assert any("cleanup failed" in note for note in error.value.__notes__)
    assert foreign[0].read_bytes() == b"do not delete"
    assert list(foreign[0].parent.iterdir()) == foreign
    assert not list(tmp_path.glob(".esign-*.tmp"))
    assert output.read_bytes() == b"previous destination"


def test_cleanup_denial_does_not_mask_primary_failure(pdf_path, keys, tmp_path, monkeypatch):
    stage = signing_io.SigningTransaction.write_stage
    unlink = Path.unlink
    retained = []
    failure = RuntimeError("original failure")

    def fail_after_stage(tx, name, data):
        retained.append(stage(tx, name, data))
        raise failure

    def deny_owned_file(path, *args, **kwargs):
        if path in retained:
            raise PermissionError("injected cleanup denial")
        return unlink(path, *args, **kwargs)

    monkeypatch.setattr(signing_io.SigningTransaction, "write_stage", fail_after_stage)
    monkeypatch.setattr(Path, "unlink", deny_owned_file)
    output = tmp_path / "absent.pdf"
    with pytest.raises(RuntimeError) as error:
        invoke(pdf_path, output, keys)
    assert error.value is failure
    assert any("cleanup denial" in note for note in failure.__notes__)
    assert not output.exists()
    assert retained[0].exists()


def test_stage_creation_is_exclusive_and_cannot_claim_existing_file(tmp_path):
    foreign = None
    with pytest.raises(FileExistsError):
        with signing_io.SigningTransaction(tmp_path / "output.pdf") as tx:
            foreign = tx.workspace / "collision.pdf"
            foreign.write_bytes(b"unowned")
            tx.write_stage("collision.pdf", b"replacement")
    assert foreign.read_bytes() == b"unowned"


@pytest.mark.parametrize("existing", [False, True])
def test_concurrent_destination_change_is_preserved(pdf_path, keys, tmp_path, monkeypatch, existing):
    output = tmp_path / "destination.pdf"
    if existing:
        output.write_bytes(b"previous destination")

    def change_destination(candidate, pk_ed, pk_falcon):
        result = verify_file(candidate, pk_ed, pk_falcon)
        output.write_bytes(b"concurrent destination")
        return result

    monkeypatch.setattr(sign, "verify_file", change_destination)
    with pytest.raises(ValueError) as error:
        invoke(pdf_path, output, keys)
    assert error.value.code == "path.changed"
    assert output.read_bytes() == b"concurrent destination"
    assert_clean(tmp_path)


@pytest.mark.parametrize("protected", ["source", "public-key"])
def test_retargeted_input_paths_are_rechecked_without_symlink_privilege(pdf_path, keys, tmp_path, monkeypatch, protected):
    link = tmp_path / "simulated-link"
    target = pdf_path if protected == "source" else keys.pk_falcon
    later = tmp_path / "new-link-target"
    later.write_bytes(b"new target must survive")
    current_target = [target]
    resolve = Path.resolve

    def simulated_resolve(path, *args, **kwargs):
        return current_target[0] if path == link else resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", simulated_resolve)
    output = tmp_path / "destination.pdf"

    def retarget(candidate, pk_ed, pk_falcon):
        result = verify_file(candidate, pk_ed, pk_falcon)
        current_target[0] = later
        os.link(later, output)
        return result

    monkeypatch.setattr(sign, "verify_file", retarget)
    with pytest.raises(ValueError) as error:
        invoke(link if protected == "source" else pdf_path, output, keys,
               public_key=link if protected == "public-key" else keys.pk_falcon)
    assert error.value.code == "path.alias"
    assert output.read_bytes() == later.read_bytes() == b"new target must survive"
    assert_clean(tmp_path)


def test_detected_candidate_mutation_after_verification_aborts(pdf_path, keys, tmp_path, monkeypatch):
    output = tmp_path / "destination.pdf"
    output.write_bytes(b"previous destination")

    def change_after_verification(candidate, pk_ed, pk_falcon):
        result = verify_file(candidate, pk_ed, pk_falcon)
        assert result[0] is True
        with open(candidate, "ab") as handle:
            handle.write(b"changed after verification")
        return result

    monkeypatch.setattr(sign, "verify_file", change_after_verification)
    with pytest.raises(ValueError) as error:
        invoke(pdf_path, output, keys)
    assert error.value.code == "candidate.changed"
    assert output.read_bytes() == b"previous destination"
    assert_clean(tmp_path)


def test_no_clock_work_after_successful_publication(pdf_path, keys, tmp_path, monkeypatch):
    replace, now = os.replace, sign.time.time
    published = [False]

    def publish(*args):
        replace(*args)
        published[0] = True

    def clock():
        if published[0]:
            raise RuntimeError("fallible clock work after commit")
        return now()

    monkeypatch.setattr(signing_io.os, "replace", publish)
    monkeypatch.setattr(sign.time, "time", clock)
    try:
        result = invoke(pdf_path, tmp_path / "signed.pdf", keys)
        assert len(result) == 11
    finally:
        published[0] = False


@pytest.mark.parametrize("layer", ["ed25519", "falcon"])
def test_cryptographically_invalid_but_size_valid_signatures_cannot_publish(pdf_path, keys, tmp_path, monkeypatch, layer):
    if layer == "ed25519":
        real_key = sign.SigningKey

        def invalid_ed(seed):
            return SimpleNamespace(verify_key=real_key(seed).verify_key,
                                   sign=lambda message: SimpleNamespace(signature=b"\0" * 64))

        monkeypatch.setattr(sign, "SigningKey", invalid_ed)
    else:
        monkeypatch.setattr(sign.falcon_512, "sign", lambda *args: b"\0" * 650)
    output = tmp_path / "destination.pdf"
    output.write_bytes(b"previous destination")
    with pytest.raises(ValueError, match="self-verification"):
        invoke(pdf_path, output, keys)
    assert output.read_bytes() == b"previous destination"
    assert_clean(tmp_path)


def test_no_ed_public_file_discovery_or_fallback(pdf_path, keys, tmp_path, monkeypatch):
    original_public = tmp_path / "trusted-ed.key"
    original_public.write_bytes(keys.pk_ed.read_bytes())
    keys.pk_ed.write_bytes(b"deliberately invalid adjacent public key")
    original_open = Path.open

    def reject_discovery(path, *args, **kwargs):
        if path == keys.pk_ed:
            raise AssertionError("Unexpected Ed25519 public-key filename discovery")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", reject_discovery)
    output = tmp_path / "derived.pdf"
    invoke(pdf_path, output, keys)
    assert verify_file(output, original_public, keys.pk_falcon)[0] is True
    assert_clean(tmp_path)


@pytest.mark.parametrize("filename", [".esign-work-final.pdf", ".esign-candidate-final.tmp", ".ESIGN-WORK-case.tmp"])
def test_temporary_name_patterns_cannot_equal_destination(pdf_path, keys, tmp_path, monkeypatch, filename):
    output = tmp_path / filename
    mkdtemp, mkstemp = signing_io.tempfile.mkdtemp, signing_io.tempfile.mkstemp

    def checked(create, *args, **kwargs):
        # A disjoint prefix excludes even a random name collision with an absent destination.
        assert not os.path.normcase(output.name).startswith(os.path.normcase(kwargs["prefix"]))
        return create(*args, **kwargs)

    monkeypatch.setattr(signing_io.tempfile, "mkdtemp", lambda *a, **kw: checked(mkdtemp, *a, **kw))
    monkeypatch.setattr(signing_io.tempfile, "mkstemp", lambda *a, **kw: checked(mkstemp, *a, **kw))
    invoke(pdf_path, output, keys)
    assert verify_file(output, keys.pk_ed, keys.pk_falcon)[0] is True
    assert set(tmp_path.glob(".esign-*")) - {output} == set()
