"""Offline guards for the Slice 12 pair verifier, absence controls and record stamps.

These checks exist because of the F3 and F4 review findings. F3: the capture
verifier must download the checkpoint file and compare a digest, never branch on
a stdout marker. F4: every absence assertion needs a positive control that
proves the detection code can fire, and an unexercised control must be recorded
as unproven rather than passed. Each classifier here is a pure function, so the
pair comparison can be judged without a Sandbox. Nothing in this module contacts
the API or needs credentials; the live clauses stay unrun.

Each test is written to fail when its own branch of a classifier is mutated.
"""

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
