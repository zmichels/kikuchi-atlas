from __future__ import annotations

import json
from pathlib import Path

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
