"""Run real Streamlit branches with disposable uploads and injected failures."""

import builtins
import base64
import io
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
from unittest.mock import MagicMock

import pytest

import keygen
import sign
import verify


APP = Path(__file__).resolve().parents[1] / "app.py"
SIGN_MENU, SIGN_BUTTON = "KÝ SỐ TÀI LIỆU", "THỰC HIỆN KÝ SỐ HYBRID"
VERIFY_MENU, VERIFY_BUTTON = "XÁC THỰC TÀI LIỆU", "TIẾN HÀNH XÁC THỰC"
KEY_MENU, KEY_BUTTON = "QUẢN LÝ KHÓA", "BẮT ĐẦU TẠO BỘ KHÓA MỚI"


def upload(data, name="document.pdf"):
    value = io.BytesIO(data)
    value.name = name
    return value


@pytest.fixture
def ui(monkeypatch, tmp_path):
    temp_root = tmp_path / "ui-temporary"
    temp_root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp_root))
    monkeypatch.chdir(tmp_path)

    def execute(menu, uploads=(), *, configure=None):
        st = MagicMock(name="streamlit")
        st.session_state.__contains__.return_value = True
        st.session_state.menu = menu
        selected = {SIGN_MENU: SIGN_BUTTON, VERIFY_MENU: VERIFY_BUTTON, KEY_MENU: KEY_BUTTON}[menu]
        st.button.side_effect = lambda label, **kwargs: label == selected
        st.columns.return_value = [st, st]
        st.file_uploader.side_effect = uploads
        if configure:
            configure(st)
        monkeypatch.setitem(sys.modules, "streamlit", st)
        runpy.run_path(str(APP), run_name="__phase2b4b3_ui_test__")
        return st

    return execute, temp_root


def signing_uploads(pdf_path, keys):
    return [upload(pdf_path.read_bytes()), upload(keys.sk_ed.read_bytes()),
            upload(keys.sk_falcon.read_bytes()), upload(keys.pk_falcon.read_bytes())]


def verification_uploads(signed_pdf, keys):
    return [upload(signed_pdf.read_bytes()), upload(keys.pk_ed.read_bytes()),
            upload(keys.pk_falcon.read_bytes())]


def assert_no_download(st):
    st.download_button.assert_not_called()
    st.success.assert_not_called()


