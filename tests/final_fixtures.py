from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from kikuchi_lab.model import DetectorPatternProduct, MasterPatternProduct, SourceRecord
from kikuchi_lab.model.identity import canonical_json, stable_id
from kikuchi_lab.orientations.selection import create_orientation_selection


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value), encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_proof(
    tmp_path: Path,
    *,
    proof_source: dict | None = None,
    proof_phase: dict | None = None,
    proof_energy_kev: float = 20.0,
) -> tuple[Path, Path]:
    run = tmp_path / "proof" / "proof-fixture"
    candidate = {
        "id": "fo-011-phi1-045",
        "name": "bc mixed axis phi1 045",
        "orientation": {
            "angle_units": "degree",
            "euler_bunge_deg": [45.0, 51.50414783, 0.0],
            "frame": "crystal_to_sample",
        },
        "bunge_phi1_deg": 45.0,
        "zone_axis_uvw": [0, 1, 1],
        "zone_axis_intent": "Center [011] on sample ND.",
        "composition_intent": "Diagonal crossing.",
        "zone_axis_label": "[011]",
    }
    candidate_identity = {
        "schema_version": 1,
        "phase": "forsterite (Mg2SiO4)",
        "space_group": "Pnma (No. 62, standard setting)",
        "point_group": "mmm",
        "orientation_convention": (
            "active crystal-to-sample Bunge ZXZ Euler angles in degrees"
        ),
        "phi1_semantics": "explicit first Bunge Euler angle",
        "equivalence_tolerance_deg": 0.01,
        "generation_rationale": "Bounded human-review set.",
        "exhaustive": False,
        "lattice_abc_angstrom": [10.207, 5.98, 4.756],
        "candidates": [
            {key: value for key, value in candidate.items() if key != "zone_axis_label"}
        ],
    }
    candidate_set_id = stable_id("candidate-set", candidate_identity)
    candidate_set = {
        "candidate_set_id": candidate_set_id,
        **candidate_identity,
        "candidates": [candidate],
    }
    detector = {
        "shape": [18, 24],
        "supersampled_shape": [36, 48],
        "pc": {"x": 0.5, "y": 0.72, "z": 0.6, "convention": "tsl", "units": "fraction"},
        "sample_tilt_deg": 70.0,
        "detector_tilt_deg": 0.0,
        "detector_azimuth_deg": 0.0,
        "detector_twist_deg": 0.0,
        "angle_units": "degree",
        "pixel_size_um": 500.0,
        "effective_pixel_size_um": 250.0,
        "physical_extent_um": [9000.0, 12000.0],
        "binning": 1,
        "supersampling": 2,
    }
    comparison = {
        "detector_recipe_id": stable_id("recipe", detector),
        "detector": detector,
        "energy_kev": proof_energy_kev,
    }
    evidence = {
        "schema_version": 1,
        "candidate": candidate,
        "comparison_contract": comparison,
        "processing_evidence": {
            "geometry": {
                "source_shape": [36, 48],
                "output_shape": [18, 24],
                "supersampling": 2,
                "physical_extent_um": [9000.0, 12000.0],
            }
        },
        "metrics": {
            "schema_version": 1,
            "raw": {"gradient": {"mean": 1.0}},
            "processed": {"gradient": {"mean": 2.0}},
        },
    }
    candidate_set_path = run / "metadata/orientation-candidates.json"
    evidence_path = run / "candidates" / candidate["id"] / "evidence.json"
    raw_path = run / "candidates" / candidate["id"] / "raw.bin"
    _write_json(candidate_set_path, candidate_set)
    _write_json(evidence_path, evidence)
    raw_path.write_bytes(b"sealed proof pixels")
    files = {}
    for path in (candidate_set_path, evidence_path, raw_path):
        files[path.relative_to(run).as_posix()] = {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
    source_contract = proof_source or {
        "identifier": "COD-9000319",
        "sha256": "550b8c89c617267d39e7cb6a07fe6f55cd2343453c1c45ec77738bf6fd25d9cd",
        "source_id": "source-ca21e09f345e7146",
    }
    phase_contract = proof_phase or {
        "name": "forsterite",
        "formula": "Mg2SiO4",
        "space_group_number": 62,
        "space_group_setting": "P n m a",
        "lattice_angstrom": [10.207, 5.98, 4.756, 90.0, 90.0, 90.0],
        "lattice_absolute_tolerance": 1e-6,
    }
    master_contract = {
        "schema_version": 1,
        "source": source_contract,
        "phase": phase_contract,
        "simulation": {
            "requested": {"voltage_kv": proof_energy_kev},
            "resolved": {"voltage_kv": proof_energy_kev},
        },
        "product": {
            "projection": "Lambert square equal-area",
            "hemisphere_order": ["north", "south"],
        },
    }
    identity = {
        "candidate_order": [candidate["id"]],
        "candidate_set_id": candidate_set_id,
        "comparison_contract": comparison,
        "master_contract": master_contract,
    }
    manifest = {
        "schema_version": 3,
        "proof_id": stable_id("proof", identity),
        "state": "awaiting-human-selection",
        "identity": identity,
        "candidate_order": [candidate["id"]],
        "candidate_set_id": candidate_set_id,
        "master_contract": master_contract,
        "files": files,
    }
    _write_json(run / "manifest.json", manifest)
    selection = create_orientation_selection(
        run=run,
        candidate_id=candidate["id"],
        author="Z",
        rationale="Balanced radial bands and clarity-forward potential.",
        selected_on="2026-07-13",
        output_root=tmp_path / "decisions",
    )
    return run, selection.selection_path


def canonical_master(*, perturbation: float = 0.0) -> MasterPatternProduct:
    y, x = np.mgrid[-1:1:17j, -1:1:17j]
    source = SourceRecord(
        uri="https://www.crystallography.net/cod/9000319.cif",
        sha256="550b8c89c617267d39e7cb6a07fe6f55cd2343453c1c45ec77738bf6fd25d9cd",
        license="CC0-1.0",
        citation=(
            "Smyth, J. R. and Hazen, R. M. (1973). The crystal structures of "
            "forsterite and hortonolite at several temperatures up to 900 C. "
            "American Mineralogist 58, 588-593."
        ),
    )
    recipe_sha256 = "1" * 64
    recipe_id = f"recipe-{recipe_sha256[:16]}"
    return MasterPatternProduct.from_array(
        np.stack((10 + x + y + perturbation, 9 - x + 0.5 * y + perturbation)),
        metadata={
            "phase": {
                "name": "forsterite",
                "formula": "Mg2SiO4",
                "space_group": {"number": 62, "setting": "P n m a"},
                "lattice": {
                    "values": [10.207, 5.98, 4.756, 90.0, 90.0, 90.0],
                    "units": "angstrom",
                },
            },
            "source_structure": {
                "identifier": "COD-9000319",
                "sha256": source.sha256,
                "source_id": source.source_id,
                "provenance": source.to_dict(),
            },
            "generator": {"name": "ebsdsim", "version": "0.1.8"},
            "simulation": {
                "recipe_id": recipe_id,
                "recipe_sha256": recipe_sha256,
                "voltage_kv": 20.0,
                "requested_backend": "gpu",
                "resolved_backend": "gpu_fly_first",
            },
            "projection": "Lambert square equal-area",
            "hemisphere_order": ["north", "south"],
            "energy_kev": 20.0,
            "intensity_units": "raw dynamical intensity",
            "coordinate_frame": "crystal:Pnma-derived-from-Pbnm",
            "provenance_links": [source.source_id, recipe_id],
        },
    )


def fixture_projector(*, master, orientation, detector, energy_kev):
    height, width = detector.supersampled_shape
    y, x = np.mgrid[-1:1 : complex(height), -1:1 : complex(width)]
    phi1, phi, phi2 = np.deg2rad(orientation.euler_bunge_deg)
    radial = np.hypot(x + 0.12, y - 0.18)
    bands = (
        np.cos((8.0 + phi / np.pi) * x + phi1)
        + 0.7 * np.sin(11.0 * y - phi2)
        + 0.3 * np.cos(18.0 * radial)
    )
    texture = 0.035 * np.sin(37.0 * x) * np.sin(31.0 * y)
    image = (4.0 + bands + texture).astype(np.float32)
    return DetectorPatternProduct.from_array(
        image,
        master_product_id=master.product_id,
        projection_recipe_id=stable_id(
            "recipe",
            {
                "orientation": orientation.to_dict(),
                "detector": detector.to_dict(),
                "energy_kev": energy_kev,
            },
        ),
        metadata={
            "intensity_units": "raw dynamical intensity",
            "detector_frame": "EDAX-TSL:RD-TD-ND",
            "energy_kev": energy_kev,
            "orientation": orientation.to_dict(),
            "detector": detector.to_dict(),
            "supersampling": detector.supersampling,
        },
    )
