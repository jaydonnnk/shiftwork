"""FastAPI factory. The tracer opens the DB, ensures the schema, seeds the
bookshop engagement and mounts the static client."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from shiftwork import config
from shiftwork.api.routes import domain_error_handler, lifecycle_error_handler, router
from shiftwork.domain.errors import ShiftworkDomainError
from shiftwork.orchestrator import LifecycleError
from shiftwork.store import db, repo


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = db.connect(app.state.db_path)
    try:
        db.ensure_schema(conn)
        repo.seed_engagement(
            conn, config.BOOKSHOP_SLUG, config.BOOKSHOP_BUSINESS_KIND, config.BOOKSHOP_DISPLAY_NAME
        )
        repo.seed_engagement_config(
            conn,
            config.BOOKSHOP_SLUG,
            business_kind=config.BOOKSHOP_BUSINESS_KIND,
            assist_level="scaffolded",
            allowed_assist_roles=("hint", "diagnose"),
            total_assist_budget_per_shift=config.BOOKSHOP_TOTAL_ASSIST_BUDGET,
            enabled_check_families=config.BOOKSHOP_FAMILIES,
            attempt_limit=config.DEFAULT_ATTEMPT_LIMIT,
            rotation_group_size=config.BOOKSHOP_ROTATION_GROUP_SIZE,
        )
    finally:
        conn.close()
    yield


def create_app(db_path: str | None = None) -> FastAPI:
    app = FastAPI(title="Shiftwork", version="0.2.0-thin", lifespan=lifespan)
    app.state.db_path = db_path or config.db_path()
    app.add_exception_handler(LifecycleError, lifecycle_error_handler)
    app.add_exception_handler(ShiftworkDomainError, domain_error_handler)
    app.include_router(router)
    app.mount("/", StaticFiles(directory=config.CLIENT_DIR, html=True), name="client")
    return app
