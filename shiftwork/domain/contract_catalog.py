"""Immutable, versioned contract-option catalogs (program design S3.2).

A catalog file pins its own ``content_hash`` over its semantic content (option
ids, dimensions, learner labels, evaluator rule ids, required dimensions and
version). The loader recomputes that hash and refuses to serve a catalog whose
file was edited after freezing, which is what makes a used option's label or
rule id immutable (test 43). A correction authors a NEW catalog version; it
never rewrites a frozen one.
"""

import json
from datetime import datetime
from pathlib import Path

from shiftwork import config
from shiftwork.domain import canonical
from shiftwork.domain.errors import CatalogNotFound, CatalogTampered, InvalidContract
from shiftwork.domain.models import (
    ContractCatalog,
    ContractDimension,
    ContractOption,
    ContractOptionId,
    ContractParams,
    Slug,
)


def catalog_path(slug: Slug, version: int) -> Path:
    return config.CATALOG_DIR / f"{slug}_v{version}.json"


def _semantic_payload(data: dict) -> dict:
    options = sorted(
        (
            {
                "id": option["id"],
                "dimension": option["dimension"],
                "learner_label": option["learner_label"],
                "evaluator_rule_id": option["evaluator_rule_id"],
            }
            for option in data["options"]
        ),
        key=lambda option: option["id"],
    )
    return {
        "engagement_slug": data["engagement_slug"],
        "version": data["version"],
        "required_dimensions": sorted(data["required_dimensions"]),
        "options": options,
    }


def compute_catalog_hash(data: dict) -> str:
    """The canonical hash of a catalog's semantic content (frozen_at excluded)."""
    return canonical.content_hash(_semantic_payload(data))


def load_catalog(slug: Slug, version: int) -> ContractCatalog:
    path = catalog_path(slug, version)
    if not path.exists():
        raise CatalogNotFound(f"no contract catalog for {slug} v{version}")
    data = json.loads(path.read_text(encoding="utf-8"))
    recomputed = compute_catalog_hash(data)
    pinned = data.get("content_hash")
    if pinned != recomputed:
        raise CatalogTampered(
            f"catalog {slug} v{version} is not immutable: frozen hash {pinned!r} "
            f"does not reproduce as {recomputed!r}"
        )
    return ContractCatalog(
        engagement_slug=data["engagement_slug"],
        version=data["version"],
        content_hash=recomputed,
        required_dimensions=tuple(ContractDimension(dim) for dim in data["required_dimensions"]),
        options=tuple(
            ContractOption(
                id=ContractOptionId(option["id"]),
                dimension=ContractDimension(option["dimension"]),
                learner_label=option["learner_label"],
                evaluator_rule_id=option["evaluator_rule_id"],
            )
            for option in data["options"]
        ),
        frozen_at=datetime.fromisoformat(data["frozen_at"]),
    )


def catalog_hash(slug: Slug, version: int) -> str:
    return load_catalog(slug, version).content_hash


def validate_contract(catalog: ContractCatalog, params: ContractParams) -> None:
    """Reject a contract that the frozen catalog does not support (test 22).

    Refuses: a version mismatch, an option id absent from this catalog (for
    example one authored for another engagement), an option bound to the wrong
    dimension, and any required dimension left unselected.
    """
    if params.catalog_version != catalog.version:
        raise InvalidContract(
            f"contract references catalog v{params.catalog_version}; "
            f"loaded {catalog.engagement_slug} v{catalog.version}"
        )

    options_by_id = {option.id: option for option in catalog.options}

    for option_id in params.must_never:
        option = options_by_id.get(option_id)
        if option is None:
            raise InvalidContract(f"option {option_id} is not in catalog {catalog.engagement_slug} v{catalog.version}")
        if option.dimension is not ContractDimension.MUST_NEVER:
            raise InvalidContract(f"option {option_id} is not a MUST_NEVER invariant")

    for dimension, option_id in params.selections.items():
        option = options_by_id.get(option_id)
        if option is None:
            raise InvalidContract(f"option {option_id} is not in catalog {catalog.engagement_slug} v{catalog.version}")
        if option.dimension is not dimension:
            raise InvalidContract(f"option {option_id} does not belong to dimension {dimension}")

    for dimension in catalog.required_dimensions:
        if dimension is ContractDimension.MUST_NEVER:
            if not params.must_never:
                raise InvalidContract("required dimension MUST_NEVER needs at least one option")
        elif dimension not in params.selections:
            raise InvalidContract(f"required dimension {dimension} was not selected")
