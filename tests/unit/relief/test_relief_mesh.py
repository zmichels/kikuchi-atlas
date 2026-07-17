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
    validate_canonical_relief_mesh,
    validate_relief_mesh,
    write_relief_preview,
)
from kikuchi_lab.relief.topology import IcosphereTopology


def _geometry(topology, filtered=None, *, base=40.0, maximum=1.2):
    if filtered is None:
        filtered = 0.5 * (topology.directions[:, 2] + 1.0)
    radii = base + maximum * filtered
    return ReliefGeometry(
        topology_id=topology.topology_id,
        directions=topology.directions,
        faces=topology.faces,
        filtered_values=filtered,
        radii_mm=radii,
        vertices=topology.directions * radii[:, None],
        base_radius_mm=base,
        maximum_relief_mm=maximum,
    )


@pytest.fixture(scope="module")
def relief_fixture():
    topology = build_icosphere(2)
    return topology, _geometry(topology)


@pytest.fixture(scope="module")
def canonical_fixture():
    topology = build_icosphere(7)
    geometry = _geometry(topology)
    validation = validate_canonical_relief_mesh(geometry, topology, fdm_context=None)
    return topology, geometry, validation


@pytest.fixture(scope="module")
def field_artifact(canonical_fixture):
    topology, geometry, _ = canonical_fixture
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
    assert report.topology_fingerprint.startswith("relief-topology-sha256-")
    assert report.geometry_fingerprint.startswith("relief-geometry-sha256-")
    assert len(report.topology_fingerprint.rsplit("-", 1)[1]) == 64
    assert len(report.geometry_fingerprint.rsplit("-", 1)[1]) == 64
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
            "radial representation",
        ),
    ],
)
def test_validation_rejects_topology_and_radial_failures(relief_fixture, mutation, message):
    topology, geometry = relief_fixture
    with pytest.raises(ValueError, match=message):
        validate_relief_mesh(mutation(geometry), topology, fdm_context=None)


@pytest.mark.parametrize("radius", [39.9, 41.3])
def test_validation_rejects_vertices_outside_configured_radial_range(
    relief_fixture, radius
):
    topology, geometry = relief_fixture
    filtered = np.full(len(geometry.vertices), (radius - 40.0) / 1.2)
    broken = replace(
        geometry,
        filtered_values=filtered,
        vertices=geometry.directions * radius,
        radii_mm=np.full(len(geometry.vertices), radius),
    )
    with pytest.raises(ValueError, match="configured radial range|filtered values"):
        validate_relief_mesh(broken, topology, fdm_context=None)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda g: replace(g, vertices=g.vertices + np.array([0.01, 0.0, 0.0])),
            "radial representation",
        ),
        (
            lambda g: replace(g, radii_mm=np.full(len(g.radii_mm), np.nan)),
            "radii_mm",
        ),
        (
            lambda g: replace(g, radii_mm=g.radii_mm + 0.01),
            "radial representation",
        ),
        (
            lambda g: replace(g, filtered_values=np.full(len(g.radii_mm), np.nan)),
            "filtered values",
        ),
        (
            lambda g: replace(g, filtered_values=1.0 - g.filtered_values),
            "radius displacement",
        ),
    ],
)
def test_validation_rejects_spoofed_radial_arrays(relief_fixture, mutation, message):
    topology, geometry = relief_fixture
    with pytest.raises(ValueError, match=message):
        validate_relief_mesh(mutation(geometry), topology, None)


def test_actual_radius_cannot_stack_ledger_and_representation_tolerances(
    relief_fixture,
):
    topology, geometry = relief_fixture
    index = int(np.argmax(geometry.filtered_values))
    upper = geometry.base_radius_mm + geometry.maximum_relief_mm
    filtered = geometry.filtered_values.copy()
    filtered[index] = 1.0
    radii = geometry.radii_mm.copy()
    radii[index] = upper + 0.79e-10
    vertices = geometry.vertices.copy()
    vertices[index] = geometry.directions[index] * (upper + 1.78e-10)
    stacked = replace(
        geometry,
        filtered_values=filtered,
        radii_mm=radii,
        vertices=vertices,
    )

    with pytest.raises(ValueError, match="actual vertex radial range"):
        validate_relief_mesh(stacked, topology, None)


