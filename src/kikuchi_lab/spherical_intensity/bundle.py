"""Deterministic exchange artifacts and atomic publication for sampled S2 fields."""

from __future__ import annotations

import errno
import hashlib
import io
import json
import math
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Protocol
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
_COLLISION_INVESTIGATION = "diagnostics/collision-investigation.json"
_MANIFEST = "manifest.json"
_MTEX_SCRIPT = "forsterite-s2-mtex.m"
_ALLOWED_SCIENTIFIC_EXTENSIONS = {_MTEX_SCRIPT}
_MTEX_STATUSES = {"passed", "unavailable", "failed", "timed-out"}
_MTEX_COMMON_OUTPUTS = {
    "forsterite-s2-density-vectors.csv",
    "forsterite-s2-mtex-preview.png",
    "diagnostics/mtex-result.json",
    "figures/exact-node-scatter.png",
    "figures/colored-sphere.png",
    "figures/density-cloud.png",
    "figures/raw-vs-density-channels.png",
}
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


class _MtexRunResultLike(Protocol):
    status: str
    command: tuple[str, ...]
    normalized_error: str | None
    metrics: Mapping[str, object]
    produced_files: tuple[str, ...]
    last_stage: str | None
    elapsed_seconds: float


class SphericalBundleExistsError(FileExistsError):
    """Raised when an immutable S2 run already exists at publication time."""


class SphericalBundleInvestigationError(SphericalBundleExistsError):
    """Raised when one stable run identity has differing validated derivatives."""


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


def _metadata_without_axial_semantics(metadata: Mapping[str, object]) -> dict[str, object]:
    plain = plain_data(metadata)
    if not isinstance(plain, dict):
        raise SphericalBundleCorruptionError("spherical metadata must be a mapping")
    plain.pop("domain_semantics", None)
    plain.pop("axial", None)
    return plain


def _expected_axial_representative_count(field: SphericalIntensityField) -> int:
    metadata = field.metadata_dict()
    equator = metadata.get("equator")
    tolerance_value = equator.get("tolerance") if isinstance(equator, dict) else None
    if (
        isinstance(tolerance_value, bool)
        or not isinstance(tolerance_value, (int, float))
        or not math.isfinite(float(tolerance_value))
        or float(tolerance_value) < 0
    ):
        raise SphericalBundleCorruptionError("directional equator metadata is invalid")
    tolerance = float(tolerance_value)
    upper_xyz = field.xyz[field.hemisphere == 1]
    representative = (upper_xyz[:, 2] > tolerance) | (
        (np.abs(upper_xyz[:, 2]) <= tolerance)
        & (
            (upper_xyz[:, 0] > 0)
            | ((upper_xyz[:, 0] == 0) & (upper_xyz[:, 1] >= 0))
        )
    )
    return int(np.count_nonzero(representative))


