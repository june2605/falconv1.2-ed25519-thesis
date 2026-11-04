"""Execute the actual app verification branch with simulated Streamlit controls."""

import io
from pathlib import Path
import runpy
import sys
from unittest.mock import MagicMock

import pytest

from verify import verify_file


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


@pytest.mark.parametrize("valid", [False, True], ids=["reject-invalid-tuple", "accept-valid-tuple"])
def test_app_uses_validity_boolean_instead_of_tuple_truthiness(
    signed_pdf, keys, monkeypatch, tmp_path, valid,
):
    data = signed_pdf.read_bytes()
    if not valid:
        data = data.replace(b"Phase 1", b"phase 1", 1)
        signed_pdf.write_bytes(data)
    result = verify_file(signed_pdf, keys.pk_ed, keys.pk_falcon)
    assert result[0] is valid
    assert bool(result) is True  # Demonstrates why the inherited `if tuple` fails.

    st = MagicMock(name="streamlit")
    # app.py checks membership as well as attributes on Streamlit session state.
    st.session_state.__contains__.return_value = True
    st.session_state.menu = "XÁC THỰC TÀI LIỆU"
    st.button.side_effect = lambda label, **kwargs: label == "TIẾN HÀNH XÁC THỰC"
    st.columns.return_value = [st, st]
    st.file_uploader.side_effect = [
        io.BytesIO(data), io.BytesIO(keys.pk_ed.read_bytes()),
        io.BytesIO(keys.pk_falcon.read_bytes()),
    ]
    monkeypatch.setitem(sys.modules, "streamlit", st)
    monkeypatch.chdir(tmp_path)
    # Isolate the application's own temporary files from other users' files.
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    runpy.run_path(str(APP_PATH), run_name="__phase1_ui_test__")

    if valid:
        st.error.assert_not_called()
        st.success.assert_called_once()
        st.balloons.assert_called_once()
    else:
        st.success.assert_not_called()
        st.balloons.assert_not_called()
        st.error.assert_called_once()
        assert "KHÔNG HỢP LỆ" in st.error.call_args.args[0]
