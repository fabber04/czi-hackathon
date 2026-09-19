import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dotenv import load_dotenv

from ledger_core import extract_ledger, friendly_gemini_error, is_rate_limit_error

ROOT = Path(__file__).resolve().parent
PREVIEW_DIR = ROOT / "ui-preview"
load_dotenv(ROOT / ".env")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PREVIEW_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/extract":
            self.send_error(404, "Not found")
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
            result = extract_ledger(
                source=str(payload.get("source") or "image"),
                mime_type=str(payload.get("mime_type") or "image/jpeg"),
                data_b64=str(payload.get("data") or ""),
                business_name=str(payload.get("business_name") or ""),
                category=str(payload.get("category") or ""),
            )
            self._send_json(200, result)
        except Exception as error:
            message = friendly_gemini_error(error)
            if is_rate_limit_error(error) or "quota" in message.lower():
                status = 429
            elif "503" in message or "overloaded" in message.lower():
                status = 503
            else:
                status = 500
            self._send_json(status, {"error": message})

    def _send_json(self, status: int, body: dict):
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args):
        print("[%s] %s" % (self.log_date_time_string(), format % args))


if __name__ == "__main__":
    port = 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"PocketLedger preview + extract API: http://127.0.0.1:{port}/")
    server.serve_forever()
