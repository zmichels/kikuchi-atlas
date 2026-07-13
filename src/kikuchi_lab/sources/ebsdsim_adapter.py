"""Public-API boundary from ebsdsim artifacts to canonical project products."""

from __future__ import annotations

import hashlib
import math
import shutil
import time
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from ebsdsim import master_pattern_from_cif
from ebsdsim.mploader import load_master_pattern

from kikuchi_lab.model.identity import canonical_json
from kikuchi_lab.model.persistence import save_master_product
from kikuchi_lab.model.products import MasterPatternProduct
from kikuchi_lab.model.provenance import PhaseRecord
from kikuchi_lab.model.recipes import SimulationRecipe

from .structure import StructureRecord, materialize_simulation_cif, verify_structure


@dataclass(frozen=True)
class GeneratedMasterPattern:
    ebsdsim_npz: Path
    canonical_product: Path
    manifest: Path
    product: MasterPatternProduct
    npz_sha256: str
    simulation_cif: Path | None = None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _recipe_sha256(recipe: SimulationRecipe) -> str:
    return hashlib.sha256(canonical_json(recipe.to_dict()).encode("utf-8")).hexdigest()


def load_simulation_recipe(path: str | Path) -> SimulationRecipe:
    """Load a versioned YAML simulation recipe with no implicit controls."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.pop("schema_version", None) != 1:
        raise ValueError("unsupported simulation recipe schema")
    name = raw.pop("name", None)
    if not isinstance(name, str) or not name:
        raise ValueError("simulation recipe requires a name")
    expected = set(SimulationRecipe.__dataclass_fields__)
    unknown = set(raw) - expected
    missing = expected - set(raw)
    if unknown or missing:
        raise ValueError(
            f"simulation recipe fields differ: missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    return SimulationRecipe(**raw)


def _close(name: str, observed: Any, expected: float, *, atol: float = 1e-6) -> None:
    try:
        value = float(observed)
    except (TypeError, ValueError) as error:
        raise ValueError(f"resolved {name} is not numeric") from error
    if not math.isclose(value, float(expected), rel_tol=1e-6, abs_tol=atol):
        raise ValueError(f"resolved {name} mismatch: {value!r} != {expected!r}")


def _formula_counts(source: StructureRecord, sites: list[dict[str, Any]]) -> str:
    counts: dict[str, float] = {}
    for site in sites:
        symbol = str(site.get("symbol", ""))
        counts[symbol] = counts.get(symbol, 0.0) + float(site.get("occupancy", 0.0)) * int(
            site.get("multiplicity", 0)
        )
    formula_elements = re_formula_elements(source.formula)
    positive = [counts.get(element, 0.0) for element in formula_elements]
    if not positive or min(positive) <= 0:
        return ""
    scale = min(positive)
    parts: list[str] = []
    for element in formula_elements:
        normalized = counts.get(element, 0.0) / scale
        rounded = round(normalized)
        if not math.isclose(normalized, rounded, abs_tol=1e-6):
            return ""
        parts.append(element if rounded == 1 else f"{element}{rounded}")
    return "".join(parts)


def re_formula_elements(formula: str) -> tuple[str, ...]:
    """Return element symbols in the source formula's deliberate order."""
    import re

    return tuple(re.findall(r"[A-Z][a-z]?", formula))


def _validate_resolved_cell(cell: Any, source: StructureRecord) -> None:
    if not isinstance(cell, dict):
        raise ValueError("ebsdsim metadata is missing the resolved cell")
    if cell.get("space_group") != source.space_group_number:
        raise ValueError(
            f"resolved space group mismatch: {cell.get('space_group')} != "
            f"{source.space_group_number}"
        )
    a, b, c, alpha, beta, gamma = source.lattice_angstrom
    transformed_lattice = (b, c, a, beta, gamma, alpha)
    for name, expected in zip(
        ("a_angstrom", "b_angstrom", "c_angstrom", "alpha_deg", "beta_deg", "gamma_deg"),
        transformed_lattice,
        strict=True,
    ):
        _close(f"cell {name}", cell.get(name), expected)
    sites = cell.get("sites")
    if not isinstance(sites, list) or len(sites) != len(source.sites):
        raise ValueError("resolved site count mismatch")
    expected_multiplicities = source.simulation_setting.get("target_site_multiplicities")
    if not isinstance(expected_multiplicities, list) or len(expected_multiplicities) != len(
        source.sites
    ):
        raise ValueError("source basis transform lacks target site multiplicities")
    for observed, expected, expected_multiplicity in zip(
        sites, source.sites, expected_multiplicities, strict=True
    ):
        if observed.get("symbol") != expected.element:
            raise ValueError(f"resolved site element mismatch for {expected.label}")
        fract = observed.get("fract")
        if not isinstance(fract, list) or len(fract) != 3:
            raise ValueError(f"resolved site coordinates missing for {expected.label}")
        x, y, z = expected.fract
        for axis, coordinate in enumerate((y, z, x)):
            _close(f"site {expected.label} coordinate {axis}", fract[axis], coordinate)
        _close(f"site {expected.label} occupancy", observed.get("occupancy"), expected.occupancy)
        if observed.get("multiplicity") != expected_multiplicity:
            raise ValueError(
                f"resolved site {expected.label} multiplicity mismatch: "
                f"{observed.get('multiplicity')!r} != {expected_multiplicity!r}"
            )
        expected_b_iso = 8.0 * math.pi**2 * expected.u_iso_angstrom_sq
        _close(
            f"site {expected.label} B_iso",
            observed.get("b_iso_angstrom_sq"),
            expected_b_iso,
            atol=1e-5,
        )
    formula = _formula_counts(source, sites)
    if formula != source.formula:
        raise ValueError(f"resolved formula mismatch: {formula!r} != {source.formula!r}")


