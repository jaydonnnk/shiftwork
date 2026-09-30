"""HTTP handlers only: parse/validate, delegate, map typed errors to status codes."""

import sqlite3
from collections.abc import Iterator

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Request
from fastapi.responses import JSONResponse

from shiftwork import orchestrator
from shiftwork.api import schemas
from shiftwork.domain.errors import ShiftworkDomainError
from shiftwork.domain.models import AssistRole, ContractParams, InvestigationRequest, SelectionRequest
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
    payload = schemas.BoardView.of(orchestrator.board_snapshot(conn, slug))
    orchestrator.assert_public_projection(payload.model_dump(mode="json"), conn)
    return payload


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


@router.get("/artifact-versions/{version_id}", response_model=schemas.ArtifactSourceView)
def get_artifact_source(
    version_id: str, conn: sqlite3.Connection = Depends(get_conn)
) -> schemas.ArtifactSourceView:
    return schemas.ArtifactSourceView.model_validate(orchestrator.artifact_source(conn, version_id))


@router.post("/shifts/{shift_id}/runs", response_model=schemas.RunView, status_code=202)
def start_run(
    shift_id: str,
    background: BackgroundTasks,
    request: Request,
    body: schemas.OperationRequest | None = Body(default=None),
    conn: sqlite3.Connection = Depends(get_conn),
) -> schemas.RunView:
    # The controller's configured executor and shop snapshot are persisted on the
    # run row; the request body carries neither, so the learner cannot select them.
    run = orchestrator.start_run(
        conn,
        shift_id,
        executor=request.app.state.executor,
        shop_snapshot=request.app.state.shop_snapshot,
        client_request_id=body.client_request_id if body else None,
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
    payload = [
        schemas.RunOutputView.of(output, **orchestrator.output_evidence_for(conn, output, run))
        for output in orchestrator.list_outputs(conn, run_id)
    ]
    orchestrator.assert_public_projection([entry.model_dump(mode="json") for entry in payload], conn)
    return payload


@router.get("/runs/{run_id}/checks", response_model=list[schemas.CheckResultView])
def get_checks(
    run_id: str, conn: sqlite3.Connection = Depends(get_conn)
) -> list[schemas.CheckResultView]:
    payload = [
        schemas.CheckResultView.of(result) for result in orchestrator.list_check_results(conn, run_id)
    ]
    orchestrator.assert_public_projection([entry.model_dump(mode="json") for entry in payload], conn)
    return payload


@router.get("/engagements/{slug}/ledger", response_model=schemas.LedgerView)
def get_ledger(slug: str, conn: sqlite3.Connection = Depends(get_conn)) -> schemas.LedgerView:
    payload = orchestrator.ledger(conn, slug)
    view = schemas.LedgerView(chain_status=payload["chain_status"], events=payload["events"])
    orchestrator.assert_public_projection(view.model_dump(mode="json"), conn)
    return view


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
    shift_id: str, request: Request, conn: sqlite3.Connection = Depends(get_conn)
) -> schemas.InvestigateStationView:
    return schemas.InvestigateStationView.of(orchestrator.investigate_station(
        conn, shift_id, adapter=request.app.state.executor,
        assist_gateway=request.app.state.assist_gateway,
    ))


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
    # The controller chooses the workloads, the adapter and the frozen material;
    # the body names the candidates and, for a comparison, the learner's declared
    # treatment for the difference between them.
    adapter = "tokenfactory" if request.app.state.executor == "tokenfactory" else "local_process"
    if body.kind == "QUALIFYING_COMPARISON":
        if adapter == "tokenfactory" and request.app.state.live_comparison_budget is None:
            raise orchestrator.LifecycleError("conflict", "live comparison requires a bounded run budget")
        experiment = orchestrator.create_qualifying_comparison(
            conn,
            shift_id,
            candidate_a_version_id=body.candidate_a_version_id,
            candidate_b_version_id=body.candidate_b_version_id,
            investigation_id=body.investigation_id,
            declared_treatment=body.declared_treatment,
            client_request_id=body.client_request_id,
            adapter=adapter,
        )
        if experiment.state == "PLANNED" and orchestrator.comparison_run(conn, experiment.id) is not None:
            if request.app.state.live_comparison_budget is None:
                background.add_task(orchestrator.execute_comparison_task,
                                    request.app.state.db_path, experiment.id)
            else:
                background.add_task(orchestrator.execute_comparison_task,
                                    request.app.state.db_path, experiment.id,
                                    request.app.state.live_comparison_budget)
    else:
        experiment = orchestrator.create_diagnostic_experiment(
            conn,
            shift_id,
            candidate_version_id=body.candidate_a_version_id,
            investigation_id=body.investigation_id,
            client_request_id=body.client_request_id,
            adapter=adapter,
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


@router.post("/shifts/{shift_id}/selections", response_model=schemas.SelectionView, status_code=201)
def create_selection(
    shift_id: str, body: SelectionRequest, conn: sqlite3.Connection = Depends(get_conn)
) -> schemas.SelectionView:
    view = schemas.SelectionView.of(orchestrator.append_selection(conn, shift_id, body))
    orchestrator.assert_public_projection(view.model_dump(mode="json"), conn)
    return view


@router.get("/engagements/{slug}/selections", response_model=list[schemas.SelectionView])
def get_selections(
    slug: str, conn: sqlite3.Connection = Depends(get_conn)
) -> list[schemas.SelectionView]:
    payload = [schemas.SelectionView.of(item) for item in orchestrator.selection_history(conn, slug)]
    orchestrator.assert_public_projection([item.model_dump(mode="json") for item in payload], conn)
    return payload


@router.post("/shifts/{shift_id}/assist", response_model=schemas.AssistEventView)
def request_assist(
    shift_id: str,
    body: schemas.AssistRequest,
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
) -> schemas.AssistEventView:
    event = orchestrator.request_assist(
        conn, shift_id, body.investigation_id, AssistRole(body.role),
        message=body.message, client_request_id=body.client_request_id,
        gateway=request.app.state.assist_gateway,
    )
    return schemas.AssistEventView.model_validate(orchestrator.assist_event_view(event))


@router.post("/assist-events/{event_id}/decision", response_model=schemas.AssistEventView)
def decide_assist(event_id: str, body: schemas.AssistDecision,
                  conn: sqlite3.Connection = Depends(get_conn)) -> schemas.AssistEventView:
    event = orchestrator.record_assist_decision(conn, event_id, body.accepted)
    return schemas.AssistEventView.model_validate(orchestrator.assist_event_view(event))
