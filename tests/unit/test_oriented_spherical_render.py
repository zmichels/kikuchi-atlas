from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from mpl_toolkits.mplot3d.axes3d import Axes3D
from PIL import Image

from kikuchi_lab.model.identity import canonical_json
from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.near_depth.overlap import AxialBandSet
from kikuchi_lab.projection.kikuchipy_adapter import (
    transform_crystal_direction_to_sample,
)
from kikuchi_lab.spherical_intensity.orientation import (
    OrientedProfile,
    load_oriented_spherical_recipe,
)
from kikuchi_lab.spherical_intensity.oriented_render import (
    OrientedSphericalRender,
    _axis_endpoints,
    _presentation_hemisphere,
    render_oriented_spherical,
)
from kikuchi_lab.spherical_intensity.presentation import (
    PresentationSource,
    evaluate_presentation,
)
from kikuchi_lab.spherical_intensity.reprojection import (
    inverse_rotate_directions,
    stereographic_grid,
)


ROOT = Path(__file__).parents[2]
EXPECTED = {
    "identity-vs-oriented-upper.png",
    "oriented-upper.png",
    "oriented-lower.png",
    "oriented-sphere-front.png",
    "oriented-sphere-rear.png",
    "orientation-axes.png",
}
CAMERAS = [
    {"elevation_deg": 20.0, "azimuth_deg": -65.0},
    {"elevation_deg": -20.0, "azimuth_deg": 115.0},
]


@pytest.fixture
def smoke_oriented_recipe():
    return load_oriented_spherical_recipe(
        ROOT / "recipes/spherical/ice-ih-oriented-s2-proof.yml",
        profile="smoke",
    )


@pytest.fixture
def compact_oriented_recipe(smoke_oriented_recipe):
    profile = OrientedProfile(
        name="smoke",
        source_half_size=8,
        figure_size_px=33,
        sphere_longitude_count=17,
        sphere_latitude_count=9,
        tile_rows=7,
        timeout_seconds=10,
    )
    return replace(smoke_oriented_recipe, profile=profile)


@pytest.fixture
def synthetic_presentation_source():
    size = 17
    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float32)
    x, y = np.meshgrid(coordinate, coordinate)
    upper = np.clip(0.25 + 0.25 * x + 0.15 * y, 0.0, 1.0)
    lower = np.flip(upper, axis=(0, 1)).copy()
    grid = stereographic_grid(size, "upper")
    axial = AxialBandSet(
        hkl=np.array([[1, 0, 0]], dtype=np.int32),
        normals=np.array([[1.0, 0.0, 0.0]]),
        theta_radian=np.array([0.1]),
        structure_factor_abs=np.array([1.0]),
    )
    return PresentationSource(
        toned_master=np.stack([upper, lower]),
        axial_bands=axial,
        band_weights=np.array([1.0]),
        overlap_normalization=1.0,
        upper_directions=grid.directions[grid.valid],
        upper_valid=grid.valid,
        gain=0.38,
        ceiling=0.985,
        ledger={
            "scientific_claim": "presentation_only",
            "spatial_filter": "none",
            "center_overlay": False,
            "boundary_overlay": False,
        },
    )


def test_render_has_canonical_inventory_and_final_dimensions(
    synthetic_presentation_source,
    smoke_oriented_recipe,
) -> None:
    render = render_oriented_spherical(
        synthetic_presentation_source,
        smoke_oriented_recipe,
    )

    assert set(render.figures) == EXPECTED
    for name, payload in render.figures.items():
        assert payload.startswith(b"\x89PNG\r\n\x1a\n")
        with Image.open(BytesIO(payload)) as image:
            expected = (960, 480) if name == "identity-vs-oriented-upper.png" else (480, 480)
            assert image.size == expected
            assert image.getbbox() is not None

    assert render.ledger["spatial_filter"] == "none"
    assert render.ledger["center_overlay"] is False
    assert render.ledger["boundary_overlay"] is False


