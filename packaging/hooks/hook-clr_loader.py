"""Use only Windows x64 .NET Framework loader from the pinned clr_loader."""
from pathlib import Path
from PyInstaller.utils.hooks import get_package_paths

base = Path(get_package_paths('clr_loader')[1])
binaries = [(str(base / 'ffi/dlls/amd64/ClrLoader.dll'), 'clr_loader/ffi/dlls/amd64')]
