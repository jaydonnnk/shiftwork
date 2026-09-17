"""FastAPI factory. The tracer opens the DB, ensures the schema, seeds the
bookshop engagement and mounts the static client."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from shiftwork import config
from shiftwork.api.routes import lifecycle_error_handler, router
from shiftwork.orchestrator import LifecycleError
from shiftwork.store import db, repo


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = db.connect(app.state.db_path)
    try:
        db.ensure_schema(conn)
        repo.seed_engagement(
            conn, config.BOOKSHOP_SLUG, config.BOOKSHOP_BUSINESS_KIND, "The Ironbridge Bookshop"
        )
    finally:
        conn.close()
    yield


def create_app(db_path: str | None = None) -> FastAPI:
    app = FastAPI(title="Shiftwork", version="0.1.0-tracer", lifespan=lifespan)
    app.state.db_path = db_path or config.db_path()
    app.add_exception_handler(LifecycleError, lifecycle_error_handler)
    app.include_router(router)
    app.mount("/", StaticFiles(directory=config.CLIENT_DIR, html=True), name="client")
    return app