def _validate_axial_eligibility(
    build: SphericalIntensityBuild,
    recipe: SphericalIntensityRecipe,
    metadata: Mapping[str, object],
) -> None:
    diagnostics = build.diagnostics_dict()
    axial_diagnostics = diagnostics.get("axial")
    antipodal = diagnostics.get("antipodal")
    phase = metadata.get("phase")
    if not isinstance(axial_diagnostics, dict) or not isinstance(antipodal, dict):
        raise SphericalBundleCorruptionError(
            "axial eligibility diagnostics are missing or invalid"
        )
    if not isinstance(phase, dict) or type(phase.get("contains_inversion")) is not bool:
        raise SphericalBundleCorruptionError("axial eligibility inversion is invalid")
    expected_fields = {
        "status",
        "contains_inversion",
        "observed_normalized_rms",
        "observed_normalized_max",
        "normalized_rms_limit",
        "normalized_max_limit",
        "representative_count",
    }
    if set(axial_diagnostics) != expected_fields:
        raise SphericalBundleCorruptionError(
            "axial eligibility diagnostic fields are not exact"
        )
    observed_rms = antipodal.get("normalized_rms")
    observed_max = antipodal.get("normalized_max")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
        for value in (observed_rms, observed_max)
    ):
        raise SphericalBundleCorruptionError(
            "axial eligibility antipodal observations are invalid"
        )
    inversion = phase["contains_inversion"]
    expected_values: dict[str, object] = {
        "contains_inversion": inversion,
        "observed_normalized_rms": observed_rms,
        "observed_normalized_max": observed_max,
        "normalized_rms_limit": recipe.tolerances.axial_normalized_rms_max,
        "normalized_max_limit": recipe.tolerances.axial_normalized_max,
    }
    for name, expected in expected_values.items():
        observed = axial_diagnostics[name]
        if type(expected) is bool:
            matches = observed is expected
        else:
            matches = (
                not isinstance(observed, bool)
                and isinstance(observed, (int, float))
                and math.isfinite(float(observed))
                and observed == expected
            )
        if not matches:
            raise SphericalBundleCorruptionError(
                f"axial eligibility diagnostic {name} does not match its source"
            )

    if not recipe.emit_axial:
        expected_status = "disabled-by-recipe"
    elif not inversion:
        expected_status = "phase-has-no-inversion"
    elif (
        float(observed_rms) > recipe.tolerances.axial_normalized_rms_max
        or float(observed_max) > recipe.tolerances.axial_normalized_max
    ):
        expected_status = "antipodal-residual-exceeds-tolerance"
    else:
        expected_status = "emitted"
    if axial_diagnostics["status"] != expected_status:
        raise SphericalBundleCorruptionError(
            "axial eligibility status does not match the canonical branch"
        )
    expected_present = expected_status == "emitted"
    if (build.axial_field is not None) != expected_present:
        raise SphericalBundleCorruptionError(
            "axial eligibility status and field presence disagree"
        )
    expected_count = (
        _expected_axial_representative_count(build.field) if expected_present else 0
    )
    if (
        type(axial_diagnostics["representative_count"]) is not int
        or axial_diagnostics["representative_count"] != expected_count
    ):
        raise SphericalBundleCorruptionError(
            "axial eligibility representative count is not canonical"
        )


