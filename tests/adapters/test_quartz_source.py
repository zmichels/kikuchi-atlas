from __future__ import annotations

from pathlib import Path

import pytest

from kikuchi_lab.sources.structure import load_structure_record, verify_structure
from kikuchi_lab.workflows import build_direct_art_catalog


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/quartz/source.yml"
RECIPE = ROOT / "recipes/reflectors/quartz-art-bands.yml"


def test_quartz_source_is_ambient_right_handed_alpha_quartz() -> None:
    record = load_structure_record(SOURCE)
    verified = verify_structure(record)

    assert verified.parsed_formula == "SiO2"
    assert verified.parsed_space_group_number == 152
    assert verified.parsed_lattice_angstrom == pytest.approx(
        (4.914, 4.914, 5.406, 90.0, 90.0, 120.0)
    )
    assert verified.site_labels == ("Si1", "O1")
    assert record.setting == "P 31 2 1"
    assert record.simulation_setting["handedness"] == "right-handed P 31 2 1"


def test_quartz_direct_catalog_has_eleven_eligible_bands(tmp_path: Path) -> None:
    result = build_direct_art_catalog(
        recipe_path=RECIPE,
        output_root=tmp_path,
    )

    assert result.eligible_member_count >= 11
