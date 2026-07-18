from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from kikuchi_lab.sources.structure import load_structure_record, verify_structure
from kikuchi_lab.workflows import build_direct_art_catalog


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/diamond/source.yml"
CIF = ROOT / "phases/diamond/COD-2101499-diamond-derived.cif"
RECIPE = ROOT / "recipes/reflectors/diamond-art-bands.yml"


def test_diamond_source_is_cubic_fd3m_with_pinned_thermal_carbon() -> None:
    record = load_structure_record(SOURCE)
    verified = verify_structure(record)

    assert record.identifier == "COD-2101499-diamond-derived"
    assert verified.parsed_formula == "C1"
    assert verified.parsed_space_group_number == 227
    assert verified.parsed_lattice_angstrom == pytest.approx(
        (3.56658, 3.56658, 3.56658, 90.0, 90.0, 90.0)
    )
    assert verified.site_labels == ("C",)
    assert verified.site_u_iso_angstrom_sq == pytest.approx((0.01,))
    assert record.simulation_setting["target_setting"] == "F d -3 m"
    assert record.simulation_setting["target_fractional_origin_shift"] == [
        -0.125,
        -0.125,
        -0.125,
    ]
    assert hashlib.sha256(CIF.read_bytes()).hexdigest() == record.sha256
    assert record.simulation_setting["original_cod_sha256"] == (
        "d6be73a0b0c170dcc6e8ab629598739b603a24d2cfb668a72383ad723ab972ed"
    )


def test_diamond_direct_catalog_has_eleven_eligible_bands(tmp_path: Path) -> None:
    result = build_direct_art_catalog(recipe_path=RECIPE, output_root=tmp_path)

    assert result.eligible_member_count >= 11
