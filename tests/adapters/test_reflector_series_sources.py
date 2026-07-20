from __future__ import annotations

from pathlib import Path

import pytest

from kikuchi_lab.sources.structure import load_structure_record, verify_structure


ROOT = Path(__file__).parents[2]


@pytest.mark.parametrize(
    ("phase", "identifier"),
    [
        ("quartz", "COD-9012600"),
        ("forsterite", "COD-9000319"),
        ("titanite", "COD-9000509"),
        ("zircon", "COD-9000684-isotropic-U"),
        ("diamond", "COD-2101499-diamond-derived"),
        ("ice-ih", "COD-1572233-O-sublattice"),
    ],
)
def test_reflector_series_sources_verify_against_tracked_cifs(
    phase: str, identifier: str
) -> None:
    record = load_structure_record(ROOT / "phases" / phase / "source.yml")
    verified = verify_structure(record)

    assert record.identifier == identifier
    assert verified.sha256_matches is True
    assert verified.parsed_space_group_number == record.space_group_number
    assert record.thermal_factor_policy["missing"] == "reject"
    assert verified.missing_thermal_factor_labels == ()
