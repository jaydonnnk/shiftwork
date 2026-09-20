"""Shared session helpers for the Slice 7 orchestrator suite (budget, rotation, repair).

Every test drives the real HTTP surface against a real database. The shipped
controller binding (Slice 8) pairs each attempt's stimulus prefix with the fuller
shop snapshot and its authored transcript, so attempts run with no config or
environment mutation. A test that must fail or redirect one attempt overrides the
authored pairing for that attempt's (batch, snapshot) key for the duration of the
POST; the checked-in fixtures are never modified.
"""

import base64
import contextlib
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from shiftwork import config
from shiftwork.app import create_app
from shiftwork.sealed import store as sealed_store

RUNS_DIR = config.FIXTURE_DIR / "runs"
# One transcript per attempt, each paired with that attempt's prefix batch and the
# default shop snapshot. Attempt 1 fails every family's first variant
# (MISSING_EVIDENCE, which opens incidents); attempt 2 passes; attempt 3 answers
# the third request.
ATTEMPT_TRANSCRIPTS = (
    RUNS_DIR / "bookshop_repair_01_incident.json",
    RUNS_DIR / "bookshop_repair_02.json",
    RUNS_DIR / "bookshop_repair_03.json",
)
CONTRACT = {
    "catalog_version": 2,
    "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
    "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
    "response_time_limit_ms": 3000,
    "declared_limits": [],
}
TERMINAL_STATES = {"FINALIZED", "FAILED"}


class BookshopShift:
    """One bookshop shift driven over HTTP, one attempt at a time."""

    def __init__(self, client: TestClient, db_file: Path, monkeypatch=None) -> None:
        self.client = client
        self.db_file = db_file
        self.monkeypatch = monkeypatch
        self.shift_id = ""
        self.versions: list[str] = []

    def open(self) -> None:
        response = self.client.post("/api/engagements/bookshop/shifts")
        assert response.status_code == 201, response.text
        self.shift_id = response.json()["id"]

    def edit(self, addition: str = "\n# repair\n") -> None:
        draft = self.client.get(f"/api/shifts/{self.shift_id}/artifact")
        assert draft.status_code == 200, draft.text
        files = dict(draft.json()["files"])
        files["service.py"] = files["service.py"] + addition
        saved = self.client.put(f"/api/shifts/{self.shift_id}/artifact", json={"files": files})
        assert saved.status_code == 200, saved.text

    def freeze(self) -> dict:
        response = self.client.post(
            f"/api/shifts/{self.shift_id}/artifact/versions", json={"contract": CONTRACT}
        )
        assert response.status_code == 201, response.text
        body = response.json()
        self.versions.append(body["id"])
        return body

    def attempt(self, transcript: Path | None = None) -> dict:
        """POST one run and wait for a terminal state.

        Without ``transcript`` the authored pairing for this attempt's stimulus
        prefix and the bound snapshot resolves the replay. With one, that single
        pairing is overridden for this POST (the authored map is restored after the
        test), so a test can redirect or fail exactly this attempt.
        """
        if transcript is not None:
            assert self.monkeypatch is not None, "an attempt override needs the monkeypatch fixture"
            board = self.client.get("/api/engagements/bookshop/board")
            assert board.status_code == 200, board.text
            batch = config.BOOKSHOP_ATTEMPT_BATCHES[board.json()["attempts_used"]]
            self.monkeypatch.setitem(
                config.RECORDED_TRANSCRIPTS,
                (batch, config.BOOKSHOP_SNAPSHOT_HASH),
                str(transcript),
            )
        response = self.client.post(f"/api/shifts/{self.shift_id}/runs")
        assert response.status_code == 202, response.text
        return self.run(response.json()["id"])

    def run(self, run_id: str) -> dict:
        deadline = time.monotonic() + 10
        while True:
            response = self.client.get(f"/api/runs/{run_id}")
            assert response.status_code == 200, response.text
            body = response.json()
            if body["state"] in TERMINAL_STATES or time.monotonic() > deadline:
                return body
            time.sleep(0.02)

    def board(self) -> dict:
        response = self.client.get("/api/engagements/bookshop/board")
        assert response.status_code == 200, response.text
        return response.json()

    def ledger(self) -> dict:
        response = self.client.get("/api/engagements/bookshop/ledger")
        assert response.status_code == 200, response.text
        return response.json()


@pytest.fixture()
def session(tmp_path, monkeypatch):
    """An open shift with one frozen version, on a fresh database."""
    db_file = tmp_path / "orchestrator.db"
    with TestClient(create_app(str(db_file))) as client:
        shift = BookshopShift(client, db_file, monkeypatch)
        shift.open()
        shift.freeze()
        yield shift


@pytest.fixture()
def restart(tmp_path, monkeypatch):
    """Enter another app instance over an existing database file (a restart)."""
    stack = contextlib.ExitStack()

    def build(db_file: Path) -> BookshopShift:
        client = stack.enter_context(TestClient(create_app(str(db_file))))
        session = BookshopShift(client, db_file, monkeypatch)
        session.shift_id = "bookshop-shift-01"
        return session

    try:
        yield build
    finally:
        stack.close()


@pytest.fixture()
def sealed_inventory(tmp_path, monkeypatch):
    """A writable copy of all three sealed families, for tests that limit one.

    Nothing under ``shiftwork/sealed/cases/`` is ever touched: the copy lives in
    ``tmp_path`` and the loader is pointed at it.
    """
    directory = tmp_path / "sealed-cases"
    directory.mkdir()
    for name in sealed_store._FAMILY_FILES.values():
        (directory / name).write_bytes((config.SEALED_CASES_DIR / name).read_bytes())
    monkeypatch.setattr(config, "SEALED_CASES_DIR", directory)

    def publish(family: str, cases: list[dict], cycle: int) -> Path:
        data = {
            "family": family,
            "schema_version": 1,
            "cycle": cycle,
            "cases": cases,
        }
        path = directory / sealed_store._FAMILY_FILES[family]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    return {"directory": directory, "publish": publish}


def family_cases(family: str) -> list[dict]:
    """The raw authored cases of one real family, as mutable dicts."""
    path = config.SEALED_CASES_DIR / sealed_store._FAMILY_FILES[family]
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def retarget(tmp_path: Path, source: Path, changes: dict[int, bytes], name: str) -> Path:
    """A transcript copy with the chosen request ordinals' bodies replaced.

    The batch and snapshot hashes are copied unchanged, so the copy still pairs
    with the same attempt prefix; only the artifact's answer changes.
    """
    data = json.loads(source.read_text(encoding="utf-8"))
    seen = {capture["request_ordinal"] for capture in data["captures"]}
    assert set(changes) <= seen, f"no capture for ordinals {sorted(set(changes) - seen)}"
    for capture in data["captures"]:
        body = changes.get(capture["request_ordinal"])
        if body is not None:
            capture["body_base64"] = base64.b64encode(body).decode("ascii")
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


STALE_ANSWER = b'{"action":"answer","claims":[{"kind":"stock","value":"in_stock"}],"evidence_refs":[]}'
ASK = b'{"action":"ask","claims":[],"evidence_refs":[],"record_age_ms":null}'
