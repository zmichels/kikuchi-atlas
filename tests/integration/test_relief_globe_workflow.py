from __future__ import annotations

import hashlib
import json
import errno
from dataclasses import replace
from pathlib import Path

import pytest
import trimesh
import yaml

import kikuchi_lab.relief.workflow as workflow
from kikuchi_lab.model import MasterPatternProduct, load_master_product, save_master_product
from kikuchi_lab.relief import build_relief_globe
from tests.relief_fixtures import analytic_master_product


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def analytic_master_file(tmp_path: Path) -> Path:
    return save_master_product(tmp_path / "analytic.npz", analytic_master_product())


@pytest.fixture
def canonical_recipe_file(tmp_path: Path, analytic_master_file: Path) -> Path:
    return _write_canonical_recipe(analytic_master_file, tmp_path / "analytic.yml")


def _write_canonical_recipe(master_file: Path, path: Path) -> Path:
    master = load_master_product(master_file)
    payload = {
        "schema": "kikuchi.relief-globe-recipe/v1",
        "source": {
            "product_id": master.product_id,
            "array_sha256": master.array_sha256,
            "file_sha256": _sha256(master_file),
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
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _tree_hashes(path: Path) -> dict[str, str]:
    return {item.name: _sha256(item) for item in sorted(path.iterdir())}


def test_invalid_phase_slug_leaves_no_staging_and_does_not_block_corrected_retry(
    monkeypatch, tmp_path
):
    source = analytic_master_product()
    invalid_metadata = source.metadata_dict()
    invalid_metadata["phase"]["name"] = "岩"
    invalid = MasterPatternProduct.from_array(source.intensity, metadata=invalid_metadata)
    invalid_file = save_master_product(tmp_path / "invalid.npz", invalid)
    invalid_recipe = _write_canonical_recipe(invalid_file, tmp_path / "invalid.yml")
    output = tmp_path / "out"
    monkeypatch.setattr(
        workflow,
        "build_spherical_scalar_field",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("corrected retry reached pipeline")),
    )

    with pytest.raises(
        ValueError, match="phase name cannot form a safe lowercase ASCII slug"
    ):
        build_relief_globe(invalid_file, invalid_recipe, output)

    assert not output.exists()
    assert list(tmp_path.glob("**/*.partial")) == []
    assert list(tmp_path.glob("**/relief-globe-build-*")) == []

    corrected_file = save_master_product(tmp_path / "corrected.npz", source)
    corrected_recipe = _write_canonical_recipe(corrected_file, tmp_path / "corrected.yml")
    with pytest.raises(RuntimeError, match="corrected retry reached pipeline"):
        build_relief_globe(corrected_file, corrected_recipe, output)

    assert not output.exists()


@pytest.mark.parametrize(
    ("needle", "replacement", "field"),
    [
        ("lower: 1.0", "lower: 2.0", "percentiles"),
        ("upper: 99.0", "upper: 98.0", "percentiles"),
        ("gamma: 1.0", "gamma: 0.8", "gamma"),
        ("fwhm_mm: 0.8", "fwhm_mm: 0.9", "FWHM"),
        ("cutoff_sigma: 3.0", "cutoff_sigma: 2.5", "cutoff"),
        ("base_diameter_mm: 80.0", "base_diameter_mm: 79.0", "geometry"),
        ("maximum_relief_mm: 1.2", "maximum_relief_mm: 1.1", "geometry"),
        ("subdivisions: 7", "subdivisions: 6", "geometry"),
        ("topology: icosphere", "topology: alternate-sphere", "geometry"),
        ("direction: bright_outward", "direction: dark_outward", "direction"),
        ("kind: spherical_gaussian", "kind: alternate_filter", "filter kind"),
        ("- stl", "- obj", "export"),
    ],
)
def test_workflow_rejects_noncanonical_recipe_before_source_work(
    monkeypatch, tmp_path, canonical_recipe_file, needle, replacement, field
):
    candidate = tmp_path / f"changed-{field.replace(' ', '-')}.yml"
    candidate.write_text(
        canonical_recipe_file.read_text(encoding="utf-8").replace(needle, replacement),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        workflow,
        "_sha256_file",
        lambda _path: (_ for _ in ()).throw(AssertionError("source work must not start")),
    )

    with pytest.raises(ValueError, match=f"canonical.*{field}"):
        build_relief_globe("unused.npz", candidate, tmp_path / "out")

    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("spoof", [True, float("nan"), "1.0"])
def test_workflow_rejects_type_spoofed_canonical_number_before_source_work(
    monkeypatch, tmp_path, canonical_recipe_file, spoof
):
    recipe = workflow.load_relief_globe_recipe(canonical_recipe_file)
    monkeypatch.setattr(
        workflow,
        "load_relief_globe_recipe",
        lambda _path: replace(recipe, mapping=replace(recipe.mapping, gamma=spoof)),
    )
    monkeypatch.setattr(
        workflow,
        "_sha256_file",
        lambda _path: (_ for _ in ()).throw(AssertionError("source work must not start")),
    )

    with pytest.raises(ValueError, match="canonical.*gamma"):
        build_relief_globe("unused.npz", "unused.yml", tmp_path / "out")


def test_real_no_replace_primitive_preserves_existing_destination(tmp_path):
    staging = tmp_path / "build.partial"
    completed = tmp_path / "build"
    staging.mkdir()
    completed.mkdir()
    (staging / "new").write_text("new", encoding="utf-8")
    (completed / "sentinel").write_text("original", encoding="utf-8")

    with pytest.raises(FileExistsError):
        workflow._rename_directory_no_replace(staging, completed)

    assert (completed / "sentinel").read_text(encoding="utf-8") == "original"
    assert (staging / "new").read_text(encoding="utf-8") == "new"


def test_no_replace_primitive_fails_closed_on_unsupported_platform(monkeypatch, tmp_path):
    staging = tmp_path / "build.partial"
    completed = tmp_path / "build"
    staging.mkdir()
    monkeypatch.setattr(workflow.platform, "system", lambda: "UnsupportedOS")

    with pytest.raises(RuntimeError, match="no-replace.*unsupported"):
        workflow._rename_directory_no_replace(staging, completed)

    assert staging.exists() and not completed.exists()


def test_destination_race_never_clobbers_and_cleans_partial(monkeypatch, tmp_path):
    staging = tmp_path / "build.partial"
    completed = tmp_path / "build"
    staging.mkdir()
    (staging / "new").write_text("new", encoding="utf-8")

    def race(_staging, destination):
        destination.mkdir()
        (destination / "sentinel").write_text("racer", encoding="utf-8")
        raise FileExistsError(errno.EEXIST, "exists")

    monkeypatch.setattr(workflow, "_rename_directory_no_replace", race)
    with pytest.raises(FileExistsError):
        workflow._publish_staging(staging, completed, tmp_path)

    assert (completed / "sentinel").read_text(encoding="utf-8") == "racer"
    assert not staging.exists()


def test_rename_failure_cleans_partial(monkeypatch, tmp_path):
    staging = tmp_path / "build.partial"
    completed = tmp_path / "build"
    staging.mkdir()
    monkeypatch.setattr(
        workflow, "_rename_directory_no_replace", lambda *_args: (_ for _ in ()).throw(OSError("rename failed"))
    )

    with pytest.raises(OSError, match="rename failed"):
        workflow._publish_staging(staging, completed, tmp_path)

    assert not staging.exists() and not completed.exists()


def test_parent_fsync_failure_rolls_back_publication(monkeypatch, tmp_path):
    staging = tmp_path / "build.partial"
    completed = tmp_path / "build"
    staging.mkdir()
    (staging / "artifact").write_text("payload", encoding="utf-8")
    calls = 0

    def fsync(_path):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("parent fsync failed")

    monkeypatch.setattr(workflow, "_fsync_directory", fsync)
    with pytest.raises(RuntimeError, match="rolled back.*parent fsync failed"):
        workflow._publish_staging(staging, completed, tmp_path)

    assert calls == 2
    assert not staging.exists() and not completed.exists()


def test_rollback_failure_reports_uncertain_completed_path(monkeypatch, tmp_path):
    staging = tmp_path / "build.partial"
    completed = tmp_path / "build"
    staging.mkdir()
    monkeypatch.setattr(workflow, "_fsync_directory", lambda _path: (_ for _ in ()).throw(OSError("fsync")))
    monkeypatch.setattr(workflow, "_remove_published_directory", lambda _path: (_ for _ in ()).throw(OSError("rollback")))

    with pytest.raises(workflow.ReliefPublicationUncertainError, match=str(completed)):
        workflow._publish_staging(staging, completed, tmp_path)

    assert completed.exists() and not staging.exists()


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
    for name, record in manifest["files"].items():
        artifact = first.path / name
        assert record == {"bytes": artifact.stat().st_size, "sha256": _sha256(artifact)}
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
