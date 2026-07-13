from __future__ import annotations

import hashlib
import json
from pathlib import Path

import imageio.v3 as iio
import numpy as np

from kikuchi_lab.model import (
    DetectorPatternProduct,
    MasterPatternProduct,
    SourceRecord,
    save_master_product,
    stable_id,
)
from kikuchi_lab.model.identity import canonical_json
from kikuchi_lab.workflows.proof import render_proof


ROOT = Path(__file__).parents[2]


def _canonical_master(source_sha256: str = "1" * 64) -> MasterPatternProduct:
    y, x = np.mgrid[-1:1:33j, -1:1:33j]
    source = SourceRecord(
        uri="https://example.invalid/forsterite.cif",
        sha256=source_sha256,
        license="CC0-1.0",
        citation="Deterministic proof-workflow fixture.",
    )
    recipe_content = {"fixture": "proof", "voltage_kv": 20.0}
    recipe_sha256 = hashlib.sha256(canonical_json(recipe_content).encode()).hexdigest()
    recipe_id = f"recipe-{recipe_sha256[:16]}"
    return MasterPatternProduct.from_array(
        np.stack((10 + x + y, 9 - x + 0.5 * y)),
        metadata={
            "phase": {
                "name": "forsterite",
                "formula": "Mg2SiO4",
                "space_group": {"number": 62, "setting": "P n m a"},
                "lattice": {
                    "values": [10.207, 5.980, 4.756, 90.0, 90.0, 90.0],
                    "units": "angstrom",
                },
            },
            "source_structure": {
                "identifier": "proof-fixture",
                "sha256": source.sha256,
                "source_id": source.source_id,
                "provenance": source.to_dict(),
            },
            "generator": {"name": "test-fixture", "version": "1"},
            "simulation": {
                "recipe_id": recipe_id,
                "recipe_sha256": recipe_sha256,
                "voltage_kv": 20.0,
            },
            "projection": "Lambert square equal-area",
            "hemisphere_order": ["north", "south"],
            "energy_kev": 20.0,
            "intensity_units": "raw dynamical intensity",
            "coordinate_frame": "crystal:Pnma-derived-from-Pbnm",
            "provenance_links": [source.source_id, recipe_id],
        },
    )


def _fixture_projector(*, master, orientation, detector, energy_kev):
    height, width = detector.supersampled_shape
    y, x = np.mgrid[-1:1 : complex(height), -1:1 : complex(width)]
    phi1, phi, phi2 = np.deg2rad(orientation.euler_bunge_deg)
    image = (
        4.0
        + np.cos((5.0 + phi / np.pi) * x + phi1)
        + 0.6 * np.sin((7.0 + phi2 / np.pi) * y - phi2)
        + 0.25 * x * y
    ).astype(np.float32)
    metadata = {
        "intensity_units": "raw dynamical intensity",
        "detector_frame": "EDAX-TSL:RD-TD-ND",
        "energy_kev": energy_kev,
        "orientation": orientation.to_dict(),
        "detector": detector.to_dict(),
        "supersampling": detector.supersampling,
    }
    return DetectorPatternProduct.from_array(
        image,
        master_product_id=master.product_id,
        projection_recipe_id=detector.recipe_id,
        metadata=metadata,
    )


