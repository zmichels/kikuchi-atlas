from __future__ import annotations

import hashlib

import numpy as np
from diffpy.structure import Lattice
from kikuchipy.detectors import EBSDDetector
from kikuchipy.signals import EBSDMasterPattern
from orix.crystal_map import Phase
from orix.quaternion import Rotation

from kikuchi_lab.model.identity import canonical_json
from kikuchi_lab.model.products import MasterPatternProduct
from kikuchi_lab.model.provenance import SourceRecord
from kikuchi_lab.model.recipes import DetectorRecipe, Orientation
from kikuchi_lab.projection.kikuchipy_adapter import (
    _to_kikuchipy_detector,
    _to_kikuchipy_master_pattern,
    _to_kikuchipy_rotation,
    project_with_kikuchipy,
)


def canonical_master() -> MasterPatternProduct:
    y, x = np.mgrid[-1:1:17j, -1:1:17j]
    north = 11.0 + 2.0 * x + y + 0.5 * np.cos(4 * x * y)
    south = 9.0 - x + 1.5 * y + 0.25 * np.sin(3 * x)
    source = SourceRecord(
        uri="https://example.invalid/forsterite.cif",
        sha256="1" * 64,
        license="CC0-1.0",
        citation="Deterministic projection test fixture.",
    )
    recipe_payload = {"fixture": "projection", "voltage_kv": 20.0}
    recipe_sha256 = hashlib.sha256(canonical_json(recipe_payload).encode()).hexdigest()
    recipe_id = f"recipe-{recipe_sha256[:16]}"
    return MasterPatternProduct.from_array(
        np.stack((north, south)),
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
                "identifier": "projection-fixture",
                "sha256": source.sha256,
                "source_id": source.source_id,
                "provenance": source.to_dict(),
            },
            "generator": {"name": "test-fixture", "version": "1"},
            "simulation": {
                "recipe_id": recipe_id,
                "recipe_sha256": recipe_sha256,
                "voltage_kv": 20.0,
                "upstream_npz_sha256": "2" * 64,
            },
            "projection": "Lambert square equal-area",
            "hemisphere_order": ["north", "south"],
            "energy_kev": 20.0,
            "intensity_units": "raw dynamical intensity",
            "coordinate_frame": "crystal:Pnma-derived-from-Pbnm",
            "provenance_links": [source.source_id, recipe_id, f"sha256:{'2' * 64}"],
        },
    )


def detector_recipe(**changes: object) -> DetectorRecipe:
    values = {
        "shape": (12, 16),
        "pcx": 0.42,
        "pcy": 0.61,
        "pcz": 0.72,
        "pc_convention": "tsl",
        "sample_tilt_deg": 70.0,
        "detector_tilt_deg": 1.5,
        "detector_azimuth_deg": 2.5,
        "detector_twist_deg": -3.5,
        "pixel_size_um": 70.0,
        "binning": 2,
        "supersampling": 2,
    }
    values.update(changes)
    return DetectorRecipe(**values)


def test_projection_preserves_public_geometry_and_source_identity():
    master = canonical_master()
    orientation = Orientation((17.0, 31.0, 43.0))
    detector = detector_recipe()

    out = project_with_kikuchipy(
        master=master,
        orientation=orientation,
        detector=detector,
        energy_kev=20.0,
    )

    metadata = out.metadata_dict()
    assert out.intensity.shape == (24, 32)
    assert out.intensity.dtype == np.float32
    assert np.isfinite(out.intensity).all()
    assert not out.intensity.flags.writeable
    assert out.master_product_id == master.product_id
    assert metadata["master_product_id"] == master.product_id
    assert metadata["master_array_sha256"] == master.array_sha256
    assert metadata["source_npz_sha256"] == "2" * 64
    assert metadata["orientation"] == orientation.to_dict()
    assert metadata["orientation_frame"] == "crystal_to_sample"
    assert metadata["detector"] == detector.to_dict()
    assert metadata["detector_frame"] == "EDAX-TSL:RD-TD-ND"
    assert metadata["pc_convention"] == "tsl"
    assert metadata["energy_kev"] == 20.0
    assert metadata["supersampling"] == 2


