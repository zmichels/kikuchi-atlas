"""Atomic publication of separate stereographic-master Ice intensity globes."""

from __future__ import annotations

import hashlib
import io
import json
import platform
import shutil
import zipfile
from dataclasses import asdict, dataclass, replace
from importlib.metadata import version
from pathlib import Path

import numpy as np
import trimesh
import yaml
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from kikuchi_lab import __version__
from kikuchi_lab.globe_mesh import (
    GlobeGeometrySpec,
    build_radial_geometry,
    duplicate_triangle_count,
    validate_globe_mesh,
)
from kikuchi_lab.model.identity import plain_data, stable_id
from kikuchi_lab.relief.topology import build_icosphere
from kikuchi_lab.relief.workflow import _fsync_tree, _publish_staging
from kikuchi_lab.workflows.ice_kinematical import simulate_ice_kinematical

from .intensity import STEREOGRAPHIC_SAMPLING_CONTRACT, build_ice_intensity_field, sample_stereographic_grid


INTENSITY_BUILD_SCHEMA = "kikuchi.ice-intensity-globe-build/v1"
INTENSITY_MANIFEST_SCHEMA = "kikuchi.ice-intensity-globe-manifest/v1"
INTENSITY_VALIDATION_SCHEMA = "kikuchi.ice-intensity-mesh-validation/v1"
_ARRAY_ORDER = ("directions", "sampled_raw", "mapped_values", "radii_mm", "faces")
_STL_RADIAL_SAFETY_MARGIN_MM = 1e-5


@dataclass(frozen=True)
class IceIntensityGlobeBuildResult:
    build_id: str
    path: Path
    manifest: Path
    stl: Path
    preview: Path
    field: Path
    ledger: Path
    validation: Path


@dataclass(frozen=True)
class IceIntensityRecipe:
    base_diameter_mm: float
    maximum_relief_mm: float
    subdivisions: int
    lower_percentile: float
    upper_percentile: float
    gamma: float
    recipe_id: str

    def identity_dict(self) -> dict[str, object]:
        return {
            "schema": "kikuchi.ice-intensity-globe-recipe/v1",
            "geometry": {"base_diameter_mm": self.base_diameter_mm, "maximum_relief_mm": self.maximum_relief_mm, "topology": "icosphere", "subdivisions": self.subdivisions, "direction": "bright_outward"},
            "mapping": {"percentiles": {"lower": self.lower_percentile, "upper": self.upper_percentile}, "gamma": self.gamma},
        }


