from __future__ import annotations

import json
from pathlib import Path

import pytest

from kikuchi_lab.workflows.ice_reflector_catalog import build_ice_reflector_catalog


ROOT = Path(__file__).parents[2]
RECIPE = ROOT / "recipes/reflectors/ice-ih-catalog.yml"


def test_catalog_build_is_path_neutral_and_no_clobber(tmp_path: Path) -> None:
    left = build_ice_reflector_catalog(RECIPE, tmp_path / "left")
    right = build_ice_reflector_catalog(RECIPE, tmp_path / "right")

    assert left.run_id == right.run_id
    assert json.loads(left.catalog.read_text(encoding="utf-8"))["catalog_id"].startswith(
        "reflector-catalog-"
    )
    with pytest.raises(FileExistsError, match="completed reflector catalog"):
        build_ice_reflector_catalog(RECIPE, tmp_path / "left")


def test_catalog_bundle_uses_only_plain_json_and_records_selection_ledger(tmp_path: Path) -> None:
    result = build_ice_reflector_catalog(RECIPE, tmp_path / "catalogs")

    files = {path.name for path in result.path.iterdir()}
    assert files == {
        "reflector-catalog.json",
        "catalog-recipe.json",
        "catalog-ledger.json",
        "manifest.json",
    }
    for path in result.path.iterdir():
        assert path.read_bytes().endswith(b"\n")
        json.loads(path.read_text(encoding="utf-8"))

    ledger = json.loads(result.ledger.read_text(encoding="utf-8"))
    assert ledger["counts"] == {
        "eligible": 15,
        "eligible_weight_blocks": 6,
        "total": 30,
    }
    assert ledger["cohorts"] == {"1": 4, "2": 1, "3": 6, "4": 4}
    assert ledger["threshold"] == 0.08
    assert ledger["tie_policy"] == "keep_equal_weights_together"
    assert "oxygen sublattice" in ledger["claim_boundary"].lower()
