from __future__ import annotations

import json
from pathlib import Path

import pytest

from kikuchi_lab.reflector_globe.workflow import build_reflector_globe
from kikuchi_lab.workflows.ice_reflector_catalog import build_ice_reflector_catalog


ROOT = Path(__file__).parents[2]
CATALOG_RECIPE = ROOT / "recipes/reflectors/ice-ih-catalog.yml"
RIDGE_RECIPE = ROOT / "recipes/globes/ice-ih-reflector-ridges.yml"


def test_mismatched_catalog_selection_is_rejected_before_output_mutation(tmp_path: Path) -> None:
    catalog = build_ice_reflector_catalog(CATALOG_RECIPE, tmp_path / "catalog")
    payload = json.loads(catalog.catalog.read_text())
    payload["selection"]["cohort_count"] = 3
    invalid = tmp_path / "invalid-catalog.json"
    invalid.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="catalog_id does not match catalog content"):
        build_reflector_globe(invalid, RIDGE_RECIPE, tmp_path / "globes")

    assert not (tmp_path / "globes").exists()