def test_render_bytes_are_deterministic_and_only_axis_figure_is_annotated(
    synthetic_presentation_source,
    compact_oriented_recipe,
) -> None:
    first = render_oriented_spherical(
        synthetic_presentation_source,
        compact_oriented_recipe,
    )
    second = render_oriented_spherical(
        synthetic_presentation_source,
        compact_oriented_recipe,
    )

    assert {
        name: hashlib.sha256(payload).hexdigest() for name, payload in first.figures.items()
    } == {name: hashlib.sha256(payload).hexdigest() for name, payload in second.figures.items()}
    assert first.ledger["center_overlay"] is False
    assert first.ledger["boundary_overlay"] is False
    assert first.ledger["spatial_filter"] == "none"
    assert first.ledger["raster_interpolation"] == "nearest"
    assert first.ledger["image_rotation"] is False
    assert first.ledger["annotated_figures"] == ["orientation-axes.png"]
    assert first.ledger["axis_labels"] == [
        "RD",
        "TD",
        "ND",
        "G_cs[100]",
        "G_cs[010]",
        "G_cs[001]",
    ]


@pytest.mark.parametrize("hemisphere", ["upper", "lower"])
def test_tiled_hemisphere_matches_one_shot_direction_evaluation(
    synthetic_presentation_source,
    compact_oriented_recipe,
    hemisphere,
) -> None:
    size = 31
    actual, valid = _presentation_hemisphere(
        synthetic_presentation_source,
        compact_oriented_recipe.orientation,
        hemisphere=hemisphere,
        size=size,
        tile_rows=4,
        check_deadline=lambda: None,
    )
    grid = stereographic_grid(size, hemisphere)
    expected = np.zeros((size, size), dtype=np.float32)
    crystal = inverse_rotate_directions(
        grid.directions[grid.valid],
        compact_oriented_recipe.orientation,
    )
    expected[grid.valid] = evaluate_presentation(
        synthetic_presentation_source,
        crystal,
    )

    np.testing.assert_array_equal(valid, grid.valid)
    np.testing.assert_allclose(actual[valid], expected[valid], rtol=0.0, atol=1e-7)
    assert np.count_nonzero(actual[~valid]) == 0


def test_hemisphere_allocates_only_bounded_direction_tiles(
    synthetic_presentation_source,
    compact_oriented_recipe,
    monkeypatch,
) -> None:
    import kikuchi_lab.spherical_intensity.oriented_render as subject

    original = subject.stereographic_grid_rows
    observed_shapes: list[tuple[int, int, int]] = []

    def recording_grid(size, hemisphere, row_start, row_stop):
        grid = original(size, hemisphere, row_start, row_stop)
        observed_shapes.append(grid.directions.shape)
        return grid

    monkeypatch.setattr(subject, "stereographic_grid_rows", recording_grid)
    _presentation_hemisphere(
        synthetic_presentation_source,
        compact_oriented_recipe.orientation,
        hemisphere="upper",
        size=33,
        tile_rows=7,
        check_deadline=lambda: None,
    )

    assert observed_shapes
    assert max(shape[0] for shape in observed_shapes) <= 7
    assert all(shape[1:] == (33, 3) for shape in observed_shapes)
    assert (33, 33, 3) not in observed_shapes


def test_identity_source_grid_fast_path_is_exact_and_still_row_tiled(
    synthetic_presentation_source,
    monkeypatch,
) -> None:
    import kikuchi_lab.spherical_intensity.oriented_render as subject

    def fail_if_inverse_rotation_is_used(*args, **kwargs):
        raise AssertionError("identity source-grid fast path inverse-rotated directions")

    monkeypatch.setattr(subject, "inverse_rotate_directions", fail_if_inverse_rotation_is_used)
    calls = 0

    def check() -> None:
        nonlocal calls
        calls += 1

    values, valid = _presentation_hemisphere(
        synthetic_presentation_source,
        Orientation((0.0, 0.0, 0.0)),
        hemisphere="upper",
        size=17,
        tile_rows=5,
        check_deadline=check,
    )
    expected = evaluate_presentation(
        synthetic_presentation_source,
        synthetic_presentation_source.upper_directions,
    )

    np.testing.assert_array_equal(valid, synthetic_presentation_source.upper_valid)
    np.testing.assert_allclose(values[valid], expected, rtol=0.0, atol=1e-7)
    assert calls == math.ceil(17 / 5)


