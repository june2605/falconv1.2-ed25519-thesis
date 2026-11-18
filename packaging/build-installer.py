"""Build Setup from the exact approved Phase 4C.2A portable payload."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent.parent
APPROVED = ROOT / 'frontend/qa/phase4c2a/release-manifest.json'
SETUP_NAME = 'HybridSign-Setup-Phase4C2B-win-x64.exe'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_payload(source, approved):
    source = source.absolute()
    if any(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
           for path in (source, *source.parents)):
        raise ValueError('Payload must use an ordinary local directory.')
    records = approved['files']
    expected = {record['file']: record for record in records}
    if len(expected) != approved['fileCount'] or len(records) != len(expected):
        raise ValueError('Approved manifest has an inconsistent file count.')
    actual = set()
    for path in source.rglob('*'):
        info = path.lstat()
        if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError('Payload contains a reparse point.')
        if stat.S_ISDIR(info.st_mode):
            continue
        name = path.relative_to(source).as_posix()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or name not in expected
                or not all(re.fullmatch(r'[A-Za-z0-9_.-]+', part) for part in name.split('/'))):
            raise ValueError(f'Unexpected payload entry: {name}')
        record = expected[name]
        if info.st_size != record['bytes'] or digest(path) != record['sha256']:
            raise ValueError(f'Payload bytes differ from the approved release: {name}')
        actual.add(name)
    if actual != set(expected) or sum(r['bytes'] for r in records) != approved['totalBytes']:
        raise ValueError('Payload is incomplete or the approved size is inconsistent.')
    return records


def write_includes(stage, source, records):
    payload = stage / 'payload'
    file_entries = []
    conditions = []
    # Install the entry point after its dependencies. Uninstall records the
    # exact managed paths, including the original notices, in its own log.
    for record in sorted(records, key=lambda item: (item['file'] == 'HybridSign.exe', item['file'])):
        name = Path(record['file'])
        target = payload / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
        if digest(target) != record['sha256']:
            raise ValueError(f'Payload changed while staging: {name.as_posix()}')
        destination = '{app}' if name.parent == Path('.') else f'{{app}}\\{name.parent}'
        before_install = '; BeforeInstall: ReleaseLaunchGuard' if name == Path('HybridSign.exe') else ''
        file_entries.append(f'Source: "{target}"; DestDir: "{destination}"; Flags: ignoreversion{before_install}')
        conditions.append(f"  if not MatchesOwnedFile(Root, '{name}', '{record['sha256']}') then Exit;")
    (stage / 'files.iss').write_text('\n'.join(file_entries) + '\n', encoding='utf-8-sig')
    text = ['function PayloadIsSafe(Root: String): Boolean;', 'begin', '  Result := False;',
            *conditions, '  Result := True;', 'end;']
    (stage / 'ownership.iss').write_text('\n'.join(text) + '\n', encoding='utf-8-sig')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iscc', type=Path, required=True, help='Existing Inno Setup ISCC.exe')
    parser.add_argument('--payload', type=Path, default=ROOT / 'dist/portable/HybridSign')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/installer')
    args = parser.parse_args()
    compiler = args.iscc.resolve(strict=True)
    if not compiler.is_file():
        parser.error('--iscc must name an existing ISCC.exe file')
    output = args.output.resolve()
    if output.exists():
        parser.error('Output already exists. Specify a fresh --output directory.')
    approved = json.loads(APPROVED.read_text(encoding='utf-8'))
    records = validate_payload(args.payload, approved)
    work = ROOT / 'build'
    work.mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='installer-', dir=work))
    write_includes(stage, args.payload, records)
    output.mkdir(parents=True)
    result = subprocess.run([str(compiler), f'/DPayloadIncludes={stage}', f'/O{output}',
                             str(ROOT / 'packaging/HybridSign.iss')],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stage / 'compiler.log').write_bytes(result.stdout)
    print(result.stdout.decode('utf-8', errors='replace'))
    result.check_returncode()
    setup = output / SETUP_NAME
    sha256 = digest(setup)
    (output / (SETUP_NAME + '.sha256')).write_text(f'{sha256}  {SETUP_NAME}\n', encoding='ascii')
    shutil.copyfile(APPROVED, output / 'payload-manifest.json')
    shutil.copyfile(stage / 'payload/THIRD-PARTY-NOTICES.txt', output / 'THIRD-PARTY-NOTICES.txt')
    print(f'{setup.name}: {setup.stat().st_size} bytes, SHA-256 {sha256}')


if __name__ == '__main__':
    main()