def _validate_axial_coherence(
    field: SphericalIntensityField,
    axial: SphericalAxialField,
    recipe: SphericalIntensityRecipe,
    diagnostics: Mapping[str, object],
) -> None:
    directional_metadata = field.metadata_dict()
    axial_metadata = axial.metadata_dict()
    if _metadata_without_axial_semantics(axial_metadata) != (
        _metadata_without_axial_semantics(directional_metadata)
    ):
        raise SphericalBundleCorruptionError(
            "axial and directional metadata coherence check failed"
        )

    axial_diagnostics = plain_data(diagnostics.get("axial"))
    if not isinstance(axial_diagnostics, dict):
        raise SphericalBundleCorruptionError("axial diagnostics are invalid")
    count = len(axial.xyz)
    if axial_diagnostics.get("representative_count") != count:
        raise SphericalBundleCorruptionError(
            "axial representative count disagrees with diagnostics"
        )

    grid = directional_metadata["grid"]
    equator = directional_metadata["equator"]
    normalization = directional_metadata["normalization"]
    if not isinstance(grid, dict) or not isinstance(equator, dict) or not isinstance(
        normalization, dict
    ):
        raise SphericalBundleCorruptionError("directional axial metadata is invalid")
    size = grid["size"]
    tolerance = equator["tolerance"]
    if type(size) is not int or not isinstance(tolerance, (int, float)):
        raise SphericalBundleCorruptionError("directional grid/equator metadata is invalid")

    upper = field.hemisphere == 1
    upper_xyz = field.xyz[upper]
    upper_rows = field.source_row[upper]
    upper_columns = field.source_column[upper]
    representative = (upper_xyz[:, 2] > float(tolerance)) | (
        (np.abs(upper_xyz[:, 2]) <= float(tolerance))
        & (
            (upper_xyz[:, 0] > 0)
            | ((upper_xyz[:, 0] == 0) & (upper_xyz[:, 1] >= 0))
        )
    )
    expected_rows = upper_rows[representative]
    expected_columns = upper_columns[representative]
    if len(expected_rows) != count:
        raise SphericalBundleCorruptionError(
            "axial representative count disagrees with directional ownership"
        )
    expected_pairs = np.stack(
        [
            np.column_stack(
                [np.ones(count, dtype=np.int32), expected_rows, expected_columns]
            ),
            np.column_stack(
                [
                    -np.ones(count, dtype=np.int32),
                    size - 1 - expected_rows,
                    size - 1 - expected_columns,
                ]
            ),
        ],
        axis=1,
    )
    if not np.array_equal(axial.source_pairs, expected_pairs):
        raise SphericalBundleCorruptionError(
            "axial source-pair order, ownership, range, or uniqueness is invalid"
        )
    if not np.array_equal(axial.xyz, upper_xyz[representative]):
        raise SphericalBundleCorruptionError(
            "axial vectors do not match their directional representatives"
        )
    if np.unique(axial.source_pairs.reshape(count, 6), axis=0).shape[0] != count:
        raise SphericalBundleCorruptionError("axial source pairs must be unique")

    directional_raw = {
        (int(hemisphere), int(row), int(column)): raw
        for hemisphere, row, column, raw in zip(
            field.hemisphere,
            field.source_row,
            field.source_column,
            field.intensity_raw,
            strict=True,
        )
    }
    for index, pair in enumerate(axial.source_pairs):
        member_a = tuple(int(value) for value in pair[0])
        member_b = tuple(int(value) for value in pair[1])
        if member_a not in directional_raw:
            raise SphericalBundleCorruptionError("axial representative is missing directionally")
        if member_b in directional_raw:
            expected_raw = np.float32(
                (np.float64(directional_raw[member_a]) + directional_raw[member_b]) / 2.0
            )
            if axial.intensity_raw[index] != expected_raw:
                raise SphericalBundleCorruptionError(
                    "axial raw intensity is not the directional pair mean"
                )
        else:
            antipodal = diagnostics.get("antipodal")
            if not isinstance(antipodal, Mapping):
                raise SphericalBundleCorruptionError(
                    "equator axial validation requires antipodal diagnostics"
                )
            maximum_absolute = antipodal.get("maximum_absolute")
            if (
                isinstance(maximum_absolute, bool)
                or not isinstance(maximum_absolute, (int, float))
                or not math.isfinite(float(maximum_absolute))
                or float(maximum_absolute) < 0
            ):
                raise SphericalBundleCorruptionError(
                    "equator axial antipodal residual is invalid"
                )
            if abs(float(axial.xyz[index, 2])) > float(tolerance):
                raise SphericalBundleCorruptionError(
                    "missing directional pair member is not on the equator"
                )
            retained = np.float32(directional_raw[member_a])
            observed = np.float32(axial.intensity_raw[index])
            rounding_allowance = float(
                max(abs(np.spacing(retained)), abs(np.spacing(observed)))
            )
            allowed = 0.5 * float(maximum_absolute) + rounding_allowance
            if abs(float(observed) - float(retained)) > allowed:
                raise SphericalBundleCorruptionError(
                    "equator axial raw exceeds the half-antipodal-residual bound"
                )

    low = normalization.get("realized_low")
    high = normalization.get("realized_high")
    if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
        raise SphericalBundleCorruptionError("axial normalization window is invalid")
    expected_normalized = np.clip(
        (axial.intensity_raw.astype(np.float64) - float(low)) / (float(high) - float(low)),
        0.0,
        1.0,
    )
    expected_density = expected_normalized**recipe.density.exponent
    if not np.array_equal(axial.intensity_normalized, expected_normalized):
        raise SphericalBundleCorruptionError(
            "axial normalization does not use the shared directional window"
        )
    if not np.array_equal(axial.density_weight, expected_density):
        raise SphericalBundleCorruptionError(
            "axial density does not use the shared directional exponent"
        )


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


