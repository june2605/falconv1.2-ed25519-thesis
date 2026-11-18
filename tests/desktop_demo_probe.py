"""Private, visible Windows demo driver. Never installed/exposed by the app.

Real Open/Save dialogs are accepted through their native filename controls.
The real masked password form is filled locally on its GUI thread. No path or
password is injected into JavaScript and no private key is exported.
"""
from collections import deque
import ctypes
from ctypes import wintypes
import faulthandler
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import time

import webview
from desktop import launcher, vault_service, signing_service
from desktop.dialogs import NativeDialogs
from signing_io import SigningTransaction
import vault_io
from verify import verify_file_with_public_keys


control = json.loads(sys.stdin.buffer.readline())
paths = {name: Path(control[name]) for name in ('source', 'output', 'tampered', 'corrupted', 'vault', 'wrong', 'invalid')}
password = control.pop('password')
mode = control['mode']
qa = Path('frontend/qa/phase4c1')
qa.mkdir(parents=True, exist_ok=True)
report = {'passed': False, 'mode': mode, 'generatedPairs': 0,
          'nativePasswordsMasked': True, 'nativeDialogsAccepted': False,
          'noPlaintextKeyWrites': True, 'workerOwnership': True, 'dialogs': []}
plans, passwords, gui_ids, pairs = deque(), deque(), [], []
release_sign, sign_finished = threading.Event(), threading.Event()
stage = 'startup'
diagnostics_done = threading.Event()


def diagnostics():
    last = None
    while not diagnostics_done.wait(.5):
        if stage != last:
            print('DEMO_STAGE=' + json.dumps({'mode': mode, 'stage': stage,
                  'completedDialogs': len(report['dialogs'])}), flush=True)
            last = stage


diagnostic_thread = threading.Thread(target=diagnostics, name='DemoDiagnostics', daemon=True)
diagnostic_thread.start()

user = ctypes.windll.user32
callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user.EnumThreadWindows.argtypes = [wintypes.DWORD, callback_type, wintypes.LPARAM]
user.EnumChildWindows.argtypes = [wintypes.HWND, callback_type, wintypes.LPARAM]
user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user.GetDlgItem.argtypes, user.GetDlgItem.restype = [wintypes.HWND, ctypes.c_int], wintypes.HWND
user.GetFocus.restype = user.GetForegroundWindow.restype = wintypes.HWND
user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user.IsChild.argtypes = [wintypes.HWND, wintypes.HWND]
user.IsWindowVisible.argtypes = [wintypes.HWND]
user.SetForegroundWindow.argtypes = [wintypes.HWND]
user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
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
    values = (Input * len(events))(*(Input(1, InputUnion(keyboard=KeyboardInput(vk, scan, flags, 0, 0))) for vk, scan, flags in events))
    assert user.SendInput(len(values), values, ctypes.sizeof(Input)) == len(values)


def chord(modifier, letter):
    keyboard([(modifier, 0, 0), (letter, 0, 0), (letter, 0, 2), (modifier, 0, 2)])


def text_of(hwnd, *, classname=False):
    buffer = ctypes.create_unicode_buffer(512)
    (user.GetClassNameW if classname else user.GetWindowTextW)(hwnd, buffer, len(buffer))
    return buffer.value


def windows_on_thread():
    found = []
    def visit(hwnd, _):
        found.append((hwnd, text_of(hwnd)))
        return True
    user.EnumThreadWindows(ctypes.windll.kernel32.GetCurrentThreadId(), callback_type(visit), 0)
    return found


def dialog_input_state(hwnd):
    foreground = user.GetForegroundWindow()
    process = wintypes.DWORD()
    user.GetWindowThreadProcessId(foreground, ctypes.byref(process))
    focus = user.GetFocus()
    return {'dialogForeground': foreground == hwnd, 'ownedForeground': process.value == os.getpid(),
            'focusedEdit': bool(focus and user.IsChild(hwnd, focus) and 'Edit' in text_of(focus, classname=True))}


