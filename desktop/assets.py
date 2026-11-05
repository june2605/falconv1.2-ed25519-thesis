"""pywebview server adapter serving only an immutable compiled-asset snapshot.

No application routes, HTTP bridge, CORS, directory listings or filesystem API.
"""
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
import mimetypes
from pathlib import Path
import stat
from threading import Thread
from types import MappingProxyType

CSP = ("default-src 'none'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; font-src 'self'; connect-src 'none'; object-src 'none'; "
       "frame-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
_EXTENSIONS = {".js", ".css", ".woff", ".woff2", ".svg", ".png", ".ico"}


class BuildError(Exception):
    def __init__(self):
        super().__init__("Frontend build missing or unsafe. Run npm run build in frontend.")


@dataclass(frozen=True)
class Asset:
    content: bytes
    content_type: str


@dataclass(frozen=True)
class BuildSnapshot:
    root: Path
    assets: object


def _is_reparse(path):
    info = path.lstat()
    return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def capture_build(root):
    try:
        root = Path(root).absolute()
        # Check ancestors before resolve, including Windows directory junctions.
        if any(_is_reparse(path) for path in [root, *root.parents]):
            raise BuildError()
        root = root.resolve(strict=True)
        paths = [root / "index.html"]
        if (root / "mark.svg").exists():
            paths.append(root / "mark.svg")
        directory = root / "assets"
        if not directory.is_dir() or _is_reparse(directory):
            raise BuildError()
        for path in directory.rglob("*"):
            if _is_reparse(path):
                raise BuildError()
            if path.is_file() and path.suffix in _EXTENSIONS:
                paths.append(path)
        captured, total = {}, 0
        for path in paths:
            info = path.stat()
            if _is_reparse(path) or not path.is_file() or info.st_nlink != 1 or info.st_size > 16 * 1024 * 1024:
                raise BuildError()
            content = path.read_bytes()
            total += len(content)
            if not content or total > 64 * 1024 * 1024:
                raise BuildError()
            relative = "/" + path.relative_to(root).as_posix()
            kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            captured[relative] = Asset(content, kind)
        if not any(path.endswith(".js") for path in captured):
            raise BuildError()
        return BuildSnapshot(root, MappingProxyType(captured))
    except (OSError, ValueError):
        raise BuildError() from None


def make_server_type(snapshot):
    """Implement pywebview's documented server-class hook, without Bottle routes."""
    class AssetServer:
        _instances = []

        @classmethod
        def start_server(cls, urls, http_port, **_):
            expected = str(snapshot.root / "index.html")
            if urls != [expected] or http_port is not None:
                raise BuildError()
            instance = cls()
            instance.root_path = instance.common_path = str(snapshot.root)
            instance.js_api_endpoint = None  # Edge uses the native message channel.
            instance.js_callback = {}
            owner = instance

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *_):
                    pass

                def do_GET(self):
                    origin = self.headers.get("Origin")
                    path = "/index.html" if self.path == "/" else self.path
                    asset = snapshot.assets.get(path)
                    if self.headers.get("Host") != owner.address.removeprefix("http://").rstrip("/") or (origin and origin != owner.address.rstrip("/")):
                        self._deny()
                        return
                    if asset is None:
                        self._deny()
                        return
                    self.send_response(200)
                    self.send_header("Content-Type", asset.content_type)
                    self.send_header("Content-Length", str(len(asset.content)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Security-Policy", CSP)
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.send_header("X-Frame-Options", "DENY")
                    self.send_header("Referrer-Policy", "no-referrer")
                    self.end_headers()
                    if self.command != "HEAD":
                        self.wfile.write(asset.content)

                do_HEAD = do_GET

                def _deny(self):
                    self.send_response(403)
                    self.send_header("Content-Length", "0")
                    self.end_headers()

                def do_POST(self):
                    self._deny()

            class LoopbackServer(HTTPServer):
                def get_request(self):
                    connection, address = super().get_request()
                    connection.settimeout(1)
                    return connection, address

            instance._httpd = LoopbackServer(("127.0.0.1", 0), Handler)
            try:
                instance._httpd.timeout = 1
                instance.address = f"http://127.0.0.1:{instance._httpd.server_port}/"
                instance._thread = Thread(target=instance._httpd.serve_forever, name="HybridSign-assets", daemon=False)
                instance._thread.start()
            except Exception:
                instance._httpd.server_close()
                raise
            instance._running = True
            cls._instances.append(instance)
            return instance.address, instance.common_path, instance

        @property
        def is_running(self):
            return self._running

        @classmethod
        def close_all(cls):
            for instance in cls._instances:
                if instance._running:
                    try:
                        instance._httpd.shutdown()
                    finally:
                        try:
                            instance._httpd.server_close()
                        finally:
                            instance._thread.join(2)
                            instance._running = instance._thread.is_alive()
                    if instance._running:
                        raise RuntimeError("Desktop asset server did not stop.")
    return AssetServer
