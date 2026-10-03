"""Blank Northline service. No booking, routing or repair solution is supplied."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


def answer(request, snapshot):
    # Learner implementation belongs here. Missing tasks are deliberate.
    return {"request_id": request["request_id"], "task_results": [],
            "evidence_refs": [], "uncertainty_codes": []}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 65536:
            self.send_error(400)
            return
        try:
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict) or not isinstance(request.get("request_id"), str):
                raise ValueError("request_id is required")
        except (ValueError, UnicodeDecodeError):
            self.send_error(400)
            return
        body = json.dumps(answer(request, self.server.snapshot), separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    with HTTPServer(("127.0.0.1", 8080), Handler) as server:
        server.snapshot = json.loads(Path("shop.json").read_text(encoding="utf-8"))
        server.serve_forever()
