from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import trimesh

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
    published = trimesh.load_mesh(result.stl, file_type="stl", process=True)
    assert isinstance(published, trimesh.Trimesh)
    radii = np.linalg.norm(published.vertices, axis=1)
    assert published.is_watertight is True
    assert published.is_winding_consistent is True
    assert published.body_count == 1
    assert radii.min() >= 40.0
    assert radii.max() <= 43.0
    assert validation["minimum_radius_mm"] == radii.min()
    assert validation["maximum_radius_mm"] == radii.max()
    assert {path.name for path in result.path.iterdir()} == {
        "ice-ih-reflector-ridges.stl",
        "ice-ih-reflector-ridges-preview.png",
        "ridge-field.npz",
        "ridge-ledger.json",
        "mesh-validation.json",
        "reflector-globe-manifest.json",
    }
