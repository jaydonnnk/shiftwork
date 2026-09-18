"""Pinned constants and fixture locations. No secrets live here.

Slice 2 adds the real fixture paths (contract catalog, frozen shop snapshot,
mission fixtures, sealed cases, the thin transcript) and the bookshop
engagement_config seed values accepted by the user on 2026-09-17
(04-slices.md S11 decision 3: attempt_limit 3, rotation_group_size 6, total
assist budget 6). Assist/rotation enforcement lands in later slices; the values
are seeded now so the engagement_config row is real.
"""

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent

DEFAULT_DB_PATH = "shiftwork.db"
BOOKSHOP_SLUG = "bookshop"
BOOKSHOP_BUSINESS_KIND = "bookshop"
BOOKSHOP_DISPLAY_NAME = "The Ironbridge Bookshop"
INCIDENT_PREFIX = "BWB"
TRACER_ADAPTER = "recorded"
GENESIS_HASH = "0" * 64

# Bookshop engagement_config seed (S7.1 defaults, user-accepted 2026-09-17).
DEFAULT_ATTEMPT_LIMIT = 3
BOOKSHOP_ROTATION_GROUP_SIZE = 6
BOOKSHOP_TOTAL_ASSIST_BUDGET = 6

FIXTURE_DIR = PACKAGE_DIR / "fixtures"
CATALOG_DIR = FIXTURE_DIR / "catalogs"
THIN_TRANSCRIPT = FIXTURE_DIR / "runs" / "thin_stale.json"
BOOKSHOP_SNAPSHOT = FIXTURE_DIR / "shop" / "bookshop_snapshot.json"
BOOKSHOP_MISSION = FIXTURE_DIR / "mission" / "bookshop_mission_v1.json"
SEALED_CASES_DIR = PACKAGE_DIR / "sealed" / "cases"
CLIENT_DIR = PACKAGE_DIR / "client"


def db_path() -> str:
    return os.environ.get("SHIFTWORK_DB_PATH", DEFAULT_DB_PATH)
