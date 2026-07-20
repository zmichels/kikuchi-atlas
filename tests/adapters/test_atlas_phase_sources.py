from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from kikuchi_lab.kinematical.kikuchipy_adapter import _phase_from_record
from kikuchi_lab.reflectors.diffsims_adapter import enumerate_reflector_members
from kikuchi_lab.reflectors.recipe import load_reflector_recipe
from kikuchi_lab.sources.structure import load_structure_record, verify_structure


ROOT = Path(__file__).parents[2]


@pytest.mark.parametrize(
    ("slug", "identifier", "space_group", "site_count", "expanded_count"),
    [
        ("plagioclase-an52", "COD-8103560", 2, 18, 36),
        ("muscovite-2m1", "COD-9014960", 15, 15, 112),
        ("diopside", "COD-1000007", 15, 6, 40),
    ],
)
def test_promoted_atlas_sources_preserve_their_checked_structure(
    slug: str,
    identifier: str,
    space_group: int,
    site_count: int,
    expanded_count: int,
) -> None:
    record = load_structure_record(ROOT / "phases" / slug / "source.yml")
    verified = verify_structure(record)
    phase = _phase_from_record(record)

    assert record.identifier == identifier
    assert verified.sha256_matches is True
    assert verified.parsed_space_group_number == space_group
    assert len(verified.site_labels) == site_count
    assert len(phase.structure) == expanded_count


def test_an52_centered_triclinic_source_uses_a_primitive_half_volume_view() -> None:
    record = load_structure_record(ROOT / "phases/plagioclase-an52/source.yml")
    phase = _phase_from_record(record)

    assert record.simulation_setting["target_setting"] == "P -1 primitive"
    assert phase.structure.lattice.volume == pytest.approx(669.485 / 2.0, rel=2e-6)
    assert Counter(atom.label for atom in phase.structure)["Si4"] == 2


def test_muscovite_mixed_site_species_remain_explicit_from_the_cif() -> None:
    record = load_structure_record(ROOT / "phases/muscovite-2m1/source.yml")
    verified = verify_structure(record)

    assert verified.site_elements[0:5] == ("K", "Na", "Al", "Fe", "Mg")
    assert verified.site_occupancies[0:5] == pytest.approx(
        (0.86, 0.10, 0.95, 0.02, 0.03)
    )
    assert verified.site_elements[-1] == "O"


def test_muscovite_reflector_catalog_uses_exact_integer_hkls_after_symmetrising() -> None:
    record = load_structure_record(ROOT / "phases/muscovite-2m1/source.yml")
    recipe = load_reflector_recipe(
        ROOT / "recipes/reflectors/muscovite-2m1-catalog.yml"
    )

    members = enumerate_reflector_members(record, recipe)

    assert members
    assert all(
        all(isinstance(index, int) for index in member.hkl) for member in members
    )
