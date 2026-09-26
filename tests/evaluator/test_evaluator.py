"""Evaluator family suite (program design S6 C: tests 11-15) + the test 44 evaluator clause.

Written before the Slice 4 implementation: every test here must fail against the
Slice 2/3 minimal evaluator (one hardcoded case, no contract parameterization, no
negative control, no schema alarm). Expectations are hand-authored from the
committed rule semantics, not generated from evaluator output.

Revised 2026-09-18 after an independent execution review returned REVISE. The
review's MAJOR-2 (the response-validation wiring had no end-to-end coverage) is
closed by ``test_validation_failure_through_evaluate_is_malformed_response``;
the MAJOR-1 fix moved every stance rule constant into the catalog v2 learner
labels, guarded by ``test_v2_labels_declare_the_rule_constants`` and
``test_sealed_expected_blocks_carry_no_rule_parameters``; the test 11 closure
scan is now transitive, test 13 searches every scalar in each expected block,
and test 15 plus the ordinals guard cover file-level schema versions and
unusable ordinal lists.

Test 11: transitive import closure of evaluator/sealed/customer_answer contains no
HTTP client, no socket use and no assist module; a full evaluation passes with
sockets blocked. Test 12: the deliberately broken transcript yields failing
verdicts per failure mode; the passing transcript passes (negative control
against an always-pass evaluator). Test 13: results and API payloads carry only
reason codes and opaque refs, never sealed expected values or notes. Test 14: the
same transcript flips verdicts exactly where the committed stance's visible
policy allows both, while fixed invariants stay stance-independent. Test 15: an
unknown sealed schema version, file-level or per-case, is a hard typed error,
never a silent skip. Test 44 (evaluator clause): a declared limit cannot satisfy
a required executable dimension or silently become an evaluator rule.
"""

import ast
import asyncio
import base64
import json
import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from shiftwork import config
from shiftwork.app import create_app
from shiftwork.domain import canonical, contract_catalog, task_contract
from shiftwork.domain.errors import InvalidContract, InvalidSealedCase, UnsupportedSealedSchema
from shiftwork.domain.models import (
    ContractDimension,
    ContractOptionId,
    ContractParams,
    ReasonCode,
    RunOutput,
)
from shiftwork.evaluator import evaluator
from shiftwork.executor import base as executor_base
from shiftwork.executor.recorded import RecordedAdapter
from shiftwork.sealed import store as sealed_store

FAMILY_BATCH = config.FIXTURE_DIR / "requests" / "stale_family.jsonl"
FAMILY_SNAPSHOT = config.FIXTURE_DIR / "shop" / "bookshop_stale_snapshot.json"
PASSING_TRANSCRIPT = config.FIXTURE_DIR / "runs" / "passing_stale.json"
FAILING_TRANSCRIPT = config.FIXTURE_DIR / "runs" / "failing_stale.json"
CONTRACT_FIXTURE = config.FIXTURE_DIR / "artifacts" / "bookshop" / "contract_stale_family.json"
CASE_FILE = config.SEALED_CASES_DIR / "bookshop_stale_information.json"

NEWEST = ContractOptionId.USE_NEWEST_RECORD_WITH_AGE
VERIFY_NOW = ContractOptionId.VERIFY_EXACT_CLAIMS_NOW
HIGH_RISK_ONLY = ContractOptionId.HARD_CHECK_HIGH_RISK_ONLY

# Hand-derived from the committed rule semantics and the hand-authored bodies in
# failing_stale.json (see each sealed case note). Never produced by running the
# evaluator first.
FAILING_UNDER_NEWEST = {
    1: ReasonCode.STALE_BEYOND_RULE,
    2: ReasonCode.STALE_BEYOND_RULE,
    3: ReasonCode.INVENTED_FACT,
    4: ReasonCode.INVENTED_FACT,
    5: ReasonCode.MISSING_EVIDENCE,
    6: ReasonCode.MALFORMED_RESPONSE,
}


def _contract(stance: ContractOptionId, declared_limits: tuple[str, ...] = ()) -> ContractParams:
    # Catalog v2: the version whose labels state the one-hour freshness rule and
    # the price high-risk kind that the evaluator constants mirror.
    return ContractParams(
        catalog_version=2,
        must_never=(ContractOptionId.NEVER_INVENT_PRICE_STOCK_POLICY,),
        selections={ContractDimension.STANCE: stance},
        response_time_limit_ms=3000,
        declared_limits=declared_limits,
    )


def _replay(fixture, run_id: str = "run-0001") -> list[RunOutput]:
    batch_hash = canonical.content_hash(
        base64.b64encode(FAMILY_BATCH.read_bytes()).decode("ascii")
    )
    request = executor_base.RunRequest(
        artifact_snapshot=executor_base.ArtifactSnapshotRef(files={}, manifest_hash="unused-recorded-replay"),
        request_batch=executor_base.BatchRef(path_ref="stale_family.jsonl", content_hash=batch_hash),
        shop_snapshot_ref=str(FAMILY_SNAPSHOT),
        harness_ref="stdlib-loopback-v1",
        image_ref="local-python-stdlib",
        deadline_s=5,
        inference_grant=None,
    )
    result = asyncio.run(RecordedAdapter(fixture).execute(request))
    assert result.failure is None
    batch = {entry.ordinal: entry for entry in executor_base.load_batch(request.request_batch)}
    outputs = []
    for output in executor_base.normalize_captures(result.captures, request.deadline_s):
        outputs.append(
            output.model_copy(
                update={
                    "id": f"{run_id}-out-{output.request_ordinal}",
                    "run_id": run_id,
                    "request_text": batch[output.request_ordinal].text,
                }
            )
        )
    return outputs


def _records() -> dict:
    data = json.loads(FAMILY_SNAPSHOT.read_text(encoding="utf-8"))
    return {record["record_id"]: record for record in data["records"]}


def _cases():
    # The evaluator-level tests score a full family directly; run-scoped draw
    # resolution lives in the orchestrator tests.
    return sealed_store.load_family(sealed_store.STALE_INFORMATION)


def _by_check(results):
    return {result.check_id: result for result in results}


def _ordinal_of(case) -> int:
    return case.request_ordinals[0]


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(config.PACKAGE_DIR).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(["shiftwork", *parts])


