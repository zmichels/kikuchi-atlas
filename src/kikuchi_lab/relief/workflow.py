"""Content-addressed atomic publication of spherical intensity-relief globes."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path

import numpy as np

from kikuchi_lab import __version__
from kikuchi_lab.model import load_master_product
from kikuchi_lab.model.identity import plain_data, stable_id

from .field import build_spherical_scalar_field
from .mapping import (
    build_relief_geometry,
    filter_spherical_values,
    map_source_field,
    sample_mapped_field,
)
from .mesh import (
    ReliefFieldArtifact,
    relief_field_npz_bytes,
    relief_stl_bytes,
    validate_canonical_relief_mesh,
    write_relief_preview,
)
from .recipes import load_relief_globe_recipe
from .topology import build_icosphere


@dataclass(frozen=True)
class ReliefGlobeBuildResult:
    build_id: str
    path: Path
    manifest: Path
    stl: Path
    preview: Path
    field: Path
    validation: Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _array_record(value: np.ndarray) -> dict[str, object]:
    array = np.asarray(value)
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "sha256": hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest(),
    }


def _file_record(path: Path) -> dict[str, object]:
    return {"bytes": path.stat().st_size, "sha256": _sha256_file(path)}


def _software_versions() -> dict[str, str]:
    """Capture the complete runtime identity once for identity and manifest."""
    return {
        "python": platform.python_version(),
        "kikuchi-lab": __version__,
        "numpy": version("numpy"),
        "scipy": version("scipy"),
        "kikuchipy": version("kikuchipy"),
        "trimesh": version("trimesh"),
        "matplotlib": version("matplotlib"),
    }


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) is None:
        raise ValueError("phase name cannot form a safe lowercase ASCII slug")
    return slug


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(
            plain_data(payload),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_tree(root: Path) -> None:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            descriptor = os.open(path, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    for directory in sorted(
        (path for path in root.rglob("*") if path.is_dir()),
        key=lambda path: (-len(path.relative_to(root).parts), str(path)),
    ):
        _fsync_directory(directory)
    _fsync_directory(root)


def _require_fresh_destinations(partial: Path, completed: Path) -> None:
    if completed.exists():
        raise FileExistsError(f"completed relief globe bundle already exists: {completed}")
    if partial.exists():
        raise FileExistsError(f"partial relief globe bundle already exists: {partial}")


def _artifact(samples, filtered: np.ndarray, geometry) -> ReliefFieldArtifact:
    rows = np.asarray(samples.source_rows, dtype=np.int32)
    columns = np.asarray(samples.source_columns, dtype=np.int32)
    return ReliefFieldArtifact(
        directions=np.asarray(geometry.directions, dtype=np.float64),
        hemisphere=np.where(geometry.directions[:, 2] >= 0.0, 1, -1).astype(np.int8),
        source_rows=rows[:, (0, 1, 0, 1)],
        source_columns=columns[:, (0, 0, 1, 1)],
        weights=np.asarray(samples.weights, dtype=np.float64),
        sampled_raw=np.asarray(samples.raw_values, dtype=np.float64),
        mapped=np.asarray(samples.mapped_values, dtype=np.float64),
        filtered=np.asarray(filtered, dtype=np.float64),
        radii_mm=np.asarray(geometry.radii_mm, dtype=np.float64),
        faces=np.asarray(geometry.faces, dtype=np.int64),
    )


def _identity(
    recipe,
    master,
    source_file_sha256,
    field,
    topology,
    mapped,
    filter_report,
    validation,
    versions,
) -> dict[str, object]:
    return {
        "schema": "kikuchi.relief-globe-build/v1",
        "recipe": recipe.identity_dict(),
        "recipe_id": recipe.recipe_id,
        "source": {
            "master_product_id": master.product_id,
            "array_sha256": master.array_sha256,
            "file_sha256": source_file_sha256,
        },
        "field": {
            "field_id": field.field_id,
            "coordinate_frame": field.coordinate_frame,
            "projection": field.projection,
            "seam": asdict(field.seam),
        },
        "mapping": {
            "lower_percentile": mapped.lower_percentile,
            "upper_percentile": mapped.upper_percentile,
            "lower_value": mapped.lower_value,
            "upper_value": mapped.upper_value,
            "gamma": mapped.gamma,
            "direction": recipe.mapping.direction,
        },
        "topology": {
            "topology_id": topology.topology_id,
            "subdivisions": topology.subdivisions,
            "directions": _array_record(topology.directions),
            "faces": _array_record(topology.faces),
        },
        "interpolation": {
            "contract": "lambert-square-bilinear-ledger/north-owns-equator/v1"
        },
        "filter": asdict(filter_report),
        "validation": validation.to_dict(),
        "software_versions": versions,
    }


def _manifest(identity, recipe, master, field, topology, mapped, filter_report,
              geometry, validation, staging: Path) -> dict[str, object]:
    files = {
        path.name: _file_record(path)
        for path in sorted(staging.iterdir(), key=lambda item: item.name)
        if path.is_file() and path.name != "relief-manifest.json"
    }
    metadata = master.metadata_dict()
    bounds = validation.bounds_mm
    maximum_diameter = 2.0 * validation.maximum_radius_mm
    return {
        "schema": "kikuchi.relief-globe-manifest/v1",
        "build_id": stable_id("relief-globe-build", identity),
        "identity": identity,
        "recipe_id": recipe.recipe_id,
        "recipe": recipe.identity_dict(),
        "source": {
            "master_product_id": master.product_id,
            "array_sha256": master.array_sha256,
            "file_sha256": recipe.source.file_sha256,
            "phase": metadata["phase"],
            "grid": metadata["array"],
            "projection": field.projection,
            "coordinate_frame": field.coordinate_frame,
            "hemisphere_order": metadata["hemisphere_order"],
            "seam": asdict(field.seam),
        },
        "mapping": identity["mapping"],
        "topology": {
            **identity["topology"],
            "vertex_count": len(topology.directions),
            "triangle_count": len(topology.faces),
            "euler_characteristic": validation.euler_characteristic,
        },
        "interpolation": identity["interpolation"],
        "filter": asdict(filter_report),
        "geometry": {
            "base_radius_mm": geometry.base_radius_mm,
            "maximum_relief_mm": geometry.maximum_relief_mm,
            "minimum_radius_mm": validation.minimum_radius_mm,
            "maximum_radius_mm": validation.maximum_radius_mm,
            "maximum_possible_diameter_mm": maximum_diameter,
            "bounds_mm": bounds,
        },
        "validation_report": "mesh-validation.json",
        "validation": validation.to_dict(),
        "units": "millimetre",
        "software_versions": identity["software_versions"],
        "files": files,
    }


def _result(build_id: str, completed: Path) -> ReliefGlobeBuildResult:
    stl = tuple(completed.glob("*-intensity-relief-globe.stl"))
    preview = tuple(completed.glob("*-intensity-relief-preview.png"))
    expected = {"relief-field.npz", "mesh-validation.json", "relief-manifest.json"}
    if len(stl) != 1 or len(preview) != 1 or not expected.issubset(
        path.name for path in completed.iterdir()
    ) or len(tuple(completed.iterdir())) != 5:
        raise RuntimeError("published relief globe bundle has an invalid export inventory")
    return ReliefGlobeBuildResult(
        build_id=build_id,
        path=completed,
        manifest=completed / "relief-manifest.json",
        stl=stl[0],
        preview=preview[0],
        field=completed / "relief-field.npz",
        validation=completed / "mesh-validation.json",
    )


def build_relief_globe(
    master_pattern_path: str | Path,
    recipe_path: str | Path,
    output_root: str | Path,
) -> ReliefGlobeBuildResult:
    """Build, validate, and atomically publish one immutable relief globe."""
    recipe = load_relief_globe_recipe(recipe_path)
    source_path = Path(master_pattern_path).resolve()
    source_file_sha256 = _sha256_file(source_path)
    if source_file_sha256 != recipe.source.file_sha256:
        raise ValueError("master product file SHA-256 does not match relief recipe")
    master = load_master_product(source_path)
    field = build_spherical_scalar_field(master, recipe.source)
    topology = build_icosphere(recipe.geometry.subdivisions)
    mapped = map_source_field(field, recipe.mapping)
    samples = sample_mapped_field(mapped, topology)
    filtered, filter_report = filter_spherical_values(
        samples.mapped_values,
        topology.directions,
        recipe.geometry.base_diameter_mm / 2.0,
        recipe.filter,
    )
    geometry = build_relief_geometry(
        topology,
        filtered,
        recipe.geometry.base_diameter_mm,
        recipe.geometry.maximum_relief_mm,
    )
    validation = validate_canonical_relief_mesh(geometry, topology, recipe.fdm_context)
    versions = _software_versions()
    identity = _identity(
        recipe,
        master,
        source_file_sha256,
        field,
        topology,
        mapped,
        filter_report,
        validation,
        versions,
    )
    build_id = stable_id("relief-globe-build", identity)
    root = Path(output_root).resolve()
    partial = root / f"{build_id}.partial"
    completed = root / build_id
    root.mkdir(parents=True, exist_ok=True)
    _require_fresh_destinations(partial, completed)
    partial.mkdir()
    try:
        stem = f"{_safe_slug(master.metadata_dict()['phase']['name'])}-intensity-relief"
        (partial / f"{stem}-globe.stl").write_bytes(
            relief_stl_bytes(geometry, topology, validation)
        )
        write_relief_preview(
            partial / f"{stem}-preview.png",
            geometry,
            topology,
            validation,
            lower_percentile=mapped.lower_percentile,
            upper_percentile=mapped.upper_percentile,
            gamma=mapped.gamma,
            filter_fwhm_mm=filter_report.fwhm_mm,
        )
        artifact = _artifact(samples, filtered, geometry)
        (partial / "relief-field.npz").write_bytes(
            relief_field_npz_bytes(artifact, geometry, topology, validation)
        )
        _write_json(partial / "mesh-validation.json", validation.to_dict())
        manifest = _manifest(
            identity, recipe, master, field, topology, mapped, filter_report,
            geometry, validation, partial
        )
        _write_json(partial / "relief-manifest.json", manifest)
        _fsync_tree(partial)
        os.replace(partial, completed)
        _fsync_directory(root)
    except Exception:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return _result(build_id, completed)
