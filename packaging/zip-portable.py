"""Optional local archive. Only files from the validated release inventory."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

folder = Path(sys.argv[1]).resolve(strict=True)
manifest_path = folder.with_suffix('.manifest.json')
record = json.loads(manifest_path.read_text(encoding='utf-8'))
archive = folder.parent / 'HybridSign-Phase4C2A-win-x64-portable.zip'
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
archive.with_suffix('.zip.sha256').write_text(digest + '  ' + archive.name + '\n', encoding='utf-8')
print(f'{archive.name}: {archive.stat().st_size} bytes; SHA-256 {digest}')