def _resolve_module(module_name: str) -> Path | None:
    """Resolve a shiftwork module name to its source file, if one exists."""
    if module_name != "shiftwork" and not module_name.startswith("shiftwork."):
        return None
    parts = module_name.split(".")[1:]
    base = config.PACKAGE_DIR.joinpath(*parts) if parts else config.PACKAGE_DIR
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def _transitive_imports(roots: list[Path]) -> tuple[set[str], set[Path]]:
    """Follow every shiftwork import reachable from ``roots``, to a fixed point."""
    imported: set[str] = set()
    parsed: set[Path] = set()
    queue: list[Path] = []
    for root in roots:
        queue.extend(sorted(root.rglob("*.py")) if root.is_dir() else [root])
    while queue:
        path = queue.pop()
        if path in parsed:
            continue
        parsed.add(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        candidates: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                candidates.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    package = _module_name(path).split(".")
                    if path.name != "__init__.py":
                        package = package[:-1]
                    package = package[: len(package) - (node.level - 1)]
                    base = ".".join(package)
                    if node.module:
                        candidates.append(f"{base}.{node.module}" if base else node.module)
                    else:
                        candidates.extend(
                            f"{base}.{alias.name}" for alias in node.names if alias.name != "*"
                        )
                elif node.module:
                    candidates.append(node.module)
                    candidates.extend(
                        f"{node.module}.{alias.name}" for alias in node.names if alias.name != "*"
                    )
        for name in candidates:
            imported.add(name)
            resolved = _resolve_module(name)
            if resolved is not None:
                queue.append(resolved)
    return imported, parsed


def test_evaluator_import_closure_no_network_no_llm(monkeypatch):
    # Test 11, clause 1: static transitive-closure scan of the evaluation
    # modules: every shiftwork module reachable from the roots is parsed, so a
    # forbidden import inside domain/models.py, canonical.py or errors.py is
    # caught too, not only a direct import at a root.
    forbidden = (
        "http.client",
        "httpx",
        "requests",
        "urllib",
        "socket",
        "aiohttp",
        "ssl",
        "openai",
        "shiftwork.assist",
        "shiftwork.executor",
        "shiftwork.curation",
    )
    roots = [
        config.PACKAGE_DIR / "evaluator",
        config.PACKAGE_DIR / "sealed",
        config.PACKAGE_DIR / "domain" / "customer_answer.py",
    ]
    imported, parsed = _transitive_imports(roots)
    assert imported, "the closure scan found no imports; it would pass vacuously"
    parsed_names = {path.name for path in parsed}
    assert {"models.py", "canonical.py", "errors.py"} <= parsed_names, (
        f"the closure scan did not reach the domain modules; parsed {sorted(str(p) for p in parsed)}"
    )
    for module in imported:
        assert not any(
            module == blocked or module.startswith(blocked + ".") for blocked in forbidden
        ), f"forbidden import in the evaluation closure: {module}"

    # Test 11, clause 2: a full evaluation passes with sockets blocked. The
    # file-based replay runs first (its event loop owns a loopback self-pipe);
    # the evaluation itself must complete without touching any socket.
    outputs = _replay(FAILING_TRANSCRIPT)
    cases = _cases()
    contract = _contract(NEWEST)
    records = _records()

    def blocked(*args, **kwargs):
        raise AssertionError("evaluation attempted network access")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    results = evaluator.evaluate(outputs, cases, contract, records)
    assert len(results) == 6


def test_evaluator_negative_control():
    # Test 12: the deliberately broken transcript fails per failure mode; the
    # hand-authored correct transcript passes. An always-pass or always-fail
    # evaluator cannot satisfy both halves.
    cases = _cases()
    failing = _by_check(
        evaluator.evaluate(_replay(FAILING_TRANSCRIPT), cases, _contract(NEWEST), _records())
    )
    assert len(failing) == 6
    for case in cases.cases:
        result = failing[case.check_id]
        assert result.verdict == "fail", case.check_id
        assert result.reason_code is FAILING_UNDER_NEWEST[_ordinal_of(case)], case.check_id

    passing = evaluator.evaluate(
        _replay(PASSING_TRANSCRIPT), cases, _contract(NEWEST), _records()
    )
    assert len(passing) == 6
    assert all(result.verdict == "pass" and result.reason_code is None for result in passing)


def _expected_scalar_tokens(value) -> list[str]:
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, (str, int)):
        return [str(value)]
    if isinstance(value, list):
        return [token for item in value for token in _expected_scalar_tokens(item)]
    if isinstance(value, dict):
        return [token for item in value.values() for token in _expected_scalar_tokens(item)]
    return []


def _sealed_tokens() -> list[str]:
    """Every scalar in every expected block: record ids, refs, claim values, notes."""
    case_file = json.loads(CASE_FILE.read_text(encoding="utf-8"))
    return [
        token for raw in case_file["cases"] for token in _expected_scalar_tokens(raw["expected"])
    ]


def test_check_results_never_contain_expected_values():
    # Test 13: results carry reason codes and opaque refs only. Every sealed
    # expected scalar (record ids, superseded refs, claim values and notes, not
    # only the claim values) must appear nowhere in a serialized result, and
    # every expected_ref is a distinct opaque hash.
    cases = _cases()
    results = evaluator.evaluate(
        _replay(FAILING_TRANSCRIPT), cases, _contract(NEWEST), _records()
    )
    sealed_values = _sealed_tokens()
    assert len(sealed_values) >= 4 * len(cases.cases)
    assert any(len(value) >= 20 for value in sealed_values)
    refs = set()
    for result in results:
        payload = result.model_dump(mode="json")
        ref = payload.pop("expected_ref")
        assert ref.startswith("sealed:") and len(ref) == len("sealed:") + 64
        int(ref.removeprefix("sealed:"), 16)
        refs.add(ref)
        serialized = json.dumps(payload, sort_keys=True)
        for value in sealed_values:
            assert value not in serialized, result.check_id
    assert len(refs) == len(results)

    # The API projection of the same rules (thin path, case 1) leaks nothing.
    import tempfile

    with tempfile.TemporaryDirectory(prefix="shiftwork-eval-") as workdir:
        with TestClient(
            create_app(str(Path(workdir) / "eval.db"), shop_snapshot=config.THIN_SNAPSHOT)
        ) as client:
            shift = client.post("/api/engagements/bookshop/shifts").json()
            contract = json.loads(CONTRACT_FIXTURE.read_text(encoding="utf-8"))
            assert client.post(
                f"/api/shifts/{shift['id']}/artifact/versions", json={"contract": contract}
            ).status_code == 201
            started = client.post(f"/api/shifts/{shift['id']}/runs")
            assert started.status_code == 202
            checks = client.get(f"/api/runs/{started.json()['id']}/checks").json()
    assert len(checks) == len(config.BOOKSHOP_FAMILIES)
    for check in checks:
        assert check["reason_code"] == "STALE_BEYOND_RULE"
        ref = check.pop("expected_ref")
        assert ref.startswith("sealed:") and len(ref) == len("sealed:") + 64
    serialized = json.dumps(checks, sort_keys=True)
    for value in sealed_values:
        assert value not in serialized