@pytest.mark.parametrize(("filtered_value", "offset"), [(0.0, -0.99e-10), (1.0, 0.99e-10)])
def test_actual_and_ledger_radii_pass_inside_each_physical_tolerance_boundary(
    relief_fixture, filtered_value, offset
):
    topology, geometry = relief_fixture
    index = int(
        np.argmin(geometry.filtered_values)
        if filtered_value == 0.0
        else np.argmax(geometry.filtered_values)
    )
    configured = geometry.base_radius_mm + geometry.maximum_relief_mm * filtered_value
    accepted_radius = configured + offset
    filtered = geometry.filtered_values.copy()
    filtered[index] = filtered_value
    radii = geometry.radii_mm.copy()
    radii[index] = accepted_radius
    vertices = geometry.vertices.copy()
    vertices[index] = geometry.directions[index] * accepted_radius

    report = validate_relief_mesh(
        replace(
            geometry,
            filtered_values=filtered,
            radii_mm=radii,
            vertices=vertices,
        ),
        topology,
        None,
    )
    assert report.passed is True


def test_validation_rejects_nonunit_topology_directions(relief_fixture):
    topology, geometry = relief_fixture
    directions = topology.directions.copy()
    directions[0] *= 1.01
    spoofed_topology = replace(topology, directions=directions)
    spoofed_geometry = replace(
        geometry,
        directions=directions,
        vertices=directions * geometry.radii_mm[:, None],
    )
    with pytest.raises(ValueError, match="finite unit directions"):
        validate_relief_mesh(spoofed_geometry, spoofed_topology, None)


