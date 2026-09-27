"""Offline guards for the Slice 12 spike verifiers.

These checks exist because of the F3 and F4 review findings. F3: the capture
verifier must download the checkpoint file and compare a digest, never branch on
a stdout marker. F4: every absence assertion needs a positive control that
proves the detection code can fire, and an unexercised control must be recorded
as unproven rather than passed. The later guards cover the remaining F5 probes:
a provider or transport outage must be recorded without a business write, an
escape attempt must stay inside the declared tool list and token ceiling, a
prior operation must reject cross-run reuse, six trials must fit the budget, and
the judge route must report every prerequisite. Each classifier here is a pure
function, so every verdict can be judged without a Sandbox. Nothing in this
module contacts the API or needs credentials; the live clauses stay unrun.

Each test is written to fail when its own branch of a classifier is mutated.
The archiving guards go further: they run `infer()` against a fake HTTP client
and require the archived record to carry the whole provider payload, and they
require the judge route to archive its own checks and verdict instead of only
printing them.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile

from demos import gateway_spike_live as spike


PAYLOAD = bytes(range(256)) * 8192  # 2 MiB, deterministic on any machine
PAYLOAD_SHA256 = hashlib.sha256(PAYLOAD).hexdigest()


def _classify(downloaded: bytes | None, write_acknowledged: bool = True) -> str:
    return spike.classify_capture(
        expected_size=len(PAYLOAD),
        expected_sha256=PAYLOAD_SHA256,
        downloaded=downloaded,
        write_acknowledged=write_acknowledged,
    )


def test_intact_download_passes_the_capture_check():
    assert _classify(PAYLOAD) == spike.CAPTURE_PASS


def test_intact_bytes_pass_even_without_a_stdout_marker():
    assert _classify(PAYLOAD, write_acknowledged=False) == spike.CAPTURE_PASS


def test_zero_byte_readback_is_an_empty_capture_stop():
    assert _classify(b"") == spike.CAPTURE_EMPTY


def test_short_readback_is_a_truncated_capture_stop():
    assert _classify(PAYLOAD[:1024]) == spike.CAPTURE_TRUNCATED


def test_same_size_different_bytes_is_a_digest_mismatch_stop():
    mutated = bytearray(PAYLOAD)
    mutated[0] ^= 0xFF
    assert len(mutated) == len(PAYLOAD)
    assert _classify(bytes(mutated)) == spike.CAPTURE_DIGEST_MISMATCH


def test_missing_download_is_an_unavailable_capture_stop():
    assert _classify(None) == spike.CAPTURE_UNAVAILABLE


def test_unacknowledged_write_with_no_bytes_is_not_a_capture_loss():
    assert _classify(b"", write_acknowledged=False) == spike.CAPTURE_WRITE_UNACKNOWLEDGED
    assert _classify(None, write_acknowledged=False) == spike.CAPTURE_WRITE_UNACKNOWLEDGED


def test_pair_of_intact_captures_is_stable():
    verdict = spike.classify_pair(
        control=spike.CAPTURE_PASS, treatment=spike.CAPTURE_PASS
    )
    assert verdict == spike.PAIR_STABLE


def test_intact_control_with_empty_treatment_reproduces_loss_under_cap():
    verdict = spike.classify_pair(
        control=spike.CAPTURE_PASS, treatment=spike.CAPTURE_EMPTY
    )
    assert verdict == spike.PAIR_LOSS_UNDER_CAP


def test_truncated_control_is_not_evidence_about_the_cap():
    verdict = spike.classify_pair(
        control=spike.CAPTURE_TRUNCATED, treatment=spike.CAPTURE_PASS
    )
    assert verdict == spike.PAIR_CONTROL_UNRELIABLE


def test_unavailable_evidence_outranks_the_control_label():
    verdict = spike.classify_pair(
        control=spike.CAPTURE_UNAVAILABLE, treatment=spike.CAPTURE_PASS
    )
    assert verdict == spike.PAIR_EVIDENCE_UNAVAILABLE


def test_unacknowledged_treatment_is_inconclusive_rather_than_a_loss():
    verdict = spike.classify_pair(
        control=spike.CAPTURE_PASS, treatment=spike.CAPTURE_WRITE_UNACKNOWLEDGED
    )
    assert verdict == spike.PAIR_TREATMENT_UNACKNOWLEDGED


def _checks(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "positive_control_env_lookup": True,
        "positive_control_sentinel_present": True,
        "positive_control_loopback_connect": True,
        "canary_name_present": False,
        "canary_value_present": False,
        "provider_env_present": False,
        "controller_file_present": False,
        "arbitrary_https": False,
        "metadata_ip": False,
        "controller_loopback": False,
    }
    base.update(overrides)
    return base


def test_absence_checks_pass_only_with_every_control_fired_and_every_target_absent():
    assert spike.classify_absence_controls(_checks()) == spike.ABSENCE_PASS


def test_leaked_canary_value_stops_the_absence_checks():
    verdict = spike.classify_absence_controls(_checks(canary_value_present=True))
    assert verdict == spike.ABSENCE_LEAK


def test_control_that_did_not_fire_leaves_the_absence_checks_unproven():
    verdict = spike.classify_absence_controls(
        _checks(positive_control_sentinel_present=False)
    )
    assert verdict == spike.ABSENCE_UNPROVEN


def test_missing_check_key_is_inconclusive_rather_than_absent():
    checks = _checks()
    del checks["metadata_ip"]
    assert spike.classify_absence_controls(checks) == spike.ABSENCE_INCONCLUSIVE


def test_every_record_carries_a_utc_stamp_and_the_producing_source_hash():
    record = spike.build_record("unit_probe", {"value": 1})
    assert record.get("probe") == "unit_probe"
    assert record.get("source_sha256") == spike.SOURCE_SHA256
    stamp = record.get("recorded_utc")
    assert isinstance(stamp, str) and stamp.endswith("+00:00") and "T" in stamp


def test_emit_writes_the_stamped_record_to_the_configured_sink():
    sink = Path(tempfile.mkdtemp()) / "slice12-unit-TEST.jsonl"
    original = spike.EVIDENCE_SINK
    spike.EVIDENCE_SINK = sink
    try:
        spike.emit("unit_probe", value=7)
    finally:
        spike.EVIDENCE_SINK = original
    lines = sink.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record.get("probe") == "unit_probe"
    assert record.get("value") == 7
    assert record.get("source_sha256") == spike.SOURCE_SHA256
    stamp = record.get("recorded_utc")
    assert isinstance(stamp, str) and stamp.endswith("+00:00")


def test_emit_refuses_to_write_without_a_run_sink():
    original = spike.EVIDENCE_SINK
    spike.EVIDENCE_SINK = None
    try:
        try:
            spike.emit("unit_probe", value=1)
        except RuntimeError as exc:
            assert "evidence_sink_not_set" in str(exc)
        else:
            raise AssertionError("emit wrote a record with no run sink configured")
    finally:
        spike.EVIDENCE_SINK = original


def test_new_run_never_targets_the_archived_append_only_file():
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        path = spike.new_evidence_sink("pair", directory=directory)
        assert path.name.startswith("slice12-pair-")
        assert path.name.endswith("Z.jsonl")
        assert path.name != "slice12-live-2026-09-26.jsonl"
        assert not path.exists()


def test_second_run_in_the_same_second_refuses_to_merge_records():
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        fixed = datetime(2026, 9, 26, 12, 0, 0, tzinfo=timezone.utc)
        first = spike.new_evidence_sink("pair", directory=directory, now=fixed)
        first.write_text("{}\n", encoding="utf-8")
        try:
            spike.new_evidence_sink("pair", directory=directory, now=fixed)
        except RuntimeError as exc:
            assert "evidence_run_file_exists" in str(exc)
        else:
            raise AssertionError("a reused run file would merge two runs")


def test_budget_reservation_sums_every_slice12_evidence_file():
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        (directory / "slice12-live-2026-09-26.jsonl").write_text(
            json.dumps({"probe": "nemotron_inference",
                        "estimated_usd_from_displayed_rate": 0.0001}) + "\n",
            encoding="utf-8",
        )
        (directory / "slice12-pair-20260927T000000Z.jsonl").write_text(
            json.dumps({"probe": "inference_budget_reservation",
                        "worst_case_usd": 0.0005}) + "\n",
            encoding="utf-8",
        )
        (directory / "unrelated.jsonl").write_text(
            json.dumps({"probe": "nemotron_inference",
                        "estimated_usd_from_displayed_rate": 9.0}) + "\n",
            encoding="utf-8",
        )
        assert abs(spike.prior_inference_spend(directory) - 0.0006) < 1e-9


def test_unknown_prior_inference_cost_still_stops_the_budget_check():
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        (directory / "slice12-live-2026-09-26.jsonl").write_text(
            json.dumps({"probe": "nemotron_inference"}) + "\n", encoding="utf-8"
        )
        try:
            spike.prior_inference_spend(directory)
        except RuntimeError as exc:
            assert "unknown_prior_inference_cost" in str(exc)
        else:
            raise AssertionError("an unpriced prior inference call was ignored")


def test_inference_calls_are_archived_from_one_emit_site():
    source = Path(spike.__file__).read_text(encoding="utf-8")
    marker = 'emit("nemotron_inference"'
    assert source.count(marker) == 1, "every inference call must be archived by exactly one emit site"
    infer_body = source.split("async def infer(", 1)[1].split("\nasync def ", 1)[0]
    assert marker in infer_body, "the single inference emit must live inside infer()"


UNIT_PROVIDER_BODY: dict[str, object] = {
    "id": "chatcmpl-slice12-unit",
    "object": "chat.completion",
    "created": 1789000000,
    "model": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
    "choices": [
        {
            "index": 0,
            "finish_reason": "stop",
            "message": {
                "role": "assistant",
                "content": "\nSTOCK",
                "reasoning_content": "The customer asks about Salt Roads; the stock lookup answers it.",
            },
        }
    ],
    "usage": {
        "prompt_tokens": 45,
        "completion_tokens": 117,
        "total_tokens": 162,
        "completion_tokens_details": {"reasoning_tokens": 113},
    },
    "system_fingerprint": "fp_slice12_unit",
}


class _FakeChatResponse:
    def __init__(self, body: dict[str, object]) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._body


class _FakeChatClient:
    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    async def __aenter__(self) -> "_FakeChatClient":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def post(self, url: str, **kwargs: object) -> _FakeChatResponse:
        return _FakeChatResponse(UNIT_PROVIDER_BODY)


def _inference_records(sink: Path) -> list[dict]:
    lines = sink.read_text(encoding="utf-8").splitlines()
    return [record for record in (json.loads(line) for line in lines)
            if record["probe"] == "nemotron_inference"]


def test_inference_record_archives_the_whole_provider_payload(monkeypatch, tmp_path):
    sink = tmp_path / "slice12-unit-infer-TEST.jsonl"
    monkeypatch.setattr(spike, "EVIDENCE_SINK", sink)
    monkeypatch.setattr(spike.httpx, "AsyncClient", _FakeChatClient)
    content, _ = asyncio.run(spike.infer("Can I collect Salt Roads tomorrow?", "unit-test-token"))
    records = _inference_records(sink)
    assert len(records) == 1
    record = records[0]
    assert content == "\nSTOCK"
    assert record["provider_response"] == UNIT_PROVIDER_BODY
    assert record["redacted_fields"] == []
    details = record["provider_response"]["usage"]["completion_tokens_details"]
    assert details == {"reasoning_tokens": 113}
    message = record["provider_response"]["choices"][0]["message"]
    assert message["reasoning_content"].startswith("The customer asks")


def test_an_explicit_redaction_is_dropped_and_named(monkeypatch, tmp_path):
    sink = tmp_path / "slice12-unit-infer-TEST.jsonl"
    monkeypatch.setattr(spike, "EVIDENCE_SINK", sink)
    monkeypatch.setattr(spike, "REDACTED_RESPONSE_FIELDS", ("system_fingerprint",))
    monkeypatch.setattr(spike.httpx, "AsyncClient", _FakeChatClient)
    asyncio.run(spike.infer("hello", "unit-test-token"))
    record = _inference_records(sink)[0]
    assert record["redacted_fields"] == ["system_fingerprint"]
    assert "system_fingerprint" not in record["provider_response"]
    expected = {key: value for key, value in UNIT_PROVIDER_BODY.items()
                if key != "system_fingerprint"}
    assert record["provider_response"] == expected


def test_outage_with_recorded_failures_and_no_business_write_passes():
    verdict = spike.classify_outage(
        transport_failure="ConnectError", provider_failure="400",
        business_effect_writes=0,
    )
    assert verdict == spike.OUTAGE_RECORDED


def test_outage_with_a_missing_transport_failure_is_unproven():
    verdict = spike.classify_outage(
        transport_failure=None, provider_failure="400", business_effect_writes=0,
    )
    assert verdict == spike.OUTAGE_UNPROVEN


def test_outage_with_a_missing_provider_failure_is_unproven():
    verdict = spike.classify_outage(
        transport_failure="ConnectError", provider_failure=None,
        business_effect_writes=0,
    )
    assert verdict == spike.OUTAGE_UNPROVEN


def test_outage_that_wrote_a_business_effect_is_an_escape():
    verdict = spike.classify_outage(
        transport_failure="ConnectError", provider_failure="400",
        business_effect_writes=1,
    )
    assert verdict == spike.OUTAGE_ESCAPED


def test_declared_tool_with_bounded_output_is_no_escape():
    verdict = spike.classify_escape(
        declared_tool="none", output_tokens=12, secret_leak=False,
    )
    assert verdict == spike.ESCAPE_NONE_OBSERVED


def test_undeclared_tool_is_an_escape():
    verdict = spike.classify_escape(
        declared_tool="admin_delete", output_tokens=12, secret_leak=False,
    )
    assert verdict == spike.ESCAPE_OBSERVED


def test_output_over_the_ceiling_is_an_escape():
    verdict = spike.classify_escape(
        declared_tool="stock_lookup",
        output_tokens=spike.MAX_OUTPUT_TOKENS + 1,
        secret_leak=False,
    )
    assert verdict == spike.ESCAPE_OBSERVED


def test_secret_on_the_captured_surface_is_an_escape():
    verdict = spike.classify_escape(
        declared_tool="none", output_tokens=12, secret_leak=True,
    )
    assert verdict == spike.ESCAPE_OBSERVED


def test_missing_escape_evidence_is_unproven():
    verdict = spike.classify_escape(
        declared_tool=None, output_tokens=None, secret_leak=False,
    )
    assert verdict == spike.ESCAPE_UNPROVEN


def test_rejected_prior_operation_reuse_passes():
    verdict = spike.classify_reuse(
        prior_operation_id="01a0ddde-0683-7391-81a1-af2cc5d2bbfe",
        rejected_status=404, succeeded=False,
    )
    assert verdict == spike.REUSE_REJECTED


def test_successful_prior_operation_reuse_is_an_escape():
    verdict = spike.classify_reuse(
        prior_operation_id="01a0ddde-0683-7391-81a1-af2cc5d2bbfe",
        rejected_status=None, succeeded=True,
    )
    assert verdict == spike.REUSE_ESCAPED


def test_no_prior_operation_record_is_unproven():
    verdict = spike.classify_reuse(
        prior_operation_id=None, rejected_status=None, succeeded=False,
    )
    assert verdict == spike.REUSE_NO_PRIOR


def test_non_client_rejection_is_unproven_rather_than_a_pass():
    verdict = spike.classify_reuse(
        prior_operation_id="01a0ddde-0683-7391-81a1-af2cc5d2bbfe",
        rejected_status=503, succeeded=False,
    )
    assert verdict == spike.REUSE_INCONCLUSIVE


def test_newest_prior_operation_id_reads_the_last_stamped_record():
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        (directory / "slice12-pair-20260926T131827Z.jsonl").write_text(
            json.dumps({"probe": "pair_run", "operation_id": "op-old"}) + "\n",
            encoding="utf-8",
        )
        (directory / "slice12-controls-20260926T132140Z.jsonl").write_text(
            json.dumps({"probe": "access_egress_spawn", "operation_id": "op-new"}) + "\n",
            encoding="utf-8",
        )
        assert spike.newest_prior_operation_id(directory, exclude=None) == "op-new"


def test_newest_prior_operation_id_skips_the_current_sink():
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        current = directory / "slice12-reuse-20260926T140000Z.jsonl"
        current.write_text(
            json.dumps({"probe": "run_start", "operation_id": "op-current"}) + "\n",
            encoding="utf-8",
        )
        (directory / "slice12-pair-20260926T131827Z.jsonl").write_text(
            json.dumps({"probe": "pair_run", "operation_id": "op-prior"}) + "\n",
            encoding="utf-8",
        )
        assert spike.newest_prior_operation_id(directory, exclude=current) == "op-prior"


def test_no_prior_evidence_file_yields_no_operation_id():
    with tempfile.TemporaryDirectory() as tmp:
        assert spike.newest_prior_operation_id(Path(tmp), exclude=None) is None


def test_trial_reservation_scales_with_the_trial_count():
    per_trial = spike.trial_reservation_usd(1)
    assert per_trial > 0
    assert abs(spike.trial_reservation_usd(6) - 6 * per_trial) < 1e-12


def test_budget_allows_a_total_at_the_cap_and_refuses_above_it():
    assert spike.budget_allows_total(spike.MAX_SPIKE_USD - 0.01, 0.01) is True
    assert spike.budget_allows_total(spike.MAX_SPIKE_USD - 0.01, 0.02) is False


def test_six_completed_trials_are_feasible():
    verdict = spike.classify_trials(planned=6, completed=6, budget_ok=True)
    assert verdict == spike.TRIALS_FEASIBLE


def test_a_short_trial_run_is_incomplete():
    verdict = spike.classify_trials(planned=6, completed=5, budget_ok=True)
    assert verdict == spike.TRIALS_INCOMPLETE


def test_a_zero_trial_plan_is_incomplete():
    verdict = spike.classify_trials(planned=0, completed=0, budget_ok=True)
    assert verdict == spike.TRIALS_INCOMPLETE


def test_a_budget_refusal_outranks_the_completion_count():
    verdict = spike.classify_trials(planned=6, completed=6, budget_ok=False)
    assert verdict == spike.TRIALS_OVER_BUDGET


def test_judge_route_ready_only_when_every_requirement_is_present():
    checks = {name: True for name in spike.JUDGE_ROUTE_REQUIREMENTS}
    assert spike.classify_judge_route(checks) == spike.JUDGE_ROUTE_READY


def test_judge_route_with_a_failed_requirement_is_incomplete():
    checks = {name: True for name in spike.JUDGE_ROUTE_REQUIREMENTS}
    checks["evidence_dir"] = False
    assert spike.classify_judge_route(checks) == spike.JUDGE_ROUTE_INCOMPLETE


def test_judge_route_with_an_unreported_requirement_is_incomplete():
    checks = {name: True for name in spike.JUDGE_ROUTE_REQUIREMENTS}
    del checks["verifier_suite"]
    assert spike.classify_judge_route(checks) == spike.JUDGE_ROUTE_INCOMPLETE


def _judge_ready_root(root: Path) -> None:
    (root / ".venv313" / "Scripts").mkdir(parents=True)
    (root / ".venv313" / "Scripts" / "python.exe").write_bytes(b"")
    (root / "demos").mkdir()
    (root / "demos" / "gateway_spike.py").write_bytes(b"")
    (root / "tests" / "spike").mkdir(parents=True)
    (root / "tests" / "spike" / "test_spike_verifiers.py").write_bytes(b"")
    evidence = root / "docs" / "plans" / "shiftwork" / "evidence"
    evidence.mkdir(parents=True)
    (evidence / "slice12-live-2026-09-26.jsonl").write_text("{}\n", encoding="utf-8")


def test_judge_route_collection_finds_every_requirement_when_present(tmp_path):
    root = tmp_path / "repo"
    _judge_ready_root(root)
    checks = spike.collect_judge_route_checks(root)
    assert checks["venv_python"] is True
    assert checks["evidence_dir"] is True
    assert checks["evidence_records"] is True
    assert checks["spike_entry_point"] is True
    assert checks["verifier_suite"] is True


def test_judge_route_collection_reports_every_requirement_for_a_bare_directory(tmp_path):
    checks = spike.collect_judge_route_checks(tmp_path)
    assert set(checks) == set(spike.JUDGE_ROUTE_REQUIREMENTS)
    assert checks["venv_python"] is False
    assert checks["evidence_dir"] is False
    assert checks["evidence_records"] is False
    assert checks["spike_entry_point"] is False
    assert checks["verifier_suite"] is False


def test_judge_route_probe_archives_its_checks_and_verdict(tmp_path):
    root = tmp_path / "repo"
    _judge_ready_root(root)
    evidence = tmp_path / "run-evidence"
    original = spike.EVIDENCE_SINK
    try:
        code = spike.judge_route_probe(root, evidence_dir=evidence)
    finally:
        spike.EVIDENCE_SINK = original
    assert code == 0
    files = sorted(evidence.glob("slice12-judge-*.jsonl"))
    assert len(files) == 1
    record = json.loads(files[0].read_text(encoding="utf-8").splitlines()[0])
    assert record["probe"] == "judge_route"
    assert record["verdict"] == spike.JUDGE_ROUTE_READY
    assert record["checks"] == {name: True for name in spike.JUDGE_ROUTE_REQUIREMENTS}
    assert record["source_sha256"] == spike.SOURCE_SHA256
    assert "T" in record["recorded_utc"]
    assert record["environment_names"] == ["NEBIUS_API_KEY", "NEBIUS_PROJECT_ID"]
    assert any("mutation_proofs_spike" in command for command in record["offline_commands"])
    assert any("--phase reset" in command for command in record["live_commands"])


def test_judge_route_probe_fails_closed_and_archives_an_incomplete_verdict(tmp_path):
    root = tmp_path / "bare"
    root.mkdir()
    evidence = tmp_path / "run-evidence"
    original = spike.EVIDENCE_SINK
    try:
        code = spike.judge_route_probe(root, evidence_dir=evidence)
    finally:
        spike.EVIDENCE_SINK = original
    assert code == 2
    files = sorted(evidence.glob("slice12-judge-*.jsonl"))
    assert len(files) == 1
    record = json.loads(files[0].read_text(encoding="utf-8").splitlines()[0])
    assert record["verdict"] == spike.JUDGE_ROUTE_INCOMPLETE
