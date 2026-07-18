from __future__ import annotations

import numpy as np
import pytest

from kikuchi_lab.globe_mesh import (
    GlobeGeometrySpec,
    build_radial_geometry,
    validate_globe_mesh,
)
from kikuchi_lab.relief.mapping import build_relief_geometry
from kikuchi_lab.relief.topology import build_icosphere


def test_generic_globe_geometry_accepts_three_mm_relief() -> None:
    topology = build_icosphere(2)
    spec = GlobeGeometrySpec(80.0, 3.0, 2)

    geometry = build_radial_geometry(topology, np.ones(len(topology.directions)), spec)

    assert np.allclose(geometry.radii_mm, 43.0)
    assert validate_globe_mesh(geometry, topology, spec).passed


def test_existing_canonical_relief_rejects_noncanonical_geometry() -> None:
    with pytest.raises(ValueError, match="80.0 mm diameter and 1.2 mm relief"):
        build_relief_geometry(build_icosphere(2), np.zeros(162), 80.0, 3.0)


@pytest.mark.parametrize(
    "spec",
    [
        GlobeGeometrySpec(80.0, 1.2, 2),
        GlobeGeometrySpec(80.0, 3.0, 2),
    ],
)
def test_generic_globe_geometry_preserves_topology(spec: GlobeGeometrySpec) -> None:
    topology = build_icosphere(spec.subdivisions)
    geometry = build_radial_geometry(topology, np.zeros(len(topology.directions)), spec)

    assert np.array_equal(geometry.directions, topology.directions)
    assert np.array_equal(geometry.faces, topology.faces)
    assert geometry.base_radius_mm == pytest.approx(spec.base_diameter_mm / 2.0)
