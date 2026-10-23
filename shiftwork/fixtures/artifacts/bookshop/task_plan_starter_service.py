"""Bellwether starter for mission v2: the model's task plan decides what gets done.

For each customer request the service asks the controller gateway for a task
plan, then performs exactly the planned tasks, in the planned order, starting
each with the tool the plan named. It has no code that completes a task the
plan omits: when the plan leaves out a required task, or the gateway returns a
plan failure, the answer lacks that task and the visible check fails. A task
whose named tool cannot perform it is left out too, and logged.

Records come only from the trusted driver's /tool replies. The service reads
shop.json only for the snapshot clock and dependency status, which no tool
returns.
"""

import http.client
import json
import os
import re
import sys
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

MAX_RECORD_AGE_MS = 3600000
TASK_VOCABULARY = {
    "collection": "say whether the requested title and edition can be collected on the requested date",
    "alternative": "when collection cannot be confirmed, suggest a different same-genre title under the "
                   "customer's price limit that can be collected on that date",
    "price": "state the public price of the requested title and edition",
    "stock": "state the public stock quantity of the requested title and edition",
}
TOOLS = {
    "public_record_lookup": "read records of one kind (price, stock or availability) for one title and edition",
    "public_catalog_search": "list titles in one genre",
    "public_price_lookup": "read the price records for one title and edition",
    "public_stock_lookup": "read the stock records for one title and edition",
    "public_availability_lookup": "read the collection availability records for one title and edition",
}
_REQUESTS_SERVED = 0


def observe(kind, **detail):
    entry = {"source": "service_reported", "kind": kind, **detail}
    sys.stderr.buffer.write(json.dumps(entry, separators=(",", ":")).encode("utf-8") + b"\n")
    sys.stderr.buffer.flush()


def gateway_call(path, payload):
    port = int(os.environ["SHIFTWORK_GATEWAY_PORT"])
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=25)
    connection.request("POST", path, body=json.dumps(payload).encode("utf-8"),
                       headers={"Content-Type": "application/json"})
    response = connection.getresponse()
    body = response.read()
    status = response.status
    connection.close()
    if status != 200:
        raise RuntimeError("controller gateway refused: %d" % status)
    return json.loads(body)


def next_request_ordinal():
    """One per served request; the controller's gateway policy ordinal, not the body's."""
    global _REQUESTS_SERVED
    _REQUESTS_SERVED += 1
    return _REQUESTS_SERVED


def ask_for_plan(text):
    prompt = (
        "You plan the work for a bookshop customer request. Reply with JSON only, no prose and no "
        'code fence, shaped exactly as {"plan": [{"task_type": "...", "tool_name": "..."}]}. '
        "List one step per task the customer needs, in the order to do them. "
        "Allowed task_type values: "
        + "; ".join(f"{name} ({meaning})" for name, meaning in TASK_VOCABULARY.items())
        + ". Allowed tool_name values: "
        + "; ".join(f"{name} ({meaning})" for name, meaning in TOOLS.items())
        + ". Customer request: " + text
    )
    ordinal = next_request_ordinal()
    try:
        reply = gateway_call("/infer", {"request_ordinal": ordinal, "input_text": prompt})
    except (OSError, ValueError, RuntimeError):
        return None, "GATEWAY_UNAVAILABLE"
    return reply.get("plan"), reply.get("plan_failure")


def lookup(tool, entity_ref, kind=None):
    body = {"tool": tool, "entity_ref": entity_ref}
    if tool == "public_record_lookup":
        body["record_kind"] = kind
    try:
        records = gateway_call("/tool", body).get("records", [])
    except (OSError, ValueError, RuntimeError):
        observe("tool_call", tool=tool, entity_ref=entity_ref, status="failed")
        return []
    observe("tool_call", tool=tool, entity_ref=entity_ref, status="ok", record_count=len(records))
    return records


KIND_TOOLS = {"price": "public_price_lookup", "stock": "public_stock_lookup",
              "availability": "public_availability_lookup"}


def records_with(tool, entity_ref, kind):
    """Records of one kind using the named tool, or None when that tool cannot read them."""
    if tool == "public_record_lookup" or tool == KIND_TOOLS[kind]:
        return lookup(tool, entity_ref, kind)
    return None


def current(records, snapshot, date=None):
    """Newest current available record, None when absent, "conflict" when unresolved."""
    rows = [
        record for record in records
        if record["record_age_ms"] <= MAX_RECORD_AGE_MS
        and snapshot["dependencies"].get(record["dependency"]) == "available"
        and (date is None or (isinstance(record["value"], dict)
                              and record["value"].get("collection_date") == date))
    ]
    if not rows:
        return None
    if len({json.dumps(row["value"], sort_keys=True) for row in rows}) > 1:
        return "conflict"
    return min(rows, key=lambda row: (row["record_age_ms"], row["record_id"]))


def claim(record):
    return {"kind": record["kind"], "entity_ref": record["entity_ref"],
            "value": record["value"], "evidence_refs": [record["record_id"]]}


def result(task_id, status, entity_ref, claims=(), code=None):
    return {"task_id": task_id, "status": status, "entity_ref": entity_ref, "claims": list(claims),
            "commitment_ref": None, "explanation_code": code}


