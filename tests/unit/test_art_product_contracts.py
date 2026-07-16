from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

from kikuchi_lab.art_products import (
    ArtBandCatalog,
    ArtBandMember,
    TattooBoundary,
    TattooGeometry,
    TattooPath,
)
from kikuchi_lab.model.identity import stable_id


def _member(**overrides: object) -> ArtBandMember:
    values: dict[str, object] = {
        "hkl": (1, 0, 2),
        "normal_crystal": (0.0, 0.6, 0.8),
        "bragg_half_width_rad": 0.012,
        "structure_factor_magnitude": 18.5,
        "normalized_weight": 0.75,
        "globe_cohort": 3,
        "globe_eligible": True,
        "tattoo_eligible": True,
        "acceptance_state": "unreviewed",
        "acceptance_reason": "automatic catalog candidate",
    }
    values.update(overrides)
    return ArtBandMember(**values)


def _catalog(*members: ArtBandMember) -> ArtBandCatalog:
    return ArtBandCatalog(
        schema_version=1,
        source_structure_id="structure-ice-ih",
        source_structure_sha256="a" * 64,
        source_recipe_id="recipe-source-0123456789abcdef",
        presentation_recipe_id="recipe-presentation-0123456789abcdef",
        eligibility_min_weight=0.10,
        members=members or (_member(),),
    )


def _path(**overrides: object) -> TattooPath:
    values: dict[str, object] = {
        "member_id": _member().member_id,
        "tier": "dominant",
        "width_mm": 4.8,
        "points_mm": np.array([[-40.0, -20.0], [0.0, 8.0], [42.0, 25.0]]),
        "score_components": {
            "strength": 0.75,
            "angular_width": 0.4,
            "nonredundancy": 1.0,
            "coverage": 0.8,
            "zone_relationship": 0.5,
        },
        "selection_reason": "highest ranked nonredundant center trace",
    }
    values.update(overrides)
    return TattooPath(**values)


def _geometry(
    *paths: TattooPath,
    boundary: TattooBoundary | None = None,
) -> TattooGeometry:
    values: dict[str, object] = {
        "schema_version": 1,
        "catalog_id": "art-band-catalog-0123456789abcdef",
        "orientation_id": "orientation-0123456789abcdef",
        "artboard_size_mm": 145.0,
        "boundary": boundary or _boundary(),
        "paths": paths or (_path(),),
        "projection": "upper_specimen_stereographic_center_trace",
    }
    return TattooGeometry(**values)


def _boundary(**changes: object) -> TattooBoundary:
    values = {
        "schema_version": 1,
        "role": "stereographic_hemisphere_boundary",
        "scientific_claim": "noncrystallographic_projection_primitive",
        "center_mm": (72.5, 72.5),
        "outer_diameter_mm": 132.0,
        "width_mm": 2.2,
        "ink": "#000000",
    }
    values.update(changes)
    return TattooBoundary(**values)


def test_art_band_member_is_frozen_owned_and_intrinsically_identified() -> None:
    normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    member = _member(normal_crystal=normal)

    normal[:] = (1.0, 0.0, 0.0)
    assert member.normal_crystal.dtype == np.dtype("<f8")
    assert np.array_equal(member.normal_crystal, [0.0, 0.0, 1.0])
    assert not member.normal_crystal.flags.writeable
    with pytest.raises(ValueError):
        member.normal_crystal[0] = 1.0
    with pytest.raises(FrozenInstanceError):
        member.globe_cohort = 4

    policy_change = replace(
        member,
        globe_cohort=1,
        globe_eligible=False,
        tattoo_eligible=False,
        acceptance_state="rejected",
        acceptance_reason="composition review",
    )
    assert policy_change.member_id == member.member_id


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("hkl", (0, 0, 0), "hkl"),
        ("hkl", (1.0, 0, 2), "hkl"),
        ("hkl", (True, 0, 2), "hkl"),
        ("normal_crystal", (0.0, 0.0, 0.999999999999), "unit"),
        ("bragg_half_width_rad", 0.0, "positive and finite"),
        ("bragg_half_width_rad", float("nan"), "positive and finite"),
        ("structure_factor_magnitude", -1.0, "positive and finite"),
        ("structure_factor_magnitude", float("inf"), "positive and finite"),
        ("normalized_weight", 0.0, r"\(0, 1\]"),
        ("normalized_weight", 1.01, r"\(0, 1\]"),
        ("globe_cohort", 0, "1, 2, 3, 4, or None"),
        ("globe_cohort", True, "1, 2, 3, 4, or None"),
        ("globe_eligible", 1, "boolean"),
        ("acceptance_state", "approved", "acceptance_state"),
        ("acceptance_reason", "", "acceptance_reason"),
    ],
)
def test_art_band_member_rejects_invalid_values(
    field: str, value: object, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _member(**{field: value})


def test_catalog_has_complete_policy_identity_and_unique_members() -> None:
    member = _member()
    changed_policy = replace(member, globe_cohort=4)

    assert member.member_id == changed_policy.member_id
    assert _catalog(member).catalog_id != _catalog(changed_policy).catalog_id
    with pytest.raises(ValueError, match="member_id values must be unique"):
        _catalog(member, changed_policy)


def test_catalog_identity_is_independent_of_filesystem_location(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()

    monkeypatch.chdir(first_root)
    first = _catalog()
    monkeypatch.chdir(second_root)
    second = _catalog()

    assert first.catalog_id == second.catalog_id
    assert first.to_dict() == second.to_dict()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", True, "schema_version"),
        ("schema_version", 2, "schema_version"),
        ("source_structure_sha256", "A" * 64, "lowercase SHA-256"),
        ("source_structure_sha256", "a" * 63, "lowercase SHA-256"),
        ("eligibility_min_weight", 0.0, r"\(0, 1\]"),
        ("eligibility_min_weight", 1.01, r"\(0, 1\]"),
        ("members", (), "non-empty"),
    ],
)
def test_catalog_rejects_invalid_values(
    field: str, value: object, message: str
) -> None:
    values: dict[str, object] = {
        "schema_version": 1,
        "source_structure_id": "structure-ice-ih",
        "source_structure_sha256": "a" * 64,
        "source_recipe_id": "recipe-source-0123456789abcdef",
        "presentation_recipe_id": "recipe-presentation-0123456789abcdef",
        "eligibility_min_weight": 0.10,
        "members": (_member(),),
    }
    values[field] = value
    with pytest.raises(ValueError, match=message):
        ArtBandCatalog(**values)


