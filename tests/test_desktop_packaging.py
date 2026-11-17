"""Source/frozen resource and windowless error regressions; no security bypass."""
from pathlib import Path
import subprocess
import os
import sys

import pytest

from desktop import launcher, runtime
from desktop.assets import BuildError


def test_source_resources_do_not_depend_on_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    expected = Path(launcher.__file__).resolve().parent.parent
    assert runtime.resource_root() == expected
    assert launcher.default_build_path() == expected / 'frontend' / 'dist'


def test_frozen_resources_use_only_explicit_bundle_root(monkeypatch, tmp_path):
    bundle = tmp_path / 'Portable space \u0111' / '_internal'
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(bundle), raising=False)
    monkeypatch.chdir(tmp_path)
    assert runtime.resource_root() == bundle
    assert launcher.default_build_path() == bundle / 'frontend' / 'dist'


@pytest.mark.parametrize('value', [None, '', 'relative', 42])
def test_frozen_invalid_bundle_root_never_falls_back(monkeypatch, value):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', value, raising=False)
    with pytest.raises(runtime.StartupError, match='bundle'):
        runtime.resource_root()


def test_source_startup_error_retains_stderr(monkeypatch, capsys):
    monkeypatch.setattr(launcher, 'launch', lambda: (_ for _ in ()).throw(BuildError()))
    assert launcher.main() == 1
    assert 'Frontend build missing or unsafe' in capsys.readouterr().err


@pytest.mark.parametrize('failure', [BuildError(), runtime.StartupError('Microsoft .NET Framework 4.6.2 or later is required.'), RuntimeError('PRIVATE DIAGNOSTIC')])
def test_windowless_startup_uses_sanitized_native_error(monkeypatch, failure):
    messages = []
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'stderr', None)
    monkeypatch.setattr(runtime, '_native_startup_message', messages.append)
    monkeypatch.setattr(launcher, 'launch', lambda: (_ for _ in ()).throw(failure))
    assert launcher.main() == 1
    assert len(messages) == 1 and 'PRIVATE DIAGNOSTIC' not in messages[0]
    assert 'npm' not in messages[0]
    if isinstance(failure, BuildError):
        assert 'complete portable' in messages[0]


def test_sample_pdf_is_declared_binary_and_git_clean_filter_preserves_bytes():
    root = Path(__file__).resolve().parent.parent
    path = root / 'demo_assets/sample-unsigned.pdf'
    attr = subprocess.check_output(['git', 'check-attr', 'binary', 'text', '--', str(path)], cwd=root).decode()
    assert 'binary: set' in attr and 'text: unset' in attr
    expected = subprocess.check_output(['git', 'hash-object', '--no-filters', str(path)], cwd=root)
    actual = subprocess.check_output(['git', 'hash-object', '--path=demo_assets/sample-unsigned.pdf', str(path)], cwd=root)
    assert actual == expected


def test_sample_pdf_clean_checkout_preserves_exact_xref_bytes(tmp_path):
    # Separate index/checkout only: no second repository, commit or main-index change.
    root = Path(__file__).resolve().parent.parent
    env = dict(os.environ, GIT_INDEX_FILE=str(tmp_path / 'index'))
    subprocess.run(['git', 'read-tree', 'HEAD'], cwd=root, env=env, check=True)
    subprocess.run(['git', 'add', '--', '.gitattributes', 'demo_assets/sample-unsigned.pdf'], cwd=root, env=env, check=True)
    checkout = tmp_path / 'clean checkout'
    checkout.mkdir()
    subprocess.run(['git', 'checkout-index', '--prefix=' + checkout.as_posix() + '/', '--',
                    '.gitattributes', 'demo_assets/sample-unsigned.pdf'], cwd=root, env=env, check=True)
    data = (checkout / 'demo_assets/sample-unsigned.pdf').read_bytes()
    assert data == (root / 'demo_assets/sample-unsigned.pdf').read_bytes()
    assert len(data) == 742 and data[559:].startswith(b'xref\n0 6\n')


@pytest.mark.parametrize('missing', [True, False])
def test_frozen_metadata_checks_are_not_bypassed(monkeypatch, missing):
    import importlib.metadata
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    def version(_):
        if missing: raise importlib.metadata.PackageNotFoundError()
        return '0.0.0'
    monkeypatch.setattr(importlib.metadata, 'version', version)
    with pytest.raises(runtime.StartupError, match='complete portable'):
        runtime.require_runtime()


@pytest.mark.parametrize('suffix', ['original.hvault', 'signed.pdf', '_internal/assets/../output.pdf', 'folder/../output.pdf'])
def test_frozen_application_folder_cannot_be_a_user_destination(monkeypatch, tmp_path, suffix):
    install = tmp_path / 'Portable application'
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(install / 'HybridSign.exe'))
    with pytest.raises(ValueError, match='application folder'):
        runtime.validate_user_destination(install / suffix)


def test_frozen_external_user_destination_and_source_profile_remain_compatible(monkeypatch, tmp_path):
    install, work = tmp_path / 'Portable application', tmp_path / 'User files'
    work.mkdir()
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(install / 'HybridSign.exe'))
    monkeypatch.chdir(work)
    assert runtime.validate_user_destination('signed.pdf') is None
    with pytest.raises(ValueError):
        runtime.validate_user_destination('../Portable application/output.pdf')
    monkeypatch.setattr(sys, 'frozen', False)
    assert runtime.validate_user_destination(install / 'source-compatible.pdf') is None


def test_build_script_preserves_an_existing_release(tmp_path):
    root = Path(__file__).resolve().parent.parent
    release = tmp_path / 'HybridSign'
    release.mkdir(); sentinel = release / 'keep.txt'; sentinel.write_bytes(b'preserve this release')
    result = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                             str(root / 'packaging/build-portable.ps1'), '-DistPath', str(tmp_path)],
                            capture_output=True, cwd=tmp_path)
    assert result.returncode != 0 and b'Output already exists' in result.stderr
    assert sentinel.read_bytes() == b'preserve this release' and set(release.iterdir()) == {sentinel}


@pytest.mark.parametrize('name', ['user.hvault', 'private.KEY', 'personal.pdf', 'Benchmark/data.bin', '.env', 'secret.pem'])
def test_release_inventory_rejects_nonruntime_content(tmp_path, name):
    import runpy
    root = Path(__file__).resolve().parent.parent
    inventory = runpy.run_path(str(root / 'packaging/release_manifest.py'))['release_manifest']
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'not runtime content')
    with pytest.raises(ValueError, match='Forbidden'):
        inventory(tmp_path)