def _scientific_extensions(
    build: SphericalIntensityBuild,
    recipe: SphericalIntensityRecipe,
) -> Mapping[str, bytes]:
    """Internal Task-4 seam; T021 intentionally registers no generated script."""
    del build, recipe
    return {}


def _validated_extension_payloads(
    value: Mapping[str, bytes],
) -> tuple[dict[str, bytes], dict[str, dict[str, object]]]:
    if not isinstance(value, Mapping):
        raise TypeError("scientific extensions must be an internal mapping")
    if not set(value).issubset(_ALLOWED_SCIENTIFIC_EXTENSIONS):
        raise ValueError("scientific extension inventory contains an unsupported filename")
    payloads: dict[str, bytes] = {}
    records: dict[str, dict[str, object]] = {}
    for relative in sorted(value):
        payload = value[relative]
        if type(payload) is not bytes or not payload:
            raise ValueError("scientific extension payloads must be non-empty bytes")
        payloads[relative] = payload
        records[relative] = {
            "bytes": len(payload),
            "sha256": _sha256_bytes(payload),
        }
    return payloads, records


def _validate_inputs(
    build: SphericalIntensityBuild,
    recipe: SphericalIntensityRecipe,
    source: StructureRecord,
    extension_records: Mapping[str, Mapping[str, object]],
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

    _validate_axial_eligibility(build, recipe, metadata)
    axial = build.axial_field
    if axial is not None:
        _validate_axial_identity(axial)
        axial_metadata = axial.metadata_dict()
        if axial_metadata.get("recipe_id") != recipe.recipe_id:
            raise ValueError("axial field and spherical recipe identities do not agree")
        axial_source = axial_metadata.get("source")
        if not isinstance(axial_source, dict) or any(
            axial_source.get(key) != links[key]
            for key in ("phase_source_id", "source_sha256")
        ):
            raise ValueError("axial field and supplied source identities do not agree")
        _validate_axial_coherence(build.field, axial, recipe, build.diagnostics)

    scientific_identity: dict[str, object] = {
        "schema_version": 1,
        "field_id": build.field.field_id,
        "channel_sha256": dict(build.field.channel_sha256),
        "recipe": _scientific_recipe(recipe),
        "verified_source_links": links,
        "axial_available": axial is not None,
        "axial_field_id": axial.field_id if axial is not None else None,
        "axial_channel_sha256": dict(axial.channel_sha256) if axial is not None else None,
        "extension_artifacts": plain_data(extension_records),
    }
    return scientific_identity, links


def _ledger(
    root: Path,
    build: SphericalIntensityBuild,
    recipe: SphericalIntensityRecipe,
    links: Mapping[str, str],
    extension_records: Mapping[str, Mapping[str, object]],
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
        "extension_artifacts": plain_data(extension_records),
    }


def stage_spherical_bundle(
    output_root: str | Path,
    build: SphericalIntensityBuild,
    recipe: SphericalIntensityRecipe,
    source: StructureRecord,
) -> SphericalBundleStage:
    """Validate and stage deterministic Python exchange artifacts without promotion."""
    extension_payloads, extension_records = _validated_extension_payloads(
        _scientific_extensions(build, recipe)
    )
    scientific_identity, links = _validate_inputs(
        build, recipe, source, extension_records
    )
    root = Path(output_root).resolve()
    staging = root / f".s2-partial-{uuid4().hex}"
    stage = SphericalBundleStage(
        staging_path=staging,
        output_root=root,
        scientific_identity=scientific_identity,
        field_id=build.field.field_id,
    )
    root.mkdir(parents=True, exist_ok=True)
    _fsync_directory(root)
    try:
        staging.mkdir()
    except FileExistsError:
        raise SphericalBundlePartialError(f"spherical stage already exists: {staging}") from None
    _fsync_directory(root)

    _write_directional_csv(staging / _DIRECTIONAL_CSV, build.field, recipe.csv_float_format)
    _write_npz(staging / _DIRECTIONAL_NPZ, build.field)
    if build.axial_field is not None:
        _write_axial_csv(staging / _AXIAL_CSV, build.axial_field, recipe.csv_float_format)
    for relative, payload in extension_payloads.items():
        _write_bytes(staging / relative, payload)
    _write_json(
        staging / _LEDGER_JSON,
        _ledger(staging, build, recipe, links, extension_records),
    )
    _fsync_directory_tree(staging)
    return stage


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
        "extension_artifacts",
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
    extensions = ledger.get("extension_artifacts")
    if not isinstance(extensions, dict) or not set(extensions).issubset(
        _ALLOWED_SCIENTIFIC_EXTENSIONS
    ):
        raise SphericalBundleCorruptionError(
            "spherical ledger extension artifact inventory is invalid"
        )
    for relative, record in extensions.items():
        path = stage.staging_path / relative
        if not path.is_file() or record != _artifact_record(path):
            raise SphericalBundleCorruptionError(
                f"registered scientific extension is missing or corrupt: {relative}"
            )
    return ledger


def _partial_files(root: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.name.endswith(".partial")
            and tuple(path.relative_to(root).parts[:2])
            != ("diagnostics", "quarantine")
        ),
        key=lambda path: str(path.relative_to(root)),
    )