def test_contract_parameterized_checks():
    # Test 14: the same transcript flips exactly where the committed stance's
    # learner-visible policy allows both readings, and never because one hidden
    # stance is rewarded. The two policies in play are constants stated in the
    # catalog v2 labels: the one-hour limit and price as the high-risk kind.
    # Fixed invariants are unaffected by contract choice.
    cases = _cases()
    outputs = _replay(FAILING_TRANSCRIPT)
    ordinal_to_check = {_ordinal_of(case): case.check_id for case in cases.cases}

    newest = _by_check(evaluator.evaluate(outputs, cases, _contract(NEWEST), _records()))
    verify = _by_check(evaluator.evaluate(outputs, cases, _contract(VERIFY_NOW), _records()))
    hard = _by_check(evaluator.evaluate(outputs, cases, _contract(HIGH_RISK_ONLY), _records()))

    # Request 1: hard-asserting stale stock. Refused by the one-hour rule the
    # newest-with-age label states; legitimate under verify-exact (which states
    # no limit and accepts the newest record with its true age) and under
    # hard-check-high-risk-only (stock is not the high-risk kind).
    assert newest[ordinal_to_check[1]].reason_code is ReasonCode.STALE_BEYOND_RULE
    assert verify[ordinal_to_check[1]].verdict == "pass"
    assert hard[ordinal_to_check[1]].verdict == "pass"

    # Request 2: the same shape for a price, the high-risk kind, which the
    # hard-check-high-risk label also refuses, while verify-exact still allows it.
    assert newest[ordinal_to_check[2]].reason_code is ReasonCode.STALE_BEYOND_RULE
    assert verify[ordinal_to_check[2]].verdict == "pass"
    assert hard[ordinal_to_check[2]].reason_code is ReasonCode.STALE_BEYOND_RULE

    # Fixed invariants do not move with the stance.
    for results in (newest, verify, hard):
        assert results[ordinal_to_check[4]].reason_code is ReasonCode.INVENTED_FACT
        assert results[ordinal_to_check[5]].reason_code is ReasonCode.MISSING_EVIDENCE
        assert results[ordinal_to_check[6]].reason_code is ReasonCode.MALFORMED_RESPONSE

    # Correct behavior is never punished by any stance.
    for stance in (NEWEST, VERIFY_NOW, HIGH_RISK_ONLY):
        results = evaluator.evaluate(_replay(PASSING_TRANSCRIPT), cases, _contract(stance), _records())
        assert all(result.verdict == "pass" for result in results), stance


def _family_copy() -> dict:
    return json.loads(CASE_FILE.read_text(encoding="utf-8"))


def _write_family(tmp_path: Path, family: dict) -> None:
    (tmp_path / "bookshop_stale_information.json").write_text(
        json.dumps(family), encoding="utf-8"
    )


def test_unknown_sealed_schema_version_alarms(tmp_path, monkeypatch):
    # Test 15: an unknown sealed schema_version is a hard typed error, both per
    # case and at the file level.
    monkeypatch.setattr(config, "SEALED_CASES_DIR", tmp_path)

    family = _family_copy()
    family["cases"][0]["schema_version"] = 2
    _write_family(tmp_path, family)
    with pytest.raises(UnsupportedSealedSchema):
        sealed_store.load_family(sealed_store.STALE_INFORMATION)

    family = _family_copy()
    family["schema_version"] = 2
    _write_family(tmp_path, family)
    with pytest.raises(UnsupportedSealedSchema):
        sealed_store.load_family(sealed_store.STALE_INFORMATION)

    # A valid family still loads from the patched directory.
    _write_family(tmp_path, _family_copy())
    cases = sealed_store.load_family(sealed_store.STALE_INFORMATION)
    assert len(cases.cases) == 6


def test_sealed_case_ordinals_must_be_usable(tmp_path, monkeypatch):
    # Slice 4 revision guard: a case whose request_ordinals list is empty or
    # duplicated could never match unambiguously, so loading alarms instead of
    # letting the case silently never score.
    monkeypatch.setattr(config, "SEALED_CASES_DIR", tmp_path)
    for broken in ([], [1, 1]):
        family = _family_copy()
        family["cases"][0]["request_ordinals"] = broken
        _write_family(tmp_path, family)
        with pytest.raises(InvalidSealedCase):
            sealed_store.load_family(sealed_store.STALE_INFORMATION)


def test_validation_failure_through_evaluate_is_malformed_response():
    # Slice 4 revision regression (independent review MAJOR-2): evaluate must
    # run validate_service_response, so a body whose age attestation is false
    # or whose ref does not resolve fails MALFORMED_RESPONSE end to end.
    # Replacing that call with a pass-through makes this test fail.
    cases = _cases()
    records = _records()
    outputs = _replay(FAILING_TRANSCRIPT)
    case_id = "chk-stale-information-01"
    false_age = (
        b'{"action":"answer","claims":[{"kind":"stock","value":"in_stock"}],'
        b'"evidence_refs":["catalog:9780441013593"],"record_age_ms":1}'
    )
    bad_ref = (
        b'{"action":"answer","claims":[{"kind":"stock","value":"in_stock"}],'
        b'"evidence_refs":["catalog:no-such-record"],"record_age_ms":1}'
    )
    for body in (false_age, bad_ref):
        probe = [
            output.model_copy(update={"body": body}) if output.request_ordinal == 1 else output
            for output in outputs
        ]
        result = next(
            item
            for item in evaluator.evaluate(probe, cases, _contract(NEWEST), records)
            if item.check_id == case_id
        )
        assert result.verdict == "fail"
        assert result.reason_code is ReasonCode.MALFORMED_RESPONSE

    # Non-vacuous probe: the transcript's own body scores STALE instead.
    baseline = next(
        item
        for item in evaluator.evaluate(outputs, cases, _contract(NEWEST), records)
        if item.check_id == case_id
    )
    assert baseline.reason_code is ReasonCode.STALE_BEYOND_RULE


