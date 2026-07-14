from __future__ import annotations

import hashlib
from importlib import import_module
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import sys
import zipfile

import numpy as np
import pytest

from kikuchi_lab.model.identity import canonical_json, stable_id
from kikuchi_lab.spherical_intensity import (
    SphericalBundleExistsError,
    SphericalBundlePartialError,
    SphericalBundleStage,
    SphericalIntensityBuild,
    build_spherical_intensity,
    finalize_spherical_bundle,
    stage_spherical_bundle,
)
sys.path.insert(0, str(Path(__file__).parents[1]))
_fixtures = import_module("spherical_fixtures")
fixture_source = _fixtures.fixture_source
noncentrosymmetric_source = _fixtures.noncentrosymmetric_source
small_spherical_build = _fixtures.small_spherical_build
spherical_recipe = _fixtures.spherical_recipe
symmetric_master = _fixtures.symmetric_master
synthetic_simulation = _fixtures.synthetic_simulation


BASE_FILES = {
    "forsterite-s2-intensity.csv",
    "forsterite-s2-intensity.npz",
    "forsterite-s2-intensity.json",
    "forsterite-s2-axial.csv",
    "diagnostics/mtex-status.json",
}
DIRECTIONAL_HEADER = (
    "x,y,z,hemisphere,source_row,source_column,intensity_raw,"
    "intensity_normalized,density_weight"
)
AXIAL_HEADER = (
    "x,y,z,member_a_hemisphere,member_a_row,member_a_column,"
    "member_b_hemisphere,member_b_row,member_b_column,intensity_raw,"
    "intensity_normalized,density_weight"
)
NPZ_MEMBERS = [
    "density_weight.npy",
    "hemisphere.npy",
    "intensity_normalized.npy",
    "intensity_raw.npy",
    "source_column.npy",
    "source_row.npy",
    "xyz.npy",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage(root: Path, *, build: SphericalIntensityBuild | None = None) -> SphericalBundleStage:
    return stage_spherical_bundle(
        root,
        build or small_spherical_build(),
        spherical_recipe(),
        fixture_source(),
    )


def _python_only_bundle(
    root: Path, *, build: SphericalIntensityBuild | None = None
):
    return finalize_spherical_bundle(_stage(root, build=build), mtex_result=None)


def _without_axial_build() -> SphericalIntensityBuild:
    source = noncentrosymmetric_source()
    return build_spherical_intensity(
        synthetic_simulation(symmetric_master(), source=source),
        source,
        spherical_recipe(),
    )


def test_python_bundle_has_exact_inventory_and_hashes(tmp_path: Path) -> None:
    result = _python_only_bundle(tmp_path)
    manifest_path = result.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert set(manifest["files"]) == BASE_FILES
    actual = {
        str(path.relative_to(result.path))
        for path in result.path.rglob("*")
        if path.is_file()
    }
    assert actual == BASE_FILES | {"manifest.json"}
    assert manifest_path.read_text(encoding="utf-8") == canonical_json(manifest)
    assert "manifest.json" not in manifest["files"]
    for relative, record in manifest["files"].items():
        payload = (result.path / relative).read_bytes()
        assert record == {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    assert result.manifest_sha256 == _sha256(manifest_path)


def test_csv_headers_rows_numeric_format_and_lf_are_exact(tmp_path: Path) -> None:
    stage = _stage(tmp_path)
    directional = (stage.staging_path / "forsterite-s2-intensity.csv").read_bytes()
    axial = (stage.staging_path / "forsterite-s2-axial.csv").read_bytes()

    assert b"\r" not in directional + axial
    directional_lines = directional.decode("ascii").splitlines()
    axial_lines = axial.decode("ascii").splitlines()
    assert directional.endswith(b"\n")
    assert axial.endswith(b"\n")
    assert directional_lines[0] == DIRECTIONAL_HEADER
    assert directional_lines[1] == "0,-1,0,1,0,2,3,1,1"
    assert directional_lines[2] == (
        "-0.66666666666666663,-0.66666666666666663,0.33333333333333331,"
        "1,1,1,1.75,0.37106918238993714,0.22603845541715939"
    )
    assert axial_lines[0] == AXIAL_HEADER
    assert axial_lines[1] == (
        "-0.66666666666666663,-0.66666666666666663,0.33333333333333331,"
        "1,1,1,-1,3,3,1.75,0.37106918238993714,0.22603845541715939"
    )
    assert len(directional_lines) == len(small_spherical_build().field.xyz) + 1
    assert len(axial_lines) == len(small_spherical_build().axial_field.xyz) + 1


def test_npz_has_exact_sorted_members_dtypes_values_and_fixed_zip_metadata(
    tmp_path: Path,
) -> None:
    build = small_spherical_build()
    stage = _stage(tmp_path, build=build)
    path = stage.staging_path / "forsterite-s2-intensity.npz"

    with zipfile.ZipFile(path) as archive:
        assert archive.namelist() == NPZ_MEMBERS
        for info in archive.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.compress_type == zipfile.ZIP_DEFLATED
            assert info.external_attr == 0o600 << 16
    with np.load(path, allow_pickle=False) as arrays:
        assert sorted(arrays.files) == [name.removesuffix(".npy") for name in NPZ_MEMBERS]
        expected = {
            "density_weight": ("<f8", build.field.density_weight),
            "hemisphere": ("|i1", build.field.hemisphere),
            "intensity_normalized": ("<f8", build.field.intensity_normalized),
            "intensity_raw": ("<f4", build.field.intensity_raw),
            "source_column": ("<i4", build.field.source_column),
            "source_row": ("<i4", build.field.source_row),
            "xyz": ("<f8", build.field.xyz),
        }
        for name, (dtype, values) in expected.items():
            assert arrays[name].dtype.str == dtype
            np.testing.assert_array_equal(arrays[name], values)


def test_repeated_staging_writes_identical_scientific_artifact_bytes(
    tmp_path: Path,
) -> None:
    first = _stage(tmp_path / "first").staging_path
    second = _stage(tmp_path / "second").staging_path
    for relative in (
        "forsterite-s2-intensity.csv",
        "forsterite-s2-intensity.npz",
        "forsterite-s2-intensity.json",
        "forsterite-s2-axial.csv",
    ):
        assert (first / relative).read_bytes() == (second / relative).read_bytes()


def test_ledger_is_path_free_canonical_and_links_exact_scientific_identities(
    tmp_path: Path,
) -> None:
    build = small_spherical_build()
    recipe = spherical_recipe()
    source = fixture_source()
    stage = _stage(tmp_path, build=build)
    path = stage.staging_path / "forsterite-s2-intensity.json"
    ledger = json.loads(path.read_text(encoding="utf-8"))

    assert path.read_text(encoding="utf-8") == canonical_json(ledger)
    assert ledger["schema_version"] == 1
    assert ledger["field_id"] == build.field.field_id
    assert ledger["metadata"] == build.field.metadata_dict()
    assert ledger["channel_sha256"] == dict(build.field.channel_sha256)
    assert ledger["recipe"] == {"recipe_id": recipe.recipe_id, "content": recipe.to_dict()}
    assert ledger["verified_source_links"] == {
        "phase_source_id": source.source_record.source_id,
        "source_sha256": source.sha256,
        "source_uri": source.uri,
        "source_page_uri": source.page_uri,
    }
    assert ledger["axial_available"] is True
    assert ledger["axial_field_id"] == build.axial_field.field_id
    assert ledger["axial_channel_sha256"] == dict(build.axial_field.channel_sha256)
    assert ledger["extension_artifacts"] == {}
    assert set(ledger["artifacts"]) == {
        "forsterite-s2-intensity.csv",
        "forsterite-s2-intensity.npz",
        "forsterite-s2-axial.csv",
    }
    assert "manifest" not in canonical_json(ledger)
    assert str(tmp_path) not in canonical_json(ledger)
    assert str(source.record_path) not in canonical_json(ledger)
    for relative, record in ledger["artifacts"].items():
        payload = (stage.staging_path / relative).read_bytes()
        assert record == {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def test_noncentrosymmetric_bundle_omits_only_axial_csv_and_marks_absence(
    tmp_path: Path,
) -> None:
    source = noncentrosymmetric_source()
    build = _without_axial_build()
    stage = stage_spherical_bundle(tmp_path, build, spherical_recipe(), source)
    result = finalize_spherical_bundle(stage, mtex_result=None)

    assert not (result.path / "forsterite-s2-axial.csv").exists()
    actual = {
        str(path.relative_to(result.path))
        for path in result.path.rglob("*")
        if path.is_file()
    }
    assert actual == (BASE_FILES - {"forsterite-s2-axial.csv"}) | {"manifest.json"}
    ledger = json.loads((result.path / "forsterite-s2-intensity.json").read_text())
    assert ledger["axial_available"] is False
    assert ledger["axial_field_id"] is None
    assert ledger["axial_channel_sha256"] is None


def test_axial_absence_rejects_a_reserved_axial_file_added_after_staging(
    tmp_path: Path,
) -> None:
    source = noncentrosymmetric_source()
    stage = stage_spherical_bundle(
        tmp_path, _without_axial_build(), spherical_recipe(), source
    )
    (stage.staging_path / "forsterite-s2-axial.csv").write_text(
        "not-a-validated-axial-field\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="axial"):
        finalize_spherical_bundle(stage, mtex_result=None)


def test_stage_validates_recipe_source_and_build_integrity_before_writing(
    tmp_path: Path,
) -> None:
    build = small_spherical_build()
    mismatched_recipe = replace(
        spherical_recipe(),
        density=replace(spherical_recipe().density, exponent=2.0),
    )
    with pytest.raises(ValueError, match="recipe"):
        stage_spherical_bundle(tmp_path / "recipe", build, mismatched_recipe, fixture_source())
    with pytest.raises(ValueError, match="source"):
        stage_spherical_bundle(
            tmp_path / "source", build, spherical_recipe(), noncentrosymmetric_source()
        )

    object.__setattr__(build.field, "field_id", "s2-field-corrupt")
    with pytest.raises(ValueError, match="corrupt|identity"):
        stage_spherical_bundle(tmp_path / "corrupt", build, spherical_recipe(), fixture_source())
    assert not (tmp_path / "recipe").exists()
    assert not (tmp_path / "source").exists()
    assert not (tmp_path / "corrupt").exists()


def test_finalization_rejects_scientific_artifact_corruption(tmp_path: Path) -> None:
    stage = _stage(tmp_path)
    with (stage.staging_path / "forsterite-s2-intensity.csv").open("ab") as handle:
        handle.write(b"corrupt\n")

    with pytest.raises(ValueError, match="corrupt"):
        finalize_spherical_bundle(stage, mtex_result=None)
    assert stage.staging_path.is_dir()
    assert not [path for path in tmp_path.iterdir() if path.name.startswith("s2-run-")]


def test_failed_writer_leaves_diagnostic_partial_but_never_promotes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kikuchi_lab.spherical_intensity import bundle as bundle_module

    def raising_writer(*args, **kwargs) -> None:
        raise OSError("synthetic write failure")

    monkeypatch.setattr(bundle_module, "_write_csv", raising_writer)
    with pytest.raises(OSError, match="synthetic write failure"):
        _stage(tmp_path)
    children = list(tmp_path.iterdir())
    assert len(children) == 1
    assert children[0].name.startswith(".s2-partial-")
    assert children[0].is_dir()
    assert not [path for path in children if not path.name.startswith(".s2-partial-")]


def test_partial_suffix_is_rejected_and_controlled_failure_status_is_preserved(
    tmp_path: Path,
) -> None:
    stage = _stage(tmp_path)
    (stage.staging_path / "future-output.partial").write_text("incomplete", encoding="utf-8")

    with pytest.raises(SphericalBundlePartialError, match=r"\.partial"):
        finalize_spherical_bundle(stage, mtex_result=None)
    assert stage.staging_path.is_dir()
    status = json.loads(
        (stage.staging_path / "diagnostics/mtex-status.json").read_text(encoding="utf-8")
    )
    assert status["status"] == "finalization-failed"
    assert status["failure_kind"] == "partial-artifact"
    assert not [path for path in tmp_path.iterdir() if path.name.startswith("s2-run-")]


def test_manifest_is_written_last_and_never_self_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kikuchi_lab.spherical_intensity import bundle as bundle_module

    writes: list[str] = []
    original = bundle_module._write_json

    def recording_writer(path: Path, value: object) -> None:
        writes.append(path.name)
        original(path, value)

    monkeypatch.setattr(bundle_module, "_write_json", recording_writer)
    result = _python_only_bundle(tmp_path)
    manifest = json.loads((result.path / "manifest.json").read_text())
    assert writes[-1] == "manifest.json"
    assert "manifest.json" not in manifest["files"]
    assert result.manifest_sha256 not in canonical_json(manifest)


def test_finalizer_fsyncs_every_pre_manifest_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kikuchi_lab.spherical_intensity import bundle as bundle_module

    stage = _stage(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(
        bundle_module,
        "_fsync_existing_file",
        lambda path: calls.append(str(path.relative_to(stage.staging_path))),
    )
    finalize_spherical_bundle(stage, mtex_result=None)
    assert set(calls) == BASE_FILES


def test_existing_destination_is_never_replaced_even_at_final_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kikuchi_lab.spherical_intensity import bundle as bundle_module

    first = _python_only_bundle(tmp_path)
    sentinel = first.path / "sentinel.txt"
    sentinel.write_text("original", encoding="utf-8")
    second = _stage(tmp_path)
    with pytest.raises(SphericalBundleExistsError):
        finalize_spherical_bundle(second, mtex_result=None)
    assert sentinel.read_text(encoding="utf-8") == "original"

    collision_root = tmp_path / "late"
    stage = _stage(collision_root)
    real_promote = bundle_module._promote_directory_no_replace

    def colliding_promote(source: Path, destination: Path) -> None:
        destination.mkdir()
        (destination / "sentinel.txt").write_text("racer", encoding="utf-8")
        real_promote(source, destination)

    monkeypatch.setattr(bundle_module, "_promote_directory_no_replace", colliding_promote)
    with pytest.raises(SphericalBundleExistsError):
        finalize_spherical_bundle(stage, mtex_result=None)
    assert next(collision_root.glob("s2-run-*/sentinel.txt")).read_text() == "racer"
    assert stage.staging_path.is_dir()
    assert not list(collision_root.glob(".*.publishing"))


def test_run_id_is_path_neutral_and_only_stable_mtex_observations_affect_it(
    tmp_path: Path,
) -> None:
    first = _python_only_bundle(tmp_path / "relocated-a")
    second = _python_only_bundle(tmp_path / "relocated-b")
    assert first.run_id == second.run_id

    changed_recipe = spherical_recipe(half_size=3)
    changed_build = build_spherical_intensity(
        synthetic_simulation(symmetric_master(half_size=3)),
        fixture_source(),
        changed_recipe,
    )
    changed_stage = stage_spherical_bundle(
        tmp_path / "changed-science",
        changed_build,
        changed_recipe,
        fixture_source(),
    )
    changed_science = finalize_spherical_bundle(changed_stage, mtex_result=None)
    assert changed_science.run_id != first.run_id

    success_a = finalize_spherical_bundle(
        _stage(tmp_path / "mtex-a"),
        mtex_result={
            "status": "success",
            "requested_profile": "smoke",
            "versions": {"mtex": "6.1.1", "matlab": "24.2"},
            "elapsed_seconds": 1.0,
            "command": "/private/a/matlab -batch run",
            "log": "first path /private/a",
        },
    )
    success_b = finalize_spherical_bundle(
        _stage(tmp_path / "mtex-b"),
        mtex_result={
            "status": "success",
            "requested_profile": "smoke",
            "versions": {"mtex": "6.1.1", "matlab": "24.2"},
            "elapsed_seconds": 99.0,
            "command": "/private/b/matlab -batch run",
            "log": "different prose",
        },
    )
    assert success_a.run_id == success_b.run_id
    assert success_a.run_id != first.run_id

    changed_version = finalize_spherical_bundle(
        _stage(tmp_path / "mtex-c"),
        mtex_result={
            "status": "success",
            "requested_profile": "smoke",
            "versions": {"mtex": "6.2.0", "matlab": "24.2"},
        },
    )
    changed_status = finalize_spherical_bundle(
        _stage(tmp_path / "mtex-d"),
        mtex_result={"status": "failed", "requested_profile": "smoke", "error": "boom"},
    )
    assert changed_version.run_id != success_a.run_id
    assert changed_status.run_id != success_a.run_id


def test_manifest_run_identity_matches_path_and_excludes_diagnostic_prose(
    tmp_path: Path,
) -> None:
    result = finalize_spherical_bundle(
        _stage(tmp_path),
        mtex_result={
            "status": "failed",
            "requested_profile": "smoke",
            "error": "local error /private/tmp/example",
            "elapsed_seconds": 12.5,
        },
    )
    manifest = json.loads((result.path / "manifest.json").read_text())
    assert manifest["run_identity"]["schema_version"] == 1
    assert stable_id("s2-run", manifest["run_identity"]) == result.run_id
    assert (
        "source_kinematical_recipe"
        not in manifest["run_identity"]["scientific_identity"]["recipe"]["content"]
    )
    assert manifest["run_identity"]["mtex"] == {
        "requested_profile": "smoke",
        "status": "failed",
    }
    assert "local error" not in canonical_json(manifest["run_identity"])
    status = json.loads((result.path / "diagnostics/mtex-status.json").read_text())
    assert status["error"] == "local error /private/tmp/example"


def test_successful_mtex_versions_cannot_smuggle_a_local_path_into_run_identity(
    tmp_path: Path,
) -> None:
    stage = _stage(tmp_path)
    with pytest.raises(ValueError, match="local path"):
        finalize_spherical_bundle(
            stage,
            mtex_result={
                "status": "success",
                "requested_profile": "smoke",
                "versions": {"mtex": "/Applications/MATLAB_R2024b.app"},
            },
        )
    assert stage.staging_path.is_dir()
    assert not [path for path in tmp_path.iterdir() if path.name.startswith("s2-run-")]


def test_stage_and_build_are_deeply_immutable(tmp_path: Path) -> None:
    build = small_spherical_build()
    stage = _stage(tmp_path, build=build)
    with pytest.raises(FrozenInstanceError):
        stage.field_id = "changed"
    with pytest.raises(TypeError):
        stage.scientific_identity["field_id"] = "changed"
    with pytest.raises(TypeError):
        stage.scientific_identity["recipe"]["content"]["name"] = "changed"
    with pytest.raises(ValueError):
        build.field.xyz.setflags(write=True)