def _structural_mtex_result(result: object) -> dict[str, object]:
    if isinstance(result, Mapping):
        raise TypeError("mtex_result must satisfy the frozen MtexRunResult contract")
    required = (
        "status",
        "command",
        "normalized_error",
        "metrics",
        "produced_files",
        "last_stage",
        "elapsed_seconds",
    )
    try:
        values = {name: getattr(result, name) for name in required}
    except AttributeError as error:
        raise TypeError("mtex_result must satisfy the frozen MtexRunResult contract") from error
    if not isinstance(values["status"], str) or values["status"] not in _MTEX_STATUSES:
        raise ValueError("mtex_result status is not canonical")
    command = values["command"]
    if not isinstance(command, tuple) or any(
        not isinstance(part, str) or not part for part in command
    ):
        raise TypeError("mtex_result command must be a tuple of non-empty strings")
    normalized_error = values["normalized_error"]
    if normalized_error is not None and (
        not isinstance(normalized_error, str) or not normalized_error
    ):
        raise TypeError("mtex_result normalized_error must be text or None")
    metrics = values["metrics"]
    if not isinstance(metrics, Mapping):
        raise TypeError("mtex_result metrics must be a mapping")
    plain_metrics = plain_data(metrics)
    if not isinstance(plain_metrics, dict):
        raise TypeError("mtex_result metrics must be a mapping")
    produced_files = values["produced_files"]
    if not isinstance(produced_files, tuple) or any(
        not isinstance(relative, str) or not relative for relative in produced_files
    ):
        raise TypeError("mtex_result produced_files must be a tuple of relative names")
    if len(set(produced_files)) != len(produced_files):
        raise ValueError("mtex_result produced_files must be unique")
    last_stage = values["last_stage"]
    if last_stage is not None and (not isinstance(last_stage, str) or not last_stage):
        raise TypeError("mtex_result last_stage must be text or None")
    elapsed = values["elapsed_seconds"]
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0
    ):
        raise ValueError("mtex_result elapsed_seconds must be finite and nonnegative")
    return {
        "status": values["status"],
        "command": list(command),
        "normalized_error": normalized_error,
        "metrics": plain_metrics,
        "produced_files": list(produced_files),
        "last_stage": last_stage,
        "elapsed_seconds": float(elapsed),
    }


