from __future__ import annotations

import json
from pathlib import Path

from kikuchi_lab.reflector_globe.workflow import build_reflector_globe
from kikuchi_lab.workflows.ice_reflector_catalog import build_ice_reflector_catalog


ROOT = Path(__file__).parents[2]
CATALOG_RECIPE = ROOT / "recipes/reflectors/ice-ih-catalog.yml"
RIDGE_RECIPE = ROOT / "recipes/globes/ice-ih-reflector-ridges.yml"


def test_real_ice_ridge_globe_is_a_watertight_three_mm_bounded_single_body(tmp_path: Path) -> None:
    catalog = build_ice_reflector_catalog(CATALOG_RECIPE, tmp_path / "catalog")
    result = build_reflector_globe(catalog.catalog, RIDGE_RECIPE, tmp_path / "globes")
    validation = json.loads(result.validation.read_text())

    assert validation["watertight"] is True
    assert validation["winding_consistent"] is True
    assert validation["body_count"] == 1
    assert validation["minimum_radius_mm"] >= 40.0
    assert validation["maximum_radius_mm"] <= 43.0
    assert {path.name for path in result.path.iterdir()} == {
        "ice-ih-reflector-ridges.stl",
        "ice-ih-reflector-ridges-preview.png",
        "ridge-field.npz",
        "ridge-ledger.json",
        "mesh-validation.json",
        "reflector-globe-manifest.json",
    }
