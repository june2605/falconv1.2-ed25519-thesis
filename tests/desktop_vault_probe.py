"""GUI driver only: no production test/debug API, credentials stay in Python."""
import ctypes
import json
from pathlib import Path
import sys
import threading
import time
import traceback

import webview
from desktop import launcher
from desktop.dialogs import NativeDialogs
import desktop.vault_service as service
import vault_io

control = json.loads(sys.stdin.buffer.readline())
signing = control.get('signing', False)
mode, vault_path, password = control["mode"], Path(control["path"]), control.pop("password")
results = {"passed": False, "maskedNativePassword": False, "guiThreadConfirmed": False,
           "shutdownLockedOnWorker": False, "noSecretBridgeOrDiskWrites": True, "generatedPairs": 0}
gui_ids, pairs, password_modes = [], [], []
original_create = webview.create_window
original_form, original_file = NativeDialogs._build_password_dialog, NativeDialogs._file_dialog
original_gen, original_lock = service.generate_hybrid_key_pair, service.lock_vault
original_write = vault_io._write_candidate_bytes
original_unlock = service.unlock_vault
file_choices = 0


def capture(window, name, *, current=False):
    """Owned window bounds only; never capture a desktop or unmasked input."""
    from PIL import ImageGrab
    from ctypes import wintypes
    rect = wintypes.RECT()
    hwnd = int(window.native.Handle.ToInt64())
    assert ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect)) == 0
    directory = Path('frontend/qa/phase4b3a') if signing else Path("frontend/qa/phase4b2a1" if current else "frontend/qa/phase4b2a")
    directory.mkdir(parents=True, exist_ok=True)
    ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom), all_screens=True).save(directory / name)


def unlock_with_visible_progress(*args):
    # Test-only delay makes the actual worker phase observable on fast hardware.
    time.sleep(0.35)
    return original_unlock(*args)


def generate():
    assert mode == "create", "Reopen must not generate new keys"
    pair = original_gen()
    pairs.append(pair)
    results["generatedPairs"] += 1
    return pair


def locked(handle):
    original_lock(handle)
    results["shutdownLockedOnWorker"] = handle.is_locked and threading.current_thread().name == "HybridSign-worker"


def write(stream, data):
    assert len(data) == 2416 and password.encode() not in data
    for pair in pairs:
        assert pair.ed25519_private_seed not in data and pair.falcon_private_key not in data
        assert pair.ed25519_private_seed.hex().encode() not in data
        assert pair.falcon_private_key.hex().encode() not in data
    return original_write(stream, data)


service.generate_hybrid_key_pair, service.lock_vault = generate, locked
service.unlock_vault = unlock_with_visible_progress
vault_io._write_candidate_bytes = write


def file_selection(self, creating):
    global file_choices
    from System.Threading import Thread
    assert int(Thread.CurrentThread.ManagedThreadId) == gui_ids[0]
    # Native file accept is a Python-only seam; real save/open pickers are
    # separately configured/tested and require manual acceptance validation.
    file_choices += 1
    return str(vault_path)


def password_form(self, creating):
    from System.Threading import Thread
    from System.Windows.Forms import Timer
    assert int(Thread.CurrentThread.ManagedThreadId) == gui_ids[0]
    try:
        form, boxes, error, ok = original_form(self, creating)
    except Exception:
        traceback.print_exc()  # Construction occurs before any password is set.
        raise
    assert all(box.UseSystemPasswordChar and box.MaxLength == 1024 for box in boxes)
    assert all(not str(box.Text) for box in boxes)  # Passwords are never remembered.
    results["maskedNativePassword"] = results["guiThreadConfirmed"] = True
    behavior = password_modes.pop(0) if password_modes else "valid"
    timer = Timer()
    timer.Interval = 700 if behavior == "retry" else 120
    def tick(*_):
        timer.Stop()
        if behavior == "cancel":
            form.CancelButton.PerformClick()
        else:
            if behavior == "retry":
                capture(self._window, "retrying.png", current=True)  # Empty masked native controls.
            for box in boxes:
                box.Text = "incorrect native password" if behavior == "wrong" else password
            ok.PerformClick()
    timer.Tick += tick
    form.Shown += lambda *_: timer.Start()
    form.FormClosed += lambda *_: timer.Dispose()
    return form, boxes, error, ok


