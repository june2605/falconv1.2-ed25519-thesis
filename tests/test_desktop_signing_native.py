"""Real Windows/WebView2 workflow plus independent disk verification."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from conftest import make_pdf


def test_real_windows_signing_and_reopened_original_vault(tmp_path):
    root = Path(__file__).resolve().parent.parent
    source, vault = tmp_path / 'unsigned.pdf', tmp_path / 'desktop.hvault'
    source.write_bytes(make_pdf('Disposable desktop signing evidence'))
    reports = []
    for mode in ('create', 'reopen'):
        with tempfile.TemporaryFile() as log:
            child = subprocess.run([sys.executable, '-B', '-c',
                "import runpy; runpy.run_path('tests/desktop_vault_probe.py', run_name='__main__')"],
                input=json.dumps({'mode': mode, 'path': str(vault), 'password': 'disposable desktop signing password',
                    'signing': True, 'input': str(source), 'output': str(tmp_path / (mode + '-signed.pdf'))}).encode(),
                stdout=log, stderr=log, cwd=root, timeout=90)
            log.seek(0)
            captured = log.read().decode('utf-8', errors='replace')
        assert child.returncode == 0, captured
        line = next(line for line in captured.splitlines() if line.startswith('VAULT_PROBE='))
        report = json.loads(line.removeprefix('VAULT_PROBE='))
        assert report['passed'] and report['ownedThreadsStopped'] and report['shutdownLockedOnWorker']
        assert report['maskedNativePassword'] and report['guiThreadConfirmed'] and report['activeClosePrevented']
        assert all(report['signingEvidence'][key] is True for key in (
            'outputExists', 'sourceUnchanged', 'vaultUnchangedAndEncrypted', 'diskVerifierAccepted',
            'tamperRejected', 'noPrivateKeyFiles', 'selfVerifiedShown'))
        reports.append(report)
    assert reports[0]['public'] == reports[1]['public']
    assert reports[0]['generatedPairs'] == 1 and reports[1]['generatedPairs'] == 0
