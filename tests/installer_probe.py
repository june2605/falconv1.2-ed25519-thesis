"""External acceptance of Setup, the installed GUI, and the recorded uninstaller."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import time
import winreg


HERE = Path(__file__).resolve().parent
portable = runpy.run_path(str(HERE / 'portable_shell_probe.py'))
Probe = portable['Probe']
ShellProcess = portable['ShellProcess']
AutomationElement, WindowPattern = portable['AutomationElement'], portable['WindowPattern']
from System import Environment
from System.Security.Principal import WindowsIdentity, WindowsPrincipal, WindowsBuiltInRole
from System.Windows.Automation import Condition, ControlType, InvokePattern, TreeScope

APP_KEY = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{3699C4A8-8612-4F01-BB26-F014797A9CBE}_is1'
START = Path(str(Environment.GetFolderPath(Environment.SpecialFolder.Programs))) / 'HybridSign/HybridSign.lnk'
DESKTOP = Path(str(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory))) / 'HybridSign.lnk'
TITLE = 'Setup - HybridSign version 0.1.0'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def snapshot(folder):
    return {p.relative_to(folder).as_posix(): sha(p) for p in folder.rglob('*') if p.is_file()}


def registry(hive=winreg.HKEY_CURRENT_USER):
    try:
        with winreg.OpenKey(hive, APP_KEY, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            return {name: winreg.QueryValueEx(key, name)[0] for name in
                    ('DisplayName', 'DisplayVersion', 'Publisher', 'Inno Setup: App Path', 'UninstallString')}
    except FileNotFoundError:
        return None


def uninstall_command(app):
    entry = registry()
    assert entry['DisplayName'] == 'HybridSign version 0.1.0' and entry['DisplayVersion'] == '0.1.0'
    assert entry['Publisher'] == 'HybridSign thesis project'
    assert Path(entry['Inno Setup: App Path']) == app and registry(winreg.HKEY_LOCAL_MACHINE) is None
    exe = Path(entry['UninstallString'].strip('"'))
    assert exe.parent == app and exe.name.startswith('unins') and exe.suffix == '.exe'
    return exe


class InstalledProbe(Probe):
    def start(self):
        if self.report.get('pids'):
            self.start_shortcut(START)
        else:
            super().start()

    def start_shortcut(self, shortcut):
        self.process = ShellProcess(shortcut)
        self.report.setdefault('pids', []).append(self.process.pid)
        self.window = self.wait(lambda: next((w for w in self.windows()
            if w.Current.Name == 'HybridSign \u2014 Desktop Preview'), None))
        self.wait(lambda: self.present('Desktop Connected'))
        self.wait(lambda: self.present('No vault unlocked'))
        self.report['checks'].append('locked-on-startup-through-' + ('start-menu' if shortcut == START else 'desktop-shortcut'))

    def denied_location(self, suffix, path):
        super().denied_location(suffix, path)
        if suffix == 'Save signed PDF' and hasattr(self, 'busy_guard'):
            self.busy_guard()


def screen(title):
    return next((w for w in AutomationElement.RootElement.FindAll(TreeScope.Children, Condition.TrueCondition)
                 if w.Current.Name == title), None)


def wizard_button(probe, label):
    button = probe.wait(lambda: probe.find(label, ControlType.Button, enabled=True))
    button.GetCurrentPattern(InvokePattern.Pattern).Invoke()


def command(exe, log, options):
    return subprocess.run([str(exe), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/LOG=' + str(log),
                           *options], timeout=90).returncode


def run(setup, base, work, evidence):
    if registry() or registry(winreg.HKEY_LOCAL_MACHINE) or START.exists() or DESKTOP.exists():
        raise RuntimeError('An existing HybridSign installation or shortcut is present. Use a separate test account.')
    assert base.is_dir() and not any(base.iterdir())
    assert work.is_dir() and not any(work.iterdir())
    assert screen(TITLE) is None
    app = base / 'Installed application \u0111'
    build = json.loads((setup.parent / 'payload-manifest.json').read_text(encoding='utf-8'))
    expected = {item['file']: item['sha256'] for item in build['files']}
    checks = {}
    evidence.mkdir(parents=True, exist_ok=True)
    probe = InstalledProbe(app, work, evidence)
    probe.stage = 'fresh install wizard'
    proc = subprocess.Popen([str(setup), '/DIR=' + str(app), '/TASKS=desktopicon',
                             '/LOG=' + str(work / 'fresh.log')], cwd=work)
    probe.window = probe.wait(lambda: screen(TITLE))
    probe.capture('setup-information.png')
    wizard_button(probe, 'Next')
    probe.wait(lambda: probe.present('Select Destination Location'))
    wizard_button(probe, 'Next')
    probe.wait(lambda: probe.present('Select Additional Tasks'))
    probe.capture('setup-optional-desktop.png')
    assert probe.find('Create a &Desktop shortcut', ControlType.ListItem)
    wizard_button(probe, 'Next')
    probe.wait(lambda: probe.find('Install', enabled=True))
    wizard_button(probe, 'Install')
    probe.wait(lambda: probe.find('Finish', enabled=True), timeout=50)
    probe.capture('setup-complete.png')
    wizard_button(probe, 'Finish')
    assert proc.wait(timeout=25) == 0
    assert START.is_file() and DESKTOP.is_file()
    assert {n: sha(app / n) for n in expected} == expected
    uninstaller = uninstall_command(app)
    checks['freshInstallCode'] = 0
    checks['installTokenElevated'] = WindowsPrincipal(WindowsIdentity.GetCurrent()).IsInRole(WindowsBuiltInRole.Administrator)
    checks['installedPayloadHashesMatched'] = len(expected)

    def busy_guard():
        before = snapshot(app)
        install_log, uninstall_log = work / 'busy-setup.log', work / 'busy-uninstall.log'
        setup_exit = command(setup, install_log, ['/DIR=' + str(app), '/TASKS=desktopicon'])
        uninstall_exit = command(uninstaller, uninstall_log, [])
        assert setup_exit == 7 and uninstall_exit != 0 and probe.process.poll() is None
        assert all('HybridSign is open' in path.read_text(encoding='utf-8-sig', errors='replace')
                   for path in (install_log, uninstall_log))
        assert snapshot(app) == before and registry() is not None
        assert probe.modal('Save signed PDF') is not None
        checks['busySetupRefusalCode'] = setup_exit
        checks['busyUninstallRefusalCode'] = uninstall_exit

    probe.busy_guard = busy_guard
    probe.run(HERE.parent / 'demo_assets/sample-unsigned.pdf')
    probe.stage = 'Desktop shortcut launch'
    probe.start_shortcut(DESKTOP)
    probe.capture('installed-desktop-shortcut-launch.png')
    probe.stop()
    checks['desktopShortcutLaunch'] = True

    probe.stage = 'same-version in-place reinstall and uninstall'
    vault = work / 'original.hvault'
    signed = work / 'signed.pdf'
    protected = {p: sha(p) for p in work.iterdir() if p.suffix in ('.hvault', '.pdf')}
    # A misplaced user file at a known payload name is also protected. Restore
    # our disposable README after exercising both actual refusal paths.
    readme = app / 'README.txt'
    original_readme = readme.read_bytes()
    readme.write_bytes(signed.read_bytes())
    try:
        assert command(setup, work / 'changed-payload-setup.log', ['/DIR=' + str(app)]) == 7
        assert command(uninstaller, work / 'changed-payload-uninstall.log', []) == 1
        assert sha(readme) == sha(signed) and registry() is not None
        checks['changedManagedFilePreservedOnRefusal'] = True
    finally:
        readme.write_bytes(original_readme)
    installed_vault, installed_pdf = app / 'unexpected vault.hvault', app / 'unexpected signed.pdf'
    shutil.copyfile(vault, installed_vault)
    shutil.copyfile(signed, installed_pdf)
    unknown = {installed_vault: sha(vault), installed_pdf: sha(signed)}
    assert command(setup, work / 'in-place.log', ['/DIR=' + str(app), '/TASKS=desktopicon']) == 0
    assert {n: sha(app / n) for n in expected} == expected
    assert all(sha(p) == h for p, h in (protected | unknown).items())
    checks['inPlaceSameVersionCode'] = 0
    uninstaller = uninstall_command(app)
    assert command(uninstaller, work / 'uninstall.log', []) == 0
    probe.wait(lambda: registry() is None and not (app / 'HybridSign.exe').exists() and not uninstaller.exists())
    assert set(snapshot(app)) == {p.name for p in unknown}
    assert all(sha(p) == h for p, h in (protected | unknown).items())
    assert not START.exists() and not DESKTOP.exists()
    checks['firstUninstallCode'] = 0
    checks['outsideUserFilesPreserved'] = len(protected)
    checks['unknownFilesInsidePreserved'] = len(unknown)

    # The old folder now contains unknown files, so a fresh install refuses it.
    assert command(setup, work / 'occupied.log', ['/DIR=' + str(app)]) == 7
    assert all(sha(p) == h for p, h in unknown.items())
    checks['occupiedDirectoryRefused'] = True
    probe.stage = 'reinstall after uninstall and same-vault recovery'
    probe.app = base / 'Reinstalled application \u0111'
    assert command(setup, work / 'reinstall.log', ['/DIR=' + str(probe.app), '/TASKS=']) == 0
    assert {n: sha(probe.app / n) for n in expected} == expected
    assert START.is_file() and not DESKTOP.exists()
    uninstaller = uninstall_command(probe.app)
    probe.start_shortcut(START)
    probe.go('Key Vault'); probe.unlock(vault)
    assert probe.key_id() == probe.report['hybridKeyId']
    probe.capture('reinstalled-original-vault.png')
    probe.verify(signed, 'VALID', authenticated=True)
    probe.capture('reinstalled-original-signature-valid.png')
    probe.stop()
    assert all(sha(p) == h for p, h in protected.items())
    checks['reinstallSameVaultAndId'] = True
    checks['optionalDesktopUnchecked'] = True
    assert command(uninstaller, work / 'final-uninstall.log', []) == 0
    probe.wait(lambda: registry() is None and not uninstaller.exists())
    assert not snapshot(probe.app) and not START.exists() and not DESKTOP.exists()
    assert all(sha(p) == h for p, h in (protected | unknown).items())
    checks['finalUninstallCode'] = 0
    return {'passed': True, 'setupSha256': sha(setup), 'checks': checks, 'installedGui': probe.report}


if __name__ == '__main__':
    setup, installation, documents = (Path(arg).resolve(strict=True) for arg in sys.argv[1:4])
    evidence = Path(sys.argv[4]).resolve()
    result = run(setup, installation, documents, evidence)
    (evidence / 'installer-checks.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result), flush=True)
