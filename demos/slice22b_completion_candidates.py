"""Operator verification candidates authored from public Northline requirements.

These bytes are not a learner submission or a new production trusted-local pin.
"""
import json

SERVICE = r'''"""Operator verification fixture; public inputs only, simulated actions."""
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import re

PROVISIONAL_FIRST = __POLICY__
commitments = {}

def received_intent(request):
    text = request['text']
    explicit = re.findall(r'\bcounter intent ([A-Za-z0-9][A-Za-z0-9_-]*)(?=[\s.,;!?]|$)', text)
    visits = re.findall(r'\bvisit (V-[0-9]+)(?=[\s.,;!?]|$)', text)
    if (len(re.findall(r'\bcounter intent\b', text)) != len(explicit)
            or len(re.findall(r'\bvisit V-', text)) != len(visits)
            or len(set(explicit)) > 1 or len(set(visits)) > 1):
        raise ValueError('ambiguous or malformed intent')
    visit = 'northline-intent-' + visits[0].replace('-', '') if visits else None
    key = explicit[0] if explicit else visit or request['request_id']
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,255}', key) or (explicit and visit and key != visit):
        raise ValueError('invalid or conflicting intent')
    return key

def respond(request, intent, act):
    entity, text = request['entity_ref'], request['text'].lower()
    task = {'task_id': 'booking', 'status': 'REFERRED', 'entity_ref': entity,
            'claims': [], 'commitment_ref': None, 'explanation_code': 'BOOKING_DATA_UNAVAILABLE'}
    if 'uninspected' in text:
        routed = act({'operation': 'ROUTE_HUMAN', 'resource': 'mechanic_schedule',
                      'entity_ref': entity, 'route': 'human_mechanic'})
        task.update(task_id='safety', status='COMPLETED', explanation_code=None,
                    claims=[{'kind': 'safety_route', 'entity_ref': entity,
                             'value': 'human_mechanic', 'evidence_refs': [routed['receipt']]}])
    elif any(word in text for word in ('account', 'payment', 'customer history')):
        task.update(status='REFUSED', explanation_code='ACCESS_NOT_PERMITTED')
    else:
        declared = re.search(r'stable commitment reference is ([A-Za-z0-9_-]+)', request['text'])
        if intent in commitments:
            task.update(status='COMPLETED', commitment_ref=commitments[intent], explanation_code=None)
        elif declared:
            # Customer-supplied text is a reference, never evidence of an executed write.
            task.update(status='COMPLETED', commitment_ref=declared[1], explanation_code=None)
        else:
            pieces = entity.split(':')
            part = 'part:chain:standard' if 'chain' in text else 'part:brake-pad:standard' if 'brake-pad' in text else None
            if len(pieces) == 3 and pieces[0] == 'slot' and part:
                date = pieces[1]
                stock = act({'operation': 'READ', 'resource': 'parts_availability', 'entity_ref': part})['records']
                stock_ready = (len(stock) == 1 and type(stock[0]['value']) is int
                               and stock[0]['value'] > 0 and 0 <= stock[0]['record_age_ms'] <= 3600000)
                provisional = None
                reference = 'repair-' + intent
                write = {'operation': 'WRITE_SLOT', 'resource': 'repair_slots', 'entity_ref': entity,
                         'part_ref': part, 'booking_date': date, 'intent_key': intent,
                         'commitment_ref': reference, 'stage': 'FINAL'}
                if stock_ready and PROVISIONAL_FIRST:
                    provisional = act({**write, 'stage': 'PROVISIONAL'})
                schedule = act({'operation': 'READ', 'resource': 'mechanic_schedule', 'entity_ref': entity})['records']
                ready = (stock_ready and len(schedule) == 1
                         and 0 <= schedule[0]['record_age_ms'] <= 3600000
                         and schedule[0]['value']['collection_date'] == date
                         and schedule[0]['value']['can_collect'] is True)
                if provisional:
                    act({'operation': 'ROLLBACK', 'resource': 'repair_slots', 'entity_ref': entity,
                         'target_receipt': provisional['receipt']})
                if ready:
                    final = act(write)
                    commitments[intent] = final['commitment_ref']
                    task.update(status='COMPLETED', commitment_ref=final['commitment_ref'], explanation_code=None)
    return {'request_id': request['request_id'], 'task_results': [task],
            'evidence_refs': [ref for claim in task['claims'] for ref in claim['evidence_refs']],
            'uncertainty_codes': []}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def act(self, operation):
        conn = http.client.HTTPConnection('127.0.0.1', int(os.environ['SHIFTWORK_GATEWAY_PORT']), timeout=5)
        try:
            conn.request('POST', '/deployment', json.dumps(operation).encode(),
                         {'X-Shiftwork-Request-Token': self.headers['X-Shiftwork-Request-Token']})
            response = conn.getresponse()
            if response.status != 200:
                raise RuntimeError('resource action refused')
            return json.loads(response.read())
        finally:
            conn.close()
    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        intent = self.headers.get('X-Shiftwork-Intent-Key') or received_intent(request)
        body = json.dumps(respond(request, intent, self.act), separators=(',', ':')).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == '__main__':
    with HTTPServer(('127.0.0.1', 0), Handler) as server:
        print(json.dumps({'port': server.server_port}), flush=True)
        server.serve_forever()
'''

VISIBLE_TESTS = '''"""Visible operator checks, not independent acceptance authority."""
import unittest
import service

class RetryTests(unittest.TestCase):
    def test_existing_intent_never_writes_again(self):
        service.commitments.clear()
        service.commitments['counter-visit'] = 'repair-counter-visit'
        def unexpected_action(operation):
            self.fail('retry attempted another resource action')
        response = service.respond({'request_id': 'delivery-2', 'text': 'Retry the brake-pad booking.',
                                    'entity_ref': 'slot:2026-10-04:0900'}, 'counter-visit', unexpected_action)
        self.assertEqual(response['task_results'][0]['commitment_ref'], 'repair-counter-visit')

if __name__ == '__main__':
    unittest.main()
'''

def candidate_files(label):
    if label not in ('A', 'B'):
        raise ValueError('candidate label must be A or B')
    strategy = 'provisional allocation before schedule read, then rollback and final confirmation' if label == 'A' else 'both reads before one final allocation'
    return {
        'service.py': SERVICE.replace('__POLICY__', 'True' if label == 'A' else 'False'),
        'discovery.md': '# Operator verification discovery\nPublic P-01 requires current parts and slot evidence before final confirmation. W-01 requires one stable commitment per intent. P-02 routes uninspected safety questions; P-03 excludes payments/accounts/history.\nStrategy: ' + strategy + '.\nNo learner authorship or learning evidence.\n',
        'permissions.json': json.dumps({'reads': ['parts_availability', 'mechanic_schedule'], 'writes': ['repair_slots']}, indent=2),
        'acceptance_tests.py': VISIBLE_TESTS,
        'runbook.md': '# Operator verification runbook ' + label + '\nStrategy: ' + strategy + '.\nRetain the final reference by received stable intent; retries make no additional write. Escalate uninspected safety questions to a human mechanic. Refuse prohibited account/payment/history work.\nLimits: simulated resources only; process-memory receipts are lost on restart; a customer-provided prior reference proves no prior write. No durable external booking, concurrent-worker correctness, learner authorship, model interpretation or learning claim.\n',
    }
