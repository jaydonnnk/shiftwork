"""Sealed-case loader (program design S3.3).

Slice 2 loads ONE sealed case from the checked-in sealed store. The ``expected``
block in each file is sealed: it is read only by the evaluator, which exposes an
opaque ``expected_ref`` and never the value. These cases are agent-drafted and
require user review before they are treated as sealed acceptance authority.
"""

import json

from shiftwork import config
from shiftwork.evaluator.evaluator import SealedCase

THIN_CASE_NAME = "bookshop_stale_information"


def load_sealed_case(name: str) -> SealedCase:
    path = config.SEALED_CASES_DIR / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return SealedCase.model_validate(data)


def load_thin_case() -> SealedCase:
    return load_sealed_case(THIN_CASE_NAME)