def labelled_button(parent, label):
    found = []
    def visit(hwnd, _):
        if text_of(hwnd, classname=True) == 'Button' and text_of(hwnd).replace('&', '').strip() == label:
            found.append(hwnd)
        return True
    user.EnumChildWindows(parent, callback_type(visit), 0)
    return found[0] if found else None


def actual_dialog(provider, kind, original, *args, **kwargs):
    """Automate only this GUI thread's exact owned modal; never return a fake selection."""
    from System.Threading import Thread
    from System.Windows.Forms import Timer
    assert int(Thread.CurrentThread.ManagedThreadId) == gui_ids[0]
    planned_kind, destination, approval = plans.popleft()
    assert planned_kind == kind
    titles = {
        'vault-save': 'HybridSign \u2014 Save a new encrypted vault',
        'vault-open': 'HybridSign \u2014 Open encrypted vault',
        'pdf-open': 'HybridSign \u2014 Choose unsigned PDF',
        'pdf-save': 'HybridSign \u2014 Save signed PDF',
        'verify-open': 'HybridSign \u2014 Choose signed PDF',
        'notice': 'HybridSign \u2014 Operation in progress',
    }
    timer, status, errors = Timer(), ['waiting'], []
    timer.Interval = 150
    deadline = time.monotonic() + 10
    saw_confirmation = []
    shown_dialog, filename_matched = [], []
    owner_handle = 0
    previous_confirmation = 0
    def tick(*_):
        nonlocal owner_handle, previous_confirmation
        try:
            owned = windows_on_thread()
            if time.monotonic() > deadline:
                errors.append({'phase': status[0], 'error': 'native dialog deadline',
                               **dialog_input_state(owner_handle)})
                for hwnd, title in owned:
                    if title in (titles[kind], 'Confirm Save As') or text_of(hwnd, classname=True) == '#32770':
                        user.PostMessageW(hwnd, 0x10, 0, 0)
                return
            if kind == 'pdf-save' and status[0] == 'submitted':
                for hwnd, _ in owned:
                    if previous_confirmation == hwnd:
                        continue
                    yes, no = labelled_button(hwnd, 'Yes'), labelled_button(hwnd, 'No')
                    if yes and no and user.IsWindowVisible(yes) and user.IsWindowVisible(no):
                        if 'Yes' not in text_of(yes) or 'No' not in text_of(no):
                            continue
                        saw_confirmation.append(bool(approval))
                        previous_confirmation = hwnd
                        assert user.PostMessageW(yes if approval else no, 0xF5, 0, 0)
                        status[0] = 'submitted' if approval else 'rejected-overwrite'
                        return
            for hwnd, title in owned:
                if title != titles[kind]:
                    continue
                owner_handle = hwnd
                if kind == 'notice':
                    button = labelled_button(hwnd, 'OK') or user.GetDlgItem(hwnd, 1)
                    if button:
                        report['activeCloseRefused'] = True
                        user.SendMessageW(button, 0xF5, 0, 0)
                    return
                if destination is None or status[0] == 'rejected-overwrite':
                    user.PostMessageW(hwnd, 0x10, 0, 0)
                    return
                if status[0] not in ('waiting', 'focused', 'typing'):
                    return
                if user.GetForegroundWindow() != hwnd:
                    user.SetForegroundWindow(hwnd)
                    return  # Wait for Windows to activate the intended modal before typing.
                if status[0] == 'waiting':
                    chord(0x12, ord('N'))  # Native Alt+N; do not block the modal GUI thread.
                    status[0] = 'focused'
                    return
                focus = user.GetFocus()
                report['fileEditClass'] = text_of(focus, classname=True)
                if not (focus and user.IsChild(hwnd, focus) and 'Edit' in report['fileEditClass']):
                    return  # Alt+N posts input. Its focus change can arrive on a later tick.
                if status[0] == 'focused':
                    chord(0x11, ord('A'))
                    units = str(destination).encode('utf-16-le')
                    events = []
                    for offset in range(0, len(units), 2):
                        unit = int.from_bytes(units[offset:offset + 2], 'little')
                        events.extend([(0, unit, 4), (0, unit, 6)])
                    keyboard(events)
                    status[0] = 'typing'
                    return
                if text_of(focus) != str(destination):
                    return
                filename_matched.append(True)
                shown_dialog.append(provider._active)
                status[0] = 'submitted'
                submit = user.GetDlgItem(hwnd, 1)
                assert submit and user.IsChild(hwnd, submit)
                assert user.PostMessageW(submit, 0xF5, 0, 0)  # Activate the actual native button once.
                return
        except Exception as error:
            errors.append({'phase': status[0], 'error': type(error).__name__,
                           **dialog_input_state(owner_handle)})
            for hwnd, title in windows_on_thread():
                if title in (titles[kind], 'Confirm Save As'):
                    user.PostMessageW(hwnd, 0x10, 0, 0)
    timer.Tick += tick
    try:
        timer.Start()
        result = original(provider, *args, **kwargs)
    finally:
        timer.Stop(); timer.Dispose()
    accepted_path = result.path if result is not None and kind == 'pdf-save' else result
    report['dialogs'].append({'kind': kind, 'accepted': result is not None,
                              'matchedRequested': result is not None and kind != 'notice' and Path(accepted_path) == destination,
                              'selectedName': Path(accepted_path).name if result is not None and kind != 'notice' else None,
                              'finalName': Path(str(shown_dialog[-1].FileName)).name if shown_dialog else None,
                              'filenameControlMatched': bool(filename_matched) and all(filename_matched),
                              'automationErrors': errors,
                              'overwrite': saw_confirmation[-1] if saw_confirmation else None})
    assert not errors, 'Native dialog automation failed: ' + kind
    if kind == 'notice':
        return result
    if destination is None or approval is False:
        assert result is None
    else:
        accepted = result.path if kind == 'pdf-save' else result
        assert accepted is not None and Path(accepted) == destination
        report['nativeDialogsAccepted'] = True
    return result


