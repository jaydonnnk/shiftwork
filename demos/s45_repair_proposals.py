"""Prepare new, unapproved learner-style repair examples without executing them.

The stopped A/B pair is retained separately in s45_repairs.py. These sources
are operator-authored proposals, not learner work or measured repair evidence.
"""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import textwrap

from shiftwork import config


PROMPT_REPAIR = '''
def ask_for_plan(text):
    prompt = (
        'Return JSON only: {"plan":[{"task_type":"...","tool_name":"..."}]}. '
        'Use exactly the tasks the customer requests, each once. No extra tasks. '
        'For collection, check collection first, then the conditional alternative. '
        'A conditional alternative is still a plan step; execution decides whether it applies. '
        'Collection uses public_availability_lookup; alternative uses public_catalog_search; '
        'price uses public_price_lookup; stock uses public_stock_lookup. '
        'Do not add stock merely because collection needs a stock check internally. '
        'No explanation, reasoning or code fences. Customer request: ' + text
    )
    ordinal = next_request_ordinal()
    try:
        reply = gateway_call('/infer', {'request_ordinal': ordinal, 'input_text': prompt, 'enable_thinking': False})
    except (OSError, ValueError, RuntimeError):
        return None, 'GATEWAY_UNAVAILABLE'
    return reply.get('plan'), reply.get('plan_failure')
'''

SCHEMA_REPAIR = '''
PLAN_TOOLS = {
    'collection': ('public_availability_lookup', 'public_record_lookup'),
    'alternative': ('public_catalog_search',),
    'price': ('public_price_lookup', 'public_record_lookup'),
    'stock': ('public_stock_lookup', 'public_record_lookup'),
}
PLAN_SCHEMA = {
    'type': 'object', 'required': ['plan'], 'additionalProperties': False,
    'properties': {'plan': {'type': 'array', 'minItems': 1, 'maxItems': 4,
        'items': {'oneOf': [
            {'type': 'object', 'required': ['task_type', 'tool_name'], 'additionalProperties': False,
             'properties': {'task_type': {'const': task}, 'tool_name': {'enum': list(tools)}}}
            for task, tools in PLAN_TOOLS.items()
        ]}}},
}

def validate_plan(plan):
    if not isinstance(plan, list) or not 1 <= len(plan) <= 4:
        return False
    seen = set()
    for step in plan:
        if not isinstance(step, dict) or set(step) != {'task_type', 'tool_name'}:
            return False
        task, tool = step['task_type'], step['tool_name']
        if not isinstance(task, str) or not isinstance(tool, str):
            return False
        if task not in PLAN_TOOLS or tool not in PLAN_TOOLS[task] or task in seen:
            return False
        if task == 'collection' and 'alternative' in seen:
            return False
        seen.add(task)
    return True

def ask_for_plan(text):
    prompt = (
        'Return only JSON matching this schema: ' + json.dumps(PLAN_SCHEMA, separators=(',', ':'))
        + '. Task meanings: ' + json.dumps(TASK_VOCABULARY, separators=(',', ':'))
        + '. Include each requested task once and no unrequested tasks. '
        'A conditional alternative remains in the plan, after collection. '
        'Collection already checks stock internally; this does not request a separate stock task. '
        'No prose or code fences. Customer request: ' + text
    )
    ordinal = next_request_ordinal()
    try:
        reply = gateway_call('/infer', {'request_ordinal': ordinal, 'input_text': prompt, 'enable_thinking': False})
    except (OSError, ValueError, RuntimeError):
        return None, 'GATEWAY_UNAVAILABLE'
    if reply.get('plan_failure') is not None:
        return None, reply['plan_failure']
    plan = reply.get('plan')
    if not validate_plan(plan):
        return None, 'LEARNER_SCHEMA_INVALID'
    return plan, None
'''


def candidate_files(label):
    replacements = {'prompt': PROMPT_REPAIR, 'schema': SCHEMA_REPAIR}
    replacement = textwrap.dedent(replacements[label]).strip() + '\n'
    starter = config.PACKAGE_DIR / 'fixtures/artifacts/bookshop/task_plan_starter_service.py'
    source = starter.read_text()
    node = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'ask_for_plan')
    lines = source.splitlines(keepends=True)
    source = ''.join(lines[:node.lineno - 1]) + replacement + ''.join(lines[node.end_lineno:])
    source = f'# UNAPPROVED operator-authored S45 {label} proposal. Not learner work or learning evidence.\n' + source
    compile(source, f's45-proposed-{label}', 'exec')
    return {'service.py': source}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    manifest = {'state': 'PROPOSED_UNAPPROVED', 'authorship': 'operator-authored examples of learner-editable repairs',
        'effectiveness': 'unmeasured', 'model': 'nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B',
        'shared_settings': {'enable_thinking': False, 'temperature': 0, 'max_tokens': 1024,
            'user_messages': 1, 'calls_per_request': 1, 'retries': 0, 'input_bytes': 8192,
            'gateway_deadline_s': 20, 'workspace_deadline_s': 45}, 'candidates': []}
    for label in ('prompt', 'schema'):
        source = candidate_files(label)['service.py']
        folder = args.out / label
        folder.mkdir()
        (folder / 'service.py').write_text(source)
        manifest['candidates'].append({'label': label, 'source_sha256': hashlib.sha256(source.encode()).hexdigest()})
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