_RESOLVED_FLOAT_CONTROLS = {
    "voltage_kv": "voltage_kv",
    "dmin": "dmin_nm",
    "energy_binwidth_keV": "energy_binwidth_kev",
    "marginal_coverage": "marginal_coverage",
    "relative_image_stop": "relative_image_stop",
    "bethe_c_strong": "bethe_c_strong",
    "bethe_c_weak": "bethe_c_weak",
    "bethe_c_cutoff": "bethe_c_cutoff",
    "dbdiff_sg_cutoff": "dbdiff_sg_cutoff",
    "sigma_deg": "sigma_deg",
    "omega_deg": "omega_deg",
    "mc_relative_tol": "mc_relative_tol",
}


def _validate_resolved_simulation(metadata: dict[str, Any], recipe: SimulationRecipe) -> None:
    for resolved, requested in _RESOLVED_FLOAT_CONTROLS.items():
        _close(resolved, metadata.get(resolved), getattr(recipe, requested))
    for resolved, requested in {
        "halfw": "halfw",
        "rank": "rank",
        "exact_slow_cpu": "exact_slow_cpu",
    }.items():
        if metadata.get(resolved) != getattr(recipe, requested):
            raise ValueError(f"resolved {resolved} does not match requested recipe")
    backend = metadata.get("mc_backend")
    honored = backend == "surrogate" if recipe.mc_backend == "surrogate" else backend == "gpu_fly_first"
    if not honored:
        raise ValueError(
            f"requested backend {recipe.mc_backend!r} was not honored; resolved {backend!r}"
        )
    used = metadata.get("mc_n_trajectories")
    if isinstance(used, bool) or not isinstance(used, int) or used <= 0:
        raise ValueError("resolved Monte Carlo trajectory count must be a positive integer")
    converged = metadata.get("mc_converged")
    if not isinstance(converged, bool):
        raise ValueError("resolved Monte Carlo convergence flag must be boolean")
    if recipe.mc_auto_stop:
        if used < recipe.mc_min_trajectories:
            raise ValueError("resolved Monte Carlo count is below requested minimum")
        if used > recipe.mc_max_trajectories:
            raise ValueError("resolved Monte Carlo count exceeds requested maximum")
    elif used != recipe.n_trajectories:
        raise ValueError("resolved Monte Carlo trajectory count does not match bounded request")
    elif converged:
        raise ValueError("bounded Monte Carlo run cannot report auto-stop convergence")


def _simulation_phase(source: StructureRecord) -> PhaseRecord:
    a, b, c, alpha, beta, gamma = source.lattice_angstrom
    return PhaseRecord(
        name=source.name,
        formula=source.formula,
        space_group_number=source.space_group_number,
        setting=str(source.simulation_setting["target_setting"]),
        lattice_angstrom=(b, c, a, beta, gamma, alpha),
    )


def _source_phase(source: StructureRecord) -> PhaseRecord:
    return PhaseRecord(
        name=source.name,
        formula=source.formula,
        space_group_number=source.space_group_number,
        setting=source.setting,
        lattice_angstrom=source.lattice_angstrom,
    )


