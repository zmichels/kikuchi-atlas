from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

from kikuchi_lab.art_products.rotation_animation import axis_angle_matrix


ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "scripts" / "render_retained_near_depth_rotation.py"
_SPEC = importlib.util.spec_from_file_location("retained_near_depth_rotation", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(MODULE)


def test_retained_field_rotation_closes_cleanly_without_a_spatial_filter() -> None:
    size = 33
    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float32)
    x, y = np.meshgrid(coordinate, coordinate)
    master = np.stack((0.55 + 0.20 * x + 0.10 * y, 0.55 - 0.15 * x + 0.05 * y))
    overlap = np.maximum(0.0, 1.0 - (x * x + y * y)).astype(np.float32)
    directions, valid = MODULE._screen_directions(128)
    first = MODULE._render_frame(
        master,
        overlap,
        normalization=1.0,
        gain=0.38,
        ceiling=0.985,
        screen_directions=directions,
        screen_valid=valid,
        rotation=axis_angle_matrix(np.array((1.0, 0.0, 0.0)), 0.0),
        base_orientation=np.eye(3),
    )
    closure = MODULE._render_frame(
        master,
        overlap,
        normalization=1.0,
        gain=0.38,
        ceiling=0.985,
        screen_directions=directions,
        screen_valid=valid,
        rotation=axis_angle_matrix(np.array((1.0, 0.0, 0.0)), 360.0),
        base_orientation=np.eye(3),
    )
    pixels = np.asarray(first)
    assert first.mode == "RGB"
    assert first.size == (128, 128)
    assert tuple(pixels[0, 0]) == (16, 21, 25)
    np.testing.assert_array_equal(pixels, np.asarray(closure))
