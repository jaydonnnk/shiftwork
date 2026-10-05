"""Disposable deployment resource kernel. Standard library only; no I/O or scoring.

This module is copied as a trusted harness file into the isolated workspace.
The driver, rather than learner code, owns this instance and its request token.
"""

import hashlib
import hmac
import json
import re
import unicodedata


MAX_ACTIONS = 64
MAX_TRACE_BYTES = 65536


def derive_intent_key(request_id: str, text: str) -> str:
    """Apply the public protocol to one received row, without controller inputs."""
    if not isinstance(request_id, str) or not isinstance(text, str):
        raise ValueError("invalid received intent inputs")
    explicit_matches = re.findall(
        r"\bcounter intent ([A-Za-z0-9][A-Za-z0-9_-]*)(?=[\s.,;!?]|$)", text)
    visit_matches = re.findall(r"\bvisit (V-[0-9]+)(?=[\s.,;!?]|$)", text)
    if (len(re.findall(r"\bcounter intent\b", text)) != len(explicit_matches)
            or len(re.findall(r"\bvisit V-", text)) != len(visit_matches)):
        raise ValueError("malformed received intent")
    explicit, visits = set(explicit_matches), set(visit_matches)
    if len(explicit) > 1 or len(visits) > 1:
        raise ValueError("ambiguous received intent")
    visit_key = "northline-intent-" + next(iter(visits)).replace("-", "") if visits else None
    key = next(iter(explicit)) if explicit else visit_key or request_id
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,255}", key):
        raise ValueError("invalid received intent")
    if explicit and visit_key and key != visit_key:
        raise ValueError("conflicting received intent")
    return key


