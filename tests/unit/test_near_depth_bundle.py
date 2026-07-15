from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.artifacts import BundleExistsError
from kikuchi_lab.kinematical import (
    KinematicalArrayProduct,
    KinematicalSimulation,
    load_kinematical_recipe,
)
from kikuchi_lab.model.identity import canonical_json, stable_id
from kikuchi_lab.near_depth import load_near_depth_recipe
from kikuchi_lab.near_depth.bundle import write_near_depth_bundle
from kikuchi_lab.near_depth.overlap import OverlapField
from kikuchi_lab.near_depth.render import NearDepthRender
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases" / "ice-ih" / "source.yml"
BASE_RECIPE = ROOT / "recipes" / "kinematical" / "ice-ih-oxygen-quiet-proof.yml"
TREATMENT_RECIPE = (
    ROOT / "recipes" / "presentation" / "ice-ih-near-depth-stepped.yml"
)


@pytest.fixture
def bundle_inputs():
    source = load_structure_record(SOURCE)
    base = load_kinematical_recipe(BASE_RECIPE)
    treatment = load_near_depth_recipe(TREATMENT_RECIPE)
    metadata = {
        "source_id": source.source_record.source_id,
        "source_sha256": source.sha256,
        "recipe_id": base.recipe_id,
        "projection": "stereographic",
        "hemisphere": "both",
    }
    master = KinematicalArrayProduct.from_array(
        "master-stereographic",
        np.zeros((2, 5, 5), dtype=np.float32),
        metadata=metadata,
    )
    simulation = KinematicalSimulation(
        master_stereographic=master,
        master_lambert=KinematicalArrayProduct.from_array(
            "master-lambert",
            np.zeros((2, 5, 5), dtype=np.float32),
            metadata={**metadata, "projection": "lambert-square-equal-area"},
        ),
        detector=KinematicalArrayProduct.from_array(
            "detector",
            np.zeros((4, 6), dtype=np.float32),
            metadata={**metadata, "projection": "gnomonic"},
        ),
        reflector_catalog={},
        projection_ledger={"frames": {"crystal": "test crystal frame"}},
    )
    raw = np.zeros((5, 5), dtype=np.float32)
    raw[2, 2] = 0.25
    overlap = OverlapField(
        raw=raw,
        normalized=np.clip(raw / 0.25, 0, 1),
        valid_disk=np.ones((5, 5), dtype=bool),
        normalization_value=0.25,
        axial_band_count=3,
        metadata={"membership_equation": "abs(dot(direction, normal)) <= sin(theta_B)"},
    )
    render = NearDepthRender(
        figures={
            "etched-master-near-depth-stepped.png": b"depth-png",
            "quiet-vs-near-depth-stepped.png": b"comparison-png",
        },
        diagnostic_png=b"diagnostic-png",
        ledger={
            "schema_version": 1,
            "base_recipe_id": base.recipe_id,
            "treatment_recipe_id": treatment.recipe_id,
        },
    )
    return render, overlap, simulation, treatment, base, source


def test_depth_bundle_has_complete_content_addressed_inventory(
    tmp_path: Path,
    bundle_inputs,
) -> None:
    result = write_near_depth_bundle(tmp_path, *bundle_inputs)
    manifest_path = result.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["run_id"] == stable_id("near-depth-run", manifest["run_identity"])
    assert result.run_id == manifest["run_id"]
    assert result.manifest_sha256 == hashlib.sha256(
        manifest_path.read_bytes()
    ).hexdigest()
    assert set(manifest["files"]) == {
        "figures/etched-master-near-depth-stepped.png",
        "figures/quiet-vs-near-depth-stepped.png",
        "diagnostics/overlap-additional-depth.npy",
        "diagnostics/overlap-additional-depth.png",
        "diagnostics/depth-render-ledger.json",
        "recipes/near-depth.json",
    }
    for name, record in manifest["files"].items():
        path = result.path / name
        assert record == {
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    assert manifest_path.read_text(encoding="utf-8") == canonical_json(manifest)


def test_depth_bundle_identity_links_base_source_product_and_overlap(
    tmp_path: Path,
    bundle_inputs,
) -> None:
    render, overlap, simulation, treatment, base, source = bundle_inputs
    result = write_near_depth_bundle(
        tmp_path,
        render,
        overlap,
        simulation,
        treatment,
        base,
        source,
    )
    manifest = json.loads((result.path / "manifest.json").read_text(encoding="utf-8"))
    identity = manifest["run_identity"]

    assert identity["treatment_recipe_id"] == treatment.recipe_id
    assert identity["base_recipe_id"] == base.recipe_id
    assert identity["source_id"] == source.source_record.source_id
    assert identity["source_sha256"] == source.sha256
    assert identity["base_stereographic_product_id"] == (
        simulation.master_stereographic.product_id
    )
    assert identity["base_stereographic_array_sha256"] == (
        simulation.master_stereographic.array_sha256
    )
    assert identity["overlap_raw_sha256"] == hashlib.sha256(
        overlap.raw.tobytes(order="C")
    ).hexdigest()
    assert json.loads(
        (result.path / "recipes" / "near-depth.json").read_text(encoding="utf-8")
    ) == treatment.to_dict()


def test_depth_bundle_refuses_to_replace_same_completed_run(
    tmp_path: Path,
    bundle_inputs,
) -> None:
    write_near_depth_bundle(tmp_path, *bundle_inputs)

    with pytest.raises(BundleExistsError, match="completed bundle already exists"):
        write_near_depth_bundle(tmp_path, *bundle_inputs)
