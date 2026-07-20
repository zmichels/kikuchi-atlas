from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
from diffpy.structure import Lattice

from kikuchi_lab.kinematical import load_kinematical_recipe
from kikuchi_lab.kinematical.kikuchipy_adapter import (
    _phase_from_record,
    _projection_ledger,
    simulate_kinematical_arrays,
)
from kikuchi_lab.sources.structure import load_structure_record, verify_structure


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases" / "ice-ih" / "source.yml"
RECIPE = ROOT / "recipes" / "kinematical" / "ice-ih-oxygen-quiet-proof.yml"


def test_ice_ih_oxygen_source_is_verified_and_explicitly_bounded() -> None:
    record = load_structure_record(SOURCE)
    verified = verify_structure(record)

    assert verified.sha256_matches
    assert verified.parsed_formula == "O"
    assert verified.parsed_space_group_number == 194
    assert verified.site_labels == ("O1",)
    assert record.simulation_setting["model_scope"] == "average oxygen sublattice only"
    assert record.simulation_setting["omitted_source_sites"] == ["H1a", "H1b"]


def test_phase_adapter_accepts_identity_hexagonal_setting() -> None:
    phase = _phase_from_record(load_structure_record(SOURCE))

    assert phase.space_group.number == 194
    assert phase.space_group.short_name.replace(" ", "") == "P63/mmc"
    np.testing.assert_allclose(
        phase.structure.lattice.cell_parms(),
        [4.3815, 4.3815, 7.183, 90.0, 90.0, 120.0],
    )
    source_frame_structure = phase.structure.copy()
    source_frame_structure.place_in_lattice(
        Lattice(4.3815, 4.3815, 7.183, 90.0, 90.0, 120.0)
    )
    np.testing.assert_allclose(source_frame_structure[0].xyz, [1 / 3, 2 / 3, 0.4378])


def test_ice_projection_ledger_records_identity_setting_and_c_axis() -> None:
    record = load_structure_record(SOURCE)
    recipe = load_kinematical_recipe(RECIPE)
    ledger = _projection_ledger(record, recipe)

    assert ledger["frames"]["crystal"] == (
        "P 63/m m c direct and reciprocal Cartesian frames"
    )
    assert ledger["frames"]["source_to_crystal"] == {
        "source_setting": "P 63/m m c",
        "target_setting": "P 63/m m c",
        "lattice_transform": {
            "target_from_source": ["a", "b", "c"],
            "equation": "(a', b', c') = (a, b, c)",
        },
        "fractional_coordinate_transform": {
            "target_from_source": ["x", "y", "z"],
            "equation": "(x', y', z') = (x, y, z)",
        },
    }
    assert ledger["known_axis_check"]["zone_axis_uvw"] == [0, 0, 1]
    assert ledger["known_axis_check"]["misalignment_deg"] < 1e-8


def test_ice_small_kinematical_smoke_uses_same_quiet_contract() -> None:
    record = load_structure_record(SOURCE)
    recipe = replace(load_kinematical_recipe(RECIPE), half_size=16)
    simulation, context = simulate_kinematical_arrays(record, recipe)

    assert context.master_signal.data.shape == (2, 33, 33)
    assert simulation.master_stereographic.intensity.shape == (2, 33, 33)
    assert simulation.detector.intensity.shape == (1536, 2048)
    assert set(context.overlay_simulators) == {"balanced", "quiet"}
    assert simulation.reflector_catalog["overlays"]["quiet"]["retained_count"] > 0
    retained_hkl = {
        tuple(reflection["hkl"])
        for reflection in simulation.reflector_catalog["master"]["reflections"]
    }
    assert (0, 0, 1) not in retained_hkl
