"""Atomic, content-addressed publication of Ice reflector-ridge globes."""

from __future__ import annotations

import hashlib
import io
import json
import platform
import shutil
import zipfile
from dataclasses import asdict, dataclass, replace
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path

import numpy as np
import trimesh
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from kikuchi_lab import __version__
from kikuchi_lab.globe_mesh import (
    GlobeGeometrySpec,
    ReliefMeshValidation,
    build_radial_geometry,
    duplicate_triangle_count,
    validate_globe_mesh,
)
from kikuchi_lab.model import identity as identity_module
from kikuchi_lab.model.identity import plain_data, stable_id
from kikuchi_lab.reflectors.catalog import _cohorts
from kikuchi_lab.reflectors.contracts import ReflectorCatalog, ReflectorMember
from kikuchi_lab.reflectors import build_reflector_catalog, load_reflector_recipe
from kikuchi_lab.relief.topology import build_icosphere
from kikuchi_lab.relief.workflow import _fsync_tree, _publish_staging, _write_json
from kikuchi_lab.sources.structure import load_structure_record

from .field import RidgeField, evaluate_reflector_ridges
from .recipes import load_reflector_ridge_recipe


REFLECTOR_GLOBE_BUILD_SCHEMA = "kikuchi.reflector-ridge-globe-build/v1"
REFLECTOR_GLOBE_MANIFEST_SCHEMA = "kikuchi.reflector-ridge-globe-manifest/v1"
REFLECTOR_GLOBE_VALIDATION_SCHEMA = "kikuchi.reflector-ridge-mesh-validation/v1"
REFLECTOR_GLOBE_LEDGER_SCHEMA = "kikuchi.reflector-ridge-ledger/v2"
REFLECTOR_GLOBE_BUNDLE_LAYOUT_CONTRACT = "atomic-six-file-reflector-ridge-globe/v1"
REFLECTOR_GLOBE_NPZ_CONTRACT = "zip-stored-npy/fixed-order-1980-epoch-mode-0600/v1"
REFLECTOR_GLOBE_STL_CONTRACT = "trimesh-binary-stl/process-false/serialization-safe-radial-range/v2"
REFLECTOR_GLOBE_PREVIEW_CONTRACT = "matplotlib-figure-canvas-agg/900x900-rgba/v1"
REFLECTOR_GLOBE_JSON_CONTRACT = "json/sorted-indent-2-utf8-newline/v1"

_FIELD_ARRAY_ORDER = ("directions", "ridge_values", "contributor_counts", "radii_mm", "faces")
_STL_RADIAL_SAFETY_MARGIN_MM = 1e-5
_ICE_SOURCE_STRUCTURE_ID = "COD-1572233-O-sublattice"
_ICE_SOURCE_STRUCTURE_SHA256 = "4327a279e414a62f861d143e18570e9d741bbbb7d04dd2fb471c930988f95b81"
_ICE_REFLECTION_RECIPE_ID = "reflector-recipe-ea20e740ed0ebfef"
_ICE_ENERGY_KEV = 20.0
_ICE_ELIGIBILITY_MIN_WEIGHT = 0.08
_ICE_TIE_POLICY = "keep_equal_weights_together"
_ICE_COHORT_COUNT = 4
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ICE_CATALOG_RECIPE = _PROJECT_ROOT / "recipes/reflectors/ice-ih-catalog.yml"
_ICE_SOURCE_RECORD = _PROJECT_ROOT / "phases/ice-ih/source.yml"


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


@dataclass(frozen=True)
class _ValidatedCatalogSelection:
    selected_member_ids: tuple[str, ...]
    rejected_member_ids: tuple[str, ...]


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
        "ledger": REFLECTOR_GLOBE_LEDGER_SCHEMA,
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


