from __future__ import annotations

import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from app.api.routes import DemoRuntime, json_response, save_recording_response
from app.config import load_config


ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
ASSETS_DIR = ROOT.parent / "assets"
RECORDINGS_DIR = ROOT.parent / "recordings"


class DemoRequestHandler(BaseHTTPRequestHandler):
    runtime: DemoRuntime

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/state":
            json_response(self, 200, self.runtime.snapshot())
            return
        if path == "/":
            self._serve_file(WEB_DIR / "index.html")
            return
        if path.startswith("/web/"):
            self._serve_file(WEB_DIR / path.removeprefix("/web/"))
            return
        if path.startswith("/assets/"):
            self._serve_file(ASSETS_DIR / path.removeprefix("/assets/"))
            return
        if path.startswith("/recordings/"):
            self._serve_file(RECORDINGS_DIR / path.removeprefix("/recordings/"))
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/start":
            accepted, message = self.runtime.start()
            json_response(self, 202 if accepted else 409, {"ok": accepted, "message": message})
            return
        if path == "/api/reset":
            self.runtime.reset()
            json_response(self, 200, {"ok": True, "message": "已重置"})
            return
        if path == "/api/recording":
            save_recording_response(self, self.runtime, RECORDINGS_DIR)
            return
        self.send_error(404, "Not found")

    def log_message(self, format: str, *args) -> None:
        print(f"[http] {self.address_string()} - {format % args}")

    def _serve_file(self, file_path: Path) -> None:
        try:
            resolved = file_path.resolve()
            allowed_roots = (WEB_DIR.resolve(), ASSETS_DIR.resolve(), RECORDINGS_DIR.resolve())
            if not any(resolved == root or root in resolved.parents for root in allowed_roots):
                self.send_error(403, "Forbidden")
                return
            if not resolved.exists() or not resolved.is_file():
                self.send_error(404, "Not found")
                return

            content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            body = resolved.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except OSError as exc:
            self.send_error(500, str(exc))


def main() -> None:
    config = load_config()
    DemoRequestHandler.runtime = DemoRuntime(robot_mode=config.robot_mode)
    server = ThreadingHTTPServer((config.host, config.port), DemoRequestHandler)
    print(f"Go2 door check demo running at http://{config.host}:{config.port}")
    print(f"ROBOT_MODE={config.robot_mode}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down demo server")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