def _require_exact_metric(metrics: Mapping[str, object], name: str, expected: object) -> None:
    if metrics.get(name) != expected:
        raise ValueError(f"passed MTEX metric {name} does not match the staged profile")


def _passed_mtex_identity(
    stage: SphericalBundleStage,
    ledger: Mapping[str, object],
    diagnostic: Mapping[str, object],
) -> tuple[dict[str, object], set[str]]:
    identity = plain_data(stage.scientific_identity)
    recipe_record = identity.get("recipe")
    if not isinstance(recipe_record, dict) or not isinstance(
        recipe_record.get("content"), dict
    ):
        raise SphericalBundleCorruptionError("stage recipe identity is invalid")
    recipe = recipe_record["content"]
    profile = recipe.get("profile")
    tolerances = recipe.get("tolerances")
    if not isinstance(profile, dict) or not isinstance(tolerances, dict):
        raise SphericalBundleCorruptionError("stage recipe profile is invalid")
    extensions = ledger.get("extension_artifacts")
    if not isinstance(extensions, dict) or set(extensions) != {_MTEX_SCRIPT}:
        raise ValueError("passed MTEX result requires the registered generated script")

    command = diagnostic["command"]
    if not isinstance(command, list) or not command:
        raise ValueError("passed MTEX result requires an observed command")
    if diagnostic["normalized_error"] is not None:
        raise ValueError("passed MTEX result cannot retain a normalized error")
    produced_list = diagnostic["produced_files"]
    assert isinstance(produced_list, list)
    produced = set(produced_list)
    required = set(_MTEX_COMMON_OUTPUTS)
    axial_available = ledger.get("axial_available") is True
    if axial_available:
        required.add("figures/directional-vs-axial.png")
    if produced != required or produced_list != sorted(required):
        raise ValueError("passed MTEX produced output inventory is not exact")

    metrics = diagnostic["metrics"]
    if not isinstance(metrics, dict):
        raise TypeError("passed MTEX metrics must be canonical")
    required_metrics = {
        "schema_version",
        "profile",
        "node_count",
        "node_normalized_error",
        "point_count",
        "rng_seed",
        "rng_generator",
        "sampling_resolution_deg",
        "display_resolution_deg",
        "axial_available",
        "matlab_version",
        "mtex_version",
        "validated_files",
    }
    if set(metrics) != required_metrics or metrics.get("schema_version") != 1:
        raise ValueError("passed MTEX metrics do not use canonical schema 1")
    metadata = ledger.get("metadata")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("diagnostics"), dict):
        raise SphericalBundleCorruptionError("ledger diagnostics are invalid")
    _require_exact_metric(metrics, "profile", profile.get("name"))
    _require_exact_metric(
        metrics, "node_count", metadata["diagnostics"].get("point_count")
    )
    _require_exact_metric(metrics, "point_count", profile.get("point_count"))
    _require_exact_metric(metrics, "rng_seed", recipe.get("rng_seed"))
    _require_exact_metric(metrics, "rng_generator", recipe.get("rng_generator"))
    _require_exact_metric(
        metrics, "sampling_resolution_deg", profile.get("sampling_resolution_deg")
    )
    _require_exact_metric(
        metrics, "display_resolution_deg", recipe.get("display_resolution_deg")
    )
    _require_exact_metric(metrics, "axial_available", axial_available)
    _require_exact_metric(metrics, "mtex_version", recipe.get("expected_mtex_version"))
    matlab_version = metrics.get("matlab_version")
    if not isinstance(matlab_version, str) or not matlab_version:
        raise ValueError("passed MTEX metrics require an actual MATLAB version")
    node_error = metrics.get("node_normalized_error")
    node_limit = tolerances.get("mtex_node_normalized_max")
    if (
        isinstance(node_error, bool)
        or not isinstance(node_error, (int, float))
        or not math.isfinite(float(node_error))
        or float(node_error) < 0
        or not isinstance(node_limit, (int, float))
        or float(node_error) > float(node_limit)
    ):
        raise ValueError("passed MTEX node error exceeds the staged tolerance")

    validated_files = metrics.get("validated_files")
    if not isinstance(validated_files, dict) or set(validated_files) != required:
        raise ValueError("passed MTEX validated output hashes are not exact")
    for relative in sorted(required):
        path = stage.staging_path / relative
        record = validated_files[relative]
        if not path.is_file() or record != _artifact_record(path):
            raise ValueError(f"passed MTEX output/hash validation failed: {relative}")

    stable = {
        "requested_profile": profile["name"],
        "status": "passed",
        "versions": {
            "matlab": matlab_version,
            "mtex": metrics["mtex_version"],
        },
    }
    _reject_absolute_local_paths(stable, "stable_mtex_identity")
    return stable, required