NativeDialogs._file_dialog = file_selection
NativeDialogs._build_password_dialog = password_form

if signing:
    import desktop.signing_service as signing_service
    from desktop.pdf_io import output_choice
    from signing_io import SigningTransaction
    original_sign = signing_service.sign_vault_document
    original_stage, original_candidate = SigningTransaction.write_stage, SigningTransaction.write_candidate

    def sign_on_owner(*args):
        assert threading.current_thread().name == 'HybridSign-worker'
        time.sleep(1.5)  # Observe an actual pending operation and a native close attempt.
        return original_sign(*args)

    def no_plaintext(data):
        assert password.encode() not in data
        for pair in pairs:
            for secret in (pair.ed25519_private_seed, pair.falcon_private_key):
                assert secret not in data and secret.hex().encode() not in data

    def stage(self, name, data):
        no_plaintext(data)
        return original_stage(self, name, data)

    def candidate(self, data):
        no_plaintext(data)
        return original_candidate(self, data)

    def pdf_dialog(self, saving, suggested_name=None):
        from System.Threading import Thread
        assert int(Thread.CurrentThread.ManagedThreadId) == gui_ids[0]
        return output_choice(control['output']) if saving else control['input']

    def close_notice(self):
        from System.Threading import Thread
        assert int(Thread.CurrentThread.ManagedThreadId) == gui_ids[0]
        results['activeClosePrevented'] = True

    signing_service.sign_vault_document = sign_on_owner
    SigningTransaction.write_stage, SigningTransaction.write_candidate = stage, candidate
    NativeDialogs._pdf_dialog = pdf_dialog
    NativeDialogs.signing_close_notice = close_notice


