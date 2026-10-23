"""Gate 3 obligation 62 (S43): the task-plan starter has no rescue code.

The starter runs as a subprocess against the real trusted driver handler and
the real plan-mode gateway, with labelled operator-authored test replies in
place of the provider. Its answers are assessed by the deterministic evaluator.
"""

import json

from demos import s43_task_plan as harness
from shiftwork import config

FULL = harness.CASES[0][1]
OMITS_ALTERNATIVE = harness.CASES[1][1]
UNLISTED_TOOL = harness.CASES[2][1]


def _only_answer(reply, **kwargs):
    outcome = harness.run_starter_offline(reply, **kwargs)
    assert len(outcome["responses"]) == 1 and outcome["responses"][0]["status"] == 200
    return outcome, outcome["responses"][0]["body"]


def _by_task(assessments):
    return {item.task_id: item for item in assessments}


def test_full_plan_completes_every_required_task():
    # The control: the same harness and starter can pass, so a failure below is
    # caused by the plan, not by the harness.
    _, body = _only_answer(FULL)
    assessments, useful = harness.assess(body)
    assert useful is True
    assert {item.outcome.value for item in assessments} == {"USEFUL_COMPLETION"}


def test_starter_omitting_a_required_task_fails_the_visible_check():
    outcome, body = _only_answer(OMITS_ALTERNATIVE)
    assert outcome["gateway_codes"] == [None]
    assert [r["task_id"] for r in json.loads(body)["task_results"]] == ["collection", "price"]
    assessments, useful = harness.assess(body)
    alternative = _by_task(assessments)["alternative"]
    assert alternative.mandatory_pass is False
    assert alternative.outcome.value == "MISSING_OUTPUT"
    assert [code.value for code in alternative.reason_codes] == ["REQUIRED_TASK_MISSING"]
    assert useful is False


def test_plan_failure_yields_no_task_results():
    outcome, body = _only_answer(UNLISTED_TOOL)
    assert outcome["gateway_codes"] == ["TOOL_NOT_ALLOWED"]
    assert json.loads(body)["task_results"] == []
    assessments, useful = harness.assess(body)
    assert useful is False
    assert _by_task(assessments)["collection"].reason_codes[0].value == "REQUIRED_TASK_MISSING"


def test_a_tool_that_cannot_do_the_task_leaves_it_out():
    reply = harness._plan(("collection", "public_price_lookup"), ("alternative", "public_catalog_search"))
    _, body = _only_answer(reply)
    assert [r["task_id"] for r in json.loads(body)["task_results"]] == ["alternative"]
    assert harness.assess(body)[1] is False


def test_starter_reads_records_only_through_the_driver():
    # Every claimed record id must appear in a driver tool_result event, so the
    # answer comes from tools the plan used, not from reading shop.json.
    outcome, body = _only_answer(FULL)
    served = {rid for event in outcome["events"] if event["kind"] == "tool_result"
              for rid in event.get("record_ids", [])}
    claimed = set(json.loads(body)["evidence_refs"])
    assert claimed and claimed <= served


def test_starter_source_is_the_mapped_v2_starter():
    mapped = config.bellwether_starter_files("fixtures/mission/bookshop_pivot_v2.json")["service.py"]
    assert mapped == harness.STARTER and mapped.name == "task_plan_starter_service.py"
