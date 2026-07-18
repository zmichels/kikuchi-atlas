from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.reflector_globe.workflow import build_reflector_globe
from kikuchi_lab.reflectors.contracts import ReflectorCatalog, ReflectorMember
from kikuchi_lab.workflows.ice_reflector_catalog import build_ice_reflector_catalog


ROOT = Path(__file__).parents[2]
CATALOG_RECIPE = ROOT / "recipes/reflectors/ice-ih-catalog.yml"
RIDGE_RECIPE = ROOT / "recipes/globes/ice-ih-reflector-ridges.yml"


def _recompute_catalog_id(payload: dict[str, object]) -> None:
    members = tuple(
        ReflectorMember(
            hkl=tuple(item["hkl"]),
            normal_crystal=np.asarray(item["normal_crystal"], dtype=np.float64),
            dspacing_angstrom=item["dspacing_angstrom"],
            bragg_half_width_rad=item["bragg_half_width_rad"],
            structure_factor_abs=item["structure_factor_abs"],
            normalized_weight=item["normalized_weight"],
            eligible=item["eligible"],
            cohort=item["cohort"],
        )
        for item in payload["members"]
    )
    catalog = ReflectorCatalog(
        source_structure_id=payload["source_structure_id"],
        source_structure_sha256=payload["source_structure_sha256"],
        energy_kev=payload["energy_kev"],
        reflection_recipe_id=payload["reflection_recipe_id"],
        selection=payload["selection"],
        members=members,
    )
    payload["catalog_id"] = catalog.catalog_id


def test_mismatched_catalog_selection_is_rejected_before_output_mutation(tmp_path: Path) -> None:
    catalog = build_ice_reflector_catalog(CATALOG_RECIPE, tmp_path / "catalog")
    payload = json.loads(catalog.catalog.read_text())
    payload["selection"]["cohort_count"] = 3
    invalid = tmp_path / "invalid-catalog.json"
    invalid.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="catalog_id does not match catalog content"):
        build_reflector_globe(invalid, RIDGE_RECIPE, tmp_path / "globes")

    assert not (tmp_path / "globes").exists()


def test_recomputed_catalog_id_cannot_hide_wrong_ice_source_checksum(tmp_path: Path) -> None:
    catalog = build_ice_reflector_catalog(CATALOG_RECIPE, tmp_path / "catalog")
    payload = json.loads(catalog.catalog.read_text())
    payload["source_structure_sha256"] = "0" * 64
    _recompute_catalog_id(payload)
    invalid = tmp_path / "wrong-source-catalog.json"
    invalid.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="source_structure_sha256.*canonical Ice source"):
        build_reflector_globe(invalid, RIDGE_RECIPE, tmp_path / "globes")

    assert not (tmp_path / "globes").exists()


def test_recomputed_catalog_id_cannot_hide_selected_rejected_swap(tmp_path: Path) -> None:
    catalog = build_ice_reflector_catalog(CATALOG_RECIPE, tmp_path / "catalog")
    payload = json.loads(catalog.catalog.read_text())
    selected = next(member for member in reversed(payload["members"]) if member["eligible"])
    rejected = next(member for member in payload["members"] if not member["eligible"])
    selected["eligible"], selected["cohort"] = False, None
    rejected["eligible"], rejected["cohort"] = True, 1
    _recompute_catalog_id(payload)
    invalid = tmp_path / "swapped-membership-catalog.json"
    invalid.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="selected/rejected membership or cohort assignment"):
        build_reflector_globe(invalid, RIDGE_RECIPE, tmp_path / "globes")

    assert not (tmp_path / "globes").exists()
