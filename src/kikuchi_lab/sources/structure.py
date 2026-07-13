"""Tracked CIF source loading and independent catalog validation."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

import yaml
from CifFile import ReadCif

from kikuchi_lab.model.provenance import SourceRecord


_REQUIRED_THERMAL_FACTOR_POLICY = {
    "source_field": "_atom_site_U_iso_or_equiv",
    "source_units": "angstrom^2",
    "simulation_field": "B_iso",
    "conversion": "B_iso = 8 * pi^2 * U_iso",
    "simulation_units": "angstrom^2",
    "missing": "reject",
}


@dataclass(frozen=True)
class SiteRecord:
    label: str
    element: str
    fract: tuple[float, float, float]
    occupancy: float
    u_iso_angstrom_sq: float


@dataclass(frozen=True)
class StructureRecord:
    record_path: Path
    cif_path: Path
    identifier: str
    sha256: str
    retrieved: str
    uri: str
    page_uri: str
    license: str
    license_uri: str
    copying_policy: str
    citation: str
    name: str
    formula: str
    space_group_number: int
    setting: str
    lattice_angstrom: tuple[float, float, float, float, float, float]
    sites: tuple[SiteRecord, ...]
    thermal_factor_policy: dict[str, Any]
    simulation_setting: dict[str, Any]

    @property
    def source_record(self) -> SourceRecord:
        return SourceRecord(
            uri=self.uri,
            sha256=self.sha256,
            license=self.license,
            citation=self.citation,
        )

    @property
    def site_occupancies(self) -> tuple[float, ...]:
        return tuple(site.occupancy for site in self.sites)

    @property
    def site_u_iso_angstrom_sq(self) -> tuple[float, ...]:
        return tuple(site.u_iso_angstrom_sq for site in self.sites)


@dataclass(frozen=True)
class VerifiedStructure:
    sha256_matches: bool
    parsed_formula: str
    parsed_space_group_number: int
    parsed_lattice_angstrom: tuple[float, float, float, float, float, float]
    site_labels: tuple[str, ...]
    site_elements: tuple[str, ...]
    site_occupancies: tuple[float, ...]
    site_u_iso_angstrom_sq: tuple[float, ...]
    occupancy_source: str
    thermal_factor_policy: dict[str, Any]
    missing_thermal_factor_labels: tuple[str, ...]


def _required(mapping: dict[str, Any], key: str) -> Any:
    if key not in mapping:
        raise ValueError(f"structure record requires {key}")
    return mapping[key]


def load_structure_record(path: str | Path) -> StructureRecord:
    """Load a project-owned YAML structure record and resolve its tracked CIF."""
    record_path = Path(path).resolve()
    raw = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError("unsupported structure record schema")
    phase = _required(raw, "phase")
    if not isinstance(phase, dict):
        raise ValueError("phase must be an object")
    raw_sites = _required(raw, "sites")
    if not isinstance(raw_sites, list) or not raw_sites:
        raise ValueError("sites must be a non-empty list")
    sites = tuple(
        SiteRecord(
            label=str(_required(site, "label")),
            element=str(_required(site, "element")),
            fract=tuple(float(value) for value in _required(site, "fract")),
            occupancy=float(_required(site, "occupancy")),
            u_iso_angstrom_sq=float(_required(site, "u_iso_angstrom_sq")),
        )
        for site in raw_sites
    )
    if any(len(site.fract) != 3 for site in sites):
        raise ValueError("each site fractional coordinate must contain three values")
    lattice = tuple(float(value) for value in _required(phase, "lattice_angstrom"))
    if len(lattice) != 6:
        raise ValueError("phase lattice_angstrom must contain six values")
    identifier = str(_required(raw, "identifier"))
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", identifier) is None:
        raise ValueError("structure identifier contains path-capable characters")
    cif_reference = Path(str(_required(raw, "cif")))
    if cif_reference.is_absolute():
        raise ValueError("CIF reference must be relative to the source record")
    cif_path = (record_path.parent / cif_reference).resolve()
    if not cif_path.is_relative_to(record_path.parent):
        raise ValueError("CIF reference escapes the source-record directory")
    return StructureRecord(
        record_path=record_path,
        cif_path=cif_path,
        identifier=identifier,
        sha256=str(_required(raw, "sha256")),
        retrieved=str(_required(raw, "retrieved")),
        uri=str(_required(raw, "uri")),
        page_uri=str(_required(raw, "page_uri")),
        license=str(_required(raw, "license")),
        license_uri=str(_required(raw, "license_uri")),
        copying_policy=str(_required(raw, "copying_policy")),
        citation=str(_required(raw, "citation")),
        name=str(_required(phase, "name")),
        formula=str(_required(phase, "formula")),
        space_group_number=int(_required(phase, "space_group_number")),
        setting=str(_required(phase, "setting")),
        lattice_angstrom=lattice,
        sites=sites,
        thermal_factor_policy=dict(_required(raw, "thermal_factor_policy")),
        simulation_setting=dict(_required(raw, "simulation_setting")),
    )


def _block_tags(block: Any) -> dict[str, str]:
    return {str(key).lower(): key for key in block.keys()}


def _scalar(block: Any, tags: dict[str, str], name: str) -> str:
    key = tags.get(name.lower())
    if key is None:
        raise ValueError(f"CIF is missing {name}")
    return str(block[key]).strip().strip("'\"")


def _number(value: Any) -> float:
    cleaned = re.sub(r"\(\d+\)$", "", str(value).strip().strip("'\""))
    return float(cleaned)


def _symbol(label: str) -> str:
    match = re.match(r"([A-Za-z]{1,2})", label)
    if match is None:
        raise ValueError(f"cannot infer element from site label {label!r}")
    candidate = match.group(1)
    return candidate[0].upper() + candidate[1:].lower()


def _loop_column(block: Any, tags: dict[str, str], name: str) -> list[Any] | None:
    key = tags.get(name.lower())
    if key is None:
        return None
    return list(block[key])


def _assert_close(label: str, actual: float, expected: float, tolerance: float = 1e-7) -> None:
    if abs(actual - expected) > tolerance:
        raise ValueError(f"{label} mismatch: CIF {actual!r}, catalog {expected!r}")


def _validate_thermal_factor_policy(policy: dict[str, Any]) -> None:
    for key, expected in _REQUIRED_THERMAL_FACTOR_POLICY.items():
        if policy.get(key) != expected:
            raise ValueError(
                f"thermal factor policy {key} must be {expected!r}; got {policy.get(key)!r}"
            )
    fallback = policy.get("ebsdsim_fallback_b_iso_angstrom_sq")
    if (
        isinstance(fallback, bool)
        or not isinstance(fallback, (int, float))
        or not math.isfinite(float(fallback))
        or not math.isclose(float(fallback), 0.5, rel_tol=0.0, abs_tol=0.0)
    ):
        raise ValueError(
            "thermal factor policy must document ebsdsim fallback as exactly 0.5 angstrom^2"
        )


def verify_structure(record: StructureRecord) -> VerifiedStructure:
    """Parse the tracked CIF and compare every simulation-relevant source value."""
    _validate_thermal_factor_policy(record.thermal_factor_policy)
    payload = record.cif_path.read_bytes()
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if actual_sha256 != record.sha256:
        raise ValueError(
            f"CIF checksum mismatch: expected {record.sha256}, observed {actual_sha256}"
        )
    cif = ReadCif(StringIO(payload.decode("utf-8")))
    if not cif.keys():
        raise ValueError("CIF has no data block")
    block = cif[list(cif.keys())[0]]
    tags = _block_tags(block)

    formula = re.sub(r"\s+", "", _scalar(block, tags, "_cod_original_formula_sum"))
    if formula != record.formula:
        raise ValueError(f"formula mismatch: CIF {formula!r}, catalog {record.formula!r}")
    space_group = int(_number(_scalar(block, tags, "_space_group_IT_number")))
    if space_group != record.space_group_number:
        raise ValueError(
            f"space group mismatch: CIF {space_group}, catalog {record.space_group_number}"
        )
    lattice_names = (
        "_cell_length_a",
        "_cell_length_b",
        "_cell_length_c",
        "_cell_angle_alpha",
        "_cell_angle_beta",
        "_cell_angle_gamma",
    )
    lattice = tuple(_number(_scalar(block, tags, name)) for name in lattice_names)
    for name, actual, expected in zip(lattice_names, lattice, record.lattice_angstrom, strict=True):
        _assert_close(name, actual, expected)

    labels = _loop_column(block, tags, "_atom_site_label")
    xs = _loop_column(block, tags, "_atom_site_fract_x")
    ys = _loop_column(block, tags, "_atom_site_fract_y")
    zs = _loop_column(block, tags, "_atom_site_fract_z")
    if labels is None or xs is None or ys is None or zs is None:
        raise ValueError("CIF is missing atom-site labels or fractional coordinates")
    occupancies = _loop_column(block, tags, "_atom_site_occupancy")
    u_iso = _loop_column(block, tags, "_atom_site_U_iso_or_equiv")
    parsed_labels = tuple(str(value) for value in labels)
    parsed_elements = tuple(_symbol(label) for label in parsed_labels)
    parsed_occupancies = (
        tuple(1.0 for _ in labels)
        if occupancies is None
        else tuple(_number(value) for value in occupancies)
    )
    missing_thermal = (
        parsed_labels
        if u_iso is None
        else tuple(
            label
            for label, value in zip(parsed_labels, u_iso)
            if str(value).strip() in {"", ".", "?"}
        )
    )
    if missing_thermal and record.thermal_factor_policy.get("missing") == "reject":
        raise ValueError(f"missing thermal factors for sites: {', '.join(missing_thermal)}")
    parsed_u_iso = tuple(_number(value) for value in (u_iso or []))

    if len(record.sites) != len(parsed_labels):
        raise ValueError("site count mismatch")
    for index, expected in enumerate(record.sites):
        if parsed_labels[index] != expected.label or parsed_elements[index] != expected.element:
            raise ValueError(f"site identity mismatch at index {index}")
        for axis, values in enumerate((xs, ys, zs)):
            _assert_close(
                f"site {expected.label} fractional coordinate {axis}",
                _number(values[index]),
                expected.fract[axis],
            )
        _assert_close(
            f"site {expected.label} occupancy", parsed_occupancies[index], expected.occupancy
        )
        _assert_close(
            f"site {expected.label} U_iso",
            parsed_u_iso[index],
            expected.u_iso_angstrom_sq,
        )

    return VerifiedStructure(
        sha256_matches=True,
        parsed_formula=formula,
        parsed_space_group_number=space_group,
        parsed_lattice_angstrom=lattice,
        site_labels=parsed_labels,
        site_elements=parsed_elements,
        site_occupancies=parsed_occupancies,
        site_u_iso_angstrom_sq=parsed_u_iso,
        occupancy_source=(
            "implicit CIF default 1.0" if occupancies is None else "_atom_site_occupancy"
        ),
        thermal_factor_policy=dict(record.thermal_factor_policy),
        missing_thermal_factor_labels=tuple(missing_thermal),
    )


def materialize_simulation_cif(record: StructureRecord, path: str | Path) -> Path:
    """Write a deterministic Pnma simulation view without altering the COD source.

    COD 9000319 is expressed in non-standard Pbnm, whereas ebsdsim's numbered
    space-group operations use standard Pnma. The documented cyclic permutation
    ``(a', b', c') = (b, c, a)`` and ``(x', y', z') = (y, z, x)`` preserves the
    structure and restores the correct special-position multiplicities.
    """
    verify_structure(record)
    setting = record.simulation_setting
    if setting.get("source_setting") != record.setting:
        raise ValueError("simulation setting source does not match catalog setting")
    if setting.get("target_setting") != "P n m a":
        raise ValueError("ebsdsim simulation setting must be standard P n m a")
    if setting.get("target_lattice_from_source") != ["b", "c", "a"]:
        raise ValueError("unsupported simulation lattice transformation")
    if setting.get("target_fractional_from_source") != ["y", "z", "x"]:
        raise ValueError("unsupported simulation coordinate transformation")

    a, b, c, alpha, beta, gamma = record.lattice_angstrom
    transformed_lattice = (b, c, a, beta, gamma, alpha)
    lines = [
        f"# Derived simulation view of {record.identifier}; authoritative CIF remains unchanged.",
        f"# source_sha256 {record.sha256}",
        "# basis_transform source_Pbnm_to_target_Pnma: (a,b,c)->(b,c,a); (x,y,z)->(y,z,x)",
        f"data_{record.identifier.lower().replace('-', '_')}_pnma",
        f"_chemical_formula_sum '{record.formula}'",
        f"_chemical_name_mineral '{record.name}'",
        f"_space_group_IT_number {record.space_group_number}",
        "_symmetry_space_group_name_H-M 'P n m a'",
        f"_cell_length_a {transformed_lattice[0]:.8f}",
        f"_cell_length_b {transformed_lattice[1]:.8f}",
        f"_cell_length_c {transformed_lattice[2]:.8f}",
        f"_cell_angle_alpha {transformed_lattice[3]:.8f}",
        f"_cell_angle_beta {transformed_lattice[4]:.8f}",
        f"_cell_angle_gamma {transformed_lattice[5]:.8f}",
        "loop_",
        "_atom_site_label",
        "_atom_site_type_symbol",
        "_atom_site_fract_x",
        "_atom_site_fract_y",
        "_atom_site_fract_z",
        "_atom_site_occupancy",
        "_atom_site_U_iso_or_equiv",
    ]
    for site in record.sites:
        x, y, z = site.fract
        lines.append(
            f"{site.label} {site.element} {y:.8f} {z:.8f} {x:.8f} "
            f"{site.occupancy:.8f} {site.u_iso_angstrom_sq:.8f}"
        )
    destination = Path(path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination
