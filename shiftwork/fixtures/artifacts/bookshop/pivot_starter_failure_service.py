"""Intentionally incomplete public starter for pinned local verification."""

import json
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


def observe(kind, **detail):
    entry = {"source": "service_reported", "kind": kind, **detail}
    sys.stderr.buffer.write(json.dumps(entry, separators=(",", ":")).encode("utf-8") + b"\n")
    sys.stderr.buffer.flush()


def public_record_lookup(snapshot, entity_ref, kind):
    observe("tool_call", tool="public_record_lookup", entity_ref=entity_ref, record_kind=kind)
    record = next(
        (item for item in snapshot["records"] if item["entity_ref"] == entity_ref and item["kind"] == kind),
        None,
    )
    observe("tool_result", tool="public_record_lookup", record_ids=[] if record is None else [record["record_id"]])
    return record


def answer(request, snapshot):
    intent = "price" if re.search(r"\bprice\b|£", request["text"], re.IGNORECASE) else "unrouted"
    observe("interpretation", request_id=request["request_id"], intent=intent, method="keyword_router")
    results = []
    evidence_refs = []
    if intent == "price":
        record = public_record_lookup(snapshot, request["entity_ref"], "price")
        if record is not None:
            evidence_refs = [record["record_id"]]
            results.append({
                "task_id": "price",
                "status": "COMPLETED",
                "entity_ref": request["entity_ref"],
                "claims": [{
                    "kind": "price",
                    "entity_ref": record["entity_ref"],
                    "value": record["value"],
                    "evidence_refs": evidence_refs,
                }],
                "commitment_ref": None,
                "explanation_code": None,
            })
    return {
        "request_id": request["request_id"],
        "task_results": results,
        "evidence_refs": evidence_refs,
        "uncertainty_codes": [],
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        if self.path != "/":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError("invalid request length")
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict) or any(
                not isinstance(request.get(key), str) or not request[key].strip()
                for key in ("request_id", "text", "entity_ref")
            ):
                raise ValueError("invalid request fields")
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
