from dataclasses import FrozenInstanceError
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pytest
import yaml
from orix.quaternion import Rotation as OrixRotation

from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.projection.kikuchipy_adapter import (
    transform_crystal_direction_to_sample,
)
from kikuchi_lab.spherical_intensity.orientation import (
    load_oriented_spherical_recipe,
    orientation_ledger,
    orientation_matrix,
)
from kikuchi_lab.spherical_intensity.recipe import load_spherical_intensity_recipe


ROOT = Path(__file__).parents[2]
RECIPE = ROOT / "recipes" / "spherical" / "ice-ih-oriented-s2-proof.yml"
FIELD_RECIPE = ROOT / "recipes" / "spherical" / "ice-ih-s2-intensity.yml"
ORIENTATION = Orientation((17.0, 31.0, 43.0), frame="crystal_to_sample")


def _recipe_payload() -> dict[str, object]:
    payload = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _mapping(payload: dict[str, object], name: str) -> dict[str, object]:
    value = payload[name]
    assert isinstance(value, dict)
    return value


def _set_path(
    payload: dict[str, object], path: tuple[str, ...], value: object
) -> None:
    target = payload
    for name in path[:-1]:
        target = _mapping(target, name)
    target[path[-1]] = value


def _write_recipe(tmp_path: Path, payload: dict[str, object]) -> Path:
    candidate = tmp_path / "candidate.yml"
    candidate.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return candidate


def test_oriented_ice_recipe_has_approved_orientation_and_profiles() -> None:
    smoke = load_oriented_spherical_recipe(RECIPE, profile="smoke")
    review = load_oriented_spherical_recipe(RECIPE, profile="review")

    assert smoke.orientation.euler_bunge_deg == (17.0, 31.0, 43.0)
    assert smoke.orientation.frame == "crystal_to_sample"
    assert (
        smoke.profile.source_half_size,
        smoke.profile.figure_size_px,
        smoke.profile.timeout_seconds,
    ) == (32, 480, 180)
    assert (
        review.profile.source_half_size,
        review.profile.figure_size_px,
        review.profile.timeout_seconds,
    ) == (512, 2400, 600)
    assert review.interpolation == "bilinear"
    assert review.spatial_filter == "none"
    assert review.background_color == "#101519"


def test_oriented_recipe_contract_is_immutable_and_content_identified() -> None:
    recipe = load_oriented_spherical_recipe(RECIPE, profile="review")

    assert recipe.recipe_id == stable_id("recipe", recipe.to_dict())
    assert recipe.profile.to_dict() == {
        "name": "review",
        "source_half_size": 512,
        "figure_size_px": 2400,
        "sphere_longitude_count": 721,
        "sphere_latitude_count": 361,
        "tile_rows": 48,
        "timeout_seconds": 600,
    }
    with pytest.raises(FrozenInstanceError):
        recipe.interpolation = "nearest"


def test_ice_field_recipe_has_approved_bounded_profiles() -> None:
    smoke = load_spherical_intensity_recipe(FIELD_RECIPE, profile="smoke")
    acceptance = load_spherical_intensity_recipe(FIELD_RECIPE, profile="acceptance")

    assert (
        smoke.profile.half_size,
        smoke.profile.point_count,
        smoke.profile.timeout_seconds,
    ) == (32, 10_000, 180)
    assert (
        acceptance.profile.half_size,
        acceptance.profile.point_count,
        acceptance.profile.timeout_seconds,
    ) == (128, 100_000, 600)
    assert acceptance.source_kinematical_recipe == (
        "../kinematical/ice-ih-oxygen-quiet-proof.yml"
    )
    assert acceptance.rng_seed == 20260716
    assert acceptance.emit_axial is False


