from __future__ import annotations

import errno
import hashlib
import json
from dataclasses import replace
from pathlib import Path
import zipfile

import numpy as np
import pytest

import kikuchi_lab.spherical_intensity.oriented_bundle as bundle_module
from kikuchi_lab.artifacts import BundleExistsError, PartialBundleError
from kikuchi_lab.kinematical import load_kinematical_recipe
from kikuchi_lab.kinematical.kikuchipy_adapter import simulate_kinematical_arrays
from kikuchi_lab.model.identity import canonical_json, plain_data, stable_id
from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.near_depth import load_near_depth_recipe
from kikuchi_lab.sources.structure import load_structure_record
from kikuchi_lab.spherical_intensity.contracts import SphericalIntensityField
from kikuchi_lab.spherical_intensity.mapping import build_spherical_intensity
from kikuchi_lab.spherical_intensity.orientation import (
    load_oriented_spherical_recipe,
)
from kikuchi_lab.spherical_intensity.oriented_bundle import (
    write_oriented_spherical_bundle,
)
from kikuchi_lab.spherical_intensity.oriented_render import (
    OrientedSphericalRender,
    render_oriented_spherical,
)
from kikuchi_lab.spherical_intensity.presentation import build_presentation_source
from kikuchi_lab.spherical_intensity.recipe import load_spherical_intensity_recipe
from kikuchi_lab.spherical_intensity.rotation import rotate_spherical_field


ROOT = Path(__file__).parents[2]
ORIENTED_RECIPE = ROOT / "recipes/spherical/ice-ih-oriented-s2-proof.yml"
SOURCE_RECIPE = ROOT / "recipes/spherical/ice-ih-s2-intensity.yml"
PRESENTATION_RECIPE = ROOT / "recipes/presentation/ice-ih-near-depth-stepped-field-led.yml"
EXPECTED_FILES = {
    "data/oriented-s2-field.npz",
    "diagnostics/source-field-ledger.json",
    "diagnostics/orientation-ledger.json",
    "diagnostics/reprojection-ledger.json",
    "diagnostics/presentation-ledger.json",
    "diagnostics/figure-ledger.json",
    "diagnostics/stage-timing.json",
    "figures/identity-vs-oriented-upper.png",
    "figures/oriented-upper.png",
    "figures/oriented-lower.png",
    "figures/oriented-sphere-front.png",
    "figures/oriented-sphere-rear.png",
    "figures/orientation-axes.png",
    "recipes/oriented-spherical.json",
    "recipes/source-spherical.json",
    "recipes/presentation.json",
    "source/structure.json",
}
NPZ_MEMBERS = [
    "density_weight.npy",
    "hemisphere.npy",
    "intensity_normalized.npy",
    "intensity_raw.npy",
    "source_column.npy",
    "source_row.npy",
    "xyz_sample.npy",
]

