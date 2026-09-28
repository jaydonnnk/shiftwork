"""Draft candidate B: plan-first repair favoring the greatest shelf stock.

The same proposed rule set as candidate A, written as resolve-then-answer: the
service builds a plan of the facts each task needs, then emits the envelope.
Candidate B answers the optional price fact only when the request asks for a
price. For a qualifying alternative it favors the greatest current shelf stock,
breaking ties by lower price. Candidate A favors the lowest price.

Request-shape convention (reviewed with the three comparison workloads): a
request containing "collect" asks for collection plus a conditional
alternative; a request containing "how much" asks for price and stock facts.
The collection date is the day after the snapshot's own observed date, because
the frozen snapshot clock is the only clock this service may read.
"""

import json
import re
import sys
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

MAX_RECORD_AGE_MS = 3600000


def observe(kind, **detail):
    entry = {"source": "service_reported", "kind": kind, **detail}
    sys.stderr.buffer.write(json.dumps(entry, separators=(",", ":")).encode("utf-8") + b"\n")
    sys.stderr.buffer.flush()


def resolve(snapshot, entity_ref, kind, date=None):
    """("ok", record) for a resolved group, ("missing", None), ("conflict", None)."""
    rows = [
        record
        for record in snapshot["records"]
        if record["entity_ref"] == entity_ref
        and record["kind"] == kind
        and record["record_age_ms"] <= MAX_RECORD_AGE_MS
        and snapshot["dependencies"].get(record["dependency"]) == "available"
        and (
            date is None
            or (isinstance(record["value"], dict) and record["value"].get("collection_date") == date)
        )
    ]
    if not rows:
        return "missing", None
    if len({json.dumps(row["value"], sort_keys=True) for row in rows}) > 1:
        return "conflict", None
    return "ok", min(rows, key=lambda row: (row["record_age_ms"], row["record_id"]))


def make_claim(record):
    return {
        "kind": record["kind"],
        "entity_ref": record["entity_ref"],
        "value": record["value"],
        "evidence_refs": [record["record_id"]],
    }


def result(task_id, status, entity_ref, claims=(), code=None):
    return {
        "task_id": task_id, "status": status, "entity_ref": entity_ref,
        "claims": list(claims), "commitment_ref": None, "explanation_code": code,
    }


def plan_fact(snapshot, task_id, entity_ref, kind):
    state, record = resolve(snapshot, entity_ref, kind)
    if state != "ok":
        return result(task_id, "REFERRED", entity_ref, code="PUBLIC_DATA_UNAVAILABLE")
    return result(task_id, "COMPLETED", entity_ref, [make_claim(record)])


def plan_collection(snapshot, entity_ref, date):
    state, availability = resolve(snapshot, entity_ref, "availability", date)
    if state != "ok":
        return result("collection", "REFERRED", entity_ref, code="PUBLIC_DATA_UNAVAILABLE"), None
    claims = [make_claim(availability)]
    if availability["value"].get("can_collect") is True:
        stock_state, stock = resolve(snapshot, entity_ref, "stock")
        if stock_state != "ok" or not isinstance(stock["value"], int) or stock["value"] <= 0:
            return result("collection", "REFERRED", entity_ref, code="PUBLIC_DATA_UNAVAILABLE"), None
        claims.append(make_claim(stock))
    return result("collection", "COMPLETED", entity_ref, claims), availability["value"].get("can_collect") is True


def plan_alternative(snapshot, requested, date, limit):
    genre = snapshot["entities"][requested]["genre"]
    unresolved = False
    qualifying = []
    for entity_ref, entity in snapshot["entities"].items():
        if entity_ref == requested or entity["genre"] != genre:
            continue
        states = {
            kind: resolve(snapshot, entity_ref, kind, date if kind == "availability" else None)
            for kind in ("price", "stock", "availability")
        }
        if any(state != "ok" for state, _ in states.values()):
            unresolved = True
            continue
        price = states["price"][1]
        stock = states["stock"][1]
        availability = states["availability"][1]
        qualifies = (
            isinstance(price["value"], int)
            and price["value"] < limit
            and isinstance(stock["value"], int)
            and stock["value"] > 0
            and availability["value"].get("can_collect") is True
        )
        if qualifies:
            claims = [make_claim(price), make_claim(stock), make_claim(availability)]
            qualifying.append((-stock["value"], price["value"], entity_ref, claims))
    if qualifying:
        _, _, entity_ref, claims = min(qualifying)
        return result("alternative", "COMPLETED", entity_ref, claims)
    if unresolved:
        return result("alternative", "REFERRED", requested, code="PUBLIC_DATA_UNAVAILABLE")
    return result("alternative", "REFUSED", requested, code="NO_MATCHING_ALTERNATIVE")


def build_plan(snapshot, request):
    text = request["text"]
    entity_ref = request["entity_ref"]
    shape = "collection" if "collect" in text.lower() else "facts"
    observe("interpretation", request_id=request["request_id"], method="keyword_router", shape=shape)
    plan = []
    if shape == "collection":
        date = (datetime.fromisoformat(snapshot["observed_at"].replace("Z", "+00:00")).date()
                + timedelta(days=1)).isoformat()
        price_state, price = resolve(snapshot, entity_ref, "price")
        asks_price = bool(re.search(r"how much|price|\bcost\b", text, re.IGNORECASE))
        if asks_price and price_state == "ok":
            plan.append(result("price", "COMPLETED", entity_ref, [make_claim(price)]))
        collection, confirmed = plan_collection(snapshot, entity_ref, date)
        plan.append(collection)
        match = re.search(r"£\s*(\d+)", text)
        limit = int(match.group(1)) * 100 if match else None
        if confirmed:
            plan.append(result("alternative", "NOT_APPLICABLE", entity_ref))
        elif limit is None:
            plan.append(result("alternative", "REFERRED", entity_ref, code="PUBLIC_DATA_UNAVAILABLE"))
        else:
            plan.append(plan_alternative(snapshot, entity_ref, date, limit))
    else:
        plan.append(plan_fact(snapshot, "price", entity_ref, "price"))
        plan.append(plan_fact(snapshot, "stock", entity_ref, "stock"))
    return plan


def envelope(request, snapshot):
    plan = build_plan(snapshot, request)
    evidence_refs = []
    for entry in plan:
        for item in entry["claims"]:
            for ref in item["evidence_refs"]:
                if ref not in evidence_refs:
                    evidence_refs.append(ref)
    return {
        "request_id": request["request_id"],
        "task_results": plan,
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
        body = json.dumps(envelope(request, self.server.snapshot), separators=(",", ":")).encode("utf-8")
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