def test_tattoo_path_owns_read_only_little_endian_points() -> None:
    points = np.array([[-10.0, -5.0], [10.0, 5.0]], dtype=np.float32)
    scores = {"strength": 0.8}
    path = _path(points_mm=points, score_components=scores)

    points[:] = 0.0
    scores["strength"] = 0.0
    assert path.points_mm.dtype == np.dtype("<f8")
    assert np.array_equal(path.points_mm, [[-10.0, -5.0], [10.0, 5.0]])
    assert path.score_components == {"strength": 0.8}
    assert not path.points_mm.flags.writeable
    with pytest.raises(ValueError):
        path.points_mm[0, 0] = 2.0
    with pytest.raises(TypeError):
        path.score_components["strength"] = 0.2
    with pytest.raises(FrozenInstanceError):
        path.width_mm = 4.2
    assert len(path.points_sha256) == 64
    assert path.points_sha256 == path.points_sha256.lower()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("tier", "structural", "tier"),
        ("width_mm", 0.0, "positive and finite"),
        ("width_mm", float("inf"), "positive and finite"),
        ("points_mm", [[0.0, 0.0]], r"shape \(N, 2\) with N >= 2"),
        ("points_mm", [[0.0, 0.0], [1.0, 2.0, 3.0]], r"shape \(N, 2\)"),
        ("points_mm", [[0.0, 0.0], [float("nan"), 1.0]], "finite"),
        ("score_components", {}, "non-empty"),
        ("score_components", {"strength": float("nan")}, "finite"),
        ("selection_reason", "", "selection_reason"),
    ],
)
def test_tattoo_path_rejects_invalid_values(
    field: str, value: object, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _path(**{field: value})


def test_projection_boundary_is_frozen_separate_evidence() -> None:
    boundary = _boundary()
    assert boundary.to_dict()["scientific_claim"] == (
        "noncrystallographic_projection_primitive"
    )
    assert boundary.to_dict()["center_mm"] == [72.5, 72.5]
    assert boundary.boundary_id.startswith("tattoo-boundary-")
    with pytest.raises(FrozenInstanceError):
        boundary.width_mm = 3.0


def test_projection_boundary_identity_includes_every_physical_field() -> None:
    original = _boundary()
    for field, value in (
        ("center_mm", [72.4, 72.5]),
        ("outer_diameter_mm", 131.9),
        ("width_mm", 2.1),
        ("scientific_claim", "forged-reflector"),
    ):
        changed = original.identity_dict()
        changed[field] = value
        assert stable_id("tattoo-boundary", changed) != original.boundary_id


def test_tattoo_geometry_identity_includes_coordinate_hashes_and_widths() -> None:
    path = _path()
    moved_points = path.points_mm.copy()
    moved_points[1, 0] += 0.01
    moved = _path(points_mm=moved_points)
    resized = _path(width_mm=4.81)

    original = _geometry(path)
    assert _geometry(moved).geometry_id != original.geometry_id
    assert _geometry(resized).geometry_id != original.geometry_id
    assert original.to_dict()["paths"][0]["points_sha256"] == path.points_sha256


def test_geometry_identity_includes_separate_projection_boundary() -> None:
    boundary = _boundary()
    original = _geometry(_path(), boundary=boundary)
    original_id = boundary.boundary_id
    object.__setattr__(boundary, "boundary_id", "tattoo-boundary-forged")
    try:
        changed = replace(original, boundary=boundary)
        assert changed.geometry_id != original.geometry_id
        assert len(changed.paths) == 1
    finally:
        object.__setattr__(boundary, "boundary_id", original_id)


def test_tattoo_geometry_requires_fixed_projection_and_unique_ids() -> None:
    path = _path()
    with pytest.raises(ValueError, match="projection"):
        replace(_geometry(path), projection="lower_specimen_stereographic_center_trace")
    with pytest.raises(ValueError, match="path_id values must be unique"):
        _geometry(path, path)

    alternate = _path(points_mm=[[-30.0, -10.0], [30.0, 10.0]])
    assert alternate.path_id != path.path_id
    with pytest.raises(ValueError, match="member_id values must be unique"):
        _geometry(path, alternate)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", 2, "schema_version"),
        ("artboard_size_mm", 0.0, "positive and finite"),
        ("artboard_size_mm", float("nan"), "positive and finite"),
        ("paths", (), "non-empty"),
    ],
)
def test_tattoo_geometry_rejects_invalid_values(
    field: str, value: object, message: str
) -> None:
    values: dict[str, object] = {
        "schema_version": 1,
        "catalog_id": "art-band-catalog-0123456789abcdef",
        "orientation_id": "orientation-0123456789abcdef",
        "artboard_size_mm": 145.0,
        "boundary": _boundary(),
        "paths": (_path(),),
        "projection": "upper_specimen_stereographic_center_trace",
    }
    values[field] = value
    with pytest.raises(ValueError, match=message):
        TattooGeometry(**values)
