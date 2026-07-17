import hashlib
import io
import zipfile
from dataclasses import replace
from pathlib import Path

import imageio.v3 as iio
import numpy as np
import pytest
import trimesh

from kikuchi_lab.relief import ReliefFDMContext, ReliefGeometry, build_icosphere
from kikuchi_lab.relief.mesh import (
    FIELD_ARRAY_ORDER,
    ReliefFieldArtifact,
    relief_field_npz_bytes,
    relief_stl_bytes,
    validate_relief_mesh,
    write_relief_preview,
)
from kikuchi_lab.relief.topology import IcosphereTopology


@pytest.fixture
def relief_fixture():
    topology = build_icosphere(2)
    filtered = 0.5 * (topology.directions[:, 2] + 1.0)
    radii = 40.0 + 1.2 * filtered
    geometry = ReliefGeometry(
        topology_id=topology.topology_id,
        directions=topology.directions,
        faces=topology.faces,
        filtered_values=filtered,
        radii_mm=radii,
        vertices=topology.directions * radii[:, None],
        base_radius_mm=40.0,
        maximum_relief_mm=1.2,
    )
    return topology, geometry


@pytest.fixture
def field_artifact(relief_fixture):
    topology, geometry = relief_fixture
    count = len(topology.directions)
    return ReliefFieldArtifact(
        directions=topology.directions,
        hemisphere=np.where(topology.directions[:, 2] >= 0.0, 1, -1).astype(np.int8),
        source_rows=np.zeros((count, 4), dtype=np.int32),
        source_columns=np.ones((count, 4), dtype=np.int32),
        weights=np.full((count, 4), 0.25, dtype=np.float64),
        sampled_raw=np.linspace(0.0, 2.0, count, dtype=np.float64),
        mapped=np.linspace(0.0, 1.0, count, dtype=np.float64),
        filtered=geometry.filtered_values,
        radii_mm=geometry.radii_mm,
        faces=topology.faces,
    )


def test_valid_radial_mesh_passes_without_mutation(relief_fixture):
    topology, geometry = relief_fixture
    before_vertices = geometry.vertices.copy()
    before_faces = geometry.faces.copy()
    report = validate_relief_mesh(geometry, topology, fdm_context=None)

    assert report.passed is True
    assert report.watertight is True
    assert report.winding_consistent is True
    assert report.body_count == 1
    assert report.euler_characteristic == 2
    assert report.radial_certificate_minimum > report.radial_certificate_tolerance
    assert report.maximum_radius_mm <= 41.2 + 1e-10
    assert report.self_intersection_contract == (
        "positive-radial-bijection-over-canonical-icosphere"
    )
    assert report.to_dict()["warnings"] == []
    assert np.array_equal(geometry.vertices, before_vertices)
    assert np.array_equal(geometry.faces, before_faces)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda g: replace(g, faces=g.faces[:-1]), "canonical topology"),
        (lambda g: replace(g, faces=np.vstack((g.faces, g.faces[0]))), "canonical topology"),
        (lambda g: replace(g, faces=g.faces[:, ::-1]), "canonical topology"),
        (
            lambda g: replace(g, vertices=g.vertices * np.array([1.0, 1.0, -1.0])),
            "radial projection",
        ),
    ],
)
def test_validation_rejects_topology_and_radial_failures(relief_fixture, mutation, message):
    topology, geometry = relief_fixture
    broken = mutation(geometry)
    with pytest.raises(ValueError, match=message):
        validate_relief_mesh(broken, topology, fdm_context=None)


@pytest.mark.parametrize("radius", [39.9, 41.3])
def test_validation_rejects_vertices_outside_configured_radial_range(
    relief_fixture, radius
):
    topology, geometry = relief_fixture
    vertices = geometry.directions * radius
    broken = replace(geometry, vertices=vertices, radii_mm=np.full(len(vertices), radius))
    with pytest.raises(ValueError, match="configured radial range"):
        validate_relief_mesh(broken, topology, fdm_context=None)


