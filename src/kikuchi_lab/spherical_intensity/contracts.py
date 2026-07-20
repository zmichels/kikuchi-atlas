"""Immutable project-owned contracts for sampled spherical intensity fields."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Literal

import numpy as np

from kikuchi_lab.model.identity import canonical_json, plain_data, stable_id


ProfileName = Literal["smoke", "acceptance"]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_METADATA_MAPPINGS = (
    "source",
    "projection",
    "frame",
    "grid",
    "phase",
    "equator",
    "normalization",
)


def _require_text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")


def _require_real(value: object, field: str, *, positive: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    if not math.isfinite(float(value)) or (positive and float(value) <= 0):
        qualifier = "positive and finite" if positive else "finite"
        raise ValueError(f"{field} must be {qualifier}")


def _require_positive_integer(value: object, field: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field} must be a positive integer")


def _require_relative_path(value: object, field: str) -> None:
    _require_text(value, field)
    assert isinstance(value, str)
    if value.startswith(("/", "file://")) or re.match(r"^[A-Za-z]:[\\/]", value):
        raise ValueError(f"{field} must be a relative path")


def _freeze(value: object) -> object:
    plain = plain_data(value)
    if isinstance(plain, dict):
        return MappingProxyType({key: _freeze(item) for key, item in plain.items()})
    if isinstance(plain, list):
        return tuple(_freeze(item) for item in plain)
    return plain


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _owned(value: object, dtype: np.dtype, shape_tail: tuple[int, ...]) -> np.ndarray:
    converted = np.array(value, dtype=dtype, order="C", copy=True)
    if converted.ndim != 1 + len(shape_tail) or converted.shape[1:] != shape_tail:
        raise ValueError(f"array shape must be (n, {', '.join(map(str, shape_tail))})")
    if converted.shape[0] == 0:
        raise ValueError("array columns must be non-empty")
    if not np.isfinite(converted).all():
        raise ValueError("array values must be finite")
    return np.frombuffer(converted.tobytes(order="C"), dtype=dtype).reshape(converted.shape)


def _hash_channels(channels: Mapping[str, np.ndarray]) -> dict[str, str]:
    return {
        name: hashlib.sha256(channel.tobytes(order="C")).hexdigest()
        for name, channel in channels.items()
    }


def _metadata_mapping(metadata: dict[str, object], name: str) -> dict[str, object]:
    value = metadata.get(name)
    if not isinstance(value, dict) or not value:
        raise ValueError(f"spherical field metadata {name} must be a non-empty mapping")
    return value


def _reject_absolute_paths(value: object, location: str = "metadata") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_absolute_paths(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_absolute_paths(item, f"{location}[{index}]")
    elif isinstance(value, str) and (
        value.startswith(("/", "file://")) or re.match(r"^[A-Za-z]:[\\/]", value)
    ):
        raise ValueError(f"{location} must not contain an absolute local path")


def _validated_metadata(
    metadata: Mapping[str, object], *, domain_semantics: Literal["directional", "axial-derived"]
) -> dict[str, object]:
    if not isinstance(metadata, Mapping):
        raise TypeError("spherical field metadata must be a mapping")
    plain = plain_data(metadata)
    if not isinstance(plain, dict):
        raise TypeError("spherical field metadata must be a mapping")
    if plain.get("kind") != "spherical_scalar_field":
        raise ValueError("spherical field metadata kind must be spherical_scalar_field")
    if plain.get("domain") != "S2":
        raise ValueError("spherical field metadata domain must be S2")
    if plain.get("domain_semantics") != domain_semantics:
        raise ValueError(
            f"spherical field metadata domain_semantics must be {domain_semantics}"
        )
    for name in _REQUIRED_METADATA_MAPPINGS:
        _metadata_mapping(plain, name)

    source = _metadata_mapping(plain, "source")
    _require_text(source.get("product_id"), "metadata source.product_id")
    checksum = source.get("array_sha256")
    if not isinstance(checksum, str) or not _SHA256.fullmatch(checksum):
        raise ValueError("metadata source.array_sha256 must be a lowercase SHA-256 digest")
    source_shape = source.get("shape")
    if (
        not isinstance(source_shape, list)
        or len(source_shape) != 3
        or any(type(dimension) is not int or dimension <= 0 for dimension in source_shape)
        or source_shape[0] != 2
        or source_shape[1] != source_shape[2]
    ):
        raise ValueError(
            "metadata source.shape must be [2, N, N] with positive integer dimensions"
        )
    _require_text(source.get("dtype"), "metadata source.dtype")
    _require_real(source.get("energy_kev"), "metadata source.energy_kev", positive=True)

    projection = _metadata_mapping(plain, "projection")
    if projection.get("name") != "stereographic":
        raise ValueError("metadata projection.name must be stereographic")
    if projection.get("hemisphere_order") != ["upper", "lower"]:
        raise ValueError("metadata projection.hemisphere_order must be [upper, lower]")
    poles = projection.get("poles")
    if not isinstance(poles, dict) or poles.get("upper") != -1 or poles.get("lower") != 1:
        raise ValueError("metadata projection.poles must define upper=-1 and lower=1")
    if projection.get("transform_owner") != (
        "orix.projections.InverseStereographicProjection"
    ):
        raise ValueError(
            "metadata projection.transform_owner must name "
            "orix.projections.InverseStereographicProjection"
        )
    _require_text(
        projection.get("transform_version"), "metadata projection.transform_version"
    )

    frame = _metadata_mapping(plain, "frame")
    _require_text(frame.get("name"), "metadata frame.name")
    if frame.get("handedness") != "right-handed":
        raise ValueError("metadata frame.handedness must be right-handed")
    if frame.get("vector_units") != "dimensionless":
        raise ValueError("metadata frame.vector_units must be dimensionless")

    grid = _metadata_mapping(plain, "grid")
    _require_positive_integer(grid.get("size"), "metadata grid.size")
    if grid.get("row_axis") != "Y ascending -1 to +1":
        raise ValueError("metadata grid.row_axis is missing or unsupported")
    if grid.get("column_axis") != "X ascending -1 to +1":
        raise ValueError("metadata grid.column_axis is missing or unsupported")
    if grid.get("X_formula") != "X(j) = -1 + 2*j/(N - 1)":
        raise ValueError("metadata grid.X_formula is missing or unsupported")
    if grid.get("Y_formula") != "Y(i) = -1 + 2*i/(N - 1)":
        raise ValueError("metadata grid.Y_formula is missing or unsupported")
    if source_shape[1:] != [grid["size"], grid["size"]]:
        raise ValueError("metadata source.shape must agree with metadata grid.size")

    phase = _metadata_mapping(plain, "phase")
    _require_positive_integer(phase.get("space_group"), "metadata phase.space_group")
    _require_text(phase.get("point_group"), "metadata phase.point_group")
    if not isinstance(phase.get("contains_inversion"), bool):
        raise ValueError("metadata phase.contains_inversion must be boolean")

    equator = _metadata_mapping(plain, "equator")
    if equator.get("owner") != "upper":
        raise ValueError("metadata equator.owner must be upper")

    normalization = _metadata_mapping(plain, "normalization")
    _require_text(normalization.get("name"), "metadata normalization.name")

    if domain_semantics == "axial-derived":
        axial = _metadata_mapping(plain, "axial")
        _require_text(axial.get("representative_rule"), "metadata axial.representative_rule")
        _require_text(axial.get("source_pair_rule"), "metadata axial.source_pair_rule")

    _reject_absolute_paths(plain)
    canonical_json(plain)
    return plain


def _validate_vectors(vectors: np.ndarray) -> None:
    norm_error = np.abs(np.linalg.norm(vectors, axis=1) - 1.0)
    if float(np.max(norm_error, initial=0.0)) > 5e-13:
        raise ValueError("xyz must contain unit vectors within 5e-13")


def _validate_intensity_columns(
    columns: Mapping[str, np.ndarray], *, count: int
) -> None:
    if any(column.shape != (count,) for column in columns.values()):
        raise ValueError("spherical field columns must have equal length")
    normalized = columns["intensity_normalized"]
    if np.any((normalized < 0) | (normalized > 1)):
        raise ValueError("intensity_normalized must be within inclusive [0, 1]")
    if np.any(columns["density_weight"] < 0):
        raise ValueError("density_weight must be nonnegative")


@dataclass(frozen=True)
class DensityWeightRecipe:
    name: str
    low_percentile: float
    high_percentile: float
    exponent: float

    def __post_init__(self) -> None:
        _require_text(self.name, "density name")
        _require_real(self.low_percentile, "density low_percentile")
        _require_real(self.high_percentile, "density high_percentile")
        _require_real(self.exponent, "density exponent", positive=True)
        if not 0 <= self.low_percentile < self.high_percentile <= 100:
            raise ValueError("density percentiles must increase within [0, 100]")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SphericalToleranceRecipe:
    disk_epsilon_multiplier: int
    unit_norm_max: float
    stereo_round_trip_rad_max: float
    equator_normalized_max: float
    axial_normalized_rms_max: float
    axial_normalized_max: float
    mtex_node_normalized_max: float

    def __post_init__(self) -> None:
        _require_positive_integer(self.disk_epsilon_multiplier, "disk_epsilon_multiplier")
        for field in (
            "unit_norm_max",
            "stereo_round_trip_rad_max",
            "equator_normalized_max",
            "axial_normalized_rms_max",
            "axial_normalized_max",
            "mtex_node_normalized_max",
        ):
            _require_real(getattr(self, field), field, positive=True)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SphericalProfile:
    name: ProfileName
    half_size: int
    point_count: int
    sampling_resolution_deg: float
    timeout_seconds: int

    def __post_init__(self) -> None:
        if self.name not in {"smoke", "acceptance"}:
            raise ValueError("profile name must be smoke or acceptance")
        _require_positive_integer(self.half_size, "profile half_size")
        _require_positive_integer(self.point_count, "profile point_count")
        _require_real(
            self.sampling_resolution_deg,
            "profile sampling_resolution_deg",
            positive=True,
        )
        _require_positive_integer(self.timeout_seconds, "profile timeout_seconds")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SphericalIntensityRecipe:
    schema_version: int
    name: str
    source_kinematical_recipe: str
    profile: SphericalProfile
    density: DensityWeightRecipe
    tolerances: SphericalToleranceRecipe
    rng_seed: int
    rng_generator: str
    csv_float_format: str
    display_resolution_deg: float
    emit_axial: bool
    expected_mtex_version: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("schema_version must be integer 1")
        _require_text(self.name, "recipe name")
        _require_relative_path(
            self.source_kinematical_recipe, "source_kinematical_recipe"
        )
        _require_positive_integer(self.rng_seed, "rng_seed")
        _require_text(self.rng_generator, "rng_generator")
        _require_text(self.csv_float_format, "csv_float_format")
        _require_real(self.display_resolution_deg, "display_resolution_deg", positive=True)
        if not isinstance(self.emit_axial, bool):
            raise ValueError("emit_axial must be boolean")
        _require_text(self.expected_mtex_version, "expected_mtex_version")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "source_kinematical_recipe": self.source_kinematical_recipe,
            "profile": self.profile.to_dict(),
            "density": self.density.to_dict(),
            "tolerances": self.tolerances.to_dict(),
            "rng_seed": self.rng_seed,
            "rng_generator": self.rng_generator,
            "csv_float_format": self.csv_float_format,
            "display_resolution_deg": self.display_resolution_deg,
            "emit_axial": self.emit_axial,
            "expected_mtex_version": self.expected_mtex_version,
        }

    @property
    def recipe_id(self) -> str:
        scientific_recipe = self.to_dict()
        del scientific_recipe["source_kinematical_recipe"]
        return stable_id("recipe", scientific_recipe)


@dataclass(frozen=True, init=False, eq=False)
class SphericalIntensityField:
    xyz: np.ndarray
    hemisphere: np.ndarray
    source_row: np.ndarray
    source_column: np.ndarray
    intensity_raw: np.ndarray
    intensity_normalized: np.ndarray
    density_weight: np.ndarray
    metadata: Mapping[str, object]
    channel_sha256: Mapping[str, str]
    field_id: str

    @classmethod
    def from_columns(
        cls,
        *,
        xyz: object,
        hemisphere: object,
        source_row: object,
        source_column: object,
        intensity_raw: object,
        intensity_normalized: object,
        density_weight: object,
        metadata: Mapping[str, object],
    ) -> SphericalIntensityField:
        vectors = _owned(xyz, np.dtype("<f8"), (3,))
        columns = {
            "hemisphere": _owned(hemisphere, np.dtype("i1"), ()),
            "source_row": _owned(source_row, np.dtype("<i4"), ()),
            "source_column": _owned(source_column, np.dtype("<i4"), ()),
            "intensity_raw": _owned(intensity_raw, np.dtype("<f4"), ()),
            "intensity_normalized": _owned(
                intensity_normalized, np.dtype("<f8"), ()
            ),
            "density_weight": _owned(density_weight, np.dtype("<f8"), ()),
        }
        count = vectors.shape[0]
        _validate_vectors(vectors)
        _validate_intensity_columns(columns, count=count)
        if not set(np.unique(columns["hemisphere"])).issubset({-1, 1}):
            raise ValueError("hemisphere must use +1 upper and -1 lower")
        if np.any(columns["source_row"] < 0) or np.any(columns["source_column"] < 0):
            raise ValueError("source row and column indices must be nonnegative")

        channels = {"xyz": vectors, **columns}
        hashes = _hash_channels(channels)
        plain = _validated_metadata(metadata, domain_semantics="directional")
        product = object.__new__(cls)
        for name, channel in channels.items():
            object.__setattr__(product, name, channel)
        object.__setattr__(product, "metadata", _freeze(plain))
        object.__setattr__(product, "channel_sha256", _freeze(hashes))
        object.__setattr__(
            product,
            "field_id",
            stable_id("s2-field", {"metadata": plain, "channel_sha256": hashes}),
        )
        return product

    def metadata_dict(self) -> dict[str, object]:
        thawed = _thaw(self.metadata)
        assert isinstance(thawed, dict)
        return thawed


@dataclass(frozen=True, init=False, eq=False)
class SphericalAxialField:
    xyz: np.ndarray
    source_pairs: np.ndarray
    intensity_raw: np.ndarray
    intensity_normalized: np.ndarray
    density_weight: np.ndarray
    metadata: Mapping[str, object]
    channel_sha256: Mapping[str, str]
    field_id: str

    @classmethod
    def from_columns(
        cls,
        *,
        xyz: object,
        source_pairs: object,
        intensity_raw: object,
        intensity_normalized: object,
        density_weight: object,
        metadata: Mapping[str, object],
    ) -> SphericalAxialField:
        vectors = _owned(xyz, np.dtype("<f8"), (3,))
        pairs = _owned(source_pairs, np.dtype("<i4"), (2, 3))
        columns = {
            "intensity_raw": _owned(intensity_raw, np.dtype("<f4"), ()),
            "intensity_normalized": _owned(
                intensity_normalized, np.dtype("<f8"), ()
            ),
            "density_weight": _owned(density_weight, np.dtype("<f8"), ()),
        }
        count = vectors.shape[0]
        _validate_vectors(vectors)
        _validate_intensity_columns(columns, count=count)
        if pairs.shape[0] != count:
            raise ValueError("spherical axial columns must have equal length")
        if not np.all(pairs[:, 0, 0] == 1) or not np.all(pairs[:, 1, 0] == -1):
            raise ValueError("source pair hemisphere values must be ordered [+1, -1]")
        if np.any(pairs[:, :, 1:] < 0):
            raise ValueError("source pair row and column indices must be nonnegative")

        channels = {"xyz": vectors, "source_pairs": pairs, **columns}
        hashes = _hash_channels(channels)
        plain = _validated_metadata(metadata, domain_semantics="axial-derived")
        product = object.__new__(cls)
        for name, channel in channels.items():
            object.__setattr__(product, name, channel)
        object.__setattr__(product, "metadata", _freeze(plain))
        object.__setattr__(product, "channel_sha256", _freeze(hashes))
        object.__setattr__(
            product,
            "field_id",
            stable_id("s2-axial", {"metadata": plain, "channel_sha256": hashes}),
        )
        return product

    def metadata_dict(self) -> dict[str, object]:
        thawed = _thaw(self.metadata)
        assert isinstance(thawed, dict)
        return thawed


@dataclass(frozen=True)
class SphericalIntensityBuild:
    field: SphericalIntensityField
    axial_field: SphericalAxialField | None
    diagnostics: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.field, SphericalIntensityField):
            raise TypeError("field must be a SphericalIntensityField")
        if self.axial_field is not None and not isinstance(
            self.axial_field, SphericalAxialField
        ):
            raise TypeError("axial_field must be a SphericalAxialField or None")
        if not isinstance(self.diagnostics, Mapping):
            raise TypeError("spherical build diagnostics must be a mapping")
        object.__setattr__(self, "diagnostics", _freeze(self.diagnostics))

    def diagnostics_dict(self) -> dict[str, object]:
        thawed = _thaw(self.diagnostics)
        if not isinstance(thawed, dict):
            raise TypeError("spherical build diagnostics must be a mapping")
        return thawed
