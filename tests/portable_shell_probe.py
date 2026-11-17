"""Normal Windows Shell Open (double-click verb), no console/test entry point."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import runpy
import sys

driver = runpy.run_path(str(Path(__file__).with_name('portable_probe.py')))
Probe, AutomationElement = driver['Probe'], driver['AutomationElement']
WindowPattern = driver['WindowPattern']


class ShellExecuteInfo(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('mask', wintypes.ULONG), ('hwnd', wintypes.HWND),
                ('verb', wintypes.LPCWSTR), ('file', wintypes.LPCWSTR), ('parameters', wintypes.LPCWSTR),
                ('directory', wintypes.LPCWSTR), ('show', ctypes.c_int), ('instance', wintypes.HINSTANCE),
                ('idlist', ctypes.c_void_p), ('className', wintypes.LPCWSTR), ('classKey', wintypes.HKEY),
                ('hotkey', wintypes.DWORD), ('icon', wintypes.HANDLE), ('process', wintypes.HANDLE)]


class ShellProcess:
    def __init__(self, executable):
        shell, self.kernel = ctypes.windll.shell32, ctypes.windll.kernel32
        shell.ShellExecuteExW.argtypes = [ctypes.POINTER(ShellExecuteInfo)]
        self.kernel.GetProcessId.argtypes = [wintypes.HANDLE]
        self.kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        self.kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        info = ShellExecuteInfo()
        info.size, info.mask, info.verb = ctypes.sizeof(info), 0x140, 'open'
        info.file, info.directory, info.show = str(executable), str(executable.parent), 1
        assert shell.ShellExecuteExW(ctypes.byref(info)) and info.process
        self.handle, self.pid = info.process, self.kernel.GetProcessId(info.process)

    def poll(self):
        code = wintypes.DWORD()
        assert self.kernel.GetExitCodeProcess(self.handle, ctypes.byref(code))
        return None if code.value == 259 else code.value

    def wait(self, timeout):
        assert self.kernel.WaitForSingleObject(self.handle, int(timeout * 1000)) == 0
        result = self.poll(); self.kernel.CloseHandle(self.handle)
        return result


if __name__ == '__main__':
    app, evidence = (Path(v).resolve() for v in sys.argv[1:3])
    probe = Probe(app, app.parent, evidence)
    for key in ('PYTHONHOME', 'PYTHONPATH', 'VIRTUAL_ENV'):
        os.environ.pop(key, None)
    os.environ['PATH'] = os.environ['WINDIR'] + '\\System32;' + os.environ['WINDIR']
    probe.process = ShellProcess(app / 'HybridSign.exe')
    probe.window = probe.wait(lambda: next((w for w in probe.windows() if w.Current.Name == 'HybridSign \u2014 Desktop Preview'), None))
    probe.wait(lambda: probe.present('Desktop Connected'))
    assert probe.present('No vault unlocked')
    assert sum(w.Current.Name == 'HybridSign \u2014 Desktop Preview' for w in probe.windows()) == 1
    probe.capture('shell-open.png')
    probe.window.GetCurrentPattern(WindowPattern.Pattern).Close()
    assert probe.process.wait(timeout=30) == 0
    result = {'passed': True, 'normalShellOpen': True, 'applicationWorkingDirectory': True,
              'singleNativeWindow': True, 'startsLocked': True, 'exitCode': 0}
    (evidence / 'shell-checks.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
