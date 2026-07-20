from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.kinematical.contracts import KinematicalArrayProduct
from kikuchi_lab.kinematical.master_product import canonical_master_product
from kikuchi_lab.kinematical.recipe import load_kinematical_recipe
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
RECIPE_PATH = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"


def _source_product() -> KinematicalArrayProduct:
    recipe = load_kinematical_recipe(RECIPE_PATH)
    source = load_structure_record(RECIPE_PATH.parent / recipe.source_record)
    upper = np.arange(25, dtype=np.float32).reshape(5, 5)
    return KinematicalArrayProduct.from_array(
        "master-lambert",
        np.stack((upper, upper)),
        metadata={
            "source_id": source.source_record.source_id,
            "source_structure_id": source.identifier,
            "source_sha256": source.sha256,
            "recipe_id": recipe.recipe_id,
            "projection": "lambert-square-equal-area",
            "hemisphere": "both",
            "energy_kev": recipe.energy_kev,
        },
    )


def test_canonical_master_product_preserves_lambert_samples_and_lineage() -> None:
    recipe = load_kinematical_recipe(RECIPE_PATH)
    source = load_structure_record(RECIPE_PATH.parent / recipe.source_record)
    raw = _source_product()

    product = canonical_master_product(raw, source=source, recipe=recipe)

    assert np.array_equal(product.intensity, raw.intensity)
    assert product.intensity.dtype == np.float32
    metadata = product.metadata_dict()
    assert metadata["projection"] == "Lambert square equal-area"
    assert metadata["hemisphere_order"] == ["north", "south"]
    assert metadata["simulation"]["recipe_id"] == recipe.recipe_id
    assert metadata["source_structure"]["source_id"] == source.source_record.source_id
    assert raw.product_id in metadata["provenance_links"]
    assert raw.array_sha256 in metadata["provenance_links"]
    assert metadata["hemisphere_grid_alignment"]["lower_operation"] == "identity"


def test_canonical_master_product_records_lower_grid_alignment() -> None:
    recipe = load_kinematical_recipe(RECIPE_PATH)
    source = load_structure_record(RECIPE_PATH.parent / recipe.source_record)
    raw = _source_product()
    intensity = np.array(raw.intensity, copy=True)
    intensity[1] = np.fliplr(intensity[1])
    reindexed = KinematicalArrayProduct.from_array(raw.label, intensity, metadata=raw.metadata)

    product = canonical_master_product(reindexed, source=source, recipe=recipe)

    assert np.array_equal(product.intensity[0], product.intensity[1])
    assert product.metadata_dict()["hemisphere_grid_alignment"]["lower_operation"] == "flip-left-right"


def test_canonical_master_product_rejects_a_noncontinuous_hemisphere_pair() -> None:
    recipe = load_kinematical_recipe(RECIPE_PATH)
    source = load_structure_record(RECIPE_PATH.parent / recipe.source_record)
    raw = _source_product()
    intensity = np.array(raw.intensity, copy=True)
    intensity[1] += 100.0
    discontinuous = KinematicalArrayProduct.from_array(raw.label, intensity, metadata=raw.metadata)

    with pytest.raises(ValueError, match="cannot be aligned at the equator"):
        canonical_master_product(discontinuous, source=source, recipe=recipe)


def test_canonical_master_product_rejects_a_mismatched_retained_source() -> None:
    recipe = load_kinematical_recipe(RECIPE_PATH)
    source = load_structure_record(RECIPE_PATH.parent / recipe.source_record)
    raw = _source_product()
    metadata = dict(raw.metadata)
    metadata["source_sha256"] = "0" * 64
    mismatched = KinematicalArrayProduct.from_array(
        raw.label,
        raw.intensity,
        metadata=metadata,
    )

    with pytest.raises(ValueError, match="source SHA-256"):
        canonical_master_product(mismatched, source=source, recipe=recipe)
