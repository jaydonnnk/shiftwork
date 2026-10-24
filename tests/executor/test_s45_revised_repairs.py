"""Authored offline controls prove instructions and execution, not model quality."""

import ast
import json

import pytest

from demos import s43_task_plan as harness
from demos.s45_revised_repairs import candidate_files
from shiftwork import config
from shiftwork.domain import task_contract
from shiftwork.gateway.protocol import REASONING_OFF_MODEL


def source_namespace(label):
    namespace = {'__name__': 'operator_authored_revision'}
    exec(compile(candidate_files(label)['service.py'], label, 'exec'), namespace)
    return namespace


@pytest.mark.parametrize('label', ['prompt', 'schema'])
def test_revised_prompt_enumerates_exact_task_names_and_conditional_alternative(label):
    ns = source_namespace(label)
    calls = []
    plan = [{'task_type': 'alternative', 'tool_name': 'public_catalog_search'}]
    ns['gateway_call'] = lambda path, payload: calls.append((path, payload)) or {'plan': plan, 'plan_failure': None}
    assert ns['ask_for_plan']('Public customer wording') == (plan, None)
    prompt = calls[0][1]['input_text']
    assert 'Allowed task_type strings: collection, alternative, price, stock.' in prompt, 'exact task vocabulary must be explicit in both revised prompts'
    assert 'Use alternative, never conditional_alternative.' in prompt, 'a conditional alternative must use the frozen alternative name'
    assert '"task_type":"alternative"' in prompt, 'both prompts must show the literal alternative plan key'


@pytest.mark.parametrize('label', ['prompt', 'schema'])
def test_revised_prompt_distinguishes_requested_tasks_from_internal_lookups(label):
    ns = source_namespace(label)
    calls = []
    ns['gateway_call'] = lambda path, payload: calls.append(payload) or {'plan': [{'task_type': 'price', 'tool_name': 'public_price_lookup'}], 'plan_failure': None}
    ns['ask_for_plan']('Public customer wording')
    prompt = calls[0]['input_text']
    assert 'A price-only question does not request collection or stock.' in prompt, 'price questions must not invent collection or stock tasks'
    assert 'A stock-only question does not request collection.' in prompt, 'stock questions must not invent collection tasks'
    assert 'Collection can use stock internally without a separate stock task.' in prompt, 'tool dependencies must not become unrequested response tasks'
    assert 'Include price only when asked, not merely because an alternative has a price limit.' in prompt, 'an alternative price limit is not a separate price request'


@pytest.mark.parametrize('label', ['prompt', 'schema'])
def test_revised_sources_preserve_all_starter_behavior_outside_plan_request(label):
    def unchanged(source):
        tree = ast.parse(source)
        tree.body = [node for node in tree.body if not (
            isinstance(node, ast.FunctionDef) and node.name in ('ask_for_plan', 'validate_plan')
            or isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in ('PLAN_SCHEMA', 'PLAN_TOOLS') for target in node.targets))]
        return ast.dump(tree, include_attributes=False)
    assert unchanged(candidate_files(label)['service.py']) == unchanged(harness.STARTER.read_text()), 'revised examples must not add task completion or hidden answer repair'


@pytest.mark.parametrize('label', ['prompt', 'schema'])
def test_revised_sources_keep_exactly_one_call_and_return_valid_plan_unchanged(label):
    ns = source_namespace(label)
    plan = [{'task_type': 'collection', 'tool_name': 'public_availability_lookup'}, {'task_type': 'alternative', 'tool_name': 'public_catalog_search'}]
    calls = []
    ns['gateway_call'] = lambda path, payload: calls.append((path, payload)) or {'plan': plan, 'plan_failure': None}
    assert ns['ask_for_plan']('Public wording') == (plan, None)
    assert len(calls) == 1 and calls[0][0] == '/infer'
    assert set(calls[0][1]) == {'request_ordinal', 'input_text', 'enable_thinking'} and calls[0][1]['enable_thinking'] is False
    assert calls[0][1]['input_text'].endswith('Public wording') and len(calls[0][1]['input_text'].encode()) < 8192


