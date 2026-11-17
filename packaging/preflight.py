"""Read-only build prerequisites; no installs or environment upgrades."""
import importlib.metadata as metadata
from pathlib import Path
import struct
import sys

if sys.platform != 'win32' or struct.calcsize('P') != 8 or sys.version_info[:2] != (3, 11):
    raise SystemExit('Build requires Windows x64 and Python 3.11.')

expected = {'PyInstaller': '6.22.3', 'pyinstaller-hooks-contrib': '2026.10',
            'pywebview': '6.2.1', 'pythonnet': '3.2.1', 'clr_loader': '0.3.1',
            'pqcrypto': '0.3.4', 'PyNaCl': '1.6.2', 'cryptography': '50.0.2'}
for package, version in expected.items():
    if metadata.version(package) != version:
        raise SystemExit(f'Build requires the documented {package}=={version}; do not silently upgrade dependencies.')
root = Path(__file__).resolve().parent.parent
if not (root / 'logobig.ico').is_file():
    raise SystemExit('Application icon is missing.')
print('Windows x64 / Python 3.11 / pinned packaging and runtime prerequisites confirmed.')
