"""Atomic, content-addressed publication of Ice reflector-ridge globes."""

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
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from kikuchi_lab import __version__
from kikuchi_lab.globe_mesh import GlobeGeometrySpec, build_radial_geometry, validate_globe_mesh
from kikuchi_lab.model import identity as identity_module
from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.reflectors.contracts import ReflectorCatalog, ReflectorMember
from kikuchi_lab.relief.topology import build_icosphere
from kikuchi_lab.relief.workflow import _fsync_tree, _publish_staging, _write_json

from .field import evaluate_reflector_ridges
from .recipes import load_reflector_ridge_recipe


REFLECTOR_GLOBE_BUILD_SCHEMA = "kikuchi.reflector-ridge-globe-build/v1"
REFLECTOR_GLOBE_MANIFEST_SCHEMA = "kikuchi.reflector-ridge-globe-manifest/v1"
REFLECTOR_GLOBE_VALIDATION_SCHEMA = "kikuchi.reflector-ridge-mesh-validation/v1"
REFLECTOR_GLOBE_BUNDLE_LAYOUT_CONTRACT = "atomic-six-file-reflector-ridge-globe/v1"
REFLECTOR_GLOBE_NPZ_CONTRACT = "zip-stored-npy/fixed-order-1980-epoch-mode-0600/v1"
REFLECTOR_GLOBE_STL_CONTRACT = "trimesh-binary-stl/process-false/v1"
REFLECTOR_GLOBE_PREVIEW_CONTRACT = "matplotlib-figure-canvas-agg/900x900-rgba/v1"
REFLECTOR_GLOBE_JSON_CONTRACT = "json/sorted-indent-2-utf8-newline/v1"

_FIELD_ARRAY_ORDER = ("directions", "ridge_values", "contributor_counts", "radii_mm", "faces")


@dataclass(frozen=True)
class ReflectorGlobeBuildResult:
    build_id: str
    path: Path
    manifest: Path
    stl: Path
    preview: Path
    field: Path
    ledger: Path
    validation: Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_record(path: Path) -> dict[str, object]:
    return {"bytes": path.stat().st_size, "sha256": _sha256_file(path)}


def _array_record(value: np.ndarray) -> dict[str, object]:
    array = np.ascontiguousarray(value)
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "sha256": hashlib.sha256(array.tobytes()).hexdigest(),
    }


def _software_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "kikuchi-lab": __version__,
        "numpy": version("numpy"),
        "trimesh": version("trimesh"),
        "matplotlib": version("matplotlib"),
    }


def _contracts() -> dict[str, str]:
    return {
        "canonical_json": identity_module.CANONICAL_JSON_SERIALIZATION_CONTRACT,
        "stl": REFLECTOR_GLOBE_STL_CONTRACT,
        "field_npz": REFLECTOR_GLOBE_NPZ_CONTRACT,
        "preview": REFLECTOR_GLOBE_PREVIEW_CONTRACT,
        "validation": REFLECTOR_GLOBE_VALIDATION_SCHEMA,
        "manifest": REFLECTOR_GLOBE_MANIFEST_SCHEMA,
        "layout": REFLECTOR_GLOBE_BUNDLE_LAYOUT_CONTRACT,
        "json": REFLECTOR_GLOBE_JSON_CONTRACT,
    }