def test_adapter_builds_pnma_phase_from_canonical_metadata():
    signal = _to_kikuchipy_master_pattern(canonical_master())

    assert isinstance(signal, EBSDMasterPattern)
    assert signal.projection == "lambert"
    assert signal.hemisphere == "both"
    assert signal.phase.name == "forsterite"
    assert signal.phase.space_group.number == 62
    assert signal.phase.space_group.short_name.replace(" ", "") == "Pnma"
    np.testing.assert_allclose(
        signal.phase.structure.lattice.cell_parms(),
        [10.207, 5.98, 4.756, 90, 90, 90],
    )


def test_adapter_detector_preserves_geometry_at_supersampled_resolution():
    recipe = detector_recipe()

    detector = _to_kikuchipy_detector(recipe)

    assert isinstance(detector, EBSDDetector)
    assert detector.shape == recipe.supersampled_shape
    assert detector.px_size == recipe.pixel_size_um / recipe.supersampling
    assert detector.binning == recipe.binning
    np.testing.assert_allclose(detector.pc_tsl(), [[recipe.pcx, recipe.pcy, recipe.pcz]])
    assert detector.tilt == recipe.detector_tilt_deg
    assert detector.azimuthal == recipe.detector_azimuth_deg
    assert detector.twist == recipe.detector_twist_deg
    assert detector.sample_tilt == recipe.sample_tilt_deg
    assert detector.shape[0] * detector.px_size * detector.binning == recipe.physical_extent_um[0]
    assert detector.shape[1] * detector.px_size * detector.binning == recipe.physical_extent_um[1]


def test_projection_matches_direct_kikuchipy_standard_passive_call():
    master = canonical_master()
    orientation = Orientation((17.0, 31.0, 43.0))
    detector_recipe_value = detector_recipe()

    adapter_rotation = _to_kikuchipy_rotation(orientation)
    standard_rotation = Rotation.from_euler(
        orientation.euler_bunge_deg,
        degrees=True,
        direction="lab2crystal",
    )
    np.testing.assert_allclose(adapter_rotation.data, standard_rotation.data, atol=1e-15)

    direct = _to_kikuchipy_master_pattern(master).get_patterns(
        standard_rotation,
        _to_kikuchipy_detector(detector_recipe_value),
        energy=20.0,
        dtype_out="float32",
        compute=True,
        show_progressbar=False,
    )
    adapted = project_with_kikuchipy(
        master=master,
        orientation=orientation,
        detector=detector_recipe_value,
        energy_kev=20.0,
    )

    np.testing.assert_allclose(adapted.intensity, direct.data[0], rtol=0, atol=0)
    assert adapted.intensity.max() < 100.0
    assert adapted.intensity.min() > 0.0


def test_adapter_rejects_energy_inconsistent_with_integrated_master():
    with np.testing.assert_raises_regex(ValueError, "energy"):
        project_with_kikuchipy(
            master=canonical_master(),
            orientation=Orientation((0.0, 0.0, 0.0)),
            detector=detector_recipe(),
            energy_kev=15.0,
        )


def test_public_recipes_reject_unknown_frames_and_pc_conventions():
    with np.testing.assert_raises_regex(ValueError, "frame"):
        Orientation((0.0, 0.0, 0.0), frame="sample_to_crystal")
    with np.testing.assert_raises_regex(ValueError, "convention"):
        detector_recipe(pc_convention="emsoft")


def test_private_seam_types_are_not_embedded_in_returned_product():
    out = project_with_kikuchipy(
        master=canonical_master(),
        orientation=Orientation((0.0, 0.0, 0.0)),
        detector=detector_recipe(),
        energy_kev=20.0,
    )

    assert not isinstance(out, (EBSDMasterPattern, EBSDDetector, Rotation, Phase, Lattice))
