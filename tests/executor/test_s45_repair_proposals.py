"""Unapproved proposals, checked with authored replies, never live model output."""

import ast
import json

import pytest

from demos import s43_task_plan as harness
from demos.s45_repair_proposals import candidate_files
from shiftwork.gateway.protocol import REASONING_OFF_MODEL


def source_namespace(label):
    namespace = {'__name__': 'operator_authored_proposal'}
    exec(compile(candidate_files(label)['service.py'], label, 'exec'), namespace)
    return namespace


@pytest.mark.parametrize('label', ['prompt', 'schema'])
def test_proposals_keep_every_starter_behavior_outside_plan_request(label):
    def unchanged(source):
        tree = ast.parse(source)
        tree.body = [node for node in tree.body if not (
            isinstance(node, ast.FunctionDef) and node.name in ('ask_for_plan', 'validate_plan')
            or isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in ('PLAN_SCHEMA', 'PLAN_TOOLS') for target in node.targets))]
        return ast.dump(tree, include_attributes=False)
    assert unchanged(candidate_files(label)['service.py']) == unchanged(harness.STARTER.read_text()), 'proposal must not change task completion, tools or service response logic'


@pytest.mark.parametrize('label', ['prompt', 'schema'])
def test_proposals_make_one_call_with_same_reasoning_setting_and_preserve_plan(label):
    ns = source_namespace(label)
    plan = [{'task_type': 'collection', 'tool_name': 'public_availability_lookup'}]
    calls = []
    ns['gateway_call'] = lambda path, payload: calls.append((path, payload)) or {'plan': plan, 'plan_failure': None}
    assert ns['ask_for_plan']('Public customer wording') == (plan, None), 'valid provider plan must be returned without repair'
    assert len(calls) == 1 and calls[0][0] == '/infer', 'exactly one model call, no retry or tool substitute'
    assert set(calls[0][1]) == {'request_ordinal', 'input_text', 'enable_thinking'} and calls[0][1]['enable_thinking'] is False
    assert calls[0][1]['input_text'].endswith('Public customer wording') and len(calls[0][1]['input_text'].encode()) < 8192


@pytest.mark.parametrize('plan', [None, [], 'plan', [{}], [{'task_type': [], 'tool_name': 'public_catalog_search'}],
    [{'task_type': 'unknown', 'tool_name': 'public_catalog_search'}],
    [{'task_type': 'collection', 'tool_name': 'public_price_lookup'}],
    [{'task_type': 'collection', 'tool_name': 'public_availability_lookup', 'extra': 'unapproved'}],
    [{'task_type': 'collection', 'tool_name': 'public_availability_lookup'}] * 2,
    [{'task_type': 'alternative', 'tool_name': 'public_catalog_search'}, {'task_type': 'collection', 'tool_name': 'public_availability_lookup'}],
    [{'task_type': 'price', 'tool_name': 'public_price_lookup'}] * 5])
def test_schema_repair_refuses_invalid_plan_without_completing_or_retrying(plan):
    ns = source_namespace('schema')
    calls = []
    ns['gateway_call'] = lambda path, payload: calls.append((path, payload)) or {'plan': plan, 'plan_failure': None}
    assert ns['ask_for_plan']('Public request') == (None, 'LEARNER_SCHEMA_INVALID'), 'invalid plan must be rejected without rescue'
    assert len(calls) == 1


@pytest.mark.parametrize('label', ['prompt', 'schema'])
@pytest.mark.parametrize('reply, useful', [(harness.CASES[0][1], True), (harness.CASES[1][1], False), ('invalid JSON', False)])
def test_authored_reply_runs_preserve_useful_completion_and_no_rescue(label, reply, useful, monkeypatch):
    original = harness.InferencePolicy

    def common_policy(**kwargs):
        return original(**{**kwargs, 'model': REASONING_OFF_MODEL, 'allow_reasoning_off': True})

    monkeypatch.setattr(harness, 'InferencePolicy', common_policy)
    result = harness.run_starter_offline(reply, starter_source=candidate_files(label)['service.py'])
    assert len(result['responses']) == 1 and result['responses'][0]['status'] == 200, 'the public service must actually return a response'
    body = result['responses'][0]['body']
    assert harness.assess(body)[1] is useful, 'missing or invalid plans cannot become useful completion'
    if not useful:
        assert 'alternative' not in [row['task_id'] for row in json.loads(body)['task_results']], 'a model-omitted task must remain omitted'
