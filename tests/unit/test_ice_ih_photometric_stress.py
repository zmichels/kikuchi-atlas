from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/run_ice_ih_photometric_stress.py"
_SPEC = importlib.util.spec_from_file_location("ice_ih_photometric_stress", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(MODULE)


def test_stress_cases_are_deterministic_and_preserve_explicit_affine_case() -> None:
    image = np.arange(35, dtype=np.float64).reshape(5, 7)

    first = MODULE.stress_cases(image)
    second = MODULE.stress_cases(image)

    assert [item[0] for item in first] == [item[0] for item in second]
    assert len(first) == 6
    np.testing.assert_allclose(first[1][2], second[1][2])
    np.testing.assert_allclose(first[-1][2], second[-1][2])
    np.testing.assert_allclose(first[1][2], np.mean(image) + 1.6 * (image - np.mean(image)))


def test_stress_cases_reject_flat_or_nonfinite_images() -> None:
    with pytest.raises(ValueError, match="non-zero contrast"):
        MODULE.stress_cases(np.ones((3, 3)))
    with pytest.raises(ValueError, match="finite"):
        MODULE.stress_cases(np.asarray(((1.0, np.nan), (2.0, 3.0))))
