from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import trimesh
import yaml

import kikuchi_lab.relief.workflow as workflow
from kikuchi_lab.model import load_master_product, save_master_product
from kikuchi_lab.relief import build_relief_globe
from tests.relief_fixtures import analytic_master_product


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def analytic_master_file(tmp_path: Path) -> Path:
    return save_master_product(tmp_path / "analytic.npz", analytic_master_product())


@pytest.fixture
def canonical_recipe_file(tmp_path: Path, analytic_master_file: Path) -> Path:
    master = load_master_product(analytic_master_file)
    payload = {
        "schema": "kikuchi.relief-globe-recipe/v1",
        "source": {
            "product_id": master.product_id,
            "array_sha256": master.array_sha256,
            "file_sha256": _sha256(analytic_master_file),
        },
        "geometry": {
            "base_diameter_mm": 80.0,
            "maximum_relief_mm": 1.2,
            "topology": "icosphere",
            "subdivisions": 7,
        },
        "mapping": {"percentiles": {"lower": 1.0, "upper": 99.0}, "gamma": 1.0,
                    "direction": "bright_outward"},
        "filter": {"kind": "spherical_gaussian", "fwhm_mm": 0.8, "cutoff_sigma": 3.0},
        "export": {"formats": ["stl"]},
        "fdm_context": {"process": "filament_fdm"},
    }
    path = tmp_path / "analytic.yml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _tree_hashes(path: Path) -> dict[str, str]:
    return {item.name: _sha256(item) for item in sorted(path.iterdir())}


@pytest.mark.slow
def test_analytic_globe_build_is_reproducible_atomic_and_complete(
    tmp_path, analytic_master_file, canonical_recipe_file
):
    first = build_relief_globe(analytic_master_file, canonical_recipe_file, tmp_path / "first")
    second = build_relief_globe(analytic_master_file, canonical_recipe_file, tmp_path / "second")
    assert first.build_id == second.build_id
    assert _tree_hashes(first.path) == _tree_hashes(second.path)
    assert {path.name for path in first.path.iterdir()} == {
        "forsterite-intensity-relief-globe.stl",
        "forsterite-intensity-relief-preview.png",
        "relief-field.npz",
        "mesh-validation.json",
        "relief-manifest.json",
    }
    manifest = json.loads(first.manifest.read_text(encoding="utf-8"))
    assert manifest["units"] == "millimetre"
    assert manifest["topology"]["vertex_count"] == 163842
    assert manifest["topology"]["triangle_count"] == 327680
    assert manifest["source"]["master_product_id"] == load_master_product(analytic_master_file).product_id
    assert manifest["validation"]["passed"] is True
    assert manifest["identity"]["validation"] == manifest["validation"]
    assert manifest["identity"]["validation"]["geometry_fingerprint"].startswith(
        "relief-geometry-sha256-"
    )
    assert set(manifest["files"]) == {
        first.stl.name, first.preview.name, first.field.name, first.validation.name
    }
    loaded = trimesh.load_mesh(first.stl, process=True)
    assert loaded.is_volume and loaded.body_count == 1


@pytest.mark.slow
def test_runtime_version_change_changes_build_id(
    monkeypatch, tmp_path, analytic_master_file, canonical_recipe_file
):
    original = workflow._software_versions
    monkeypatch.setattr(workflow, "_software_versions", lambda: {**original(), "scipy": "changed"})
    changed = build_relief_globe(analytic_master_file, canonical_recipe_file, tmp_path / "changed")
    monkeypatch.setattr(workflow, "_software_versions", original)
    normal = build_relief_globe(analytic_master_file, canonical_recipe_file, tmp_path / "normal")
    assert changed.build_id != normal.build_id


@pytest.mark.slow
def test_failure_removes_partial_bundle(
    monkeypatch, tmp_path, analytic_master_file, canonical_recipe_file
):
    def fail_preview(*_args, **_kwargs):
        raise RuntimeError("preview failed")

    monkeypatch.setattr(workflow, "write_relief_preview", fail_preview)
    with pytest.raises(RuntimeError, match="preview failed"):
        build_relief_globe(analytic_master_file, canonical_recipe_file, tmp_path)
    assert list(tmp_path.glob("*.partial")) == []
    assert list(tmp_path.glob("relief-globe-build-*")) == []