def _recipe(path: str | Path) -> IceIntensityRecipe:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    try:
        if set(raw) != {"schema", "geometry", "mapping"} or raw["schema"] != "kikuchi.ice-intensity-globe-recipe/v1":
            raise ValueError
        geometry, mapping = raw["geometry"], raw["mapping"]
        if set(geometry) != {"base_diameter_mm", "maximum_relief_mm", "topology", "subdivisions", "direction"} or set(mapping) != {"percentiles", "gamma"} or set(mapping["percentiles"]) != {"lower", "upper"}:
            raise ValueError
        diameter, relief = float(geometry["base_diameter_mm"]), float(geometry["maximum_relief_mm"])
        lower, upper, gamma = float(mapping["percentiles"]["lower"]), float(mapping["percentiles"]["upper"]), float(mapping["gamma"])
        subdivisions = geometry["subdivisions"]
        if geometry["topology"] != "icosphere" or geometry["direction"] != "bright_outward" or type(subdivisions) is not int or not 0 <= subdivisions <= 7 or not np.isfinite((diameter, relief, lower, upper, gamma)).all() or diameter <= 0 or relief <= 0 or not 0 <= lower < upper <= 100 or gamma <= 0:
            raise ValueError
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid Ice intensity globe recipe") from error
    identity = {"schema": raw["schema"], "geometry": geometry, "mapping": mapping}
    return IceIntensityRecipe(diameter, relief, subdivisions, lower, upper, gamma, stable_id("ice-intensity-globe-recipe", identity))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(plain_data(payload), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _npz_bytes(arrays: dict[str, np.ndarray]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in _ARRAY_ORDER:
            content = io.BytesIO()
            np.lib.format.write_array(content, np.ascontiguousarray(arrays[name]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type, info.external_attr = zipfile.ZIP_STORED, 0o600 << 16
            archive.writestr(info, content.getvalue())
    return stream.getvalue()


def _preview(path: Path, geometry) -> None:
    triangles = np.asarray(geometry.vertices)[np.asarray(geometry.faces)]
    values = np.asarray(geometry.filtered_values)[np.asarray(geometry.faces)].mean(axis=1)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    from matplotlib import colormaps
    rgba = colormaps["magma"](values)
    rgba[:, :3] *= (0.35 + 0.65 * np.clip(normals @ np.array((0.35, -0.45, 0.82)), 0.0, 1.0))[:, None]
    figure = Figure(figsize=(9, 9), dpi=100, facecolor="white")
    canvas = FigureCanvasAgg(figure)
    axes = figure.add_subplot(111, projection="3d")
    axes.add_collection3d(Poly3DCollection(triangles, facecolors=rgba, linewidths=0))
    radius = geometry.base_radius_mm + geometry.maximum_relief_mm
    axes.set(xlim=(-radius, radius), ylim=(-radius, radius), zlim=(-radius, radius))
    axes.set_box_aspect((1, 1, 1))
    axes.view_init(elev=22, azim=38)
    axes.set_axis_off()
    canvas.print_png(path, metadata={"Software": "kikuchi-lab"})
    figure.clear()


def _result(build_id: str, path: Path) -> IceIntensityGlobeBuildResult:
    return IceIntensityGlobeBuildResult(build_id, path, path / "intensity-globe-manifest.json", path / "ice-ih-intensity-relief.stl", path / "ice-ih-intensity-relief-preview.png", path / "intensity-field.npz", path / "intensity-ledger.json", path / "mesh-validation.json")


def _serialization_safe_values(values: np.ndarray, maximum_relief_mm: float) -> np.ndarray:
    margin = _STL_RADIAL_SAFETY_MARGIN_MM
    if 2.0 * margin >= maximum_relief_mm:
        raise ValueError("STL radial safety margin leaves no relief range")
    return margin / maximum_relief_mm + (1.0 - 2.0 * margin / maximum_relief_mm) * values


def _validate_serialized_stl(payload: bytes, source, geometry):
    """Validate the exact float32 STL delivered to consumers."""
    loaded = trimesh.load_mesh(io.BytesIO(payload), file_type="stl", process=True)
    if not isinstance(loaded, trimesh.Trimesh):
        raise RuntimeError("binary STL did not load as one mesh")
    vertices, faces = np.asarray(loaded.vertices), np.asarray(loaded.faces)
    radii = np.linalg.norm(vertices, axis=1)
    triangles = vertices[faces]
    certificate = np.einsum(
        "ij,ij->i",
        np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]),
        triangles[:, 0],
    )
    failures: list[str] = []
    if not loaded.is_watertight:
        failures.append("watertight")
    if not loaded.is_winding_consistent:
        failures.append("winding")
    if loaded.body_count != 1:
        failures.append("one connected body")
    if not loaded.is_volume or not np.isfinite(loaded.volume) or loaded.volume <= 0.0:
        failures.append("positive volume")
    if duplicate_triangle_count(faces):
        failures.append("duplicate triangles")
    if np.count_nonzero(loaded.area_faces <= 1e-12):
        failures.append("degenerate triangles")
    if not np.isfinite(certificate).all() or np.any(certificate <= source.radial_certificate_tolerance):
        failures.append("radial projection")
    # The exact delivered STL is float32.  Values were deliberately mapped
    # inward by _STL_RADIAL_SAFETY_MARGIN_MM before export, so permit only that
    # tiny coordinate-rounding envelope around this recipe's physical range.
    lower_bound = geometry.base_radius_mm - _STL_RADIAL_SAFETY_MARGIN_MM
    upper_bound = (
        geometry.base_radius_mm
        + geometry.maximum_relief_mm
        + _STL_RADIAL_SAFETY_MARGIN_MM
    )
    if radii.min() < lower_bound or radii.max() > upper_bound:
        failures.append("serialized radial range")
    if failures:
        raise ValueError("serialized STL validation failed: " + ", ".join(failures))
    return replace(
        source,
        watertight=True,
        winding_consistent=True,
        body_count=1,
        euler_characteristic=int(loaded.euler_number),
        positive_volume=True,
        volume_mm3=float(loaded.volume),
        surface_area_mm2=float(loaded.area),
        bounds_mm=(tuple(loaded.bounds[0]), tuple(loaded.bounds[1])),
        minimum_radius_mm=float(radii.min()),
        maximum_radius_mm=float(radii.max()),
        degenerate_triangle_count=int(np.count_nonzero(loaded.area_faces <= 1e-12)),
        duplicate_triangle_count=duplicate_triangle_count(faces),
        radial_certificate_minimum=float(certificate.min()),
    )


def build_ice_intensity_globe(kinematical_recipe: str | Path, globe_recipe: str | Path, output_root: str | Path) -> IceIntensityGlobeBuildResult:
    """Build a separate, validated, stereographic-master intensity relief globe."""
    recipe = _recipe(globe_recipe)
    simulation = simulate_ice_kinematical(kinematical_recipe)
    field = build_ice_intensity_field(simulation)
    lower, upper = np.percentile(field.raw_values, (recipe.lower_percentile, recipe.upper_percentile))
    if not np.isfinite((lower, upper)).all() or upper <= lower:
        raise ValueError("Ice intensity master has a collapsed global percentile range")
    mapped_upper = np.clip((field.upper_grid - lower) / (upper - lower), 0.0, 1.0) ** recipe.gamma
    mapped_lower = np.clip((field.lower_grid - lower) / (upper - lower), 0.0, 1.0) ** recipe.gamma
    topology = build_icosphere(recipe.subdivisions)
    sampled_raw = sample_stereographic_grid(field, topology.directions, upper_grid=field.upper_grid, lower_grid=field.lower_grid)
    mapped = sample_stereographic_grid(field, topology.directions, upper_grid=mapped_upper, lower_grid=mapped_lower)
    mapped = _serialization_safe_values(mapped, recipe.maximum_relief_mm)
    geometry = build_radial_geometry(topology, mapped, GlobeGeometrySpec(recipe.base_diameter_mm, recipe.maximum_relief_mm, recipe.subdivisions))
    validation = validate_globe_mesh(geometry, topology, GlobeGeometrySpec(recipe.base_diameter_mm, recipe.maximum_relief_mm, recipe.subdivisions))
    versions = {"python": platform.python_version(), "kikuchi-lab": __version__, "numpy": version("numpy"), "trimesh": version("trimesh"), "matplotlib": version("matplotlib")}
    identity = {"schema": INTENSITY_BUILD_SCHEMA, "product_kind": "intensity_relief", "recipe": recipe.identity_dict(), "recipe_id": recipe.recipe_id, "kinematical_recipe_id": simulation.master_stereographic.metadata["recipe_id"], "master_product_id": field.master_product_id, "field_id": field.field_id, "topology_id": topology.topology_id, "sampling_contract": STEREOGRAPHIC_SAMPLING_CONTRACT, "software_versions": versions}
    build_id = stable_id("ice-intensity-globe-build", identity)
    root, completed = Path(output_root).resolve(), Path(output_root).resolve() / build_id
    partial, result = root / f"{build_id}.partial", _result(build_id, completed)
    root.mkdir(parents=True, exist_ok=True)
    if completed.exists() or partial.exists():
        raise FileExistsError(f"Ice intensity globe destination already exists: {completed if completed.exists() else partial}")
    partial.mkdir()
    try:
        mesh = trimesh.Trimesh(vertices=np.array(geometry.vertices, copy=True), faces=np.array(geometry.faces, copy=True), process=False, validate=False)
        payload = mesh.export(file_type="stl")
        if not isinstance(payload, bytes):
            raise RuntimeError("STL export did not return bytes")
        validation = _validate_serialized_stl(payload, validation, geometry)
        (partial / result.stl.name).write_bytes(payload)
        _preview(partial / result.preview.name, geometry)
        arrays = {"directions": np.asarray(topology.directions, dtype="<f8"), "sampled_raw": np.asarray(sampled_raw, dtype="<f8"), "mapped_values": np.asarray(mapped, dtype="<f8"), "radii_mm": np.asarray(geometry.radii_mm, dtype="<f8"), "faces": np.asarray(topology.faces, dtype="<i8")}
        (partial / result.field.name).write_bytes(_npz_bytes(arrays))
        _write_json(partial / result.ledger.name, {"schema": "kikuchi.ice-intensity-ledger/v1", "source_kind": field.source_kind, "field_id": field.field_id, "sampling_contract": STEREOGRAPHIC_SAMPLING_CONTRACT, "seam": asdict(field.seam), "mapping": {"lower_percentile": recipe.lower_percentile, "upper_percentile": recipe.upper_percentile, "lower_value": float(lower), "upper_value": float(upper), "gamma": recipe.gamma}})
        _write_json(partial / result.validation.name, {"schema": INTENSITY_VALIDATION_SCHEMA, **validation.to_dict()})
        files = {p.name: {"bytes": p.stat().st_size, "sha256": _sha256(p)} for p in sorted(partial.iterdir()) if p.is_file()}
        _write_json(partial / result.manifest.name, {"schema": INTENSITY_MANIFEST_SCHEMA, "product_kind": "intensity_relief", "build_id": build_id, "identity": identity, "recipe_id": recipe.recipe_id, "field_id": field.field_id, "topology": {"topology_id": topology.topology_id, "subdivisions": topology.subdivisions, "vertices": len(topology.directions), "faces": len(topology.faces)}, "validation": validation.to_dict(), "files": files})
        expected = {result.stl.name, result.preview.name, result.field.name, result.ledger.name, result.validation.name, result.manifest.name}
        if {p.name for p in partial.iterdir()} != expected:
            raise RuntimeError("staged Ice intensity globe has an invalid export inventory")
        _fsync_tree(partial)
        _publish_staging(partial, completed, root)
    except Exception:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return result


__all__ = ["IceIntensityGlobeBuildResult", "build_ice_intensity_globe"]