pytestmark = [
    pytest.mark.filterwarnings("ignore:.*GetSpaceGroup.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*placeInLattice.*:DeprecationWarning"),
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _assert_plain(value: object) -> None:
    if isinstance(value, dict):
        assert all(isinstance(key, str) for key in value)
        for item in value.values():
            _assert_plain(item)
        return
    if isinstance(value, list):
        for item in value:
            _assert_plain(item)
        return
    assert value is None or type(value) in {str, bool, int, float}


def _rebuild_field(
    field: SphericalIntensityField,
    *,
    intensity_raw: np.ndarray | None = None,
) -> SphericalIntensityField:
    return SphericalIntensityField.from_columns(
        xyz=field.xyz,
        hemisphere=field.hemisphere,
        source_row=field.source_row,
        source_column=field.source_column,
        intensity_raw=field.intensity_raw if intensity_raw is None else intensity_raw,
        intensity_normalized=field.intensity_normalized,
        density_weight=field.density_weight,
        metadata=field.metadata_dict(),
    )


@pytest.fixture(scope="module")
def oriented_bundle_inputs():
    oriented_recipe = load_oriented_spherical_recipe(
        ORIENTED_RECIPE,
        profile="smoke",
    )
    oriented_recipe = replace(
        oriented_recipe,
        profile=replace(
            oriented_recipe.profile,
            figure_size_px=64,
            sphere_longitude_count=37,
            sphere_latitude_count=19,
            tile_rows=8,
        ),
    )
    source_recipe = load_spherical_intensity_recipe(SOURCE_RECIPE, profile="smoke")
    base_path = (SOURCE_RECIPE.parent / source_recipe.source_kinematical_recipe).resolve()
    base_recipe = replace(
        load_kinematical_recipe(base_path),
        half_size=32,
        figure_size_px=64,
    )
    source = load_structure_record((base_path.parent / base_recipe.source_record).resolve())
    simulation, context = simulate_kinematical_arrays(source, base_recipe)
    source_build = build_spherical_intensity(simulation, source, source_recipe)
    identity_field = rotate_spherical_field(
        source_build.field,
        Orientation((0.0, 0.0, 0.0)),
    )
    oriented_field = rotate_spherical_field(
        source_build.field,
        oriented_recipe.orientation,
    )
    presentation_recipe = load_near_depth_recipe(PRESENTATION_RECIPE)
    presentation_source = build_presentation_source(
        simulation.master_stereographic.intensity,
        context.master_simulator.reflectors,
        base_recipe,
        presentation_recipe,
    )
    render = render_oriented_spherical(presentation_source, oriented_recipe)
    return {
        "source_build": source_build,
        "identity_field": identity_field,
        "oriented_field": oriented_field,
        "render": render,
        "oriented_recipe": oriented_recipe,
        "source_recipe": source_recipe,
        "presentation_recipe": presentation_recipe,
        "presentation_source": presentation_source,
        "source": source,
        "stage_timing": {
            "schema_version": 1,
            "elapsed_seconds": 1.0,
            "stages": [{"name": "smoke", "elapsed_seconds": 0.75}],
        },
    }


def test_bundle_contains_canonical_inventory_ledgers_recipes_and_six_figures(
    oriented_bundle_inputs,
    tmp_path: Path,
) -> None:
    result = write_oriented_spherical_bundle(tmp_path, **oriented_bundle_inputs)
    manifest_path = result.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert set(manifest["files"]) == EXPECTED_FILES
    assert {
        str(path.relative_to(result.path)) for path in result.path.rglob("*") if path.is_file()
    } == EXPECTED_FILES | {"manifest.json"}
    assert manifest_path.read_text(encoding="utf-8") == canonical_json(manifest)
    assert result.run_id == stable_id("oriented-spherical-run", manifest["run_identity"])
    assert result.path == tmp_path / result.run_id
    assert result.manifest_sha256 == _sha256(manifest_path)
    for relative, record in manifest["files"].items():
        path = result.path / relative
        assert record == {"bytes": path.stat().st_size, "sha256": _sha256(path)}

    with pytest.raises(BundleExistsError, match="completed bundle already exists"):
        write_oriented_spherical_bundle(tmp_path, **oriented_bundle_inputs)


def test_bundle_npz_has_exact_sorted_members_metadata_dtypes_values_and_hashes(
    oriented_bundle_inputs,
    tmp_path: Path,
) -> None:
    result = write_oriented_spherical_bundle(tmp_path, **oriented_bundle_inputs)
    path = result.path / "data/oriented-s2-field.npz"
    field = oriented_bundle_inputs["oriented_field"].field

    with zipfile.ZipFile(path) as archive:
        assert archive.namelist() == NPZ_MEMBERS
        for info in archive.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.compress_type == zipfile.ZIP_DEFLATED
            assert info.create_system == 3
            assert info.external_attr == 0o600 << 16
    with np.load(path, allow_pickle=False) as archive:
        expected = {
            "density_weight": ("<f8", field.density_weight),
            "hemisphere": ("|i1", field.hemisphere),
            "intensity_normalized": ("<f8", field.intensity_normalized),
            "intensity_raw": ("<f4", field.intensity_raw),
            "source_column": ("<i4", field.source_column),
            "source_row": ("<i4", field.source_row),
            "xyz_sample": ("<f8", field.xyz),
        }
        assert archive.files == [name.removesuffix(".npy") for name in NPZ_MEMBERS]
        for name, (dtype, values) in expected.items():
            assert archive[name].dtype.str == dtype
            np.testing.assert_array_equal(archive[name], values)

    manifest = json.loads((result.path / "manifest.json").read_text())
    assert manifest["files"]["data/oriented-s2-field.npz"]["sha256"] == _sha256(path)
    assert manifest["run_identity"]["oriented_channel_sha256"] == dict(field.channel_sha256)


def test_bundle_is_byte_deterministic_across_empty_output_roots(
    oriented_bundle_inputs,
    tmp_path: Path,
) -> None:
    first = write_oriented_spherical_bundle(
        tmp_path / "first",
        **oriented_bundle_inputs,
    )
    second = write_oriented_spherical_bundle(
        tmp_path / "second",
        **oriented_bundle_inputs,
    )

    assert first.run_id == second.run_id
    assert first.manifest_sha256 == second.manifest_sha256
    assert _file_hashes(first.path) == _file_hashes(second.path)


def test_run_identity_binds_source_recipes_fields_orientation_figures_and_presentation(
    oriented_bundle_inputs,
    tmp_path: Path,
) -> None:
    result = write_oriented_spherical_bundle(tmp_path, **oriented_bundle_inputs)
    manifest = json.loads((result.path / "manifest.json").read_text())
    identity = manifest["run_identity"]
    source_build = oriented_bundle_inputs["source_build"]
    identity_field = oriented_bundle_inputs["identity_field"]
    oriented_field = oriented_bundle_inputs["oriented_field"]
    render = oriented_bundle_inputs["render"]
    source = oriented_bundle_inputs["source"]

    assert identity["oriented_recipe_id"] == oriented_bundle_inputs["oriented_recipe"].recipe_id
    assert identity["source_recipe_id"] == oriented_bundle_inputs["source_recipe"].recipe_id
    assert (
        identity["presentation_recipe_id"]
        == oriented_bundle_inputs["presentation_recipe"].recipe_id
    )
    assert identity["presentation_ledger_id"] == stable_id(
        "presentation-ledger",
        oriented_bundle_inputs["presentation_source"].ledger,
    )
    assert identity["source_id"] == source.source_record.source_id
    assert identity["source_sha256"] == source.sha256
    assert identity["source_field_id"] == source_build.field.field_id
    assert identity["identity_field_id"] == identity_field.field.field_id
    assert identity["oriented_field_id"] == oriented_field.field.field_id
    assert identity["orientation_id"] == oriented_field.orientation_id
    assert identity["oriented_channel_sha256"] == dict(oriented_field.field.channel_sha256)
    assert identity["figure_sha256"] == {
        name: hashlib.sha256(payload).hexdigest()
        for name, payload in sorted(render.figures.items())
    }
    assert "stage_timing" not in identity
    assert "elapsed_seconds" not in identity


def test_ledgers_are_deep_plain_canonical_snapshots(
    oriented_bundle_inputs,
    tmp_path: Path,
) -> None:
    result = write_oriented_spherical_bundle(tmp_path, **oriented_bundle_inputs)
    expected = {
        "orientation-ledger.json": plain_data(oriented_bundle_inputs["oriented_field"].ledger),
        "presentation-ledger.json": plain_data(
            oriented_bundle_inputs["presentation_source"].ledger
        ),
        "figure-ledger.json": plain_data(oriented_bundle_inputs["render"].ledger),
        "stage-timing.json": plain_data(oriented_bundle_inputs["stage_timing"]),
    }
    for name, expected_payload in expected.items():
        path = result.path / "diagnostics" / name
        payload = json.loads(path.read_text(encoding="utf-8"))
        _assert_plain(payload)
        assert payload == expected_payload
        assert path.read_text(encoding="utf-8") == canonical_json(payload)

    source_ledger = json.loads((result.path / "diagnostics/source-field-ledger.json").read_text())
    _assert_plain(source_ledger)
    assert source_ledger == {
        "field_id": oriented_bundle_inputs["source_build"].field.field_id,
        "channel_sha256": dict(oriented_bundle_inputs["source_build"].field.channel_sha256),
        "metadata": oriented_bundle_inputs["source_build"].field.metadata_dict(),
    }


def test_bundle_json_is_output_path_neutral_and_timing_is_diagnostic_only(
    oriented_bundle_inputs,
    tmp_path: Path,
) -> None:
    first = write_oriented_spherical_bundle(
        tmp_path / "root-a",
        **oriented_bundle_inputs,
    )
    changed = dict(oriented_bundle_inputs)
    changed["stage_timing"] = {"elapsed_seconds": 987.5, "worker": "diagnostic"}
    second = write_oriented_spherical_bundle(tmp_path / "root-b", **changed)

    assert first.run_id == second.run_id
    first_manifest = json.loads((first.path / "manifest.json").read_text())
    second_manifest = json.loads((second.path / "manifest.json").read_text())
    assert first_manifest["run_identity"] == second_manifest["run_identity"]
    assert first.manifest_sha256 != second.manifest_sha256
    assert _sha256(first.path / "diagnostics/stage-timing.json") != _sha256(
        second.path / "diagnostics/stage-timing.json"
    )

    for bundle in (first, second):
        for path in bundle.path.rglob("*.json"):
            text = path.read_text(encoding="utf-8")
            assert str(tmp_path) not in text
            assert str(ROOT) not in text


def test_recipe_and_source_snapshots_are_exact_and_no_csv_is_duplicated(
    oriented_bundle_inputs,
    tmp_path: Path,
) -> None:
    result = write_oriented_spherical_bundle(tmp_path, **oriented_bundle_inputs)

    assert (
        json.loads((result.path / "recipes/oriented-spherical.json").read_text())
        == oriented_bundle_inputs["oriented_recipe"].to_dict()
    )
    assert (
        json.loads((result.path / "recipes/source-spherical.json").read_text())
        == oriented_bundle_inputs["source_recipe"].to_dict()
    )
    assert (
        json.loads((result.path / "recipes/presentation.json").read_text())
        == oriented_bundle_inputs["presentation_recipe"].to_dict()
    )
    source = json.loads((result.path / "source/structure.json").read_text())
    assert source["source_id"] == oriented_bundle_inputs["source"].source_record.source_id
    assert source["sha256"] == oriented_bundle_inputs["source"].sha256
    assert source["phase"]["name"] == oriented_bundle_inputs["source"].name
    assert not list(result.path.rglob("*.csv"))


def test_all_identity_corruption_is_rejected_before_output_root_creation(
    oriented_bundle_inputs,
    tmp_path: Path,
) -> None:
    source_build = oriented_bundle_inputs["source_build"]
    oriented_field = oriented_bundle_inputs["oriented_field"]
    raw = oriented_field.field.intensity_raw.copy()
    raw[0] = np.nextafter(raw[0], np.float32(np.inf))
    corrupted_field = _rebuild_field(oriented_field.field, intensity_raw=raw)

    wrong_render_ledger = plain_data(oriented_bundle_inputs["render"].ledger)
    wrong_render_ledger["orientation_id"] = "orientation-wrong"
    corruptions = [
        (
            {"source": replace(oriented_bundle_inputs["source"], sha256="0" * 64)},
            "source field does not match the supplied structure source",
        ),
        (
            {
                "source_recipe": replace(
                    oriented_bundle_inputs["source_recipe"],
                    rng_seed=oriented_bundle_inputs["source_recipe"].rng_seed + 1,
                )
            },
            "source field does not match the supplied source recipe",
        ),
        (
            {
                "oriented_recipe": replace(
                    oriented_bundle_inputs["oriented_recipe"],
                    orientation=Orientation((18.0, 31.0, 43.0)),
                )
            },
            "oriented field does not match the supplied oriented recipe",
        ),
        (
            {
                "presentation_recipe": replace(
                    oriented_bundle_inputs["presentation_recipe"],
                    optical_depth_gain=(
                        oriented_bundle_inputs["presentation_recipe"].optical_depth_gain + 0.01
                    ),
                )
            },
            "presentation source does not match the supplied presentation recipe",
        ),
        (
            {
                "identity_field": rotate_spherical_field(
                    source_build.field,
                    Orientation((1.0, 2.0, 3.0)),
                )
            },
            "identity field does not use the identity orientation",
        ),
        (
            {
                "oriented_field": replace(
                    oriented_field,
                    field=corrupted_field,
                )
            },
            "oriented field ledger channel hashes are inconsistent",
        ),
        (
            {
                "render": OrientedSphericalRender(
                    figures=dict(oriented_bundle_inputs["render"].figures),
                    ledger=wrong_render_ledger,
                )
            },
            "render does not match the supplied orientation",
        ),
    ]

    for index, (changes, message) in enumerate(corruptions):
        inputs = dict(oriented_bundle_inputs)
        inputs.update(changes)
        root = tmp_path / f"invalid-{index}" / "runs"
        with pytest.raises(ValueError, match=message):
            write_oriented_spherical_bundle(root, **inputs)
        assert not root.exists()


def test_figure_ledger_recipe_corruption_is_rejected_before_filesystem_mutation(
    oriented_bundle_inputs,
    tmp_path: Path,
) -> None:
    ledger = plain_data(oriented_bundle_inputs["render"].ledger)
    ledger["sphere_mesh"]["latitude_count"] += 2
    inputs = dict(oriented_bundle_inputs)
    inputs["render"] = OrientedSphericalRender(
        figures=dict(oriented_bundle_inputs["render"].figures),
        ledger=ledger,
    )
    root = tmp_path / "invalid-figure-ledger" / "runs"

    with pytest.raises(ValueError, match="render does not match the supplied"):
        write_oriented_spherical_bundle(root, **inputs)

    assert not root.exists()


def test_bundle_rejects_existing_partial_without_changing_it(
    oriented_bundle_inputs,
    tmp_path: Path,
) -> None:
    identity = write_oriented_spherical_bundle(
        tmp_path / "identity",
        **oriented_bundle_inputs,
    )
    root = tmp_path / "runs"
    root.mkdir()
    partial = root / f".{identity.run_id}.partial-fixed"
    partial.mkdir()
    evidence = partial / "evidence.txt"
    evidence.write_text("incomplete", encoding="utf-8")

    with pytest.raises(PartialBundleError, match="partial bundle already exists"):
        write_oriented_spherical_bundle(root, **oriented_bundle_inputs)

    assert evidence.read_text(encoding="utf-8") == "incomplete"
    assert not (root / identity.run_id).exists()
    assert not (root / f".{identity.run_id}.publishing").exists()


def test_bundle_rejects_foreign_publication_owner_without_removing_it(
    oriented_bundle_inputs,
    tmp_path: Path,
) -> None:
    identity = write_oriented_spherical_bundle(
        tmp_path / "identity",
        **oriented_bundle_inputs,
    )
    root = tmp_path / "runs"
    root.mkdir()
    owner = root / f".{identity.run_id}.publishing"
    owner.mkdir()

    with pytest.raises(PartialBundleError, match="publication already in progress"):
        write_oriented_spherical_bundle(root, **oriented_bundle_inputs)

    assert owner.is_dir()
    assert list(root.iterdir()) == [owner]


def test_mid_write_failure_keeps_partial_removes_owner_and_never_promotes(
    oriented_bundle_inputs,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = write_oriented_spherical_bundle(
        tmp_path / "identity",
        **oriented_bundle_inputs,
    )
    root = tmp_path / "runs"
    root.mkdir()
    real_write_json = bundle_module._write_json

    def fail_manifest(path: Path, value: object) -> None:
        if path.name == "manifest.json":
            raise OSError("injected manifest write failure")
        real_write_json(path, value)

    monkeypatch.setattr(bundle_module, "_write_json", fail_manifest)
    with pytest.raises(OSError, match="injected manifest write failure"):
        write_oriented_spherical_bundle(root, **oriented_bundle_inputs)

    assert not (root / identity.run_id).exists()
    partials = list(root.glob(f".{identity.run_id}.partial-*"))
    assert len(partials) == 1
    assert (partials[0] / "data/oriented-s2-field.npz").is_file()
    assert not (root / f".{identity.run_id}.publishing").exists()


def test_atomic_promotion_collision_preserves_rival_and_recoverable_partial(
    oriented_bundle_inputs,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = write_oriented_spherical_bundle(
        tmp_path / "identity",
        **oriented_bundle_inputs,
    )
    root = tmp_path / "runs"
    root.mkdir()
    destination = root / identity.run_id

    def inject_rival(source: Path, target: Path) -> None:
        assert target == destination
        target.mkdir()
        (target / "rival.txt").write_text("rival", encoding="utf-8")
        raise OSError(errno.EEXIST, "injected no-replace collision")

    monkeypatch.setattr(bundle_module, "_promote_directory_no_replace", inject_rival)
    with pytest.raises(BundleExistsError, match="completed bundle already exists"):
        write_oriented_spherical_bundle(root, **oriented_bundle_inputs)

    assert (destination / "rival.txt").read_text(encoding="utf-8") == "rival"
    partials = list(root.glob(f".{identity.run_id}.partial-*"))
    assert len(partials) == 1
    assert (partials[0] / "manifest.json").is_file()
    assert not (root / f".{identity.run_id}.publishing").exists()
