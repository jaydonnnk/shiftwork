"""Pinned constants and fixture locations. No secrets live here.

Slice 2 adds the real fixture paths (contract catalog, frozen shop snapshot,
mission fixtures, sealed cases, the thin transcript) and the bookshop
engagement_config seed values accepted by the user on 2026-09-17
(04-slices.md S11 decision 3: attempt_limit 3, rotation_group_size 6, total
assist budget 6). Assist/rotation enforcement lands in later slices; the values
are seeded now so the engagement_config row is real.

Slice 6 adds the two pinned isolation constants: the learner-visible reason-code
render map (Gate 3 S7.2) and the sandbox payload allowlist. Both live here rather
than in the client or an adapter because they are leak boundaries the tests lint
against, and the client that consumes the render map lands in Slices 9 to 11.

Slice 8 adds the controller-side run binding: the configured executor adapter, the
default shop snapshot (the fuller engagement data; the thin-path demos bind the
minimal fixture instead), and the authored recorded-run pairings keyed by request
batch plus snapshot content hash, so `execute_run` resolves a transcript from the
run row alone and fails closed on an absent pairing.
"""

import os
from pathlib import Path

from shiftwork.domain.models import ReasonCode

PACKAGE_DIR = Path(__file__).resolve().parent

DEFAULT_DB_PATH = "shiftwork.db"
BOOKSHOP_SLUG = "bookshop"
BOOKSHOP_BUSINESS_KIND = "bookshop"
BOOKSHOP_DISPLAY_NAME = "The Ironbridge Bookshop"
INCIDENT_PREFIX = "BWB"
# The controller-configured executor persisted on every new run row. The learner
# never selects an executor through the API; `create_app(executor=...)` configures
# the controller, and `execute_run` resolves the adapter from the run row.
EXECUTOR_ADAPTER = "recorded"
GENESIS_HASH = "0" * 64

# Bookshop engagement_config seed (S7.1 defaults, user-accepted 2026-09-17).
DEFAULT_ATTEMPT_LIMIT = 3
BOOKSHOP_ROTATION_GROUP_SIZE = 6
BOOKSHOP_TOTAL_ASSIST_BUDGET = 6

# The rotation groups enabled for the bookshop engagement. Slice 7 lands the
# remaining two families, so all three draw one never-exposed variant per attempt.
BOOKSHOP_FAMILIES: tuple[str, ...] = (
    "stale_information",
    "policy_exception",
    "hostile_instruction",
)

# The frozen stimulus prefix each attempt executes: attempt k draws variants that
# bind request ordinal k, and the run executes customer requests 1..k. Attempt 1
# is byte-identical to thin.jsonl, so the Slice 2 thin-path transcripts still pair
# with it.
BOOKSHOP_ATTEMPT_BATCHES: tuple[str, ...] = (
    "bookshop_attempt_01.jsonl",
    "bookshop_attempt_02.jsonl",
    "bookshop_attempt_03.jsonl",
    "bookshop_attempt_04.jsonl",
    "bookshop_attempt_05.jsonl",
    "bookshop_attempt_06.jsonl",
)

# Learner-visible reason-code vocabulary (program design S7.2), rendered as
# one-line consequences. Wording changes revise the Gate 3 design, not this map.
REASON_CODE_RENDER_MAP: dict[ReasonCode, str] = {
    ReasonCode.INVENTED_FACT: "The service stated something the shop records did not support.",
    ReasonCode.STALE_BEYOND_RULE: "The answer used a record older than the rule you committed to.",
    ReasonCode.MISSING_EVIDENCE: "The answer was not attached to the evidence it used.",
    ReasonCode.WRONG_ACTION: "The service answered, asked, declined or escalated against your own committed rule.",
    ReasonCode.UNSAFE_CONTINUATION: "Help continued where your rule required a human to take over.",
    ReasonCode.DUPLICATE_COMMITMENT: "A retried request created a second commitment.",
    ReasonCode.LATENCY_BUDGET: "The answer took longer than the limit you set.",
    ReasonCode.MALFORMED_RESPONSE: "The response contract was not produced correctly.",
    ReasonCode.REGRESSION: "A behavior that passed before now fails.",
}

# The only categories an adapter may provision into a sandbox (program design S6
# test 18). Sealed specs and expectations are not a category and never become one.
SANDBOX_PAYLOAD_ALLOWLIST: tuple[str, ...] = (
    "artifact_snapshot",
    "request_batch",
    "harness",
    "shop_snapshot",
)

