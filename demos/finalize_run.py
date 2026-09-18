"""Slice 5 finalization demo: one real run finalizes into hash-chained events.

Seeds a bookshop shift, freezes the committed catalog v2 contract, attaches one
captured answer whose stock claim contradicts the run-consumed shop snapshot,
then runs the single idempotent finalization transaction (evaluate -> reduce ->
chain -> events -> incidents -> FINALIZED). Reads the ledger and outputs back
over HTTP to show derivation links and catalog-version references resolving to
raw records, and demonstrates that a second finalize nets zero new events.

The captured answer cites the thin-path bookshop snapshot because finalization
evaluates against the snapshot the run consumed; the stale-family transcript
belongs to a different snapshot and is scored by demos.evaluate_transcript.

Run from the repository root:
  python -m demos.finalize_run
"""

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from shiftwork import config, orchestrator  # noqa: E402
from shiftwork.app import create_app  # noqa: E402
from shiftwork.domain.models import ContractParams, RunOutput, RunState  # noqa: E402
from shiftwork.ledger import chain  # noqa: E402
from shiftwork.store import db, repo  # noqa: E402

CONTRACT_FIXTURE = config.FIXTURE_DIR / "artifacts" / "bookshop" / "contract_stale_family.json"


def _invented_output(run_id: str) -> RunOutput:
    body = json.dumps(
        {
            "action": "answer",
            "claims": [{"kind": "stock", "value": "out_of_stock"}],
            "evidence_refs": ["catalog:9780441013593"],
            "record_age_ms": 5400000,
        }
    ).encode("utf-8")
    return RunOutput(
        id=f"{run_id}-out-1",
        run_id=run_id,
        request_ordinal=1,
        request_text="Is Dune hardback in stock?",
        http_status=200,
        body=body,
        elapsed_ms=1,
    )


def main() -> int:
    contract = ContractParams.model_validate_json(CONTRACT_FIXTURE.read_bytes())
    with tempfile.TemporaryDirectory(prefix="shiftwork-finalize-") as workdir:
        db_file = str(Path(workdir) / "finalize.db")
        with TestClient(create_app(db_file)) as client:
            conn = db.connect(db_file)
            try:
                shift = orchestrator.open_next_shift(conn)
                orchestrator.freeze_version(conn, shift.id, contract)
                run = orchestrator.start_run(conn, shift.id)
                repo.insert_output(conn, _invented_output(run.id))
                repo.update_run(conn, run.id, RunState.CAPTURED)
                conn.commit()

                finalized = orchestrator.finalize_run(conn, run.id)
                events_once = repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
                incidents_once = repo.list_incidents(conn, config.BOOKSHOP_SLUG)

                orchestrator.finalize_run(conn, run.id)
                events_twice = repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
                incidents_twice = repo.list_incidents(conn, config.BOOKSHOP_SLUG)
            finally:
                conn.close()

            ledger = client.get("/api/engagements/bookshop/ledger").json()
            outputs = client.get(f"/api/runs/{run.id}/outputs").json()
            board = client.get("/api/engagements/bookshop/board").json()

    assert finalized.state is RunState.FINALIZED
    assert chain.verify_chain(events_once) is chain.ChainStatus.VALID
    assert events_twice == events_once and incidents_twice == incidents_once
    assert ledger["chain_status"] == "VALID"
    assert all(event["derivation"] is not None for event in ledger["events"])
    assert all(event["catalog"] is not None for event in ledger["events"])

    print(f"run {run.id} state={finalized.state.value}")
    for event in ledger["events"]:
        derivation = event["derivation"]
        print(
            f"  seq {event['seq']} {event['event_type']} reason={derivation['reason_code']} "
            f"ordinal={derivation['request_ordinal']} catalog_v{event['catalog']['catalog_version']}"
        )
    for incident in incidents_once:
        print(f"  incident {incident.id} {incident.reason_code.value} state={incident.state.value}")
    rendered = [item["customer_text"] for item in outputs if item["customer_text"]]
    print(f"  rendered customer texts: {len(rendered)} of {len(outputs)}")
    print(f"  board open_incidents={len(board['open_incidents'])} chain={board['chain_status']}")
    print(
        f"finalize-run evidence complete: run {run.id} FINALIZED, {len(events_once)} hash-chained "
        f"events chain {ledger['chain_status']}, {len(incidents_once)} incidents opened, "
        f"finalize twice nets zero new events, ledger derivation and catalog-version links resolved"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