original_file = NativeDialogs._file_dialog
original_pdf = NativeDialogs._pdf_dialog
original_form = NativeDialogs._build_password_dialog
original_notice = NativeDialogs.signing_close_notice
NativeDialogs._file_dialog = lambda self, creating: actual_dialog(self, 'vault-save' if creating else 'vault-open', original_file, creating)
NativeDialogs._pdf_dialog = lambda self, suggested_name, verification=False: actual_dialog(self,
    'pdf-save' if suggested_name is not None else 'verify-open' if verification else 'pdf-open',
    original_pdf, suggested_name, verification=verification)
NativeDialogs.signing_close_notice = lambda self: actual_dialog(self, 'notice', original_notice)


def password_form(self, creating):
    from System.Threading import Thread
    from System.Windows.Forms import Timer
    assert int(Thread.CurrentThread.ManagedThreadId) == gui_ids[0]
    form, boxes, error, ok = original_form(self, creating)
    assert all(box.UseSystemPasswordChar and not str(box.Text) for box in boxes)
    behavior = passwords.popleft()
    timer = Timer(); timer.Interval = 180
    def fill(*_):
        timer.Stop()
        if behavior == 'cancel':
            form.CancelButton.PerformClick()
        else:
            for box in boxes:
                box.Text = secrets.token_urlsafe(24) if behavior == 'wrong' else password
            ok.PerformClick()
    timer.Tick += fill
    form.Shown += lambda *_: timer.Start()
    form.FormClosed += lambda *_: timer.Dispose()
    return form, boxes, error, ok


NativeDialogs._build_password_dialog = password_form
original_generate, original_unlock, original_lock = vault_service.generate_hybrid_key_pair, vault_service.unlock_vault, vault_service.lock_vault
original_sign = signing_service.sign_vault_document
original_write = vault_io._write_candidate_bytes
original_stage, original_candidate = SigningTransaction.write_stage, SigningTransaction.write_candidate