def load_ebsdsim_npz(
    path: str | Path,
    *,
    source: StructureRecord,
    recipe: SimulationRecipe,
    elapsed_seconds: float | None = None,
    expected_npz_sha256: str | None = None,
) -> MasterPatternProduct:
    """Validate and convert one untouched public ebsdsim NPZ artifact.

    ``elapsed_seconds`` is accepted only to prove that runtime does not enter
    canonical metadata or identity; generated bundles record it in the external
    manifest instead.
    """
    verify_structure(source)
    npz_path = Path(path).resolve()
    # Capture the native container checksum before loading or deriving any
    # project-owned representation from it.
    npz_sha256 = _sha256(npz_path)
    if expected_npz_sha256 is not None and npz_sha256 != expected_npz_sha256:
        raise ValueError("native ebsdsim NPZ changed before project ingestion")
    loaded = load_master_pattern(npz_path)
    metadata = loaded.meta
    if not np.isfinite(loaded.integrated_fs).all() or not np.isfinite(loaded.bin_fs).all():
        raise ValueError("ebsdsim fundamental-sector arrays must contain only finite values")
    if not all(key in metadata for key in ("is_centrosymmetric", "needs_southern_hemisphere")):
        raise ValueError("ebsdsim artifact lacks explicit hemisphere semantics")
    _validate_resolved_cell(metadata.get("cell"), source)
    _validate_resolved_simulation(metadata, recipe)
    north, south = loaded.reconstruct_integrated(normalize=None)
    intensity = np.stack((north, south)).astype(np.float32, copy=False)
    if not np.isfinite(intensity).all():
        raise ValueError("ebsdsim master pattern must contain only finite values")
    recipe_sha256 = _recipe_sha256(recipe)
    source_record = source.source_record
    resolved = {
        key: value
        for key, value in metadata.items()
        if key
        in {
            "voltage_kv",
            "grid_size",
            "halfw",
            "dmin",
            "energy_binwidth_keV",
            "rank",
            "exact_slow_cpu",
            "bethe_c_strong",
            "bethe_c_weak",
            "bethe_c_cutoff",
            "dbdiff_sg_cutoff",
            "marginal_coverage",
            "relative_image_stop",
            "mc_backend",
            "sigma_deg",
            "omega_deg",
            "mc_n_trajectories",
            "mc_converged",
            "mc_relative_tol",
            "n_mc_bins",
            "n_bins_run",
            "stopped_by_relative_change",
            "last_relative_change",
            "pg_num",
            "pg_symbol",
        }
    }
    basis_transform = {
        key: source.simulation_setting[key]
        for key in (
            "source_setting",
            "target_setting",
            "target_lattice_from_source",
            "target_fractional_from_source",
            "target_site_multiplicities",
        )
    }
    canonical_metadata = {
        "phase": _simulation_phase(source).to_dict(),
        "source_structure": {
            "identifier": source.identifier,
            "sha256": source.sha256,
            "source_id": source_record.source_id,
            "retrieved": source.retrieved,
            "page_uri": source.page_uri,
            "provenance": source_record.to_dict(),
            "thermal_factor_policy": source.thermal_factor_policy,
            "simulation_setting": source.simulation_setting,
            "original_phase": _source_phase(source).to_dict(),
            "basis_transform": basis_transform,
        },
        "generator": {"name": "ebsdsim", "version": version("ebsdsim")},
        "simulation": {
            "recipe_id": recipe.recipe_id,
            "recipe_sha256": recipe_sha256,
            "voltage_kv": recipe.voltage_kv,
            "requested": recipe.to_dict(),
            "requested_backend": recipe.mc_backend,
            "resolved_backend": metadata["mc_backend"],
            "resolved": resolved,
            "control_evidence": {
                "native_reported": [
                    "mc_converged",
                    "mc_n_trajectories",
                    "mc_relative_tol",
                ],
                "invocation_only": [
                    "mc_auto_stop",
                    "mc_min_trajectories",
                    "mc_max_trajectories",
                ],
            },
            "upstream_npz_sha256": npz_sha256,
        },
        "projection": "Lambert square equal-area",
        "hemisphere_order": ["north", "south"],
        "energy_kev": recipe.voltage_kv,
        "intensity_units": "raw dynamical intensity",
        "coordinate_frame": "crystal:Pnma-derived-from-Pbnm",
        "provenance_links": [
            source_record.source_id,
            recipe.recipe_id,
            f"sha256:{npz_sha256}",
        ],
    }
    return MasterPatternProduct.from_array(intensity, metadata=canonical_metadata)


