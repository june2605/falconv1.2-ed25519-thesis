"""Isolated native GUI probe; only public metadata and synthetic UI operations.

Not an exposed application API. Run by test_desktop_native.py in its own process
because pywebview/WinForms has process-global GUI state and main-thread ownership.
"""
import json
from pathlib import Path
from threading import Event
import time
import traceback
import ctypes
import threading

import webview
from desktop import launcher
from desktop.security import NativeGuard

results = {"checks": [], "passed": False}
finished = Event()
original_create = webview.create_window
original_fail = NativeGuard._fail


def diagnostic_fail(self):
    # Test-process diagnostics only; never forwarded through the bridge.
    traceback.print_exc()
    original_fail(self)


NativeGuard._fail = diagnostic_fail


def create(*args, **kwargs):
    window = original_create(*args, **kwargs)
    def probe():
        if finished.is_set():
            return
        finished.set()
        try:
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                if window.evaluate_js("document.querySelector('.preview-indicator')?.textContent.trim()") == "Desktop Connected":
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("Desktop handshake did not complete")
            results["checks"].append("desktop_connected")
            assert ctypes.windll.user32.IsWindowVisible(int(window.native.Handle.ToInt64()))
            results["windowDpi"] = int(window.native.DeviceDpi)
            methods = window.evaluate_js("Object.keys(window.pywebview.api).sort()")
            assert methods == ["get_app_info", "get_capabilities"], methods
            results["checks"].append("only_two_metadata_methods")
            window.evaluate_js("window.__probe = {}; window.pywebview.api.get_app_info().then(x => window.__probe.info=x); window.pywebview.api.get_capabilities().then(x=>window.__probe.caps=x); window.pywebview.api.get_app_info('invalid').then(x=>window.__probe.invalid=x); void 0")
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                response = window.evaluate_js("window.__probe")
                if "info" in response and "caps" in response and "invalid" in response:
                    break
                time.sleep(0.05)
            assert response["info"]["data"]["runtime"] == "pywebview-edgechromium", response
            assert response["invalid"]["error"]["code"] == "INVALID_REQUEST", response
            assert response["caps"]["data"] == {"nativeShell": True, "vaultOperations": False,
                                                "pdfSigning": False, "pdfVerification": False,
                                                "accountRegistry": False}, response
            results["metadata"] = response
            results["checks"].append("correct_metadata_and_capability_flags")
            for route, heading in [("sign", "Sign a document"), ("verify", "Verify a signature"),
                                   ("vault", "Manage your signing keys"), ("settings", "Personalize your workspace"),
                                   ("dashboard", "Your digital signing workspace")]:
                window.evaluate_js(f"window.location.hash='/{route}'; void 0")
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline and window.evaluate_js("document.querySelector('h1')?.textContent") != heading:
                    time.sleep(0.05)
                assert window.evaluate_js("document.querySelector('h1')?.textContent") == heading
            results["checks"].append("all_five_routes")
            window.evaluate_js("window.location.hash='/settings'; void 0")
            time.sleep(0.1)
            for theme in ["dark", "light"]:
                window.evaluate_js(f"document.querySelector('input[value={theme}]').click(); void 0")
                time.sleep(0.1)
                assert window.evaluate_js("document.documentElement.dataset.theme") == theme
            results["checks"].append("light_dark_themes")
            window.resize(1100, 720)
            time.sleep(0.15)
            assert window.evaluate_js("document.querySelector('main').scrollWidth <= document.querySelector('main').clientWidth")
            window.evaluate_js("window.location.hash='/verify'; void 0")
            time.sleep(0.1)
            assert window.evaluate_js("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Verify PDF').disabled")
            window.evaluate_js("window.location.hash='/sign'; void 0")
            time.sleep(0.1)
            window.evaluate_js("[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Just exploring')).click(); void 0")
            time.sleep(0.1)
            window.evaluate_js("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Preview unlock').click(); void 0")
            time.sleep(0.1)
            window.evaluate_js("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Preview unlocked state').click(); void 0")
            time.sleep(0.7)
            window.evaluate_js("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Continue to review').click(); void 0")
            time.sleep(0.1)
            assert window.evaluate_js("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Sign PDF').disabled")
            assert not window.evaluate_js("!!document.querySelector('input[type=password]')")
            results["checks"].append("crypto_actions_disabled_no_password_inputs")
            original_url = window.get_current_url().split("#")[0]
            for url in ["https://example.invalid/", "file:///C:/Windows/win.ini", "data:text/html,evil"]:
                window.evaluate_js(f"window.location.href={json.dumps(url)}; void 0")
                time.sleep(0.2)
                assert window.get_current_url().split("#")[0] == original_url
            window.evaluate_js("window.open('https://example.invalid/'); void 0")
            time.sleep(0.2)
            assert len(webview.windows) == 1
            assert window.get_current_url().split("#")[0] == original_url
            results["checks"].append("untrusted_navigation_and_popup_blocked")
            window.evaluate_js("window.chrome.webview.postMessage(['__class__.__init__','[]','123']); window.chrome.webview.postMessage(['pywebviewStateUpdate','{}','123']); void 0")
            time.sleep(0.1)
            assert window.evaluate_js("document.querySelector('.preview-indicator').textContent.trim()") == "Desktop Connected"
            results["checks"].append("unapproved_raw_messages_ignored")
            window.evaluate_js("window.location.hash='/settings'; void 0")
            time.sleep(0.1)
            window.evaluate_js("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Reset preview').click(); void 0")
            time.sleep(0.1)
            window.evaluate_js("window.location.hash='/dashboard'; void 0")
            time.sleep(0.15)
            window.evaluate_js("[...document.querySelectorAll('button[aria-label^=Dismiss]')].forEach(b=>b.click()); document.querySelector('h1').focus(); void 0")
            # Capture only this owned, foreground test window, never the desktop.
            from System import Action
            from desktop.runtime import fit_window_to_work_area
            window.native.Invoke(Action(lambda: fit_window_to_work_area(window.native)))
            window.on_top = True
            time.sleep(0.2)
            from PIL import ImageGrab
            from ctypes import wintypes
            rect = wintypes.RECT()
            hwnd = int(window.native.Handle.ToInt64())
            assert ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect)) == 0
            directory = Path("frontend/qa/phase4b1")
            directory.mkdir(parents=True, exist_ok=True)
            ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom), all_screens=True).save(directory / "native-dashboard.png")
            results["windowVisible"] = True
            results["passed"] = True
        except Exception as error:
            results["error"] = str(error)
            traceback.print_exc()
        finally:
            window.destroy()
    window.events.loaded += probe
    return window


webview.create_window = create
exit_code = launcher.main()
results["exitCode"] = exit_code
results["ownedThreadsStopped"] = not any(thread.name.startswith("HybridSign-") for thread in threading.enumerate())
results["cryptoModulesImported"] = any(name in __import__('sys').modules for name in ("vault", "sign", "verify", "hybrid_keys"))
if results["passed"] and exit_code == 0:
    Path("frontend/qa/phase4b1/native-checks.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
print("NATIVE_PROBE=" + json.dumps(results), flush=True)
raise SystemExit(0 if results["passed"] and exit_code == 0 else 1)
