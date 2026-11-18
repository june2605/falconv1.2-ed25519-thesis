"""Visible Windows GUI driver only. No production/debug API or PDF copies."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback

import webview
from desktop import launcher
from desktop.dialogs import NativeDialogs

control = json.loads(sys.stdin.buffer.readline())
paths = {key: Path(control[key]) for key in ('signed', 'tampered', 'vault', 'wrong')}
before = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in paths.items()}
parent_files = {path.parent: set(path.parent.iterdir()) for path in paths.values()}
report = {'passed': False, 'results': [], 'noPasswordPrompt': True, 'realNativePickers': False}
original_create = webview.create_window
choices = [paths['signed'], paths['vault'], paths['tampered'], paths['vault'], paths['signed'], paths['wrong'], None]
gui = []
qa = Path('frontend/qa/phase4b3b1-interactions/native' if control.get('interactions') else 'frontend/qa/phase4b3b1-sidebar/native' if control.get('sidebar') else 'frontend/qa/phase4b3b1/native' if control.get('responsive') else 'frontend/qa/phase4b3b')
qa.mkdir(parents=True, exist_ok=True)


def no_password(*args, **kwargs):
    report['noPasswordPrompt'] = False
    raise AssertionError('Public verification must never request a password')


NativeDialogs.password = no_password


def capture(window, name):
    from PIL import ImageGrab
    time.sleep(.15)  # DOM acceptance can precede the WebView2 compositor frame.
    rect = wintypes.RECT()
    hwnd = int(window.native.Handle.ToInt64())
    assert ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect)) == 0
    ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom), all_screens=True).save(qa / name)


original_pdf_dialog = NativeDialogs._pdf_dialog

def picker(self, *, pdf):
    from System.Threading import Thread
    assert int(Thread.CurrentThread.ManagedThreadId) == gui[0]
    selected = choices.pop(0)
    if selected is not None:
        # Existing Phase 4B GUI-test pattern: accept only in private Python on
        # the GUI thread. This is not a production or JavaScript test hook.
        report['fileAcceptance'] = 'Python-only GUI-thread seam'
        return str(selected)
    from System.Windows.Forms import Timer
    timer = Timer()
    timer.Interval = 150
    user = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumThreadWindows.argtypes = [wintypes.DWORD, callback_type, wintypes.LPARAM]
    user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    def tick(*_):
        def visit(hwnd, _):
            title = ctypes.create_unicode_buffer(256)
            user.GetWindowTextW(hwnd, title, 256)
            if title.value == 'HybridSign \u2014 Choose signed PDF':
                user.PostMessageW(hwnd, 0x10, 0, 0)
                timer.Stop()
            return True
        user.EnumThreadWindows(ctypes.windll.kernel32.GetCurrentThreadId(), callback_type(visit), 0)
    timer.Tick += tick
    try:
        timer.Start()
        assert original_pdf_dialog(self, None, verification=True) is None
        report['realNativePickers'] = True
        report['realNativeCancellation'] = True
        return None
    finally:
        timer.Stop(); timer.Dispose()

NativeDialogs._pdf_dialog = lambda self, suggested_name, verification=False: picker(self, pdf=True)
NativeDialogs._file_dialog = lambda self, creating: picker(self, pdf=False)

def create(*args, **kwargs):
    window = original_create(*args, **kwargs)
    def before_show():
        from System.Threading import Thread
        gui.append(int(Thread.CurrentThread.ManagedThreadId))
    window.events.before_show += before_show
    def probe():
        try:
            def wait(expression, timeout=20):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    value = window.evaluate_js(expression)
                    if value: return value
                    time.sleep(.04)
                raise AssertionError('Visible native verification condition did not settle: ' + expression)
            def click(label):
                wait(f"(()=>{{const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==={json.dumps(label)}&&!x.disabled);if(!b)return false;b.click();return true;}})()")
            pointer_listener = """window.addEventListener('pointermove', event => {
                window.__nativePointer = [event.clientX, event.clientY];
            }, {capture: true, passive: true}); void 0"""
            def move_pointer(x, y):
                # Move the real cursor in the WebView's physical client area.
                # Wait for the renderer to observe the event before advancing.
                user = ctypes.windll.user32
                user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
                user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
                user.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
                user.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
                user.SetPhysicalCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
                user.GetForegroundWindow.restype = wintypes.HWND
                user.SetForegroundWindow.argtypes = [wintypes.HWND]
                user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
                hwnd = int(window.native.Handle.ToInt64())
                view = provider._on_gui(lambda: int(window.native.webview.Handle.ToInt64()))
                rect, origin = wintypes.RECT(), wintypes.POINT(0, 0)
                viewport = window.evaluate_js('({width:innerWidth,height:innerHeight})')
                previous = user.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))  # Per-monitor aware v2.
                assert previous, 'Cannot read physical window coordinates'
                try:
                    assert user.GetClientRect(view, ctypes.byref(rect))
                    assert user.ClientToScreen(view, ctypes.byref(origin))
                finally:
                    user.SetThreadDpiAwarenessContext(previous)
                if user.GetForegroundWindow() != hwnd:
                    user.SetForegroundWindow(hwnd)
                until = time.monotonic() + 2
                while user.GetForegroundWindow() != hwnd and time.monotonic() < until:
                    time.sleep(.02)
                foreground = user.GetForegroundWindow()
                process = wintypes.DWORD()
                user.GetWindowThreadProcessId(foreground, ctypes.byref(process))
                report['pointer'] = {'cssTarget': [x, y], 'windowForeground': foreground == hwnd,
                                     'ownedForeground': process.value == os.getpid()}
                assert foreground == hwnd, 'Owned WebView2 window did not receive foreground'
                assert user.SetPhysicalCursorPos(round(origin.x + x * rect.right / viewport['width']),
                                                 round(origin.y + y * rect.bottom / viewport['height']))
                wait(f"window.__nativePointer && Math.abs(window.__nativePointer[0]-{x})<=2 && "
                     f"Math.abs(window.__nativePointer[1]-{y})<=2 && document.elementFromPoint({x},{y})?.matches(':hover')")
            def click_pointer(selector):
                encoded = json.dumps(selector)
                point = wait(f"(()=>{{const n=document.querySelector({encoded});if(!n||n.disabled)return false;const r=n.getBoundingClientRect();return {{x:r.left+r.width/2,y:r.top+r.height/2}};}})()")
                move_pointer(point['x'], point['y'])
                wait(f"document.querySelector({encoded}).matches(':hover')")
                ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
            def sidebar_check(mode):
                def action(label):
                    wait(f"(()=>{{const b=[...document.querySelectorAll('.smart-sidebar button')].find(x=>x.getAttribute('aria-label')==={json.dumps(label)}&&!x.disabled);if(!b)return false;b.click();return true;}})()")
                def geometry():
                    return window.evaluate_js("""(()=>{const m=document.querySelector('main'),r=m.getBoundingClientRect();return {left:r.left,width:r.width,scroll:m.scrollTop};})()""")
                def settled(expanded):
                    width = 250 if expanded else 72
                    wait(f"document.querySelector('main').getBoundingClientRect().left==={width}&&document.querySelector('.smart-sidebar').getBoundingClientRect().width==={width}")
                def reserves_space(before):
                    current = geometry()
                    return (current['left'] == 250 and current['width'] == before['width'] - 178
                            and current['scroll'] == before['scroll']
                            and window.evaluate_js("""(()=>{const s=document.querySelector('.smart-sidebar').getBoundingClientRect();return ['main','.topbar','.task-actions-host'].every(q=>document.querySelector(q).getBoundingClientRect().left>=s.right-.5);})()"""))
                def escape_panel():
                    window.evaluate_js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));void 0")
                    wait("document.querySelector('.smart-sidebar').dataset.expanded==='false'")
                    settled(False)
                initial = window.evaluate_js("document.querySelector('.smart-sidebar').dataset.docked==='true'")
                assert initial is False  # Auto follows the pointer even in a wide window.
                wait("document.querySelector('.smart-sidebar').dataset.expanded==='false'")
                settled(False)
                before = geometry()
                action('Expand sidebar')
                wait("document.querySelector('.smart-sidebar').dataset.expanded==='true'")
                settled(True)
                manual_reserved = reserves_space(before)
                manual_geometry = geometry()
                capture(window, 'sidebar-' + mode + '-expanded.png')
                escape_panel()
                move_pointer(600, 170)
                move_pointer(30, 170)
                wait("document.querySelector('.smart-sidebar').dataset.expanded==='true'")
                settled(True)
                hover_reserved = reserves_space(before)
                hover_geometry = geometry()
                # Real Windows pointer clicks stay inside the same sidebar.
                navigation_held = True
                for route in ('dashboard', 'sign', 'verify', 'vault', 'settings', 'verify'):
                    click_pointer(f'.smart-sidebar a[href="#/{route}"]')
                    wait(f"location.hash==='#/{route}'&&!!document.querySelector('.nav-item.active[href=\"#/{route}\"]')")
                    navigation_held = navigation_held and window.evaluate_js("document.querySelector('.smart-sidebar').dataset.expanded==='true'")
                assert navigation_held
                move_pointer(600, 170)
                wait("document.querySelector('.smart-sidebar').dataset.expanded==='false'")
                settled(False)
                move_pointer(30, 170)
                wait("document.querySelector('.smart-sidebar').dataset.expanded==='true'")
                move_pointer(600, 170)
                move_pointer(30, 170); time.sleep(.3)
                reentry = window.evaluate_js("document.querySelector('.smart-sidebar').dataset.expanded==='true'")
                assert reentry
                pin_allowed = window.evaluate_js("!document.querySelector('.sidebar-pin').disabled")
                unpin_inside = unpin_outside = None
                if pin_allowed:
                    click_pointer('.sidebar-pin')
                    wait("document.querySelector('.smart-sidebar').dataset.docked==='true'")
                    click_pointer('.sidebar-pin')  # Unpin while the pointer is inside.
                    wait("document.querySelector('.smart-sidebar').dataset.mode==='auto'")
                    unpin_inside = window.evaluate_js("document.querySelector('.smart-sidebar').dataset.expanded==='true'")
                    move_pointer(600, 170)
                    wait("document.querySelector('.smart-sidebar').dataset.expanded==='false'")
                    move_pointer(30, 170)
                    wait("document.querySelector('.smart-sidebar').dataset.expanded==='true'")
                    click_pointer('.sidebar-pin')
                    wait("document.querySelector('.smart-sidebar').dataset.docked==='true'")
                    move_pointer(600, 170)
                    action('Unpin sidebar')  # Mode change with pointer already outside.
                    wait("document.querySelector('.smart-sidebar').dataset.expanded==='false'")
                    unpin_outside = window.evaluate_js("document.querySelector('.smart-sidebar').dataset.mode==='auto'")
                move_pointer(30, 170)
                wait("document.querySelector('.smart-sidebar').dataset.expanded==='true'")
                click_pointer('.sidebar-auto')  # Auto off.
                wait("document.querySelector('.smart-sidebar').dataset.mode==='manual'")
                click_pointer('.sidebar-auto')  # Auto on, still inside.
                wait("document.querySelector('.smart-sidebar').dataset.mode==='auto'")
                auto_inside = window.evaluate_js("document.querySelector('.smart-sidebar').dataset.expanded==='true'")
                move_pointer(600, 170)
                wait("document.querySelector('.smart-sidebar').dataset.expanded==='false'")
                move_pointer(30, 170)
                wait("document.querySelector('.smart-sidebar').dataset.expanded==='true'")
                click_pointer('.sidebar-auto')  # Manual expanded, then enable from outside.
                wait("document.querySelector('.smart-sidebar').dataset.mode==='manual'")
                move_pointer(600, 170); time.sleep(.3)
                assert window.evaluate_js("document.querySelector('.smart-sidebar').dataset.expanded==='true'")
                action('Automatic sidebar')
                wait("document.querySelector('.smart-sidebar').dataset.expanded==='false'")
                auto_outside = window.evaluate_js("document.querySelector('.smart-sidebar').dataset.mode==='auto'")
                settled(False)

                # Stable control row and exact public ID in the real WebView2 UI.
                window.evaluate_js("document.querySelector('.key-id-toggle').scrollIntoView({block:'center'});void 0")
                def id_geometry():
                    return window.evaluate_js("""(()=>{const r=s=>{const q=document.querySelector(s).getBoundingClientRect();return {x:q.x,y:q.y,width:q.width,height:q.height}};return {copy:r('.key-id-copy'),toggle:r('.key-id-toggle')};})()""")
                id_before = id_geometry()
                click_pointer('.key-id-toggle')
                wait("document.querySelector('.key-id-toggle').getAttribute('aria-expanded')==='true'")
                id_open = id_geometry()
                id_stable = id_open == id_before
                full_exact = window.evaluate_js("""(()=>{const b=document.querySelector('.key-id-toggle'),c=document.querySelector('.key-id-full');return b.textContent==='View full ID'&&b.getAttribute('aria-controls')===c.parentElement.id&&!c.parentElement.hidden;})()""")
                full_exact = full_exact and window.evaluate_js("document.querySelector('.key-id-full').textContent") == report['hybridKeyId']
                capture(window, 'id-' + mode + '-expanded.png')
                click_pointer('.key-id-toggle')
                wait("document.querySelector('.key-id-toggle').getAttribute('aria-expanded')==='false'")
                id_stable = id_stable and id_geometry() == id_before
                preserved = window.evaluate_js("!![...document.querySelectorAll('h2')].find(n=>n.textContent==='HYBRID VALID')")
                assert manual_reserved and hover_reserved and preserved and auto_inside and auto_outside and id_stable and full_exact, {'checks': [manual_reserved, hover_reserved, preserved, auto_inside, auto_outside, id_stable, full_exact], 'before': before, 'manual': manual_geometry, 'hover': hover_geometry, 'idBefore': id_before, 'idOpen': id_open, 'idAfter': id_geometry()}
                return {'docked': initial, 'manualSpaceReserved': manual_reserved, 'hoverSpaceReserved': hover_reserved,
                        'resultPreserved': preserved, 'devicePixelRatio': window.evaluate_js('devicePixelRatio'),
                        'navigationHeldOpen': navigation_held, 'reentryCancelled': reentry,
                        'unpinInside': unpin_inside, 'unpinOutside': unpin_outside,
                        'autoInside': auto_inside, 'autoOutside': auto_outside,
                        'idStable': id_stable, 'fullIdExact': full_exact}
            wait("document.querySelector('.preview-indicator')?.textContent==='Desktop Connected'")
            window.evaluate_js("window.location.hash='/verify'; void 0")
            wait("!![...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Choose signed PDF')")
            # There is no managed session in this child at all: public verification
            # cannot accidentally succeed through an unlocked key-pair fallback.
            assert not window.evaluate_js("!!document.querySelector('input[type=password],input[type=file]')")
            for expected in ('valid', 'invalid', 'invalid'):
                click('Choose signed PDF')
                click('Choose encrypted vault')
                click('Verify PDF')
                wait(f"!![...document.querySelectorAll('h2')].find(x=>x.textContent==='HYBRID {expected.upper()}')")
                window.evaluate_js("window.__verification=null;window.pywebview.api.get_verification_state().then(x=>window.__verification=x);void 0")
                status = wait('window.__verification')
                assert status['ok'] is True and status['data']['state'] == expected
                assert status['data']['hybridValid'] is (expected == 'valid')
                assert status['data']['keySource']['trust'] == 'unauthenticated-metadata'
                encoded = json.dumps(status)
                assert all(str(path.parent) not in encoded for path in paths.values())
                report['results'].append(expected)
                report['hybridKeyId'] = status['data']['keySource']['hybridKeyId'] if expected == 'valid' else report['hybridKeyId']
                window.on_top = True
                time.sleep(.15)
                name = 'valid' if len(report['results']) == 1 else 'tampered' if len(report['results']) == 2 else 'wrong-keys'
                capture(window, control['label'] + '-' + name + '.png')
                if control.get('responsive') and len(report['results']) == 1:
                    from System.Drawing import Size
                    from System.Windows.Forms import FormWindowState
                    provider = NativeDialogs(window)
                    window.evaluate_js(pointer_listener)
                    default_size = provider._on_gui(lambda: (window.native.Width, window.native.Height))
                    report['responsive'] = {}
                    def resize_native(mode):
                        if mode == 'maximized': window.native.WindowState = FormWindowState.Maximized
                        elif mode in ('restored', 'minimum'):
                            window.native.WindowState = FormWindowState.Normal
                            window.native.Size = window.native.MinimumSize if mode == 'minimum' else Size(*default_size)
                        return {'width': window.native.Width, 'height': window.native.Height, 'dpi': window.native.DeviceDpi}
                    for mode in ('default', 'maximized', 'restored', 'minimum'):
                        window.evaluate_js("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Copy full ID').focus();void 0")
                        native_size = provider._on_gui(lambda: resize_native(mode))
                        time.sleep(.25)
                        if control.get('sidebar'):
                            # A resized window can move under the parked cursor.
                            # Measure its resting state after an actual leave.
                            move_pointer(600, 170)
                            wait("document.querySelector('.smart-sidebar').dataset.resizing==='false' && "
                                 "document.querySelector('.smart-sidebar').dataset.expanded==='false'")
                        metrics = wait("""(()=>{
                            const main=document.querySelector('main'), content=document.querySelector('.page-container'), footer=document.querySelector('.task-actions-host');
                            const m=main.getBoundingClientRect(), f=footer.getBoundingClientRect(), active=document.activeElement, r=active.getBoundingClientRect();
                            return {width:innerWidth,height:innerHeight,noOverflow:main.scrollWidth<=main.clientWidth&&document.documentElement.scrollWidth<=innerWidth,
                                footerSafe:m.bottom<=f.top+1,resultPreserved:[...document.querySelectorAll('h2')].some(n=>n.textContent==='HYBRID VALID'),
                                focusVisible:active.textContent.trim()==='Copy full ID'&&r.top>=m.top-1&&r.bottom<=m.bottom+1,
                                sidebarCollapsed:getComputedStyle(document.querySelector('.nav-item span')).display==='none',
                                columns:getComputedStyle(document.querySelector('.workflow-grid')).gridTemplateColumns.split(' ').length};
                        })()""")
                        assert metrics['noOverflow'] and metrics['footerSafe'] and metrics['focusVisible']
                        report['responsive'][mode] = {**metrics, 'native': native_size}
                        window.evaluate_js("document.querySelector('main').scrollTop=0;void 0")
                        capture(window, 'verify-' + mode + '.png')
                        window.evaluate_js("document.activeElement.scrollIntoView({block:'center'});void 0")
                        capture(window, 'verify-' + mode + '-result.png')
                        if control.get('sidebar'):
                            report.setdefault('sidebar', {})[mode] = sidebar_check(mode)
                    # The remaining original valid/tampered/wrong-key/cancel
                    # checks still run after the actual native resize sequence.
            click('Choose signed PDF')  # Real Cancel from the native picker.
            wait("!![...document.querySelectorAll('h2')].find(x=>x.textContent==='No verification performed')")
            # Clearing an old result precedes the human dialog. Wait for its
            # actual completion before destroying the owned WinForms window.
            wait("!![...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='Choose signed PDF'&&!x.disabled)")
            assert report.get('realNativeCancellation') is True
            report['results'].append('cancelled')
            report['lockedPublicVerification'] = True
            assert not choices
            report['inputsUnchanged'] = all(hashlib.sha256(path.read_bytes()).hexdigest() == before[key] for key, path in paths.items())
            assert report['inputsUnchanged']
            assert all(set(parent.iterdir()) == names for parent, names in parent_files.items())
            report['noArtifactsCreated'] = True
            report['files'] = {key: {'name': path.name, 'sizeBytes': path.stat().st_size} for key, path in paths.items()}
            report['passed'] = True
        except Exception:
            traceback.print_exc()  # Test-only public assertions; no keys/passwords are loaded.
        finally:
            window.destroy()
    window.events.loaded += probe
    return window


webview.create_window = create
exit_code = launcher.main()
report['ownedThreadsStopped'] = not any(thread.name.startswith('HybridSign-') for thread in threading.enumerate())
if report['passed'] and exit_code == 0:
    (qa / (control['label'] + '-checks.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('VERIFICATION_PROBE=' + json.dumps(report), flush=True)
raise SystemExit(0 if report['passed'] and exit_code == 0 else 1)
