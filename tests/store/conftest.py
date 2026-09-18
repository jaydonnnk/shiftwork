"""Shared store-test fixtures: a connected, seeded bookshop database.

These back the Slice 2 store tests (version immutability, freeze-requires-valid-
contract, restart reconstruction). They build a real connection on a temp file so
the tests exercise the real schema.sql DDL and repo groups, not a mock.
"""

import pytest

from shiftwork import config, orchestrator
from shiftwork.domain.models import (
    ContractDimension,
    ContractOptionId,
    ContractParams,
)
from shiftwork.store import db, repo


@pytest.fixture()
def seed_bookshop():
    def _seed(conn):
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

    return _seed


@pytest.fixture()
def conn(tmp_path, seed_bookshop):
    connection = db.connect(tmp_path / "store.db")
    db.ensure_schema(connection)
    seed_bookshop(connection)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture()
def shift(conn):
    return orchestrator.open_next_shift(conn, config.BOOKSHOP_SLUG)


@pytest.fixture()
def make_contract():
    def _make(**overrides) -> ContractParams:
        base = {
            "catalog_version": 1,
            "must_never": (ContractOptionId.NEVER_INVENT_PRICE_STOCK_POLICY,),
            "selections": {
                ContractDimension.STANCE: ContractOptionId.USE_NEWEST_RECORD_WITH_AGE
            },
            "response_time_limit_ms": 3000,
            "declared_limits": ("Answers one fixed shelf-stock request per shift.",),
        }
        base.update(overrides)
        return ContractParams(**base)

    return _make
