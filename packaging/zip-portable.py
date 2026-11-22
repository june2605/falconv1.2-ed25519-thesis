"""Optional local archive. Only files from the validated release inventory."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('payload', type=Path)
parser.add_argument('--candidate', action='store_true', help='Use the separate Windows rc1 archive name')
args = parser.parse_args()
folder = args.payload.resolve(strict=True)
manifest_path = folder.with_suffix('.manifest.json')
record = json.loads(manifest_path.read_text(encoding='utf-8'))
name = ('HybridSign-0.1.0-rc1-win-x64-portable.zip' if args.candidate
        else 'HybridSign-Phase4C2A-win-x64-portable.zip')
archive = folder.parent / name
checksum = archive.with_suffix('.zip.sha256')
if checksum.exists():
    raise FileExistsError('The archive checksum already exists. Use a fresh release folder.')
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
    for item in record['files']:
        path = folder / item['file']
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Release changed after manifest creation.')
        output.write(path, 'HybridSign/' + item['file'])
    for path in (manifest_path, folder.with_suffix('.sha256')):
        output.write(path, path.name)
with zipfile.ZipFile(archive) as check:
    assert check.testzip() is None
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
with checksum.open('x', encoding='utf-8') as stream:
    stream.write(digest + '  ' + archive.name + '\n')
print(f'{archive.name}: {archive.stat().st_size} bytes; SHA-256 {digest}')
