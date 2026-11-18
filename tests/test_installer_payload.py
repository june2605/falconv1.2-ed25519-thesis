"""Reject changes between approval, staging, and installer compilation."""
import hashlib
from pathlib import Path
import runpy

import pytest


BUILDER = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'packaging/build-installer.py'))


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
