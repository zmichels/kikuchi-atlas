"""Deterministic exchange artifacts and atomic publication for sampled S2 fields."""

from __future__ import annotations

import errno
import hashlib
import io
import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any
from uuid import uuid4
import zipfile

import numpy as np

from kikuchi_lab.kinematical.bundle import (
    _fsync_directory,
    _fsync_directory_tree,
    _promote_directory_no_replace,
)
from kikuchi_lab.model.identity import canonical_json, plain_data, stable_id
from kikuchi_lab.sources.structure import StructureRecord

from .contracts import (
    SphericalAxialField,
    SphericalIntensityBuild,
    SphericalIntensityField,
    SphericalIntensityRecipe,
)


_DIRECTIONAL_CSV = "forsterite-s2-intensity.csv"
_DIRECTIONAL_NPZ = "forsterite-s2-intensity.npz"
_LEDGER_JSON = "forsterite-s2-intensity.json"
_AXIAL_CSV = "forsterite-s2-axial.csv"
_MTEX_STATUS = "diagnostics/mtex-status.json"
_MANIFEST = "manifest.json"
_DIRECTIONAL_HEADER = (
    "x,y,z,hemisphere,source_row,source_column,intensity_raw,"
    "intensity_normalized,density_weight"
)
_AXIAL_HEADER = (
    "x,y,z,member_a_hemisphere,member_a_row,member_a_column,"
    "member_b_hemisphere,member_b_row,member_b_column,intensity_raw,"
    "intensity_normalized,density_weight"
)
_CSV_CHUNK_ROWS = 65_536


class SphericalBundleExistsError(FileExistsError):
    """Raised when an immutable S2 run already exists at publication time."""


class SphericalBundlePartialError(FileExistsError):
    """Raised when incomplete evidence makes publication unsafe."""


class SphericalBundleCorruptionError(ValueError):
    """Raised when staged scientific bytes no longer match their ledger."""


def _freeze(value: object) -> object:
    plain = plain_data(value)
    if isinstance(plain, dict):
        return MappingProxyType({key: _freeze(item) for key, item in plain.items()})
    if isinstance(plain, list):
        return tuple(_freeze(item) for item in plain)
    return plain


