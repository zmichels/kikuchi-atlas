"""Immutable publication of exact oriented spherical fields and figures."""

from __future__ import annotations

import errno
import hashlib
import io
import os
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import numpy as np

from kikuchi_lab.artifacts import BundleExistsError, PartialBundleError
from kikuchi_lab.kinematical.bundle import (
    _fsync_directory,
    _fsync_directory_tree,
    _promote_directory_no_replace,
    _source_payload,
    _write_bytes,
    _write_json,
)
from kikuchi_lab.model.identity import plain_data, stable_id
from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.near_depth.contracts import NearDepthTreatmentRecipe
from kikuchi_lab.sources.structure import StructureRecord

from .contracts import (
    SphericalIntensityBuild,
    SphericalIntensityField,
    SphericalIntensityRecipe,
)
from .orientation import OrientedSphericalRecipe, orientation_ledger
from .oriented_render import OrientedSphericalRender
from .presentation import PresentationSource
from .rotation import OrientedSphericalIntensityField


_FIGURE_NAMES = {
    "identity-vs-oriented-upper.png",
    "oriented-upper.png",
    "oriented-lower.png",
    "oriented-sphere-front.png",
    "oriented-sphere-rear.png",
    "orientation-axes.png",
}
_NON_COORDINATE_CHANNELS = (
    "hemisphere",
    "source_row",
    "source_column",
    "intensity_raw",
    "intensity_normalized",
    "density_weight",
)
_SPHERE_CAMERAS = [
    {"elevation_deg": 20.0, "azimuth_deg": -65.0},
    {"elevation_deg": -20.0, "azimuth_deg": 115.0},
]
_AXIS_LABELS = [
    "RD",
    "TD",
    "ND",
    "G_cs[100]",
    "G_cs[010]",
    "G_cs[001]",
]


@dataclass(frozen=True)
class OrientedSphericalBundleResult:
    run_id: str
    path: Path
    manifest_sha256: str


