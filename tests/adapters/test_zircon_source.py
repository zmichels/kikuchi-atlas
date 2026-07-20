from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path

import pytest

from kikuchi_lab.sources.structure import load_structure_record, verify_structure
from kikuchi_lab.workflows import build_direct_art_catalog


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/zircon/source.yml"
ORIGINAL = ROOT / "phases/zircon/COD-9000684-original.cif"
DERIVATIVE = ROOT / "phases/zircon/COD-9000684-isotropic-u.cif"
RECIPE = ROOT / "recipes/reflectors/zircon-art-bands.yml"
ORIGINAL_SHA256 = "e461a480345cbb60af43cff99a8f6783cf8a3c41530fcb686c506de97b79c44f"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_zircon_derivative_records_exact_anisotropic_to_isotropic_policy() -> None:
    record = load_structure_record(SOURCE)
    verified = verify_structure(record)

    assert verified.parsed_formula == "ZrSiO4"
    assert verified.parsed_space_group_number == 141
    assert verified.parsed_lattice_angstrom == pytest.approx(
        (6.6042, 6.6042, 5.9796, 90.0, 90.0, 90.0)
    )
    assert verified.site_labels == ("Zr", "Si", "O")
    assert record.setting == "I 41/a m d :2"
    assert record.simulation_setting["derived_from_sha256"] == ORIGINAL_SHA256
    assert record.simulation_setting["u_iso_derivation"] == (
        "U_iso = (U_11 + U_22 + U_33) / 3 for orthogonal tetragonal axes"
    )
    assert verified.site_u_iso_angstrom_sq == pytest.approx(
        (0.003493333333333333, 0.003933333333333333, 0.006363333333333333)
    )
    assert _sha256(ORIGINAL) == ORIGINAL_SHA256
    assert _sha256(DERIVATIVE) == record.sha256


def test_zircon_direct_catalog_has_eleven_eligible_bands(tmp_path: Path) -> None:
    result = build_direct_art_catalog(
        recipe_path=RECIPE,
        output_root=tmp_path,
    )

    assert result.eligible_member_count >= 11


def test_zircon_origin_choice_two_is_shifted_to_diffpy_choice_one() -> None:
    from kikuchi_lab.kinematical.kikuchipy_adapter import _phase_from_record

    record = load_structure_record(SOURCE)
    assert record.simulation_setting["target_fractional_origin_shift"] == [
        0.0,
        0.25,
        -0.125,
    ]

    phase = _phase_from_record(record)

    assert Counter(atom.label for atom in phase.structure) == {
        "Zr": 4,
        "Si": 4,
        "O": 16,
    }
    zircon_positions = [atom.xyz for atom in phase.structure if atom.label == "Zr"]
    assert any(position == pytest.approx((0.0, 0.0, 0.0)) for position in zircon_positions)