def _contains_decision_key(value: object) -> bool:
    forbidden = {"selected_candidate_id", "winner", "ranking", "score"}
    if isinstance(value, dict):
        return bool(forbidden.intersection(value)) or any(
            _contains_decision_key(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_decision_key(item) for item in value)
    return False


def test_proof_renders_every_candidate_under_one_comparison_contract(tmp_path: Path) -> None:
    source_path = tmp_path / "source" / "forsterite.cif"
    source_path.parent.mkdir()
    source_path.write_bytes(b"deterministic-forsterite-source")
    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    master = _canonical_master(source_sha256)
    master_bundle = tmp_path / "master.bundle"
    master_path = save_master_product(master_bundle / "master-product.npz", master)
    master_manifest = master_bundle / "master.manifest.json"
    master_manifest.write_text(
        canonical_json({"master_product_id": master.product_id, "schema_version": 1})
    )
    execution_context = {
        "software": {
            "kikuchi-lab": "0.1.0",
            "kikuchipy": "0.13.0",
            "scikit-image": "0.25.2",
            "numpy": "2.4.6",
            "orix": "0.14.1",
            "pillow": "12.3.0",
            "ebsdsim": "0.1.8",
            "wgpu": "0.31.1",
        },
        "doctor": {
            "ok": True,
            "checks": {
                "webgpu_adapter": {
                    "ok": True,
                    "observed": "fixture-adapter",
                    "details": {"backend_type": "TestBackend", "device": "Fixture GPU"},
                }
            },
        },
        "git": {
            "branch": "codex/test",
            "revision": "a" * 40,
            "dirty": False,
        },
    }
    invocation = [
        "kikuchi-lab",
        "proof",
        "--recipe",
        "recipes/proof/forsterite-proof.yml",
    ]
    first = render_proof(
        master=master,
        recipe_path=ROOT / "recipes/proof/forsterite-proof.yml",
        output_root=tmp_path / "first",
        projector=_fixture_projector,
        execution_context=execution_context,
        invocation=invocation,
        master_locator=master_path,
        source_locator=source_path,
    )
    second = render_proof(
        master=master,
        recipe_path=ROOT / "recipes/proof/forsterite-proof.yml",
        output_root=tmp_path / "second",
        projector=_fixture_projector,
        execution_context={
            **execution_context,
            "git": {**execution_context["git"], "dirty": True},
        },
        invocation=[*invocation, "--output", "/a/different/local/path"],
        master_locator=master_path,
        source_locator=source_path,
    )

    assert first.proof_id == second.proof_id
    assert first.candidate_ids == second.candidate_ids
    assert first.state == "awaiting-human-selection"
    assert len(first.candidate_ids) == 12

    manifest = json.loads((first.path / "manifest.json").read_text())
    assert manifest["proof_id"] == first.proof_id
    assert manifest["state"] == "awaiting-human-selection"
    assert manifest["candidate_order"] == list(first.candidate_ids)
    assert manifest["quality_grade"] == "proof"
    assert manifest["intended_use"] == "orientation-comparison"
    assert manifest["not_final_quality"] is True
    assert manifest["limitations"] == {
        "dmin_nm": 0.08,
        "energy_binwidth_kev": 20.0,
        "energy_integration": "one-bin",
        "rank": 8,
    }
    assert manifest["identity"]["quality_grade"] == "proof"
    assert manifest["identity"]["intended_use"] == "orientation-comparison"
    assert manifest["identity"]["not_final_quality"] is True
    assert manifest["identity"]["contact_sheet_contract"] == {
        "schema_version": 2,
        "processed_variant": "scientific-clean",
        "processing_recipe_id": manifest["comparison_contract"]["processing_recipe_id"],
        "quality_banner": "ascii-proof-grade-v1",
    }
    assert stable_id("proof", manifest["identity"]) == first.proof_id
    assert manifest["comparison_contract"] == json.loads(
        (second.path / "manifest.json").read_text()
    )["comparison_contract"]
    assert not _contains_decision_key(manifest)

    detector_ids = set()
    processing_ids = set()
    metric_schemas = set()
    for candidate_id in first.candidate_ids:
        candidate = first.path / "candidates" / candidate_id
        evidence = json.loads((candidate / "evidence.json").read_text())
        detector_ids.add(evidence["comparison_contract"]["detector_recipe_id"])
        processing_ids.add(evidence["comparison_contract"]["processing_recipe_id"])
        metric_schemas.add(tuple(sorted(evidence["metrics"])))
        assert evidence["candidate"]["id"] == candidate_id
        assert evidence["candidate"]["zone_axis_label"].startswith("[")
        assert evidence["candidate"]["bunge_phi1_deg"] == evidence["candidate"][
            "orientation"
        ]["euler_bunge_deg"][0]
        policy = evidence["comparison_contract"]["preview_quantization"]
        assert policy == {
            "scope": "per-panel-per-candidate",
            "method": "robust-percentile-linear",
            "percentiles": [0.5, 99.5],
            "comparison_use": "structural",
            "absolute_intensity_comparable": False,
        }
        for panel in ("raw", "processed"):
            assert evidence["quantization"][panel]["black_point"] < evidence[
                "quantization"
            ][panel]["white_point"]
        assert (candidate / "raw.npy").is_file()
        assert (candidate / "raw.tif").is_file()
        assert (candidate / "raw.png").is_file()
        assert (candidate / "processed.npy").is_file()
        assert (candidate / "processed.tif").is_file()
        assert (candidate / "processed.png").is_file()
    assert len(detector_ids) == 1
    assert len(processing_ids) == 1
    assert len(metric_schemas) == 1

    contact = json.loads((first.path / "contact-sheet.json").read_text())
    assert contact["candidate_order"] == list(first.candidate_ids)
    assert contact["panels"] == ["raw", "processed"]
    assert contact["processed_variant"] == {
        "name": "scientific-clean",
        "recipe_id": manifest["comparison_contract"]["processing_recipe_id"],
        "short_id": manifest["comparison_contract"]["processing_recipe_id"].split("-")[1][
            :8
        ],
    }
    assert contact["quality_banner"]["quality_grade"] == "proof"
    assert contact["quality_banner"]["not_final_quality"] is True
    assert "PROOF-GRADE" in contact["quality_banner"]["text"]
    assert "NOT FINAL QUALITY" in contact["quality_banner"]["text"]
    assert "scientific-clean" in contact["quality_banner"]["text"]
    assert all(ord(character) < 128 for character in contact["quality_banner"]["text"])
    assert contact["quality_banner"]["text"] in contact["rendered_text"]
    assert all("Euler" in label and "phi1=" in label and "[" in label for label in contact["labels"])
    sheet = iio.imread(first.contact_sheet)
    assert sheet.ndim == 2
    assert sheet.shape == tuple(contact["pixel_shape"])
    assert contact["label_height_px"] >= 20
    assert not _contains_decision_key(contact)

    execution = json.loads((first.path / "provenance/execution.json").read_text())
    assert execution["invocation"] == invocation
    assert execution["software"] == execution_context["software"]
    assert execution["doctor"]["checks"]["webgpu_adapter"]["details"] == {
        "backend_type": "TestBackend",
        "device": "Fixture GPU",
    }
    assert execution["git"] == execution_context["git"]
    origin = json.loads((first.path / "provenance/master-origin.json").read_text())
    assert origin["source"]["canonical_path"] == str(source_path.resolve())
    assert origin["source"]["sha256"] == source_sha256
    assert origin["master_product"]["canonical_path"] == str(master_path.resolve())
    assert origin["master_product"]["bundle_path"] == str(master_bundle.resolve())
    assert origin["master_product"]["manifest_path"] == str(master_manifest.resolve())
    assert origin["master_product"]["manifest_sha256"] == hashlib.sha256(
        master_manifest.read_bytes()
    ).hexdigest()
    assert origin["identity_exclusion"] == "local locators and execution context"
    assert manifest["evidence"]["execution"] == "provenance/execution.json"
    assert manifest["evidence"]["master_origin"] == "provenance/master-origin.json"
    assert "provenance/execution.json" in manifest["files"]
    assert "provenance/master-origin.json" in manifest["files"]