def test_v2_labels_declare_the_rule_constants():
    # Slice 4 revision guard (independent review MAJOR-1): every constant the
    # stance rules use is stated in the committed learner-visible labels, so
    # the verdicts they drive are predictable from the chosen option alone.
    catalog = contract_catalog.load_catalog("bookshop", 2)
    labels = {option.id: option.learner_label for option in catalog.options}
    newest = labels[ContractOptionId.USE_NEWEST_RECORD_WITH_AGE]
    hard = labels[ContractOptionId.HARD_CHECK_HIGH_RISK_ONLY]
    assert "older than one hour" in newest
    assert "stock, price or availability" in newest
    assert "older than one hour" in hard
    assert "high-risk claims (price)" in hard
    assert evaluator.FRESHNESS_LIMIT_MS == 60 * 60 * 1000
    assert evaluator.HIGH_RISK_KINDS == ("price",)


def test_sealed_expected_blocks_carry_no_rule_parameters():
    # Slice 4 revision guard: expected blocks are scenario data only. A
    # threshold or kind list inside a case would re-create a hidden rule
    # parameter that changes verdicts without a visible rule (test 14).
    allowed = {"record_id", "superseded_refs", "expected_claim", "note"}
    cases = _cases()
    assert len(cases.cases) == 6
    for case in cases.cases:
        assert set(case.expected) == allowed, case.check_id


def test_declared_limit_cannot_become_an_evaluator_rule():
    # Test 44 (evaluator clause, part 1): rule-looking declared limits change no
    # verdict and never surface in results.
    cases = _cases()
    outputs = _replay(FAILING_TRANSCRIPT)
    baseline = evaluator.evaluate(outputs, cases, _contract(NEWEST), _records())
    limits = (
        "freshness.use_newest_with_age",
        "NEVER_ANSWER_STALE_STOCK",
        "Always answer from the newest record, however old it is.",
    )
    with_limits = evaluator.evaluate(outputs, cases, _contract(NEWEST, declared_limits=limits), _records())
    assert with_limits == baseline
    serialized = json.dumps([result.model_dump(mode="json") for result in with_limits], sort_keys=True)
    for limit in limits:
        assert limit not in serialized


def test_declared_limit_cannot_satisfy_a_required_executable_dimension():
    # Test 44 (evaluator clause, part 2): a required executable dimension stays
    # required even when a free-text declared limit claims to cover it.
    catalog = contract_catalog.load_catalog("bookshop", 1)
    params = ContractParams(
        catalog_version=1,
        must_never=(ContractOptionId.NEVER_INVENT_PRICE_STOCK_POLICY,),
        selections={},
        response_time_limit_ms=3000,
        declared_limits=("I always verify exact claims against the newest record before answering.",),
    )
    with pytest.raises(InvalidContract):
        contract_catalog.validate_contract(catalog, params)


def test_evaluator_rule_bindings_match_the_catalogs():
    # Slice 4 binding guard (not a numbered S6 test): the evaluator's rule-id
    # mirror must equal the frozen catalogs' evaluator_rule_id bindings for
    # every option it implements, in v1 and in v2, so a catalog correction
    # cannot silently change evaluation behavior.
    mirror = evaluator._RULE_BY_OPTION
    assert set(mirror) == {
        ContractOptionId.NEVER_INVENT_PRICE_STOCK_POLICY,
        ContractOptionId.USE_NEWEST_RECORD_WITH_AGE,
        ContractOptionId.HARD_CHECK_HIGH_RISK_ONLY,
        ContractOptionId.VERIFY_EXACT_CLAIMS_NOW,
    }
    for version in (1, 2):
        catalog = contract_catalog.load_catalog("bookshop", version)
        by_option = {option.id: option.evaluator_rule_id for option in catalog.options}
        for option_id, rule_id in mirror.items():
            assert by_option[option_id] == rule_id, (version, option_id)


# ---------------------------------------------------------------------------
# Slice 11: task-aware assessment of the reviewed public Bellwether incident
# (Gate 3 obligations 9 to 13 and 15). The sealed-family tests above are
# unchanged: they score the older action/claims envelope and the user-sealed
# inventory stays immutable.
# ---------------------------------------------------------------------------

PIVOT_DATE = "2026-09-26"
PIVOT_REQUESTED = "book:salt-roads:paperback"
PIVOT_ALTERNATIVE = "book:harbour-atlas:paperback"
PIVOT_HARDBACK = "book:salt-roads:hardback"


@pytest.fixture(scope="module")
def pivot_mission():
    return task_contract.load_mission(config.PIVOT_MISSION)


@pytest.fixture(scope="module")
def pivot_snapshot():
    return task_contract.load_public_state(config.PIVOT_PUBLIC_STATE)


@pytest.fixture(scope="module")
def pivot_spec(pivot_mission):
    return pivot_mission.request_specs[0]


def _pivot_result(task_id, status, entity_ref=PIVOT_REQUESTED, claims=(), commitment_ref=None, code=None):
    return {
        "task_id": task_id,
        "status": status,
        "entity_ref": entity_ref,
        "claims": list(claims),
        "commitment_ref": commitment_ref,
        "explanation_code": code,
    }


def _pivot_claim(kind, value, entity_ref=PIVOT_REQUESTED, refs=()):
    return {"kind": kind, "entity_ref": entity_ref, "value": value, "evidence_refs": list(refs)}


