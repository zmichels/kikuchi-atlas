from __future__ import annotations

from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from importlib import import_module
from pathlib import Path
import re
import sys

import numpy as np
import pytest

from kikuchi_lab.model.identity import plain_data
from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.projection.kikuchipy_adapter import (
    transform_crystal_direction_to_sample,
)
from kikuchi_lab.spherical_intensity.orientation import (
    orientation_ledger,
    orientation_matrix,
)
from kikuchi_lab.spherical_intensity.rotation import rotate_spherical_field


sys.path.insert(0, str(Path(__file__).parents[1]))
_fixtures = import_module("spherical_fixtures")
pytestmark = [
    pytest.mark.filterwarnings("ignore:.*GetSpaceGroup.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*placeInLattice.*:DeprecationWarning"),
]
_CHANNELS = (
    "xyz",
    "hemisphere",
    "source_row",
    "source_column",
    "intensity_raw",
    "intensity_normalized",
    "density_weight",
)
_NON_COORDINATE_CHANNELS = _CHANNELS[1:]


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [item for child in value.values() for item in _strings(child)]
    if isinstance(value, (list, tuple)):
        return [item for child in value for item in _strings(child)]
    return []


def test_identity_rotation_preserves_every_channel_exactly() -> None:
    source = _fixtures.small_spherical_build().field

    oriented = rotate_spherical_field(source, Orientation((0.0, 0.0, 0.0)))

    for name in _CHANNELS:
        np.testing.assert_array_equal(
            getattr(oriented.field, name), getattr(source, name)
        )
        assert oriented.field.channel_sha256[name] == source.channel_sha256[name]


def test_arbitrary_rotation_moves_only_xyz_and_matches_adapter() -> None:
    source = _fixtures.small_spherical_build().field
    orientation = Orientation((17.0, 31.0, 43.0))

    oriented = rotate_spherical_field(source, orientation)

    expected = np.stack(
        [
            transform_crystal_direction_to_sample(vector, orientation)
            for vector in source.xyz
        ]
    )
    np.testing.assert_allclose(oriented.field.xyz, expected, rtol=0.0, atol=5e-13)
    np.testing.assert_allclose(
        np.linalg.norm(oriented.field.xyz, axis=1), 1.0, rtol=0.0, atol=5e-13
    )
    assert oriented.field.channel_sha256["xyz"] != source.channel_sha256["xyz"]
    for name in _NON_COORDINATE_CHANNELS:
        np.testing.assert_array_equal(
            getattr(oriented.field, name), getattr(source, name)
        )
        assert oriented.field.channel_sha256[name] == source.channel_sha256[name]


def test_rotated_nodes_invert_to_the_exact_source_nodes() -> None:
    source = _fixtures.small_spherical_build().field
    orientation = Orientation((17.0, 31.0, 43.0))

    oriented = rotate_spherical_field(source, orientation)
    round_trip = oriented.field.xyz @ orientation_matrix(orientation)

    np.testing.assert_allclose(round_trip, source.xyz, rtol=0.0, atol=5e-13)
    assert oriented.ledger["maximum_inverse_error"] <= 5e-13


def test_oriented_field_arrays_and_ledger_reject_mutation() -> None:
    oriented = rotate_spherical_field(
        _fixtures.small_spherical_build().field,
        Orientation((17.0, 31.0, 43.0)),
    )

    for name in _CHANNELS:
        channel = getattr(oriented.field, name)
        assert not channel.flags.writeable
        with pytest.raises(ValueError):
            channel[...] = channel
    with pytest.raises(FrozenInstanceError):
        oriented.product_id = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        oriented.ledger["channel_sha256_before"]["xyz"] = "changed"  # type: ignore[index]


def test_oriented_identity_records_product_and_frame_provenance() -> None:
    source = _fixtures.small_spherical_build().field
    source_metadata = source.metadata_dict()
    identity = rotate_spherical_field(source, Orientation((0.0, 0.0, 0.0)))
    orientation = Orientation((17.0, 31.0, 43.0))

    oriented = rotate_spherical_field(source, orientation)

    assert oriented.product_id != identity.product_id
    assert oriented.source_field_id == source.field_id
    assert oriented.orientation_id == orientation.orientation_id
    assert oriented.ledger["output_axis_order"] == ("RD", "TD", "ND")
    assert oriented.ledger["source_field_id"] == source.field_id
    assert oriented.ledger["oriented_field_id"] == oriented.field.field_id
    assert plain_data(oriented.ledger) == {
        **orientation_ledger(orientation),
        "source_field_id": source.field_id,
        "oriented_field_id": oriented.field.field_id,
        "channel_sha256_before": dict(source.channel_sha256),
        "channel_sha256_after": dict(oriented.field.channel_sha256),
        "maximum_inverse_error": oriented.ledger["maximum_inverse_error"],
    }

    metadata = oriented.field.metadata_dict()
    assert source.metadata_dict() == source_metadata
    for name, value in source_metadata.items():
        if name != "frame":
            assert metadata[name] == value
    assert metadata["frame"] == {
        "name": "EDAX-TSL:RD-TD-ND",
        "handedness": "right-handed",
        "vector_units": "dimensionless",
    }
    assert metadata["orientation"] == orientation_ledger(orientation)
    assert metadata["oriented_from"] == {
        "source_field_id": source.field_id,
        "source_xyz_sha256": source.channel_sha256["xyz"],
    }
    assert not any(
        text.startswith(("/", "file://")) or re.match(r"^[A-Za-z]:[\\/]", text)
        for text in _strings(metadata)
    )
