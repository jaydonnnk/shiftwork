"""One separately authorized Northline Sandbox starter, with no inference.

Default mode only hashes/checks local files. --offline-rehearsal uses the local
executor. --execute is reserved for explicit user authorization of the printed
manifest digest; it refuses any changed bytes and never retries a reservation.
"""
import argparse
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.gateway.redaction import serialized_contains
from shiftwork.live_budget import LiveOperationBudget
from shiftwork.packs import registry

ROOT = Path(__file__).resolve().parents[1]
MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
IMAGE = "c7ad32fe-8621-3cd2-9022-521c6da02ac1"


class NoInferenceOperationBudget(LiveOperationBudget):
    def before_inference(self, model: str) -> None:
        raise ValueError("this packet authorizes no inference")


def preflight() -> dict:
    if config.SERVICE_MODEL != MODEL or config.TOKEN_FACTORY_IMAGE != IMAGE:
        raise RuntimeError("configured model or image differs from this packet")
    orchestrator.admit_pack("northline")
    pins = [pin for pack in registry.registered_packs() for pin in pack.reviewed_pins]
    if len(pins) != 42 or any(hashlib.sha256((config.PACKAGE_DIR / pin.path).read_bytes()).hexdigest() != pin.sha256 for pin in pins):
        raise RuntimeError("reviewed material differs from this packet")
    files = [path for path in config.PACKAGE_DIR.rglob("*.py") if "__pycache__" not in path.parts]
    files.append(Path(__file__).resolve())
    manifest = {
        "action": "S22B_ONE_LIVE_BLANK_STARTER", "model": MODEL, "image": IMAGE,
        "sandbox_operations_max": 1, "inference_calls_max": 0,
        "spawn_timeout_seconds": 45, "layer_bytes_max": 16777216,
        "reviewed_pins": {pin.path: pin.sha256 for pin in pins},
        "runtime": {str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)},
    }
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return {"manifest": manifest, "manifest_sha256": hashlib.sha256(raw).hexdigest()}


def load_authorized_credentials() -> None:
    # Called only by the separately authorized execute mode. Never print values.
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() in {"NEBIUS_API_KEY", "NEBIUS_PROJECT_ID"}:
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    if not os.environ.get("NEBIUS_API_KEY") or not os.environ.get("NEBIUS_PROJECT_ID", "").startswith("aiproject-"):
        raise RuntimeError("authorized Sandbox credentials are unavailable")


def run(out: Path, *, live: bool, packet: dict) -> None:
    out.mkdir(parents=True, exist_ok=False)
    (out / "once.marker").write_text("One reservation only. Failure consumes it. Do not retry.\n", encoding="utf-8")
    (out / "packet.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")
    meter = NoInferenceOperationBudget(MODEL, Decimal("0"), Decimal("0"))
    meter.preflight(model=MODEL, requests=1)
    with TestClient(create_app(str(out / "starter.db"), executor="tokenfactory" if live else "local_process", live_operation_budget=meter if live else None)) as client:
        opened = client.post("/api/engagements/northline/shifts")
        if opened.status_code != 201:
            raise RuntimeError("starter shift did not open")
        shift_id = opened.json()["id"]
        started = client.post(f"/api/shifts/{shift_id}/runs", json={"client_request_id": "s22b-one-starter"})
        if started.status_code != 202:
            raise RuntimeError("starter reservation did not return 202")
        run_id = started.json()["id"]
        receipt = {
            "run": client.get(f"/api/runs/{run_id}").json(),
            "outputs": client.get(f"/api/runs/{run_id}/outputs").json(),
            "checks": client.get(f"/api/runs/{run_id}/checks").json(),
            "ledger": client.get("/api/engagements/northline/ledger").json(),
            "board": client.get("/api/engagements/northline/board").json(),
            "sandbox_operations": meter.operations, "inference_calls": meter.calls,
        }
    # Keep a red or incomplete public receipt before checking the expected result.
    for key in ("NEBIUS_API_KEY", "NEBIUS_PROJECT_ID"):
        if live and serialized_contains(receipt, os.environ[key]):
            raise RuntimeError("public receipt contains a controller credential; stop")
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    expected_mode = "ISOLATED_LIVE" if live else "TRUSTED_LOCAL"
    assert receipt["run"]["state"] == "FINALIZED", "starter did not finalize"
    assert receipt["run"]["evidence_mode"] == expected_mode
    assert len(receipt["outputs"]) == 1 and receipt["checks"]
    assert any(row["verdict"] == "fail" for row in receipt["checks"]), "blank starter falsely passed"
    assert receipt["board"]["incidents"], "starter failure did not create an incident"
    assert not any(row["event_type"] in {"BOOKING_COMMITTED", "ROLLOUT_APPROVED", "HANDOVER_DECLARED"} for row in receipt["ledger"]["events"])
    assert meter.calls == 0 and meter.operations == (1 if live else 0)
    print(json.dumps({"status": "PASS", "mode": expected_mode, "out": str(out), "sandbox_operations": meter.operations, "inference_calls": meter.calls}))


def main() -> None:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--offline-rehearsal", action="store_true")
    modes.add_argument("--execute", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--approved-manifest-sha256")
    args = parser.parse_args()
    packet = preflight()
    if not args.offline_rehearsal and not args.execute:
        print(json.dumps(packet, indent=2))
        return
    if args.out is None:
        parser.error("a fresh --out directory is required")
    if args.execute:
        if args.approved_manifest_sha256 != packet["manifest_sha256"]:
            raise RuntimeError("explicit approval must bind these exact packet bytes")
        load_authorized_credentials()
    run(args.out.resolve(), live=args.execute, packet=packet)


if __name__ == "__main__":
    main()