def _pivot_envelope(spec, task_results, evidence_refs=()):
    body = json.dumps(
        {
            "request_id": spec.id,
            "task_results": task_results,
            "evidence_refs": list(evidence_refs),
            "uncertainty_codes": [],
        },
        separators=(",", ":"),
    ).encode("utf-8")
    return task_contract.validate_response_envelope(spec, body)


def _assess(spec, mission, snapshot, response):
    return {
        assessment.task_id: assessment
        for assessment in evaluator.assess_request(
            spec=spec,
            request_ordinal=1,
            mission=mission,
            snapshot=snapshot,
            response=response,
        )
    }


def _recorded_starter_envelope(spec):
    """The exact response the pinned starter actually produced."""
    return _pivot_envelope(
        spec,
        [
            _pivot_result(
                "price",
                "COMPLETED",
                claims=[_pivot_claim("price", 1800, refs=["public:salt-roads:paperback:price"])],
            )
        ],
        evidence_refs=["public:salt-roads:paperback:price"],
    )


def _complete_envelope(spec):
    return _pivot_envelope(
        spec,
        [
            _pivot_result(
                "price",
                "COMPLETED",
                claims=[_pivot_claim("price", 1800, refs=["public:salt-roads:paperback:price"])],
            ),
            _pivot_result(
                "collection",
                "COMPLETED",
                claims=[
                    _pivot_claim(
                        "availability",
                        {"collection_date": PIVOT_DATE, "can_collect": False},
                        refs=["public:salt-roads:paperback:collection"],
                    )
                ],
            ),
            _pivot_result(
                "alternative",
                "COMPLETED",
                entity_ref=PIVOT_ALTERNATIVE,
                claims=[
                    _pivot_claim("price", 1600, PIVOT_ALTERNATIVE, ["public:harbour-atlas:paperback:price"]),
                    _pivot_claim("stock", 3, PIVOT_ALTERNATIVE, ["public:harbour-atlas:paperback:stock"]),
                    _pivot_claim(
                        "availability",
                        {"collection_date": PIVOT_DATE, "can_collect": True},
                        PIVOT_ALTERNATIVE,
                        ["public:harbour-atlas:paperback:collection"],
                    ),
                ],
            ),
        ],
        evidence_refs=[
            "public:salt-roads:paperback:price",
            "public:salt-roads:paperback:collection",
            "public:harbour-atlas:paperback:price",
            "public:harbour-atlas:paperback:stock",
            "public:harbour-atlas:paperback:collection",
        ],
    )


def _snapshot_with(snapshot, record_id, **fields):
    return snapshot.model_copy(
        update={
            "records": tuple(
                record.model_copy(update=fields) if record.record_id == record_id else record
                for record in snapshot.records
            )
        }
    )


def test_true_price_without_collection_or_alternative_fails_required_tasks(
    pivot_spec, pivot_mission, pivot_snapshot
):
    """Obligation 9: the reviewed starter's real output, assessed.

    Every claim the starter made is true and supported. The request still fails,
    because a supported optional price does not complete either required task.
    """
    assessed = _assess(
        pivot_spec, pivot_mission, pivot_snapshot, _recorded_starter_envelope(pivot_spec)
    )
    assert assessed["price"].outcome is task_contract.TaskOutcome.USEFUL_COMPLETION
    for task_id in ("collection", "alternative"):
        assert assessed[task_id].outcome is task_contract.TaskOutcome.MISSING_OUTPUT
        assert ReasonCode.REQUIRED_TASK_MISSING in assessed[task_id].reason_codes
        assert assessed[task_id].mandatory_pass is False
    assert evaluator.request_usefully_completed(pivot_spec, list(assessed.values())) is False


def test_a_complete_answer_usefully_completes_the_same_request(
    pivot_spec, pivot_mission, pivot_snapshot
):
    """Negative control: the assessor is not simply always failing."""
    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, _complete_envelope(pivot_spec))
    for task_id in ("price", "collection", "alternative"):
        assert assessed[task_id].outcome is task_contract.TaskOutcome.USEFUL_COMPLETION, task_id
    assert evaluator.request_usefully_completed(pivot_spec, list(assessed.values())) is True


@pytest.mark.parametrize(
    "task_results",
    [
        [_pivot_result("price", "COMPLETED", claims=[_pivot_claim("price", 1800, refs=["public:salt-roads:paperback:price"])])],
        [_pivot_result("collection", "COMPLETED", claims=[_pivot_claim("availability", {"collection_date": PIVOT_DATE, "can_collect": False}, refs=["public:salt-roads:paperback:collection"])])],
        [],
    ],
    ids=["price-only-stub", "collection-only-stub", "empty-stub"],
)
def test_a_stubbed_success_cannot_carry_the_request(
    pivot_spec, pivot_mission, pivot_snapshot, task_results
):
    """A stub that returns some true answer must still fail the required-task set."""
    response = _pivot_envelope(pivot_spec, task_results, evidence_refs=[
        ref for result in task_results for claim in result["claims"] for ref in claim["evidence_refs"]
    ])
    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, response)
    assert evaluator.request_usefully_completed(pivot_spec, list(assessed.values())) is False


def test_wrong_entity_supported_claim_fails(pivot_spec, pivot_mission, pivot_snapshot):
    """Obligation 10: truth is not relevance.

    The hardback really is available for collection on the requested date and the
    claim cites a real agreeing record. It still cannot answer a paperback
    question.
    """
    response = _pivot_envelope(
        pivot_spec,
        [
            _pivot_result(
                "collection",
                "COMPLETED",
                entity_ref=PIVOT_HARDBACK,
                claims=[
                    _pivot_claim(
                        "availability",
                        {"collection_date": PIVOT_DATE, "can_collect": True},
                        PIVOT_HARDBACK,
                        ["public:salt-roads:hardback:collection"],
                    ),
                    _pivot_claim("stock", 2, PIVOT_HARDBACK, ["public:salt-roads:hardback:stock"]),
                ],
            )
        ],
        evidence_refs=["public:salt-roads:hardback:collection", "public:salt-roads:hardback:stock"],
    )
    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, response)
    assert assessed["collection"].outcome is task_contract.TaskOutcome.INCORRECT_OUTPUT
    assert ReasonCode.WRONG_ENTITY in assessed["collection"].reason_codes
    assert assessed["collection"].mandatory_pass is False


