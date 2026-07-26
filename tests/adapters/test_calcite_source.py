from __future__ import annotations

from pathlib import Path

from kikuchi_lab.sources.structure import load_structure_record, verify_structure


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/calcite/source.yml"


def test_calcite_295k_source_is_checksum_and_structure_verified() -> None:
    record = load_structure_record(SOURCE)
    verified = verify_structure(record)

    assert record.identifier == "COD-1547350"
    assert record.formula == "C1Ca1O3"
    assert record.space_group_number == 167
    assert record.setting == "R -3 c :H"
    assert record.simulation_setting["temperature_kelvin"] == 295
    assert record.simulation_setting["target_site_multiplicities"] == [6, 6, 18]
    assert verified.sha256_matches
    assert verified.parsed_formula == record.formula
    assert verified.missing_thermal_factor_labels == ()
