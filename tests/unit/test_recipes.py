from dataclasses import FrozenInstanceError

import pytest

from kikuchi_lab.model.provenance import PhaseRecord, SourceRecord
from kikuchi_lab.model.recipes import (
    DetectorRecipe,
    Orientation,
    ProcessingRecipe,
    ProcessingStage,
    SimulationRecipe,
)


def valid_simulation_recipe(**changes):
    values = {
        "voltage_kv": 20.0,
        "halfw": 250,
        "dmin_nm": 0.05,
        "energy_binwidth_kev": 1.0,
        "n_trajectories": 100_000,
        "sigma_deg": 70.0,
        "omega_deg": 0.0,
        "rank": 20,
        "chunk_size": 64,
        "marginal_coverage": 0.99,
        "relative_image_stop": 0.01,
        "mc_backend": "gpu",
        "bethe_c_strong": 4.0,
        "bethe_c_weak": 8.0,
        "bethe_c_cutoff": 50.0,
        "dbdiff_sg_cutoff": 1e-5,
        "mc_auto_stop": True,
        "mc_relative_tol": 0.01,
        "mc_min_trajectories": 10_000,
        "mc_max_trajectories": 1_000_000,
        "exact_slow_cpu": False,
    }
    values.update(changes)
    return SimulationRecipe(**values)


def test_simulation_recipe_exposes_every_ebsdsim_control_and_stable_identity():
    recipe = valid_simulation_recipe()

    assert recipe.to_dict()["mc_backend"] == "gpu"
    assert recipe.to_dict()["exact_slow_cpu"] is False
    assert recipe.recipe_id == valid_simulation_recipe().recipe_id


def test_recipe_objects_are_frozen():
    recipe = valid_simulation_recipe()

    with pytest.raises(FrozenInstanceError):
        recipe.halfw = 10


def test_processing_parameters_are_deeply_immutable():
    stage = ProcessingStage("tone", {"window": [0.1, 0.9]})
    recipe = ProcessingRecipe([stage])

    with pytest.raises(TypeError):
        stage.parameters["window"] = (0.2, 0.8)
    with pytest.raises(TypeError):
        stage.parameters["window"][0] = 0.2
    assert isinstance(recipe.stages, tuple)


def test_orientation_requires_active_crystal_to_sample_frame():
    orientation = Orientation((10, 20, 30))

    assert orientation.euler_bunge_deg == (10.0, 20.0, 30.0)
    assert orientation.frame == "crystal_to_sample"
    with pytest.raises(ValueError, match="frame"):
        Orientation((0, 0, 0), frame="sample_to_crystal")


def test_detector_supersampling_preserves_geometry():
    detector = DetectorRecipe(
        shape=(96, 128),
        pcx=0.5,
        pcy=0.45,
        pcz=0.6,
        pc_convention="bruker",
        sample_tilt_deg=70.0,
        detector_tilt_deg=1.0,
        detector_azimuth_deg=2.0,
        detector_twist_deg=3.0,
        pixel_size_um=70.0,
        binning=2,
        supersampling=4,
    )

    assert detector.supersampled_shape == (384, 512)
    assert detector.effective_pixel_size_um == pytest.approx(35.0)
    assert detector.physical_extent_um == pytest.approx((13440.0, 17920.0))
    assert detector.to_dict()["pc"] == {
        "x": 0.5,
        "y": 0.45,
        "z": 0.6,
        "convention": "bruker",
        "units": "fraction",
    }


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"pc_convention": "mystery"}, "convention"),
        ({"pcx": 1.1}, "pcx"),
        ({"pcy": -0.1}, "pcy"),
        ({"pcz": 0.0}, "pcz"),
        ({"pc_convention": "emsoft"}, "convention"),
        ({"supersampling": 0}, "supersampling"),
    ],
)
def test_detector_rejects_invalid_convention_or_fraction(changes, match):
    values = {
        "shape": (96, 128),
        "pcx": 0.5,
        "pcy": 0.5,
        "pcz": 0.6,
        "pc_convention": "bruker",
        "sample_tilt_deg": 70.0,
        "detector_tilt_deg": 0.0,
        "detector_azimuth_deg": 0.0,
        "detector_twist_deg": 0.0,
        "pixel_size_um": 70.0,
        "binning": 1,
        "supersampling": 2,
    }
    values.update(changes)

    with pytest.raises(ValueError, match=match):
        DetectorRecipe(**values)


@pytest.mark.parametrize("convention", ["bruker", "tsl", "oxford"])
def test_detector_accepts_explicit_fraction_based_vendor_conventions(convention):
    detector = DetectorRecipe(
        shape=(96, 128),
        pcx=0.5,
        pcy=0.5,
        pcz=0.6,
        pc_convention=convention,
        sample_tilt_deg=70.0,
        detector_tilt_deg=0.0,
        detector_azimuth_deg=0.0,
        detector_twist_deg=0.0,
        pixel_size_um=70.0,
        binning=1,
        supersampling=1,
    )

    assert detector.to_dict()["pc"]["convention"] == convention


def test_provenance_records_validate_scientific_units_and_source_hash():
    source = SourceRecord("https://example.test/a.cif", "a" * 64, "CC0", "A citation")
    phase = PhaseRecord(
        "forsterite", "Mg2SiO4", 62, "Pnma", (4.75, 10.20, 5.98, 90, 90, 90)
    )

    assert source.source_id.startswith("source-")
    assert phase.to_dict()["lattice"]["units"] == "angstrom"
    assert phase.phase_id.startswith("phase-")

    with pytest.raises(ValueError, match="SHA-256"):
        SourceRecord("https://example.test/a.cif", "short", "CC0", "A citation")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_phase_record_rejects_nonfinite_lattice_values(value):
    with pytest.raises(ValueError, match="finite"):
        PhaseRecord("forsterite", "Mg2SiO4", 62, "Pnma", (value, 10.2, 5.98, 90, 90, 90))


@pytest.mark.parametrize("space_group", [True, 62.0, "62"])
def test_phase_record_rejects_boolean_or_noninteger_space_group(space_group):
    with pytest.raises(ValueError, match="space_group_number"):
        PhaseRecord(
            "forsterite", "Mg2SiO4", space_group, "Pnma", (4.75, 10.2, 5.98, 90, 90, 90)
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", " "),
        ("formula", 123),
        ("setting", None),
    ],
)
def test_phase_record_rejects_blank_or_nonstring_text(field, value):
    values = {
        "name": "forsterite",
        "formula": "Mg2SiO4",
        "space_group_number": 62,
        "setting": "Pnma",
        "lattice_angstrom": (4.75, 10.2, 5.98, 90, 90, 90),
    }
    values[field] = value

    with pytest.raises(ValueError, match=field):
        PhaseRecord(**values)