def test_a_true_price_for_the_wrong_edition_is_unsupported(
    pivot_spec, pivot_mission, pivot_snapshot
):
    response = _pivot_envelope(
        pivot_spec,
        [
            _pivot_result(
                "price",
                "COMPLETED",
                claims=[_pivot_claim("price", 2400, PIVOT_HARDBACK, ["public:salt-roads:hardback:price"])],
            )
        ],
        evidence_refs=["public:salt-roads:hardback:price"],
    )
    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, response)
    assert ReasonCode.WRONG_ENTITY in assessed["price"].reason_codes


def test_a_result_labelled_with_the_wrong_entity_fails_even_when_its_claims_are_right(
    pivot_spec, pivot_mission, pivot_snapshot
):
    """Isolates the result-level entity check from the claim-level one.

    Every claim here names the requested paperback and is fully supported, so the
    only defect is the result's own ``entity_ref``. Without this case the two limbs
    of the same rule catch each other's faults and prove neither.
    """
    response = _pivot_envelope(
        pivot_spec,
        [
            _pivot_result(
                "price",
                "COMPLETED",
                entity_ref=PIVOT_HARDBACK,
                claims=[_pivot_claim("price", 1800, PIVOT_REQUESTED, ["public:salt-roads:paperback:price"])],
            )
        ],
        evidence_refs=["public:salt-roads:paperback:price"],
    )
    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, response)
    assert ReasonCode.WRONG_ENTITY in assessed["price"].reason_codes
    assert assessed["price"].outcome is task_contract.TaskOutcome.INCORRECT_OUTPUT


def test_justified_fallbacks_on_every_required_task_do_not_complete_the_request(
    pivot_spec, pivot_mission, pivot_snapshot
):
    """Isolates the required-task limb of ``request_usefully_completed``.

    Every mandatory rule passes in this variation: the price is supported, the
    collection referral is justified by contradictory necessary information, and
    the refusal is justified because no candidate meets the budget. The request
    still did not usefully complete, because a justified fallback never counts as
    completion. The ``mandatory_pass`` premise below is what stops the earlier
    short-circuit from masking this limb.
    """
    varied = _snapshot_with(
        _snapshot_with(
            pivot_snapshot,
            "public:salt-roads:paperback:collection",
            value={"collection_date": PIVOT_DATE, "can_collect": True},
        ),
        "public:harbour-atlas:paperback:price",
        value=2400,
    )
    response = _pivot_envelope(
        pivot_spec,
        [
            _pivot_result(
                "price",
                "COMPLETED",
                claims=[_pivot_claim("price", 1800, refs=["public:salt-roads:paperback:price"])],
            ),
            _pivot_result("collection", "REFERRED", code="PUBLIC_DATA_UNAVAILABLE"),
            _pivot_result("alternative", "REFUSED", code="NO_MATCHING_ALTERNATIVE"),
        ],
        evidence_refs=["public:salt-roads:paperback:price"],
    )
    assessed = _assess(pivot_spec, pivot_mission, varied, response)
    assert assessed["price"].outcome is task_contract.TaskOutcome.USEFUL_COMPLETION
    assert assessed["collection"].outcome is task_contract.TaskOutcome.JUSTIFIED_REFERRAL
    assert assessed["alternative"].outcome is task_contract.TaskOutcome.JUSTIFIED_REFUSAL
    assert all(item.mandatory_pass for item in assessed.values()), "isolation premise broke"
    assert evaluator.request_usefully_completed(pivot_spec, list(assessed.values())) is False


def test_blanket_refusal_is_not_useful_completion(pivot_spec, pivot_mission, pivot_snapshot):
    """Obligation 11: refusal and blanket clarification stay out of completion."""
    refused = _pivot_envelope(
        pivot_spec,
        [_pivot_result("collection", "REFUSED", code="PUBLIC_DATA_UNAVAILABLE")],
    )
    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, refused)
    assert assessed["collection"].outcome is task_contract.TaskOutcome.UNJUSTIFIED_REFUSAL
    assert ReasonCode.UNJUSTIFIED_REFUSAL in assessed["collection"].reason_codes
    assert assessed["collection"].mandatory_pass is False
    assert evaluator.request_usefully_completed(pivot_spec, list(assessed.values())) is False


def test_an_unneeded_clarification_is_unjustified(pivot_spec, pivot_mission, pivot_snapshot):
    """The request names one title and one edition and resolves tomorrow already."""
    for code in ("MISSING_ENTITY_DETAIL", "MISSING_COLLECTION_DATE"):
        response = _pivot_envelope(
            pivot_spec, [_pivot_result("collection", "NEEDS_CLARIFICATION", code=code)]
        )
        assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, response)
        assert assessed["collection"].outcome is task_contract.TaskOutcome.UNJUSTIFIED_CLARIFICATION, code
        assert ReasonCode.UNJUSTIFIED_CLARIFICATION in assessed["collection"].reason_codes
        assert assessed["collection"].mandatory_pass is False


