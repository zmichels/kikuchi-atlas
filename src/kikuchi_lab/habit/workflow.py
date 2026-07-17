"""Content-addressed, atomic publication of printable crystal-habit bundles."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path

from kikuchi_lab import __version__
from kikuchi_lab.habit.crystallography import expand_habit_planes
from kikuchi_lab.habit.geometry import (
    orient_and_scale_habit,
    solve_convex_habit,
    triangulate_habit,
)
from kikuchi_lab.habit.mesh import (
    stl_bytes,
    validate_triangle_mesh,
    write_habit_preview,
)
from kikuchi_lab.habit.parity import MTEXParityReport, compare_mtex_reference
from kikuchi_lab.habit.recipes import load_habit_recipe
from kikuchi_lab.model.identity import plain_data, stable_id


SOLVER_CONTRACT = {
    "name": "deterministic-convex-halfspace-intersection",
    "relative_tolerance": 1e-9,
    "visible_polygon_order": "expanded-plane-order",
}
MESH_CONTRACT = {
    "name": "canonical-outward-polygon-fan-triangulation",
    "validation_processing": False,
    "minimum_triangle_area_mm2": 1e-12,
    "self_intersection": "convex-watertight-volume-proof",
}


@dataclass(frozen=True)
class HabitBuildResult:
    build_id: str
    path: Path
    manifest: Path
    stl: Path
    preview: Path
    validation: Path
    parity: Path | None = None


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


def _file_record(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    return {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _software_versions() -> dict[str, str]:
    return {
        "kikuchi-lab": __version__,
        "matplotlib": version("matplotlib"),
        "numpy": version("numpy"),
        "orix": version("orix"),
        "scipy": version("scipy"),
        "trimesh": version("trimesh"),
    }


def _manifest(
    identity: dict[str, object],
    recipe: object,
    phase: object,
    planes: tuple[object, ...],
    polygon: object,
    triangles: object,
    report: object,
    parity_report: MTEXParityReport | None,
    staging: Path,
) -> dict[str, object]:
    visible_polygons = [asdict(face) for face in polygon.faces]
    triangle_to_polygon = [
        {
            "triangle_index": triangle_index,
            "polygon_index": int(polygon_index),
            "plane_id": polygon.faces[int(polygon_index)].plane_id,
        }
        for triangle_index, polygon_index in enumerate(triangles.triangle_face_indices)
    ]
    files = {
        path.name: _file_record(path)
        for path in sorted(staging.iterdir(), key=lambda item: item.name)
        if path.is_file() and path.name != "habit-manifest.json"
    }
    manifest = {
        "schema": "kikuchi.habit-manifest/v1",
        "build_id": stable_id("habit-build", identity),
        "identity": identity,
        "recipe_id": recipe.recipe_id,
        "recipe": recipe.identity_dict(),
        "phase_source": {
            "cif_sha256": recipe.phase.cif_sha256,
            "provenance": dict(recipe.phase.provenance),
        },
        "phase": asdict(phase),
        "orientation_matrix": [list(row) for row in recipe.orientation_matrix],
        "expanded_planes": [asdict(plane) for plane in planes],
        "vertices_mm": polygon.vertices.tolist(),
        "visible_polygons": visible_polygons,
        "visible_family_labels": sorted({face.family_label for face in polygon.faces}),
        "inactive_plane_ids": list(polygon.inactive_plane_ids),
        "inactive_plane_count": len(polygon.inactive_plane_ids),
        "triangles": triangles.triangles.tolist(),
        "triangle_count": len(triangles.triangles),
        "triangle_to_polygon": triangle_to_polygon,
        "units": "millimetre",
        "tolerances": {
            "solver_relative": SOLVER_CONTRACT["relative_tolerance"],
            "minimum_triangle_area_mm2": MESH_CONTRACT["minimum_triangle_area_mm2"],
        },
        "software_versions": _software_versions(),
        "validation_report": "mesh-validation.json",
        "validation": report.to_dict(),
        "files": files,
    }
    if parity_report is not None:
        manifest["mtex_parity_report"] = "mtex-parity.json"
        manifest["mtex_parity"] = parity_report.to_dict()
    return manifest


def _require_fresh_destinations(staging: Path, completed: Path) -> None:
    if completed.exists():
        raise FileExistsError(f"completed habit bundle already exists: {completed}")
    if staging.exists():
        raise FileExistsError(f"partial habit bundle already exists: {staging}")


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
    directories = sorted(
        (path for path in root.rglob("*") if path.is_dir()),
        key=lambda path: (-len(path.relative_to(root).parts), str(path)),
    )
    for directory in directories:
        _fsync_directory(directory)
    _fsync_directory(root)


def _result(build_id: str, completed: Path) -> HabitBuildResult:
    stl_files = tuple(completed.glob("*-habit.stl"))
    preview_files = tuple(completed.glob("*-habit-preview.png"))
    if len(stl_files) != 1 or len(preview_files) != 1:
        raise RuntimeError("published habit bundle has an invalid export inventory")
    return HabitBuildResult(
        build_id=build_id,
        path=completed,
        manifest=completed / "habit-manifest.json",
        stl=stl_files[0],
        preview=preview_files[0],
        validation=completed / "mesh-validation.json",
        parity=(
            completed / "mtex-parity.json"
            if (completed / "mtex-parity.json").is_file()
            else None
        ),
    )


def build_habit(
    recipe_path: str | Path,
    output_root: str | Path,
    *,
    mtex_reference: str | Path | None = None,
) -> HabitBuildResult:
    """Build, validate, and atomically publish one immutable habit bundle."""

    recipe = load_habit_recipe(recipe_path)
    phase, planes = expand_habit_planes(recipe)
    crystal_polygon = solve_convex_habit(planes)
    parity_report = (
        compare_mtex_reference(crystal_polygon, mtex_reference)
        if mtex_reference is not None
        else None
    )
    polygon = orient_and_scale_habit(
        crystal_polygon,
        recipe.orientation_matrix,
        recipe.maximum_dimension_mm,
    )
    triangles = triangulate_habit(polygon)
    report = validate_triangle_mesh(triangles, polygon, recipe.fdm_context)
    identity = {
        "schema": "kikuchi.habit-build/v1",
        "recipe": recipe.identity_dict(),
        "phase": asdict(phase),
        "solver": SOLVER_CONTRACT,
        "mesh_contract": MESH_CONTRACT,
    }
    if mtex_reference is not None:
        reference_bytes = Path(mtex_reference).read_bytes()
        identity["mtex_reference_sha256"] = hashlib.sha256(reference_bytes).hexdigest()
    build_id = stable_id("habit-build", identity)
    root = Path(output_root).resolve()
    staging = root / f"{build_id}.partial"
    completed = root / build_id
    root.mkdir(parents=True, exist_ok=True)
    _require_fresh_destinations(staging, completed)
    staging.mkdir()
    try:
        stem = f"{_safe_slug(recipe.phase.name)}-habit"
        (staging / f"{stem}.stl").write_bytes(stl_bytes(triangles))
        write_habit_preview(staging / f"{stem}-preview.png", polygon)
        _write_json(staging / "mesh-validation.json", report.to_dict())
        if parity_report is not None:
            _write_json(staging / "mtex-parity.json", parity_report.to_dict())
        manifest = _manifest(
            identity,
            recipe,
            phase,
            planes,
            polygon,
            triangles,
            report,
            parity_report,
            staging,
        )
        _write_json(staging / "habit-manifest.json", manifest)
        _fsync_tree(staging)
        os.replace(staging, completed)
        _fsync_directory(root)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return _result(build_id, completed)