def test_ui_verifier_exception_cleans_all_uploads(ui, signed_pdf, keys, monkeypatch):
    execute, temporary = ui

    def fail(*args):
        raise OSError("injected verification error")

    monkeypatch.setattr(verify, "verify_file", fail)
    st = execute(VERIFY_MENU, verification_uploads(signed_pdf, keys))
    st.error.assert_called_once()
    assert_no_download(st)
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("kind", ["empty", "text", "truncated-header"])
def test_ui_rejects_obviously_invalid_pdf_before_signing(ui, pdf_path, keys, monkeypatch, kind):
    execute, temporary = ui
    uploads = signing_uploads(pdf_path, keys)
    uploads[0] = upload({"empty": b"", "text": b"ordinary text", "truncated-header": b"%PDF-"}[kind])
    signer = MagicMock()
    monkeypatch.setattr(sign, "sign_file", signer)
    st = execute(SIGN_MENU, uploads)
    assert_no_download(st)
    st.error.assert_called_once()
    signer.assert_not_called()
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("kind", ["partial", "tampered"])
def test_ui_never_offers_unverified_signer_output(ui, pdf_path, keys, monkeypatch, kind):
    execute, temporary = ui
    real_sign = sign.sign_file

    def bad_output(source, output, sk_ed, sk_falcon, *, pk_falcon):
        if kind == "partial":
            Path(output).write_bytes(b"%PDF-1.4\nincomplete signed output")
            return (output,) + (0,) * 10
        result = real_sign(source, output, sk_ed, sk_falcon, pk_falcon=pk_falcon)
        data = Path(output).read_bytes()
        Path(output).write_bytes(data.replace(b"Phase 1", b"phase 1", 1))
        return result

    monkeypatch.setattr(sign, "sign_file", bad_output)
    st = execute(SIGN_MENU, signing_uploads(pdf_path, keys))
    assert_no_download(st)
    st.error.assert_called_once()
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("menu", [SIGN_MENU, VERIFY_MENU])
@pytest.mark.parametrize("fault", ["create", "upload-read", "write", "operation", "permission", "success-ui", "download-ui"])
def test_ui_ordinary_failures_leave_no_upload_artifacts(ui, pdf_path, signed_pdf, keys, monkeypatch, menu, fault):
    execute, temporary = ui
    uploads = signing_uploads(pdf_path, keys) if menu == SIGN_MENU else verification_uploads(signed_pdf, keys)
    error_type = PermissionError if fault == "permission" else OSError

    def fail(*args, **kwargs):
        raise error_type("injected operation failure")

    if fault == "create":
        monkeypatch.setattr(tempfile, "mkdtemp", fail)
        monkeypatch.setattr(tempfile, "NamedTemporaryFile", fail)
    elif fault == "upload-read":
        uploads[2].getvalue = fail
    elif fault == "write":
        original = Path.write_bytes

        def fail_after_write(path, data):
            result = original(path, data)
            if temporary in path.parents:
                fail()
            return result

        monkeypatch.setattr(Path, "write_bytes", fail_after_write)
    elif fault in ("operation", "permission"):
        monkeypatch.setattr(sign if menu == SIGN_MENU else verify,
                            "sign_file" if menu == SIGN_MENU else "verify_file", fail)

    def configure(st):
        if fault == "success-ui":
            st.success.side_effect = fail
        elif fault == "download-ui":
            # Verification has no download; inject its result animation instead.
            (st.download_button if menu == SIGN_MENU else st.balloons).side_effect = fail

    st = execute(menu, uploads, configure=configure)
    st.error.assert_called_once()
    if fault not in ("success-ui", "download-ui"):
        assert_no_download(st)
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("menu,index", [(SIGN_MENU, i) for i in range(4)] + [(VERIFY_MENU, i) for i in range(3)])
def test_missing_uploads_do_not_create_temporary_files(ui, pdf_path, signed_pdf, keys, menu, index):
    execute, temporary = ui
    uploads = signing_uploads(pdf_path, keys) if menu == SIGN_MENU else verification_uploads(signed_pdf, keys)
    uploads[index] = None
    st = execute(menu, uploads)
    assert_no_download(st)
    if index:
        st.warning.assert_called_once()
    assert list(temporary.iterdir()) == []


def test_key_generation_downloads_closed_bytes_and_complete_ui_workflow(ui, pdf_path, tmp_path):
    execute, temporary = ui
    generated = {}

    def capture_keys(st):
        def download(label, data, filename=None, **kwargs):
            assert isinstance(data, bytes), "Download must not receive an open key handle"
            assert list(temporary.iterdir()) == []
            generated[filename] = data

        st.download_button.side_effect = download

    key_ui = execute(KEY_MENU, configure=capture_keys)
    key_ui.error.assert_not_called()
    assert len(generated) == 4
    signing = execute(SIGN_MENU, [upload(pdf_path.read_bytes()), upload(generated["ed25519_priv.key"]),
                                 upload(generated["falcon_priv.key"]), upload(generated["falcon_pub.key"])])
    signing.error.assert_not_called()
    signed = signing.download_button.call_args.args[1]
    public = [upload(generated["ed25519_pub.key"]), upload(generated["falcon_pub.key"])]
    valid = execute(VERIFY_MENU, [upload(signed)] + public)
    valid.success.assert_called_once()
    valid.error.assert_not_called()
    altered = signed.replace(b"Phase 1", b"phase 1", 1)
    assert altered != signed
    invalid = execute(VERIFY_MENU, [upload(altered)] + public)
    invalid.success.assert_not_called()
    invalid.error.assert_called_once()
    assert "KHÔNG HỢP LỆ" in invalid.error.call_args.args[0]
    assert list(temporary.iterdir()) == []