def test_a_justified_referral_is_distinct_from_a_justified_refusal(
    pivot_spec, pivot_mission, pivot_snapshot
):
    """Obligation 12: both fallbacks can be justified, and neither is completion.

    The referral needs contradictory necessary information, which the reviewed
    state does not contain, so the snapshot is varied to create it: current
    can_collect=true against current stock zero.
    """
    contradicted = _snapshot_with(
        pivot_snapshot,
        "public:salt-roads:paperback:collection",
        value={"collection_date": PIVOT_DATE, "can_collect": True},
    )
    referred = _pivot_envelope(
        pivot_spec, [_pivot_result("collection", "REFERRED", code="PUBLIC_DATA_UNAVAILABLE")]
    )
    assessed = _assess(pivot_spec, pivot_mission, contradicted, referred)
    assert assessed["collection"].outcome is task_contract.TaskOutcome.JUSTIFIED_REFERRAL
    assert assessed["collection"].mandatory_pass is True
    assert assessed["collection"].reason_codes == ()
    assert evaluator.request_usefully_completed(pivot_spec, list(assessed.values())) is False

    # The same referral against the reviewed state is unjustified: nothing there
    # is missing, stale, unavailable or conflicting.
    unjustified = _assess(pivot_spec, pivot_mission, pivot_snapshot, referred)
    assert unjustified["collection"].outcome is task_contract.TaskOutcome.UNJUSTIFIED_REFERRAL

    # A justified refusal needs a complete catalog with no qualifying candidate.
    priced_out = _snapshot_with(pivot_snapshot, "public:harbour-atlas:paperback:price", value=2400)
    refused = _pivot_envelope(
        pivot_spec, [_pivot_result("alternative", "REFUSED", code="NO_MATCHING_ALTERNATIVE")]
    )
    refusal_assessed = _assess(pivot_spec, pivot_mission, priced_out, refused)
    assert refusal_assessed["alternative"].outcome is task_contract.TaskOutcome.JUSTIFIED_REFUSAL
    assert refusal_assessed["alternative"].mandatory_pass is True
    assert evaluator.request_usefully_completed(pivot_spec, list(refusal_assessed.values())) is False

    # With the reviewed alternative in stock the same refusal is unjustified.
    assert (
        _assess(pivot_spec, pivot_mission, pivot_snapshot, refused)["alternative"].outcome
        is task_contract.TaskOutcome.UNJUSTIFIED_REFUSAL
    )


def test_a_referral_cannot_borrow_another_candidates_data_problem(
    pivot_spec, pivot_mission, pivot_snapshot
):
    """An unresolvable candidate does not justify referral while a qualifying one exists."""
    unknown = pivot_snapshot.model_copy(
        update={
            "records": pivot_snapshot.records
            + (
                task_contract.PublicRecord(
                    record_id="public:salt-roads:hardback:stock:conflict",
                    entity_ref=PIVOT_HARDBACK,
                    kind="stock",
                    value=9,
                    record_age_ms=0,
                    dependency="inventory",
                ),
            )
        }
    )
    referred = _pivot_envelope(
        pivot_spec, [_pivot_result("alternative", "REFERRED", code="PUBLIC_DATA_UNAVAILABLE")]
    )
    assessed = _assess(pivot_spec, pivot_mission, unknown, referred)
    assert assessed["alternative"].outcome is task_contract.TaskOutcome.UNJUSTIFIED_REFERRAL


def test_missing_capture_is_missing_evidence_not_refusal(pivot_spec, pivot_mission, pivot_snapshot):
    """Obligation 13: absent execution evidence cannot become an answer."""
    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, None)
    assert set(assessed) == {"price", "collection", "alternative"}
    for task_id, assessment in assessed.items():
        assert assessment.outcome is task_contract.TaskOutcome.MISSING_OUTPUT, task_id
        assert ReasonCode.MISSING_EXECUTION_EVIDENCE in assessment.reason_codes, task_id
        assert assessment.mandatory_pass is False, task_id
        for forbidden in (
            task_contract.TaskOutcome.JUSTIFIED_REFUSAL,
            task_contract.TaskOutcome.JUSTIFIED_REFERRAL,
            task_contract.TaskOutcome.JUSTIFIED_CLARIFICATION,
            task_contract.TaskOutcome.UNJUSTIFIED_REFUSAL,
            task_contract.TaskOutcome.UNJUSTIFIED_REFERRAL,
            task_contract.TaskOutcome.UNJUSTIFIED_CLARIFICATION,
        ):
            assert assessment.outcome is not forbidden, task_id


def test_an_unsupported_claim_value_fails(pivot_spec, pivot_mission, pivot_snapshot):
    response = _pivot_envelope(
        pivot_spec,
        [_pivot_result("price", "COMPLETED", claims=[_pivot_claim("price", 1999, refs=["public:salt-roads:paperback:price"])])],
        evidence_refs=["public:salt-roads:paperback:price"],
    )
    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, response)
    assert ReasonCode.UNSUPPORTED_CLAIM in assessed["price"].reason_codes
    assert assessed["price"].outcome is task_contract.TaskOutcome.INCORRECT_OUTPUT


def test_citing_the_newest_record_of_a_conflicting_group_is_unsupported(
    pivot_spec, pivot_mission, pivot_snapshot
):
    conflicted = pivot_snapshot.model_copy(
        update={
            "records": pivot_snapshot.records
            + (
                task_contract.PublicRecord(
                    record_id="public:salt-roads:paperback:price:newer",
                    entity_ref=PIVOT_REQUESTED,
                    kind="price",
                    value=1999,
                    currency="GBP",
                    record_age_ms=0,
                    dependency="catalog",
                ),
            )
        }
    )
    response = _pivot_envelope(
        pivot_spec,
        [_pivot_result("price", "COMPLETED", claims=[_pivot_claim("price", 1999, refs=["public:salt-roads:paperback:price:newer"])])],
        evidence_refs=["public:salt-roads:paperback:price:newer"],
    )
    assessed = _assess(pivot_spec, pivot_mission, conflicted, response)
    assert ReasonCode.UNSUPPORTED_CLAIM in assessed["price"].reason_codes


def test_a_collection_answer_may_not_create_a_commitment(
    pivot_spec, pivot_mission, pivot_snapshot
):
    response = _pivot_envelope(
        pivot_spec,
        [
            _pivot_result(
                "collection",
                "COMPLETED",
                commitment_ref="booking-0001",
                claims=[
                    _pivot_claim(
                        "availability",
                        {"collection_date": PIVOT_DATE, "can_collect": False},
                        refs=["public:salt-roads:paperback:collection"],
                    )
                ],
            )
        ],
        evidence_refs=["public:salt-roads:paperback:collection"],
    )
    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, response)
    assert ReasonCode.INVALID_COMMITMENT in assessed["collection"].reason_codes
    assert assessed["collection"].mandatory_pass is False


def test_a_true_can_collect_needs_supported_positive_stock(
    pivot_spec, pivot_mission, pivot_snapshot
):
    """The requested edition has zero stock, so confirming collection is unsupported."""
    response = _pivot_envelope(
        pivot_spec,
        [
            _pivot_result(
                "collection",
                "COMPLETED",
                claims=[
                    _pivot_claim(
                        "availability",
                        {"collection_date": PIVOT_DATE, "can_collect": True},
                        refs=["public:salt-roads:paperback:collection"],
                    )
                ],
            )
        ],
        evidence_refs=["public:salt-roads:paperback:collection"],
    )
    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, response)
    assert assessed["collection"].outcome is task_contract.TaskOutcome.INCORRECT_OUTPUT
    assert ReasonCode.UNSUPPORTED_CLAIM in assessed["collection"].reason_codes


