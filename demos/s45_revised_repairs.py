"""Prepare revised S45 examples without changing either stopped candidate pair."""

import argparse
import ast
import hashlib
import json
from pathlib import Path

from demos import s45_repair_proposals as original


TASK_GUIDANCE = (
    'Allowed task_type strings: collection, alternative, price, stock. '
    'Use alternative, never conditional_alternative. '
    'Include each requested task once; do not invent a customer task from a tool dependency. '
    'A price-only question does not request collection or stock. '
    'A stock-only question does not request collection. '
    'Collection can use stock internally without a separate stock task. '
    'Include price only when asked, not merely because an alternative has a price limit. '
    'If the customer asks for a conditional alternative, keep that alternative step after collection; '
    'execution decides whether it applies. '
    'Example: "How much does this book cost?" requests price only. '
    'Example: "How many copies are in stock?" requests stock only. '
    'Example: "Can I pick it up tomorrow?" requests collection only. '
    'Example: "Can I pick it up tomorrow? If unavailable, suggest another book under £20." '
    'requests exactly {"plan":[{"task_type":"collection","tool_name":"public_availability_lookup"},'
    '{"task_type":"alternative","tool_name":"public_catalog_search"}]}. '
)


def candidate_files(label):
    source = original.candidate_files(label)['service.py']
    if label == 'prompt':
        prompt = (
            'Return JSON only: {"plan":[{"task_type":"...","tool_name":"..."}]}. '
            + TASK_GUIDANCE
            + 'Collection uses public_availability_lookup; alternative uses public_catalog_search; '
            'price uses public_price_lookup; stock uses public_stock_lookup. '
        )
        prompt_expression = repr(prompt)
        validation = ''
    else:
        prompt_expression = (
            repr('Return only JSON matching this schema: ')
            + " + json.dumps(PLAN_SCHEMA, separators=(',', ':')) + "
            + repr('. ' + TASK_GUIDANCE + 'Task meanings: ')
            + " + json.dumps(TASK_VOCABULARY, separators=(',', ':')) + '. '"
        )
        validation = (
            "    if reply.get('plan_failure') is not None:\n"
            "        return None, reply['plan_failure']\n"
            "    if not validate_plan(reply.get('plan')):\n"
            "        return None, 'LEARNER_SCHEMA_INVALID'\n"
        )
    replacement = (
        'def ask_for_plan(text):\n'
        f'    prompt = {prompt_expression} + \'No prose, reasoning or code fences. Customer request: \' + text\n'
        '    ordinal = next_request_ordinal()\n'
        '    try:\n'
        "        reply = gateway_call('/infer', {'request_ordinal': ordinal, 'input_text': prompt, 'enable_thinking': False})\n"
        '    except (OSError, ValueError, RuntimeError):\n'
        "        return None, 'GATEWAY_UNAVAILABLE'\n"
        + validation
        + "    return reply.get('plan'), reply.get('plan_failure')\n"
    )
    node = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'ask_for_plan')
    lines = source.splitlines(keepends=True)
    source = ''.join(lines[:node.lineno - 1]) + replacement + ''.join(lines[node.end_lineno:])
    source = source.replace('# UNAPPROVED operator-authored S45 ', '# UNAPPROVED revised operator-authored S45 ', 1)
    compile(source, f's45-revised-{label}', 'exec')
    return {'service.py': source}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    manifest = {'state': 'PROPOSED_UNAPPROVED', 'authorship': 'operator-authored examples, not learner work',
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
