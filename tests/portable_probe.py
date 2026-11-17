"""External Windows UI Automation acceptance of the unmodified portable EXE.

Run explicitly after building/copying. No test code is bundled, no JS/CDP/debug
channel is enabled, and no password is passed through argv, environment or files.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time

import clr

framework = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/WPF'
for assembly in ('UIAutomationTypes', 'UIAutomationClient'):
    clr.AddReference(str(framework / (assembly + '.dll')))
from System import Int32, IntPtr
from System.Windows.Automation import (
    AutomationElement, Condition, ControlType, InvokePattern, PropertyCondition,
    TreeScope, ValuePattern, WindowPattern, WindowVisualState, TransformPattern,
    SelectionItemPattern, ElementNotAvailableException, ElementNotEnabledException, TogglePattern,
)

user = ctypes.windll.user32
user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user.SetForegroundWindow.argtypes = [wintypes.HWND]
user.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user.SetPhysicalCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
user.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))  # Driver only: UIA physical coordinates.
user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user.GetForegroundWindow.restype = wintypes.HWND
user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]


class KeyboardInput(ctypes.Structure):
    _fields_ = [('vk', wintypes.WORD), ('scan', wintypes.WORD), ('flags', wintypes.DWORD),
                ('time', wintypes.DWORD), ('extra', wintypes.WPARAM)]


class MouseInput(ctypes.Structure):
    _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG), ('data', wintypes.DWORD),
                ('flags', wintypes.DWORD), ('time', wintypes.DWORD), ('extra', wintypes.WPARAM)]


class InputUnion(ctypes.Union):
    _fields_ = [('keyboard', KeyboardInput), ('mouse', MouseInput)]


class Input(ctypes.Structure):
    _fields_ = [('kind', wintypes.DWORD), ('value', InputUnion)]


user.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]


def keyboard(events):
    inputs = (Input * len(events))(*(Input(1, InputUnion(keyboard=KeyboardInput(vk, scan, flags, 0, 0))) for vk, scan, flags in events))
    assert user.SendInput(len(inputs), inputs, ctypes.sizeof(Input)) == len(inputs)


class Probe:
    def __init__(self, app, work, evidence):
        self.app, self.work, self.evidence = app, work, evidence
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.password = secrets.token_urlsafe(24)
        self.process = None
        self.report = {'passed': False, 'driver': 'external Windows UI Automation',
                       'noBundledTestHooks': True, 'noRemoteDebugging': True, 'checks': [], 'windowStates': {}}
        self.stage = 'startup'

    def wait(self, action, timeout=25):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = action()
            if result: return result
            if self.process and self.process.poll() is not None:
                raise AssertionError('Packaged process exited unexpectedly')
            time.sleep(.08)
        raise AssertionError('Packaged UI did not settle at ' + self.stage)

    def windows(self):
        roots = list(AutomationElement.RootElement.FindAll(TreeScope.Children,
            PropertyCondition(AutomationElement.ProcessIdProperty, Int32(self.process.pid))))
        # UIA nests owned native dialogs beneath their owner, unlike EnumWindows.
        return roots + [child for root in roots for child in root.FindAll(TreeScope.Descendants,
            PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Window))]

    def nodes(self, root=None):
        return list((root or self.window).FindAll(TreeScope.Descendants, Condition.TrueCondition))

    def find(self, name, kind=None, root=None, enabled=False):
        for node in self.nodes(root):
            try:
                current = node.Current
                if current.Name == name and (kind is None or current.ControlType == kind) and (not enabled or current.IsEnabled):
                    return node
            except ElementNotAvailableException:
                continue  # Read-only tree snapshot raced a React render.

    def present(self, name):
        return self.find(name) is not None

    def click(self, name, *, kind=ControlType.Button, root=None):
        # Real mouse input, with UIA used only for accessible identity/bounds.
        # Do not resubmit a delivered action or enable a browser debugging port.
        owner = root or self.window
        user.SetWindowPos(owner.Current.NativeWindowHandle, 0, 0, 0, 0, 0, 0x43)
        user.SetForegroundWindow(owner.Current.NativeWindowHandle)
        self.wait(lambda: self.find(name, kind, root, enabled=True))
        previous, stable_since = None, time.monotonic()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            node = self.wait(lambda: self.find(name, kind, root, enabled=True))
            rect = node.Current.BoundingRectangle
            assert rect.Width > 0 and rect.Height > 0
            geometry = (rect.X, rect.Y, rect.Width, rect.Height)
            user.SetPhysicalCursorPos(int(rect.X + rect.Width / 2), int(rect.Y + rect.Height / 2))
            if geometry != previous:
                previous, stable_since = geometry, time.monotonic()
            elif time.monotonic() - stable_since >= .4:
                break
            time.sleep(.1)
        else:
            raise AssertionError('Pointer target did not stabilize')
        assert user.GetForegroundWindow() == owner.Current.NativeWindowHandle, 'Owned UI lost foreground'
        user.mouse_event(2, 0, 0, 0, 0)
        user.mouse_event(4, 0, 0, 0, 0)

    def go(self, name):
        self.click(name, kind=ControlType.Hyperlink)
        time.sleep(.2)

    def modal(self, suffix):
        return next((w for w in self.windows() if w.Current.Name == 'HybridSign \u2014 ' + suffix), None)

    def file(self, suffix, path, saving=False):
        self.stage = 'waiting for native file dialog: ' + suffix
        dialog = self.wait(lambda: self.modal(suffix))
        self.stage = 'native filename input: ' + suffix
        edits = [n for n in self.nodes(dialog) if n.Current.ControlType == ControlType.Edit
                 and 'File name' in n.Current.Name]
        assert len(edits) == 1, 'Native filename field was not identified uniquely'
        self.type_filename(dialog, edits[0], path)
        self.click('Save' if saving else 'Open', root=dialog)
        self.stage = 'waiting for native file dialog to close: ' + suffix
        self.wait(lambda: self.modal(suffix) is None)

    def type_filename(self, dialog, edit, path):
        user.SetForegroundWindow(dialog.Current.NativeWindowHandle)
        edit.SetFocus()
        self.wait(lambda: user.GetForegroundWindow() == dialog.Current.NativeWindowHandle)
        self.wait(lambda: edit.Current.HasKeyboardFocus)
        keyboard([(0x11, 0, 0), (ord('A'), 0, 0), (ord('A'), 0, 2), (0x11, 0, 2)])
        units = str(path).encode('utf-16-le')
        events = []
        for offset in range(0, len(units), 2):
            unit = int.from_bytes(units[offset:offset + 2], 'little')
            events.extend([(0, unit, 4), (0, unit, 6)])
        keyboard(events)
        # SendInput queues native messages; do not read an old filename frame.
        self.wait(lambda: edit.GetCurrentPattern(ValuePattern.Pattern).Current.Value == str(path))

    def denied_location(self, suffix, path):
        dialog = self.wait(lambda: self.modal(suffix))
        edit = next(n for n in self.nodes(dialog) if n.Current.ControlType == ControlType.Edit and n.Current.Name == 'File name:')
        self.type_filename(dialog, edit, path)
        self.click('Save', root=dialog)
        notice = self.wait(lambda: self.modal('Choose another location'))
        assert not path.exists()
        self.click('OK', root=notice)
        self.wait(lambda: self.modal('Choose another location') is None)
        assert self.modal(suffix) is not None
        self.report['checks'].append('application-folder-output-rejected:' + path.suffix)

    def password_dialog(self, creating=False, wrong=False):
        self.stage = 'masked password creation' if creating else 'masked password unlock'
        dialog = self.wait(lambda: self.modal('Create encrypted vault' if creating else 'Unlock encrypted vault'))
        boxes = [n for n in self.nodes(dialog) if n.Current.ControlType == ControlType.Edit]
        assert len(boxes) == (2 if creating else 1) and all(b.Current.IsPassword for b in boxes)
        self.report['nativePasswordControlsMasked'] = True
        for box in boxes:
            box.GetCurrentPattern(ValuePattern.Pattern).SetValue(secrets.token_urlsafe(24) if wrong else self.password)
        self.click('Create Vault' if creating else 'Unlock Vault', root=dialog)
        self.wait(lambda: self.modal('Create encrypted vault' if creating else 'Unlock encrypted vault') is None)

    def capture(self, name):
        from PIL import ImageGrab
        rect = wintypes.RECT()
        assert ctypes.windll.dwmapi.DwmGetWindowAttribute(self.window.Current.NativeWindowHandle, 9,
               ctypes.byref(rect), ctypes.sizeof(rect)) == 0
        time.sleep(.2)
        ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom), all_screens=True).save(self.evidence / name)

    def move_to(self, x, y):
        rect = self.window.Current.BoundingRectangle
        user.SetPhysicalCursorPos(int(rect.X + x), int(rect.Y + y))

    def sidebar(self, state):
        self.move_to(35, 265)
        self.wait(lambda: self.find('Collapse sidebar', ControlType.Button))
        self.go('Dashboard')
        time.sleep(.4)
        assert self.present('Collapse sidebar')  # Navigation does not collapse under pointer.
        self.capture('packaged-sidebar-' + state + '.png')
        automatic = self.find('Automatic sidebar', ControlType.Button)
        assert automatic and str(automatic.GetCurrentPattern(TogglePattern.Pattern).Current.ToggleState) == 'On'
        if state == 'maximized':
            self.click('Pin sidebar')
            self.move_to(600, 140); time.sleep(.5)
            assert self.present('Unpin sidebar')
            self.click('Unpin sidebar')
            self.click('Automatic sidebar')
            assert str(self.find('Automatic sidebar', ControlType.Button).GetCurrentPattern(TogglePattern.Pattern).Current.ToggleState) == 'Off'
            self.move_to(600, 140); time.sleep(.6)
            assert self.present('Collapse sidebar')
            self.click('Collapse sidebar'); self.wait(lambda: self.present('Expand sidebar'))
            self.move_to(35, 265); time.sleep(.6)
            assert self.present('Expand sidebar')
            self.click('Expand sidebar'); self.click('Automatic sidebar')
            self.report['checks'].append('sidebar-manual-and-auto-toggle')
        self.move_to(600, 140)
        self.wait(lambda: self.present('Expand sidebar'))
        self.report['checks'].append('sidebar-auto-and-navigation:' + state)

    def window_qa(self):
        self.stage = 'packaged window/sidebar acceptance'
        pattern = self.window.GetCurrentPattern(WindowPattern.Pattern)
        for state in ('default', 'maximized', 'restored', 'minimum'):
            if state == 'maximized': pattern.SetWindowVisualState(WindowVisualState.Maximized)
            elif state == 'restored': pattern.SetWindowVisualState(WindowVisualState.Normal)
            elif state == 'minimum': self.window.GetCurrentPattern(TransformPattern.Pattern).Resize(1200.0, 750.0)
            time.sleep(.5)
            rect = self.window.Current.BoundingRectangle
            self.report['windowStates'][state] = {'physicalWidth': rect.Width, 'physicalHeight': rect.Height}
            self.sidebar(state)
        self.window.GetCurrentPattern(TransformPattern.Pattern).Resize(1600.0, 1000.0)
        self.go('Settings')
        dark = self.wait(lambda: self.find('Dark', ControlType.RadioButton))
        dark.GetCurrentPattern(SelectionItemPattern.Pattern).Select()
        self.wait(lambda: self.find('Dark', ControlType.RadioButton).GetCurrentPattern(SelectionItemPattern.Pattern).Current.IsSelected)
        for name in ('Dashboard', 'Sign Document', 'Verify Signature', 'Key Vault', 'Settings'):
            self.go(name); self.capture('packaged-dark-' + name.lower().replace(' ', '-') + '.png')
        self.find('Light', ControlType.RadioButton).GetCurrentPattern(SelectionItemPattern.Pattern).Select()
        self.report['checks'].append('five-packaged-screens-dark-and-light')

    def start(self):
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV')}
        env['PATH'] = os.environ['WINDIR'] + '\\System32;' + os.environ['WINDIR']
        self.process = subprocess.Popen([str(self.app / 'HybridSign.exe')], cwd=self.work, env=env)
        self.report.setdefault('pids', []).append(self.process.pid)
        self.window = self.wait(lambda: next((w for w in self.windows() if w.Current.Name == 'HybridSign \u2014 Desktop Preview'), None))
        self.wait(lambda: self.present('Desktop Connected'))
        assert self.present('No vault unlocked')
        self.report['checks'].append('locked-on-startup')

    def stop(self):
        self.window.GetCurrentPattern(WindowPattern.Pattern).Close()
        assert self.process.wait(timeout=30) == 0
        self.report['checks'].append('clean-exe-exit')
        self.process = None

    def key_id(self):
        self.click('View full ID')
        def full_id():
            return next((n.Current.Name for n in self.nodes() if re.fullmatch(r'hybrid-v1:[0-9a-f]{64}', n.Current.Name)), None)
        return self.wait(full_id)

    def copy_public_id(self, expected):
        self.click('Copy full ID')
        kernel = ctypes.windll.kernel32
        user.GetClipboardData.argtypes, user.GetClipboardData.restype = [wintypes.UINT], wintypes.HANDLE
        kernel.GlobalLock.argtypes, kernel.GlobalLock.restype = [wintypes.HANDLE], ctypes.c_void_p
        kernel.GlobalUnlock.argtypes = [wintypes.HANDLE]
        def matches():
            if not user.OpenClipboard(None): return False
            try:
                handle = user.GetClipboardData(13)
                if not handle: return False
                pointer = kernel.GlobalLock(handle)
                if not pointer: return False
                try: return ctypes.wstring_at(pointer) == expected
                finally: kernel.GlobalUnlock(handle)
            finally: user.CloseClipboard()
        self.wait(matches, timeout=5)
        self.report['checks'].append('copied-exact-public-hybrid-id')

    def create_vault(self, path):
        self.go('Key Vault'); self.click('Create Vault')
        if path.name == 'original.hvault':
            self.denied_location('Save a new encrypted vault', self.app / 'blocked.hvault')
        self.file('Save a new encrypted vault', path, saving=True)
        self.password_dialog(creating=True)
        self.wait(lambda: path.exists() and self.present('Locked'))

    def unlock(self, path):
        self.click('Unlock Vault'); self.file('Open encrypted vault', path)
        self.password_dialog()
        self.wait(lambda: self.present('Unlocked'))

    def sign(self, source, output):
        self.go('Sign Document'); self.click('Choose PDF')
        self.file('Choose unsigned PDF', source)
        self.click('Continue to review')
        duplicate = self.find('Sign PDF', ControlType.Button).GetCurrentPattern(InvokePattern.Pattern)
        self.click('Sign PDF')
        if output.name == 'signed.pdf':
            self.wait(lambda: self.modal('Save signed PDF'))
            assert not self.find('Sign PDF', ControlType.Button).Current.IsEnabled
            try: duplicate.Invoke()
            except (ElementNotEnabledException, ElementNotAvailableException): pass
            assert sum(w.Current.Name == 'HybridSign \u2014 Save signed PDF' for w in self.windows()) == 1
            self.report['checks'].append('duplicate-sign-action-during-save-disabled')
            self.denied_location('Save signed PDF', self.app / 'blocked.pdf')
            # Reserved signing is already active while the native Save is open.
            user.PostMessageW(self.window.Current.NativeWindowHandle, 0x10, 0, 0)
            notice = self.wait(lambda: self.modal('Operation in progress'))
            self.click('OK', root=notice)
            self.wait(lambda: self.modal('Operation in progress') is None)
            assert self.modal('Save signed PDF') is not None
            self.report['checks'].append('busy-close-refused-during-signing-save')
        self.file('Save signed PDF', output, saving=True)
        self.wait(lambda: output.exists() and self.present('Signed PDF saved'))
        assert self.present('Completed self-verification')

    def verify(self, path, expected, authenticated=False):
        self.go('Verify Signature'); self.click('Choose signed PDF')
        self.file('Choose signed PDF', path)
        self.wait(lambda: self.present('No verification performed'))
        if authenticated: self.click('Use authenticated vault')
        self.click('Verify PDF')
        self.wait(lambda: self.present('HYBRID ' + expected))

    def run(self, sample):
        original = self.work / 'public sample.pdf'
        original.write_bytes(sample.read_bytes())
        source_digest = hashlib.sha256(original.read_bytes()).hexdigest()
        vault, wrong = self.work / 'original.hvault', self.work / 'wrong.hvault'
        signed, changed = self.work / 'signed.pdf', self.work / 'tampered.pdf'
        self.start(); self.capture('packaged-dashboard.png')
        self.window_qa()
        self.stage = 'native vault create/unlock'
        self.create_vault(vault); self.unlock(vault)
        first = self.key_id(); self.report['hybridKeyId'] = first
        self.copy_public_id(first)
        self.capture('packaged-unlocked.png')
        self.stage = 'real signing'
        self.sign(original, signed); self.capture('packaged-signed.png')
        assert signed.read_bytes().startswith(b'%PDF-1.4\n') and signed.stat().st_size > len(original.read_bytes())
        self.stage = 'valid and tampered verification'
        self.verify(signed, 'VALID', authenticated=True); self.capture('packaged-valid.png')
        data = signed.read_bytes(); assert data.count(b'APPROVED') == 1
        changed.write_bytes(data.replace(b'APPROVED', b'REJECTED', 1))
        self.verify(changed, 'INVALID'); self.capture('packaged-tampered.png')
        self.report['checks'] += ['original-vault-generated-by-exe', 'real-signing-self-verified', 'saved-pdf-valid', 'modified-copy-invalid']
        self.go('Key Vault'); self.click('Lock Vault'); self.wait(lambda: self.present('Locked'))
        self.verify(signed, 'VALID'); self.report['checks'].append('locked-public-verification')
        self.click('Choose encrypted vault'); self.file('Open encrypted vault', vault)
        self.wait(lambda: self.present('UNAUTHENTICATED'))
        assert self.modal('Unlock encrypted vault') is None
        self.verify(signed, 'VALID')
        self.report['checks'].append('password-free-public-metadata-verification')
        self.stage = 'independent wrong-key vault'
        self.create_vault(wrong); self.unlock(wrong)
        assert self.key_id() != first
        self.verify(signed, 'INVALID', authenticated=True); self.capture('packaged-wrong-keys.png')
        self.report['checks'].append('wrong-keys-invalid')
        self.go('Key Vault'); self.click('Lock Vault'); self.wait(lambda: self.present('Locked'))
        self.stop()
        self.stage = 'second executable process'
        self.start(); self.go('Key Vault'); self.capture('packaged-restart-locked.png')
        self.unlock(vault); assert self.key_id() == first
        self.report['checks'].append('original-id-survives-exe-restart')
        self.sign(original, self.work / 'signed-after-restart.pdf')
        self.verify(self.work / 'signed-after-restart.pdf', 'VALID', authenticated=True)
        self.report['checks'].append('sign-and-verify-after-restart')
        self.capture('packaged-reopened-valid.png')
        assert hashlib.sha256(original.read_bytes()).hexdigest() == source_digest
        self.report['sourceSha256'] = source_digest
        self.report['signedBytes'] = signed.stat().st_size
        self.report['vaultBytes'] = vault.stat().st_size
        self.inspect_loaded_components()
        self.stop(); self.report['passed'] = True

    def inspect_loaded_components(self):
        kernel, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        psapi.EnumProcessModulesEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE), wintypes.DWORD,
                                               ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
        psapi.GetModuleFileNameExW.argtypes = [wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
        handle = kernel.OpenProcess(0x410, False, self.process.pid)
        assert handle
        try:
            modules, needed = (wintypes.HMODULE * 2048)(), wintypes.DWORD()
            assert psapi.EnumProcessModulesEx(handle, modules, ctypes.sizeof(modules), ctypes.byref(needed), 3)
            paths = []
            for module in modules[:needed.value // ctypes.sizeof(wintypes.HMODULE)]:
                name = ctypes.create_unicode_buffer(32768)
                assert psapi.GetModuleFileNameExW(handle, module, name, len(name))
                paths.append(Path(name.value))
            required = ['python311.dll', 'falcon_512', '_sodium', '_rust']
            evidence = {}
            for component in required:
                matches = [p for p in paths if component in p.name]
                assert matches and all(p.is_relative_to(self.app) for p in matches)
                evidence[component] = [p.relative_to(self.app).as_posix() for p in matches]
            assert not any('.venv' in str(p) or 'Final_Thesis_GitHub' in str(p) for p in paths)
            self.report['loadedNativeComponents'] = evidence
            self.report['checks'].append('loaded-python-and-crypto-from-copied-folder')
        finally:
            kernel.CloseHandle(handle)


if __name__ == '__main__':
    app, work, evidence, sample = (Path(v).resolve() for v in sys.argv[1:5])
    work.mkdir(parents=True, exist_ok=True)
    probe = Probe(app, work, evidence)
    try:
        probe.run(sample)
    except Exception as error:
        probe.report['failure'] = {'stage': probe.stage, 'type': type(error).__name__}
        if isinstance(error, AssertionError): probe.report['failure']['condition'] = str(error)
        print(json.dumps(probe.report), flush=True)
        # Credentials stay local; no traceback/local-value dump.
        raise SystemExit(1)
    (evidence / 'packaged-checks.json').write_text(json.dumps(probe.report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(probe.report), flush=True)
