from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from kikuchi_lab.sources.structure import load_structure_record, verify_structure
from kikuchi_lab.workflows import build_direct_art_catalog


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/titanite/source.yml"
CIF = ROOT / "phases/titanite/COD-9000509.cif"
RECIPE = ROOT / "recipes/reflectors/titanite-art-bands.yml"
EXPECTED_SHA256 = "ed45563f6621488f165373f2847c65acef197744322e0937d985518a3437be42"


def test_titanite_source_is_room_temperature_synthetic_p21a() -> None:
    record = load_structure_record(SOURCE)
    verified = verify_structure(record)

    assert verified.parsed_formula == "CaTiSiO5"
    assert verified.parsed_space_group_number == 14
    assert verified.parsed_lattice_angstrom == pytest.approx(
        (7.068, 8.714, 6.562, 90.0, 113.82, 90.0)
    )
    assert verified.site_labels == (
        "Ca",
        "Ti",
        "Si",
        "O1",
        "O2",
        "O3",
        "O4",
        "O5",
    )
    assert record.setting == "P 1 21/a 1"
    assert record.simulation_setting["temperature_kelvin"] == 298.15
    assert hashlib.sha256(CIF.read_bytes()).hexdigest() == EXPECTED_SHA256


def test_titanite_direct_catalog_has_eleven_eligible_bands(tmp_path: Path) -> None:
    result = build_direct_art_catalog(
        recipe_path=RECIPE,
        output_root=tmp_path,
    )

    assert result.eligible_member_count >= 11


def test_titanite_p21a_axes_are_mapped_to_diffpy_p21c() -> None:
    from diffpy.structure import Lattice

    from kikuchi_lab.kinematical.kikuchipy_adapter import _phase_from_record

    record = load_structure_record(SOURCE)
    assert record.simulation_setting["target_lattice_from_source"] == ["c", "b", "a"]
    assert record.simulation_setting["target_fractional_from_source"] == [
        "z",
        "y",
        "x",
    ]

    phase = _phase_from_record(record)

    assert len(phase.structure) == 32
    assert phase.space_group.short_name == "P21/c"
    assert phase.structure.lattice.cell_parms() == pytest.approx(
        (6.562, 8.714, 7.068, 90.0, 113.82, 90.0)
    )
    target_frame = phase.structure.copy()
    target_frame.placeInLattice(Lattice(base=phase._diffpy_lattice))
    calcium_positions = [atom.xyz for atom in target_frame if atom.label == "Ca"]
    assert any(
        position == pytest.approx((0.25130, 0.41840, 0.24390))
        for position in calcium_positions
    )
