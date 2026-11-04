"""Execute signing callers with disposable uploads and a one-run demo dataset."""

import io
from pathlib import Path
import runpy
import sys
import tempfile
from unittest.mock import MagicMock

import pytest

from verify import verify_file


@pytest.mark.parametrize("public_key", ["correct", "incorrect", "missing"])
def test_app_signing_requires_and_passes_falcon_public_key(pdf_path, keys, key_factory, tmp_path, monkeypatch, public_key):
    upload = io.BytesIO(pdf_path.read_bytes())
    upload.name = "upload.pdf"
    public = None if public_key == "missing" else io.BytesIO(
        (keys if public_key == "correct" else key_factory()).pk_falcon.read_bytes())
    st = MagicMock(name="streamlit")
    st.session_state.__contains__.return_value = True
    st.session_state.menu = "KÝ SỐ TÀI LIỆU"
    st.button.side_effect = lambda label, **kwargs: label == "THỰC HIỆN KÝ SỐ HYBRID"
    st.columns.return_value = [st, st]
    st.file_uploader.side_effect = [upload, io.BytesIO(keys.sk_ed.read_bytes()),
                                    io.BytesIO(keys.sk_falcon.read_bytes()), public]
    monkeypatch.setitem(sys.modules, "streamlit", st)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    before = set(tmp_path.iterdir())
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.py"), run_name="__signing_ui_test__")
    assert set(tmp_path.iterdir()) == before  # Uploads and outputs cleaned on success and failure.
    if public_key == "correct":
        st.error.assert_not_called()
        st.success.assert_called_once()
        st.download_button.assert_called_once()
        signed = tmp_path / "download.pdf"
        signed.write_bytes(st.download_button.call_args.args[1])
        assert verify_file(signed, keys.pk_ed, keys.pk_falcon)[0] is True
    else:
        st.success.assert_not_called()
        st.download_button.assert_not_called()
        (st.warning if public_key == "missing" else st.error).assert_called_once()


def test_demo_passes_explicit_falcon_public_key(pdf_path, tmp_path, monkeypatch):
    import demo

    for name in ("data_test", "key", "benchmark"):
        (tmp_path / name).mkdir()
    (tmp_path / "data_test/file_test_1mb.pdf").write_bytes(pdf_path.read_bytes())
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(demo, "range", lambda count: range(1), raising=False)
    monkeypatch.setattr(demo, "sign_results", [])
    monkeypatch.setattr(demo, "verify_results", [])
    demo.main()
    assert len(demo.sign_results) == len(demo.verify_results) == 1
    assert demo.verify_results[0]["ok"] is True
