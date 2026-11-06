"""Actual Windows/WebView2 results, private native-selection seam and real picker cancellation."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from conftest import make_pdf
from keygen import generate_hybrid_key_pair
from vault import create_vault, unlock_vault
from vault_signing import sign_vault_document


def test_real_windows_valid_tampered_wrong_keys_cancel_and_locked_verification(tmp_path):
    vault, wrong = tmp_path / 'native.hvault', tmp_path / 'wrong.hvault'
    source, signed, tampered = (tmp_path / name for name in ('source.pdf', 'signed.pdf', 'tampered.pdf'))
    source.write_bytes(make_pdf('Actual native verification'))
    create_vault(vault, generate_hybrid_key_pair(), 'disposable verification password')
    create_vault(wrong, generate_hybrid_key_pair(), 'different disposable password')
    with unlock_vault(vault, 'disposable verification password') as handle:
        sign_vault_document(handle, source, signed)
    tampered.write_bytes(signed.read_bytes().replace(b'Actual native verification', b'Actual native modification'))
    with tempfile.TemporaryFile() as log:
        process = subprocess.run([sys.executable, '-B', '-c',
            "import runpy; runpy.run_path('tests/desktop_verification_probe.py', run_name='__main__')"],
            input=json.dumps({'signed': str(signed), 'tampered': str(tampered), 'vault': str(vault),
                             'wrong': str(wrong), 'label': 'disposable'}).encode(),
            stdout=log, stderr=log, timeout=100, cwd=Path(__file__).resolve().parent.parent)
        log.seek(0)
        captured = log.read().decode('utf-8', errors='replace')
    assert process.returncode == 0, captured
    report = json.loads(next(line.removeprefix('VERIFICATION_PROBE=') for line in captured.splitlines() if line.startswith('VERIFICATION_PROBE=')))
    assert report['passed'] and report['lockedPublicVerification'] and report['realNativePickers']
    assert report['results'] == ['valid', 'invalid', 'invalid', 'cancelled']
    assert report['realNativeCancellation'] and report['fileAcceptance'] == 'Python-only GUI-thread seam'
    assert report['inputsUnchanged'] and report['noPasswordPrompt'] and report['ownedThreadsStopped']