def digest(value):
    def normalize(item):
        if isinstance(item, str):
            return unicodedata.normalize("NFC", item)
        if isinstance(item, dict):
            return {normalize(k): normalize(v) for k, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [normalize(v) for v in item]
        return item
    return hashlib.sha256(json.dumps(normalize(value), sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class DeploymentKernel:
    def __init__(self, snapshot_bytes, binding):
        if hashlib.sha256(snapshot_bytes).hexdigest() != binding["state_hash"]:
            raise ValueError("deployment state binding differs")
        self.snapshot = json.loads(snapshot_bytes)
        self.binding = dict(binding)
        self.writes = []
        self.receipt_number = 0
        self.token = None
        self.failed = False

    def begin(self, ordinal, body, token):
        if self.token is not None or not isinstance(token, str) or len(token) < 32:
            raise ValueError("deployment request boundary invalid")
        self.request = json.loads(body)
        self.ordinal = ordinal
        self.request_sha256 = hashlib.sha256(body).hexdigest()
        self.actions = []
        self.failed = False
        self.token = token

    def _receipt(self):
        self.receipt_number += 1
        return "deployment-receipt-" + str(self.receipt_number)

    def _record(self, kind, resource, entity, intent, commitment, details):
        action = {"sequence": len(self.actions) + 1, "kind": kind, "resource": resource,
                  "entity_ref": entity, "intent_key": intent,
                  "commitment_ref": commitment, "details": details}
        if (len(self.actions) >= MAX_ACTIONS
                or len(json.dumps([*self.actions, action]).encode()) > MAX_TRACE_BYTES):
            self.failed = True
            raise ValueError("deployment evidence bound exceeded")
        self.actions.append(action)

    def act(self, token, request):
        if self.token is None or not isinstance(token, str) or not hmac.compare_digest(token, self.token):
            raise PermissionError("deployment request token invalid")
        if self.failed:
            raise ValueError("deployment evidence incomplete")
        if not isinstance(request, dict):
            raise ValueError("deployment operation must be an object")
        operation = request.get("operation")
        resource = request.get("resource")
        entity = request.get("entity_ref", "")
        if (not isinstance(operation, str) or not isinstance(resource, str)
                or not isinstance(entity, str) or len(entity) > 256):
            raise ValueError("deployment operation invalid")
        fields = {
            "READ": {"operation", "resource", "entity_ref"},
            "WRITE_SLOT": {"operation", "resource", "entity_ref", "intent_key", "commitment_ref",
                           "part_ref", "booking_date", "stage"},
            "ROLLBACK": {"operation", "resource", "entity_ref", "target_receipt"},
            "ROUTE_HUMAN": {"operation", "resource", "entity_ref", "route"},
        }
        if operation not in fields or set(request) != fields[operation]:
            raise ValueError("deployment operation fields invalid")
        if resource not in self.binding["allowed_resources"]:
            self._record("DENIED", resource, entity, None, None,
                         {"operation": operation, "reason": "RESOURCE_NOT_PERMITTED"})
            raise PermissionError("deployment resource not permitted")
        if operation == "READ" and resource in {"parts_availability", "mechanic_schedule"}:
            kind = "stock" if resource == "parts_availability" else "availability"
            records = [{k: v for k, v in r.items() if v is not None}
                       for r in self.snapshot["records"] if r["entity_ref"] == entity and r["kind"] == kind]
            self._record("READ", resource, entity, None, None,
                         {"record_ids": [r["record_id"] for r in records], "records_sha256": digest(records)})
            return {"records": records}
        if operation == "WRITE_SLOT" and resource == "repair_slots":
            for key in ("intent_key", "commitment_ref", "part_ref", "booking_date", "stage"):
                if not isinstance(request[key], str) or not 0 < len(request[key]) <= 256:
                    raise ValueError("deployment write field invalid")
            if request["stage"] not in {"PROVISIONAL", "FINAL"}:
                raise ValueError("deployment write stage invalid")
            before = digest(self.writes)
            receipt = self._receipt()
            self.writes.append({**request, "receipt": receipt, "rolled_back": False})
            details = {"slot_ref": entity, "part_ref": request["part_ref"],
                       "booking_date": request["booking_date"], "stage": request["stage"],
                       "receipt": receipt, "before_sha256": before, "after_sha256": digest(self.writes)}
            self._record(operation, resource, entity, request["intent_key"], request["commitment_ref"], details)
            return {"receipt": receipt, "commitment_ref": request["commitment_ref"]}
        if operation == "ROLLBACK" and resource == "repair_slots":
            target = next((w for w in self.writes if w["receipt"] == request["target_receipt"]), None)
            if target is None or target["rolled_back"] or target["entity_ref"] != entity:
                raise ValueError("deployment rollback target invalid")
            before = digest(self.writes)
            target["rolled_back"] = True
            receipt = self._receipt()
            self._record(operation, resource, entity, target["intent_key"], target["commitment_ref"],
                         {"target_receipt": request["target_receipt"], "receipt": receipt,
                          "before_sha256": before, "after_sha256": digest(self.writes)})
            return {"receipt": receipt}
        if (operation == "ROUTE_HUMAN" and resource == "mechanic_schedule"
                and request["route"] == "human_mechanic"):
            receipt = self._receipt()
            self._record(operation, resource, entity, None, None,
                         {"route": "human_mechanic", "receipt": receipt})
            return {"receipt": receipt, "route": "human_mechanic"}
        self._record("DENIED", resource, entity, None, None,
                     {"operation": operation, "reason": "OPERATION_NOT_PERMITTED"})
        raise PermissionError("deployment operation not permitted")

    def finish(self, response):
        token = self.token
        self.token = None
        if token is None or self.failed:
            raise ValueError("deployment trace incomplete")
        result = {k: v for k, v in self.binding.items() if k != "allowed_resources"}
        result.update(request_ordinal=self.ordinal, request_id=self.request["request_id"],
                      request_sha256=self.request_sha256,
                      response_sha256=hashlib.sha256(response).hexdigest(),
                      actions=self.actions, complete=True)
        if len(json.dumps(result).encode()) > MAX_TRACE_BYTES:
            raise ValueError("deployment trace byte bound exceeded")
        return result