def test_validation_rejects_nonfinite_and_degenerate_vertices(relief_fixture):
    topology, geometry = relief_fixture
    nonfinite = geometry.vertices.copy()
    nonfinite[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite vertices"):
        validate_relief_mesh(replace(geometry, vertices=nonfinite), topology, None)

    degenerate = geometry.vertices.copy()
    degenerate[geometry.faces[0, 1]] = degenerate[geometry.faces[0, 0]]
    with pytest.raises(ValueError, match="radial representation|degenerate triangles"):
        validate_relief_mesh(replace(geometry, vertices=degenerate), topology, None)


def test_validation_rejects_changed_direction_order(relief_fixture):
    topology, geometry = relief_fixture
    changed = geometry.directions.copy()
    changed[[0, 1]] = changed[[1, 0]]
    with pytest.raises(ValueError, match="canonical topology"):
        validate_relief_mesh(replace(geometry, directions=changed), topology, None)


def test_topology_validation_proves_edge_incidence_uniqueness_and_connectivity(
    relief_fixture,
):
    topology, geometry = relief_fixture
    duplicate_faces = topology.faces.copy()
    duplicate_faces[-1] = duplicate_faces[0]
    duplicate_topology = replace(topology, faces=duplicate_faces)
    with pytest.raises(ValueError, match="triangle uniqueness"):
        validate_relief_mesh(replace(geometry, faces=duplicate_faces), duplicate_topology, None)

    bad_incidence_faces = topology.faces.copy()
    bad_incidence_faces[-1] = (0, 1, 2)
    bad_incidence_topology = replace(topology, faces=bad_incidence_faces)
    with pytest.raises(ValueError, match="edge incidence exactly two"):
        validate_relief_mesh(
            replace(geometry, faces=bad_incidence_faces), bad_incidence_topology, None
        )
    directions = np.array(
        [(1, 1, 1), (-1, -1, 1), (-1, 1, -1), (1, -1, -1)], dtype=np.float64
    )
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    directions = np.vstack((directions, -directions))
    faces = np.array(
        [
            (0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3),
            (4, 6, 5), (4, 5, 7), (4, 7, 6), (5, 6, 7),
        ],
        dtype=np.int64,
    )
    disconnected_topology = IcosphereTopology("disconnected", 0, directions, faces)
    disconnected_geometry = _geometry(disconnected_topology)
    with pytest.raises(ValueError, match="one connected component"):
        validate_relief_mesh(disconnected_geometry, disconnected_topology, None)


def test_fdm_observations_are_advisory_and_nonmutating(relief_fixture):
    topology, geometry = relief_fixture
    before_vertices = geometry.vertices.copy()
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
    assert np.array_equal(geometry.vertices, before_vertices)


def test_canonical_gate_accepts_only_approved_topology_and_dimensions(canonical_fixture):
    topology, geometry, report = canonical_fixture
    assert topology.subdivisions == 7 and report.passed

    small = build_icosphere(2)
    with pytest.raises(ValueError, match="approved subdivision-7"):
        validate_canonical_relief_mesh(_geometry(small), small, None)
    with pytest.raises(ValueError, match="approved canonical topology"):
        validate_canonical_relief_mesh(
            replace(geometry, topology_id="spoof"), replace(topology, topology_id="spoof"), None
        )
    for changed in (
        _geometry(topology, base=39.0, maximum=1.2),
        _geometry(topology, base=40.0, maximum=1.1),
    ):
        with pytest.raises(ValueError, match="40.0 mm base.*1.2 mm"):
            validate_canonical_relief_mesh(changed, topology, None)


def test_binary_stl_uses_canonical_gate(canonical_fixture, relief_fixture):
    topology, geometry, _ = canonical_fixture
    payload = relief_stl_bytes(geometry, topology)
    assert payload == relief_stl_bytes(geometry, topology)
    loaded = trimesh.load_mesh(io.BytesIO(payload), file_type="stl", process=True)
    assert loaded.is_volume and loaded.body_count == 1
    small_topology, small_geometry = relief_fixture
    with pytest.raises(ValueError, match="approved subdivision-7"):
        relief_stl_bytes(small_geometry, small_topology)


def test_field_npz_is_bound_and_byte_deterministic(canonical_fixture, field_artifact):
    topology, geometry, validation = canonical_fixture
    first = relief_field_npz_bytes(field_artifact, geometry, topology, validation)
    second = relief_field_npz_bytes(field_artifact, geometry, topology, validation)
    assert first == second
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert archive.namelist() == [f"{name}.npy" for name in FIELD_ARRAY_ORDER]
        assert {item.date_time for item in archive.infolist()} == {(1980, 1, 1, 0, 0, 0)}
        assert np.load(archive.open("faces.npy"), allow_pickle=False).dtype == np.int64


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("directions", lambda a: np.array(1.0), "directions"),
        ("directions", lambda a: np.roll(a, 1, axis=0), "canonical directions"),
        ("hemisphere", lambda a: -a, "hemisphere alignment"),
        ("source_rows", lambda a: np.full_like(a, -1), "source_rows"),
        ("weights", lambda a: a * 0.5, "weights.*sum"),
        ("weights", lambda a: replace_value(a, (0, 0), -0.1), "weights.*nonnegative"),
        ("mapped", lambda a: replace_value(a, 0, 1.1), "mapped"),
        ("filtered", lambda a: np.roll(a, 1), "filtered.*canonical geometry"),
        ("radii_mm", lambda a: np.roll(a, 1), "radii_mm.*canonical geometry"),
        ("faces", lambda a: np.roll(a, 1, axis=0), "faces.*canonical topology"),
    ],
)
def test_field_npz_rejects_malformed_or_misaligned_artifact(
    canonical_fixture, field_artifact, field, value, message
):
    topology, geometry, validation = canonical_fixture
    altered = replace(field_artifact, **{field: value(getattr(field_artifact, field))})
    with pytest.raises(ValueError, match=message):
        relief_field_npz_bytes(altered, geometry, topology, validation)


def replace_value(array, index, value):
    changed = array.copy()
    changed[index] = value
    return changed