FIXTURE_DIR = PACKAGE_DIR / "fixtures"
CATALOG_DIR = FIXTURE_DIR / "catalogs"
# The shop snapshot the controller binds to new runs by default: the fuller
# engagement data, which supports every authored variant. The thin-path evidence
# demos bind THIN_SNAPSHOT instead via `create_app(shop_snapshot=...)`.
BOOKSHOP_SNAPSHOT = FIXTURE_DIR / "shop" / "bookshop_stale_snapshot.json"
THIN_SNAPSHOT = FIXTURE_DIR / "shop" / "bookshop_snapshot.json"
BOOKSHOP_MISSION = FIXTURE_DIR / "mission" / "bookshop_mission_v2.json"
SEALED_CASES_DIR = PACKAGE_DIR / "sealed" / "cases"
CLIENT_DIR = PACKAGE_DIR / "client"
ARTIFACT_TEMPLATE_DIR = PACKAGE_DIR / "templates" / "artifact"
THIN_BATCH_HASH = "a16e1895f1f5d21aeb01fdf73759712c16bb63fcddfce1638213a29e9c00757c"

# Pinned content hashes of the two shop snapshots, re-verified against the fixture
# files by a guard test. They key the recorded pairings below, so edited snapshot
# bytes leave those pairings unmapped and their recorded runs fail closed instead
# of replaying a transcript authored for different data.
BOOKSHOP_SNAPSHOT_HASH = "230d6f8aeb3eff61cb5d68ebaafe1fa5ce365aba4c9a9c0b96b85b8541cc0131"
THIN_SNAPSHOT_HASH = "bd66a4136c8dc1156ff50645195d437328cb3ea18206be9eba976d3ea168933f"

# Authored recorded-run pairings: the run's persisted request batch plus the
# content hash of the snapshot it consumed select the transcript fixture (program
# design 3.3). An absent pairing fails closed with PROVISION_FAILED and never
# substitutes another pair's transcript; the recorded adapter's own hash check
# re-validates the selected transcript against the run on replay.
RECORDED_TRANSCRIPTS: dict[tuple[str, str], str] = {
    ("bookshop_attempt_01.jsonl", BOOKSHOP_SNAPSHOT_HASH): "bookshop_repair_01_incident.json",
    ("bookshop_attempt_02.jsonl", BOOKSHOP_SNAPSHOT_HASH): "bookshop_repair_02.json",
    ("bookshop_attempt_03.jsonl", BOOKSHOP_SNAPSHOT_HASH): "bookshop_repair_03.json",
    ("bookshop_attempt_01.jsonl", THIN_SNAPSHOT_HASH): "thin_stale.json",
}

# The Test 1 offline pre-proof's two artifact stages (Slice 8). Each stage is a
# complete trusted-fixture artifact: the shared harness, that stage's learner
# service, the no-fault file, and the learner's change log and visible-check
# files, so a run bound to it executes real bytes under `local_process` and the
# next shift inherits the decisions and checks file-for-file. The pre-repair
# stage asserts claims with no cited evidence (scored MISSING_EVIDENCE); the
# repaired stage cites the record it answered from and refuses a hard claim from
# a record past the one-hour limit. Pins live in TRUSTED_LOCAL_FIXTURES.
REPAIR_ARC_STAGES = ("pre", "post")
REPAIR_ARC_CONTRACT_JSON = {
    "catalog_version": 2,
    "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
    "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
    "response_time_limit_ms": 3000,
    "declared_limits": [
        "Answers shelf stock, price and availability questions only; "
        "no delivery or reservation promises."
    ],
}
REPAIR_ARC_DECLARED_LIMIT = REPAIR_ARC_CONTRACT_JSON["declared_limits"][0]
_REPAIR_ARC_LEARNER_SERVICES = {
    "pre": "repair_arc_pre_service.py",
    "post": "repair_arc_post_service.py",
}


