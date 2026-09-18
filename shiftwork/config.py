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
BOOKSHOP_MISSION = FIXTURE_DIR / "mission" / "bookshop_mission_v2.json"
SEALED_CASES_DIR = PACKAGE_DIR / "sealed" / "cases"
CLIENT_DIR = PACKAGE_DIR / "client"
ARTIFACT_TEMPLATE_DIR = PACKAGE_DIR / "templates" / "artifact"
THIN_BATCH_HASH = "a16e1895f1f5d21aeb01fdf73759712c16bb63fcddfce1638213a29e9c00757c"

# The manifest alone is caller-supplied, so exact file bytes have a separate pin.
TRUSTED_LOCAL_FIXTURES = {
    "happy_path": ("6e36ed1b3c602fa1585bc499f6cf9adcb232756ed5726bd50ea756eb8311433d", "10826190b7318ec0c27a5d41cf241d5453e04c20c4b33ad336815ecca1293924"),
    "port_dead": ("3fca29de3e0bb2cb9f1b87e4a6bc6e44ec0b2f0613d84dd9bebccd30d912e3fe", "9e4ae1f16d75a5d9fdc9d0897255664b0706abef9dcb7bc92a10ed11723afad9"),
    "timeout": ("85949f7e6ad38f8dfee55716a5ccd1198853088e603024ed24a9781da6286f1d", "71b1a13c8d67705933e4a25cc96f3dbc24d778c66efff195cd5b59b954217449"),
    "truncated_body": ("f1009134d914b1f76c0a8efb4c6d448374a9eed25d3cc7b21a51f6fe0e62ded4", "f20ac6af6a60cdf44a85c5e8f29b37fc9092c36ad5e7031d4bf0a6706e226718"),
    "non_utf8_body": ("ce232c73f2b6e7d4257e009acea06685544b3fe47c81eb99910e0b2ce05a7d15", "659025e8dc151b31490bec5054c0401e677c240dcb0a847c74a4907fed411cf6"),
    "connection_refused": ("c15bf5ca1fc39f818a8b51a2b7451574c99e94ce080b5446e94f812580fec99c", "dad47aea8427d2bad00367bc5824d19d6582a8d337f456269818ba68a94a8c7f"),
    "kill_mid_batch": ("3ed340e86545c9e8e23a727abb6964853631ae0a06c936d8976ad81c47c9062e", "ac3ffc04f0123f540e018ae91c86f80a1423afb7995b98f32766276f5dae8f58"),
    "env_probe": ("42b7be0ed72373478f205b3793066da8ebffb2c536b8e8779362b01f65f9a33a", "860018c4c94ef50a929ddc1f799e45427832b24b731123e1ad09ff99e2287d42"),
}


def db_path() -> str:
    return os.environ.get("SHIFTWORK_DB_PATH", DEFAULT_DB_PATH)
