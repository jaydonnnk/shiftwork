"""Only the run's own trusted public-status record can override combined state."""

from types import SimpleNamespace as NS

import pytest

from shiftwork import comparison_flow
from shiftwork.domain.models import RunState
from shiftwork.store import repo
from shiftwork import orchestrator


@pytest.mark.parametrize("fault", ["identity", "source", "false", "integer", "string"])
def test_public_phase_status_rejects_untrusted_or_nonboolean_success(monkeypatch, fault):
    run = NS(id="test-run", state=RunState.FAILED)
    observation = NS(id="test-run-public-status", public_payload_json={
        "source": "controller_verified", "public_repetition_complete": True})
    if fault == "identity": observation.id = "unbound-observation"
    if fault == "source": observation.public_payload_json["source"] = "service_reported"
    if fault == "false": observation.public_payload_json["public_repetition_complete"] = False
    if fault == "integer": observation.public_payload_json["public_repetition_complete"] = 1
    if fault == "string": observation.public_payload_json["public_repetition_complete"] = "true"
    monkeypatch.setattr(repo, "list_observations", lambda conn, run_id: [observation])
    assert comparison_flow._public_repetition_state(None, run) == "FAILED", (
        "only an owned controller record with boolean true proves public completion")


def test_owned_public_success_survives_a_later_combined_failure(monkeypatch):
    run = NS(id="test-run", state=RunState.FAILED)
    observation = NS(id="test-run-public-status", public_payload_json={
        "source": "controller_verified", "public_repetition_complete": True})
    monkeypatch.setattr(repo, "list_observations", lambda conn, run_id: [observation])
    assert comparison_flow._public_repetition_state(None, run) == "COMPLETE", (
        "a later failure cannot erase retained public completion")


def test_comparison_dispatcher_refuses_recorded_without_local_fallback():
    with pytest.raises(orchestrator.LifecycleError, match="no safe executor"):
        comparison_flow._comparison_adapter(NS(adapter="recorded"), None, None, None)
