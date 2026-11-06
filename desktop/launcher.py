"""Launch with: .venv/Scripts/python.exe -m desktop.launcher"""
import logging
from pathlib import Path
import sys

from .assets import BuildError, capture_build, make_server_type
from .verification_bridge import VerificationBridge
from .dialogs import NativeDialogs
from .runtime import StartupError, require_runtime
from .security import NativeGuard, NavigationPolicy
from .verification_worker import VerificationWorker as Worker


def default_build_path():
    return Path(__file__).resolve().parent.parent / "frontend" / "dist"


def launch():
    snapshot = capture_build(default_build_path())
    require_runtime()
    import webview
    logging.getLogger("pywebview").setLevel(logging.CRITICAL)
    webview.settings.update({"ALLOW_DOWNLOADS": False, "ALLOW_FILE_URLS": False,
                             "OPEN_EXTERNAL_LINKS_IN_BROWSER": False,
                             "OPEN_DEVTOOLS_IN_DEBUG": False, "REMOTE_DEBUGGING_PORT": None})
    worker = Worker()
    bridge = VerificationBridge(worker, trusted=lambda: False)
    server_type = make_server_type(snapshot)
    guard, failures = [], []
    window = webview.create_window("HybridSign — Desktop Preview", str(snapshot.root / "index.html"),
                                   js_api=bridge, width=1280, height=800, min_size=(960, 600),
                                   resizable=True, background_color="#f7f8fb", text_select=True)
    bridge._dialogs = NativeDialogs(window)

    def initialized(renderer):
        if renderer != "edgechromium":
            failures.append("WebView2 renderer unavailable; no fallback is permitted.")
            return False
        try:
            instance = webview.http.global_server
            policy = NavigationPolicy(instance.address, snapshot.assets)
            security = NativeGuard(window, bridge, policy)
            guard.append(security)
            window.events.before_show += security.install
        except Exception:
            failures.append("Desktop security initialization failed.")
            return False

    def closing():
        if hasattr(worker, 'sign_busy') and worker.sign_busy():
            bridge._dialogs.signing_close_notice()
            return False
        bridge._close()
        for item in guard:
            item.close()

    window.events.initialized += initialized
    window.events.closing += closing
    try:
        worker.start()
        icon = Path(__file__).resolve().parent.parent / "logobig.ico"
        webview.start(gui="edgechromium", debug=False, http_server=True,
                      server=server_type, private_mode=True, icon=str(icon) if icon.is_file() else None)
        if failures or any(item.failed for item in guard) or not guard:
            raise StartupError("Desktop security initialization failed; no fallback was used.")
    finally:
        try:
            bridge._close()
            for item in guard:
                item.close()
        finally:
            try:
                server_type.close_all()
            finally:
                if not worker.shutdown():
                    raise StartupError("Desktop worker shutdown or vault cleanup could not be confirmed.")


def main():
    try:
        launch()
        return 0
    except (BuildError, StartupError) as error:
        print(f"HybridSign: {error}", file=sys.stderr)
    except Exception:
        print("HybridSign: Desktop startup failed. Check the documented Windows prerequisites.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
