from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/run_ice_ih_virtual_camera_transfer.py"
_SPEC = importlib.util.spec_from_file_location("ice_ih_virtual_camera_transfer", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(MODULE)


def test_target_selection_uses_identity_and_a_separated_orientation() -> None:
    half = np.sqrt(0.5)
    quaternions = np.asarray(
        (
            (1.0, 0.0, 0.0, 0.0),
            (half, half, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
        )
    )

    selected = MODULE._select_target_entries(quaternions)

    assert selected.tolist() == [0, 2]


def test_s2_coordinates_preserve_cardinal_directions() -> None:
    longitude, latitude = MODULE._s2_coordinates(
        np.asarray(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
    )

    assert np.allclose(longitude, (0.0, 90.0, 0.0))
    assert np.allclose(latitude, (0.0, 0.0, 90.0))
