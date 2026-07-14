from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier, Event, Thread

import imageio.v3 as iio
import numpy as np
import pytest

import kikuchi_lab.kinematical.bundle as bundle_module
from kikuchi_lab.artifacts import BundleExistsError, PartialBundleError
from kikuchi_lab.kinematical import (
    KinematicalArrayProduct,
    KinematicalExecution,
    KinematicalSimulation,
    load_kinematical_recipe,
)
from kikuchi_lab.kinematical.bundle import write_kinematical_bundle
from kikuchi_lab.model.identity import canonical_json, stable_id
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/forsterite/source.yml"
RECIPE = ROOT / "recipes/kinematical/forsterite-etched-master.yml"
EXPECTED = {
    "provenance/source.json",
    "recipes/kinematical.json",
    "models/reflection-catalog.json",
    "diagnostics/projection-ledger.json",
    "products/kinematical-master-stereographic.npy",
    "products/kinematical-master-stereographic.png",
    "products/kinematical-master-lambert.npy",
    "products/kinematical-master-lambert.png",
    "products/kinematical-detector.npy",
    "products/kinematical-detector.png",
    "figures/kinematical-stereographic-bands.svg",
    "figures/kinematical-spherical-bands.png",
    "figures/kinematical-detector-overlay.png",
    "figures/etched-master-balanced.png",
    "figures/etched-master-quiet.png",
    "figures/reflector-selection.png",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_kinematical_package_exports_the_bundle_interface() -> None:
    import kikuchi_lab.kinematical as kinematical

    assert kinematical.KinematicalBundleResult.__name__ == "KinematicalBundleResult"
    assert kinematical.write_kinematical_bundle is write_kinematical_bundle


def _product(
    label: str, values: np.ndarray, *, hemisphere: str | None = None
) -> KinematicalArrayProduct:
    metadata = {"projection": label, "fixture": "real-owned-array"}
    if hemisphere is not None:
        metadata["hemisphere"] = hemisphere
    return KinematicalArrayProduct.from_array(
        label,
        values,
        metadata=metadata,
    )


def fixture_recipe():
    loaded = load_kinematical_recipe(RECIPE)
    return replace(
        loaded,
        half_size=2,
        detector=replace(loaded.detector, shape=(3, 4)),
        figure_size_px=32,
    )


def test_recipe_scientific_identity_excludes_the_source_record_locator() -> None:
    first = replace(fixture_recipe(), source_record="../../phases/forsterite/source.yml")
    second = replace(fixture_recipe(), source_record="../relocated/source.yml")

    assert first.to_dict()["source_record"] != second.to_dict()["source_record"]
    assert first.recipe_id == second.recipe_id


def fixture_source():
    return load_structure_record(SOURCE)


def fixture_execution() -> KinematicalExecution:
    upper_stereo = np.arange(9, dtype=np.float32).reshape(3, 3)
    lower_stereo = np.arange(20, 29, dtype=np.float32).reshape(3, 3)
    upper_lambert = np.array(
        [[0.0, 1.0, 4.0], [9.0, 16.0, 25.0], [36.0, 49.0, 64.0]],
        dtype=np.float32,
    )
    lower_lambert = upper_lambert + 100.0
    simulation = KinematicalSimulation(
        master_stereographic=_product(
            "master-stereographic",
            np.stack((upper_stereo, lower_stereo)),
            hemisphere="both",
        ),
        master_lambert=_product(
            "master-lambert",
            np.stack((upper_lambert, lower_lambert)),
            hemisphere="both",
        ),
        detector=_product("detector", np.arange(12, dtype=np.float32).reshape(3, 4)),
        reflector_catalog={
            "master": {"relative_factor": 0.03, "retained_count": 2},
            "overlays": {
                "balanced": {"relative_factor": 0.14, "retained_count": 1},
                "quiet": {"relative_factor": 0.22, "retained_count": 1},
            },
        },
        projection_ledger={
            "schema_version": 1,
            "projections": {
                "stereographic": {"hemisphere_order": ["upper", "lower"]},
                "lambert": {"hemisphere_order": ["upper", "lower"]},
                "detector": {"projection": "gnomonic"},
            },
        },
    )
    figures = {
        "kinematical-stereographic-bands.svg": b"<svg><path/></svg>",
        "kinematical-spherical-bands.png": b"spherical-png",
        "kinematical-detector-overlay.png": b"detector-overlay-png",
        "etched-master-balanced.png": b"balanced-png",
        "etched-master-quiet.png": b"quiet-png",
        "reflector-selection.png": b"selection-png",
    }
    return KinematicalExecution(simulation=simulation, figures=figures)


def single_hemisphere_execution(hemisphere: str) -> KinematicalExecution:
    both = fixture_execution()
    plane_index = {"upper": 0, "lower": 1}[hemisphere]
    simulation = KinematicalSimulation(
        master_stereographic=_product(
            "master-stereographic",
            both.simulation.master_stereographic.intensity[plane_index],
            hemisphere=hemisphere,
        ),
        master_lambert=_product(
            "master-lambert",
            both.simulation.master_lambert.intensity[plane_index],
            hemisphere=hemisphere,
        ),
        detector=both.simulation.detector,
        reflector_catalog=both.simulation.reflector_catalog,
        projection_ledger={
            "schema_version": 1,
            "projections": {
                "stereographic": {
                    "hemisphere": hemisphere,
                    "hemisphere_order": [hemisphere],
                },
                "lambert": {
                    "hemisphere": hemisphere,
                    "hemisphere_order": [hemisphere],
                },
                "detector": {"projection": "gnomonic"},
            },
        },
    )
    return KinematicalExecution(simulation=simulation, figures=both.figures)


def slow_fixture_execution() -> KinematicalExecution:
    execution = fixture_execution()
    figures = dict(execution.figures)
    figures["kinematical-stereographic-bands.svg"] = b"<svg>" + b" " * (8 * 1024 * 1024)
    return KinematicalExecution(simulation=execution.simulation, figures=figures)


def test_kinematical_bundle_has_canonical_inventory_and_hashes(tmp_path: Path) -> None:
    execution = fixture_execution()
    recipe = fixture_recipe()
    source = fixture_source()

    result = write_kinematical_bundle(tmp_path, execution, recipe, source)

    manifest_path = result.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_path.read_text(encoding="utf-8") == canonical_json(manifest)
    assert set(manifest["files"]) == EXPECTED
    assert {
        str(path.relative_to(result.path)) for path in result.path.rglob("*") if path.is_file()
    } == EXPECTED | {"manifest.json"}
    for relative, record in manifest["files"].items():
        assert record == {
            "sha256": _sha256(result.path / relative),
            "bytes": (result.path / relative).stat().st_size,
        }
    assert result.manifest_sha256 == _sha256(manifest_path)
    serialized_recipe = json.loads(
        (result.path / "recipes/kinematical.json").read_text(encoding="utf-8")
    )
    assert serialized_recipe["source_record"] == recipe.source_record

    run_identity = {
        "schema_version": 1,
        "recipe_id": recipe.recipe_id,
        "source_id": source.source_record.source_id,
        "source_sha256": source.sha256,
        "products": {
            label: {
                "product_id": product.product_id,
                "array_sha256": product.array_sha256,
            }
            for label, product in execution.simulation.products().items()
        },
        "reflection_catalog_id": stable_id(
            "reflection-catalog", execution.simulation.reflector_catalog
        ),
        "projection_ledger_id": stable_id(
            "projection-ledger", execution.simulation.projection_ledger
        ),
    }
    assert manifest["run_identity"] == run_identity
    assert result.run_id == stable_id("kinematical-run", run_identity)
    assert result.path == tmp_path / result.run_id


def test_bundle_previews_map_each_hemisphere_pointwise_without_mutating_products(
    tmp_path: Path,
) -> None:
    execution = fixture_execution()
    originals = {
        label: product.intensity.copy()
        for label, product in execution.simulation.products().items()
    }

    result = write_kinematical_bundle(tmp_path, execution, fixture_recipe(), fixture_source())

    manifest = json.loads((result.path / "manifest.json").read_text(encoding="utf-8"))
    for label in ("master-stereographic", "master-lambert"):
        relative = f"products/kinematical-{label}.png"
        preview = iio.imread(result.path / relative)
        source_array = originals[label]
        assert preview.shape == (
            source_array.shape[1],
            source_array.shape[2] * 2,
        )
        export = manifest["png_exports"][relative]
        assert export["hemisphere_order"] == ["upper", "lower"]
        assert [plane["hemisphere"] for plane in export["planes"]] == [
            "upper",
            "lower",
        ]
        for index, plane in enumerate(export["planes"]):
            values = source_array[index]
            expected = np.rint(
                np.clip(
                    (values.astype(np.float64) - plane["black_point"])
                    / (plane["white_point"] - plane["black_point"]),
                    0.0,
                    1.0,
                )
                * 65535.0
            ).astype(np.uint16)
            start = index * values.shape[1]
            np.testing.assert_array_equal(preview[:, start : start + values.shape[1]], expected)
        np.testing.assert_array_equal(
            np.load(result.path / f"products/kinematical-{label}.npy"),
            source_array,
        )
    for label, before in originals.items():
        np.testing.assert_array_equal(execution.simulation.products()[label].intensity, before)


def test_kinematical_bundle_reproduces_identity_and_bytes_in_separate_roots(
    tmp_path: Path,
) -> None:
    execution = fixture_execution()
    first = write_kinematical_bundle(
        tmp_path / "first", execution, fixture_recipe(), fixture_source()
    )
    second = write_kinematical_bundle(
        tmp_path / "second", execution, fixture_recipe(), fixture_source()
    )

    assert first.run_id == second.run_id
    assert first.manifest_sha256 == second.manifest_sha256
    first_files = {
        str(path.relative_to(first.path)): _sha256(path)
        for path in first.path.rglob("*")
        if path.is_file()
    }
    second_files = {
        str(path.relative_to(second.path)): _sha256(path)
        for path in second.path.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files


def test_kinematical_bundle_rejects_complete_destination_without_changing_it(
    tmp_path: Path,
) -> None:
    execution = fixture_execution()
    first = write_kinematical_bundle(tmp_path, execution, fixture_recipe(), fixture_source())
    before = {
        str(path.relative_to(first.path)): _sha256(path)
        for path in first.path.rglob("*")
        if path.is_file()
    }

    with pytest.raises(BundleExistsError, match="completed.*already exists"):
        write_kinematical_bundle(tmp_path, execution, fixture_recipe(), fixture_source())

    after = {
        str(path.relative_to(first.path)): _sha256(path)
        for path in first.path.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_kinematical_bundle_rejects_existing_partial_and_leaves_it_untouched(
    tmp_path: Path,
) -> None:
    execution = fixture_execution()
    identity = write_kinematical_bundle(
        tmp_path / "identity", execution, fixture_recipe(), fixture_source()
    )
    destination = tmp_path / "runs"
    destination.mkdir()
    partial = destination / f".{identity.run_id}.partial-fixed"
    partial.mkdir()
    evidence = partial / "evidence.txt"
    evidence.write_text("incomplete evidence", encoding="utf-8")

    with pytest.raises(PartialBundleError, match="partial.*already exists"):
        write_kinematical_bundle(destination, execution, fixture_recipe(), fixture_source())

    assert evidence.read_text(encoding="utf-8") == "incomplete evidence"
    assert not (destination / identity.run_id).exists()
    assert list(destination.iterdir()) == [partial]


def test_two_simultaneous_writers_have_one_exclusive_owner_and_one_specific_collision(
    tmp_path: Path,
) -> None:
    execution = slow_fixture_execution()
    recipe = fixture_recipe()
    source = fixture_source()
    start = Barrier(2)
    stop_monitor = Event()
    ownership_observed = Event()

    def monitor_ownership() -> None:
        while not stop_monitor.wait(0.001):
            if list(tmp_path.glob(".kinematical-run-*.publishing")):
                ownership_observed.set()

    def publish():
        start.wait(timeout=5.0)
        try:
            return write_kinematical_bundle(tmp_path, execution, recipe, source)
        except Exception as error:
            return error

    monitor = Thread(target=monitor_ownership)
    monitor.start()
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(publish) for _ in range(2)]
        outcomes = [future.result(timeout=15.0) for future in futures]
    stop_monitor.set()
    monitor.join(timeout=5.0)
    assert not monitor.is_alive()

    publications = [outcome for outcome in outcomes if not isinstance(outcome, Exception)]
    collisions = [outcome for outcome in outcomes if isinstance(outcome, Exception)]
    assert ownership_observed.is_set()
    assert len(publications) == 1
    assert len(collisions) == 1
    assert type(collisions[0]) is PartialBundleError
    assert "publication already in progress" in str(collisions[0])
    winner = publications[0]
    assert winner.path == tmp_path / winner.run_id
    manifest = json.loads((winner.path / "manifest.json").read_text(encoding="utf-8"))
    for relative, record in manifest["files"].items():
        assert record["sha256"] == _sha256(winner.path / relative)
    assert not list(tmp_path.glob(f".{winner.run_id}.partial-*"))
    assert not list(tmp_path.glob(f".{winner.run_id}.publishing"))


def test_mid_write_failure_keeps_partial_removes_owner_and_never_promotes(
    tmp_path: Path,
) -> None:
    recipe = fixture_recipe()
    source = fixture_source()
    execution = slow_fixture_execution()
    identity = write_kinematical_bundle(tmp_path / "identity", fixture_execution(), recipe, source)
    runs = tmp_path / "runs"
    runs.mkdir()
    sabotage_errors: list[BaseException] = []

    def obstruct_manifest() -> None:
        deadline = time.monotonic() + 5.0
        ownership = runs / f".{identity.run_id}.publishing"
        while time.monotonic() < deadline:
            partials = list(runs.glob(f".{identity.run_id}.partial-*"))
            if ownership.is_dir() and len(partials) == 1:
                try:
                    (partials[0] / "manifest.json").mkdir()
                except BaseException as error:
                    sabotage_errors.append(error)
                return
            time.sleep(0.001)
        sabotage_errors.append(AssertionError("publication ownership was not observable"))

    sabotage = Thread(target=obstruct_manifest)
    sabotage.start()
    with pytest.raises(IsADirectoryError):
        write_kinematical_bundle(runs, execution, recipe, source)
    sabotage.join(timeout=6.0)

    assert not sabotage.is_alive()
    assert sabotage_errors == []
    assert not (runs / identity.run_id).exists()
    partials = list(runs.glob(f".{identity.run_id}.partial-*"))
    assert len(partials) == 1
    assert (partials[0] / "manifest.json").is_dir()
    assert not (runs / f".{identity.run_id}.publishing").exists()
    with pytest.raises(PartialBundleError, match="partial.*already exists"):
        write_kinematical_bundle(runs, fixture_execution(), recipe, source)


def test_final_boundary_exclusive_promotion_preserves_injected_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    execution = fixture_execution()
    recipe = fixture_recipe()
    source = fixture_source()
    identity = write_kinematical_bundle(tmp_path / "identity", execution, recipe, source)
    runs = tmp_path / "runs"
    runs.mkdir()
    destination = runs / identity.run_id
    boundary_calls = 0
    sentinel_inode: int | None = None
    real_no_replace = getattr(bundle_module, "_promote_directory_no_replace", None)
    real_rename = Path.rename

    def inject_destination(source_path: Path, destination_path: Path) -> None:
        nonlocal boundary_calls, sentinel_inode
        boundary_calls += 1
        destination_path.mkdir()
        sentinel_inode = destination_path.stat().st_ino
        if real_no_replace is None:
            real_rename(source_path, destination_path)
        else:
            real_no_replace(source_path, destination_path)

    if real_no_replace is None:
        monkeypatch.setattr(Path, "rename", inject_destination)
    else:
        monkeypatch.setattr(bundle_module, "_promote_directory_no_replace", inject_destination)

    with pytest.raises(BundleExistsError, match="completed.*already exists"):
        write_kinematical_bundle(runs, execution, recipe, source)

    assert boundary_calls == 1
    assert sentinel_inode is not None
    assert destination.is_dir()
    assert destination.stat().st_ino == sentinel_inode
    assert list(destination.iterdir()) == []
    partials = list(runs.glob(f".{identity.run_id}.partial-*"))
    assert len(partials) == 1
    assert (partials[0] / "manifest.json").is_file()
    assert not (runs / f".{identity.run_id}.publishing").exists()


def test_initial_owner_fsync_failure_removes_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    execution = fixture_execution()
    recipe = fixture_recipe()
    source = fixture_source()
    identity = write_kinematical_bundle(tmp_path / "identity", execution, recipe, source)
    runs = tmp_path / "runs"
    runs.mkdir()
    failed_once = False
    real_fsync_directory = bundle_module._fsync_directory

    def fail_initial_root_fsync(path: Path) -> None:
        nonlocal failed_once
        if path == runs and not failed_once:
            failed_once = True
            raise OSError("injected initial output-root fsync failure")
        real_fsync_directory(path)

    monkeypatch.setattr(bundle_module, "_fsync_directory", fail_initial_root_fsync)

    with pytest.raises(OSError, match="injected initial output-root fsync failure"):
        write_kinematical_bundle(runs, execution, recipe, source)

    assert failed_once is True
    assert not (runs / identity.run_id).exists()
    assert not list(runs.glob(f".{identity.run_id}.partial-*"))
    assert not (runs / f".{identity.run_id}.publishing").exists()


@pytest.mark.parametrize("hemisphere", ["upper", "lower"])
def test_rank_two_master_preview_records_its_single_hemisphere(
    tmp_path: Path, hemisphere: str
) -> None:
    execution = single_hemisphere_execution(hemisphere)
    recipe = replace(fixture_recipe(), hemisphere=hemisphere)

    result = write_kinematical_bundle(tmp_path, execution, recipe, fixture_source())

    manifest = json.loads((result.path / "manifest.json").read_text(encoding="utf-8"))
    ledger = json.loads(
        (result.path / "diagnostics/projection-ledger.json").read_text(encoding="utf-8")
    )
    for label, projection in (
        ("master-stereographic", "stereographic"),
        ("master-lambert", "lambert"),
    ):
        product = execution.simulation.products()[label]
        np.testing.assert_array_equal(
            np.load(result.path / f"products/kinematical-{label}.npy"),
            product.intensity,
        )
        preview = iio.imread(result.path / f"products/kinematical-{label}.png")
        assert preview.shape == product.intensity.shape
        assert ledger["projections"][projection]["hemisphere_order"] == [hemisphere]
        export = manifest["png_exports"][f"products/kinematical-{label}.png"]
        assert export["hemisphere_order"] == [hemisphere]
        assert [plane["hemisphere"] for plane in export["planes"]] == [hemisphere]


def test_master_preview_rejects_metadata_and_ledger_hemisphere_disagreement(
    tmp_path: Path,
) -> None:
    upper = single_hemisphere_execution("upper")
    simulation = KinematicalSimulation(
        master_stereographic=upper.simulation.master_stereographic,
        master_lambert=upper.simulation.master_lambert,
        detector=upper.simulation.detector,
        reflector_catalog=upper.simulation.reflector_catalog,
        projection_ledger={
            "schema_version": 1,
            "projections": {
                "stereographic": {"hemisphere_order": ["lower"]},
                "lambert": {"hemisphere_order": ["upper"]},
                "detector": {"projection": "gnomonic"},
            },
        },
    )
    execution = KinematicalExecution(simulation=simulation, figures=upper.figures)

    with pytest.raises(ValueError, match="metadata.*projection ledger"):
        write_kinematical_bundle(
            tmp_path,
            execution,
            replace(fixture_recipe(), hemisphere="upper"),
            fixture_source(),
        )
