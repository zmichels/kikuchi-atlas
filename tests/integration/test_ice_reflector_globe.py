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
    ledger = json.loads(result.ledger.read_text())
    manifest = json.loads(result.manifest.read_text())

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
    provenance = ledger["source_to_mesh_provenance"]
    assert provenance["source_structure"] == {
        "structure_id": "COD-1572233-O-sublattice",
        "checksum_sha256": "4327a279e414a62f861d143e18570e9d741bbbb7d04dd2fb471c930988f95b81",
    }
    policy = provenance["selection_policy"]
    assert policy["source_master_relative_factor"] == 0.03
    assert policy["selection_relative_factor"] == 0.22
    assert policy["weight_exponent"] == 2.0
    assert policy["eligibility_min_weight"] == 0.08
    assert policy["tie_policy"] == "keep_equal_weights_together"
    assert policy["package_versions"].keys() == {"diffpy-structure", "diffsims", "orix"}
    assert provenance["member_counts"] == {"catalog": 30, "selected": 15, "rejected": 15}
    assert len(provenance["selected_members"]) == 15
    assert len(provenance["rejected_members"]) == 15
    assert all(
        {
            "member_id",
            "hkl",
            "normal_crystal",
            "bragg_half_width_rad",
            "structure_factor_abs",
            "normalized_weight",
            "cohort",
            "effective_half_width_rad",
            "height_mm",
        }
        <= member.keys()
        for member in provenance["selected_members"]
    )
    assert all(
        member["rejection_reasons"][0]["code"] == "below_eligibility_min_weight"
        for member in provenance["rejected_members"]
    )
    assert manifest["source_provenance"]["selected_member_count"] == 15
    assert manifest["source_provenance"]["rejected_member_count"] == 15
    assert {path.name for path in result.path.iterdir()} == {
        "ice-ih-reflector-ridges.stl",
        "ice-ih-reflector-ridges-preview.png",
        "ridge-field.npz",
        "ridge-ledger.json",
        "mesh-validation.json",
        "reflector-globe-manifest.json",
    }
