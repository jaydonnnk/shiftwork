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
from shiftwork.domain import canonical, contract_catalog
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
    return sealed_store.load_drawn_cases("run-0001")


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
        with TestClient(create_app(str(Path(workdir) / "eval.db"))) as client:
            shift = client.post("/api/engagements/bookshop/shifts").json()
            contract = json.loads(CONTRACT_FIXTURE.read_text(encoding="utf-8"))
            assert client.post(
                f"/api/shifts/{shift['id']}/artifact/versions", json={"contract": contract}
            ).status_code == 201
            started = client.post(f"/api/shifts/{shift['id']}/runs")
            assert started.status_code == 202
            checks = client.get(f"/api/runs/{started.json()['id']}/checks").json()
    assert len(checks) == 1
    assert checks[0]["reason_code"] == "STALE_BEYOND_RULE"
    ref = checks[0].pop("expected_ref")
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
        sealed_store.load_drawn_cases("run-0001")

    family = _family_copy()
    family["schema_version"] = 2
    _write_family(tmp_path, family)
    with pytest.raises(UnsupportedSealedSchema):
        sealed_store.load_drawn_cases("run-0001")

    # A valid family still loads from the patched directory.
    _write_family(tmp_path, _family_copy())
    cases = sealed_store.load_drawn_cases("run-0001")
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
            sealed_store.load_drawn_cases("run-0001")


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
