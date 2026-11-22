"""Reject changes between approval, staging, and installer compilation."""
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = runpy.run_path(str(ROOT / 'packaging/build-installer.py'))


@pytest.fixture
def payload(tmp_path):
    source = tmp_path / 'portable'
    source.mkdir()
    data = b'approved payload bytes'
    (source / 'HybridSign.exe').write_bytes(data)
    records = [{'file': 'HybridSign.exe', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}]
    return source, {'files': records, 'fileCount': 1, 'totalBytes': len(data)}


@pytest.mark.parametrize('fault', ['extra', 'changed', 'missing', 'hardlink'])
def test_build_rejects_unapproved_payload(payload, tmp_path, fault):
    source, manifest = payload
    exe = source / 'HybridSign.exe'
    if fault == 'extra':
        (source / 'user.hvault').write_bytes(b'private fixture')
    elif fault == 'changed':
        exe.write_bytes(b'X' + exe.read_bytes()[1:])
    elif fault == 'missing':
        exe.rename(tmp_path / 'excluded.exe')
    else:
        (tmp_path / 'alias.exe').hardlink_to(exe)
    with pytest.raises(ValueError, match='payload entry|differ from|incomplete'):
        BUILDER['validate_payload'](source, manifest)


def test_staging_rechecks_bytes_before_writing_inno_entries(payload, tmp_path):
    source, manifest = payload
    records = BUILDER['validate_payload'](source, manifest)
    exe = source / 'HybridSign.exe'
    exe.write_bytes(b'Replaced after approval check')
    stage = tmp_path / 'stage'
    with pytest.raises(ValueError, match='changed while staging'):
        BUILDER['write_includes'](stage, source, records)
    assert not (stage / 'files.iss').exists()


def test_candidate_uses_only_its_reviewed_adjacent_manifest(payload):
    source, inventory = payload
    data = json.dumps(inventory).encode()
    manifest = source.with_suffix('.manifest.json')
    manifest.write_bytes(data)
    pin = hashlib.sha256(data).hexdigest()

    approval = BUILDER['read_approval'](source, pin)

    assert approval == data
    assert BUILDER['validate_payload'](source, json.loads(approval)) == inventory['files']
    manifest.write_bytes(data + b'\n')
    with pytest.raises(ValueError, match='reviewed SHA-256'):
        BUILDER['read_approval'](source, pin)


def test_legacy_approval_ignores_adjacent_manifest(payload):
    source, _ = payload
    source.with_suffix('.manifest.json').write_text('{}', encoding='utf-8')
    assert BUILDER['read_approval'](source, None) == BUILDER['APPROVED'].read_bytes()


@pytest.mark.parametrize('reformatted', [False, True])
def test_candidate_cannot_reuse_historical_approval(payload, reformatted):
    source, _ = payload
    approved = BUILDER['APPROVED'].read_bytes()
    if reformatted:
        approved = json.dumps(json.loads(approved), separators=(',', ':')).encode()
    source.with_suffix('.manifest.json').write_bytes(approved)
    with pytest.raises(ValueError, match='historical'):
        BUILDER['read_approval'](source, hashlib.sha256(approved).hexdigest())


@pytest.mark.parametrize('candidate', [False, True])
def test_portable_archive_names_and_checksums(payload, candidate):
    source, inventory = payload
    source.with_suffix('.manifest.json').write_text(json.dumps(inventory), encoding='utf-8')
    source.with_suffix('.sha256').write_text('per-file inventory\n', encoding='utf-8')
    args = [sys.executable, '-B', str(ROOT / 'packaging/zip-portable.py'), str(source)]
    if candidate:
        args.append('--candidate')
    subprocess.run(args, capture_output=True, check=True)

    name = ('HybridSign-0.1.0-rc1-win-x64-portable.zip' if candidate
            else 'HybridSign-Phase4C2A-win-x64-portable.zip')
    archive = source.parent / name
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert bundle.read('HybridSign/HybridSign.exe') == (source / 'HybridSign.exe').read_bytes()
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert archive.with_suffix('.zip.sha256').read_text().split() == [digest, name]
