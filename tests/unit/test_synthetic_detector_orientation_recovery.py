from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts/run_ice_ih_synthetic_detector_orientation_recovery.py"
)
_SPEC = importlib.util.spec_from_file_location("synthetic_detector_orientation_recovery", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(MODULE)


def test_spread_selection_starts_at_identity_and_selects_distinct_entries() -> None:
    half = np.sqrt(0.5)
    quaternions = np.asarray(
        (
            (1.0, 0.0, 0.0, 0.0),
            (half, half, 0.0, 0.0),
            (half, 0.0, half, 0.0),
            (half, 0.0, 0.0, half),
            (0.0, 1.0, 0.0, 0.0),
        )
    )

    selected = MODULE._select_spread_entries(quaternions, count=4)

    assert selected[0] == 0
    assert selected[1] == 4
    assert len(np.unique(selected)) == 4


@pytest.mark.parametrize("count", (0, 6))
def test_spread_selection_rejects_invalid_count(count: int) -> None:
    quaternions = np.asarray(((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0)))

    with pytest.raises(ValueError, match="count"):
        MODULE._select_spread_entries(quaternions, count=count)
