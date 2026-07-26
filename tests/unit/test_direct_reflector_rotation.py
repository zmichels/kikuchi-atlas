from __future__ import annotations

import json
import runpy
from pathlib import Path

import numpy as np

from kikuchi_lab.art_products.rotation_animation import (
    DirectReflectorBand,
    RotationAnimationSpec,
    axis_angle_matrix,
    render_direct_reflector_depth_frame,
    render_direct_reflector_frame,
)
from kikuchi_lab.model.recipes import Orientation


ROOT = Path(__file__).resolve().parents[2]


def test_pyrope_rotation_source_points_to_published_standard_template() -> None:
    script_globals = runpy.run_path(str(ROOT / "scripts/render_direct_reflector_rotation.py"))
    assert script_globals["PHASE_SOURCES"]["pyrope"] == Path(
        "local/atlas-expansion/pyrope/templates/"
        "pyrope-hemisphere-standard-run-cf3ddb145179cc6e"
    )
    source = ROOT / script_globals["PHASE_SOURCES"]["pyrope"]
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    assert source.is_dir()
    assert manifest["run_identity"]["phase_slug"] == "pyrope"
    assert manifest["run_identity"]["treatment"] == "standard"


def test_enstatite_rotation_source_points_to_published_standard_template() -> None:
    script_globals = runpy.run_path(str(ROOT / "scripts/render_direct_reflector_rotation.py"))
    assert script_globals["PHASE_SOURCES"]["enstatite"] == Path(
        "local/atlas-expansion/enstatite/templates/"
        "enstatite-hemisphere-standard-run-5ac8464fe1575028"
    )


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


def test_depth_frame_is_dark_and_uses_the_same_rotation_seam() -> None:
    bands = (
        DirectReflectorBand("narrow", (1.0, 0.0, 0.0), 1.0),
        DirectReflectorBand("wide", (0.0, 1.0, 0.0), 4.0),
    )
    spec = RotationAnimationSpec((2.0, 1.0, 1.0), frame_count=24, frame_size_px=128)
    first = render_direct_reflector_depth_frame(
        bands, Orientation((17.0, 31.0, 43.0)), spec, 0
    )
    closure = render_direct_reflector_depth_frame(
        bands, Orientation((17.0, 31.0, 43.0)), spec, spec.frame_count
    )
    pixels = np.asarray(first)
    assert first.mode == "RGB"
    assert tuple(pixels[0, 0]) == (16, 21, 25)
    assert int(pixels.max()) > 100
    np.testing.assert_array_equal(pixels, np.asarray(closure))
