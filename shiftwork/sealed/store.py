"""Sealed-case loader (program design S3.3/S3.4).

Slice 4 loads the complete first-family inventory (``stale_information``, six
variants) as a ``SealedCaseSet``. ``expected`` blocks are sealed: only the
evaluator reads them, and results expose an opaque ``expected_ref`` instead of
any value. A case file or individual case declaring an unknown schema version
raises ``UnsupportedSealedSchema`` rather than being skipped, and a case whose
``request_ordinals`` list is empty or duplicated raises ``InvalidSealedCase``
rather than silently never scoring (program design S6 test 15). These cases are
agent-drafted and require user review before they are treated as sealed
acceptance authority.

``load_drawn_cases`` is the approved run-scoped accessor. Variant rotation does
not exist until Slice 7, so every run currently evaluates the full family
inventory, matched to executed outputs by request ordinal; Slice 7 replaces the
body with exactly the persisted per-run draws.
"""

import json

from shiftwork import config
from shiftwork.domain.errors import InvalidSealedCase, UnsupportedSealedSchema
from shiftwork.evaluator.evaluator import SealedCase, SealedCaseSet

STALE_INFORMATION = "stale_information"

_FAMILY_FILES = {STALE_INFORMATION: "bookshop_stale_information.json"}
SUPPORTED_SCHEMA_VERSIONS = (1,)


def load_family(family: str) -> SealedCaseSet:
    path = config.SEALED_CASES_DIR / _FAMILY_FILES[family]
    data = json.loads(path.read_text(encoding="utf-8"))
    file_version = data.get("schema_version")
    if file_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise UnsupportedSealedSchema(
            f"sealed family {family!r} declares unsupported file schema_version {file_version!r}"
        )
    cases = []
    for raw in data["cases"]:
        version = raw.get("schema_version")
        if version not in SUPPORTED_SCHEMA_VERSIONS:
            raise UnsupportedSealedSchema(
                f"sealed case {raw.get('id')!r} declares unsupported schema_version {version!r}"
            )
        ordinals = raw.get("request_ordinals")
        if (
            not isinstance(ordinals, list)
            or not ordinals
            or any(isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1 for ordinal in ordinals)
            or len(set(ordinals)) != len(ordinals)
        ):
            raise InvalidSealedCase(
                f"sealed case {raw.get('id')!r} needs a non-empty, duplicate-free list of "
                f"positive request ordinals; got {ordinals!r}"
            )
        cases.append(SealedCase.model_validate(raw))
    return SealedCaseSet(cases=tuple(cases))


def load_drawn_cases(run_id: str) -> SealedCaseSet:
    return load_family(STALE_INFORMATION)