def _mtex_records(
    stage: SphericalBundleStage,
    ledger: Mapping[str, object],
    mtex_result: _MtexRunResultLike | None,
) -> tuple[dict[str, object], dict[str, object], set[str]]:
    identity = plain_data(stage.scientific_identity)
    recipe = identity.get("recipe")
    if not isinstance(recipe, dict) or not isinstance(recipe.get("content"), dict):
        raise SphericalBundleCorruptionError("stage recipe identity is invalid")
    profile = recipe["content"].get("profile")
    if not isinstance(profile, dict) or not isinstance(profile.get("name"), str):
        raise SphericalBundleCorruptionError("stage recipe profile is invalid")
    requested_profile = profile["name"]
    if mtex_result is None:
        diagnostic = {
            "schema_version": 1,
            "requested_profile": requested_profile,
            "status": "not-requested",
        }
        stable = {
            "requested_profile": requested_profile,
            "status": "not-requested",
        }
        return diagnostic, stable, set()
    else:
        observed = _structural_mtex_result(mtex_result)
        diagnostic = {
            "schema_version": 1,
            "requested_profile": requested_profile,
            **observed,
        }
    if diagnostic["status"] == "passed":
        stable, produced = _passed_mtex_identity(stage, ledger, diagnostic)
        return diagnostic, stable, produced
    if diagnostic["produced_files"]:
        raise ValueError("non-passed MTEX result cannot register scientific outputs")
    if not diagnostic["normalized_error"]:
        raise ValueError("non-passed MTEX result requires a normalized error")
    stable = {
        "requested_profile": requested_profile,
        "status": diagnostic["status"],
    }
    return diagnostic, stable, set()


def _validate_registered_inventory(
    stage: SphericalBundleStage,
    ledger: Mapping[str, object],
    produced_files: set[str],
) -> None:
    artifacts = ledger.get("artifacts")
    extensions = ledger.get("extension_artifacts")
    if not isinstance(artifacts, dict) or not isinstance(extensions, dict):
        raise SphericalBundleCorruptionError("registered scientific inventory is invalid")
    registered = set(artifacts) | set(extensions) | produced_files | {_LEDGER_JSON}
    for path in stage.staging_path.rglob("*"):
        if not path.is_file():
            continue
        relative = str(path.relative_to(stage.staging_path))
        if relative == _MANIFEST or relative.startswith("diagnostics/"):
            continue
        if relative not in registered:
            raise SphericalBundleCorruptionError(
                f"unregistered non-diagnostic file cannot be published: {relative}"
            )


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


def _passed_output_records(diagnostic: Mapping[str, object]) -> dict[str, object] | None:
    if diagnostic.get("status") != "passed":
        return None
    metrics = diagnostic.get("metrics")
    if not isinstance(metrics, dict):
        return None
    records = metrics.get("validated_files")
    if not isinstance(records, dict):
        return None
    return records


