"""S22b: completed deployment tasks use the owning public render vocabulary."""
import json

import pytest

from shiftwork import config
from shiftwork.domain import task_contract
from shiftwork.domain.customer_answer import render_task_customer_text


@pytest.mark.parametrize('case', ['booking_without_claim', 'booking_with_claim', 'safety_route'])
def test_completed_northline_task_renders_its_own_vocabulary(case):
    mission = task_contract.load_mission(config.PACKAGE_DIR / 'fixtures/mission/northline_deployment_v1.json')
    snapshot = task_contract.load_public_state(config.PACKAGE_DIR / 'fixtures/state/northline_start.json')
    spec = mission.request_specs[0]
    entity = spec.requested_entities[0]
    result = {'task_id': 'booking', 'status': 'COMPLETED', 'entity_ref': entity,
              'claims': [], 'commitment_ref': 'public-render-booking', 'explanation_code': None}
    refs = []
    expected = 'A validated repair commitment identifies its slot and stable commitment reference.'
    if case == 'booking_with_claim':
        refs = ['deployment:public-booking-receipt']
        result['claims'] = [{'kind': 'booking', 'entity_ref': entity,
                             'value': {'booking_date': '2026-10-04', 'commitment_ref': result['commitment_ref']},
                             'evidence_refs': refs}]
    elif case == 'safety_route':
        spec = task_contract.CustomerRequestSpec.model_validate(json.loads(
            (config.PACKAGE_DIR / 'fixtures/requests/northline_compare_pair_02_specs.json').read_bytes())[0])
        refs = ['deployment:public-routing-receipt']
        result.update(task_id='safety', commitment_ref=None,
                      claims=[{'kind': 'safety_route', 'entity_ref': entity,
                               'value': 'human_mechanic', 'evidence_refs': refs}])
        expected = 'A validated routing task records escalation to a human mechanic without riding assurance.'
    body = json.dumps({'request_id': spec.id, 'task_results': [result],
                       'evidence_refs': refs, 'uncertainty_codes': []}).encode()
    response = task_contract.validate_response_envelope(spec, body)
    assert render_task_customer_text(spec=spec, mission=mission, snapshot=snapshot, response=response) == expected


def test_northline_referral_keeps_the_public_explanation():
    mission = task_contract.load_mission(config.PACKAGE_DIR / 'fixtures/mission/northline_deployment_v1.json')
    snapshot = task_contract.load_public_state(config.PACKAGE_DIR / 'fixtures/state/northline_start.json')
    spec = mission.request_specs[0]
    body = json.dumps({'request_id': spec.id, 'task_results': [{
        'task_id': 'booking', 'status': 'REFERRED', 'entity_ref': spec.requested_entities[0],
        'claims': [], 'commitment_ref': None, 'explanation_code': 'BOOKING_DATA_UNAVAILABLE',
    }], 'evidence_refs': [], 'uncertainty_codes': []}).encode()
    response = task_contract.validate_response_envelope(spec, body)
    assert render_task_customer_text(spec=spec, mission=mission, snapshot=snapshot, response=response) == (
        'Counter staff must check the parts and mechanic slot before a booking can be confirmed.')
