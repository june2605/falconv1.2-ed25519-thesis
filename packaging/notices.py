"""Copy available Python/npm license texts; no source tree or dependencies copied."""
import importlib.metadata as metadata
import json
from pathlib import Path
import sys


def write_notices(folder):
    root = Path(__file__).resolve().parent.parent
    sections = ['HybridSign third-party notices (observed installed distributions).\n'
                'This inventory is not an independent license/compliance audit.\n']
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    sections += ['\n=== Python ===\n' + python_license.read_text(encoding='utf-8')]
    names = ['PyInstaller', 'pywebview', 'pythonnet', 'clr_loader', 'pqcrypto',
             'PyNaCl', 'cryptography', 'cffi', 'pycparser', 'bottle', 'proxy_tools', 'typing_extensions']
    for name in names:
        dist = metadata.distribution(name)
        sections.append(f'\n=== {name} {dist.version} ===\n')
        found = False
        for entry in dist.files or []:
            if any(token in str(entry).lower() for token in ('license', 'copying', 'notice')):
                path = Path(dist.locate_file(entry))
                if path.is_file() and path.stat().st_size < 1024 * 1024:
                    sections.append(path.read_text(encoding='utf-8', errors='replace'))
                    found = True
        if not found:
            sections.append('Declared license: ' + str(dist.metadata.get('License', 'Not supplied')) +
                            '\nNo separate license text shipped in this installed wheel; upstream review remains required.\n')
    lock = json.loads((root / 'frontend/package-lock.json').read_text(encoding='utf-8'))
    for name, record in sorted(lock['packages'].items()):
        if not name.startswith('node_modules/') or record.get('dev'):
            continue
        package = root / 'frontend' / name
        sections.append(f"\n=== npm {name.removeprefix('node_modules/')} {record['version']} ===\n")
        for path in sorted(package.glob('*')):
            if path.is_file() and path.name.lower().startswith(('license', 'copying', 'notice')):
                sections.append(path.read_text(encoding='utf-8', errors='replace'))
    (Path(folder) / 'THIRD-PARTY-NOTICES.txt').write_text('\n'.join(sections), encoding='utf-8')


if __name__ == '__main__':
    write_notices(Path(sys.argv[1]).resolve(strict=True))
