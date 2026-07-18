from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from kikuchi_lab.workflows.ice_reflector_catalog import build_ice_reflector_catalog


ROOT = Path(__file__).parents[2]
RECIPE = ROOT / "recipes/reflectors/ice-ih-catalog.yml"


def test_ice_catalog_manifest_inventories_the_complete_immutable_bundle(tmp_path: Path) -> None:
    result = build_ice_reflector_catalog(RECIPE, tmp_path / "published")
    manifest = json.loads(result.manifest.read_text(encoding="utf-8"))

    assert manifest["run_id"] == result.run_id
    assert manifest["catalog"] == "reflector-catalog.json"
    assert manifest["files"].keys() == {
        "catalog-ledger.json",
        "catalog-recipe.json",
        "reflector-catalog.json",
    }
    for relative, record in manifest["files"].items():
        payload = (result.path / relative).read_bytes()
        assert record == {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }


def test_bounded_ice_workflow_rejects_a_phase_neutral_policy_variant(tmp_path: Path) -> None:
    source = RECIPE.read_text(encoding="utf-8")
    variant = tmp_path / "variant.yml"
    variant.write_text(
        source.replace("selection_relative_factor: 0.22", "selection_relative_factor: 0.5"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="bounded Ice.*selection_relative_factor"):
        build_ice_reflector_catalog(variant, tmp_path / "published")

    assert not (tmp_path / "published").exists()
