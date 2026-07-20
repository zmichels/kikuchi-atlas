"""Exact active rotations of canonical directional S2 intensity fields."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from kikuchi_lab.model.identity import plain_data, stable_id
from kikuchi_lab.model.recipes import Orientation

from .contracts import SphericalIntensityField
from .orientation import orientation_ledger, orientation_matrix


def _freeze(value: object) -> object:
    plain = plain_data(value)
    if isinstance(plain, dict):
        return MappingProxyType({key: _freeze(item) for key, item in plain.items()})
    if isinstance(plain, list):
        return tuple(_freeze(item) for item in plain)
    return plain


@dataclass(frozen=True)
class OrientedSphericalIntensityField:
    """One immutable directional S2 field in an active sample orientation."""

    source_field_id: str
    field: SphericalIntensityField
    orientation_id: str
    ledger: Mapping[str, object]
    product_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ledger", _freeze(self.ledger))


def rotate_spherical_field(
    source: SphericalIntensityField,
    orientation: Orientation,
) -> OrientedSphericalIntensityField:
    """Actively rotate canonical crystal-frame nodes into RD-TD-ND coordinates."""
    matrix = orientation_matrix(orientation)
    if orientation.euler_bunge_deg == (0.0, 0.0, 0.0):
        xyz = source.xyz
    else:
        xyz = source.xyz @ matrix.T

    round_trip = xyz @ matrix
    if not np.allclose(round_trip, source.xyz, rtol=0.0, atol=5e-13):
        raise ValueError("oriented field inverse rotation exceeds 5e-13")

    metadata = source.metadata_dict()
    metadata["frame"] = {
        "name": "EDAX-TSL:RD-TD-ND",
        "handedness": "right-handed",
        "vector_units": "dimensionless",
    }
    metadata["orientation"] = orientation_ledger(orientation)
    metadata["oriented_from"] = {
        "source_field_id": source.field_id,
        "source_xyz_sha256": source.channel_sha256["xyz"],
    }
    field = SphericalIntensityField.from_columns(
        xyz=xyz,
        hemisphere=source.hemisphere,
        source_row=source.source_row,
        source_column=source.source_column,
        intensity_raw=source.intensity_raw,
        intensity_normalized=source.intensity_normalized,
        density_weight=source.density_weight,
        metadata=metadata,
    )

    unchanged = (
        "hemisphere",
        "source_row",
        "source_column",
        "intensity_raw",
        "intensity_normalized",
        "density_weight",
    )
    if any(
        field.channel_sha256[name] != source.channel_sha256[name]
        for name in unchanged
    ):
        raise ValueError("orientation changed a non-coordinate field channel")

    ledger = {
        **orientation_ledger(orientation),
        "source_field_id": source.field_id,
        "oriented_field_id": field.field_id,
        "channel_sha256_before": dict(source.channel_sha256),
        "channel_sha256_after": dict(field.channel_sha256),
        "maximum_inverse_error": float(np.max(np.abs(round_trip - source.xyz))),
    }
    return OrientedSphericalIntensityField(
        source_field_id=source.field_id,
        field=field,
        orientation_id=orientation.orientation_id,
        ledger=ledger,
        product_id=stable_id("oriented-s2", ledger),
    )