def test_sphere_surface_uses_every_profile_mesh_row_and_column(
    synthetic_presentation_source,
    compact_oriented_recipe,
    monkeypatch,
) -> None:
    calls: list[tuple[tuple[int, int], dict[str, object]]] = []
    original = Axes3D.plot_surface

    def recording_plot_surface(self, x, y, z, *args, **kwargs):
        calls.append((np.asarray(x).shape, dict(kwargs)))
        return original(self, x, y, z, *args, **kwargs)

    monkeypatch.setattr(Axes3D, "plot_surface", recording_plot_surface)
    render = render_oriented_spherical(
        synthetic_presentation_source,
        compact_oriented_recipe,
    )

    expected_shape = (
        compact_oriented_recipe.profile.sphere_latitude_count,
        compact_oriented_recipe.profile.sphere_longitude_count,
    )
    sphere_calls = [call for call in calls if call[0] == expected_shape]
    assert len(sphere_calls) == 2
    for shape, kwargs in sphere_calls:
        assert shape == expected_shape
        assert kwargs["rcount"] == expected_shape[0]
        assert kwargs["ccount"] == expected_shape[1]
        assert kwargs["shade"] is False
        assert kwargs["antialiased"] is False
        assert kwargs["linewidth"] == 0.0
    assert render.ledger["sphere_mesh"] == {
        "latitude_count": expected_shape[0],
        "longitude_count": expected_shape[1],
        "surface_rcount": expected_shape[0],
        "surface_ccount": expected_shape[1],
        "sampling": "full_grid_no_reduction",
    }


def test_sphere_cameras_are_fixed_and_independent_of_orientation(
    synthetic_presentation_source,
    compact_oriented_recipe,
) -> None:
    identity_recipe = replace(
        compact_oriented_recipe,
        orientation=Orientation((0.0, 0.0, 0.0)),
    )

    identity = render_oriented_spherical(synthetic_presentation_source, identity_recipe)
    oriented = render_oriented_spherical(
        synthetic_presentation_source,
        compact_oriented_recipe,
    )

    assert identity.ledger["sphere_cameras"] == CAMERAS
    assert oriented.ledger["sphere_cameras"] == CAMERAS
    assert (
        identity.figures["oriented-sphere-front.png"]
        != oriented.figures["oriented-sphere-front.png"]
    )


def test_axis_diagnostic_endpoints_match_the_public_orientation_adapter(
    compact_oriented_recipe,
) -> None:
    specimen_axes, crystal_axes = _axis_endpoints(compact_oriented_recipe.orientation)

    assert tuple(specimen_axes) == ("RD", "TD", "ND")
    np.testing.assert_array_equal(specimen_axes["RD"], [1.0, 0.0, 0.0])
    np.testing.assert_array_equal(specimen_axes["TD"], [0.0, 1.0, 0.0])
    np.testing.assert_array_equal(specimen_axes["ND"], [0.0, 0.0, 1.0])
    for label, direction in {
        "G_cs[100]": [1.0, 0.0, 0.0],
        "G_cs[010]": [0.0, 1.0, 0.0],
        "G_cs[001]": [0.0, 0.0, 1.0],
    }.items():
        np.testing.assert_allclose(
            crystal_axes[label],
            transform_crystal_direction_to_sample(
                direction,
                compact_oriented_recipe.orientation,
            ),
            rtol=0.0,
            atol=5e-13,
        )


def test_deadline_is_checked_per_tile_and_before_every_render_stage(
    synthetic_presentation_source,
    compact_oriented_recipe,
) -> None:
    calls = 0

    def check() -> None:
        nonlocal calls
        calls += 1

    render_oriented_spherical(
        synthetic_presentation_source,
        compact_oriented_recipe,
        check_deadline=check,
    )

    tile_checks = 3 * math.ceil(
        compact_oriented_recipe.profile.figure_size_px / compact_oriented_recipe.profile.tile_rows
    )
    render_stage_checks = 7  # identity, upper, lower, comparison, two spheres, axes
    assert calls == tile_checks + render_stage_checks


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("spatial_filter", "gaussian"),
        ("center_overlay", True),
        ("boundary_overlay", True),
    ],
)
def test_render_rejects_presentation_sources_with_noncanonical_art_layers(
    synthetic_presentation_source,
    compact_oriented_recipe,
    field,
    value,
) -> None:
    ledger = dict(synthetic_presentation_source.ledger)
    ledger[field] = value
    source = replace(synthetic_presentation_source, ledger=ledger)

    with pytest.raises(ValueError, match="presentation source art contract"):
        render_oriented_spherical(source, compact_oriented_recipe)


