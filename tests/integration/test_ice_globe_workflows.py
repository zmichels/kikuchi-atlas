from __future__ import annotations

import json
from pathlib import Path

import yaml

from kikuchi_lab.ice_globe.workflow import build_ice_intensity_globe
from kikuchi_lab.reflector_globe.workflow import build_reflector_globe
from kikuchi_lab.workflows.ice_reflector_catalog import build_ice_reflector_catalog


ROOT = Path(__file__).parents[2]
KINEMATICAL_RECIPE = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"
INTENSITY_RECIPE = ROOT / "recipes/globes/ice-ih-intensity.yml"
CATALOG_RECIPE = ROOT / "recipes/reflectors/ice-ih-catalog.yml"
RIDGE_RECIPE = ROOT / "recipes/globes/ice-ih-reflector-ridges.yml"


def test_intensity_and_ridge_bundles_have_distinct_product_kinds(tmp_path: Path) -> None:
    intensity = build_ice_intensity_globe(
        KINEMATICAL_RECIPE, INTENSITY_RECIPE, tmp_path / "intensity"
    )
    catalog = build_ice_reflector_catalog(CATALOG_RECIPE, tmp_path / "catalog")
    ridge = build_reflector_globe(catalog.catalog, RIDGE_RECIPE, tmp_path / "ridge")

    assert json.loads(intensity.manifest.read_text())["product_kind"] == "intensity_relief"
    assert json.loads(ridge.manifest.read_text())["product_kind"] == "reflector_defined_ridges"


def test_intensity_rerun_is_deterministic_and_accepts_non_80_mm_recipe(tmp_path: Path) -> None:
    recipe = yaml.safe_load(INTENSITY_RECIPE.read_text(encoding="utf-8"))
    recipe["geometry"].update(
        base_diameter_mm=60.0,
        maximum_relief_mm=1.5,
        subdivisions=2,
    )
    smaller_recipe = tmp_path / "non-80-mm.yml"
    smaller_recipe.write_text(yaml.safe_dump(recipe, sort_keys=False), encoding="utf-8")

    first = build_ice_intensity_globe(KINEMATICAL_RECIPE, smaller_recipe, tmp_path / "first")
    second = build_ice_intensity_globe(KINEMATICAL_RECIPE, smaller_recipe, tmp_path / "second")
    first_manifest = json.loads(first.manifest.read_text())
    second_manifest = json.loads(second.manifest.read_text())

    assert first.build_id == second.build_id == first_manifest["build_id"]
    assert first_manifest["field_id"] == second_manifest["field_id"]
    assert first_manifest["files"] == second_manifest["files"]
    assert first_manifest["validation"]["minimum_radius_mm"] >= 30.0
    assert first_manifest["validation"]["maximum_radius_mm"] <= 31.5
