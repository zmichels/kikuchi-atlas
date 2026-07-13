from __future__ import annotations

import hashlib
import json
from pathlib import Path

import imageio.v3 as iio
import numpy as np

from kikuchi_lab.model import DetectorPatternProduct, MasterPatternProduct, SourceRecord
from kikuchi_lab.model.identity import canonical_json
from kikuchi_lab.workflows.proof import render_proof


ROOT = Path(__file__).parents[2]


def _canonical_master() -> MasterPatternProduct:
    y, x = np.mgrid[-1:1:33j, -1:1:33j]
    source = SourceRecord(
        uri="https://example.invalid/forsterite.cif",
        sha256="1" * 64,
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
    forbidden = {"selected_candidate_id", "winner", "ranking", "rank", "score"}
    if isinstance(value, dict):
        return bool(forbidden.intersection(value)) or any(
            _contains_decision_key(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_decision_key(item) for item in value)
    return False


def test_proof_renders_every_candidate_under_one_comparison_contract(tmp_path: Path) -> None:
    first = render_proof(
        master=_canonical_master(),
        recipe_path=ROOT / "recipes/proof/forsterite-proof.yml",
        output_root=tmp_path / "first",
        projector=_fixture_projector,
    )
    second = render_proof(
        master=_canonical_master(),
        recipe_path=ROOT / "recipes/proof/forsterite-proof.yml",
        output_root=tmp_path / "second",
        projector=_fixture_projector,
    )

    assert first.proof_id == second.proof_id
    assert first.candidate_ids == second.candidate_ids
    assert first.state == "awaiting-human-selection"
    assert len(first.candidate_ids) == 12

    manifest = json.loads((first.path / "manifest.json").read_text())
    assert manifest["proof_id"] == first.proof_id
    assert manifest["state"] == "awaiting-human-selection"
    assert manifest["candidate_order"] == list(first.candidate_ids)
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
    assert all("Euler" in label and "phi1=" in label and "[" in label for label in contact["labels"])
    sheet = iio.imread(first.contact_sheet)
    assert sheet.ndim == 2
    assert sheet.shape == tuple(contact["pixel_shape"])
    assert contact["label_height_px"] >= 20
    assert not _contains_decision_key(contact)