def create(*args, **kwargs):
    window = original_create(*args, **kwargs)
    def shown():
        from System.Threading import Thread
        gui_ids.append(int(Thread.CurrentThread.ManagedThreadId))
    window.events.before_show += shown
    def probe():
        try:
            def wait(expression, timeout=8):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    value = window.evaluate_js(expression)
                    if value:
                        return value
                    time.sleep(0.04)
                raise AssertionError("Native UI condition did not complete")
            def click(label):
                # Native modal focus-return can start a state refresh before
                # React commits its disabled buttons. Require a stable enabled
                # control rather than clicking that old frame and losing the
                # synthetic click to the provider's existing admission gate.
                wait(f"""(()=>{{
                  const label={json.dumps(label)};
                  const b=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()===label && !b.disabled);
                  if(!b){{window.__probeButtonReady=null; return false;}}
                  const ready=window.__probeButtonReady;
                  if(!ready || ready.button!==b || ready.label!==label){{
                    window.__probeButtonReady={{button:b,label,at:performance.now()}}; return false;
                  }}
                  if(performance.now()-ready.at<200)return false;
                  window.__probeButtonReady=null; b.click(); return true;
                }})()""")
            wait("document.querySelector('.preview-indicator')?.textContent.trim()==='Desktop'")
            window.evaluate_js("window.location.hash='/vault'; void 0")
            wait("!![...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Create Vault' && !b.disabled)")
            if mode == "create":
                def cancel_real_file_dialogs():
                    from ctypes import wintypes
                    from System.Windows.Forms import Timer
                    from System.Threading import Thread
                    assert int(Thread.CurrentThread.ManagedThreadId) == gui_ids[0]
                    user = ctypes.windll.user32
                    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                    user.EnumThreadWindows.argtypes = [wintypes.DWORD, callback_type, wintypes.LPARAM]
                    user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
                    for creating in [True, False]:
                        provider = NativeDialogs(window)
                        timer = Timer()
                        timer.Interval = 150
                        expected = "HybridSign - Save a new encrypted vault" if creating else "HybridSign - Open encrypted vault"
                        def cancel_owned(*_):
                            def visit(hwnd, _):
                                title = ctypes.create_unicode_buffer(256)
                                user.GetWindowTextW(hwnd, title, 256)
                                if title.value == expected:
                                    user.PostMessageW(hwnd, 0x10, 0, 0)
                                return True
                            user.EnumThreadWindows(ctypes.windll.kernel32.GetCurrentThreadId(), callback_type(visit), 0)
                        timer.Tick += cancel_owned
                        try:
                            timer.Start()
                            assert original_file(provider, creating) is None
                        finally:
                            timer.Stop()
                            timer.Dispose()
                    return True
                results["nativeFileDialogsCancelled"] = NativeDialogs(window)._on_gui(cancel_real_file_dialogs)
            if mode == "create":
                password_modes.append("cancel")
                click("Create Vault")
                wait("!![...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Create Vault' && !b.disabled)")
                assert not vault_path.exists()
                password_modes.append("valid")
                click("Create Vault")
                wait("!!document.querySelector('.vault-name')")
                assert vault_path.stat().st_size == 2416
                before = vault_path.read_bytes()
                password_modes.append("valid")
                click("Unlock Vault")
                wait("document.querySelector('.vault-status-line')?.textContent.includes('Unlocked')")
                click("Lock Vault")
                wait("document.querySelector('.vault-status-line')?.textContent.includes('Locked')")
                wait("document.querySelector('.toast-region').textContent.includes('Vault locked')")
                expected_id = window.evaluate_js("document.querySelector('.vault-id code').textContent")
                password_modes.append("wrong")
                click("Unlock Vault")
                wait("!!document.querySelector('[role=alert]')")
                assert vault_path.read_bytes() == before
                assert window.evaluate_js("document.querySelector('[role=alert]').textContent.includes(\"Couldn't unlock vault\")")
                assert not window.evaluate_js("document.querySelector('main').textContent.includes('Vault status unconfirmed')")
                assert not window.evaluate_js("document.querySelector('.toast-region').textContent.includes('Vault locked')")
                assert window.evaluate_js("document.querySelector('.vault-status-line').textContent.includes('Locked')")
                window.on_top = True
                capture(window, "wrong-password.png", current=True)
            choices_before_retry = file_choices
            password_modes.append("retry" if mode == "create" else "valid")
            click("Try Again" if mode == "create" else "Unlock Vault")
            if mode == "create":
                wait("document.querySelector('[data-vault-progress]')?.textContent==='Waiting for password'")
                wait("document.querySelector('[data-vault-progress]')?.textContent==='Unlocking vault'")
            wait("document.querySelector('.vault-status-line')?.textContent.includes('Unlocked')")
            if mode == "create":
                assert file_choices == choices_before_retry
                assert window.evaluate_js("document.querySelector('.vault-id code').textContent") == expected_id
                assert not window.evaluate_js("!!document.querySelector('[role=alert]')")
                time.sleep(0.25)  # Let existing success/motion styles settle for review.
                capture(window, "successful-unlock.png", current=True)
                click("Lock Vault")
                wait("document.querySelector('.vault-status-line')?.textContent.includes('Locked')")
                password_modes.append("cancel")
                click("Unlock Vault")
                wait("!![...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Unlock Vault' && !b.disabled)")
                assert not window.evaluate_js("!!document.querySelector('[role=alert]')")
                assert not window.evaluate_js("document.querySelector('.toast-region').textContent.includes('Vault locked')")
                assert window.evaluate_js("document.querySelector('.vault-status-line').textContent.includes('Locked')")
                assert vault_path.read_bytes() == before
                results["authenticationUx"] = True
                password_modes.append("valid")
                click("Unlock Vault")
                wait("document.querySelector('.vault-status-line')?.textContent.includes('Unlocked')")
            window.evaluate_js("window.__publicVault = null; window.pywebview.api.get_vault_state().then(x=>window.__publicVault=x); void 0")
            reply = wait("window.__publicVault")
            assert reply["ok"] is True and reply["data"]["vault"]["state"] == "unlocked"
            public = reply["data"]["vault"]
            encoded = json.dumps(reply)
            assert password not in encoded and str(vault_path.parent) not in encoded
            assert not window.evaluate_js("!!document.querySelector('input[type=password]')")
            for pair in pairs:
                assert pair.ed25519_private_seed.hex() not in encoded and pair.falcon_private_key.hex() not in encoded
            results["public"] = {key: public[key] for key in ["hybridKeyId", "ed25519PublicKey", "falconPublicKey"]}
            click("Lock Vault")
            wait("document.querySelector('.vault-status-line')?.textContent.includes('Locked')")
            window.evaluate_js(f"window.__stale = null; window.pywebview.api.lock_vault({json.dumps(public['vaultId'])}, {json.dumps(public['sessionId'])}).then(x=>window.__stale=x); void 0")
            assert wait("window.__stale")["error"]["code"] == "STALE_SESSION"
            password_modes.append("valid")
            click("Unlock Vault")
            wait("document.querySelector('.vault-status-line')?.textContent.includes('Unlocked')")
            results["nativeExplicitLockAndStaleRejection"] = True
            assert not window.evaluate_js("document.querySelector('main').textContent.includes('DEMO VAULT')")
            if signing:
                from verify import verify_file_with_public_keys, verify_bytes
                source, output = Path(control['input']), Path(control['output'])
                source_before, vault_before = source.read_bytes(), vault_path.read_bytes()
                files_before = set(source.parent.rglob('*'))
                window.evaluate_js("[...document.querySelectorAll('button[aria-label^=Dismiss]')].forEach(b=>b.click()); void 0")
                window.evaluate_js("window.location.hash='/sign'; void 0")
                click('Choose PDF')
                click('Continue to review')
                time.sleep(.15)
                capture(window, 'signing-review.png')
                click('Sign PDF')
                wait("document.querySelector('main').textContent.includes('Signing and checking the PDF')")
                from System import Action
                window.native.BeginInvoke(Action(window.native.Close))
                deadline = time.monotonic() + 2
                while not results.get('activeClosePrevented') and time.monotonic() < deadline:
                    time.sleep(.02)
                assert results.get('activeClosePrevented') and not window.native.IsDisposed
                wait("!![...document.querySelectorAll('h2')].find(x=>x.textContent==='Signed PDF saved')", timeout=20)
                assert output.exists() and source.read_bytes() == source_before
                assert vault_path.read_bytes() == vault_before and vault_path.stat().st_size == 2416
                ed, falcon = bytes.fromhex(public['ed25519PublicKey']), bytes.fromhex(public['falconPublicKey'])
                verified = verify_file_with_public_keys(output, ed, falcon)
                assert verified[0] is True
                tampered = output.read_bytes().replace(b'%PDF-', b'%PDE-', 1)
                assert verify_bytes(tampered, ed, falcon)[0] is False
                assert set(source.parent.rglob('*')) - files_before == {output}
                assert not window.evaluate_js("!!document.querySelector('input[type=password], input[type=file]')")
                results['signingEvidence'] = {'outputExists': True, 'sourceUnchanged': True,
                    'vaultUnchangedAndEncrypted': True, 'diskVerifierAccepted': True,
                    'tamperRejected': True, 'noPrivateKeyFiles': True, 'selfVerifiedShown': True,
                    'outputBytes': output.stat().st_size}
                time.sleep(.2)
                capture(window, 'signing-completed.png')
            if mode == "create":
                window.evaluate_js("[...document.querySelectorAll('button[aria-label^=Dismiss]')].forEach(b=>b.click()); void 0")
                window.on_top = True
                time.sleep(0.15)
                capture(window, "native-vault.png")
            results["passed"] = True
        except Exception:
            traceback.print_exc()  # Test assertions contain public status only.
        finally:
            window.destroy()  # Intentionally close while unlocked.
    window.events.loaded += probe
    return window


webview.create_window = create
exit_code = launcher.main()
results["ownedThreadsStopped"] = not any(thread.name.startswith("HybridSign-") for thread in threading.enumerate())
if results["passed"] and exit_code == 0:
    report_dir = Path('frontend/qa/phase4b3a' if signing else 'frontend/qa/phase4b2a')
    (report_dir / ('vault-' + mode + '-checks.json')).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
print("VAULT_PROBE=" + json.dumps(results), flush=True)
raise SystemExit(0 if results["passed"] and exit_code == 0 else 1)
