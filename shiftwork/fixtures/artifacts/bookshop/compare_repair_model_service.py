"""Draft candidate: guard-first repair that routes its first action through Nemotron.

Same proposed rule set as candidate A (resolve each task's necessary records
before claiming anything; answer the optional price fact when the requested
edition has a current price record), with one model-in-the-loop step per
customer request: the service asks the controller's frozen gateway to choose
the first public information action (public_record_lookup or
public_catalog_search), executes that tool call against the frozen public
state, and records the choice and its outcome. The guard code then establishes
every claim under the reviewed record rules, so the required tasks complete
whether or not the model call succeeds.

Request-shape convention (reviewed with the three comparison workloads): a
request containing "collect" asks for collection plus a conditional
alternative; a request containing "how much" asks for price and stock facts.
The collection date is the day after the snapshot's own observed date, because
the frozen snapshot clock is the only clock this service may read.

The gateway call's ``request_ordinal`` comes from a per-process request
counter, never from the request body's own ordinal. The controller binds each
inference capability to the position of the request in the batch it streamed
(first streamed request is ordinal 1), while a protected one-request batch
carries the stimulus ordinal 3 in its body. A counter that tracks served
requests keeps the two in agreement without reading the body.
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
ALLOWED_TOOL_NAMES = ("public_record_lookup", "public_catalog_search")
_REQUESTS_SERVED = 0


def observe(kind, **detail):
    entry = {"source": "service_reported", "kind": kind, **detail}
    sys.stderr.buffer.write(json.dumps(entry, separators=(",", ":")).encode("utf-8") + b"\n")
    sys.stderr.buffer.flush()


def gateway_call(path, payload):
    port = int(os.environ["SHIFTWORK_GATEWAY_PORT"])
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=25)
    raw = json.dumps(payload).encode("utf-8")
    connection.request("POST", path, body=raw, headers={"Content-Type": "application/json"})
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


def choose_first_action(text):
    ordinal = next_request_ordinal()
    prompt = (
        "Choose the first public information action needed for this bookshop request. "
        "Reply with exactly one allowed name, no explanation: public_record_lookup "
        "(read a price, stock or collection record for the requested title and edition) "
        "or public_catalog_search (find similar titles in the same genre). "
        "Customer request: " + text
    )
    try:
        reply = gateway_call("/infer", {"request_ordinal": ordinal, "input_text": prompt})
    except (OSError, ValueError, RuntimeError):
        return None, ordinal, "GATEWAY_UNAVAILABLE"
    choice = reply.get("selected_tool")
    if choice not in ALLOWED_TOOL_NAMES:
        return None, ordinal, "UNLISTED_CHOICE"
    return choice, ordinal, None


def run_first_action(choice, text, snapshot, entity_ref):
    if choice == "public_catalog_search":
        genre = snapshot.get("entities", {}).get(entity_ref, {}).get("genre")
        if genre is None:
            observe("tool_call", tool=choice, entity_ref=entity_ref, status="skipped_no_genre")
            return
        try:
            hit = gateway_call("/tool", {"tool": choice, "genre": genre})
            observe("tool_call", tool=choice, genre=genre, status="ok",
                    entity_count=len(hit.get("entity_refs", [])))
        except (OSError, ValueError, RuntimeError):
            observe("tool_call", tool=choice, genre=genre, status="failed")
        return
    record_kind = "availability" if "collect" in text.lower() else "price"
    try:
        hit = gateway_call("/tool", {"tool": choice, "entity_ref": entity_ref,
                                     "record_kind": record_kind})
        observe("tool_call", tool=choice, entity_ref=entity_ref, record_kind=record_kind,
                status="ok", record_count=len(hit.get("records", [])))
    except (OSError, ValueError, RuntimeError):
        observe("tool_call", tool=choice, entity_ref=entity_ref, record_kind=record_kind,
                status="failed")


def requested_date(snapshot):
    observed = datetime.fromisoformat(snapshot["observed_at"].replace("Z", "+00:00"))
    return (observed.date() + timedelta(days=1)).isoformat()


def current_record(snapshot, entity_ref, kind, date=None):
    """Newest current available record, None when absent, "conflict" when unresolved."""
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
        return None
    if len({json.dumps(row["value"], sort_keys=True) for row in rows}) > 1:
        return "conflict"
    return min(rows, key=lambda row: (row["record_age_ms"], row["record_id"]))


def claim(record):
    return {
        "kind": record["kind"],
        "entity_ref": record["entity_ref"],
        "value": record["value"],
        "evidence_refs": [record["record_id"]],
    }


def completed(task_id, entity_ref, claims):
    return {
        "task_id": task_id, "status": "COMPLETED", "entity_ref": entity_ref,
        "claims": claims, "commitment_ref": None, "explanation_code": None,
    }


def referred(task_id, entity_ref):
    return {
        "task_id": task_id, "status": "REFERRED", "entity_ref": entity_ref,
        "claims": [], "commitment_ref": None, "explanation_code": "PUBLIC_DATA_UNAVAILABLE",
    }


def refused(task_id, entity_ref, code):
    return {
        "task_id": task_id, "status": "REFUSED", "entity_ref": entity_ref,
        "claims": [], "commitment_ref": None, "explanation_code": code,
    }


def not_applicable(task_id, entity_ref):
    return {
        "task_id": task_id, "status": "NOT_APPLICABLE", "entity_ref": entity_ref,
        "claims": [], "commitment_ref": None, "explanation_code": None,
    }


def price_result(snapshot, task_id, entity_ref):
    record = current_record(snapshot, entity_ref, "price")
    if record is None or record == "conflict":
        return referred(task_id, entity_ref)
    return completed(task_id, entity_ref, [claim(record)])


def stock_result(snapshot, task_id, entity_ref):
    record = current_record(snapshot, entity_ref, "stock")
    if record is None or record == "conflict":
        return referred(task_id, entity_ref)
    return completed(task_id, entity_ref, [claim(record)])


def collection_outcome(snapshot, entity_ref, date):
    """The collection result plus whether collection was confirmed, or (result, None)."""
    availability = current_record(snapshot, entity_ref, "availability", date)
    if availability is None or availability == "conflict":
        return referred("collection", entity_ref), None
    claims = [claim(availability)]
    if availability["value"].get("can_collect") is True:
        stock = current_record(snapshot, entity_ref, "stock")
        if (
            stock is None
            or stock == "conflict"
            or not isinstance(stock["value"], int)
            or stock["value"] <= 0
        ):
            return referred("collection", entity_ref), None
        claims.append(claim(stock))
    return completed("collection", entity_ref, claims), availability["value"].get("can_collect") is True


def alternative_outcome(snapshot, requested, date, limit):
    genre = snapshot["entities"][requested]["genre"]
    qualifying = []
    unresolved = False
    for entity_ref, entity in snapshot["entities"].items():
        if entity_ref == requested or entity["genre"] != genre:
            continue
        price = current_record(snapshot, entity_ref, "price")
        stock = current_record(snapshot, entity_ref, "stock")
        availability = current_record(snapshot, entity_ref, "availability", date)
        if "conflict" in (price, stock, availability) or None in (price, stock, availability):
            unresolved = True
            continue
        if not isinstance(price["value"], int) or price["value"] >= limit:
            continue
        if not isinstance(stock["value"], int) or stock["value"] <= 0:
            continue
        if availability["value"].get("can_collect") is not True:
            continue
        qualifying.append((price["value"], entity_ref, [claim(price), claim(stock), claim(availability)]))
    if qualifying:
        _, entity_ref, claims = min(qualifying, key=lambda entry: (entry[0], entry[1]))
        return completed("alternative", entity_ref, claims)
    if unresolved:
        return referred("alternative", requested)
    return refused("alternative", requested, "NO_MATCHING_ALTERNATIVE")


def answer(request, snapshot):
    text = request["text"]
    entity_ref = request["entity_ref"]
    shape = "collection" if "collect" in text.lower() else "facts"
    choice, ordinal, failure = choose_first_action(text)
    if choice is None:
        observe("model_choice", request_id=request["request_id"], ordinal=ordinal,
                method="gateway_tool_selection", choice="public_record_lookup",
                fallback=failure)
        choice = "public_record_lookup"
    else:
        observe("model_choice", request_id=request["request_id"], ordinal=ordinal,
                method="gateway_tool_selection", choice=choice, fallback=None)
    run_first_action(choice, text, snapshot, entity_ref)
    observe("interpretation", request_id=request["request_id"], method="guard_after_model_route",
            shape=shape)
    results = []
    if shape == "collection":
        date = requested_date(snapshot)
        price = current_record(snapshot, entity_ref, "price")
        if price is not None and price != "conflict":
            results.append(completed("price", entity_ref, [claim(price)]))
        collection, confirmed = collection_outcome(snapshot, entity_ref, date)
        results.append(collection)
        match = re.search(r"£\s*(\d+)", text)
        limit = int(match.group(1)) * 100 if match else None
        if confirmed:
            results.append(not_applicable("alternative", entity_ref))
        elif limit is None:
            results.append(referred("alternative", entity_ref))
        else:
            results.append(alternative_outcome(snapshot, entity_ref, date, limit))
    else:
        results.append(price_result(snapshot, "price", entity_ref))
        results.append(stock_result(snapshot, "stock", entity_ref))
    evidence_refs = []
    for result in results:
        for item in result["claims"]:
            for ref in item["evidence_refs"]:
                if ref not in evidence_refs:
                    evidence_refs.append(ref)
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