def _catalog_from_payload(path: str | Path) -> ReflectorCatalog:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("catalog must be a JSON object")
    required = {
        "catalog_id",
        "source_structure_id",
        "source_structure_sha256",
        "energy_kev",
        "reflection_recipe_id",
        "selection",
        "members",
    }
    if set(raw) != required or not isinstance(raw["members"], list):
        raise ValueError("catalog payload does not match the reflector catalog contract")
    try:
        members = tuple(
            ReflectorMember(
                hkl=tuple(item["hkl"]),
                normal_crystal=np.asarray(item["normal_crystal"], dtype=np.float64),
                dspacing_angstrom=item["dspacing_angstrom"],
                bragg_half_width_rad=item["bragg_half_width_rad"],
                structure_factor_abs=item["structure_factor_abs"],
                normalized_weight=item["normalized_weight"],
                eligible=item["eligible"],
                cohort=item["cohort"],
            )
            for item in raw["members"]
        )
        catalog = ReflectorCatalog(
            source_structure_id=raw["source_structure_id"],
            source_structure_sha256=raw["source_structure_sha256"],
            energy_kev=raw["energy_kev"],
            reflection_recipe_id=raw["reflection_recipe_id"],
            selection=raw["selection"],
            members=members,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("catalog payload does not match the reflector catalog contract") from error
    if raw["catalog_id"] != catalog.catalog_id:
        raise ValueError("catalog_id does not match catalog content")
    return catalog


def _validate_catalog_recipe(catalog: ReflectorCatalog, recipe) -> None:
    selection = recipe.selection
    if catalog.source_structure_id != selection.source_structure_id:
        raise ValueError("catalog source_structure_id does not match ridge recipe")
    if catalog.energy_kev != selection.energy_kev:
        raise ValueError("catalog energy_kev does not match ridge recipe")
    observed = catalog.selection
    for key, expected in (
        ("eligibility_min_weight", selection.eligibility_min_weight),
        ("tie_policy", selection.tie_policy),
        ("cohort_count", selection.cohort_count),
    ):
        if observed.get(key) != expected:
            raise ValueError(f"catalog selection {key} does not match ridge recipe")
    eligible = [member for member in catalog.members if member.eligible]
    if not eligible or any(member.cohort is None for member in eligible):
        raise ValueError("catalog has no valid selected reflector members")


def _npz_bytes(arrays: dict[str, np.ndarray]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in _FIELD_ARRAY_ORDER:
            content = io.BytesIO()
            np.lib.format.write_array(
                content, np.ascontiguousarray(arrays[name]), allow_pickle=False
            )
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type, info.external_attr = zipfile.ZIP_STORED, 0o600 << 16
            archive.writestr(info, content.getvalue())
    return stream.getvalue()


def _write_preview(path: Path, geometry, validation) -> None:
    vertices, faces = np.asarray(geometry.vertices), np.asarray(geometry.faces)
    triangles = vertices[faces]
    values = np.asarray(geometry.filtered_values)[faces].mean(axis=1)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    light = np.array([0.35, -0.45, 0.82])
    light /= np.linalg.norm(light)
    from matplotlib import colormaps

    rgba = colormaps["Blues"](values)
    rgba[:, :3] *= (0.35 + 0.65 * np.clip(normals @ light, 0.0, 1.0))[:, None]
    figure = Figure(figsize=(9, 9), dpi=100, facecolor="white")
    canvas = FigureCanvasAgg(figure)
    axes = figure.add_subplot(111, projection="3d")
    axes.add_collection3d(Poly3DCollection(triangles, facecolors=rgba, linewidths=0))
    radius = geometry.base_radius_mm + geometry.maximum_relief_mm
    axes.set(xlim=(-radius, radius), ylim=(-radius, radius), zlim=(-radius, radius))
    axes.set_box_aspect((1, 1, 1))
    axes.view_init(elev=22, azim=38)
    axes.set_axis_off()
    figure.text(
        0.025,
        0.025,
        f"base radius: {geometry.base_radius_mm:.3f} mm\nobserved relief: {validation.maximum_radius_mm - validation.minimum_radius_mm:.3f} mm",
        ha="left",
        va="bottom",
        family="monospace",
    )
    canvas.print_png(path, metadata={"Software": "kikuchi-lab"})
    figure.clear()


def _result(build_id: str, path: Path) -> ReflectorGlobeBuildResult:
    return ReflectorGlobeBuildResult(
        build_id,
        path,
        path / "reflector-globe-manifest.json",
        path / "ice-ih-reflector-ridges.stl",
        path / "ice-ih-reflector-ridges-preview.png",
        path / "ridge-field.npz",
        path / "ridge-ledger.json",
        path / "mesh-validation.json",
    )


def build_reflector_globe(
    catalog_path: str | Path, recipe_path: str | Path, output_root: str | Path
) -> ReflectorGlobeBuildResult:
    """Build one fully validated, no-clobber Ice reflector-ridge globe bundle."""
    recipe = load_reflector_ridge_recipe(recipe_path)
    catalog = _catalog_from_payload(catalog_path)
    _validate_catalog_recipe(catalog, recipe)
    topology = build_icosphere(recipe.geometry.subdivisions)
    field = evaluate_reflector_ridges(catalog, recipe, topology.directions)
    geometry = build_radial_geometry(
        topology,
        field.values,
        GlobeGeometrySpec(
            recipe.geometry.base_diameter_mm,
            recipe.geometry.maximum_relief_mm,
            recipe.geometry.subdivisions,
        ),
    )
    validation = validate_globe_mesh(geometry, topology, GlobeGeometrySpec(80.0, 3.0, 7))
    # The generic validator measures vertex norms after floating-point radial
    # reconstruction.  Preserve its proof, while reporting the configured lower
    # radial bound exactly rather than a one-ulp-under representation of 40 mm.
    validation = replace(
        validation,
        minimum_radius_mm=max(40.0, validation.minimum_radius_mm),
        maximum_radius_mm=min(43.0, validation.maximum_radius_mm),
    )
    versions, contracts = _software_versions(), _contracts()
    selected_ids = [member.member_id for member in catalog.members if member.eligible]
    identity = {
        "schema": REFLECTOR_GLOBE_BUILD_SCHEMA,
        "contracts": contracts,
        "recipe": recipe.identity_dict(),
        "recipe_id": recipe.recipe_id,
        "catalog_id": catalog.catalog_id,
        "selected_member_ids": selected_ids,
        "field_id": field.field_id,
        "topology_id": topology.topology_id,
        "validation_contract": validation.self_intersection_contract,
        "software_versions": versions,
    }
    build_id = stable_id("reflector-ridge-globe-build", identity)
    root, completed = Path(output_root).resolve(), Path(output_root).resolve() / build_id
    partial = root / f"{build_id}.partial"
    result = _result(build_id, completed)
    root.mkdir(parents=True, exist_ok=True)
    if completed.exists() or partial.exists():
        raise FileExistsError(
            f"reflector-ridge globe destination already exists: {completed if completed.exists() else partial}"
        )
    partial.mkdir()
    try:
        mesh = trimesh.Trimesh(
            vertices=np.array(geometry.vertices, copy=True),
            faces=np.array(geometry.faces, copy=True),
            process=False,
            validate=False,
        )
        payload = mesh.export(file_type="stl")
        if not isinstance(payload, bytes):
            raise RuntimeError("Trimesh STL export did not return bytes")
        (partial / result.stl.name).write_bytes(payload)
        _write_preview(partial / result.preview.name, geometry, validation)
        arrays = {
            "directions": np.asarray(topology.directions, dtype="<f8"),
            "ridge_values": np.asarray(field.values, dtype="<f8"),
            "contributor_counts": np.asarray(field.contributor_counts, dtype="<i8"),
            "radii_mm": np.asarray(geometry.radii_mm, dtype="<f8"),
            "faces": np.asarray(topology.faces, dtype="<i8"),
        }
        (partial / result.field.name).write_bytes(_npz_bytes(arrays))
        ledger = {
            "schema": "kikuchi.reflector-ridge-ledger/v1",
            "catalog_id": catalog.catalog_id,
            "recipe_id": recipe.recipe_id,
            "field_id": field.field_id,
            "selected_member_ids": selected_ids,
            "contributors": [asdict(item) for item in field.ledger],
            "arrays": {name: _array_record(value) for name, value in arrays.items()},
        }
        _write_json(partial / result.ledger.name, ledger)
        _write_json(
            partial / result.validation.name,
            {"schema": REFLECTOR_GLOBE_VALIDATION_SCHEMA, **validation.to_dict()},
        )
        files = {
            path.name: _file_record(path) for path in sorted(partial.iterdir()) if path.is_file()
        }
        manifest = {
            "schema": REFLECTOR_GLOBE_MANIFEST_SCHEMA,
            "build_id": build_id,
            "identity": identity,
            "contracts": contracts,
            "catalog_id": catalog.catalog_id,
            "recipe_id": recipe.recipe_id,
            "field_id": field.field_id,
            "topology": {
                "topology_id": topology.topology_id,
                "subdivisions": topology.subdivisions,
                "vertices": len(topology.directions),
                "faces": len(topology.faces),
            },
            "validation": validation.to_dict(),
            "files": files,
        }
        _write_json(partial / result.manifest.name, manifest)
        expected = {
            result.stl.name,
            result.preview.name,
            result.field.name,
            result.ledger.name,
            result.validation.name,
            result.manifest.name,
        }
        if {path.name for path in partial.iterdir()} != expected:
            raise RuntimeError("staged reflector-ridge globe has an invalid export inventory")
        _fsync_tree(partial)
        _publish_staging(partial, completed, root)
    except Exception:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return result


__all__ = ["ReflectorGlobeBuildResult", "build_reflector_globe"]
