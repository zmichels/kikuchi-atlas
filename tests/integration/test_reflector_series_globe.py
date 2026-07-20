from __future__ import annotations

import json
from pathlib import Path

from kikuchi_lab.reflector_globe.workflow import build_reflector_globe
from kikuchi_lab.workflows.reflector_catalog import build_reflector_catalog_bundle


ROOT = Path(__file__).parents[2]


def test_quartz_reflector_series_builds_named_watertight_ridge_globe(tmp_path: Path) -> None:
    catalog = build_reflector_catalog_bundle(
        ROOT / "recipes/reflectors/quartz-catalog.yml", tmp_path / "catalog"
    )
    globe = build_reflector_globe(
        catalog.catalog,
        ROOT / "recipes/globes/quartz-reflector-ridges.yml",
        tmp_path / "globes",
    )

    assert globe.stl.name == "quartz-reflector-ridges.stl"
    manifest = json.loads(globe.manifest.read_text(encoding="utf-8"))
    validation = json.loads(globe.validation.read_text(encoding="utf-8"))
    assert manifest["source_provenance"]["selected_member_count"] == 27
    assert validation["passed"] is True
    assert validation["watertight"] is True
    assert validation["body_count"] == 1
