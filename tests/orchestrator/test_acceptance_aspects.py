"""Typed aspect guards and exact Bellwether compatibility through real admission."""
import hashlib
import json

import pytest

from shiftwork import config, orchestrator
from shiftwork.domain.comparison import (
    AcceptanceAspect, acceptance_aspect, protected_acceptance,
    validate_acceptance_aspect, validate_legacy_payload,
)
from shiftwork.evaluator.evaluator import SealedCase
from shiftwork.domain.errors import InvalidSealedCase
from shiftwork.domain.models import ReasonCode
from shiftwork.domain.task_contract import TaskAssessment, TaskOutcome
from shiftwork.packs import registry
from shiftwork.sealed import rotation, store as sealed_store
from shiftwork.store import db, repo
from tests.packs.material import apply_staged_material, protected_family_bytes
from tests.orchestrator.test_experiment_lifecycle import _comparison_session, _reserve_comparison


INVALID_ASPECTS = (
    None, 17, "ABSENT", "unknown_legacy", {}, {"kind": "UNKNOWN"},
    {"kind": "NAMED_TASK_OUTCOMES", "expected_outcomes": ["USEFUL_COMPLETION"]},
    {"kind": "NAMED_TASK_OUTCOMES", "task_id": "missing", "expected_outcomes": ["USEFUL_COMPLETION"]},
    {"kind": "NAMED_TASK_OUTCOMES", "task_id": "collection", "expected_outcomes": []},
    {"kind": "NAMED_TASK_OUTCOMES", "task_id": "collection", "expected_outcomes": ["UNKNOWN"]},
    {"kind": "NAMED_TASK_OUTCOMES", "task_id": "collection", "expected_outcomes": ["USEFUL_COMPLETION"], "reason_code": "WRONG_ACTION"},
    {"kind": "NO_TASK_REASON_CODE"},
    {"kind": "NO_TASK_REASON_CODE", "reason_code": "UNKNOWN"},
    {"kind": "NO_TASK_REASON_CODE", "reason_code": "WRONG_ACTION", "task_id": "collection"},
    {"kind": "NO_TASK_REASON_CODE", "reason_code": "WRONG_ACTION", "expected_outcomes": ["USEFUL_COMPLETION"]},
    {"kind": "EVERY_REQUIRED_TASK_RETURNS_A_RESULT", "task_id": "collection"},
    {"kind": "EVERY_REQUIRED_TASK_RETURNS_A_RESULT", "expected_outcomes": ["USEFUL_COMPLETION"]},
    {"kind": "EVERY_REQUIRED_TASK_RETURNS_A_RESULT", "reason_code": "WRONG_ACTION"},
    {"kind": "EVERY_REQUIRED_TASK_RETURNS_A_RESULT", "extra": True},
)


def all_rows(conn):
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    return {table: list(map(tuple, conn.execute(f'SELECT * FROM "{table}" ORDER BY rowid'))) for table in tables}


@pytest.mark.parametrize("aspect", INVALID_ASPECTS)
def test_invalid_aspect_refuses_before_any_write(session, tmp_path, monkeypatch, aspect):
    a, b, investigation = _comparison_session(session)
    cases = list(sealed_store.load_family("task_completion").cases)
    expected = {**cases[0].expected, "aspect": aspect}
    if aspect == "ABSENT":
        expected.pop("aspect")
    cases[0] = cases[0].model_copy(update={"expected": expected})
    apply_staged_material(monkeypatch, tmp_path / "invalid-aspect-package", {
        "sealed/cases/bookshop_task_completion.json": protected_family_bytes(cases)})
    conn = db.connect(session.db_file)
    try:
        before = all_rows(conn)
        with pytest.raises(registry.PackUnavailable):
            _reserve_comparison(session, a, b, investigation)
        assert all_rows(conn) == before, "invalid aspect wrote exposure or other reservation state"
    finally:
        conn.close()


def assessments_for(case, outcome=TaskOutcome.USEFUL_COMPLETION):
    return tuple(TaskAssessment(request_id=case.stimulus.task_spec.id,
                 request_ordinal=case.stimulus.request.ordinal, task_id=task.id,
                 outcome=outcome, mandatory_pass=True, reason_codes=())
                 for task in case.stimulus.task_spec.tasks)


@pytest.mark.parametrize("aspect", [raw for raw in INVALID_ASPECTS
                                   if isinstance(raw, dict) and raw.get("task_id") != "missing"])
def test_kind_parameters_fail_independently(aspect):
    with pytest.raises(ValueError):
        AcceptanceAspect.model_validate(aspect)


def test_legacy_decoder_pin_owner_and_raw_type_checks_are_independent():
    case = sealed_store.load_family("task_completion").cases[0]
    changed = case.model_copy(update={"expected": {**case.expected, "note": "changed"}})
    with pytest.raises(ValueError, match="exactly pinned"):
        acceptance_aspect(changed)
    with pytest.raises(ValueError, match="only to Bellwether"):
        validate_acceptance_aspect(case, engagement_slug="northline")
    raw = case.model_dump(mode="json")
    raw["stimulus"]["request"]["ordinal"] = "3"
    parsed = SealedCase.model_validate(raw)
    assert parsed == case
    with pytest.raises(ValueError, match="exactly pinned"):
        validate_legacy_payload(raw, parsed)