def fact_task(task_id, tool, snapshot, entity_ref):
    records = records_with(tool, entity_ref, task_id)
    if records is None:
        return None
    record = current(records, snapshot)
    if record is None or record == "conflict":
        return result(task_id, "REFERRED", entity_ref, code="PUBLIC_DATA_UNAVAILABLE")
    return result(task_id, "COMPLETED", entity_ref, [claim(record)])


def collection_task(tool, snapshot, entity_ref, date):
    """(result, confirmed) for the requested entity, or (None, None) for an unusable tool."""
    records = records_with(tool, entity_ref, "availability")
    if records is None:
        return None, None
    availability = current(records, snapshot, date)
    if availability is None or availability == "conflict":
        return result("collection", "REFERRED", entity_ref, code="PUBLIC_DATA_UNAVAILABLE"), None
    claims = [claim(availability)]
    confirmed = availability["value"].get("can_collect") is True
    if confirmed:
        stock = current(lookup("public_stock_lookup", entity_ref), snapshot)
        if stock is None or stock == "conflict" or not isinstance(stock["value"], int) or stock["value"] <= 0:
            return result("collection", "REFERRED", entity_ref, code="PUBLIC_DATA_UNAVAILABLE"), None
        claims.append(claim(stock))
    return result("collection", "COMPLETED", entity_ref, claims), confirmed


def alternative_task(tool, snapshot, requested, date, limit, collection_confirmed):
    if tool != "public_catalog_search":
        return None
    if collection_confirmed:
        return result("alternative", "NOT_APPLICABLE", requested)
    if limit is None:
        return result("alternative", "REFERRED", requested, code="PUBLIC_DATA_UNAVAILABLE")
    genre = snapshot["entities"].get(requested, {}).get("genre")
    try:
        candidates = gateway_call("/tool", {"tool": tool, "genre": genre}).get("entity_refs", [])
    except (OSError, ValueError, RuntimeError):
        observe("tool_call", tool=tool, genre=genre, status="failed")
        return result("alternative", "REFERRED", requested, code="PUBLIC_DATA_UNAVAILABLE")
    observe("tool_call", tool=tool, genre=genre, status="ok", entity_count=len(candidates))
    qualifying, unresolved = [], False
    for entity_ref in candidates:
        if entity_ref == requested:
            continue
        price = current(lookup("public_price_lookup", entity_ref), snapshot)
        stock = current(lookup("public_stock_lookup", entity_ref), snapshot)
        availability = current(lookup("public_availability_lookup", entity_ref), snapshot, date)
        if "conflict" in (price, stock, availability) or None in (price, stock, availability):
            unresolved = True
            continue
        if (isinstance(price["value"], int) and price["value"] < limit
                and isinstance(stock["value"], int) and stock["value"] > 0
                and availability["value"].get("can_collect") is True):
            qualifying.append((price["value"], entity_ref, [claim(price), claim(stock), claim(availability)]))
    if qualifying:
        _, entity_ref, claims = min(qualifying, key=lambda entry: (entry[0], entry[1]))
        return result("alternative", "COMPLETED", entity_ref, claims)
    if unresolved:
        return result("alternative", "REFERRED", requested, code="PUBLIC_DATA_UNAVAILABLE")
    return result("alternative", "REFUSED", requested, code="NO_MATCHING_ALTERNATIVE")


def requested_date(snapshot):
    observed = datetime.fromisoformat(snapshot["observed_at"].replace("Z", "+00:00"))
    return (observed.date() + timedelta(days=1)).isoformat()


def answer(request, snapshot):
    text, entity_ref = request["text"], request["entity_ref"]
    plan, failure = ask_for_plan(text)
    observe("task_plan", request_id=request["request_id"], plan=plan, plan_failure=failure)
    results, done = [], set()
    collection_confirmed = False
    date = requested_date(snapshot)
    match = re.search(r"£\s*(\d+)", text)
    limit = int(match.group(1)) * 100 if match else None
    for step in plan or []:
        task, tool = step["task_type"], step["tool_name"]
        if task in done:
            observe("plan_step_skipped", task_type=task, reason="repeated")
            continue
        if task == "collection":
            outcome, confirmed = collection_task(tool, snapshot, entity_ref, date)
            collection_confirmed = confirmed is True
        elif task == "alternative":
            outcome = alternative_task(tool, snapshot, entity_ref, date, limit, collection_confirmed)
        elif task in ("price", "stock"):
            outcome = fact_task(task, tool, snapshot, entity_ref)
        else:
            outcome = None
        if outcome is None:
            observe("plan_step_skipped", task_type=task, tool_name=tool, reason="tool_cannot_do_task")
            continue
        done.add(task)
        results.append(outcome)
    evidence_refs = []
    for item in results:
        for entry in item["claims"]:
            for ref in entry["evidence_refs"]:
                if ref not in evidence_refs:
                    evidence_refs.append(ref)
    return {"request_id": request["request_id"], "task_results": results,
            "evidence_refs": evidence_refs, "uncertainty_codes": []}


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
