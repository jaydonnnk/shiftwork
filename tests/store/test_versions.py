"""Version immutability and freeze-requires-valid-contract (S6 tests 21, 22 - FULL).

Test 21 (full): freeze is content-addressed and a frozen version cannot be
mutated. Identical inputs reproduce an identical content_hash; changing a file
byte, the contract, or the catalog hash changes it; and tampering with a stored
version's files is refused on read (VersionTampered) rather than trusted.

Test 22 (full): freeze_version validates the submitted ContractParams against the
frozen catalog and refuses an invalid contract without persisting a version row.
"""

import pytest

from shiftwork import orchestrator
from shiftwork.domain import canonical
from shiftwork.domain.errors import InvalidContract, VersionTampered
from shiftwork.domain.models import ContractDimension, ContractOptionId
from shiftwork.store import repo


def test_freeze_is_deterministic_for_identical_inputs(conn, shift, make_contract):
    first = orchestrator.freeze_version(conn, shift.id, make_contract())
    second = orchestrator.freeze_version(conn, shift.id, make_contract())
    assert first.content_hash == second.content_hash
    assert first.id != second.id
    assert len(first.content_hash) == 64


def test_changing_one_file_byte_changes_the_hash(conn, shift, make_contract):
    before = orchestrator.freeze_version(conn, shift.id, make_contract())
    files = dict(before.files)
    files["service.py"] = files["service.py"] + "\n# one changed byte\n"
    orchestrator.save_draft(conn, shift.id, files)
    after = orchestrator.freeze_version(conn, shift.id, make_contract())
    assert before.content_hash != after.content_hash


def test_changing_the_contract_changes_the_hash(conn, shift, make_contract):
    before = orchestrator.freeze_version(conn, shift.id, make_contract())
    after = orchestrator.freeze_version(
        conn, shift.id, make_contract(response_time_limit_ms=8000)
    )
    assert before.content_hash != after.content_hash


def test_changing_the_catalog_hash_changes_the_hash(make_contract):
    contract = make_contract()
    files = {"service.py": "x = 1\n"}
    cj = canonical.contract_params_json(contract)
    a = canonical.artifact_content_hash(files, cj, "a" * 64)
    b = canonical.artifact_content_hash(files, cj, "b" * 64)
    assert a != b


def test_a_frozen_version_cannot_be_mutated(conn, shift, make_contract):
    version = orchestrator.freeze_version(conn, shift.id, make_contract())
    assert repo.get_version(conn, version.id).content_hash == version.content_hash
    # Tamper with the stored files behind the model's back; the read-back hash
    # check must refuse to serve a version that no longer reproduces its hash.
    conn.execute(
        "UPDATE artifact_versions SET files_json = ? WHERE id = ?",
        ('{"service.py":"TAMPERED"}', version.id),
    )
    conn.commit()
    with pytest.raises(VersionTampered):
        repo.get_version(conn, version.id)


def test_freeze_refuses_a_must_never_option_from_the_wrong_dimension(conn, shift, make_contract):
    bad = make_contract(must_never=(ContractOptionId.USE_NEWEST_RECORD_WITH_AGE,))
    with pytest.raises(InvalidContract):
        orchestrator.freeze_version(conn, shift.id, bad)
    assert repo.count_versions(conn) == 0


def test_freeze_refuses_a_selection_bound_to_the_wrong_dimension(conn, shift, make_contract):
    bad = make_contract(
        selections={ContractDimension.STANCE: ContractOptionId.NEVER_INVENT_PRICE_STOCK_POLICY}
    )
    with pytest.raises(InvalidContract):
        orchestrator.freeze_version(conn, shift.id, bad)
    assert repo.count_versions(conn) == 0


def test_freeze_refuses_a_contract_missing_a_required_dimension(conn, shift, make_contract):
    bad = make_contract(selections={})
    with pytest.raises(InvalidContract):
        orchestrator.freeze_version(conn, shift.id, bad)
    assert repo.count_versions(conn) == 0


def test_freeze_refuses_an_option_that_is_not_in_this_catalog(conn, shift, make_contract):
    # DEDUPLICATE_BOOKING_BY_REQUEST_ID is a valid enum id but is deliberately not
    # in the bookshop catalog v1 (it belongs to the bike-co-op engagement).
    bad = make_contract(
        selections={
            ContractDimension.STANCE: ContractOptionId.USE_NEWEST_RECORD_WITH_AGE,
            ContractDimension.REPEAT_REQUEST_RULE: ContractOptionId.DEDUPLICATE_BOOKING_BY_REQUEST_ID,
        }
    )
    with pytest.raises(InvalidContract):
        orchestrator.freeze_version(conn, shift.id, bad)
    assert repo.count_versions(conn) == 0
