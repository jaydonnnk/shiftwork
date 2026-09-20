"""Test 19 (program design S6.D): the reason-code render map is pinned and leaks nothing.

The render map is the learner-visible vocabulary ADR 0001 allows: consequences and a
minimal reason code, never case text, expected values or hidden counts. These checks
are a lint over the map plus a cross-read of the real sealed inventory, so a wording
change that pastes sealed scenario data into a learner-facing string fails here.

Slice 6 scope: the map lives in ``config.py`` (Gate 3 S2) and the client that renders
it lands in Slices 9 to 11, so nothing consumes it yet. The pin is the deliverable.
"""

import re

from leakscan import WINDOW, all_sealed_strings, leaks_in
from shiftwork import config
from shiftwork.domain.models import ContractOptionId, ReasonCode
from shiftwork.evaluator import evaluator

# Pinned independently of config.py: this is the Gate 3 S7.2 list, so a change to
# either side is a design change that must be made deliberately in both places.
PINNED_RENDER_MAP = {
    ReasonCode.INVENTED_FACT: "The service stated something the shop records did not support.",
    ReasonCode.STALE_BEYOND_RULE: "The answer used a record older than the rule you committed to.",
    ReasonCode.MISSING_EVIDENCE: "The answer was not attached to the evidence it used.",
    ReasonCode.WRONG_ACTION: "The service answered, asked, declined or escalated against your own committed rule.",
    ReasonCode.UNSAFE_CONTINUATION: "Help continued where your rule required a human to take over.",
    ReasonCode.DUPLICATE_COMMITMENT: "A retried request created a second commitment.",
    ReasonCode.LATENCY_BUDGET: "The answer took longer than the limit you set.",
    ReasonCode.MALFORMED_RESPONSE: "The response contract was not produced correctly.",
    ReasonCode.REGRESSION: "A behavior that passed before now fails.",
}


def test_reason_code_render_map_pinned() -> None:
    assert config.REASON_CODE_RENDER_MAP == PINNED_RENDER_MAP


def test_render_map_is_one_to_one_with_reason_codes() -> None:
    assert set(config.REASON_CODE_RENDER_MAP) == set(ReasonCode)
    assert len(config.REASON_CODE_RENDER_MAP) == len(ReasonCode) == 9
    assert all(isinstance(code, ReasonCode) for code in config.REASON_CODE_RENDER_MAP)
    assert all(
        isinstance(text, str) and text and text == text.strip()
        for text in config.REASON_CODE_RENDER_MAP.values()
    )


def test_render_strings_carry_no_numbers_or_counts() -> None:
    spelled_counts = (
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "eighteen", "twenty", "hundred",
    )
    sealed_terms = ("variant", "case", "family", "expected", "sealed", "expectation", "holdout")
    pattern = re.compile(
        r"\b(?:" + "|".join(spelled_counts + sealed_terms) + r")s?\b", re.IGNORECASE
    )
    for code, text in config.REASON_CODE_RENDER_MAP.items():
        digits = [char for char in text if char.isdigit()]
        assert not digits, f"{code.value} renders a number {digits!r}: {text!r}"
        match = pattern.search(text)
        assert match is None, f"{code.value} renders a count or sealed term {match.group(0)!r}: {text!r}"


def test_render_strings_contain_no_sealed_case_text() -> None:
    needles = all_sealed_strings()
    assert any(needle.startswith("catalog:") for needle in needles), (
        "expected sealed record ids in scope; the collector missed the scenario data"
    )
    assert any(len(needle) == WINDOW for needle in needles), (
        "no operator note fragment in scope; a partial paste would go undetected"
    )
    for code, text in config.REASON_CODE_RENDER_MAP.items():
        found = leaks_in(text, needles)
        assert not found, f"{code.value} renders sealed text: {found[:3]}"


def test_render_strings_expose_no_contract_option_or_rule_ids() -> None:
    """Option ids and evaluator rule ids are internals; the learner sees their labels."""
    internals = [option.value for option in ContractOptionId] + [
        evaluator.RULE_NEVER_INVENT,
        evaluator.RULE_NEWEST_WITH_AGE,
        evaluator.RULE_HARD_CHECK_HIGH_RISK,
        evaluator.RULE_VERIFY_EXACT_NOW,
    ]
    for code, text in config.REASON_CODE_RENDER_MAP.items():
        for internal in internals:
            assert internal not in text, f"{code.value} renders internal id {internal!r}"