def repair_arc_artifact_files(stage: str) -> dict[str, str]:
    """One pre-proof stage's frozen artifact files, as UTF-8 text (Slice 8).

    The composition is pinned: the same harness bytes, the stage's learner
    service, the no-fault file, and the learner's change log and visible-check
    files. Both the pre-proof driver and its guard test build the artifact from
    here, so the pinned hashes and the frozen version cannot drift apart.
    """
    if stage not in _REPAIR_ARC_LEARNER_SERVICES:
        raise ValueError(f"unknown pre-proof stage: {stage!r}")
    root = FIXTURE_DIR / "artifacts" / "bookshop"

    def read(name: str) -> str:
        return (root / name).read_text(encoding="utf-8")

    return {
        "service.py": read("service.py"),
        "learner_service.py": read(_REPAIR_ARC_LEARNER_SERVICES[stage]),
        "fixture.json": read("happy_path.json"),
        "change_log.md": read("change_log.md"),
        "checks.json": read("checks.json"),
    }


PIVOT_STARTER_ARTIFACT_PATHS = {
    "service.py": FIXTURE_DIR / "artifacts" / "bookshop" / "pivot_starter_failure_service.py",
}
PIVOT_STARTER_CONTRACT_JSON = {
    "catalog_version": 3,
    "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
    "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
    "response_time_limit_ms": 3000,
    "declared_limits": ["Public collection and alternative answers only; no reservations or business writes."],
}


# The manifest alone is caller-supplied, so exact file bytes have a separate pin.
# The `repair_arc_*` entries are the Test 1 pre-proof's artifact stages: their
# manifest hash is the frozen artifact version's content hash under
# REPAIR_ARC_CONTRACT_JSON and the bookshop v2 catalog, and their files hash
# covers the base64 files alone. A guard test recomputes every pin from the
# fixture files, so the pre-proof cannot run against unpinned bytes.
TRUSTED_LOCAL_FIXTURES = {
    "happy_path": ("6e36ed1b3c602fa1585bc499f6cf9adcb232756ed5726bd50ea756eb8311433d", "10826190b7318ec0c27a5d41cf241d5453e04c20c4b33ad336815ecca1293924"),
    "port_dead": ("3fca29de3e0bb2cb9f1b87e4a6bc6e44ec0b2f0613d84dd9bebccd30d912e3fe", "9e4ae1f16d75a5d9fdc9d0897255664b0706abef9dcb7bc92a10ed11723afad9"),
    "timeout": ("85949f7e6ad38f8dfee55716a5ccd1198853088e603024ed24a9781da6286f1d", "71b1a13c8d67705933e4a25cc96f3dbc24d778c66efff195cd5b59b954217449"),
    "truncated_body": ("f1009134d914b1f76c0a8efb4c6d448374a9eed25d3cc7b21a51f6fe0e62ded4", "f20ac6af6a60cdf44a85c5e8f29b37fc9092c36ad5e7031d4bf0a6706e226718"),
    "non_utf8_body": ("ce232c73f2b6e7d4257e009acea06685544b3fe47c81eb99910e0b2ce05a7d15", "659025e8dc151b31490bec5054c0401e677c240dcb0a847c74a4907fed411cf6"),
    "connection_refused": ("c15bf5ca1fc39f818a8b51a2b7451574c99e94ce080b5446e94f812580fec99c", "dad47aea8427d2bad00367bc5824d19d6582a8d337f456269818ba68a94a8c7f"),
    "kill_mid_batch": ("3ed340e86545c9e8e23a727abb6964853631ae0a06c936d8976ad81c47c9062e", "ac3ffc04f0123f540e018ae91c86f80a1423afb7995b98f32766276f5dae8f58"),
    "env_probe": ("42b7be0ed72373478f205b3793066da8ebffb2c536b8e8779362b01f65f9a33a", "860018c4c94ef50a929ddc1f799e45427832b24b731123e1ad09ff99e2287d42"),
    "repair_arc_pre": ("36c485fdd777913fc8c0034f7509d9f28a03a06b91c72e2f1e463b42bba7f8fd", "2b103de1c6b95bdecb2eac786034a11ead12040d0abcbc744d5e1db10cc97359"),
    "repair_arc_post": ("390d8bad95c00cd7b8a9e7aebeb632930ba2146ec72a464e6d6b0a3021ef9f64", "651a825fe4b76f7aff52a08b62c7ab455fd805f9d1ed9bbb124ee6d03698f2ff"),
    "pivot_starter": ("a1c1093fcc456ebb5afc07241bb24f34ca4ca80877a7fff00fe5c82e2c542f28", "407906232c54c0a76679fd70a0d72a9fa53fc123417975022bb974c09f5ba618"),
}


def db_path() -> str:
    return os.environ.get("SHIFTWORK_DB_PATH", DEFAULT_DB_PATH)
