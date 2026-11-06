"""Real Windows WebView2 integration: no substituted renderer or skipped GUI test."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def test_native_windows_shell_bridge_navigation_and_shutdown():
    root = Path(__file__).resolve().parent.parent
    # WebView2 subprocesses can inherit standard handles. File-backed output
    # avoids waiting for pipe EOF from descendants after the GUI owner exits.
    with tempfile.TemporaryFile() as output:
        process = subprocess.run([sys.executable, "-B", "-c",
                                  "import runpy; runpy.run_path('tests/desktop_native_probe.py', run_name='__main__')"],
                                 cwd=root, stdout=output, stderr=output, timeout=45)
        output.seek(0)
        captured = output.read().decode("utf-8", errors="replace")
    assert process.returncode == 0, captured
    line = next(line for line in captured.splitlines() if line.startswith("NATIVE_PROBE="))
    report = json.loads(line.removeprefix("NATIVE_PROBE="))
    assert report["passed"] and report["exitCode"] == 0
    assert report["windowVisible"] and report["ownedThreadsStopped"]
    # Phase 4B.3B adds five verification methods. PDF modules remain lazy until
    # native file selection; an empty shell must not perform PDF operations.
    assert not report["pdfModulesImported"]
    assert set(report["checks"]) == {"desktop_connected", "only_fourteen_allowlisted_methods",
        "correct_metadata_and_capability_flags", "all_five_routes", "light_dark_themes",
        "signing_prerequisites_and_no_password_inputs", "untrusted_navigation_and_popup_blocked",
        "unapproved_raw_messages_ignored"}
