from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from kikuchi_lab.sources.structure import load_structure_record, verify_structure


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/pyrope/source.yml"
ORIGINAL = ROOT / "phases/pyrope/COD-9000435-original.cif"
ORIGINAL_SHA256 = "90c7d0b964653c5d1e32aa944a45430e760f29f3910ff8997a0a3524d4f55932"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pyrope_derivative_is_checksum_and_structure_verified() -> None:
    record = load_structure_record(SOURCE)
    verified = verify_structure(record)

    assert record.identifier == "COD-9000435-isotropic-U"
    assert record.formula == "Mg3Al2Si3O12"
    assert record.space_group_number == 230
    assert record.setting == "I a -3 d"
    assert record.simulation_setting["temperature_k"] == 298.15
    assert record.simulation_setting["target_site_multiplicities"] == [24, 16, 24, 96]
    assert record.simulation_setting["derived_from_sha256"] == ORIGINAL_SHA256
    assert record.simulation_setting["u_iso_derivation"] == (
        "U_iso = (U_11 + U_22 + U_33) / 3 for orthogonal cubic axes"
    )
    assert verified.site_u_iso_angstrom_sq == pytest.approx(
        (0.011836666666666667, 0.00507, 0.0036133333333333334, 0.00596)
    )
    assert verified.missing_thermal_factor_labels == ()
    assert verified.occupancy_source == "implicit CIF default 1.0"
    assert _sha256(ORIGINAL) == ORIGINAL_SHA256
