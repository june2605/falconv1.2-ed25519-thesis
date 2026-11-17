"""Build-time allowlist checks and per-file hashes outside the portable folder."""
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import sys


def release_manifest(folder):
    folder = Path(folder).resolve(strict=True)
    records = []
    banned = {'.git', 'node_modules', 'tests', 'qa', 'benchmark', 'data_test', 'secrets'}
    for path in sorted(folder.rglob('*')):
        if path.is_symlink():
            raise ValueError('Release must not contain symbolic links.')
        if not path.is_file():
            continue
        relative = path.relative_to(folder)
        if (any(part.casefold() in banned for part in relative.parts)
                or path.name == '.env' or path.name.startswith('.env.')
                or path.suffix.lower() in {'.hvault', '.key', '.pem', '.p12', '.pfx', '.pdf', '.tmp', '.db', '.sqlite', '.sqlite3'}):
            raise ValueError('Forbidden non-runtime release content.')
        data = path.read_bytes()
        records.append({'file': relative.as_posix(), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    required = ['HybridSign.exe', '_internal/python311.dll', '_internal/frontend/dist/index.html',
                '_internal/logobig.ico', '_internal/pythonnet/runtime/Python.Runtime.dll',
                '_internal/clr_loader/ffi/dlls/amd64/ClrLoader.dll',
                '_internal/webview/lib/Microsoft.Web.WebView2.Core.dll',
                '_internal/webview/lib/Microsoft.Web.WebView2.WinForms.dll',
                '_internal/pywebview-6.2.1.dist-info/METADATA',
                '_internal/pythonnet-3.2.1.dist-info/METADATA',
                '_internal/webview/lib/runtimes/win-x64/native/WebView2Loader.dll']
    names = {r['file'] for r in records}
    if not all(name in names for name in required):
        raise ValueError('Portable runtime/resource inventory is incomplete.')
    return {'format': 1, 'windowsBuild': platform.win32_ver(), 'python': platform.python_version(),
            'buildTools': {p: metadata.version(p) for p in ['PyInstaller', 'pyinstaller-hooks-contrib']},
            'runtimePackages': {p: metadata.version(p) for p in ['pywebview', 'pythonnet', 'clr_loader',
                'pqcrypto', 'PyNaCl', 'cryptography', 'cffi', 'pycparser', 'bottle', 'proxy_tools', 'typing_extensions']},
            'fileCount': len(records), 'totalBytes': sum(r['bytes'] for r in records), 'files': records}


if __name__ == '__main__':
    folder = Path(sys.argv[1]).resolve(strict=True)
    record = release_manifest(folder)
    folder.with_suffix('.manifest.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    folder.with_suffix('.sha256').write_text(''.join(f"{r['sha256']}  HybridSign/{r['file']}\n" for r in record['files']), encoding='utf-8')
    print(f"Validated {record['fileCount']} files, {record['totalBytes']} bytes; external manifest/checksums written.")