@pytest.mark.parametrize("aspect", [raw for raw in INVALID_ASPECTS if isinstance(raw, dict)])
def test_family_validates_typed_aspects_without_deeper_snapshot_guard(tmp_path, monkeypatch, aspect):
    cases = list(sealed_store.load_family("task_completion").cases)
    cases[0] = cases[0].model_copy(update={"expected": {**cases[0].expected, "aspect": aspect}})
    apply_staged_material(monkeypatch, tmp_path / "typed-family-package", {
        "sealed/cases/bookshop_task_completion.json": protected_family_bytes(cases)})
    declaration = registry.resolve_pack("bookshop").families[-1]
    with pytest.raises(InvalidSealedCase, match="invalid protected acceptance"):
        sealed_store.load_declared_family(declaration, slug="bookshop")


@pytest.mark.parametrize("aspect", (
    {"kind": "EVERY_REQUIRED_TASK_RETURNS_A_RESULT"},
    {"kind": "NAMED_TASK_OUTCOMES", "task_id": "collection", "expected_outcomes": ["USEFUL_COMPLETION"]},
    {"kind": "NO_TASK_REASON_CODE", "reason_code": "INVALID_COMMITMENT"},
))
def test_each_typed_aspect_passes_and_fails(aspect):
    original = sealed_store.load_family("task_completion").cases[0]
    case = original.model_copy(update={"expected": {**original.expected, "aspect": aspect}})
    assessments = assessments_for(case)
    assert protected_acceptance(case, assessments), "declared typed aspect did not pass"
    target = next(i for i, row in enumerate(assessments) if row.task_id == "collection")
    changed = list(assessments)
    if aspect["kind"] == "NO_TASK_REASON_CODE":
        changed[target] = changed[target].model_copy(update={"reason_codes": (ReasonCode.INVALID_COMMITMENT,)})
    else:
        changed[target] = changed[target].model_copy(update={"outcome": TaskOutcome.MISSING_OUTPUT})
    assert not protected_acceptance(case, tuple(changed)), "typed aspect failed to detect its own fault"
    # Typed checks cannot waive the independent mandatory assessment.
    changed = [row.model_copy(update={"mandatory_pass": False}) for row in assessments]
    assert not protected_acceptance(case, tuple(changed))


def test_six_legacy_views_preserve_exact_identity():
    path = config.PACKAGE_DIR / "sealed/cases/bookshop_task_completion.json"
    before = path.read_bytes()
    cases = sealed_store.load_family("task_completion").cases
    original_models = [case.model_dump(mode="json") for case in cases]
    refs = [rotation.variant_ref(case) for case in cases]
    assert len(cases) == 6
    assert [acceptance_aspect(case).kind.value for case in cases] == [
        "EVERY_REQUIRED_TASK_RETURNS_A_RESULT", *["NAMED_TASK_OUTCOMES"] * 5]
    assert [case.model_dump(mode="json") for case in cases] == original_models
    assert [rotation.variant_ref(case) for case in cases] == refs
    assert path.read_bytes() == before


@pytest.mark.parametrize("field", ("id", "check_id", "expected", "stimulus", "request_ordinals", "schema_version"))
def test_altered_legacy_payload_is_refused(session, tmp_path, monkeypatch, field):
    a, b, investigation = _comparison_session(session)
    path = config.PACKAGE_DIR / "sealed/cases/bookshop_task_completion.json"
    data = json.loads(path.read_bytes())
    raw = data["cases"][0]
    if field in ("id", "check_id"):
        raw[field] += "-altered"
    elif field == "expected":
        raw[field]["note"] += " altered"
    elif field == "stimulus":
        raw[field]["request"]["ordinal"] = "3"  # Parsing alone would coerce this.
    elif field == "schema_version":
        raw[field] = True  # True == 1 is insufficient exact-payload proof.
    else:
        raw[field] = [4]
    data["sealed_payload_sha256"] = hashlib.sha256(json.dumps(data["cases"], sort_keys=True,
        separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    apply_staged_material(monkeypatch, tmp_path / "altered-legacy-package", {
        "sealed/cases/bookshop_task_completion.json": json.dumps(data).encode()})
    conn = db.connect(session.db_file)
    try:
        before = all_rows(conn)
        with pytest.raises(registry.PackUnavailable):
            _reserve_comparison(session, a, b, investigation)
        assert all_rows(conn) == before, "altered legacy case recorded an exposure"
    finally:
        conn.close()


def test_cross_pack_legacy_is_refused():
    declaration = registry.resolve_pack("bookshop").families[-1]
    with pytest.raises(InvalidSealedCase, match="invalid protected acceptance"):
        sealed_store.load_declared_family(declaration, slug="northline")


def test_reserved_legacy_uses_pins_without_current_file_and_refuses_cross_pack(session, tmp_path, monkeypatch):
    a, b, investigation = _comparison_session(session)
    experiment, _ = _reserve_comparison(session, a, b, investigation)
    conn = db.connect(session.db_file)
    try:
        reservation = repo.get_exposure_reservation_for_experiment(conn, experiment.id)
        before = list(map(tuple, repo.list_protected_case_snapshots(conn, reservation.id)))
        original = sealed_store.load_reserved_comparison_cases(conn, reservation.id)
        monkeypatch.setattr(config, "PACKAGE_DIR", tmp_path / "absent-package")
        assert sealed_store.load_reserved_comparison_cases(conn, reservation.id) == original
        assert list(map(tuple, repo.list_protected_case_snapshots(conn, reservation.id))) == before
        # An existing historical engagement row is not current pack admission.
        repo.seed_engagement(conn, "northline", "northline", "Northline historical")
        conn.execute("UPDATE exposure_reservations SET engagement_slug='northline' WHERE id=?", (reservation.id,))
        with pytest.raises(InvalidSealedCase, match="invalid reserved acceptance"):
            sealed_store.load_reserved_comparison_cases(conn, reservation.id)
        assert list(map(tuple, repo.list_protected_case_snapshots(conn, reservation.id))) == before
    finally:
        conn.rollback()
        conn.close()
