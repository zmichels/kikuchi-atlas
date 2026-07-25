from __future__ import annotations

from pathlib import Path

from kikuchi_lab.sources.structure import load_structure_record, verify_structure


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/enstatite/source.yml"


def test_enstatite_zero_gpa_source_is_checksum_and_structure_verified() -> None:
    record = load_structure_record(SOURCE)
    verified = verify_structure(record)

    assert record.identifier == "COD-9001593"
    assert record.formula == "MgSiO3"
    assert record.space_group_number == 61
    assert record.setting == "P b c a"
    assert record.simulation_setting["pressure_gpa"] == 0.0
    assert record.simulation_setting["target_site_multiplicities"] == [8] * 10
    assert verified.sha256_matches
    assert verified.occupancy_source == "implicit CIF default 1.0"
    assert verified.missing_thermal_factor_labels == ()