@dataclass(frozen=True)
class _BundlePayload:
    run_identity: dict[str, object]
    source_field_ledger: dict[str, object]
    orientation_ledger: dict[str, object]
    reprojection_ledger: dict[str, object]
    presentation_ledger: dict[str, object]
    figure_ledger: dict[str, object]
    stage_timing: dict[str, object]
    oriented_recipe: dict[str, object]
    source_recipe: dict[str, object]
    presentation_recipe: dict[str, object]
    source: dict[str, object]
    figures: dict[str, bytes]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory_without_manifest(root: Path) -> dict[str, dict[str, object]]:
    return {
        str(path.relative_to(root)): {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }


def _write_oriented_npz(path: Path, field: SphericalIntensityField) -> None:
    arrays = {
        "density_weight": np.asarray(field.density_weight, dtype="<f8"),
        "hemisphere": np.asarray(field.hemisphere, dtype="i1"),
        "intensity_normalized": np.asarray(field.intensity_normalized, dtype="<f8"),
        "intensity_raw": np.asarray(field.intensity_raw, dtype="<f4"),
        "source_column": np.asarray(field.source_column, dtype="<i4"),
        "source_row": np.asarray(field.source_row, dtype="<i4"),
        "xyz_sample": np.asarray(field.xyz, dtype="<f8"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        with zipfile.ZipFile(handle, mode="w") as archive:
            for name in sorted(arrays):
                payload = io.BytesIO()
                np.lib.format.write_array(payload, arrays[name], allow_pickle=False)
                info = zipfile.ZipInfo(
                    f"{name}.npy",
                    date_time=(1980, 1, 1, 0, 0, 0),
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o600 << 16
                archive.writestr(info, payload.getvalue())
        handle.flush()
        os.fsync(handle.fileno())


def _plain_mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    plain = plain_data(value)
    if not isinstance(plain, dict):
        raise TypeError(f"{name} must be a mapping")
    return plain


def _channel_hashes(field: SphericalIntensityField) -> dict[str, str]:
    channels = {
        "xyz": field.xyz,
        "hemisphere": field.hemisphere,
        "source_row": field.source_row,
        "source_column": field.source_column,
        "intensity_raw": field.intensity_raw,
        "intensity_normalized": field.intensity_normalized,
        "density_weight": field.density_weight,
    }
    return {
        name: hashlib.sha256(array.tobytes(order="C")).hexdigest()
        for name, array in channels.items()
    }


def _validated_field(
    field: SphericalIntensityField,
    *,
    name: str,
) -> tuple[dict[str, str], dict[str, object]]:
    if not isinstance(field, SphericalIntensityField):
        raise TypeError(f"{name} must be a SphericalIntensityField")
    hashes = _channel_hashes(field)
    if hashes != dict(field.channel_sha256):
        raise ValueError(f"{name} channel hashes are inconsistent")
    metadata = field.metadata_dict()
    expected_field_id = stable_id(
        "s2-field",
        {"metadata": metadata, "channel_sha256": hashes},
    )
    if field.field_id != expected_field_id:
        raise ValueError(f"{name} identity is inconsistent")
    return hashes, metadata


def _validate_oriented_wrapper(
    value: OrientedSphericalIntensityField,
    *,
    source_field: SphericalIntensityField,
    orientation: Orientation,
    name: str,
) -> tuple[dict[str, str], dict[str, object]]:
    if not isinstance(value, OrientedSphericalIntensityField):
        raise TypeError(f"{name} must be an OrientedSphericalIntensityField")
    if value.source_field_id != source_field.field_id:
        raise ValueError(f"{name} does not derive from the supplied source field")
    hashes, metadata = _validated_field(value.field, name=f"{name} field")
    ledger = _plain_mapping(value.ledger, f"{name} ledger")
    if ledger.get("channel_sha256_after") != hashes:
        raise ValueError(f"{name} ledger channel hashes are inconsistent")
    if ledger.get("channel_sha256_before") != dict(source_field.channel_sha256):
        raise ValueError(f"{name} ledger source channel hashes are inconsistent")
    if ledger.get("source_field_id") != source_field.field_id:
        raise ValueError(f"{name} ledger source field identity is inconsistent")
    if ledger.get("oriented_field_id") != value.field.field_id:
        raise ValueError(f"{name} ledger field identity is inconsistent")
    if value.orientation_id != orientation.orientation_id:
        raise ValueError(f"{name} does not match the supplied orientation")
    expected_orientation = orientation_ledger(orientation)
    if any(ledger.get(key) != plain_data(item) for key, item in expected_orientation.items()):
        raise ValueError(f"{name} ledger orientation is inconsistent")
    if value.product_id != stable_id("oriented-s2", ledger):
        raise ValueError(f"{name} product identity is inconsistent")
    if metadata.get("orientation") != expected_orientation:
        raise ValueError(f"{name} field orientation metadata is inconsistent")
    if metadata.get("oriented_from") != {
        "source_field_id": source_field.field_id,
        "source_xyz_sha256": source_field.channel_sha256["xyz"],
    }:
        raise ValueError(f"{name} field source metadata is inconsistent")
    return hashes, ledger


def _validate_presentation_binding(
    source: PresentationSource,
    recipe: NearDepthTreatmentRecipe,
) -> dict[str, object]:
    if not isinstance(source, PresentationSource):
        raise TypeError("presentation_source must be a PresentationSource")
    if not isinstance(recipe, NearDepthTreatmentRecipe):
        raise TypeError("presentation_recipe must be a NearDepthTreatmentRecipe")
    ledger = _plain_mapping(source.ledger, "presentation source ledger")
    expected = {
        "scientific_claim": "presentation_only",
        "spatial_filter": "none",
        "interpolation": "bilinear",
        "relative_factor": recipe.overlap_relative_factor,
        "weight_exponent": recipe.weight_exponent,
        "normalization_percentile": recipe.normalization_percentile,
        "optical_gain": recipe.optical_depth_gain,
        "luminance_ceiling": recipe.luminance_ceiling,
        "center_overlay": False,
        "boundary_overlay": False,
    }
    if (
        recipe.center.enabled
        or recipe.boundary.enabled
        or source.gain != recipe.optical_depth_gain
        or source.ceiling != recipe.luminance_ceiling
        or source.overlap_normalization != ledger.get("normalization_value")
        or any(ledger.get(key) != value for key, value in expected.items())
    ):
        raise ValueError("presentation source does not match the supplied presentation recipe")
    return ledger


def _validated_payload(
    *,
    source_build: SphericalIntensityBuild,
    identity_field: OrientedSphericalIntensityField,
    oriented_field: OrientedSphericalIntensityField,
    render: OrientedSphericalRender,
    oriented_recipe: OrientedSphericalRecipe,
    source_recipe: SphericalIntensityRecipe,
    presentation_recipe: NearDepthTreatmentRecipe,
    presentation_source: PresentationSource,
    source: StructureRecord,
    stage_timing: Mapping[str, object],
) -> _BundlePayload:
    if not isinstance(source_build, SphericalIntensityBuild):
        raise TypeError("source_build must be a SphericalIntensityBuild")
    if not isinstance(oriented_recipe, OrientedSphericalRecipe):
        raise TypeError("oriented_recipe must be an OrientedSphericalRecipe")
    if not isinstance(source_recipe, SphericalIntensityRecipe):
        raise TypeError("source_recipe must be a SphericalIntensityRecipe")
    if not isinstance(source, StructureRecord):
        raise TypeError("source must be a StructureRecord")
    if not isinstance(render, OrientedSphericalRender):
        raise TypeError("render must be an OrientedSphericalRender")

    source_hashes, source_metadata = _validated_field(
        source_build.field,
        name="source field",
    )
    source_provenance = _plain_mapping(
        source_metadata.get("source"),
        "source field provenance",
    )
    if (
        source_provenance.get("phase_source_id") != source.source_record.source_id
        or source_provenance.get("source_sha256") != source.sha256
    ):
        raise ValueError("source field does not match the supplied structure source")
    if source_metadata.get("recipe_id") != source_recipe.recipe_id:
        raise ValueError("source field does not match the supplied source recipe")
    if oriented_recipe.profile.source_half_size != source_recipe.profile.half_size:
        raise ValueError("oriented and source recipe profiles do not match")
    identity_orientation = Orientation((0.0, 0.0, 0.0))
    if identity_field.orientation_id != identity_orientation.orientation_id:
        raise ValueError("identity field does not use the identity orientation")
    identity_hashes, _ = _validate_oriented_wrapper(
        identity_field,
        source_field=source_build.field,
        orientation=identity_orientation,
        name="identity field",
    )
    if identity_hashes != source_hashes:
        raise ValueError("identity field does not preserve every source channel")

    if oriented_field.orientation_id != oriented_recipe.orientation.orientation_id:
        raise ValueError("oriented field does not match the supplied oriented recipe")
    oriented_hashes, oriented_ledger = _validate_oriented_wrapper(
        oriented_field,
        source_field=source_build.field,
        orientation=oriented_recipe.orientation,
        name="oriented field",
    )
    if any(oriented_hashes[name] != source_hashes[name] for name in _NON_COORDINATE_CHANNELS):
        raise ValueError("oriented field changed a non-coordinate source channel")

    presentation_ledger = _validate_presentation_binding(
        presentation_source,
        presentation_recipe,
    )
    if oriented_recipe.interpolation != presentation_ledger.get("interpolation"):
        raise ValueError("oriented recipe does not match presentation interpolation")
    if oriented_recipe.spatial_filter != presentation_ledger.get("spatial_filter"):
        raise ValueError("oriented recipe does not match presentation spatial filter")
    if oriented_recipe.background_color != presentation_recipe.background_color:
        raise ValueError("oriented and presentation recipe backgrounds do not match")

    figure_ledger = _plain_mapping(render.ledger, "figure ledger")
    profile = oriented_recipe.profile
    expected_mesh = {
        "latitude_count": profile.sphere_latitude_count,
        "longitude_count": profile.sphere_longitude_count,
        "surface_rcount": profile.sphere_latitude_count,
        "surface_ccount": profile.sphere_longitude_count,
        "sampling": "full_grid_no_reduction",
    }
    if (
        set(render.figures) != _FIGURE_NAMES
        or figure_ledger.get("orientation_id") != oriented_field.orientation_id
        or figure_ledger.get("figure_size_px") != profile.figure_size_px
        or figure_ledger.get("sphere_cameras") != _SPHERE_CAMERAS
        or figure_ledger.get("sphere_mesh") != expected_mesh
        or figure_ledger.get("hemisphere_tile_rows") != profile.tile_rows
        or figure_ledger.get("hemisphere_direction_tile_shape_upper_bound")
        != [profile.tile_rows, profile.figure_size_px, 3]
        or figure_ledger.get("hemisphere_direction_cube_retained") is not False
        or figure_ledger.get("raster_interpolation") != "nearest"
        or figure_ledger.get("field_interpolation") != oriented_recipe.interpolation
        or figure_ledger.get("spatial_filter") != oriented_recipe.spatial_filter
        or figure_ledger.get("image_rotation") is not False
        or figure_ledger.get("center_overlay") is not False
        or figure_ledger.get("boundary_overlay") is not False
        or figure_ledger.get("display_boundary") != "circular_rim_only"
        or figure_ledger.get("annotated_figures") != ["orientation-axes.png"]
        or figure_ledger.get("axis_labels") != _AXIS_LABELS
    ):
        raise ValueError("render does not match the supplied orientation and recipe")
    figures = dict(render.figures)
    if any(not isinstance(payload, bytes) for payload in figures.values()):
        raise TypeError("render figure payloads must be bytes")

    timing = _plain_mapping(stage_timing, "stage_timing")
    source_recipe_payload = _plain_mapping(source_recipe.to_dict(), "source recipe")
    oriented_recipe_payload = _plain_mapping(
        oriented_recipe.to_dict(),
        "oriented recipe",
    )
    presentation_recipe_payload = _plain_mapping(
        presentation_recipe.to_dict(),
        "presentation recipe",
    )
    source_payload = _plain_mapping(_source_payload(source), "source structure")
    source_field_ledger = {
        "field_id": source_build.field.field_id,
        "channel_sha256": source_hashes,
        "metadata": source_metadata,
    }
    reprojection_ledger = {
        "interpolation": "bilinear",
        "spatial_filter": "none",
        "equator_owner": "upper",
        "output_size_px": profile.figure_size_px,
        "tile_rows": profile.tile_rows,
    }
    run_identity: dict[str, object] = {
        "oriented_recipe_id": oriented_recipe.recipe_id,
        "source_recipe_id": source_recipe.recipe_id,
        "presentation_recipe_id": presentation_recipe.recipe_id,
        "presentation_ledger_id": stable_id(
            "presentation-ledger",
            presentation_ledger,
        ),
        "source_id": source.source_record.source_id,
        "source_sha256": source.sha256,
        "source_field_id": source_build.field.field_id,
        "identity_field_id": identity_field.field.field_id,
        "oriented_field_id": oriented_field.field.field_id,
        "orientation_id": oriented_field.orientation_id,
        "oriented_channel_sha256": oriented_hashes,
        "figure_sha256": {
            name: hashlib.sha256(payload).hexdigest() for name, payload in sorted(figures.items())
        },
    }
    return _BundlePayload(
        run_identity=run_identity,
        source_field_ledger=source_field_ledger,
        orientation_ledger=oriented_ledger,
        reprojection_ledger=reprojection_ledger,
        presentation_ledger=presentation_ledger,
        figure_ledger=figure_ledger,
        stage_timing=timing,
        oriented_recipe=oriented_recipe_payload,
        source_recipe=source_recipe_payload,
        presentation_recipe=presentation_recipe_payload,
        source=source_payload,
        figures=figures,
    )


def _write_contents(
    root: Path,
    *,
    field: SphericalIntensityField,
    payload: _BundlePayload,
) -> dict[str, dict[str, object]]:
    _write_oriented_npz(root / "data/oriented-s2-field.npz", field)
    _write_json(
        root / "diagnostics/source-field-ledger.json",
        payload.source_field_ledger,
    )
    _write_json(
        root / "diagnostics/orientation-ledger.json",
        payload.orientation_ledger,
    )
    _write_json(
        root / "diagnostics/reprojection-ledger.json",
        payload.reprojection_ledger,
    )
    _write_json(
        root / "diagnostics/presentation-ledger.json",
        payload.presentation_ledger,
    )
    _write_json(root / "diagnostics/figure-ledger.json", payload.figure_ledger)
    _write_json(root / "diagnostics/stage-timing.json", payload.stage_timing)
    for name, figure in payload.figures.items():
        _write_bytes(root / "figures" / name, figure)
    _write_json(
        root / "recipes/oriented-spherical.json",
        payload.oriented_recipe,
    )
    _write_json(root / "recipes/source-spherical.json", payload.source_recipe)
    _write_json(root / "recipes/presentation.json", payload.presentation_recipe)
    _write_json(root / "source/structure.json", payload.source)
    return _inventory_without_manifest(root)


def write_oriented_spherical_bundle(
    output_root: str | Path,
    *,
    source_build: SphericalIntensityBuild,
    identity_field: OrientedSphericalIntensityField,
    oriented_field: OrientedSphericalIntensityField,
    render: OrientedSphericalRender,
    oriented_recipe: OrientedSphericalRecipe,
    source_recipe: SphericalIntensityRecipe,
    presentation_recipe: NearDepthTreatmentRecipe,
    presentation_source: PresentationSource,
    source: StructureRecord,
    stage_timing: Mapping[str, object],
) -> OrientedSphericalBundleResult:
    """Validate and atomically publish one content-addressed oriented proof."""
    payload = _validated_payload(
        source_build=source_build,
        identity_field=identity_field,
        oriented_field=oriented_field,
        render=render,
        oriented_recipe=oriented_recipe,
        source_recipe=source_recipe,
        presentation_recipe=presentation_recipe,
        presentation_source=presentation_source,
        source=source,
        stage_timing=stage_timing,
    )
    run_id = stable_id("oriented-spherical-run", payload.run_identity)
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    completed = root / run_id
    ownership = root / f".{run_id}.publishing"
    try:
        ownership.mkdir()
    except FileExistsError:
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}") from None
        raise PartialBundleError(f"same-run publication already in progress: {ownership}") from None

    try:
        _fsync_directory(root)
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}")
        existing_partials = sorted(root.glob(f".{run_id}.partial-*"))
        if existing_partials:
            raise PartialBundleError(f"partial bundle already exists: {existing_partials[0]}")
        partial = root / f".{run_id}.partial-{uuid4().hex}"
        try:
            partial.mkdir()
        except FileExistsError:
            raise PartialBundleError(f"partial bundle already exists: {partial}") from None

        files = _write_contents(
            partial,
            field=oriented_field.field,
            payload=payload,
        )
        manifest_path = partial / "manifest.json"
        _write_json(
            manifest_path,
            {
                "schema_version": 1,
                "run_id": run_id,
                "run_identity": payload.run_identity,
                "files": files,
            },
        )
        manifest_sha256 = _sha256(manifest_path)
        _fsync_directory_tree(partial)
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}")
        try:
            _promote_directory_no_replace(partial, completed)
        except OSError as error:
            if error.errno in {errno.EEXIST, errno.ENOTEMPTY} or completed.exists():
                raise BundleExistsError(f"completed bundle already exists: {completed}") from None
            raise PartialBundleError(
                f"partial bundle could not be promoted atomically: {partial}"
            ) from None
        return OrientedSphericalBundleResult(
            run_id=run_id,
            path=completed,
            manifest_sha256=manifest_sha256,
        )
    finally:
        ownership.rmdir()
        _fsync_directory(root)


__all__ = [
    "OrientedSphericalBundleResult",
    "write_oriented_spherical_bundle",
]
