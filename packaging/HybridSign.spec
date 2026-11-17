# Official Windows x64 one-folder build; execute from any working directory.
from pathlib import Path
from PyInstaller.utils.hooks import copy_metadata

root = Path(SPECPATH).parent
metadata = []
for name in ['pywebview', 'pythonnet', 'clr_loader', 'cryptography', 'pqcrypto',
             'PyNaCl', 'cffi', 'bottle', 'proxy_tools', 'typing_extensions']:
    metadata += copy_metadata(name)

a = Analysis(
    [str(root / 'packaging/entrypoint.py')], pathex=[str(root)],
    binaries=[], datas=metadata + [(str(root / 'frontend/dist'), 'frontend/dist'),
                                  (str(root / 'logobig.ico'), '.')],
    hiddenimports=['webview.platforms.winforms', 'webview.platforms.edgechromium',
                   'clr', 'clr_loader.netfx', 'pqcrypto._sign.falcon_512',
                   'cryptography.hazmat.primitives.kdf.argon2',
                   'cryptography.hazmat.primitives.ciphers.aead', 'cryptography.exceptions'],
    hookspath=[str(root / 'packaging/hooks')],
    excludes=['streamlit', 'pytest', 'PyInstaller', 'setuptools', 'pkg_resources', 'distutils',
              'cffi.ffiplatform', 'cffi.setuptools_ext', 'cffi.verifier', 'cffi.vengine_cpy', 'cffi.vengine_gen',
              'IPython', 'notebook', 'numpy', 'pandas',
              'matplotlib', 'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
              'gi', 'cefpython3', 'webview.platforms.android', 'webview.platforms.qt', 'webview.platforms.gtk',
              'webview.platforms.cocoa', 'webview.platforms.cef', 'webview.platforms.mshtml'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='HybridSign',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, icon=str(root / 'logobig.ico'),
          uac_admin=False, contents_directory='_internal')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='HybridSign')
