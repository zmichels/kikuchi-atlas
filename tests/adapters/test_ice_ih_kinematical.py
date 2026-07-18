from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from kikuchi_lab.kinematical.kikuchipy_adapter import (
    _allowed_mask,
    _phase_from_record,
)
from kikuchi_lab.sources.structure import load_structure_record
from kikuchi_lab.workflows.ice_kinematical import simulate_ice_kinematical


ROOT = Path(__file__).parents[2]
RECIPE = ROOT / "recipes/kinematical/ice-ih-oxygen-quiet-proof.yml"
SOURCE = ROOT / "phases/ice-ih/source.yml"


def test_ice_master_has_two_finite_stereographic_hemispheres() -> None:
    simulation = simulate_ice_kinematical(RECIPE)
    master = simulation.master_stereographic

    assert master.intensity.shape == (2, 65, 65)
    assert master.metadata["projection"] == "stereographic"
    assert master.metadata["hemisphere"] == "both"
    assert np.isfinite(master.intensity).all()


def test_ice_master_records_identity_right_handed_frame_and_catalog_evidence() -> None:
    simulation = simulate_ice_kinematical(RECIPE)

    assert simulation.projection_ledger["frames"]["orientation"]["euler_bunge_deg"] == (
        0.0,
        0.0,
        0.0,
    )
    assert simulation.projection_ledger["frames"]["handedness"] == "right-handed"
    assert simulation.projection_ledger["known_axis_check"]["misalignment_deg"] == pytest.approx(
        0.0, abs=1e-10
    )
    assert simulation.projection_ledger["projections"]["stereographic"]["hemisphere_order"] == (
        "upper",
        "lower",
    )
    assert simulation.reflector_catalog["selection"]["source_master_relative_factor"] == 0.03


def test_primitive_hexagonal_allowed_mask_has_no_centering_extinctions() -> None:
    from diffsims.crystallography import ReciprocalLatticeVector

    phase = _phase_from_record(load_structure_record(SOURCE))
    vectors = ReciprocalLatticeVector.from_min_dspacing(phase, min_dspacing=0.7)

    assert _allowed_mask(vectors).dtype == bool
    assert _allowed_mask(vectors).all()


def test_primitive_hexagonal_allowed_mask_falls_back_when_upstream_is_unsupported() -> None:
    class UnsupportedAllowedVectors:
        shape = (3,)
        has_hexagonal_lattice = True
        phase = SimpleNamespace(space_group=SimpleNamespace(short_name="P 63/m m c"))

        @property
        def allowed(self) -> np.ndarray:
            raise NotImplementedError

    assert np.array_equal(_allowed_mask(UnsupportedAllowedVectors()), np.ones(3, dtype=bool))
