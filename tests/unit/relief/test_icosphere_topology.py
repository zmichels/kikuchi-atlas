import hashlib

import numpy as np
import pytest

from kikuchi_lab.relief.topology import build_icosphere


@pytest.mark.parametrize("level", range(8))
def test_icosphere_subdivision_ladder_has_exact_counts_and_orientation(level):
    topology = build_icosphere(level)
    assert len(topology.directions) == 10 * 4**level + 2
    assert len(topology.faces) == 20 * 4**level
    assert np.allclose(
        np.linalg.norm(topology.directions, axis=1), 1.0, atol=2e-15, rtol=0
    )
    a, b, c = topology.directions[topology.faces].transpose(1, 0, 2)
    assert np.all(np.einsum("ij,ij->i", np.cross(b - a, c - a), a) > 0)
    edges = np.sort(
        np.vstack(
            (
                topology.faces[:, [0, 1]],
                topology.faces[:, [1, 2]],
                topology.faces[:, [2, 0]],
            )
        ),
        axis=1,
    )
    unique_edges = np.unique(edges, axis=0)
    assert len(topology.directions) - len(unique_edges) + len(topology.faces) == 2


def test_canonical_level_seven_topology_is_stable():
    first = build_icosphere(7)
    second = build_icosphere(7)
    assert first.topology_id == second.topology_id
    assert len(first.directions) == 163842
    assert len(first.faces) == 327680
    assert (
        hashlib.sha256(first.directions.tobytes(order="C")).hexdigest()
        == "db2d0175bf29ff662f7e3acb16762ebee3687b74ca04e37c7790cf1e98e49a34"
    )
    assert (
        hashlib.sha256(first.faces.tobytes(order="C")).hexdigest()
        == "083a26ae07d4840cec1a501161e72f8e372ddd7bb0e6131b704fcedc301d8601"
    )
    assert hashlib.sha256(first.directions.tobytes()).digest() == hashlib.sha256(
        second.directions.tobytes()
    ).digest()
    assert hashlib.sha256(first.faces.tobytes()).digest() == hashlib.sha256(
        second.faces.tobytes()
    ).digest()
    assert np.array_equal(first.directions, second.directions)
    assert np.array_equal(first.faces, second.faces)


def test_icosphere_arrays_have_canonical_types_layout_and_immutability():
    topology = build_icosphere(2)
    assert topology.directions.dtype == np.float64
    assert topology.faces.dtype == np.int64
    assert topology.directions.flags.c_contiguous
    assert topology.faces.flags.c_contiguous
    assert not topology.directions.flags.writeable
    assert not topology.faces.flags.writeable


def test_icosphere_rejects_invalid_subdivision():
    for value in (-1, 8, True, 1.5):
        with pytest.raises(ValueError, match="subdivisions"):
            build_icosphere(value)
