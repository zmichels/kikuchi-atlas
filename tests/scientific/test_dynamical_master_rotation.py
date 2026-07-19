from __future__ import annotations

import numpy as np

from kikuchi_lab.dynamical_master_rotation import (
    DynamicalMasterRotationSpec,
    render_dynamical_master_frame,
)
from kikuchi_lab.relief.field import build_spherical_scalar_field

from tests.relief_fixtures import analytic_master_product, expectation_for


def test_dynamical_master_rotation_is_a_seamless_active_field_rotation() -> None:
    master = analytic_master_product(size=9)
    field = build_spherical_scalar_field(master, expectation_for(master))
    spec = DynamicalMasterRotationSpec(
        axis_sample=(1.0, 0.0, 0.0), frame_count=24, frame_size_px=128
    )

    first = render_dynamical_master_frame(field, spec, frame_index=0)
    quarter_turn = render_dynamical_master_frame(field, spec, frame_index=6)
    closure = render_dynamical_master_frame(field, spec, frame_index=24)

    assert first.mode == "RGB"
    assert first.size == (128, 128)
    assert not np.array_equal(np.asarray(first), np.asarray(quarter_turn))
    np.testing.assert_array_equal(np.asarray(first), np.asarray(closure))
