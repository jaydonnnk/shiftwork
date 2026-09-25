"""Contract catalog immutability (program design S6 test 43, PARTIAL at Slice 2).

Landed clause: changing a used option's learner_label or evaluator_rule_id is
refused, because the frozen catalog file pins a content_hash over its semantic
content and the loader recomputes it.

Deferred clause (completes at Slice 5): "a new version may change wording/
semantics while old ledger entries still resolve against their original catalog
version". That needs the ledger to resolve catalog-version references, which
the Slice 2 single-event path does not yet do. Not claimed here.
"""

import json

import pytest

from shiftwork import config
from shiftwork.domain.contract_catalog import compute_catalog_hash, load_catalog, validate_contract
from shiftwork.domain.errors import CatalogNotFound, CatalogTampered, InvalidContract
from shiftwork.domain.models import ContractParams


def _write_catalog(dirpath, data):
    path = dirpath / f"{data['engagement_slug']}_v{data['version']}.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _real_catalog_data():
    real_path = config.PACKAGE_DIR / "fixtures" / "catalogs" / "bookshop_v1.json"
    return json.loads(real_path.read_text(encoding="utf-8"))


def test_frozen_catalog_loads_and_reproduces_its_pinned_hash():
    catalog = load_catalog("bookshop", 1)
    data = _real_catalog_data()
    assert catalog.content_hash == data["content_hash"]
    assert catalog.content_hash == compute_catalog_hash(data)
    assert len(catalog.options) == len(data["options"])


@pytest.mark.parametrize("field", ["learner_label", "evaluator_rule_id"])
def test_changing_a_used_option_field_is_refused(tmp_path, monkeypatch, field):
    # Test 43 (landed clause): editing a frozen option's label or rule id breaks
    # the pinned content_hash, so the loader refuses to serve the catalog.
    data = _real_catalog_data()
    data["options"][0][field] = "TAMPERED VALUE"
    _write_catalog(tmp_path, data)
    monkeypatch.setattr(config, "CATALOG_DIR", tmp_path)
    with pytest.raises(CatalogTampered):
        load_catalog("bookshop", 1)


def test_changing_a_used_option_id_is_refused(tmp_path, monkeypatch):
    data = _real_catalog_data()
    data["options"][1]["id"] = "ESTIMATE_ONLY_WITH_EVIDENCE"
    _write_catalog(tmp_path, data)
    monkeypatch.setattr(config, "CATALOG_DIR", tmp_path)
    with pytest.raises((CatalogTampered, ValueError)):
        load_catalog("bookshop", 1)


def test_a_new_version_may_change_wording_when_rehashed(tmp_path, monkeypatch):
    # The immutable-within-a-version rule does not forbid a NEW version; it only
    # forbids editing a frozen one. A v2 with re-pinned hash loads cleanly.
    data = _real_catalog_data()
    data["version"] = 2
    data["options"][0]["learner_label"] = "Revised wording for v2"
    data.pop("content_hash")
    data["content_hash"] = compute_catalog_hash(data)
    _write_catalog(tmp_path, data)
    monkeypatch.setattr(config, "CATALOG_DIR", tmp_path)
    catalog = load_catalog("bookshop", 2)
    assert catalog.version == 2
    revised = next(o for o in catalog.options if o.id.value == data["options"][0]["id"])
    assert revised.learner_label == "Revised wording for v2"


def test_missing_catalog_version_is_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CATALOG_DIR", tmp_path)
    with pytest.raises(CatalogNotFound):
        load_catalog("bookshop", 99)


@pytest.mark.parametrize("stance", ["VERIFY_EXACT_CLAIMS_NOW", "HARD_CHECK_HIGH_RISK_ONLY"])
def test_pivot_catalog_rejects_incompatible_legacy_stances(stance):
    params = ContractParams.model_validate({
        **config.PIVOT_STARTER_CONTRACT_JSON,
        "selections": {"STANCE": stance},
    })
    validate_contract(load_catalog("bookshop", 2), params.model_copy(update={"catalog_version": 2}))
    with pytest.raises(InvalidContract, match="not in catalog"):
        validate_contract(load_catalog("bookshop", 3), params)


def test_pivot_catalog_accepts_bound_contract_and_preserves_historical_catalogs():
    catalog = load_catalog("bookshop", 3)
    validate_contract(catalog, ContractParams.model_validate(config.PIVOT_STARTER_CONTRACT_JSON))
    assert {option.id.value for option in catalog.options} == {
        "NEVER_INVENT_PRICE_STOCK_POLICY", "USE_NEWEST_RECORD_WITH_AGE",
    }
    assert catalog.content_hash == "d9f18ddafd0cd7f791bd13b58b72b165954c1c51df824c96127ad4796bf7736a"
    assert load_catalog("bookshop", 1).content_hash == "d3df268cc83863a75f465543de26ab712efd7be193200a5e82710093d235ced6"
    assert load_catalog("bookshop", 2).content_hash == "8fa29ef4a46f34b541370873caf09967445075f805fcc25200c3738f3ac36a37"


def test_pivot_catalog_policy_tampering_is_rejected(tmp_path, monkeypatch):
    data = json.loads((config.CATALOG_DIR / "bookshop_v3.json").read_bytes())
    data["options"][1]["learner_label"] = "Answer stale stock without checking."
    _write_catalog(tmp_path, data)
    monkeypatch.setattr(config, "CATALOG_DIR", tmp_path)
    with pytest.raises(CatalogTampered):
        load_catalog("bookshop", 3)