def test_validation_rejects_nonfinite_and_degenerate_vertices(relief_fixture):
    topology, geometry = relief_fixture
    nonfinite = geometry.vertices.copy()
    nonfinite[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite vertices"):
        validate_relief_mesh(replace(geometry, vertices=nonfinite), topology, None)

    degenerate = geometry.vertices.copy()
    degenerate[geometry.faces[0, 1]] = degenerate[geometry.faces[0, 0]]
    with pytest.raises(ValueError, match="degenerate triangles"):
        validate_relief_mesh(replace(geometry, vertices=degenerate), topology, None)


def test_validation_rejects_changed_direction_order(relief_fixture):
    topology, geometry = relief_fixture
    changed = geometry.directions.copy()
    changed[[0, 1]] = changed[[1, 0]]
    with pytest.raises(ValueError, match="canonical topology"):
        validate_relief_mesh(replace(geometry, directions=changed), topology, None)


def test_canonical_validation_proves_edge_incidence_uniqueness_and_connectivity(
    relief_fixture,
):
    topology, geometry = relief_fixture

    duplicate_faces = topology.faces.copy()
    duplicate_faces[-1] = duplicate_faces[0]
    duplicate_topology = replace(topology, faces=duplicate_faces)
    with pytest.raises(ValueError, match="triangle uniqueness"):
        validate_relief_mesh(
            replace(geometry, faces=duplicate_faces), duplicate_topology, fdm_context=None
        )

    bad_incidence_faces = topology.faces.copy()
    bad_incidence_faces[-1] = (0, 1, 2)
    bad_incidence_topology = replace(topology, faces=bad_incidence_faces)
    with pytest.raises(ValueError, match="edge incidence exactly two"):
        validate_relief_mesh(
            replace(geometry, faces=bad_incidence_faces),
            bad_incidence_topology,
            fdm_context=None,
        )

    directions = np.array(
        [(1, 1, 1), (-1, -1, 1), (-1, 1, -1), (1, -1, -1)], dtype=np.float64
    )
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    directions = np.vstack((directions, -directions))
    faces = np.array(
        [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3),
         (4, 6, 5), (4, 5, 7), (4, 7, 6), (5, 6, 7)],
        dtype=np.int64,
    )
    disconnected_topology = IcosphereTopology("disconnected", 0, directions, faces)
    disconnected_geometry = ReliefGeometry(
        "disconnected", directions, faces, np.zeros(8), np.full(8, 40.0),
        directions * 40.0, 40.0, 1.2
    )
    with pytest.raises(ValueError, match="one connected component"):
        validate_relief_mesh(disconnected_geometry, disconnected_topology, None)


def test_fdm_observations_are_advisory_and_nonmutating(relief_fixture):
    topology, geometry = relief_fixture
    before_vertices = geometry.vertices.copy()
    before_faces = geometry.faces.copy()
    report = validate_relief_mesh(
        geometry, topology, fdm_context=ReliefFDMContext(process="FDM")
    )

    assert report.passed is True
    assert [warning["code"] for warning in report.warnings] == [
        "fdm_minimum_edge",
        "fdm_minimum_triangle_altitude",
        "fdm_maximum_local_relief_slope",
        "fdm_radial_dynamic_range",
        "fdm_downward_face_fraction",
        "fdm_feature_floor",
    ]
    assert report.warnings[-1]["configured_mm"] == 0.8
    assert 0.0 < report.warnings[4]["measured_fraction"] < 1.0
    assert np.array_equal(geometry.vertices, before_vertices)
    assert np.array_equal(geometry.faces, before_faces)


def test_binary_stl_round_trip_is_one_slicer_style_volume(relief_fixture):
    topology, geometry = relief_fixture
    validate_relief_mesh(geometry, topology, fdm_context=None)
    payload = relief_stl_bytes(geometry, topology)
    assert payload == relief_stl_bytes(geometry, topology)
    loaded = trimesh.load_mesh(io.BytesIO(payload), file_type="stl", process=True)
    assert loaded.is_volume and loaded.body_count == 1


def test_field_npz_is_byte_deterministic_and_has_fixed_inventory(field_artifact):
    first = relief_field_npz_bytes(field_artifact)
    second = relief_field_npz_bytes(field_artifact)
    assert first == second
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert archive.namelist() == [f"{name}.npy" for name in FIELD_ARRAY_ORDER]
        assert {item.date_time for item in archive.infolist()} == {(1980, 1, 1, 0, 0, 0)}
        assert np.load(archive.open("faces.npy"), allow_pickle=False).dtype == np.int64


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("directions", lambda a: a.astype(np.float32)),
        ("hemisphere", lambda a: a.astype(np.int64)),
        ("source_rows", lambda a: a[:, :3]),
        ("weights", lambda a: np.full_like(a, np.nan)),
        ("faces", lambda a: a.astype(np.int32)),
    ],
)
def test_field_npz_rejects_wrong_dtype_shape_and_finiteness(field_artifact, field, value):
    with pytest.raises(ValueError, match=field):
        relief_field_npz_bytes(replace(field_artifact, **{field: value(getattr(field_artifact, field))}))


def test_preview_is_deterministic_rgba_and_keeps_full_mesh(
    tmp_path: Path, relief_fixture, monkeypatch
):
    topology, geometry = relief_fixture
    validation = validate_relief_mesh(geometry, topology, None)
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    captured = []
    import kikuchi_lab.relief.mesh as mesh_module

    original = mesh_module.Poly3DCollection

    def recording_collection(triangles, *args, **kwargs):
        captured.append(len(triangles))
        return original(triangles, *args, **kwargs)

    monkeypatch.setattr(mesh_module, "Poly3DCollection", recording_collection)
    kwargs = dict(lower_percentile=2.0, upper_percentile=98.0, gamma=0.8, filter_fwhm_mm=0.6)
    write_relief_preview(first, geometry, validation, **kwargs)
    write_relief_preview(second, geometry, validation, **kwargs)

    assert captured == [len(geometry.faces), len(geometry.faces)]
    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()
    image = iio.imread(first)
    assert image.shape == (900, 900, 4)
