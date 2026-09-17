"""Pinned constants for the tracer slice. No secrets live here."""

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent

DEFAULT_DB_PATH = "shiftwork.db"
BOOKSHOP_SLUG = "bookshop"
BOOKSHOP_BUSINESS_KIND = "bookshop"
INCIDENT_PREFIX = "BWB"
DEFAULT_ATTEMPT_LIMIT = 3
TRACER_ADAPTER = "recorded"
TRACER_TRANSCRIPT = PACKAGE_DIR / "fixtures" / "runs" / "tracer_transcript.json"
CLIENT_DIR = PACKAGE_DIR / "client"
GENESIS_HASH = "0" * 64


def db_path() -> str:
    return os.environ.get("SHIFTWORK_DB_PATH", DEFAULT_DB_PATH)