def test_a_supported_negative_collection_answer_usefully_completes(
    pivot_spec, pivot_mission, pivot_snapshot
):
    """`can_collect=false` is an answer, not a refusal, and needs no stock claim."""
    response = _pivot_envelope(
        pivot_spec,
        [
            _pivot_result(
                "collection",
                "COMPLETED",
                claims=[
                    _pivot_claim(
                        "availability",
                        {"collection_date": PIVOT_DATE, "can_collect": False},
                        refs=["public:salt-roads:paperback:collection"],
                    )
                ],
            )
        ],
        evidence_refs=["public:salt-roads:paperback:collection"],
    )
    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, response)
    assert assessed["collection"].outcome is task_contract.TaskOutcome.USEFUL_COMPLETION


def test_not_applicable_needs_independently_confirmed_collection(
    pivot_spec, pivot_mission, pivot_snapshot
):
    """A service declaring the alternative task away is not evidence it was inactive."""
    declared_away = _pivot_envelope(pivot_spec, [_pivot_result("alternative", "NOT_APPLICABLE")])
    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, declared_away)
    assert assessed["alternative"].outcome is task_contract.TaskOutcome.INCORRECT_OUTPUT
    assert ReasonCode.REQUIRED_TASK_MISSING in assessed["alternative"].reason_codes

    confirmed = _snapshot_with(
        _snapshot_with(
            pivot_snapshot,
            "public:salt-roads:paperback:collection",
            value={"collection_date": PIVOT_DATE, "can_collect": True},
        ),
        "public:salt-roads:paperback:stock",
        value=4,
    )
    justified = _assess(pivot_spec, pivot_mission, confirmed, declared_away)
    assert justified["alternative"].outcome is task_contract.TaskOutcome.JUSTIFIED_REFUSAL
    assert justified["alternative"].mandatory_pass is True


def test_an_over_budget_alternative_is_not_a_useful_completion(
    pivot_spec, pivot_mission, pivot_snapshot
):
    """Exactly twenty pounds does not satisfy under twenty pounds."""
    response = _pivot_envelope(
        pivot_spec,
        [
            _pivot_result(
                "alternative",
                "COMPLETED",
                entity_ref=PIVOT_HARDBACK,
                claims=[
                    _pivot_claim("price", 2400, PIVOT_HARDBACK, ["public:salt-roads:hardback:price"]),
                    _pivot_claim("stock", 2, PIVOT_HARDBACK, ["public:salt-roads:hardback:stock"]),
                    _pivot_claim(
                        "availability",
                        {"collection_date": PIVOT_DATE, "can_collect": True},
                        PIVOT_HARDBACK,
                        ["public:salt-roads:hardback:collection"],
                    ),
                ],
            )
        ],
        evidence_refs=[
            "public:salt-roads:hardback:price",
            "public:salt-roads:hardback:stock",
            "public:salt-roads:hardback:collection",
        ],
    )
    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, response)
    assert assessed["alternative"].outcome is task_contract.TaskOutcome.INCORRECT_OUTPUT
    assert ReasonCode.UNSUPPORTED_CLAIM in assessed["alternative"].reason_codes


def test_a_alternative_missing_its_stock_claim_is_incomplete(
    pivot_spec, pivot_mission, pivot_snapshot
):
    response = _pivot_envelope(
        pivot_spec,
        [
            _pivot_result(
                "alternative",
                "COMPLETED",
                entity_ref=PIVOT_ALTERNATIVE,
                claims=[
                    _pivot_claim("price", 1600, PIVOT_ALTERNATIVE, ["public:harbour-atlas:paperback:price"]),
                    _pivot_claim(
                        "availability",
                        {"collection_date": PIVOT_DATE, "can_collect": True},
                        PIVOT_ALTERNATIVE,
                        ["public:harbour-atlas:paperback:collection"],
                    ),
                ],
            )
        ],
        evidence_refs=[
            "public:harbour-atlas:paperback:price",
            "public:harbour-atlas:paperback:collection",
        ],
    )
    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, response)
    assert ReasonCode.REQUIRED_TASK_MISSING in assessed["alternative"].reason_codes


def test_assessment_is_deterministic(pivot_spec, pivot_mission, pivot_snapshot):
    response = _recorded_starter_envelope(pivot_spec)
    first = _assess(pivot_spec, pivot_mission, pivot_snapshot, response)
    second = _assess(pivot_spec, pivot_mission, pivot_snapshot, response)
    assert first == second


def test_task_assessor_reads_no_database_or_network(
    pivot_spec, pivot_mission, pivot_snapshot, monkeypatch
):
    """Obligation 15's runtime limb for the task-aware path.

    The mission and snapshot are loaded once by the caller and passed in, so
    assessment has nothing to reach for. Blocking sockets makes an implicit
    network read fail here instead of passing silently. The static limb below
    covers the import closure.
    """

    def deny_socket(*args, **kwargs):
        raise AssertionError("the task assessor opened a socket")

    monkeypatch.setattr(socket, "socket", deny_socket)

    assessed = _assess(pivot_spec, pivot_mission, pivot_snapshot, _recorded_starter_envelope(pivot_spec))
    assert assessed["collection"].outcome is task_contract.TaskOutcome.MISSING_OUTPUT
    assert evaluator.request_usefully_completed(pivot_spec, list(assessed.values())) is False


def test_task_assessment_import_closure_has_no_io(pivot_spec, pivot_mission, pivot_snapshot):
    """Obligation 15's static limb: task_contract joins the pure import closure."""
    source = Path(task_contract.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"requests", "httpx", "urllib", "http", "socket", "sqlite3", "os", "subprocess"}
    assert imported & forbidden == set(), f"task_contract imports IO modules: {imported & forbidden}"
    assert "pathlib" in imported, "the loaders take an explicit Path from the caller"