def _expected_catalog_selection() -> dict[str, object]:
    return {
        "frame": "crystal reciprocal Cartesian",
        "eligibility_min_weight": _ICE_ELIGIBILITY_MIN_WEIGHT,
        "tie_policy": _ICE_TIE_POLICY,
        "cohort_count": _ICE_COHORT_COUNT,
        "source_master_relative_factor": 0.03,
        "selection_relative_factor": 0.22,
        "weight_exponent": 2.0,
        "selection_rule": (
            "retain signed reflectors with abs(F) >= "
            "selection_relative_factor * max(abs(F)); then collapse axial pairs"
        ),
        "weight_normalization": (
            "(abs(structure_factor) / max(abs(structure_factor))) ** weight_exponent"
        ),
        "package_versions": {
            package: version(package) for package in ("diffpy-structure", "diffsims", "orix")
        },
    }


@lru_cache(maxsize=1)
def _canonical_ice_catalog() -> ReflectorCatalog:
    """Rebuild the trusted Ice reflector catalog from tracked source and recipe files."""
    recipe = load_reflector_recipe(_ICE_CATALOG_RECIPE)
    source = load_structure_record(_ICE_SOURCE_RECORD)
    return build_reflector_catalog(source, recipe)


def _catalog_evidence(catalog: ReflectorCatalog) -> tuple[dict[str, object], ...]:
    return tuple(_member_evidence(member) for member in catalog.members)


def _validate_catalog_recipe(catalog: ReflectorCatalog, recipe) -> _ValidatedCatalogSelection:
    """Authenticate and independently derive the bounded Ice catalog selection."""
    selection = recipe.selection
    if selection.source_structure_id != _ICE_SOURCE_STRUCTURE_ID:
        raise ValueError("ridge recipe source_structure_id does not match canonical Ice source")
    if selection.energy_kev != _ICE_ENERGY_KEV:
        raise ValueError("ridge recipe energy_kev does not match canonical Ice energy")
    if selection.eligibility_min_weight != _ICE_ELIGIBILITY_MIN_WEIGHT:
        raise ValueError("ridge recipe eligibility_min_weight does not match canonical Ice policy")
    if selection.tie_policy != _ICE_TIE_POLICY:
        raise ValueError("ridge recipe tie_policy does not match canonical Ice policy")
    if selection.cohort_count != _ICE_COHORT_COUNT:
        raise ValueError("ridge recipe cohort_count does not match canonical Ice policy")

    if catalog.source_structure_id != _ICE_SOURCE_STRUCTURE_ID:
        raise ValueError("catalog source_structure_id does not match canonical Ice source")
    if catalog.source_structure_sha256 != _ICE_SOURCE_STRUCTURE_SHA256:
        raise ValueError("catalog source_structure_sha256 does not match canonical Ice source")
    if catalog.energy_kev != _ICE_ENERGY_KEV:
        raise ValueError("catalog energy_kev does not match canonical Ice energy")
    if catalog.reflection_recipe_id != _ICE_REFLECTION_RECIPE_ID:
        raise ValueError("catalog reflection_recipe_id does not match canonical Ice recipe")
    if plain_data(catalog.selection) != _expected_catalog_selection():
        raise ValueError("catalog selection policy does not match canonical Ice policy")
    canonical = _canonical_ice_catalog()
    if catalog.catalog_id != canonical.catalog_id:
        raise ValueError("catalog_id does not match canonical Ice reflector catalog")
    if _catalog_evidence(catalog) != _catalog_evidence(canonical):
        raise ValueError("catalog member evidence does not match canonical Ice reflector catalog")

    members = sorted(
        catalog.members,
        key=lambda member: (-member.normalized_weight, member.hkl, member.member_id),
    )
    member_ids = tuple(member.member_id for member in members)
    if len(members) != 30 or len(set(member_ids)) != 30:
        raise ValueError("Ice ridge catalog must contain exactly 30 unique members")
    if tuple(member.member_id for member in catalog.members) != member_ids:
        raise ValueError("Ice ridge catalog members are not in canonical ranking order")

    eligible = [
        member for member in members if member.normalized_weight >= _ICE_ELIGIBILITY_MIN_WEIGHT
    ]
    rejected = [
        member for member in members if member.normalized_weight < _ICE_ELIGIBILITY_MIN_WEIGHT
    ]
    if len(eligible) != 15 or len(rejected) != 15:
        raise ValueError(
            "Ice ridge catalog must contain exactly 15 selected and 15 rejected members"
        )
    eligible_weight_blocks = {member.normalized_weight for member in eligible}
    if len(eligible_weight_blocks) != 6:
        raise ValueError("Ice ridge catalog must contain exactly 6 eligible weight blocks")

    cohort_by_member = _cohorts(eligible, _ICE_COHORT_COUNT)
    strongest_weight = max(eligible_weight_blocks)
    weakest_weight = min(eligible_weight_blocks)
    if {
        cohort_by_member[member.member_id]
        for member in eligible
        if member.normalized_weight == strongest_weight
    } != {4}:
        raise ValueError("Ice ridge catalog strongest eligible block must be cohort 4")
    if {
        cohort_by_member[member.member_id]
        for member in eligible
        if member.normalized_weight == weakest_weight
    } != {1}:
        raise ValueError("Ice ridge catalog weakest eligible block must be cohort 1")

    for member in members:
        expected_cohort = cohort_by_member.get(member.member_id)
        expected_eligible = expected_cohort is not None
        if member.eligible != expected_eligible or member.cohort != expected_cohort:
            raise ValueError(
                "catalog selected/rejected membership or cohort assignment does not match "
                "canonical Ice threshold and tie policy"
            )

    return _ValidatedCatalogSelection(
        selected_member_ids=tuple(member.member_id for member in eligible),
        rejected_member_ids=tuple(member.member_id for member in rejected),
    )


