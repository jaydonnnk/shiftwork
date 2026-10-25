"""HTTP handlers only: parse/validate, delegate, map typed errors to status codes."""

import sqlite3
from collections.abc import Iterator

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Request
from fastapi.responses import JSONResponse

from shiftwork import comparison_flow, experiments
from shiftwork import orchestrator
from shiftwork.api import schemas
from shiftwork.domain.errors import ShiftworkDomainError
from shiftwork.domain.models import AssistRole, ContractParams, InvestigationRequest, SelectionRequest
from shiftwork.orchestrator import LifecycleError
from shiftwork.store import db
from shiftwork.live_budget import LiveComparisonBudget, LiveOperationBudget, LiveDiagnosticBudget

router = APIRouter(prefix="/api")


def _action_budget(configured, expected_type):
    budget = configured() if callable(configured) else configured
    if budget is not None and not isinstance(budget, expected_type):
        raise orchestrator.LifecycleError("conflict", "live budget wiring is invalid")
    return budget


@router.get("/runtime")
def runtime(request: Request) -> dict:
    return getattr(request.app.state, "hosted_runtime", {
        "hosted": False, "notice": "Local practice controller. Keep this server on loopback.",
    })


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


@router.get("/boards", response_model=list[schemas.WorkplaceBoardView])
def get_workplace_boards(conn: sqlite3.Connection = Depends(get_conn)) -> list[schemas.WorkplaceBoardView]:
    payload = [schemas.WorkplaceBoardView(
        engagement_slug=board.engagement_slug, availability=board.availability,
        **board.display.model_dump(),
    ) for board in orchestrator.workplace_boards()]
    orchestrator.assert_public_projection([board.model_dump(mode="json") for board in payload], conn)
    return payload


def _run_view(conn, run):
    view = schemas.RunView.of(run)
    proposal = orchestrator.repo.get_assist_proposal_for_run(conn, run.id)
    if proposal is not None:
        view = view.model_copy(update={"artifact_version_id": None, "proposal_event_id": proposal["event_id"]})
    return view


@router.get("/engagements/{slug}/board", response_model=schemas.BoardView)
def get_board(slug: str, conn: sqlite3.Connection = Depends(get_conn)) -> schemas.BoardView:
    snapshot = orchestrator.board_snapshot(conn, slug)
    if snapshot["latest_run"] is not None:
        snapshot["latest_run"] = _run_view(conn, snapshot["latest_run"])
    payload = schemas.BoardView.of(snapshot)
    orchestrator.assert_public_projection(payload.model_dump(mode="json"), conn)
    return payload


@router.post("/engagements/{slug}/shifts", response_model=schemas.ShiftView, status_code=201)
def open_shift(
    slug: str,
    request: Request,
    body: None = Body(default=None),
    conn: sqlite3.Connection = Depends(get_conn),
) -> schemas.ShiftView:
    return schemas.ShiftView.of(orchestrator.open_next_shift(
        conn, slug, executor_name=request.app.state.executor))


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
        orchestrator.freeze_version(conn, shift_id, contract,
            learner_declared_generated_patch_use=body.learner_declared_generated_patch_use)
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
    # A live configured executor needs its own bounded operation ceiling before a
    # reservation exists, mirroring the live comparison gate.
    live = request.app.state.executor == "tokenfactory"
    live_budget = _action_budget(request.app.state.live_operation_budget, LiveOperationBudget) if live else None
    if live and live_budget is None:
        raise orchestrator.LifecycleError("conflict", "live operation requires a bounded run budget")
    run = orchestrator.start_run(
        conn,
        shift_id,
        executor=request.app.state.executor,
        shop_snapshot=request.app.state.shop_snapshot,
        client_request_id=body.client_request_id if body else None,
    )
    background.add_task(orchestrator.execute_run_task, request.app.state.db_path, run.id, live_budget)
    return schemas.RunView.of(run)


