"""Allowlisted provider text for public evidence views, never assessment."""

import base64
import json

from shiftwork.domain.models import ObservationKind
from shiftwork.gateway.redaction import assert_public_safe


def public_observation(observation, *, public_count: int, needles: tuple[str, ...]):
    if not 1 <= observation.request_ordinal <= public_count:
        return None
    payload = dict(observation.public_payload_json)
    if observation.kind is ObservationKind.INFERENCE_RESULT:
        status = "not retained"
        try:
            prefix = "data:application/json;base64,"
            if not observation.raw_payload_ref.startswith(prefix) or len(observation.raw_payload_ref) > 400000:
                raise ValueError("unavailable retained reply")
            raw = json.loads(base64.b64decode(observation.raw_payload_ref[len(prefix):], validate=True))
            text = raw["provider_response"]["choices"][0]["message"].get("reasoning")
            if isinstance(text, str):
                if len(text) > 65536:
                    status = "exceeds public text limit"
                else:
                    try:
                        assert_public_safe({"reasoning_text": text}, needles)
                    except ValueError:
                        status = "withheld by public safety scan"
                    else:
                        payload["reasoning_text"] = text
                        payload["reasoning_characters"] = len(text)
                        status = "provider-returned"
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            pass
        payload["reasoning_status"] = status
    return {"kind": observation.kind.value, "public_payload_json": payload}