@pytest.mark.parametrize('label', ['prompt', 'schema'])
@pytest.mark.parametrize('case', ['full', 'unknown_task', 'missing_alternative', 'extra_stock'])
def test_revised_authored_plans_still_face_independent_assessment(label, case, monkeypatch):
    full = json.loads(harness.CASES[0][1])['plan']
    plans = {'full': full,
        'unknown_task': [dict(step, task_type='conditional_alternative') if step['task_type'] == 'alternative' else step for step in full],
        'missing_alternative': [step for step in full if step['task_type'] != 'alternative'],
        'extra_stock': full + [{'task_type': 'stock', 'tool_name': 'public_stock_lookup'}]}
    original = harness.InferencePolicy
    monkeypatch.setattr(harness, 'InferencePolicy', lambda **kwargs: original(**{**kwargs, 'model': REASONING_OFF_MODEL, 'allow_reasoning_off': True}))
    result = harness.run_starter_offline(json.dumps({'plan': plans[case]}), starter_source=candidate_files(label)['service.py'])
    assert len(result['responses']) == 1 and result['responses'][0]['status'] == 200
    body = result['responses'][0]['body']
    assert harness.assess(body)[1] is (case == 'full'), 'unknown, omitted or extra tasks cannot become successful completion'
    task_ids = [row['task_id'] for row in json.loads(body)['task_results']]
    if case == 'extra_stock':
        assert 'stock' in task_ids, 'the candidate must not silently remove an extra model task to improve its result'
    if case == 'missing_alternative':
        assert 'alternative' not in task_ids, 'the candidate must not complete a model-omitted task'
    if case == 'unknown_task':
        assert result['gateway_codes'] == ['TASK_TYPE_UNKNOWN'], 'invalid task vocabulary must remain a gateway plan failure'


@pytest.mark.parametrize('label', ['prompt', 'schema'])
@pytest.mark.parametrize('extra_collection', [False, True])
def test_price_and_stock_request_rejects_extra_collection_without_silent_removal(label, extra_collection, monkeypatch, tmp_path):
    public_dir = config.PIVOT_COMPARE_REQUEST_DIR
    row = json.loads((public_dir / 'bookshop_compare_pair_02.jsonl').read_text().splitlines()[1])
    request_file = tmp_path / 'public_request.jsonl'
    request_file.write_text(json.dumps(row) + '\n')
    monkeypatch.setattr(config, 'PIVOT_INCIDENT_REQUESTS', request_file)
    spec = task_contract.CustomerRequestSpec.model_validate(json.loads((public_dir / 'bookshop_compare_pair_02_specs.json').read_text())[1])
    plan = [{'task_type': 'price', 'tool_name': 'public_price_lookup'}, {'task_type': 'stock', 'tool_name': 'public_stock_lookup'}]
    if extra_collection:
        plan.append({'task_type': 'collection', 'tool_name': 'public_availability_lookup'})
    original = harness.InferencePolicy
    monkeypatch.setattr(harness, 'InferencePolicy', lambda **kwargs: original(**{**kwargs, 'model': REASONING_OFF_MODEL, 'allow_reasoning_off': True}))
    result = harness.run_starter_offline(json.dumps({'plan': plan}), starter_source=candidate_files(label)['service.py'])
    assert len(result['responses']) == 1 and result['responses'][0]['status'] == 200
    body = result['responses'][0]['body'].encode()
    if extra_collection:
        assert 'collection' in [item['task_id'] for item in json.loads(body)['task_results']], 'an extra model task must remain visible to independent assessment'
        with pytest.raises(task_contract.TaskEnvelopeInvalid, match='unknown task'):
            task_contract.validate_response_envelope(spec, body)
    else:
        parsed = task_contract.validate_response_envelope(spec, body)
        assert [item.task_id for item in parsed.task_results] == ['price', 'stock'], 'the valid price-and-stock control must remain accepted'