@router.get("/runs/{run_id}", response_model=schemas.RunView)
def get_run(run_id: str, conn: sqlite3.Connection = Depends(get_conn)) -> schemas.RunView:
    return _run_view(conn, orchestrator.get_run(conn, run_id))


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
    return schemas.InvestigateStationView.of(experiments.investigate_station(
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
    live_budget = None
    if adapter == "tokenfactory" and body.kind in ("QUALIFYING_COMPARISON", "LATER_CONDITION_COMPARISON"):
        live_budget = _action_budget(request.app.state.live_comparison_budget, LiveComparisonBudget)
    if body.kind == "QUALIFYING_COMPARISON":
        if adapter == "tokenfactory" and live_budget is None:
            raise orchestrator.LifecycleError("conflict", "live comparison requires a bounded run budget")
        experiment = comparison_flow.create_qualifying_comparison(
            conn,
            shift_id,
            candidate_a_version_id=body.candidate_a_version_id,
            candidate_b_version_id=body.candidate_b_version_id,
            investigation_id=body.investigation_id,
            declared_treatment=body.declared_treatment,
            client_request_id=body.client_request_id,
            adapter=adapter,
            public_repetitions=body.public_repetitions,
        )
        if experiment.state == "PLANNED" and comparison_flow.comparison_run(conn, experiment.id) is not None:
            if live_budget is None:
                background.add_task(comparison_flow.execute_comparison_task,
                                    request.app.state.db_path, experiment.id)
            else:
                background.add_task(comparison_flow.execute_comparison_task,
                                    request.app.state.db_path, experiment.id,
                                    live_budget)
    elif body.kind == "LATER_CONDITION_COMPARISON":
        if adapter == "tokenfactory" and live_budget is None:
            raise orchestrator.LifecycleError("conflict", "live comparison requires a bounded run budget")
        experiment = comparison_flow.create_later_condition_comparison(
            conn,
            shift_id,
            operation_run_id=body.observed_run_id,
            declared_treatment=body.declared_treatment,
            client_request_id=body.client_request_id,
            adapter=adapter,
            public_repetitions=body.public_repetitions,
        )
        if experiment.state == "PLANNED" and comparison_flow.comparison_run(conn, experiment.id) is not None:
            if live_budget is None:
                background.add_task(comparison_flow.execute_comparison_task,
                                    request.app.state.db_path, experiment.id)
            else:
                background.add_task(comparison_flow.execute_comparison_task,
                                    request.app.state.db_path, experiment.id,
                                    live_budget)
    else:
        live_budget = (_action_budget(request.app.state.live_diagnostic_budget, LiveDiagnosticBudget)
                       if adapter == "tokenfactory" else None)
        if adapter == "tokenfactory" and body.public_repetitions > 1 and live_budget is None:
            raise orchestrator.LifecycleError("conflict", "live repetitions require a bounded diagnostic budget")
        experiment = experiments.create_diagnostic_experiment(
            conn,
            shift_id,
            candidate_version_id=body.candidate_a_version_id,
            investigation_id=body.investigation_id,
            client_request_id=body.client_request_id,
            adapter=adapter,
            public_repetitions=body.public_repetitions,
        )
        run = experiments.experiment_run(conn, experiment.id)
        if run is not None:
            background.add_task(
                experiments.execute_experiment_task, request.app.state.db_path, run.id, live_budget
            )
    return schemas.ExperimentView.of(experiments.experiment_view(conn, experiment.id))


@router.get("/experiments/{experiment_id}", response_model=schemas.ExperimentView)
def get_experiment(
    experiment_id: str, conn: sqlite3.Connection = Depends(get_conn)
) -> schemas.ExperimentView:
    return schemas.ExperimentView.of(experiments.experiment_view(conn, experiment_id))


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


@router.post("/shifts/{shift_id}/assist-events/{event_id}/run",
             response_model=schemas.ExperimentView, status_code=202)
def run_assist_proposal(shift_id: str, event_id: str, background: BackgroundTasks,
                        request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    adapter = request.app.state.executor
    budget = _action_budget(request.app.state.live_diagnostic_budget, LiveDiagnosticBudget)
    if adapter == "tokenfactory" and budget is None:
        raise orchestrator.LifecycleError("conflict", "a proposal run requires a bounded diagnostic budget")
    run = orchestrator.run_assist_proposal(conn, shift_id, event_id, adapter=adapter)
    background.add_task(experiments.execute_experiment_task, request.app.state.db_path, run.id, budget)
    return schemas.ExperimentView.of(experiments.experiment_view(conn, run.experiment_id))