def owned():
    assert threading.current_thread().name == 'HybridSign-worker'


def generate():
    owned(); assert mode == 'create'
    report['generatedPairs'] += 1
    pair = original_generate(); pairs.append(pair)
    return pair


def unlock(*args):
    owned(); return original_unlock(*args)


def lock(handle):
    owned(); original_lock(handle)
    assert handle.is_locked


def no_secrets(data):
    assert password.encode() not in data
    for pair in pairs:
        for secret in (pair.ed25519_private_seed, pair.falcon_private_key):
            assert secret not in data and secret.hex().encode() not in data


def write(stream, data):
    no_secrets(data); return original_write(stream, data)


def stage_write(self, name, data):
    no_secrets(data); return original_stage(self, name, data)


def candidate_write(self, data):
    no_secrets(data); return original_candidate(self, data)


def sign(*args):
    owned(); report['signingCalls'] = report.get('signingCalls', 0) + 1
    try:
        assert release_sign.wait(25)  # Test-only hold; real signer runs after operation-safety checks.
        return original_sign(*args)
    finally:
        sign_finished.set()


vault_service.generate_hybrid_key_pair, vault_service.unlock_vault, vault_service.lock_vault = generate, unlock, lock
signing_service.sign_vault_document = sign
vault_io._write_candidate_bytes = write
SigningTransaction.write_stage, SigningTransaction.write_candidate = stage_write, candidate_write
original_create = webview.create_window


