from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts/run_ice_ih_projection_center_sensitivity.py"
)
_SPEC = importlib.util.spec_from_file_location("projection_center_sensitivity", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(MODULE)


def test_offsets_require_an_ordered_grid_with_nominal_geometry() -> None:
    offsets = MODULE._verify_offsets(np.asarray((-0.01, 0.0, 0.01)))

    np.testing.assert_allclose(offsets, (-0.01, 0.0, 0.01))


@pytest.mark.parametrize(
    "offsets",
    (
        (-0.01, 0.01),
        (-0.01, 0.01, 0.02),
        (-0.01, 0.0, 0.0),
        (-0.01, np.nan, 0.01),
    ),
)
def test_offsets_reject_ambiguous_or_invalid_geometry_grids(offsets: tuple[float, ...]) -> None:
    with pytest.raises(ValueError, match="offsets"):
        MODULE._verify_offsets(np.asarray(offsets))
