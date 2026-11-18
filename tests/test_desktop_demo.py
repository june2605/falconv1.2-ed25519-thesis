"""Disposable real desktop journey; passwords use stdin memory, never argv/env."""
import hashlib
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile

import pytest

from keygen import generate_hybrid_key_pair
from vault import create_vault
from vault_io import lock_file_path


ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / 'demo_assets' / 'sample-unsigned.pdf'


class _Controls(dict):
    def __repr__(self):
        return '<disposable desktop controls: redacted>'


def test_public_demo_pdf_has_reproducible_ascii_content_and_correct_xref():
    data = SAMPLE.read_bytes()
    assert data.isascii() and data.startswith(b'%PDF-1.4\n')
    assert data.count(b'APPROVED') == 1
    assert len(b'APPROVED') == len(b'REJECTED')
    offset = int(re.search(rb'startxref\n(\d+)\n%%EOF\n$', data)[1])
    assert data[offset:].startswith(b'xref\n0 6\n0000000000 65535 f \n')
    entries = data[offset:].splitlines()[3:8]
    for number, entry in enumerate(entries, 1):
        assert data[int(entry[:10]):].startswith(f'{number} 0 obj\n'.encode())
    stream = re.search(rb'/Length (\d+) >>\nstream\n(.*?)endstream', data, re.S)
    assert len(stream[2]) == int(stream[1])


def _run(control):
    with tempfile.TemporaryFile() as output:
        try:
            completed = subprocess.run([sys.executable, '-B', '-c',
                "import runpy; runpy.run_path('tests/desktop_demo_probe.py', run_name='__main__')"],
                input=json.dumps(control).encode(), stdout=output, stderr=output,
                cwd=ROOT, timeout=150)
        except subprocess.TimeoutExpired as error:
            output.seek(0)
            pytest.fail(f'{error}\n{output.read().decode("utf-8", errors="replace")}', pytrace=False)
        output.seek(0)
        captured = output.read().decode('utf-8', errors='replace')
    assert completed.returncode == 0, captured
    report = json.loads(next(line.removeprefix('DEMO_PROBE=') for line in captured.splitlines() if line.startswith('DEMO_PROBE=')))
    assert report['passed'] and report['ownedThreadsStopped']
    assert report['nativePasswordsMasked'] and report['nativeDialogsAccepted']
    assert report['noPlaintextKeyWrites'] and report['workerOwnership']
    return report


def test_real_desktop_create_sign_verify_tamper_lock_and_restart(tmp_path, interactive_desktop):
    source, output, tampered, corrupted = (tmp_path / name for name in ('sample-unsigned.pdf', 'signed.pdf', 'tampered.pdf', 'corrupted.pdf'))
    vault, wrong, invalid = (tmp_path / name for name in ('demo.hvault', 'other.hvault', 'invalid.hvault'))
    source.write_bytes(SAMPLE.read_bytes())
    output.write_bytes(SAMPLE.read_bytes())  # Owned predecessor tests real overwrite No/Yes.
    corrupted.write_bytes(b'%PDF-1.4\ninvalid unsigned envelope\n')
    create_vault(wrong, generate_hybrid_key_pair(), secrets.token_urlsafe(24))
    create_vault(invalid, generate_hybrid_key_pair(), secrets.token_urlsafe(24))
    damaged = bytearray(invalid.read_bytes()); damaged[0] ^= 1; invalid.write_bytes(damaged)
    controls = {'source': str(source), 'output': str(output), 'tampered': str(tampered), 'corrupted': str(corrupted),
                'vault': str(vault), 'wrong': str(wrong), 'invalid': str(invalid),
                'password': secrets.token_urlsafe(24)}
    initial = hashlib.sha256(source.read_bytes()).hexdigest()
    before = set(tmp_path.iterdir())
    protected = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (source, wrong, invalid)}
    first = _run(_Controls({**controls, 'mode': 'create'}))
    second = _run(_Controls({**controls, 'mode': 'reopen'}))
    assert first['generatedPairs'] == 1 and second['generatedPairs'] == 0
    assert first['hybridKeyId'] == second['hybridKeyId']
    assert first['publicKeySha256'] == second['publicKeySha256'] and second['originalSignatureStillValid']
    assert first['validSignedOnDisk'] and first['tamperRejected']
    assert first['lockedPublicVerification'] and second['lockedOnRestart']
    assert first['wrongPasswordRetry'] and first['cancelledDialogsPreservedState']
    assert first['existingOutputPreservedOnCancel'] and first['overwriteConfirmed']
    assert first['oneSigningOperation'] and first['lockDuringSigningRejected']
    assert first['activeCloseRefused'] and first['noStaleValid']
    assert first['noStaleSigningSuccess']
    assert first['wrongKeysRejected'] and first['invalidVaultRejected']
    assert first['corruptedPdfRejected'] and first['staleSessionRejected']
    assert first['files']['vaultSha256'] == second['vaultSha256']
    assert set(tmp_path.iterdir()) - before == {vault, tampered, lock_file_path(vault)}
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in protected.items())
    assert hashlib.sha256(source.read_bytes()).hexdigest() == initial
    assert vault.stat().st_size == 2416 and output.exists() and tampered.exists()
