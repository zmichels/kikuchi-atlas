from __future__ import annotations

import numpy as np

from kikuchi_lab.art_products.rotation_animation import (
    DirectReflectorBand,
    RotationAnimationSpec,
    axis_angle_matrix,
    render_direct_reflector_frame,
)
from kikuchi_lab.model.recipes import Orientation


def test_full_axis_rotation_is_identity() -> None:
    matrix = axis_angle_matrix(np.array((2.0, 1.0, 1.0)), 360.0)
    np.testing.assert_allclose(matrix, np.eye(3), rtol=0.0, atol=5e-13)


def test_rotation_frame_is_square_rgb_and_seam_angles_match() -> None:
    bands = (DirectReflectorBand("band", (1.0, 0.0, 0.0), 4.0),)
    spec = RotationAnimationSpec((2.0, 1.0, 1.0), frame_count=24, frame_size_px=128)
    first = render_direct_reflector_frame(bands, Orientation((17.0, 31.0, 43.0)), spec, 0)
    closure = render_direct_reflector_frame(
        bands, Orientation((17.0, 31.0, 43.0)), spec, spec.frame_count
    )
    assert first.mode == "RGB"
    assert first.size == (128, 128)
    np.testing.assert_array_equal(np.asarray(first), np.asarray(closure))