def _member_evidence(member: ReflectorMember) -> dict[str, object]:
    return {
        "member_id": member.member_id,
        "hkl": list(member.hkl),
        "normal_crystal": member.normal_crystal.tolist(),
        "dspacing_angstrom": member.dspacing_angstrom,
        "bragg_half_width_rad": member.bragg_half_width_rad,
        "structure_factor_abs": member.structure_factor_abs,
        "normalized_weight": member.normalized_weight,
        "cohort": member.cohort,
    }


def _catalog_provenance(
    catalog: ReflectorCatalog,
    field: RidgeField,
    selection: _ValidatedCatalogSelection,
) -> dict[str, object]:
    """Materialize source-to-ridge evidence without retaining upstream objects."""
    contributors = {item.member_id: item for item in field.ledger}
    selected_ids = set(selection.selected_member_ids)
    selected: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    threshold = float(catalog.selection["eligibility_min_weight"])
    for member in catalog.members:
        evidence = _member_evidence(member)
        if member.member_id in selected_ids:
            contributor = contributors[member.member_id]
            evidence.update(
                {
                    "effective_half_width_rad": contributor.effective_half_width_rad,
                    "height_mm": contributor.height_mm,
                }
            )
            selected.append(evidence)
        else:
            evidence["rejection_reasons"] = [
                {
                    "code": "below_eligibility_min_weight",
                    "normalized_weight": member.normalized_weight,
                    "eligibility_min_weight": threshold,
                }
            ]
            rejected.append(evidence)
    if set(contributors) != {item["member_id"] for item in selected}:
        raise ValueError("ridge contributor ledger differs from selected catalog evidence")
    if tuple(item["member_id"] for item in selected) != selection.selected_member_ids:
        raise ValueError("selected catalog evidence differs from validated Ice selection")
    if tuple(item["member_id"] for item in rejected) != selection.rejected_member_ids:
        raise ValueError("rejected catalog evidence differs from validated Ice selection")
    return {
        "source_structure": {
            "structure_id": catalog.source_structure_id,
            "checksum_sha256": catalog.source_structure_sha256,
        },
        "reflection_recipe_id": catalog.reflection_recipe_id,
        "energy_kev": catalog.energy_kev,
        "selection_policy": {
            **plain_data(catalog.selection),
            "source_master_relative_factor_provenance": ("recovered source-master reflector gate"),
        },
        "member_counts": {
            "catalog": len(catalog.members),
            "selected": len(selected),
            "rejected": len(rejected),
        },
        "selected_members": selected,
        "rejected_members": rejected,
    }


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


