import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


def answer(request, snapshot):
    record = next((record for record in snapshot["records"] if record["record_id"] == request.get("record_id")), None)
    if record is None:
        return {"action": "ask", "claims": [], "evidence_refs": [], "record_age_ms": None}
    return {
        "action": "answer",
        "claims": [{"kind": record["kind"], "value": record["value"]}],
        "evidence_refs": [record["record_id"]],
        "record_age_ms": record["record_age_ms"],
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 65536:
            self.send_error(400)
            return
        try:
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict):
                raise ValueError("request must be an object")
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
    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        server.snapshot = json.loads(Path("shop.json").read_bytes())
        print(json.dumps({"port": server.server_port}), flush=True)
        server.serve_forever()
