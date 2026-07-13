from __future__ import annotations

import numpy as np

from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.projection.kikuchipy_adapter import transform_crystal_direction_to_sample


def test_active_bunge_rotation_maps_crystal_a_to_edax_tsl_td():
    # EDAX TSL sample coordinates are [RD, TD, ND]. A positive 90 degree
    # active Bunge phi1 rotation about ND carries crystal [100] from RD to TD.
    sample_direction = transform_crystal_direction_to_sample(
        (1.0, 0.0, 0.0),
        Orientation((90.0, 0.0, 0.0)),
    )

    np.testing.assert_allclose(sample_direction, [0.0, 1.0, 0.0], atol=1e-12)


def test_orientation_transform_preserves_direction_length():
    crystal_direction = np.array([1.0, 2.0, 3.0])

    sample_direction = transform_crystal_direction_to_sample(
        crystal_direction,
        Orientation((13.0, 29.0, 47.0)),
    )

    np.testing.assert_allclose(
        np.linalg.norm(sample_direction),
        np.linalg.norm(crystal_direction),
        atol=1e-12,
    )