def _serialization_safe_values(values: np.ndarray, maximum_relief_mm: float) -> np.ndarray:
    """Keep float32 STL coordinates inside the configured closed radial interval.

    Binary STL stores coordinates as float32.  Reserving this minute inward
    margin prevents component rounding from placing an otherwise exact 40 or
    43 mm radial vertex outside the published contract.  The affine mapping
    remains monotone, so the ridge field stays raised-outward.
    """
    margin = _STL_RADIAL_SAFETY_MARGIN_MM
    if 2.0 * margin >= maximum_relief_mm:
        raise ValueError("STL radial safety margin leaves no relief range")
    return margin / maximum_relief_mm + (1.0 - 2.0 * margin / maximum_relief_mm) * values


def _validate_serialized_stl(payload: bytes, source: ReliefMeshValidation) -> ReliefMeshValidation:
    """Validate the exact binary STL consumers receive and report its measurements."""
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
    duplicate_count = duplicate_triangle_count(faces)
    degenerate_count = int(np.count_nonzero(loaded.area_faces <= 1e-12))
    failures: list[str] = []
    if not loaded.is_watertight:
        failures.append("watertight")
    if not loaded.is_winding_consistent:
        failures.append("winding")
    if loaded.body_count != 1:
        failures.append("one connected body")
    if not loaded.is_volume or not np.isfinite(loaded.volume) or loaded.volume <= 0.0:
        failures.append("positive volume")
    if duplicate_count:
        failures.append("duplicate triangles")
    if degenerate_count:
        failures.append("degenerate triangles")
    if not np.isfinite(certificate).all() or np.any(
        certificate <= source.radial_certificate_tolerance
    ):
        failures.append("radial projection")
    if radii.min() < 40.0 or radii.max() > 43.0:
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
        degenerate_triangle_count=degenerate_count,
        duplicate_triangle_count=duplicate_count,
        radial_certificate_minimum=float(certificate.min()),
    )


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
    validated_selection = _validate_catalog_recipe(catalog, recipe)
    topology = build_icosphere(recipe.geometry.subdivisions)
    field = evaluate_reflector_ridges(catalog, recipe, topology.directions)
    geometry = build_radial_geometry(
        topology,
        _serialization_safe_values(field.values, recipe.geometry.maximum_relief_mm),
        GlobeGeometrySpec(
            recipe.geometry.base_diameter_mm,
            recipe.geometry.maximum_relief_mm,
            recipe.geometry.subdivisions,
        ),
    )
    validation = validate_globe_mesh(geometry, topology, GlobeGeometrySpec(80.0, 3.0, 7))
    versions, contracts = _software_versions(), _contracts()
    provenance = _catalog_provenance(catalog, field, validated_selection)
    selected_ids = list(validated_selection.selected_member_ids)
    rejected_ids = list(validated_selection.rejected_member_ids)
    identity = {
        "schema": REFLECTOR_GLOBE_BUILD_SCHEMA,
        "contracts": contracts,
        "recipe": recipe.identity_dict(),
        "recipe_id": recipe.recipe_id,
        "catalog_id": catalog.catalog_id,
        "source_structure": provenance["source_structure"],
        "reflection_recipe_id": catalog.reflection_recipe_id,
        "catalog_selection_policy": provenance["selection_policy"],
        "selected_member_ids": selected_ids,
        "rejected_member_ids": rejected_ids,
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
        validation = _validate_serialized_stl(payload, validation)
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
            "schema": REFLECTOR_GLOBE_LEDGER_SCHEMA,
            "catalog_id": catalog.catalog_id,
            "recipe_id": recipe.recipe_id,
            "field_id": field.field_id,
            "selected_member_ids": selected_ids,
            "contributors": [asdict(item) for item in field.ledger],
            "source_to_mesh_provenance": provenance,
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
            "product_kind": "reflector_defined_ridges",
            "build_id": build_id,
            "identity": identity,
            "contracts": contracts,
            "catalog_id": catalog.catalog_id,
            "source_provenance": {
                "source_structure": provenance["source_structure"],
                "reflection_recipe_id": catalog.reflection_recipe_id,
                "selection_policy": provenance["selection_policy"],
                "selected_member_count": provenance["member_counts"]["selected"],
                "rejected_member_count": provenance["member_counts"]["rejected"],
                "ledger": result.ledger.name,
            },
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
