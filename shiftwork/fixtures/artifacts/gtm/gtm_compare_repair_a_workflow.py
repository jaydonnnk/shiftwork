"""Draft A: explicit commercial phrases route by rules; other plausible buying signals enter human review.
Synthetic output records only; no model, CRM connection or message send.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

snapshot = json.loads(Path("shop.json").read_text(encoding="utf-8"))
processed = {}

def decide(record):
    value = record["value"]
    current = snapshot["dependencies"][record["dependency"]] == "available" and record["record_age_ms"] <= 3600000
    if value["suppressed"] or value["employee_count"] < 50:
        return "DISQUALIFIED"
    if not current or value["region"] == "UNKNOWN" or value["product"] == "UNKNOWN":
        return "REVIEW"
    if value["confidence"] < 80 or value["intent_label"] == "AMBIGUOUS":
        return "REVIEW"
    if value["intent_label"] == "RESEARCH":
        return "DISQUALIFIED"
    return "QUALIFIED" if any(phrase in value["note"].lower() for phrase in ("demo", "pricing", "security review")) else "REVIEW"

def answer(request):
    entity = request["entity_ref"]
    records = [r for r in snapshot["records"] if r["entity_ref"] == entity and r["kind"] == "signal"]
    if len(records) != 1:
        return {"request_id": request["request_id"], "task_results": [], "evidence_refs": [], "uncertainty_codes": []}
    record = records[0]
    value = record["value"]
    decision = decide(record)
    owner = "revenue-review" if decision == "REVIEW" else snapshot["routing_rules"].get(value["region"] + "/" + value["product"])
    # Preserve the region/product owner map.
    repeat = entity in processed or value["existing_record_ref"] is not None
    if entity in processed:
        decision, owner = processed[entity]
    tasks = []
    def result(tid, kind, claim_value=None, active=True):
        claims = [{"kind": kind, "entity_ref": entity, "value": claim_value, "evidence_refs": [record["record_id"]]}] if active else []
        tasks.append({"task_id": tid, "status": "COMPLETED" if active else "NOT_APPLICABLE", "entity_ref": entity,
                      "claims": claims, "commitment_ref": None, "explanation_code": None})
    result("qualification", "qualification", decision)
    active = decision != "DISQUALIFIED" and not repeat
    result("owner", "owner_assignment", owner, active)
    result("write", "pipeline_write", {"owner": owner, "record_ref": "pipeline:" + entity,
           "decision_trace": ["RULES_FIRST", decision]}, active)
    result("handoff", "handoff", "revenue-review", active and decision == "REVIEW")
    if active:
        processed[entity] = (decision, owner)
    return {"request_id": request["request_id"], "task_results": tasks, "evidence_refs": [record["record_id"]], "uncertainty_codes": []}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass
    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        body = json.dumps(answer(request), separators=(",", ":")).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        print(json.dumps({"port": server.server_port}), flush=True)
        server.serve_forever()