def _write_manifest(
    *,
    npz_path: Path,
    canonical_path: Path,
    product: MasterPatternProduct,
    source: StructureRecord,
    recipe: SimulationRecipe,
    simulation_cif: Path | None = None,
    elapsed_seconds: float | None = None,
    npz_sha256: str | None = None,
) -> Path:
    manifest = npz_path.with_suffix(".manifest.json")
    payload = {
        "schema_version": 1,
        "source_id": source.source_record.source_id,
        "recipe_id": recipe.recipe_id,
        "ebsdsim_npz": npz_path.name,
        "ebsdsim_npz_sha256": npz_sha256 or _sha256(npz_path),
        "canonical_product": canonical_path.name,
        "canonical_array_sha256": product.array_sha256,
        "master_product_id": product.product_id,
        "simulation_controls": {
            "requested": {
                "mc_auto_stop": recipe.mc_auto_stop,
                "mc_min_trajectories": recipe.mc_min_trajectories,
                "mc_max_trajectories": recipe.mc_max_trajectories,
                "mc_relative_tol": recipe.mc_relative_tol,
            },
            "native_reported": {
                key: product.metadata_dict()["simulation"]["resolved"][key]
                for key in ("mc_converged", "mc_n_trajectories", "mc_relative_tol")
            },
            "unreported_by_ebsdsim": [
                "mc_auto_stop",
                "mc_min_trajectories",
                "mc_max_trajectories",
            ],
        },
    }
    if elapsed_seconds is not None:
        payload["elapsed_seconds"] = float(elapsed_seconds)
    if simulation_cif is not None:
        payload.update(
            {
                "simulation_cif": simulation_cif.name,
                "simulation_cif_sha256": _sha256(simulation_cif),
                "basis_transform": {
                    key: source.simulation_setting[key]
                    for key in (
                        "source_setting",
                        "target_setting",
                        "target_fractional_from_source",
                        "target_lattice_from_source",
                    )
                },
            }
        )
    manifest.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    return manifest


def save_simulation_bundle(
    ebsdsim_npz: str | Path,
    *,
    output_root: str | Path,
    source: StructureRecord,
    recipe: SimulationRecipe,
) -> GeneratedMasterPattern:
    """Copy an untouched upstream NPZ and write validated derived artifacts."""
    original = Path(ebsdsim_npz).resolve()
    output = Path(output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    checksum = _sha256(original)
    upstream = output / f"ebsdsim-{checksum[:16]}.npz"
    if original != upstream:
        shutil.copyfile(original, upstream)
    copied_checksum = _sha256(upstream)
    if copied_checksum != checksum:
        raise ValueError("copied ebsdsim NPZ checksum differs from native source")
    product = load_ebsdsim_npz(
        upstream,
        source=source,
        recipe=recipe,
        expected_npz_sha256=checksum,
    )
    canonical = save_master_product(output / f"{product.product_id}.npz", product)
    manifest = _write_manifest(
        npz_path=upstream,
        canonical_path=canonical,
        product=product,
        source=source,
        recipe=recipe,
        npz_sha256=checksum,
    )
    return GeneratedMasterPattern(upstream, canonical, manifest, product, checksum)


def generate_master_pattern(
    *,
    source: StructureRecord,
    recipe: SimulationRecipe,
    output_npz: str | Path,
) -> GeneratedMasterPattern:
    """Run ebsdsim's public CIF API and validate all resulting artifacts."""
    verify_structure(source)
    requested_output = Path(output_npz).resolve()
    simulation_cif = materialize_simulation_cif(
        source, requested_output.with_suffix(".simulation.cif")
    )
    started = time.perf_counter()
    mp = master_pattern_from_cif(
        simulation_cif,
        voltage_kv=recipe.voltage_kv,
        halfw=recipe.halfw,
        dmin=recipe.dmin_nm,
        energy_binwidth_keV=recipe.energy_binwidth_kev,
        n_trajectories=recipe.n_trajectories,
        sigma_deg=recipe.sigma_deg,
        omega_deg=recipe.omega_deg,
        rank=recipe.rank,
        chunk_size=recipe.chunk_size,
        marginal_coverage=recipe.marginal_coverage,
        relative_image_stop=recipe.relative_image_stop,
        mc_backend=recipe.mc_backend,
        bethe_c_strong=recipe.bethe_c_strong,
        bethe_c_weak=recipe.bethe_c_weak,
        bethe_c_cutoff=recipe.bethe_c_cutoff,
        dbdiff_sg_cutoff=recipe.dbdiff_sg_cutoff,
        mc_auto_stop=recipe.mc_auto_stop,
        mc_relative_tol=recipe.mc_relative_tol,
        mc_min_trajectories=recipe.mc_min_trajectories,
        mc_max_trajectories=recipe.mc_max_trajectories,
        exact_slow_cpu=recipe.exact_slow_cpu,
    )
    saved = mp.save(requested_output).resolve()
    native_npz_sha256 = _sha256(saved)
    elapsed = time.perf_counter() - started
    product = load_ebsdsim_npz(
        saved,
        source=source,
        recipe=recipe,
        expected_npz_sha256=native_npz_sha256,
    )
    canonical = save_master_product(saved.with_name(f"{product.product_id}.npz"), product)
    manifest = _write_manifest(
        npz_path=saved,
        canonical_path=canonical,
        product=product,
        source=source,
        recipe=recipe,
        simulation_cif=simulation_cif,
        elapsed_seconds=elapsed,
        npz_sha256=native_npz_sha256,
    )
    return GeneratedMasterPattern(
        saved, canonical, manifest, product, native_npz_sha256, simulation_cif
    )
