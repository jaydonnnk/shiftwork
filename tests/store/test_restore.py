"""Restart reconstruction (S6 test 23 - PARTIAL at Slice 2).

Landed clause: after a process restart, the latest frozen version's content_hash
and the open draft reconstruct from tables alone, with no executor checkpoint and
no in-memory state. The version's stored hash is re-verified on read.

Deferred clauses (NOT claimed here): the ledger-reconstruction clause completes at
Slice 5, and the incident-reconstruction clause completes at Slice 7. The Slice 2
thin path produces one ledger event and opens no incident, so those clauses have
nothing to reconstruct against yet.
"""

from shiftwork import config, orchestrator
from shiftwork.domain.models import ContractDimension, ContractOptionId, ContractParams
from shiftwork.store import db, repo


def _contract() -> ContractParams:
    return ContractParams(
        catalog_version=1,
        must_never=(ContractOptionId.NEVER_INVENT_PRICE_STOCK_POLICY,),
        selections={ContractDimension.STANCE: ContractOptionId.USE_NEWEST_RECORD_WITH_AGE},
        response_time_limit_ms=3000,
        declared_limits=("Answers one fixed shelf-stock request per shift.",),
    )


def _seed(conn) -> None:
    repo.seed_engagement(
        conn,
        config.BOOKSHOP_SLUG,
        config.BOOKSHOP_BUSINESS_KIND,
        config.BOOKSHOP_DISPLAY_NAME,
    )
    repo.seed_engagement_config(
        conn,
        config.BOOKSHOP_SLUG,
        business_kind=config.BOOKSHOP_BUSINESS_KIND,
        assist_level="scaffolded",
        allowed_assist_roles=("hint", "diagnose"),
        total_assist_budget_per_shift=config.BOOKSHOP_TOTAL_ASSIST_BUDGET,
        enabled_check_families=("freshness",),
        attempt_limit=config.DEFAULT_ATTEMPT_LIMIT,
        rotation_group_size=config.BOOKSHOP_ROTATION_GROUP_SIZE,
    )


def test_version_and_draft_reconstruct_after_restart(tmp_path):
    db_file = tmp_path / "restore.db"

    first = db.connect(db_file)
    db.ensure_schema(first)
    _seed(first)
    shift = orchestrator.open_next_shift(first, config.BOOKSHOP_SLUG)
    files, _ = repo.get_draft(first, shift.id)
    files["service.py"] = files["service.py"] + "\n# learner revision\n"
    orchestrator.save_draft(first, shift.id, files)
    version = orchestrator.freeze_version(first, shift.id, _contract())
    frozen_hash = version.content_hash
    first.close()

    # A brand-new connection on the same file: no in-memory state carries over.
    second = db.connect(db_file)
    try:
        restored_shift = repo.get_latest_shift(second, config.BOOKSHOP_SLUG)
        assert restored_shift.id == shift.id

        restored_version = repo.get_latest_version(second, shift.id)
        assert restored_version is not None
        assert restored_version.content_hash == frozen_hash
        assert restored_version.contract == _contract()
        assert restored_version.contract_catalog_hash == version.contract_catalog_hash

        restored_draft = repo.get_draft(second, shift.id)
        assert restored_draft is not None
        assert restored_draft[0]["service.py"].endswith("# learner revision\n")
    finally:
        second.close()