def test_key_generation_permission_error_is_reported_without_deleting_existing_keys(ui, keys, tmp_path, monkeypatch):
    execute, temporary = ui
    names = ("ed25519_pub.key", "ed25519_priv.key", "falcon_pub.key", "falcon_priv.key")
    data = [getattr(keys, name).read_bytes() for name in ("pk_ed", "sk_ed", "pk_falcon", "sk_falcon")]
    for name, content in zip(names, data):
        (tmp_path / name).write_bytes(content)

    def denied(*args):
        raise PermissionError("injected key generation permission error")

    monkeypatch.setattr(keygen, "generate_keys", denied)
    st = execute(KEY_MENU)
    st.error.assert_called_once()
    assert_no_download(st)
    assert [(tmp_path / name).read_bytes() for name in names] == data
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("menu", [SIGN_MENU, VERIFY_MENU])
@pytest.mark.parametrize("operation_fails", [False, True])
def test_transient_upload_cleanup_failure_is_retried_without_leaks(ui, pdf_path, signed_pdf, keys, monkeypatch, menu, operation_fails):
    execute, temporary = ui
    cleanup = tempfile.TemporaryDirectory.cleanup
    attempts = []

    def transient(directory):
        if Path(directory.name).parent == temporary:
            attempts.append(directory.name)
            if len(attempts) == 1:
                raise PermissionError("transient sharing violation")
        return cleanup(directory)

    monkeypatch.setattr(tempfile.TemporaryDirectory, "cleanup", transient)
    if operation_fails:
        def fail(*args, **kwargs):
            raise RuntimeError("primary operation error")

        monkeypatch.setattr(sign if menu == SIGN_MENU else verify,
                            "sign_file" if menu == SIGN_MENU else "verify_file", fail)
    uploads = signing_uploads(pdf_path, keys) if menu == SIGN_MENU else verification_uploads(signed_pdf, keys)
    st = execute(menu, uploads)
    assert len(attempts) == 2
    if operation_fails:
        st.error.assert_called_once()
        assert_no_download(st)
    else:
        st.error.assert_not_called()
        st.success.assert_called_once()
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("name", ["ed25519-private.key", "falcon-private.key", "falcon-public.key", "download.pdf", "ed25519-public.key"])
def test_late_upload_write_errors_remove_private_keys(ui, pdf_path, keys, monkeypatch, name):
    execute, temporary = ui
    original = Path.write_bytes
    visited = []

    def fail_after_write(path, data):
        result = original(path, data)
        if temporary in path.parents:
            visited.append(path.name)
            if path.name == name:
                raise OSError("late write failure")
        return result

    monkeypatch.setattr(Path, "write_bytes", fail_after_write)
    st = execute(SIGN_MENU, signing_uploads(pdf_path, keys))
    assert name in visited
    assert_no_download(st)
    st.error.assert_called_once()
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("failure", ["false", "nonboolean", "exception"])
def test_download_verification_failure_cleans_private_uploads(ui, pdf_path, keys, monkeypatch, failure):
    execute, temporary = ui
    calls = []

    def fail(candidate, pk_ed, pk_falcon):
        calls.append(Path(candidate))
        assert Path(candidate).name == "download.pdf"
        assert list(temporary.rglob("falcon-private.key"))
        if failure == "exception":
            raise OSError("download verification failure")
        return (False if failure == "false" else 1,) + (0,) * 10

    monkeypatch.setattr(verify, "verify_file", fail)
    st = execute(SIGN_MENU, signing_uploads(pdf_path, keys))
    assert len(calls) == 1
    assert_no_download(st)
    st.error.assert_called_once()
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("kind", ["wrong-ed", "wrong-falcon", "malformed", "truncated", "appended", "padding", "empty-public"])
def test_ui_rejects_wrong_keys_and_malformed_signatures(ui, signed_pdf, keys, key_factory, kind):
    execute, temporary = ui
    uploads = verification_uploads(signed_pdf, keys)
    data = signed_pdf.read_bytes()
    if kind.startswith("wrong-"):
        other = key_factory()
        uploads[1 if kind == "wrong-ed" else 2] = upload(
            (other.pk_ed if kind == "wrong-ed" else other.pk_falcon).read_bytes())
    elif kind == "empty-public":
        uploads[2] = upload(b"")
    else:
        if kind == "malformed":
            data = data.replace(b"SigLength:", b"BadLength:", 1)
        elif kind == "truncated":
            data = data[:-1]
        elif kind == "appended":
            data += b"\n"
        else:
            from utils import parse_signature_pair
            position = parse_signature_pair(data).falcon.contents_end - 1
            assert data[position:position + 1] == b"0"
            data = data[:position] + b"1" + data[position + 1:]
        uploads[0] = upload(data)
    st = execute(VERIFY_MENU, uploads)
    assert_no_download(st)
    st.error.assert_called_once()
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("index", [1, 2, 3])
def test_empty_signing_key_uploads_are_rejected_without_disk_copies(ui, pdf_path, keys, index):
    execute, temporary = ui
    uploads = signing_uploads(pdf_path, keys)
    uploads[index] = upload(b"")
    st = execute(SIGN_MENU, uploads)
    assert_no_download(st)
    st.error.assert_called_once()
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("menu", [SIGN_MENU, VERIFY_MENU])
def test_exception_details_are_not_echoed_to_ui(ui, pdf_path, signed_pdf, keys, monkeypatch, menu):
    execute, temporary = ui
    secret = "uploaded-private-material-must-not-be-rendered"

    def fail(*args, **kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(sign if menu == SIGN_MENU else verify,
                        "sign_file" if menu == SIGN_MENU else "verify_file", fail)
    uploads = signing_uploads(pdf_path, keys) if menu == SIGN_MENU else verification_uploads(signed_pdf, keys)
    st = execute(menu, uploads)
    st.error.assert_called_once()
    assert secret not in str(st.error.call_args)
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("primary", [False, True])
def test_permanent_cleanup_denial_is_visible_and_never_allows_signed_download(ui, pdf_path, keys, monkeypatch, primary):
    execute, temporary = ui
    cleanup = tempfile.TemporaryDirectory.cleanup
    directories = []

    def denied(directory):
        if Path(directory.name).parent == temporary:
            # Simulate OS refusal even on the finalizer path; recover explicitly
            # once the injected denial ends, without touching unrelated files.
            directory._finalizer.detach()
            directories.append(directory)
            raise PermissionError("injected persistent cleanup denial")
        return cleanup(directory)

    def sign_failure(*args, **kwargs):
        raise RuntimeError("primary signing failure")

    monkeypatch.setattr(tempfile.TemporaryDirectory, "cleanup", denied)
    if primary:
        monkeypatch.setattr(sign, "sign_file", sign_failure)
    try:
        st = execute(SIGN_MENU, signing_uploads(pdf_path, keys))
        assert len(directories) == 2
        st.error.assert_called_once()
        st.warning.assert_called_once()
        assert_no_download(st)
        assert str(directories[0].name) in st.warning.call_args.args[0]
        assert list(temporary.rglob("ed25519-private.key"))
        assert list(temporary.rglob("falcon-private.key"))
    finally:
        for directory in directories:
            cleanup(directory)
    assert list(temporary.iterdir()) == []


def test_windows_sensitive_handles_are_closed_before_operations_and_rendering(ui, pdf_path, signed_pdf, keys, tmp_path, monkeypatch):
    execute, temporary = ui
    handles = []
    real_builtin, real_io, real_fdopen = builtins.open, io.open, os.fdopen
    real_sign, real_verify = sign.sign_file, verify.verify_file
    real_replace, real_unlink, real_rmdir = os.replace, os.unlink, os.rmdir

    def record(opener, file, *args, **kwargs):
        handle = opener(file, *args, **kwargs)
        if isinstance(file, (str, os.PathLike)) and Path(file).absolute().is_relative_to(tmp_path):
            handles.append(handle)
        return handle

    def closed():
        assert handles and all(handle.closed for handle in handles)

    def record_fd(fd, *args, **kwargs):
        handle = real_fdopen(fd, *args, **kwargs)
        handles.append(handle)
        return handle

    def sign_closed(*args, **kwargs):
        closed()
        return real_sign(*args, **kwargs)

    def verify_closed(*args, **kwargs):
        closed()
        return real_verify(*args, **kwargs)

    def filesystem_operation(operation, *args, **kwargs):
        closed()
        return operation(*args, **kwargs)

    def configure(st):
        def download(label, data, *args, **kwargs):
            closed()
            assert isinstance(data, bytes)
            assert list(temporary.iterdir()) == []

        st.download_button.side_effect = download

    monkeypatch.setattr(builtins, "open", lambda *a, **kw: record(real_builtin, *a, **kw))
    monkeypatch.setattr(io, "open", lambda *a, **kw: record(real_io, *a, **kw))
    monkeypatch.setattr(os, "fdopen", record_fd)
    monkeypatch.setattr(sign, "sign_file", sign_closed)
    monkeypatch.setattr(sign, "verify_file", verify_closed)
    monkeypatch.setattr(verify, "verify_file", verify_closed)
    monkeypatch.setattr(os, "replace", lambda *a, **kw: filesystem_operation(real_replace, *a, **kw))
    monkeypatch.setattr(os, "unlink", lambda *a, **kw: filesystem_operation(real_unlink, *a, **kw))
    monkeypatch.setattr(os, "rmdir", lambda *a, **kw: filesystem_operation(real_rmdir, *a, **kw))
    for menu, uploads in ((SIGN_MENU, signing_uploads(pdf_path, keys)),
                          (VERIFY_MENU, verification_uploads(signed_pdf, keys)),
                          (KEY_MENU, ())):
        st = execute(menu, uploads, configure=configure)
        st.error.assert_not_called()
    closed()
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("layer", ["ed25519", "falcon"])
def test_real_backend_crypto_failure_removes_private_uploads(ui, pdf_path, keys, monkeypatch, layer):
    execute, temporary = ui
    reached = []

    def fail(*args, **kwargs):
        assert list(temporary.rglob("ed25519-private.key"))
        assert list(temporary.rglob("falcon-private.key"))
        reached.append(layer)
        raise OSError("injected native signing failure")

    if layer == "ed25519":
        monkeypatch.setattr(sign.SigningKey, "sign", fail)
    else:
        monkeypatch.setattr(sign.falcon_512, "sign", fail)
    st = execute(SIGN_MENU, signing_uploads(pdf_path, keys))
    assert reached == [layer]
    assert_no_download(st)
    st.error.assert_called_once()
    assert list(temporary.iterdir()) == []


def test_download_read_error_removes_private_uploads(ui, pdf_path, keys, monkeypatch):
    execute, temporary = ui
    read = Path.read_bytes

    def denied(path):
        if path.name == "signed.pdf" and temporary in path.parents:
            raise PermissionError("injected candidate read denial")
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", denied)
    st = execute(SIGN_MENU, signing_uploads(pdf_path, keys))
    assert_no_download(st)
    st.error.assert_called_once()
    assert list(temporary.iterdir()) == []


def test_backend_cleanup_diagnostics_are_visible_without_exception_contents(ui, pdf_path, keys, monkeypatch):
    execute, temporary = ui

    def fail(*args, **kwargs):
        error = RuntimeError("do not render this secret detail")
        error.add_note("Signing temporary-file cleanup failed: do not render this secret detail")
        raise error

    monkeypatch.setattr(sign, "sign_file", fail)
    st = execute(SIGN_MENU, signing_uploads(pdf_path, keys))
    st.error.assert_called_once()
    st.warning.assert_called_once()
    assert "secret detail" not in str(st.error.call_args) + str(st.warning.call_args)
    assert_no_download(st)
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("menu", [SIGN_MENU, VERIFY_MENU])
def test_error_widget_failure_cannot_prevent_upload_cleanup(ui, pdf_path, signed_pdf, keys, monkeypatch, menu):
    execute, temporary = ui

    def fail(*args, **kwargs):
        raise RuntimeError("operation failure")

    def configure(st):
        st.error.side_effect = OSError("error widget unavailable")

    monkeypatch.setattr(sign if menu == SIGN_MENU else verify,
                        "sign_file" if menu == SIGN_MENU else "verify_file", fail)
    uploads = signing_uploads(pdf_path, keys) if menu == SIGN_MENU else verification_uploads(signed_pdf, keys)
    with pytest.raises(OSError, match="error widget unavailable"):
        execute(menu, uploads, configure=configure)
    assert list(temporary.iterdir()) == []


_FROZEN_CASES = json.loads((APP.parent / "tests/fixtures/phase1-signatures.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", _FROZEN_CASES, ids=lambda case: case["name"])
def test_ui_accepts_frozen_phase1_signatures(ui, case):
    execute, temporary = ui
    fields = ("pdf_base64", "ed25519_public_base64", "falcon_public_base64")
    uploads = [upload(base64.b64decode(case[field], validate=True)) for field in fields]
    st = execute(VERIFY_MENU, uploads)
    st.error.assert_not_called()
    st.success.assert_called_once()
    assert list(temporary.iterdir()) == []
