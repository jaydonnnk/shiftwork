"""Provider text is untrusted public evidence, never an evaluator input."""

import base64
import json
from types import SimpleNamespace

import pytest

from shiftwork.domain.models import ObservationKind
from shiftwork.gateway.redaction import serialized_contains


def observation(text, ordinal=1, **message_fields):
    body = {"provider_response": {"choices": [{"message": {
        "reasoning": text, "content": "{}", **message_fields}}]}}
    return SimpleNamespace(kind=ObservationKind.INFERENCE_RESULT, request_ordinal=ordinal,
        public_payload_json={"output_tokens": 1024, "finish_reason": "length"},
        raw_payload_ref="data:application/json;base64," + base64.b64encode(json.dumps(body).encode()).decode())


def test_public_reasoning_is_exact_provider_text_with_character_count():
    from shiftwork.public_evidence import public_observation
    text = "Operator-authored provider-text fixture. <script>untrusted</script>"
    projected = public_observation(observation(text, transport_headers="do not publish this field"),
        public_count=2, needles=())
    payload = projected["public_payload_json"]
    assert payload["reasoning_text"] == text, "show the retained text, never an invented explanation"
    assert payload["reasoning_characters"] == len(text), "character count is not a reasoning-token count"
    assert payload["output_tokens"] == 1024
    assert payload["reasoning_status"] == "provider-returned"
    assert set(payload) == {"output_tokens", "finish_reason", "reasoning_text", "reasoning_characters", "reasoning_status"}, (
        "only the allowlisted provider field may leave raw capture storage")


def test_protected_reasoning_is_never_projected():
    from shiftwork.public_evidence import public_observation
    marker = "distinctive-protected-reasoning-marker"
    source = observation(marker, ordinal=3)
    assert serialized_contains({"public_payload_json": {"reasoning_text": marker}}, marker), (
        "scanner control must detect this marker on the serialized public surface")
    assert public_observation(source, public_count=2, needles=(marker,)) is None, (
        "protected ordinals must be rejected before raw reasoning is decoded")


@pytest.mark.parametrize("form", ["raw", "json-escaped", "forward-slash"])
def test_reasoning_scan_detects_serialized_needles_and_withholds_text(form):
    from shiftwork.public_evidence import public_observation
    needle = r"C:\private\controller\sealed-material"
    text = needle if form == "raw" else json.dumps(needle)[1:-1] if form == "json-escaped" else needle.replace("\\", "/")
    source = {"public_payload_json": {"reasoning_text": text}}
    assert serialized_contains(source, needle), "the scanner must detect each serialized needle form"
    projected = public_observation(observation(text), public_count=2, needles=(needle,))
    assert projected["public_payload_json"]["reasoning_status"] == "withheld by public safety scan", (
        "unsafe provider reasoning must be withheld without breaking the evidence view")
    assert not serialized_contains(projected, needle), "the public projection must contain no unsafe text"


def test_unretained_reasoning_is_unknown_instead_of_empty():
    from shiftwork.public_evidence import public_observation
    source = observation(None)
    projected = public_observation(source, public_count=2, needles=())
    assert projected["public_payload_json"]["reasoning_status"] == "not retained"
    assert "reasoning_characters" not in projected["public_payload_json"]


def test_reasoning_character_cap_refuses_oversized_provider_text():
    from shiftwork.public_evidence import public_observation
    projected = public_observation(observation("x" * 65537), public_count=2, needles=())
    assert projected["public_payload_json"]["reasoning_status"] == "exceeds public text limit", (
        "provider reasoning must stay inside the public text bound")


@pytest.mark.parametrize("fault", ["prefix", "raw-size", "invalid-json", "non-string"])
def test_unusable_raw_reply_stays_unknown(fault):
    from shiftwork.public_evidence import public_observation
    source = observation([] if fault == "non-string" else "public text")
    if fault == "prefix":
        source.raw_payload_ref = "x" * len("data:application/json;base64,") + source.raw_payload_ref.split(",", 1)[1]
    elif fault == "raw-size":
        raw = {"provider_response": {"choices": [{"message": {"reasoning": "public text"}}]}, "unused": "x" * 310000}
        source.raw_payload_ref = "data:application/json;base64," + base64.b64encode(json.dumps(raw).encode()).decode()
    elif fault == "invalid-json":
        source.raw_payload_ref = "data:application/json;base64," + base64.b64encode(b"not JSON").decode()
    projected = public_observation(source, public_count=2, needles=())
    assert projected["public_payload_json"]["reasoning_status"] == "not retained", "unusable raw evidence cannot become an invented reasoning display"