def test_npz_and_preview_reject_stale_validation_report(canonical_fixture, field_artifact, tmp_path):
    topology, geometry, validation = canonical_fixture
    filtered = geometry.filtered_values.copy()
    filtered[[10, 11]] = filtered[[11, 10]]
    altered = _geometry(topology, filtered)
    with pytest.raises(ValueError, match="validation fingerprint"):
        relief_field_npz_bytes(
            replace(
                field_artifact,
                filtered=altered.filtered_values,
                radii_mm=altered.radii_mm,
            ),
            altered,
            topology,
            validation,
        )
    with pytest.raises(ValueError, match="validation fingerprint"):
        write_relief_preview(
            tmp_path / "stale.png",
            altered,
            topology,
            validation,
            lower_percentile=2,
            upper_percentile=98,
            gamma=0.8,
            filter_fwhm_mm=0.6,
        )
    reversed_faces = replace(geometry, faces=geometry.faces[:, ::-1])
    with pytest.raises(ValueError, match="canonical topology"):
        write_relief_preview(
            tmp_path / "faces.png",
            reversed_faces,
            topology,
            validation,
            lower_percentile=2,
            upper_percentile=98,
            gamma=0.8,
            filter_fwhm_mm=0.6,
        )
    off_ray = geometry.vertices.copy()
    off_ray[10] += np.array([0.001, 0.0, 0.0])
    with pytest.raises(ValueError, match="radial representation"):
        write_relief_preview(
            tmp_path / "vertices.png",
            replace(geometry, vertices=off_ray),
            topology,
            validation,
            lower_percentile=2,
            upper_percentile=98,
            gamma=0.8,
            filter_fwhm_mm=0.6,
        )


def test_preview_uses_fresh_metrics_when_report_scalars_are_stale(
    canonical_fixture, tmp_path, monkeypatch
):
    topology, geometry, validation = canonical_fixture
    stale = replace(validation, minimum_radius_mm=-100.0, maximum_radius_mm=100.0)
    captured_text = []
    import kikuchi_lab.relief.mesh as mesh_module
    from matplotlib.figure import Figure

    original_collection = mesh_module.Poly3DCollection
    original_text = Figure.text

    def one_triangle_collection(triangles, *args, **kwargs):
        return original_collection(triangles[:1], *args, **kwargs)

    def recording_text(figure, x, y, text, *args, **kwargs):
        captured_text.append(text)
        return original_text(figure, x, y, text, *args, **kwargs)

    monkeypatch.setattr(mesh_module, "Poly3DCollection", one_triangle_collection)
    monkeypatch.setattr(Figure, "text", recording_text)
    monkeypatch.setattr(Figure, "savefig", lambda *args, **kwargs: None)
    write_relief_preview(
        tmp_path / "fresh-metrics.png",
        geometry,
        topology,
        stale,
        lower_percentile=2,
        upper_percentile=98,
        gamma=0.8,
        filter_fwhm_mm=0.6,
    )

    observed = validation.maximum_radius_mm - validation.minimum_radius_mm
    assert f"observed relief: {observed:.3f} mm" in captured_text[0]
    assert "observed relief: 200.000 mm" not in captured_text[0]


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("lower_percentile", -1.0),
        ("lower_percentile", True),
        ("upper_percentile", np.inf),
        ("gamma", 0.0),
        ("gamma", np.nan),
        ("gamma", 1.0 + 0.0j),
        ("gamma", "1.0"),
        ("filter_fwhm_mm", 0.0),
    ],
)
def test_preview_rejects_invalid_numeric_parameters(
    canonical_fixture, tmp_path, name, value
):
    topology, geometry, validation = canonical_fixture
    kwargs = dict(
        lower_percentile=2.0,
        upper_percentile=98.0,
        gamma=0.8,
        filter_fwhm_mm=0.6,
    )
    kwargs[name] = value
    with pytest.raises(ValueError, match="preview parameters"):
        write_relief_preview(
            tmp_path / "invalid.png", geometry, topology, validation, **kwargs
        )


@pytest.mark.slow
def test_canonical_preview_is_deterministic_rgba_and_keeps_full_mesh(
    tmp_path: Path, canonical_fixture, monkeypatch
):
    topology, geometry, validation = canonical_fixture
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    captured = []
    import kikuchi_lab.relief.mesh as mesh_module

    original = mesh_module.Poly3DCollection

    def recording_collection(triangles, *args, **kwargs):
        captured.append(len(triangles))
        return original(triangles, *args, **kwargs)

    monkeypatch.setattr(mesh_module, "Poly3DCollection", recording_collection)
    kwargs = dict(
        lower_percentile=2.0,
        upper_percentile=98.0,
        gamma=0.8,
        filter_fwhm_mm=0.6,
    )
    write_relief_preview(first, geometry, topology, validation, **kwargs)
    write_relief_preview(second, geometry, topology, validation, **kwargs)

    assert captured == [len(geometry.faces), len(geometry.faces)]
    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(
        second.read_bytes()
    ).digest()
    image = iio.imread(first)
    assert image.shape == (900, 900, 4)