def create(*args, **kwargs):
    window = original_create(*args, **kwargs)
    def shown():
        from System.Threading import Thread
        gui_ids.append(int(Thread.CurrentThread.ManagedThreadId))
    window.events.before_show += shown
    def probe():
        global stage
        try:
            def wait(expression, timeout=15):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    value = window.evaluate_js(expression)
                    if value: return value
                    time.sleep(.04)
                raise AssertionError('Visible demo condition did not settle: ' + expression)
            def click(label):
                wait(f"(()=>{{const b=[...document.querySelectorAll('button')].find(n=>(n.getAttribute('aria-label')||n.textContent.trim())==={json.dumps(label)}&&!n.disabled);if(!b)return false;b.click();return true;}})()")
            def go(route):
                window.evaluate_js(f"document.querySelector('.smart-sidebar a[href=\"#/{route}\"]').click();void 0")
                wait(f"location.hash==='#/{route}'&&!!document.querySelector('.nav-item.active[href=\"#/{route}\"]')")
            def api(method, args=()):
                window.evaluate_js(f"window.__demoReply=null;window.pywebview.api[{json.dumps(method)}](...{json.dumps(args)}).then(r=>window.__demoReply=r);void 0")
                return wait('window.__demoReply')
            def capture(name):
                from PIL import ImageGrab
                time.sleep(.18)
                rect = wintypes.RECT()
                assert ctypes.windll.dwmapi.DwmGetWindowAttribute(int(window.native.Handle.ToInt64()), 9, ctypes.byref(rect), ctypes.sizeof(rect)) == 0
                ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom), all_screens=True).save(qa / name)
            def choose(kind, path, label, approval=True):
                completed_before = len(report['dialogs'])
                plans.append((kind, path, approval)); click(label)
                deadline = time.monotonic() + 15
                while len(report['dialogs']) == completed_before and time.monotonic() < deadline:
                    time.sleep(.025)
                assert len(report['dialogs']) > completed_before, 'Native picker did not complete'
                result = report['dialogs'][completed_before]
                assert not result['automationErrors'], f'Native picker automation failed: {result}'
                if path is not None and approval:
                    assert result['accepted'] and result['matchedRequested'] and result['filenameControlMatched'], result
                else:
                    assert not result['accepted'], result
                wait("!![...document.querySelectorAll('button')].find(n=>(n.getAttribute('aria-label')||n.textContent.trim())===" + json.dumps(label) + "&&!n.disabled)"
                     + ("||document.querySelector('.vault-status-line')?.textContent.includes('Unlocked')" if label == 'Unlock Vault' else ''))
                # Returning focus from a modal also refreshes native vault state.
                # Wait for that read-only phase, not an old enabled DOM frame.
                time.sleep(.2)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    status = api('get_vault_state')
                    if status['ok'] and status['data']['operation'] == 'idle': break
                    time.sleep(.04)
                else: raise AssertionError('Native focus refresh did not settle')
            def verify(expected):
                previous = api('get_verification_state')['data']['operationId']
                click('Verify PDF')
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    reply = api('get_verification_state')
                    if reply['ok'] and reply['data']['operationId'] != previous and reply['data']['state'] in ('valid', 'invalid', 'failed'):
                        break
                    time.sleep(.04)
                else:
                    raise AssertionError('Fresh native verification did not finish')
                wait("!![...document.querySelectorAll('h2')].find(n=>n.textContent==='HYBRID " + expected + "')")
                assert reply['ok'] and reply['data']['hybridValid'] is (expected == 'VALID')

            wait("document.querySelector('.preview-indicator')?.textContent==='Desktop Connected'")
            window.on_top = True
            initial = api('get_vault_state')
            assert initial['ok'] and initial['data']['vault'] is None
            assert not window.evaluate_js("!!document.querySelector('input[type=password],input[type=file]')")
            report['lockedOnRestart'] = mode == 'reopen'
            capture(mode + '-dashboard.png')
            go('vault')
            if mode == 'create':
                stage = 'real vault save and native password cancellation'
                passwords.append('cancel')
                choose('vault-save', paths['vault'], 'Create Vault')
                assert not paths['vault'].exists() and report['generatedPairs'] == 0
                stage = 'real vault creation'
                passwords.append('valid')
                choose('vault-save', paths['vault'], 'Create Vault')
                wait("document.querySelector('.vault-status-line')?.textContent.includes('Locked')")
                assert paths['vault'].stat().st_size == 2416
                capture('created-locked.png')
                stage = 'wrong native password and retry'
                passwords.append('wrong')
                choose('vault-open', paths['vault'], 'Unlock Vault')
                wait("!!document.querySelector('[role=alert]')")
                assert not window.evaluate_js("document.querySelector('.vault-status-line').textContent.includes('Unlocked')")
                accepted_before = len(report['dialogs'])
                passwords.append('valid'); click('Try Again')
                wait("document.querySelector('.vault-status-line')?.textContent.includes('Unlocked')")
                assert len(report['dialogs']) == accepted_before and report['generatedPairs'] == 1
                report['wrongPasswordRetry'] = True
            else:
                capture('reopen-no-unlocked-vault.png')
                stage = 'reopen original encrypted vault'
                passwords.append('valid')
                choose('vault-open', paths['vault'], 'Unlock Vault')
                wait("document.querySelector('.vault-status-line')?.textContent.includes('Unlocked')")

            public = api('get_vault_state')['data']['vault']
            assert public['state'] == 'unlocked'
            report['hybridKeyId'] = public['hybridKeyId']
            report['publicKeySha256'] = hashlib.sha256(bytes.fromhex(public['ed25519PublicKey']) + bytes.fromhex(public['falconPublicKey'])).hexdigest()
            assert password not in json.dumps(public)
            capture(mode + '-unlocked.png')
            click('Public key details')
            wait("!!document.querySelector('[role=dialog]')")
            assert window.evaluate_js("document.querySelector('[role=dialog]').textContent").count(public['hybridKeyId']) >= 1
            capture(mode + '-public-details.png')
            window.evaluate_js("document.querySelector('[role=dialog]').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));void 0")
            wait("!document.querySelector('[role=dialog]')")
            if mode == 'reopen':
                assert report['generatedPairs'] == 0
                assert verify_file_with_public_keys(paths['output'], bytes.fromhex(public['ed25519PublicKey']), bytes.fromhex(public['falconPublicKey']))[0] is True
                report['originalSignatureStillValid'] = True
                report['vaultSha256'] = hashlib.sha256(paths['vault'].read_bytes()).hexdigest()
                report['passed'] = True
                return

            stage = 'five screens and themes'
            for theme in ('light', 'dark'):
                go('settings')
                window.evaluate_js(f"document.querySelector('input[name=appearance][value={theme}]').click();void 0")
                for route in ('dashboard', 'sign', 'verify', 'vault', 'settings'):
                    go(route)
                    assert window.evaluate_js("document.documentElement.scrollWidth<=innerWidth&&document.querySelector('main').scrollWidth<=document.querySelector('main').clientWidth")
                    capture(theme + '-' + route + '.png')
            go('settings'); window.evaluate_js("document.querySelector('input[value=light]').click();void 0")
            go('sign')
            stage = 'real PDF open and Save cancellation'
            choose('pdf-open', None, 'Choose PDF')
            assert api('get_signing_state')['data']['state'] == 'idle'
            choose('pdf-open', paths['source'], 'Choose PDF')
            click('Continue to review'); capture('sign-review.png')
            predecessor = paths['output'].read_bytes()
            choose('pdf-save', paths['output'], 'Sign PDF', approval=False)
            assert report['dialogs'][-1]['accepted'] is False and report['dialogs'][-1]['overwrite'] is False
            assert paths['output'].read_bytes() == predecessor and not report.get('signingCalls')
            report['existingOutputPreservedOnCancel'] = True
            stage = 'signing safety and actual publication'
            plans.append(('pdf-save', paths['output'], True))
            window.evaluate_js("(()=>{const b=[...document.querySelectorAll('button')].find(n=>n.textContent.trim()==='Sign PDF');b.click();b.click();})()")
            wait("!!document.querySelector('main').textContent.includes('Signing and self-verifying')")
            go('vault')
            assert window.evaluate_js("[...document.querySelectorAll('button')].find(n=>n.textContent.trim()==='Lock Vault').disabled")
            rejected = api('lock_vault', [public['vaultId'], public['sessionId']])
            assert rejected['ok'] is False and rejected['error']['code'] == 'BUSY'
            report['lockDuringSigningRejected'] = True
            plans.append(('notice', None, True))
            from System import Action
            window.native.BeginInvoke(Action(window.native.Close))
            deadline = time.monotonic() + 5
            while not report.get('activeCloseRefused') and time.monotonic() < deadline: time.sleep(.03)
            assert report.get('activeCloseRefused') and not window.native.IsDisposed
            go('sign'); release_sign.set()
            wait("!![...document.querySelectorAll('h2')].find(n=>n.textContent==='Signed PDF saved')")
            ed, falcon = bytes.fromhex(public['ed25519PublicKey']), bytes.fromhex(public['falconPublicKey'])
            assert verify_file_with_public_keys(paths['output'], ed, falcon)[0] is True
            report['validSignedOnDisk'] = True
            report['oneSigningOperation'] = report['signingCalls'] == 1
            report['overwriteConfirmed'] = any(item['overwrite'] is True for item in report['dialogs'])
            capture('sign-completed.png')

            stage = 'invalid new signing selection must clear prior success'
            click('Choose PDF step')
            choose('pdf-open', paths['corrupted'], 'Choose PDF')
            assert not window.evaluate_js("!![...document.querySelectorAll('h2')].find(n=>n.textContent==='Signed PDF saved')")
            report['noStaleSigningSuccess'] = True

            stage = 'matching public verification'
            go('verify')
            choose('verify-open', paths['output'], 'Choose signed PDF')
            click('Use authenticated vault'); verify('VALID'); capture('verify-valid.png')
            stage = 'cancelled verification clears VALID'
            choose('verify-open', None, 'Choose signed PDF')
            wait("!![...document.querySelectorAll('h2')].find(n=>n.textContent==='No verification performed')")
            report['noStaleValid'] = True
            data = paths['output'].read_bytes()
            assert data.isascii() and data.count(b'APPROVED') == 1
            with paths['tampered'].open('xb') as target: target.write(data.replace(b'APPROVED', b'REJECTED', 1))
            assert verify_file_with_public_keys(paths['tampered'], ed, falcon)[0] is False
            choose('verify-open', paths['tampered'], 'Choose signed PDF')
            verify('INVALID'); report['tamperRejected'] = True; capture('verify-tampered.png')
            choose('verify-open', paths['corrupted'], 'Choose signed PDF')
            verify('INVALID'); report['corruptedPdfRejected'] = True
            stage = 'wrong key source and invalid vault recovery'
            choose('verify-open', paths['output'], 'Choose signed PDF')
            choose('vault-open', paths['wrong'], 'Choose encrypted vault')
            verify('INVALID'); report['wrongKeysRejected'] = True
            choose('vault-open', paths['invalid'], 'Choose encrypted vault')
            assert not window.evaluate_js("!![...document.querySelectorAll('h2')].find(n=>n.textContent==='HYBRID VALID')")
            report['invalidVaultRejected'] = window.evaluate_js("[...document.querySelectorAll('button')].find(n=>n.textContent.trim()==='Verify PDF').disabled&&!document.querySelector('.key-source-note')")
            assert report['invalidVaultRejected']
            click('Use authenticated vault'); verify('VALID')
            stage = 'lock then public-only verification'
            go('vault'); click('Lock Vault')
            wait("document.querySelector('.vault-status-line')?.textContent.includes('Locked')")
            stale = api('lock_vault', [public['vaultId'], public['sessionId']])
            assert stale['ok'] is False and stale['error']['code'] == 'STALE_SESSION'
            report['staleSessionRejected'] = True
            passwords.append('cancel')
            choose('vault-open', paths['vault'], 'Unlock Vault')
            assert api('get_vault_state')['data']['vault']['state'] == 'locked'
            report['cancelledDialogsPreservedState'] = True
            go('verify'); verify('VALID')
            report['lockedPublicVerification'] = True; capture('locked-public-valid.png')
            assert report['generatedPairs'] == 1 and paths['source'].read_bytes() == predecessor
            report['files'] = {'signedBytes': paths['output'].stat().st_size,
                               'vaultBytes': paths['vault'].stat().st_size,
                               'vaultSha256': hashlib.sha256(paths['vault'].read_bytes()).hexdigest(),
                               'sourceSha256': hashlib.sha256(paths['source'].read_bytes()).hexdigest()}
            report['passed'] = True
        except Exception as error:
            report['failure'] = {'stage': stage, 'type': type(error).__name__}
            if isinstance(error, AssertionError):
                report['failure']['condition'] = str(error)
            if stage.startswith(('invalid new signing', 'matching public', 'wrong key', 'lock then')):
                try: capture(str(Path('tmp/phase4c1-failure.png').resolve()))
                except Exception: pass
        finally:
            release_sign.set()
            if report.get('signingCalls'): sign_finished.wait(25)
            time.sleep(.2)
            window.destroy()
    window.events.loaded += probe
    return window


webview.create_window = create
faulthandler.dump_traceback_later(135)
try:
    exit_code = launcher.main()
finally:
    faulthandler.cancel_dump_traceback_later()
    diagnostics_done.set(); diagnostic_thread.join(2)
assert not diagnostic_thread.is_alive()
report['ownedThreadsStopped'] = not any(thread.name.startswith('HybridSign-') for thread in threading.enumerate())
if password in json.dumps(report):
    raise AssertionError('Demo report privacy failure')
if report['passed'] and exit_code == 0:
    (qa / (mode + '-checks.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('DEMO_PROBE=' + json.dumps(report), flush=True)
raise SystemExit(0 if report['passed'] and exit_code == 0 else 1)
