from __future__ import annotations

from pathlib import Path

import pytest

from kikuchi_lab.sources.structure import load_structure_record, verify_structure


ROOT = Path(__file__).parents[2]


@pytest.mark.parametrize(
    ("phase", "identifier", "fallback"),
    [
        ("quartz", "COD-9000775", True),
        ("forsterite", "COD-9000319", False),
        ("titanite", "COD-1011220", True),
        ("zircon", "COD-9000685", True),
        ("diamond", "COD-9008564", True),
        ("ice-ih", "COD-1572233-O-sublattice", False),
    ],
)
def test_reflector_series_sources_verify_against_tracked_cifs(
    phase: str, identifier: str, fallback: bool
) -> None:
    record = load_structure_record(ROOT / "phases" / phase / "source.yml")
    verified = verify_structure(record)

    assert record.identifier == identifier
    assert verified.sha256_matches is True
    assert verified.parsed_space_group_number == record.space_group_number
    if fallback:
        assert record.thermal_factor_policy["missing"] == "fallback"
        assert verified.missing_thermal_factor_labels == tuple(site.label for site in record.sites)
    else:
        assert record.thermal_factor_policy["missing"] == "reject"
