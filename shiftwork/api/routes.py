"""HTTP handlers only: parse/validate, delegate, map typed errors to status codes."""

import sqlite3
from collections.abc import Iterator

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse

from shiftwork import orchestrator
from shiftwork.api import schemas
from shiftwork.domain.errors import ShiftworkDomainError
from shiftwork.domain.models import ContractParams
from shiftwork.orchestrator import LifecycleError
from shiftwork.store import db

router = APIRouter(prefix="/api")


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    conn = db.connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


def lifecycle_error_handler(_request: Request, exc: LifecycleError) -> JSONResponse:
    status_code = 404 if exc.kind == "not_found" else 409
    return JSONResponse(status_code=status_code, content={"kind": exc.kind, "detail": exc.message})


def domain_error_handler(_request: Request, exc: ShiftworkDomainError) -> JSONResponse:
    status_code = 404 if exc.kind == "not_found" else 409
    return JSONResponse(status_code=status_code, content={"kind": exc.kind, "detail": exc.message})


@router.get("/engagements/{slug}/board", response_model=schemas.BoardView)
def get_board(slug: str, conn: sqlite3.Connection = Depends(get_conn)) -> schemas.BoardView:
    return schemas.BoardView.of(orchestrator.board_snapshot(conn, slug))


@router.post("/engagements/{slug}/shifts", response_model=schemas.ShiftView, status_code=201)
def open_shift(slug: str, conn: sqlite3.Connection = Depends(get_conn)) -> schemas.ShiftView:
    return schemas.ShiftView.of(orchestrator.open_next_shift(conn, slug))


@router.get("/shifts/{shift_id}/artifact", response_model=schemas.DraftView)
def read_artifact(shift_id: str, conn: sqlite3.Connection = Depends(get_conn)) -> schemas.DraftView:
    return schemas.DraftView(**orchestrator.get_draft(conn, shift_id))


@router.put("/shifts/{shift_id}/artifact", response_model=schemas.DraftView)
def write_artifact(
    shift_id: str, body: schemas.DraftUpdate, conn: sqlite3.Connection = Depends(get_conn)
) -> schemas.DraftView:
    return schemas.DraftView(**orchestrator.save_draft(conn, shift_id, body.files))


@router.post(
    "/shifts/{shift_id}/artifact/versions",
    response_model=schemas.ArtifactVersionView,
    status_code=201,
)
def freeze_version(
    shift_id: str,
    body: schemas.FreezeVersionRequest,
    conn: sqlite3.Connection = Depends(get_conn),
) -> schemas.ArtifactVersionView:
    contract = ContractParams(
        catalog_version=body.contract.catalog_version,
        must_never=tuple(body.contract.must_never),
        selections=body.contract.selections,
        response_time_limit_ms=body.contract.response_time_limit_ms,
        declared_limits=tuple(body.contract.declared_limits),
    )
    return schemas.ArtifactVersionView.of(
        orchestrator.freeze_version(conn, shift_id, contract)
    )


@router.post("/shifts/{shift_id}/runs", response_model=schemas.RunView, status_code=202)
def start_run(
    shift_id: str,
    background: BackgroundTasks,
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
) -> schemas.RunView:
    run = orchestrator.start_run(conn, shift_id)
    background.add_task(orchestrator.execute_run_task, request.app.state.db_path, run.id)
    return schemas.RunView.of(run)


@router.get("/runs/{run_id}", response_model=schemas.RunView)
def get_run(run_id: str, conn: sqlite3.Connection = Depends(get_conn)) -> schemas.RunView:
    return schemas.RunView.of(orchestrator.get_run(conn, run_id))


@router.get("/runs/{run_id}/outputs", response_model=list[schemas.RunOutputView])
def get_outputs(
    run_id: str, conn: sqlite3.Connection = Depends(get_conn)
) -> list[schemas.RunOutputView]:
    return [
        schemas.RunOutputView.of(output, customer_text=orchestrator.customer_text_for(output))
        for output in orchestrator.list_outputs(conn, run_id)
    ]


@router.get("/runs/{run_id}/checks", response_model=list[schemas.CheckResultView])
def get_checks(
    run_id: str, conn: sqlite3.Connection = Depends(get_conn)
) -> list[schemas.CheckResultView]:
    return [
        schemas.CheckResultView.of(result) for result in orchestrator.list_check_results(conn, run_id)
    ]


@router.get("/engagements/{slug}/ledger", response_model=schemas.LedgerView)
def get_ledger(slug: str, conn: sqlite3.Connection = Depends(get_conn)) -> schemas.LedgerView:
    payload = orchestrator.ledger(conn, slug)
    return schemas.LedgerView(chain_status=payload["chain_status"], events=payload["events"])


@router.get("/incidents/{incident_id}", response_model=schemas.IncidentView)
def get_incident(
    incident_id: str, conn: sqlite3.Connection = Depends(get_conn)
) -> schemas.IncidentView:
    return schemas.IncidentView.of(orchestrator.get_incident(conn, incident_id))


@router.post("/shifts/{shift_id}/close", response_model=schemas.ShiftView)
def close_shift(shift_id: str, conn: sqlite3.Connection = Depends(get_conn)) -> schemas.ShiftView:
    return schemas.ShiftView.of(orchestrator.close_shift(conn, shift_id))