@pytest.mark.parametrize(
    "path",
    [(), ("profiles",), ("profiles", "smoke"), ("orientation",)],
)
def test_oriented_recipe_rejects_unknown_fields(
    tmp_path: Path, path: tuple[str, ...]
) -> None:
    payload = _recipe_payload()
    target = payload
    for name in path:
        target = _mapping(target, name)
    target["unknown"] = "unsupported"

    with pytest.raises(ValueError, match="fields differ"):
        load_oriented_spherical_recipe(_write_recipe(tmp_path, payload), profile="smoke")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("interpolation", "nearest", "interpolation must be bilinear"),
        ("spatial_filter", "gaussian", "spatial_filter must be none"),
        ("background_color", "#000000", "background_color must be #101519"),
    ],
)
def test_oriented_recipe_rejects_noncanonical_display_operations(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    payload = _recipe_payload()
    payload[field] = value

    with pytest.raises(ValueError, match=message):
        load_oriented_spherical_recipe(_write_recipe(tmp_path, payload), profile="smoke")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_spherical_recipe", "/tmp/ice.yml"),
        ("source_spherical_recipe", r"C:\\proofs\\ice.yml"),
        ("presentation_recipe", "/tmp/presentation.yml"),
    ],
)
def test_oriented_recipe_rejects_absolute_referenced_paths(
    tmp_path: Path, field: str, value: str
) -> None:
    payload = _recipe_payload()
    payload[field] = value

    with pytest.raises(ValueError, match="relative path"):
        load_oriented_spherical_recipe(_write_recipe(tmp_path, payload), profile="smoke")


def test_oriented_recipe_rejects_unc_referenced_path(tmp_path: Path) -> None:
    payload = _recipe_payload()
    payload["source_spherical_recipe"] = r"\\server\share\ice.yml"

    with pytest.raises(ValueError, match="relative path"):
        load_oriented_spherical_recipe(_write_recipe(tmp_path, payload), profile="smoke")


@pytest.mark.parametrize(
    "field",
    [
        "source_half_size",
        "figure_size_px",
        "sphere_longitude_count",
        "sphere_latitude_count",
        "tile_rows",
        "timeout_seconds",
    ],
)
def test_oriented_recipe_rejects_boolean_profile_numbers(
    tmp_path: Path, field: str
) -> None:
    payload = _recipe_payload()
    _set_path(payload, ("profiles", "smoke", field), True)

    with pytest.raises(ValueError, match="positive integer|approved proof"):
        load_oriented_spherical_recipe(_write_recipe(tmp_path, payload), profile="smoke")


def test_oriented_recipe_validates_unselected_profile_values(tmp_path: Path) -> None:
    payload = _recipe_payload()
    _set_path(payload, ("profiles", "review", "sphere_longitude_count"), 720)

    with pytest.raises(ValueError, match="sphere grid counts must be odd"):
        load_oriented_spherical_recipe(_write_recipe(tmp_path, payload), profile="smoke")


def test_oriented_recipe_rejects_boolean_euler_angle(tmp_path: Path) -> None:
    payload = _recipe_payload()
    orientation = _mapping(payload, "orientation")
    orientation["euler_bunge_deg"] = [True, 31.0, 43.0]

    with pytest.raises(ValueError, match="Euler angles must be three finite numbers"):
        load_oriented_spherical_recipe(_write_recipe(tmp_path, payload), profile="smoke")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_oriented_recipe_rejects_nonfinite_euler_angles(
    tmp_path: Path, value: float
) -> None:
    payload = _recipe_payload()
    orientation = _mapping(payload, "orientation")
    orientation["euler_bunge_deg"] = [17.0, value, 43.0]

    with pytest.raises(ValueError, match="Euler angle must be finite"):
        load_oriented_spherical_recipe(_write_recipe(tmp_path, payload), profile="smoke")


def test_oriented_recipe_rejects_unknown_profile_name() -> None:
    with pytest.raises(ValueError, match="profile must be smoke or review"):
        load_oriented_spherical_recipe(RECIPE, profile="acceptance")  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["sphere_longitude_count", "sphere_latitude_count"])
