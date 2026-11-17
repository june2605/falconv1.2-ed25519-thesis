"""Pinned pywebview 6.2.1: JS support + EdgeChromium x64 only."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, get_package_paths

base = Path(get_package_paths('webview')[1])
datas = collect_data_files('webview', subdir='js')
# The pinned adapter enumerates all three *directories* before loading x64.
# Preserve those directory paths without shipping unused native architectures.
marker = Path(__file__).resolve().parent.parent / 'platform-directory.txt'
datas += [(str(marker), 'webview/lib/runtimes/' + arch + '/native')
          for arch in ('win-arm64', 'win-x86')]
binaries = [(str(base / 'lib' / name), 'webview/lib') for name in (
    'Microsoft.Web.WebView2.Core.dll', 'Microsoft.Web.WebView2.WinForms.dll')]
binaries += [(str(base / 'lib/runtimes/win-x64/native/WebView2Loader.dll'),
              'webview/lib/runtimes/win-x64/native')]
