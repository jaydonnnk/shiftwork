"""Minimal public-data service used only by the Slice 12 capability spike.

The process receives a customer request on stdin, asks its controller for one
interpretation, then returns a response. It has no provider credential.
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    request = json.loads(sys.stdin.readline())
    print(
        json.dumps(
            {
                "kind": "inference_request",
                "request_id": request["request_id"],
                "prompt": (
                    "Choose the single lookup needed for this bookshop request. "
                    "Reply with exactly STOCK or PRICE. Request: " + request["text"]
                ),
            }
        ),
        flush=True,
    )
    decision = json.loads(sys.stdin.readline())
    tool = decision.get("choice", "").strip().upper()
    if tool == "STOCK":
        result = {"tool": "stock_lookup", "answer": "Stock must be checked before promising collection."}
    elif tool == "PRICE":
        result = {"tool": "price_lookup", "answer": "Salt Roads paperback is £18."}
    else:
        result = {"tool": "none", "answer": "Cannot safely interpret the request."}
    print(json.dumps({"kind": "service_result", "request_id": request["request_id"], **result}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