def _read_winner_mtex_status(completed: Path) -> dict[str, object] | None:
    try:
        value = json.loads((completed / _MTEX_STATUS).read_bytes())
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _raise_existing_bundle(
    stage: SphericalBundleStage,
    completed: Path,
    run_id: str,
    candidate_diagnostic: Mapping[str, object],
) -> None:
    candidate_records = _passed_output_records(candidate_diagnostic)
    if candidate_records is not None:
        winner_diagnostic = _read_winner_mtex_status(completed)
        winner_records = (
            _passed_output_records(winner_diagnostic)
            if winner_diagnostic is not None
            else None
        )
        differing: dict[str, object] = {}
        if winner_records is None:
            differing["diagnostics/mtex-status.json"] = {
                "winner": None,
                "candidate": _artifact_record(stage.staging_path / _MTEX_STATUS),
            }
        else:
            for relative in sorted(set(winner_records) | set(candidate_records)):
                winner_record = winner_records.get(relative)
                candidate_record = candidate_records.get(relative)
                if winner_record != candidate_record:
                    differing[relative] = {
                        "winner": winner_record,
                        "candidate": candidate_record,
                    }
        if differing:
            winner_status_path = completed / _MTEX_STATUS
            investigation = {
                "schema_version": 1,
                "run_id": run_id,
                "status": "collision-requires-investigation",
                "differing_output_records": differing,
                "diagnostic_provenance": {
                    "candidate_mtex_status": _artifact_record(
                        stage.staging_path / _MTEX_STATUS
                    ),
                    "winner_mtex_status": (
                        _artifact_record(winner_status_path)
                        if winner_status_path.is_file()
                        else None
                    ),
                },
            }
            _write_json(
                stage.staging_path / _COLLISION_INVESTIGATION,
                investigation,
            )
            _fsync_directory_tree(stage.staging_path)
            raise SphericalBundleInvestigationError(
                f"stable spherical run collision requires investigation: {run_id}"
            )
    raise SphericalBundleExistsError(
        f"completed spherical bundle already exists: {completed}"
    )


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
        "identity_policy": {
            "scientific_files": "registered hashes included in stable run identity",
            "diagnostics": "inventoried by manifest and excluded from stable run identity",
        },
    }


def finalize_spherical_bundle(
    stage: SphericalBundleStage,
    *,
    mtex_result: _MtexRunResultLike | None = None,
) -> SphericalIntensityBundleResult:
    """Inventory, fsync, and atomically promote a validated S2 exchange stage."""
    ledger = _validate_stage(stage)
    partials = _partial_files(stage.staging_path)
    if partials:
        _write_failure_status(stage, "partial-artifact")
        relative = partials[0].relative_to(stage.staging_path)
        raise SphericalBundlePartialError(f"staged file still ends in .partial: {relative}")

    try:
        diagnostic, stable_mtex_identity, produced_files = _mtex_records(
            stage, ledger, mtex_result
        )
        _validate_registered_inventory(stage, ledger, produced_files)
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
    _write_json(stage.staging_path / _MTEX_STATUS, diagnostic)
    try:
        ownership.mkdir()
    except FileExistsError:
        if completed.exists():
            _raise_existing_bundle(stage, completed, run_id, diagnostic)
        raise SphericalBundlePartialError(
            f"same-run spherical publication already in progress: {ownership}"
        ) from None

    try:
        _fsync_directory(stage.output_root)
        if completed.exists():
            _raise_existing_bundle(stage, completed, run_id, diagnostic)
        stale_manifest = stage.staging_path / _MANIFEST
        if stale_manifest.exists():
            if not stale_manifest.is_file() or stale_manifest.is_symlink():
                raise SphericalBundleCorruptionError("stale spherical manifest is unsafe")
            stale_manifest.unlink()
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
                if completed.exists():
                    _raise_existing_bundle(stage, completed, run_id, diagnostic)
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
    "SphericalBundleInvestigationError",
    "SphericalBundlePartialError",
    "SphericalBundleStage",
    "SphericalIntensityBundleResult",
    "finalize_spherical_bundle",
    "stage_spherical_bundle",
]