def _reject_absolute_local_paths(value: object, location: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_absolute_local_paths(item, f"{location}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _reject_absolute_local_paths(item, f"{location}[{index}]")
    elif isinstance(value, str) and (
        value.startswith(("/", "file://")) or re.match(r"^[A-Za-z]:[\\/]", value)
    ):
        raise ValueError(f"{location} must not contain an absolute local path")


@dataclass(frozen=True)
class SphericalBundleStage:
    staging_path: Path
    output_root: Path
    scientific_identity: Mapping[str, object]
    field_id: str

    def __post_init__(self) -> None:
        staging_path = Path(self.staging_path).resolve()
        output_root = Path(self.output_root).resolve()
        if staging_path.parent != output_root or not staging_path.name.startswith(
            ".s2-partial-"
        ):
            raise ValueError("spherical staging path must be a sibling .s2-partial directory")
        if not isinstance(self.field_id, str) or not self.field_id.startswith("s2-field-"):
            raise ValueError("spherical stage requires a directional field identity")
        frozen = _freeze(self.scientific_identity)
        if not isinstance(frozen, Mapping):
            raise TypeError("spherical stage scientific_identity must be a mapping")
        if frozen.get("field_id") != self.field_id:
            raise ValueError("spherical stage field and scientific identities must agree")
        _reject_absolute_local_paths(frozen, "scientific_identity")
        object.__setattr__(self, "staging_path", staging_path)
        object.__setattr__(self, "output_root", output_root)
        object.__setattr__(self, "scientific_identity", frozen)


@dataclass(frozen=True)
class SphericalIntensityBundleResult:
    run_id: str
    path: Path
    manifest_sha256: str
    field_id: str
    mtex_status: str


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_record(path: Path) -> dict[str, object]:
    return {"bytes": path.stat().st_size, "sha256": _sha256(path)}


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _write_json(path: Path, value: object) -> None:
    _write_bytes(path, canonical_json(value).encode("utf-8"))


def _fsync_existing_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_csv(
    path: Path,
    header: str,
    columns: Sequence[np.ndarray],
    formats: Sequence[str],
) -> None:
    """Write a typed table in bounded chunks while preserving canonical row order."""
    if len(columns) != len(formats) or not columns:
        raise ValueError("CSV columns and formats must be non-empty and equal in number")
    count = len(columns[0])
    if any(len(column) != count for column in columns):
        raise ValueError("CSV columns must have equal length")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as binary:
        binary.write((header + "\n").encode("ascii"))
        for start in range(0, count, _CSV_CHUNK_ROWS):
            stop = min(start + _CSV_CHUNK_ROWS, count)
            chunk = np.column_stack([column[start:stop] for column in columns])
            text = io.StringIO(newline="")
            np.savetxt(
                text,
                chunk,
                fmt=tuple(formats),
                delimiter=",",
                newline="\n",
            )
            binary.write(text.getvalue().encode("ascii"))
        binary.flush()
        os.fsync(binary.fileno())


def _write_directional_csv(
    path: Path, field: SphericalIntensityField, float_format: str
) -> None:
    _write_csv(
        path,
        _DIRECTIONAL_HEADER,
        (
            field.xyz[:, 0],
            field.xyz[:, 1],
            field.xyz[:, 2],
            field.hemisphere,
            field.source_row,
            field.source_column,
            field.intensity_raw,
            field.intensity_normalized,
            field.density_weight,
        ),
        (float_format, float_format, float_format, "%d", "%d", "%d")
        + (float_format,) * 3,
    )


def _write_axial_csv(
    path: Path, field: SphericalAxialField, float_format: str
) -> None:
    pairs = field.source_pairs
    _write_csv(
        path,
        _AXIAL_HEADER,
        (
            field.xyz[:, 0],
            field.xyz[:, 1],
            field.xyz[:, 2],
            pairs[:, 0, 0],
            pairs[:, 0, 1],
            pairs[:, 0, 2],
            pairs[:, 1, 0],
            pairs[:, 1, 1],
            pairs[:, 1, 2],
            field.intensity_raw,
            field.intensity_normalized,
            field.density_weight,
        ),
        (float_format,) * 3 + ("%d",) * 6 + (float_format,) * 3,
    )


def _write_npz(path: Path, field: SphericalIntensityField) -> None:
    arrays = {
        "density_weight": np.asarray(field.density_weight, dtype="<f8"),
        "hemisphere": np.asarray(field.hemisphere, dtype="i1"),
        "intensity_normalized": np.asarray(field.intensity_normalized, dtype="<f8"),
        "intensity_raw": np.asarray(field.intensity_raw, dtype="<f4"),
        "source_column": np.asarray(field.source_column, dtype="<i4"),
        "source_row": np.asarray(field.source_row, dtype="<i4"),
        "xyz": np.asarray(field.xyz, dtype="<f8"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        with zipfile.ZipFile(handle, mode="w") as archive:
            for key in sorted(arrays):
                payload = io.BytesIO()
                np.lib.format.write_array(payload, arrays[key], allow_pickle=False)
                info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o600 << 16
                archive.writestr(info, payload.getvalue())
        handle.flush()
        os.fsync(handle.fileno())


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
        name: _sha256_bytes(np.asarray(channel).tobytes(order="C"))
        for name, channel in channels.items()
    }


def _axial_channel_hashes(field: SphericalAxialField) -> dict[str, str]:
    channels = {
        "xyz": field.xyz,
        "source_pairs": field.source_pairs,
        "intensity_raw": field.intensity_raw,
        "intensity_normalized": field.intensity_normalized,
        "density_weight": field.density_weight,
    }
    return {
        name: _sha256_bytes(np.asarray(channel).tobytes(order="C"))
        for name, channel in channels.items()
    }


def _validate_field_identity(field: SphericalIntensityField) -> None:
    hashes = _channel_hashes(field)
    if hashes != dict(field.channel_sha256):
        raise SphericalBundleCorruptionError("directional field channel corruption detected")
    expected = stable_id(
        "s2-field",
        {"metadata": field.metadata_dict(), "channel_sha256": hashes},
    )
    if field.field_id != expected:
        raise SphericalBundleCorruptionError("directional field identity is corrupt")


def _validate_axial_identity(field: SphericalAxialField) -> None:
    hashes = _axial_channel_hashes(field)
    if hashes != dict(field.channel_sha256):
        raise SphericalBundleCorruptionError("axial field channel corruption detected")
    expected = stable_id(
        "s2-axial",
        {"metadata": field.metadata_dict(), "channel_sha256": hashes},
    )
    if field.field_id != expected:
        raise SphericalBundleCorruptionError("axial field identity is corrupt")


def _verified_source_links(source: StructureRecord) -> dict[str, str]:
    return {
        "phase_source_id": source.source_record.source_id,
        "source_sha256": source.sha256,
        "source_uri": source.uri,
        "source_page_uri": source.page_uri,
    }


def _scientific_recipe(recipe: SphericalIntensityRecipe) -> dict[str, object]:
    content = recipe.to_dict()
    del content["source_kinematical_recipe"]
    return {"recipe_id": recipe.recipe_id, "content": content}


def _validate_inputs(
    build: SphericalIntensityBuild,
    recipe: SphericalIntensityRecipe,
    source: StructureRecord,
) -> tuple[dict[str, object], dict[str, object]]:
    if not isinstance(build, SphericalIntensityBuild):
        raise TypeError("build must be a SphericalIntensityBuild")
    if not isinstance(recipe, SphericalIntensityRecipe):
        raise TypeError("recipe must be a SphericalIntensityRecipe")
    if not isinstance(source, StructureRecord):
        raise TypeError("source must be a StructureRecord")
    _validate_field_identity(build.field)
    metadata = build.field.metadata_dict()
    if metadata.get("recipe_id") != recipe.recipe_id:
        raise ValueError("directional field and spherical recipe identities do not agree")
    source_metadata = metadata.get("source")
    if not isinstance(source_metadata, dict):
        raise ValueError("directional field source metadata is missing")
    links = _verified_source_links(source)
    for key in ("phase_source_id", "source_sha256"):
        if source_metadata.get(key) != links[key]:
            raise ValueError("directional field and supplied source identities do not agree")
    if metadata.get("diagnostics") != build.diagnostics_dict():
        raise SphericalBundleCorruptionError("build and field diagnostics do not agree")

    axial = build.axial_field
    axial_status = build.diagnostics_dict().get("axial")
    if not isinstance(axial_status, dict):
        raise ValueError("build axial diagnostics are missing")
    if axial is None:
        if axial_status.get("status") == "emitted":
            raise SphericalBundleCorruptionError("axial diagnostics claim a missing field was emitted")
    else:
        _validate_axial_identity(axial)
        axial_metadata = axial.metadata_dict()
        if axial_status.get("status") != "emitted":
            raise SphericalBundleCorruptionError("axial field conflicts with axial diagnostics")
        if axial_metadata.get("recipe_id") != recipe.recipe_id:
            raise ValueError("axial field and spherical recipe identities do not agree")
        axial_source = axial_metadata.get("source")
        if not isinstance(axial_source, dict) or any(
            axial_source.get(key) != links[key]
            for key in ("phase_source_id", "source_sha256")
        ):
            raise ValueError("axial field and supplied source identities do not agree")

    scientific_identity: dict[str, object] = {
        "schema_version": 1,
        "field_id": build.field.field_id,
        "channel_sha256": dict(build.field.channel_sha256),
        "recipe": _scientific_recipe(recipe),
        "verified_source_links": links,
        "axial_available": axial is not None,
        "axial_field_id": axial.field_id if axial is not None else None,
        "axial_channel_sha256": dict(axial.channel_sha256) if axial is not None else None,
    }
    return scientific_identity, links


def _ledger(
    root: Path,
    build: SphericalIntensityBuild,
    recipe: SphericalIntensityRecipe,
    links: Mapping[str, str],
) -> dict[str, object]:
    axial = build.axial_field
    artifact_names = [_DIRECTIONAL_CSV, _DIRECTIONAL_NPZ]
    if axial is not None:
        artifact_names.append(_AXIAL_CSV)
    return {
        "schema_version": 1,
        "field_id": build.field.field_id,
        "metadata": build.field.metadata_dict(),
        "channel_sha256": dict(build.field.channel_sha256),
        "recipe": {"recipe_id": recipe.recipe_id, "content": recipe.to_dict()},
        "verified_source_links": dict(links),
        "axial_available": axial is not None,
        "axial_field_id": axial.field_id if axial is not None else None,
        "axial_channel_sha256": dict(axial.channel_sha256) if axial is not None else None,
        "artifacts": {name: _artifact_record(root / name) for name in artifact_names},
        "extension_artifacts": {},
    }


def stage_spherical_bundle(
    output_root: str | Path,
    build: SphericalIntensityBuild,
    recipe: SphericalIntensityRecipe,
    source: StructureRecord,
) -> SphericalBundleStage:
    """Validate and stage deterministic Python exchange artifacts without promotion."""
    scientific_identity, links = _validate_inputs(build, recipe, source)
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    _fsync_directory(root)
    staging = root / f".s2-partial-{uuid4().hex}"
    try:
        staging.mkdir()
    except FileExistsError:
        raise SphericalBundlePartialError(f"spherical stage already exists: {staging}") from None
    _fsync_directory(root)

    _write_directional_csv(staging / _DIRECTIONAL_CSV, build.field, recipe.csv_float_format)
    _write_npz(staging / _DIRECTIONAL_NPZ, build.field)
    if build.axial_field is not None:
        _write_axial_csv(staging / _AXIAL_CSV, build.axial_field, recipe.csv_float_format)
    _write_json(staging / _LEDGER_JSON, _ledger(staging, build, recipe, links))
    _fsync_directory_tree(staging)
    return SphericalBundleStage(
        staging_path=staging,
        output_root=root,
        scientific_identity=scientific_identity,
        field_id=build.field.field_id,
    )


def _read_ledger(stage: SphericalBundleStage) -> dict[str, Any]:
    path = stage.staging_path / _LEDGER_JSON
    try:
        payload = path.read_bytes()
        ledger = json.loads(payload)
    except (OSError, json.JSONDecodeError) as error:
        raise SphericalBundleCorruptionError("spherical ledger is missing or invalid") from error
    if not isinstance(ledger, dict) or payload != canonical_json(ledger).encode("utf-8"):
        raise SphericalBundleCorruptionError("spherical ledger bytes are not canonical")
    return ledger


def _validate_stage(stage: SphericalBundleStage) -> dict[str, Any]:
    if not isinstance(stage, SphericalBundleStage):
        raise TypeError("stage must be a SphericalBundleStage")
    if not stage.staging_path.is_dir():
        raise SphericalBundleCorruptionError("spherical staging directory is missing")
    if stage.staging_path.parent != stage.output_root:
        raise SphericalBundleCorruptionError("spherical staging directory escaped output root")
    for path in stage.staging_path.rglob("*"):
        if path.is_symlink():
            raise SphericalBundleCorruptionError("spherical stage must not contain symlinks")
    ledger = _read_ledger(stage)
    if ledger.get("field_id") != stage.field_id:
        raise SphericalBundleCorruptionError("spherical stage and ledger field identities differ")
    identity = plain_data(stage.scientific_identity)
    for key in (
        "field_id",
        "channel_sha256",
        "verified_source_links",
        "axial_available",
        "axial_field_id",
        "axial_channel_sha256",
    ):
        if ledger.get(key) != identity.get(key):
            raise SphericalBundleCorruptionError(
                f"spherical stage scientific identity mismatch for {key}"
            )
    ledger_recipe = ledger.get("recipe")
    if not isinstance(ledger_recipe, dict) or not isinstance(
        ledger_recipe.get("content"), dict
    ):
        raise SphericalBundleCorruptionError("spherical ledger recipe identity is invalid")
    scientific_recipe = dict(ledger_recipe["content"])
    scientific_recipe.pop("source_kinematical_recipe", None)
    if {
        "recipe_id": ledger_recipe.get("recipe_id"),
        "content": scientific_recipe,
    } != identity.get("recipe"):
        raise SphericalBundleCorruptionError(
            "spherical stage scientific identity mismatch for recipe"
        )
    artifacts = ledger.get("artifacts")
    if not isinstance(artifacts, dict):
        raise SphericalBundleCorruptionError("spherical ledger artifact inventory is invalid")
    expected_artifacts = {_DIRECTIONAL_CSV, _DIRECTIONAL_NPZ}
    if ledger.get("axial_available") is True:
        expected_artifacts.add(_AXIAL_CSV)
    axial_path = stage.staging_path / _AXIAL_CSV
    if axial_path.exists() != (ledger.get("axial_available") is True):
        raise SphericalBundleCorruptionError(
            "reserved axial artifact conflicts with axial availability"
        )
    if set(artifacts) != expected_artifacts:
        raise SphericalBundleCorruptionError("spherical ledger artifact inventory is not exact")
    for relative, record in artifacts.items():
        path = stage.staging_path / relative
        if not path.is_file() or record != _artifact_record(path):
            raise SphericalBundleCorruptionError(
                f"staged spherical artifact is missing or corrupt: {relative}"
            )
    return ledger


def _partial_files(root: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.name.endswith(".partial")
        ),
        key=lambda path: str(path.relative_to(root)),
    )


def _mtex_records(
    stage: SphericalBundleStage, mtex_result: Mapping[str, object] | None
) -> tuple[dict[str, object], dict[str, object]]:
    identity = plain_data(stage.scientific_identity)
    recipe = identity.get("recipe")
    if not isinstance(recipe, dict) or not isinstance(recipe.get("content"), dict):
        raise SphericalBundleCorruptionError("stage recipe identity is invalid")
    profile = recipe["content"].get("profile")
    if not isinstance(profile, dict) or not isinstance(profile.get("name"), str):
        raise SphericalBundleCorruptionError("stage recipe profile is invalid")
    default_profile = profile["name"]
    if mtex_result is None:
        diagnostic = {
            "schema_version": 1,
            "requested_profile": default_profile,
            "status": "not-requested",
        }
    else:
        if not isinstance(mtex_result, Mapping):
            raise TypeError("mtex_result must be a mapping or None")
        converted = plain_data(mtex_result)
        if not isinstance(converted, dict):
            raise TypeError("mtex_result must be a mapping or None")
        diagnostic = {**converted, "schema_version": 1}
        requested = diagnostic.get("requested_profile")
        status = diagnostic.get("status")
        if not isinstance(requested, str) or not requested:
            raise ValueError("mtex_result requires requested_profile")
        if not isinstance(status, str) or not status:
            raise ValueError("mtex_result requires status")

    stable = {
        "requested_profile": diagnostic["requested_profile"],
        "status": diagnostic["status"],
    }
    if diagnostic["status"] == "success":
        versions = diagnostic.get("versions")
        if (
            not isinstance(versions, dict)
            or not versions
            or any(not isinstance(key, str) or not isinstance(value, str) for key, value in versions.items())
        ):
            raise ValueError("successful mtex_result requires string versions")
        stable["versions"] = versions
    _reject_absolute_local_paths(stable, "stable_mtex_identity")
    return diagnostic, stable


def _write_failure_status(stage: SphericalBundleStage, failure_kind: str) -> None:
    _write_json(
        stage.staging_path / _MTEX_STATUS,
        {
            "schema_version": 1,
            "requested_profile": plain_data(stage.scientific_identity)["recipe"]["content"][
                "profile"
            ]["name"],
            "status": "finalization-failed",
            "failure_kind": failure_kind,
        },
    )
    _fsync_directory_tree(stage.staging_path)


def _manifest(
    stage: SphericalBundleStage,
    run_id: str,
    run_identity: Mapping[str, object],
) -> dict[str, object]:
    files = {
        str(path.relative_to(stage.staging_path)): _artifact_record(path)
        for path in sorted(stage.staging_path.rglob("*"))
        if path.is_file() and path.name != _MANIFEST
    }
    return {
        "schema_version": 1,
        "run_id": run_id,
        "run_identity": dict(run_identity),
        "field_id": stage.field_id,
        "files": files,
    }


def finalize_spherical_bundle(
    stage: SphericalBundleStage,
    *,
    mtex_result: Mapping[str, object] | None = None,
) -> SphericalIntensityBundleResult:
    """Inventory, fsync, and atomically promote a validated S2 exchange stage."""
    _validate_stage(stage)
    partials = _partial_files(stage.staging_path)
    if partials:
        _write_failure_status(stage, "partial-artifact")
        relative = partials[0].relative_to(stage.staging_path)
        raise SphericalBundlePartialError(f"staged file still ends in .partial: {relative}")

    try:
        diagnostic, stable_mtex_identity = _mtex_records(stage, mtex_result)
    except (TypeError, ValueError):
        _write_failure_status(stage, "invalid-mtex-result")
        raise
    run_identity: dict[str, object] = {
        "schema_version": 1,
        "field_id": stage.field_id,
        "scientific_identity": plain_data(stage.scientific_identity),
        "mtex": stable_mtex_identity,
    }
    run_id = stable_id("s2-run", run_identity)
    completed = stage.output_root / run_id
    ownership = stage.output_root / f".{run_id}.publishing"
    try:
        ownership.mkdir()
    except FileExistsError:
        if completed.exists():
            raise SphericalBundleExistsError(
                f"completed spherical bundle already exists: {completed}"
            ) from None
        raise SphericalBundlePartialError(
            f"same-run spherical publication already in progress: {ownership}"
        ) from None

    try:
        _fsync_directory(stage.output_root)
        if completed.exists():
            raise SphericalBundleExistsError(
                f"completed spherical bundle already exists: {completed}"
            )
        stale_manifest = stage.staging_path / _MANIFEST
        if stale_manifest.exists():
            if not stale_manifest.is_file() or stale_manifest.is_symlink():
                raise SphericalBundleCorruptionError("stale spherical manifest is unsafe")
            stale_manifest.unlink()
        _write_json(stage.staging_path / _MTEX_STATUS, diagnostic)
        for path in sorted(stage.staging_path.rglob("*")):
            if path.is_file():
                _fsync_existing_file(path)
        manifest_path = stage.staging_path / _MANIFEST
        _write_json(manifest_path, _manifest(stage, run_id, run_identity))
        manifest_sha256 = _sha256(manifest_path)
        _fsync_directory_tree(stage.staging_path)
        try:
            _promote_directory_no_replace(stage.staging_path, completed)
        except OSError as error:
            if error.errno in {errno.EEXIST, errno.ENOTEMPTY} or completed.exists():
                raise SphericalBundleExistsError(
                    f"completed spherical bundle already exists: {completed}"
                ) from None
            raise SphericalBundlePartialError(
                f"spherical stage could not be promoted atomically: {stage.staging_path}"
            ) from error
        return SphericalIntensityBundleResult(
            run_id=run_id,
            path=completed,
            manifest_sha256=manifest_sha256,
            field_id=stage.field_id,
            mtex_status=str(diagnostic["status"]),
        )
    finally:
        ownership.rmdir()
        _fsync_directory(stage.output_root)


__all__ = [
    "SphericalBundleCorruptionError",
    "SphericalBundleExistsError",
    "SphericalBundlePartialError",
    "SphericalBundleStage",
    "SphericalIntensityBundleResult",
    "finalize_spherical_bundle",
    "stage_spherical_bundle",
]
