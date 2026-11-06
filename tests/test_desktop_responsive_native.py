"""Native window state/resizing checks; no production API or engine changes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from conftest import make_pdf
from keygen import generate_hybrid_key_pair
from vault import create_vault, unlock_vault
from vault_signing import sign_vault_document


def test_real_webview_default_maximized_restored_and_minimum(tmp_path):
    vault, wrong = tmp_path / 'responsive.hvault', tmp_path / 'wrong.hvault'
    source, signed, tampered = (tmp_path / name for name in ('source.pdf', 'signed.pdf', 'tampered.pdf'))
    source.write_bytes(make_pdf('Responsive native verification'))
    create_vault(vault, generate_hybrid_key_pair(), 'disposable responsive test password')
    create_vault(wrong, generate_hybrid_key_pair(), 'different disposable test password')
    with unlock_vault(vault, 'disposable responsive test password') as handle:
        sign_vault_document(handle, source, signed)
    tampered.write_bytes(signed.read_bytes().replace(b'Responsive native verification', b'Responsive native modification'))
    with tempfile.TemporaryFile() as output:
        process = subprocess.run([sys.executable, '-B', '-c',
            "import runpy; runpy.run_path('tests/desktop_verification_probe.py', run_name='__main__')"],
            input=json.dumps({'signed': str(signed), 'tampered': str(tampered), 'vault': str(vault), 'wrong': str(wrong),
                              'label': 'responsive', 'responsive': True, 'sidebar': True, 'interactions': True}).encode(),
            stdout=output, stderr=output, timeout=100, cwd=Path(__file__).resolve().parent.parent)
        output.seek(0)
        captured = output.read().decode('utf-8', errors='replace')
    assert process.returncode == 0, captured
    report = json.loads(next(line.removeprefix('VERIFICATION_PROBE=') for line in captured.splitlines() if line.startswith('VERIFICATION_PROBE=')))
    assert set(report['responsive']) == {'default', 'maximized', 'restored', 'minimum'}
    assert all(row['noOverflow'] and row['footerSafe'] and row['resultPreserved'] and row['focusVisible'] for row in report['responsive'].values())
    assert report['responsive']['minimum']['sidebarCollapsed'] is True
    assert report['responsive']['minimum']['columns'] == 1
    assert set(report['sidebar']) == {'default', 'maximized', 'restored', 'minimum'}
    assert all(row['manualSpaceReserved'] and row['hoverSpaceReserved'] and row['resultPreserved'] for row in report['sidebar'].values())
    assert all(row['docked'] is False for row in report['sidebar'].values())
    assert all(row['navigationHeldOpen'] and row['reentryCancelled'] and row['autoInside'] and row['autoOutside']
               and row['idStable'] and row['fullIdExact'] for row in report['sidebar'].values())
    assert report['sidebar']['maximized']['unpinInside'] is True
    assert report['sidebar']['maximized']['unpinOutside'] is True
    assert report['passed'] and report['inputsUnchanged'] and report['ownedThreadsStopped']
