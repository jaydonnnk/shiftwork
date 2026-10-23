"""FastAPI factory. The controller opens the DB, ensures the schema, seeds the
admitted engagements, reconciles work a restart left nonterminal and mounts the
static client."""

from contextlib import asynccontextmanager
from collections.abc import Callable
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from shiftwork import config, orchestrator
from shiftwork.assist.gateway import AssistGateway
from shiftwork.api.routes import domain_error_handler, lifecycle_error_handler, router
from shiftwork.domain.errors import ShiftworkDomainError
from shiftwork.orchestrator import LifecycleError
from shiftwork.live_budget import LiveComparisonBudget, LiveOperationBudget, LiveDiagnosticBudget
from shiftwork.store import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = db.connect(app.state.db_path)
    try:
        db.ensure_schema(conn)
        orchestrator.seed_registered_engagements(conn)
        orchestrator.verify_assist_policy_projections(conn)
        # Startup recovery (Slices 8 and 14): runs and assist events a restart
        # left nonterminal are failed, with captures and draws retained and no
        # checks or events written.
        orchestrator.reconcile_interrupted(conn)
    finally:
        conn.close()
    yield


def create_app(
    db_path: str | None = None,
    *,
    executor: str | None = None,
    shop_snapshot: str | Path | None = None,
    assist_gateway: AssistGateway | None = None,
    live_comparison_budget: LiveComparisonBudget | Callable[[], LiveComparisonBudget] | None = None,
    live_operation_budget: LiveOperationBudget | Callable[[], LiveOperationBudget] | None = None,
    live_diagnostic_budget: LiveDiagnosticBudget | Callable[[], LiveDiagnosticBudget] | None = None,
) -> FastAPI:
    """Build the controller app; ``executor`` and ``shop_snapshot`` are the
    controller-side run binding new runs persist (program design 2: adapter
    selection). Both default to the shipped constants at call time; the learner
    never selects an executor or a snapshot through the API.
    """
    if executor is None and os.environ.get("RENDER") == "true":
        from shiftwork.hosted import create_hosted_app

        return create_hosted_app(db_path)
    app = FastAPI(title="Shiftwork", version="0.2.0-thin", lifespan=lifespan)
    app.state.db_path = db_path or config.db_path()
    app.state.executor = executor or config.EXECUTOR_ADAPTER
    app.state.assist_gateway = assist_gateway
    app.state.live_comparison_budget = live_comparison_budget
    app.state.live_operation_budget = live_operation_budget
    app.state.live_diagnostic_budget = live_diagnostic_budget
    app.state.shop_snapshot = (
        Path(shop_snapshot) if shop_snapshot is not None else config.BOOKSHOP_SNAPSHOT
    )
    app.add_exception_handler(LifecycleError, lifecycle_error_handler)
    app.add_exception_handler(ShiftworkDomainError, domain_error_handler)
    app.include_router(router)
    app.mount("/", StaticFiles(directory=config.CLIENT_DIR, html=True), name="client")
    return app
