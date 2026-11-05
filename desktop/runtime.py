"""Read-only Windows prerequisite checks. Never install/download a runtime."""
import importlib.metadata
import re
import struct
import sys

MIN_WEBVIEW_MAJOR = 111  # Tailwind 4's Chromium browser feature baseline.


class StartupError(Exception):
    pass


def require_runtime():
    if sys.platform != "win32" or struct.calcsize("P") != 8 or sys.version_info[:2] != (3, 11):
        raise StartupError("Use Windows x64 with the existing Python 3.11 environment.")
    try:
        for package, version in [("pywebview", "6.2.1"), ("pythonnet", "3.2.1")]:
            if importlib.metadata.version(package) != version:
                raise StartupError("Install the pinned requirements-desktop.txt packages.")
    except importlib.metadata.PackageNotFoundError:
        raise StartupError("Install requirements-desktop.txt into the existing environment.") from None
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full") as key:
            release = winreg.QueryValueEx(key, "Release")[0]
            if type(release) is not int or release < 394802:
                raise OSError()
    except OSError:
        raise StartupError("Microsoft .NET Framework 4.6.2 or later is required.") from None
    for hive, prefix in [(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node"),
                         (winreg.HKEY_CURRENT_USER, "SOFTWARE")]:
        try:
            path = prefix + r"\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
            with winreg.OpenKey(hive, path) as key:
                version = winreg.QueryValueEx(key, "pv")[0]
            if type(version) is str and re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version) and int(version.split(".")[0]) >= MIN_WEBVIEW_MAJOR:
                return version
        except OSError:
            continue
    raise StartupError("Install Microsoft Edge WebView2 Evergreen Runtime 111 or later, then restart HybridSign.")


def fit_window_to_work_area(native):
    """Run on the GUI thread; use WinForms' own DPI coordinate system."""
    from System.Drawing import Point, Size
    from System.Windows.Forms import FormStartPosition, Screen
    area = Screen.FromControl(native).WorkingArea
    width, height = max(1, area.Width - 16), max(1, area.Height - 16)
    native.MinimumSize = Size(min(native.MinimumSize.Width, width), min(native.MinimumSize.Height, height))
    native.Size = Size(min(native.Width, width), min(native.Height, height))
    native.StartPosition = FormStartPosition.Manual
    native.Location = Point(area.Left + (area.Width - native.Width) // 2,
                            area.Top + (area.Height - native.Height) // 2)
