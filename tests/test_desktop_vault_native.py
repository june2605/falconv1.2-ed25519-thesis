"""Two real Windows desktop processes; test credentials use stdin, never argv/env."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def test_real_native_password_and_vault_reopen_across_processes(tmp_path, interactive_desktop):
    root = Path(__file__).resolve().parent.parent
    path = tmp_path / "native-test.hvault"
    reports = []
    for mode in ["create", "reopen"]:
        with tempfile.TemporaryFile() as output:
            completed = subprocess.run([sys.executable, "-B", "-c",
                "import runpy; runpy.run_path('tests/desktop_vault_probe.py', run_name='__main__')"],
                input=json.dumps({"mode": mode, "path": str(path), "password": "native test-only vault password 123"}).encode(),
                stdout=output, stderr=output, cwd=root, timeout=60)
            output.seek(0)
            captured = output.read().decode("utf-8", errors="replace")
        assert completed.returncode == 0, captured
        line = next(item for item in captured.splitlines() if item.startswith("VAULT_PROBE="))
        report = json.loads(line.removeprefix("VAULT_PROBE="))
        assert report["passed"] and report["maskedNativePassword"]
        assert report["guiThreadConfirmed"] and report["shutdownLockedOnWorker"]
        assert report["ownedThreadsStopped"] and report["noSecretBridgeOrDiskWrites"]
        assert report["nativeExplicitLockAndStaleRejection"]
        reports.append(report)
    first, second = reports
    assert first["public"] == second["public"]
    assert first["generatedPairs"] == 1 and second["generatedPairs"] == 0
    assert first["nativeFileDialogsCancelled"] is True
    assert first["authenticationUx"] is True
    assert path.stat().st_size == 2416
