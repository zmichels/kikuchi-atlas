from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import imageio.v3 as iio
import numpy as np
import pytest

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


def _product(label: str, values: np.ndarray) -> KinematicalArrayProduct:
    return KinematicalArrayProduct.from_array(
        label,
        values,
        metadata={"projection": label, "fixture": "real-owned-array"},
    )


def fixture_recipe():
    loaded = load_kinematical_recipe(RECIPE)
    return replace(
        loaded,
        half_size=2,
        detector=replace(loaded.detector, shape=(3, 4)),
        figure_size_px=32,
    )


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
            "master-stereographic", np.stack((upper_stereo, lower_stereo))
        ),
        master_lambert=_product("master-lambert", np.stack((upper_lambert, lower_lambert))),
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