def test_render_and_hemisphere_reject_invalid_inputs(
    synthetic_presentation_source,
    compact_oriented_recipe,
) -> None:
    with pytest.raises(TypeError, match="source must be a PresentationSource"):
        render_oriented_spherical(object(), compact_oriented_recipe)
    with pytest.raises(TypeError, match="recipe must be an OrientedSphericalRecipe"):
        render_oriented_spherical(synthetic_presentation_source, object())
    with pytest.raises(TypeError, match="check_deadline must be callable"):
        render_oriented_spherical(
            synthetic_presentation_source,
            compact_oriented_recipe,
            check_deadline=object(),
        )
    for arguments, message in (
        ({"hemisphere": "east", "size": 17, "tile_rows": 5}, "upper or lower"),
        ({"hemisphere": "upper", "size": 1, "tile_rows": 1}, "at least 2"),
        ({"hemisphere": "upper", "size": 17, "tile_rows": 0}, "within the output"),
        ({"hemisphere": "upper", "size": 17, "tile_rows": 18}, "within the output"),
    ):
        with pytest.raises(ValueError, match=message):
            _presentation_hemisphere(
                synthetic_presentation_source,
                compact_oriented_recipe.orientation,
                check_deadline=lambda: None,
                **arguments,
            )


def test_render_payload_validates_inventory_and_owns_immutable_mappings() -> None:
    figures = {name: b"payload" for name in EXPECTED}
    ledger = {"schema_version": 1}
    render = OrientedSphericalRender(figures=figures, ledger=ledger)
    figures["oriented-upper.png"] = b"changed"
    ledger["schema_version"] = 2

    assert render.figures["oriented-upper.png"] == b"payload"
    assert render.ledger["schema_version"] == 1
    with pytest.raises(TypeError):
        render.figures["oriented-upper.png"] = b"changed"
    with pytest.raises(TypeError):
        render.ledger["schema_version"] = 2

    with pytest.raises(ValueError, match="figure inventory is not canonical"):
        OrientedSphericalRender(figures={}, ledger={})
    invalid = dict(figures)
    invalid["oriented-upper.png"] = bytearray(b"payload")
    with pytest.raises(TypeError, match="figure payloads must be bytes"):
        OrientedSphericalRender(figures=invalid, ledger={})


def test_render_payload_deeply_freezes_nested_camera_mappings() -> None:
    figures = {name: b"payload" for name in EXPECTED}
    ledger = {"sphere_cameras": [{"elevation_deg": 20.0, "azimuth_deg": -65.0}]}
    render = OrientedSphericalRender(figures=figures, ledger=ledger)
    ledger["sphere_cameras"][0]["elevation_deg"] = -90.0

    assert render.ledger["sphere_cameras"][0]["elevation_deg"] == 20.0
    with pytest.raises(TypeError):
        render.ledger["sphere_cameras"][0]["elevation_deg"] = -90.0


def test_render_payload_deeply_freezes_annotated_figure_lists() -> None:
    figures = {name: b"payload" for name in EXPECTED}
    ledger = {"annotated_figures": ["orientation-axes.png"]}
    render = OrientedSphericalRender(figures=figures, ledger=ledger)
    ledger["annotated_figures"].append("oriented-upper.png")

    assert render.ledger["annotated_figures"] == ["orientation-axes.png"]
    assert canonical_json(render.ledger) == ('{"annotated_figures":["orientation-axes.png"]}')
    with pytest.raises(AttributeError):
        render.ledger["annotated_figures"].append("oriented-upper.png")
