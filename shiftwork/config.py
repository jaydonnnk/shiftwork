"""Pinned constants and fixture locations. No secrets live here.

Slice 2 adds the real fixture paths and the original bookshop configuration.
Slice 14 enforces the approved three-call assist policy at the controller.
Older engagement rows may retain the earlier six-call placeholder as history.

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
EXECUTOR_ADAPTER = os.environ.get("SHIFTWORK_EXECUTOR_ADAPTER", "recorded")
SERVICE_MODEL = os.environ.get("SHIFTWORK_SERVICE_MODEL", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")
ASSIST_MODEL = os.environ.get("SHIFTWORK_ASSIST_MODEL", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")
# The single owner of the sandbox image (the S12-verified public python:3.11-slim).
# The frozen execution context and the Token Factory adapter gate both read it,
# so an override executes the named image and a stale frozen image fails closed.
TOKEN_FACTORY_IMAGE = os.environ.get("SHIFTWORK_TOKEN_FACTORY_IMAGE", "c7ad32fe-8621-3cd2-9022-521c6da02ac1")
GENESIS_HASH = "0" * 64

# Bookshop engagement_config seed. Gate 3 section 7 caps assistance at three.
DEFAULT_ATTEMPT_LIMIT = 3
BOOKSHOP_ROTATION_GROUP_SIZE = 6
BOOKSHOP_TOTAL_ASSIST_BUDGET = 3

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
    # Slice 11 task-aware vocabulary (Gate 3 S3.3). Wording changes revise the
    # Gate 3 design, not this map; the pin in tests/sealed/test_render_map.py
    # fails on either side.
    ReasonCode.WRONG_ENTITY: "The answer was about a different title or edition than the customer asked for.",
    ReasonCode.REQUIRED_TASK_MISSING: "The answer left out part of what the customer asked for.",
    ReasonCode.UNSUPPORTED_CLAIM: "The answer stated a fact the current shop records do not agree on.",
    ReasonCode.INVALID_COMMITMENT: "The answer promised a reservation the task does not allow.",
    ReasonCode.UNJUSTIFIED_REFUSAL: "The service declined to answer when the shop records could have answered.",
    ReasonCode.UNJUSTIFIED_REFERRAL: "The service handed the customer to staff when the records were sufficient.",
    ReasonCode.UNJUSTIFIED_CLARIFICATION: "The service asked for a detail the request already gave.",
    ReasonCode.MISSING_EXECUTION_EVIDENCE: "The service did not run to completion, so there is no answer to judge.",
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


GTM_STARTER_CONTRACT_JSON = {
    "catalog_version": 1,
    "must_never": ["NEVER_UNOWNED_OR_DUPLICATE_SIGNAL"],
    "selections": {"ESCALATE_WHEN": "REVIEW_AMBIGUOUS_SIGNAL",
                   "REPEAT_REQUEST_RULE": "DEDUPLICATE_PIPELINE_BY_SIGNAL"},
    "response_time_limit_ms": 3000,
    "declared_limits": ["Synthetic pipeline output; no CRM connection, message send or live model."],
}


def offline_fixture_keys(slug: str) -> tuple[str, str, str]:
    """Separate GTM fixture authority from the historical Bellwether pins."""
    if slug == "gtm":
        return ("gtm_starter", "gtm_compare_candidate_a", "gtm_compare_candidate_b")
    return ("pivot_starter", "compare_candidate_a", "compare_candidate_b")


PIVOT_STARTER_ARTIFACT_PATHS = {
    "service.py": FIXTURE_DIR / "artifacts" / "bookshop" / "pivot_starter_failure_service.py",
}
# S43: the reviewed starter each Bellwether mission version opens with. The
# task-plan starter needs the controller gateway, so mission v2 and this starter
# bind only under the tokenfactory executor (Gate 3 S2 clarification, 2026-10-23).
# Values are pack-relative paths, each needing a reviewed pin before it binds.
BELLWETHER_STARTER_PATHS = {
    "fixtures/mission/bookshop_pivot_v1.json": {
        "service.py": "fixtures/artifacts/bookshop/pivot_starter_failure_service.py",
    },
    "fixtures/mission/bookshop_pivot_v2.json": {
        "service.py": "fixtures/artifacts/bookshop/task_plan_starter_service.py",
    },
}


def bellwether_starter_files(mission_path: str) -> dict[str, Path]:
    """The starter files a Bellwether mission version opens with.

    Version 1 keeps reading PIVOT_STARTER_ARTIFACT_PATHS, as it did before S43.
    """
    if mission_path == "fixtures/mission/bookshop_pivot_v1.json":
        return dict(PIVOT_STARTER_ARTIFACT_PATHS)
    return {name: PACKAGE_DIR / path for name, path in BELLWETHER_STARTER_PATHS[mission_path].items()}
PIVOT_STARTER_CONTRACT_JSON = {
    "catalog_version": 3,
    "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
    "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
    "response_time_limit_ms": 3000,
    "declared_limits": ["Public collection and alternative answers only; no reservations or business writes."],
}

# The protected family a qualifying comparison reserves from (Slice 15). Each
# pair draws one never-exposed variant and both of its candidate slots share it,
# so the comparison needs at least six reviewed variants per cycle.
BOOKSHOP_COMPARISON_FAMILIES: tuple[str, ...] = ("task_completion",)

# The reviewed ordinal map for the three public comparison workloads. It is the
# controller's only source of workload paths, hashes, counts and task-spec
# hashes; the workloads themselves live beside the other request fixtures.
PIVOT_COMPARE_MANIFEST = FIXTURE_DIR / "requests" / "bookshop_compare_manifest.json"
PIVOT_COMPARE_REQUEST_DIR = FIXTURE_DIR / "requests"

# The two draft candidate repairs the offline comparison tests execute under the
# pinned trusted-local adapter (Slice 15). They stand in for learner-authored
# versions until a separately authorized live run; each is a complete artifact
# whose frozen version composes the reviewed starter contract and the bookshop
# v3 catalog, exactly like the pinned starter.
PIVOT_COMPARE_CANDIDATE_SOURCES = {
    "A": FIXTURE_DIR / "artifacts" / "bookshop" / "compare_repair_a_service.py",
    "B": FIXTURE_DIR / "artifacts" / "bookshop" / "compare_repair_b_service.py",
}


def comparison_candidate_files(label: str) -> dict[str, str]:
    """One draft comparison candidate's frozen artifact files, as UTF-8 text."""
    source = PIVOT_COMPARE_CANDIDATE_SOURCES.get(label)
    if source is None:
        raise ValueError(f"unknown comparison candidate label: {label!r}")
    return {"service.py": source.read_bytes().decode("utf-8")}