def test_oriented_recipe_rejects_even_sphere_grid_counts(
    tmp_path: Path, field: str
) -> None:
    payload = _recipe_payload()
    _set_path(payload, ("profiles", "smoke", field), 180)

    with pytest.raises(ValueError, match="sphere grid counts must be odd"):
        load_oriented_spherical_recipe(_write_recipe(tmp_path, payload), profile="smoke")


def test_oriented_recipe_rejects_tile_rows_larger_than_figure(tmp_path: Path) -> None:
    payload = _recipe_payload()
    _set_path(payload, ("profiles", "smoke", "tile_rows"), 481)

    with pytest.raises(ValueError, match="tile_rows cannot exceed figure_size_px"):
        load_oriented_spherical_recipe(_write_recipe(tmp_path, payload), profile="smoke")


@pytest.mark.parametrize(
    ("profile", "field", "value"),
    [
        ("smoke", "source_half_size", 64),
        ("smoke", "figure_size_px", 960),
        ("smoke", "timeout_seconds", 181),
        ("review", "source_half_size", 256),
        ("review", "figure_size_px", 1200),
        ("review", "timeout_seconds", 601),
    ],
)
def test_oriented_recipe_rejects_unapproved_size_and_time_bounds(
    tmp_path: Path, profile: str, field: str, value: int
) -> None:
    payload = _recipe_payload()
    _set_path(payload, ("profiles", profile, field), value)

    with pytest.raises(ValueError, match=f"{profile} size/time bounds differ"):
        load_oriented_spherical_recipe(
            _write_recipe(tmp_path, payload),
            profile=profile,  # type: ignore[arg-type]
        )


def test_orientation_matrix_columns_match_adapter_basis_transforms() -> None:
    matrix = orientation_matrix(ORIENTATION)

    for column, basis in enumerate(np.eye(3, dtype=np.float64)):
        expected = transform_crystal_direction_to_sample(basis, ORIENTATION)
        np.testing.assert_allclose(matrix[:, column], expected, rtol=0.0, atol=5e-13)


def test_orientation_matrix_is_right_handed_and_orthonormal() -> None:
    matrix = orientation_matrix(ORIENTATION)

    np.testing.assert_allclose(matrix.T @ matrix, np.eye(3), rtol=0.0, atol=5e-13)
    assert np.linalg.det(matrix) == pytest.approx(1.0, rel=0.0, abs=5e-13)


def test_orientation_ledger_records_forward_and_inverse_frame_contract() -> None:
    matrix = orientation_matrix(ORIENTATION)
    ledger = orientation_ledger(ORIENTATION)

    assert ledger["direction"] == "active crystal_to_sample"
    assert ledger["equation_forward"] == "s = G_cs c"
    assert ledger["equation_pullback"] == "I_sample(s) = I_crystal(G_cs^-1 s)"
    assert ledger["output_frame"] == "EDAX-TSL:RD-TD-ND"
    assert ledger["output_axis_order"] == ["RD", "TD", "ND"]
    np.testing.assert_allclose(ledger["matrix_G_cs"], matrix, rtol=0.0, atol=0.0)
    np.testing.assert_allclose(
        ledger["matrix_G_cs_inverse"], matrix.T, rtol=0.0, atol=0.0
    )


def test_orientation_ledger_records_stable_identity_and_versions() -> None:
    ledger = orientation_ledger(ORIENTATION)
    expected_rotation = OrixRotation.from_euler(
        ORIENTATION.euler_bunge_deg,
        degrees=True,
        direction="crystal2lab",
    )

    assert ORIENTATION.orientation_id == stable_id("orientation", ORIENTATION.to_dict())
    assert ledger["orientation_id"] == ORIENTATION.orientation_id
    assert ledger["quaternion_component_order"] == ["a", "b", "c", "d"]
    np.testing.assert_allclose(
        ledger["quaternion_abcd"], expected_rotation.data[0], rtol=0.0, atol=0.0
    )
    assert ledger["implementation_versions"] == {
        "kikuchi-lab": version("kikuchi-lab"),
        "orix": version("orix"),
    }
