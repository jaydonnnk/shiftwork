"""Evaluator demo: fixture transcript in, CheckResults out (Slice 4).

Replays one checked-in transcript through the recorded adapter, scores it
against the sealed stale_information family under the committed bookshop
catalog v2 contract (whose labels state the one-hour freshness rule and the
price high-risk kind), and prints every CheckResult with reason codes and
opaque refs only. Sockets are blocked for the scoring phase, so both fixtures
must run fully offline.

Run from the repository root:
  python -m demos.evaluate_transcript --fixture fixtures/runs/passing_stale.json
  python -m demos.evaluate_transcript --fixture fixtures/runs/failing_stale.json
"""

import argparse
import asyncio
import base64
import json
import socket
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shiftwork import config  # noqa: E402
from shiftwork.domain import canonical  # noqa: E402
from shiftwork.domain.models import ContractParams  # noqa: E402
from shiftwork.evaluator import evaluator  # noqa: E402
from shiftwork.executor import base as executor_base  # noqa: E402
from shiftwork.executor.recorded import RecordedAdapter  # noqa: E402
from shiftwork.sealed import store as sealed_store  # noqa: E402

FAMILY_BATCH = "stale_family.jsonl"
FAMILY_SNAPSHOT = config.FIXTURE_DIR / "shop" / "bookshop_stale_snapshot.json"
DEFAULT_CONTRACT = config.FIXTURE_DIR / "artifacts" / "bookshop" / "contract_stale_family.json"

EXPECTED = {
    "passing_stale.json": "pass",
    "failing_stale.json": "fail",
}


def _block_network(*_args, **_kwargs):
    raise SystemExit("network access attempted; the evaluator must run offline")


def _show(label: str, payload) -> None:
    print(f"--- {label} ---")
    print(json.dumps(payload, indent=2, sort_keys=True))
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Score one fixture transcript against the sealed family.")
    parser.add_argument(
        "--fixture",
        required=True,
        help="transcript path relative to the shiftwork package, e.g. fixtures/runs/passing_stale.json",
    )
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT), help="committed ContractParams JSON file")
    args = parser.parse_args()

    fixture = Path(args.fixture)
    if not fixture.is_absolute():
        fixture = config.PACKAGE_DIR / fixture
    if fixture.name not in EXPECTED:
        raise SystemExit(f"unknown fixture {fixture.name!r}; expected one of {sorted(EXPECTED)}")
    contract = ContractParams.model_validate_json(Path(args.contract).read_bytes())

    batch_path = config.FIXTURE_DIR / "requests" / FAMILY_BATCH
    request = executor_base.RunRequest(
        artifact_snapshot=executor_base.ArtifactSnapshotRef(files={}, manifest_hash="demo-recorded-replay"),
        request_batch=executor_base.BatchRef(
            path_ref=FAMILY_BATCH,
            content_hash=canonical.content_hash(base64.b64encode(batch_path.read_bytes()).decode("ascii")),
        ),
        shop_snapshot_ref=str(FAMILY_SNAPSHOT),
        harness_ref="stdlib-loopback-v1",
        image_ref="local-python-stdlib",
        deadline_s=5,
        inference_grant=None,
    )
    # Offline guard: DNS and connection establishment are blocked for the whole
    # run; constructing any raw socket is blocked for the scoring phase, where
    # no event loop is running. The file-based replay itself only creates its
    # event loop's loopback self-pipe.
    loop = asyncio.new_event_loop()
    socket.create_connection = _block_network
    socket.getaddrinfo = _block_network
    try:
        result = loop.run_until_complete(RecordedAdapter(fixture).execute(request))
    finally:
        loop.close()
        socket.socket = _block_network
    if result.failure is not None:
        raise SystemExit(f"transcript replay failed: {result.failure}")
    batch = {entry.ordinal: entry for entry in executor_base.load_batch(request.request_batch)}
    outputs = [
        output.model_copy(
            update={
                "id": f"demo-out-{output.request_ordinal}",
                "run_id": "demo-run",
                "request_text": batch[output.request_ordinal].text,
            }
        )
        for output in executor_base.normalize_captures(result.captures, request.deadline_s)
    ]

    snapshot = json.loads(FAMILY_SNAPSHOT.read_text(encoding="utf-8"))
    public_records = {record["record_id"]: record for record in snapshot["records"]}
    cases = sealed_store.load_drawn_cases("demo-run")
    results = evaluator.evaluate(outputs, cases, contract, public_records)

    payload = [
        {
            "check_id": item.check_id,
            "observed_ref": item.observed_ref,
            "verdict": item.verdict,
            "reason_code": item.reason_code.value if item.reason_code else None,
            "expected_ref": item.expected_ref,
        }
        for item in results
    ]
    _show(f"{fixture.name} under STANCE={contract.selections.get('STANCE')}", payload)

    passes = sum(1 for item in results if item.verdict == "pass")
    fails = sum(1 for item in results if item.verdict == "fail")
    expected_verdict = EXPECTED[fixture.name]
    if expected_verdict == "pass" and fails != 0:
        raise SystemExit(f"expected every case to pass, got {fails} failures")
    if expected_verdict == "fail" and passes != 0:
        raise SystemExit(f"expected every case to fail, got {passes} passes")
    print(
        f"evaluate-transcript evidence complete: {fixture.name} -> {passes} pass / {fails} fail "
        f"with reason codes and opaque expected_refs; sockets blocked during scoring; contract STANCE "
        f"{contract.selections.get('STANCE')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