# The reviewed public material the first Bellwether investigation runs against
# (Slice 11). These are public by design: the learner reads the same rubric,
# request and shop state the assessor uses, so nothing here is a hidden rule.
# Raw SHA-256 pins for all five pivot fixtures are recorded in
# docs/plans/shiftwork/00-status.md and re-verified by a guard test.
PIVOT_MISSION = FIXTURE_DIR / "mission" / "bookshop_pivot_v1.json"
PIVOT_PUBLIC_STATE = FIXTURE_DIR / "shop" / "bookshop_pivot_public_state.json"
PIVOT_COMPARE_STATE = FIXTURE_DIR / "shop" / "bookshop_compare_state_v1.json"
PIVOT_INCIDENT_REQUESTS = FIXTURE_DIR / "requests" / "bookshop_pivot_incident.jsonl"


# The manifest alone is caller-supplied, so exact file bytes have a separate pin.
# The `repair_arc_*` entries are the Test 1 pre-proof's artifact stages: their
# manifest hash is the frozen artifact version's content hash under
# REPAIR_ARC_CONTRACT_JSON and the bookshop v2 catalog, and their files hash
# covers the base64 files alone. A guard test recomputes every pin from the
# fixture files, so the pre-proof cannot run against unpinned bytes.
TRUSTED_LOCAL_FIXTURES = {
    "gtm_starter": ("4ee39e23810d0d58eed9eee1cdadb8c99010934da49ff581743e1564e9aecea2", "a24b2e15a4ac11e41806e7f7a74e4cc35c3806bc722d40af5d38675bc9cdfea8"),
    "gtm_compare_candidate_a": ("80810dc77baccf00894634cf1d7b855346fc8e8bf05c1d983b621a0b7801eb33", "aa363640af12212a57f8b74f2f698c9773d2693154c4972eaa599d9c603c456d"),
    "gtm_compare_candidate_b": ("ac90344963628ad964651f7877a64af9e35997ba7acb62e4636bca8d1087a10f", "708ef678d36244d432455b0757feca0d4bd61a70eecc9493bf9a25419b91e7c2"),
    "happy_path": ("6e36ed1b3c602fa1585bc499f6cf9adcb232756ed5726bd50ea756eb8311433d", "10826190b7318ec0c27a5d41cf241d5453e04c20c4b33ad336815ecca1293924"),
    "port_dead": ("3fca29de3e0bb2cb9f1b87e4a6bc6e44ec0b2f0613d84dd9bebccd30d912e3fe", "9e4ae1f16d75a5d9fdc9d0897255664b0706abef9dcb7bc92a10ed11723afad9"),
    "timeout": ("85949f7e6ad38f8dfee55716a5ccd1198853088e603024ed24a9781da6286f1d", "71b1a13c8d67705933e4a25cc96f3dbc24d778c66efff195cd5b59b954217449"),
    "truncated_body": ("f1009134d914b1f76c0a8efb4c6d448374a9eed25d3cc7b21a51f6fe0e62ded4", "f20ac6af6a60cdf44a85c5e8f29b37fc9092c36ad5e7031d4bf0a6706e226718"),
    "non_utf8_body": ("ce232c73f2b6e7d4257e009acea06685544b3fe47c81eb99910e0b2ce05a7d15", "659025e8dc151b31490bec5054c0401e677c240dcb0a847c74a4907fed411cf6"),
    "connection_refused": ("c15bf5ca1fc39f818a8b51a2b7451574c99e94ce080b5446e94f812580fec99c", "dad47aea8427d2bad00367bc5824d19d6582a8d337f456269818ba68a94a8c7f"),
    "kill_mid_batch": ("3ed340e86545c9e8e23a727abb6964853631ae0a06c936d8976ad81c47c9062e", "ac3ffc04f0123f540e018ae91c86f80a1423afb7995b98f32766276f5dae8f58"),
    "env_probe": ("42b7be0ed72373478f205b3793066da8ebffb2c536b8e8779362b01f65f9a33a", "860018c4c94ef50a929ddc1f799e45427832b24b731123e1ad09ff99e2287d42"),
    # Slice 15's two draft comparison candidates, frozen under the starter
    # contract and the bookshop v3 catalog. Their version content hash and file
    # hash are recomputed from the fixture files by the same guard test that
    # re-verifies every other pin, so the offline comparison cannot run unpinned.
    "compare_candidate_a": ("01df104ffd8fc974ae90e733e14ffb7e7af13260452a701f7567cd86b2342c82", "db3a7e3e3108991ef4beff1d50871bca7366115fae2f63782b89887785fb3fd4"),
    "compare_candidate_b": ("21b9733dbffab5d1845edc3f0b4e5c8cd9b26aafca3edb57778bdd51e3000105", "0e4302dcc0d3b609b3cfe13175d417063b25b98229c8d61672fbc2fe3a65af10"),
    "repair_arc_pre": ("36c485fdd777913fc8c0034f7509d9f28a03a06b91c72e2f1e463b42bba7f8fd", "2b103de1c6b95bdecb2eac786034a11ead12040d0abcbc744d5e1db10cc97359"),
    "repair_arc_post": ("390d8bad95c00cd7b8a9e7aebeb632930ba2146ec72a464e6d6b0a3021ef9f64", "651a825fe4b76f7aff52a08b62c7ab455fd805f9d1ed9bbb124ee6d03698f2ff"),
    "pivot_starter": ("a1c1093fcc456ebb5afc07241bb24f34ca4ca80877a7fff00fe5c82e2c542f28", "407906232c54c0a76679fd70a0d72a9fa53fc123417975022bb974c09f5ba618"),
}


def db_path() -> str:
    return os.environ.get("SHIFTWORK_DB_PATH", DEFAULT_DB_PATH)
