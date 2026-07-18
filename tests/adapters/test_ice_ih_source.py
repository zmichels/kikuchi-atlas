from __future__ import annotations

from pathlib import Path

from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]


def test_ice_ih_oxygen_sublattice_source_is_verified() -> None:
    record = load_structure_record(ROOT / "phases/ice-ih/source.yml")

    assert record.identifier == "COD-1572233-O-sublattice"
    assert record.sha256 == "4327a279e414a62f861d143e18570e9d741bbbb7d04dd2fb471c930988f95b81"
    assert record.space_group_number == 194
    assert record.setting == "P 63/m m c"
    assert record.simulation_setting["model_scope"] == "average oxygen sublattice only"
    assert record.simulation_setting["omitted_source_sites"] == ["H1a", "H1b"]
