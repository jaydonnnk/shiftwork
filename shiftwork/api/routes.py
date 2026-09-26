"""HTTP handlers only: parse/validate, delegate, map typed errors to status codes."""

import sqlite3
from collections.abc import Iterator

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Request
from fastapi.responses import JSONResponse

from shiftwork import orchestrator
from shiftwork.api import schemas
from shiftwork.domain.errors import ShiftworkDomainError
from shiftwork.domain.models import AssistRole, ContractParams, InvestigationRequest
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
def open_shift(
    slug: str,
    body: None = Body(default=None),
    conn: sqlite3.Connection = Depends(get_conn),
) -> schemas.ShiftView:
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
    # The controller's configured executor and shop snapshot are persisted on the
    # run row; the request body carries neither, so the learner cannot select them.
    run = orchestrator.start_run(
        conn,
        shift_id,
        executor=request.app.state.executor,
        shop_snapshot=request.app.state.shop_snapshot,
    )
    background.add_task(orchestrator.execute_run_task, request.app.state.db_path, run.id)
    return schemas.RunView.of(run)


@router.get("/runs/{run_id}", response_model=schemas.RunView)
def get_run(run_id: str, conn: sqlite3.Connection = Depends(get_conn)) -> schemas.RunView:
    return schemas.RunView.of(orchestrator.get_run(conn, run_id))


@router.get("/runs/{run_id}/outputs", response_model=list[schemas.RunOutputView])
def get_outputs(
    run_id: str, conn: sqlite3.Connection = Depends(get_conn)
) -> list[schemas.RunOutputView]:
    run = orchestrator.get_run(conn, run_id)
    return [
        schemas.RunOutputView.of(output, **orchestrator.output_evidence_for(conn, output, run))
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


@router.get("/shifts/{shift_id}/investigations", response_model=schemas.InvestigateStationView)
def get_investigate_station(
    shift_id: str, conn: sqlite3.Connection = Depends(get_conn)
) -> schemas.InvestigateStationView:
    return schemas.InvestigateStationView.of(orchestrator.investigate_station(conn, shift_id))


@router.post(
    "/shifts/{shift_id}/investigations",
    response_model=schemas.InvestigationView,
    status_code=201,
)
def create_investigation(
    shift_id: str,
    body: schemas.InvestigationAppendRequest,
    conn: sqlite3.Connection = Depends(get_conn),
) -> schemas.InvestigationView:
    return schemas.InvestigationView.model_validate(
        orchestrator.append_investigation(
            conn,
            shift_id,
            InvestigationRequest(
                source_run_id=body.source_run_id,
                source_request_ordinal=body.source_request_ordinal,
                cause=body.cause,
                falsifier=body.falsifier,
                public_test=body.public_test,
                revision_of_id=body.revision_of_id,
                client_request_id=body.client_request_id,
            ),
        )
    )


@router.get("/investigations/{investigation_id}", response_model=schemas.InvestigationView)
def get_investigation(
    investigation_id: str, conn: sqlite3.Connection = Depends(get_conn)
) -> schemas.InvestigationView:
    return schemas.InvestigationView.model_validate(
        orchestrator.investigation_entry(conn, investigation_id)
    )


@router.post(
    "/shifts/{shift_id}/experiments",
    response_model=schemas.ExperimentView,
    status_code=202,
)
def create_experiment(
    shift_id: str,
    background: BackgroundTasks,
    request: Request,
    body: schemas.ExperimentRequest,
    conn: sqlite3.Connection = Depends(get_conn),
) -> schemas.ExperimentView:
    # The controller chooses the workload, the adapter and the treatment; the body
    # names only the candidate and the investigation it belongs to.
    experiment = orchestrator.create_diagnostic_experiment(
        conn,
        shift_id,
        candidate_version_id=body.candidate_a_version_id,
        investigation_id=body.investigation_id,
        client_request_id=body.client_request_id,
    )
    run = orchestrator.experiment_run(conn, experiment.id)
    if run is not None:
        background.add_task(
            orchestrator.execute_experiment_task, request.app.state.db_path, run.id
        )
    return schemas.ExperimentView.of(orchestrator.experiment_view(conn, experiment.id))


@router.get("/experiments/{experiment_id}", response_model=schemas.ExperimentView)
def get_experiment(
    experiment_id: str, conn: sqlite3.Connection = Depends(get_conn)
) -> schemas.ExperimentView:
    return schemas.ExperimentView.of(orchestrator.experiment_view(conn, experiment_id))


@router.post("/shifts/{shift_id}/assist", response_model=None)
def request_assist(
    shift_id: str,
    body: schemas.AssistRequest,
    conn: sqlite3.Connection = Depends(get_conn),
) -> None:
    """Diagnostic help. S11 always denies it: the prediction gate first, then the
    absent gateway. The typed denial carries which of the two applied; Slice 14
    replaces the raise with the attributable gateway and this route's response."""
    orchestrator.request_assist(
        conn, shift_id, body.investigation_id, AssistRole(body.role)
    )
