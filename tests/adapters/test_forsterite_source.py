from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from ebsdsim.cif import parse_cif_crystal
from ebsdsim.structure import build_cell_from_cif

from kikuchi_lab.sources.structure import (
    load_structure_record,
    materialize_simulation_cif,
    verify_structure,
)


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/forsterite/source.yml"


def test_forsterite_source_matches_catalog():
    record = load_structure_record(SOURCE)
    verified = verify_structure(record)

    assert verified.sha256_matches
    assert verified.parsed_formula == "Mg2SiO4"
    assert verified.parsed_space_group_number == 62
    assert verified.parsed_lattice_angstrom == pytest.approx(record.lattice_angstrom)
    assert verified.site_occupancies == pytest.approx(record.site_occupancies)
    assert verified.site_u_iso_angstrom_sq == pytest.approx(record.site_u_iso_angstrom_sq)
    assert verified.thermal_factor_policy == record.thermal_factor_policy
    assert verified.missing_thermal_factor_labels == ()


def test_forsterite_source_keeps_all_sites_and_implicit_full_occupancies():
    record = load_structure_record(SOURCE)
    verified = verify_structure(record)

    assert verified.site_labels == ("Mg1", "Mg2", "Si", "O1", "O2", "O3")
    assert verified.site_elements == ("Mg", "Mg", "Si", "O", "O", "O")
    assert verified.site_occupancies == (1.0,) * 6
    assert verified.occupancy_source == "implicit CIF default 1.0"


def test_forsterite_source_rejects_checksum_mismatch():
    record = load_structure_record(SOURCE)

    with pytest.raises(ValueError, match="checksum"):
        verify_structure(replace(record, sha256="0" * 64))


def test_forsterite_source_rejects_catalog_site_disagreement():
    record = load_structure_record(SOURCE)
    changed_site = replace(record.sites[0], occupancy=0.5)

    with pytest.raises(ValueError, match="occupancy"):
        verify_structure(replace(record, sites=(changed_site, *record.sites[1:])))


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("source_field", "_atom_site_B_iso_or_equiv"),
        ("source_units", "nm^2"),
        ("simulation_field", "U_iso"),
        ("conversion", "B_iso = U_iso"),
        ("simulation_units", "nm^2"),
        ("missing", "default"),
        ("ebsdsim_fallback_b_iso_angstrom_sq", 999),
        ("ebsdsim_fallback_b_iso_angstrom_sq", True),
    ],
)
def test_forsterite_source_rejects_semantically_wrong_thermal_policy(key, value):
    record = load_structure_record(SOURCE)
    changed_policy = {**record.thermal_factor_policy, key: value}

    with pytest.raises(ValueError, match="thermal factor policy"):
        verify_structure(replace(record, thermal_factor_policy=changed_policy))


def test_forsterite_catalog_links_license_publication_and_exact_cif():
    record = load_structure_record(SOURCE)
    catalog = yaml.safe_load(
        (ROOT / "reference/catalog/crystallography-open-database.yml").read_text()
    )
    entry = catalog["entries"][record.identifier]

    assert record.source_record.sha256 == (
        "550b8c89c617267d39e7cb6a07fe6f55cd2343453c1c45ec77738bf6fd25d9cd"
    )
    assert record.source_record.license == "CC0-1.0"
    assert "Smyth" in record.source_record.citation
    assert record.page_uri == "https://www.crystallography.net/cod/9000319.html"
    assert record.retrieved == "2026-07-12"
    assert catalog["license"] == record.license
    assert entry["sha256"] == record.sha256
    assert entry["original_publication"]["year"] == 1973


def test_nonstandard_pbnm_source_is_explicitly_transformed_to_standard_pnma(tmp_path):
    record = load_structure_record(SOURCE)
    original = record.cif_path.read_bytes()

    derived = materialize_simulation_cif(record, tmp_path / "forsterite-pnma.cif")
    crystal = parse_cif_crystal(derived.read_text())
    cell = build_cell_from_cif(crystal)

    assert record.cif_path.read_bytes() == original
    assert (crystal.a, crystal.b, crystal.c) == pytest.approx((10.207, 5.980, 4.756))
    assert crystal.hm_symbol == "P n m a"
    assert crystal.atom_sites[1].fract == pytest.approx((0.27740, 0.25000, 0.99150))
    assert cell.multiplicities.tolist() == [4, 4, 4, 4, 4, 8]
    assert "source_sha256 550b8c89" in derived.read_text()


@pytest.mark.parametrize("identifier", ["../evil", "phase/name", "phase.name", ".."])
def test_source_identifier_rejects_path_capable_grammar(tmp_path, identifier):
    raw = yaml.safe_load(SOURCE.read_text())
    raw["identifier"] = identifier
    raw["cif"] = "source.cif"
    (tmp_path / "source.cif").write_bytes((ROOT / "phases/forsterite/COD-9000319.cif").read_bytes())
    record_path = tmp_path / "source.yml"
    record_path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match="identifier"):
        load_structure_record(record_path)


def test_source_cif_reference_cannot_escape_record_directory(tmp_path):
    raw = yaml.safe_load(SOURCE.read_text())
    raw["cif"] = "../outside.cif"
    (tmp_path.parent / "outside.cif").write_bytes(
        (ROOT / "phases/forsterite/COD-9000319.cif").read_bytes()
    )
    record_path = tmp_path / "source.yml"
    record_path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match="CIF reference"):
        load_structure_record(record_path)
