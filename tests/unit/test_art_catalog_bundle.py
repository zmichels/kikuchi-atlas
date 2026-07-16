from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.art_products.contracts import ArtBandCatalog, ArtBandMember
from kikuchi_lab.artifacts import BundleExistsError, PartialBundleError
from kikuchi_lab.kinematical.recipe import load_kinematical_recipe
from kikuchi_lab.near_depth.recipe import load_near_depth_recipe
from kikuchi_lab.sources.structure import load_structure_record
from kikuchi_lab.spherical_intensity.orientation import load_oriented_spherical_recipe
from kikuchi_lab.spherical_intensity.recipe import load_spherical_intensity_recipe


ROOT = Path(__file__).parents[2]
CATALOG_RECIPE = ROOT / "recipes/art/ice-ih-band-catalog.yml"
ORIENTED_RECIPE = ROOT / "recipes/spherical/ice-ih-oriented-s2-proof.yml"
SPHERICAL_RECIPE = ROOT / "recipes/spherical/ice-ih-s2-intensity.yml"
KINEMATICAL_RECIPE = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"
PRESENTATION_RECIPE = (
    ROOT / "recipes/presentation/ice-ih-near-depth-stepped-field-led.yml"
)
SOURCE_RECORD = ROOT / "phases/ice-ih/source.yml"
PAYLOAD_FILES = {
    "art-band-catalog.json",
    "catalog-recipe.json",
    "catalog-ledger.json",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _catalog(
    *,
    structure_id: str,
    structure_sha256: str,
    source_recipe_id: str,
    presentation_recipe_id: str,
) -> ArtBandCatalog:
    members = tuple(
        ArtBandMember(
            hkl=(index + 1, 0, 0),
            normal_crystal=np.array(
                [np.cos(index * np.pi / 8), np.sin(index * np.pi / 8), 0.0]
            ),
            bragg_half_width_rad=0.01 + index * 0.001,
            structure_factor_magnitude=20.0 - index,
            normalized_weight=1.0 - index * 0.1,
            globe_cohort=4 - index // 2,
            globe_eligible=True,
            tattoo_eligible=True,
            acceptance_state="unreviewed",
            acceptance_reason="automatic catalog candidate",
        )
        for index in range(8)
    )
    return ArtBandCatalog(
        schema_version=1,
        source_structure_id=structure_id,
        source_structure_sha256=structure_sha256,
        source_recipe_id=source_recipe_id,
        presentation_recipe_id=presentation_recipe_id,
        eligibility_min_weight=0.10,
        members=members,
    )


@pytest.fixture
def bundle_inputs() -> dict[str, object]:
    from kikuchi_lab.workflows.ice_art_catalog import load_ice_art_catalog_recipe

    source = load_structure_record(SOURCE_RECORD)
    source_recipe = load_kinematical_recipe(KINEMATICAL_RECIPE)
    presentation_recipe = load_near_depth_recipe(PRESENTATION_RECIPE)
    return {
        "catalog": _catalog(
            structure_id=source.identifier,
            structure_sha256=source.sha256,
            source_recipe_id=source_recipe.recipe_id,
            presentation_recipe_id=presentation_recipe.recipe_id,
        ),
        "catalog_recipe": load_ice_art_catalog_recipe(CATALOG_RECIPE),
        "oriented_recipe": load_oriented_spherical_recipe(
            ORIENTED_RECIPE,
            profile="smoke",
        ),
        "spherical_recipe": load_spherical_intensity_recipe(
            SPHERICAL_RECIPE,
            profile="smoke",
        ),
        "source_recipe": source_recipe,
        "presentation_recipe": presentation_recipe,
        "source": source,
    }


@pytest.mark.parametrize(
    ("forged_field", "message"),
    [
        ("source_recipe_id", "source recipe ID"),
        ("presentation_recipe_id", "presentation recipe ID"),
        ("catalog_id", "catalog_id"),
    ],
)
def test_bundle_rejects_forged_identities_before_output_mutation(
    bundle_inputs: dict[str, object],
    tmp_path: Path,
    forged_field: str,
    message: str,
) -> None:
    from kikuchi_lab.art_products.catalog_bundle import write_art_catalog_bundle

    catalog = bundle_inputs["catalog"]
    assert isinstance(catalog, ArtBandCatalog)
    if forged_field == "catalog_id":
        object.__setattr__(catalog, "catalog_id", "art-band-catalog-forged")
    else:
        catalog = replace(catalog, **{forged_field: f"recipe-forged-{forged_field}"})
    inputs = {**bundle_inputs, "catalog": catalog}
    output_root = tmp_path / forged_field / "runs"

    with pytest.raises(ValueError, match=message):
        write_art_catalog_bundle(output_root, **inputs)

    assert not output_root.exists()


def test_bundle_has_exact_inventory_manifest_and_auditable_ledger(
    bundle_inputs: dict[str, object],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.catalog import load_art_band_catalog
    from kikuchi_lab.art_products.catalog_bundle import write_art_catalog_bundle
    from kikuchi_lab.model.identity import canonical_json, stable_id

    result = write_art_catalog_bundle(tmp_path, **bundle_inputs)
    manifest_path = result.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ledger = json.loads((result.path / "catalog-ledger.json").read_text(encoding="utf-8"))
    catalog = bundle_inputs["catalog"]
    catalog_recipe = bundle_inputs["catalog_recipe"]
    oriented_recipe = bundle_inputs["oriented_recipe"]
    spherical_recipe = bundle_inputs["spherical_recipe"]
    source_recipe = bundle_inputs["source_recipe"]
    presentation_recipe = bundle_inputs["presentation_recipe"]
    source = bundle_inputs["source"]

    assert isinstance(catalog, ArtBandCatalog)
    assert {path.name for path in result.path.iterdir()} == PAYLOAD_FILES | {
        "manifest.json"
    }
    assert set(manifest["files"]) == PAYLOAD_FILES
    assert manifest_path.read_text(encoding="utf-8") == canonical_json(manifest)
    assert result.run_id == stable_id("ice-art-catalog-run", manifest["run_identity"])
    assert result.path == tmp_path / result.run_id
    assert result.manifest_sha256 == _sha256(manifest_path)
    assert load_art_band_catalog(result.path / "art-band-catalog.json").catalog_id == (
        catalog.catalog_id
    )
    for relative, record in manifest["files"].items():
        path = result.path / relative
        assert record == {"bytes": path.stat().st_size, "sha256": _sha256(path)}

    assert ledger == {
        "schema_version": 1,
        "source": {
            "structure_id": source.identifier,
            "structure_sha256": source.sha256,
        },
        "recipe_ids": {
            "catalog_recipe_id": catalog_recipe.recipe_id,
            "oriented_recipe_id": oriented_recipe.recipe_id,
            "spherical_recipe_id": spherical_recipe.recipe_id,
            "source_recipe_id": source_recipe.recipe_id,
            "presentation_recipe_id": presentation_recipe.recipe_id,
        },
        "catalog": {
            "catalog_id": catalog.catalog_id,
            "member_count": 8,
            "globe_eligible_member_count": 8,
            "tattoo_eligible_member_count": 8,
            "globe_cohort_member_counts": {"1": 2, "2": 2, "3": 2, "4": 2},
        },
        "policies": {
            "eligibility_min_weight": 0.10,
            "globe_cohort_count": 4,
            "tie_policy": "keep_equal_weights_together",
            "ranking": "normalized_structure_factor_weight",
        },
        "claim_boundaries": {
            "product_class": "science_art",
            "scientific_claim": "presentation_only",
            "globe_height": (
                "designed tier encoding; not a physical mineral surface or direct "
                "electron-density scale"
            ),
            "tattoo_stroke_width": (
                "graphic rank encoding; not literal Bragg width, detector intensity, "
                "or medical tattooing prescription"
            ),
        },
    }


def test_bundle_run_identity_is_stable_across_parent_directories(
    bundle_inputs: dict[str, object],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.catalog_bundle import write_art_catalog_bundle

    first = write_art_catalog_bundle(tmp_path / "first", **bundle_inputs)
    second = write_art_catalog_bundle(tmp_path / "second" / "nested", **bundle_inputs)

    assert first.run_id == second.run_id
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.path.parent != second.path.parent


def test_bundle_rejects_completed_and_partial_collisions(
    bundle_inputs: dict[str, object],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.catalog_bundle import write_art_catalog_bundle

    completed_root = tmp_path / "completed"
    result = write_art_catalog_bundle(completed_root, **bundle_inputs)
    with pytest.raises(BundleExistsError, match="completed bundle already exists"):
        write_art_catalog_bundle(completed_root, **bundle_inputs)

    partial_root = tmp_path / "partial"
    partial_root.mkdir()
    stale = partial_root / f".{result.run_id}.partial-stale"
    stale.mkdir()
    with pytest.raises(PartialBundleError, match="partial bundle already exists"):
        write_art_catalog_bundle(partial_root, **bundle_inputs)
