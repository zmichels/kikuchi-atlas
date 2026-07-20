from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml

from kikuchi_lab.art_products.orientation_gallery_recipe import (
    OrientationGalleryRecipe,
    OrientationGalleryVariant,
    load_orientation_gallery_recipe,
)


ROOT = Path(__file__).parents[2]
RECIPE = ROOT / "recipes/art/five-phase-standard-orientation-gallery.yml"
SOURCE_SERIES = ROOT / "recipes/art/five-phase-hemisphere-series.yml"
_PHASE_ORDER = ("ice-ih", "forsterite", "quartz", "zircon", "titanite")
_VARIANT_SLUGS = ("azimuthal-60", "tilt-plus-20", "oblique-high")
_VARIANT_ORIENTATIONS = (
    (77.0, 31.0, 43.0),
    (17.0, 51.0, 43.0),
    (97.0, 71.0, 83.0),
)


def _payload() -> dict[str, object]:
    return yaml.safe_load(RECIPE.read_text(encoding="utf-8"))


def _write_recipe(tmp_path: Path, payload: dict[str, object]) -> Path:
    source_path = tmp_path / SOURCE_SERIES.name
    if not source_path.exists():
        source_path.write_text(SOURCE_SERIES.read_text(encoding="utf-8"), encoding="utf-8")
    path = tmp_path / RECIPE.name
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _write_source_series(tmp_path: Path, payload: dict[str, object]) -> None:
    (tmp_path / SOURCE_SERIES.name).write_text(
        yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
    )


def test_tracked_gallery_recipe_is_the_three_orientation_standard_only_policy() -> None:
    recipe = load_orientation_gallery_recipe(RECIPE)

    assert isinstance(recipe, OrientationGalleryRecipe)
    assert recipe.schema_version == 1
    assert recipe.name == "five-phase-standard-orientation-gallery"
    assert recipe.source_series_recipe == "five-phase-hemisphere-series.yml"
    assert recipe.phase_order == _PHASE_ORDER
    assert recipe.source_series.phase_order == _PHASE_ORDER
    assert recipe.treatment.name == "standard"
    assert recipe.treatment.arc_width_scale == 1.0
    assert tuple(variant.slug for variant in recipe.variants) == _VARIANT_SLUGS
    assert all(isinstance(variant, OrientationGalleryVariant) for variant in recipe.variants)
    assert (
        tuple(variant.orientation.euler_bunge_deg for variant in recipe.variants)
        == _VARIANT_ORIENTATIONS
    )
    assert all(variant.orientation.frame == "crystal_to_sample" for variant in recipe.variants)
    assert all(
        variant.orientation != recipe.source_series.orientation for variant in recipe.variants
    )
    assert len({variant.orientation for variant in recipe.variants}) == 3


def test_gallery_recipe_models_are_immutable() -> None:
    recipe = load_orientation_gallery_recipe(RECIPE)

    with pytest.raises(FrozenInstanceError):
        recipe.name = "different-gallery"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        recipe.variants[0].slug = "different-variant"  # type: ignore[misc]


def test_gallery_recipe_rejects_duplicate_variant_slugs(tmp_path: Path) -> None:
    payload = _payload()
    variants = payload["variants"]
    assert isinstance(variants, list)
    assert isinstance(variants[1], dict)
    variants[1]["slug"] = "azimuthal-60"

    with pytest.raises(ValueError, match="variant slugs"):
        load_orientation_gallery_recipe(_write_recipe(tmp_path, payload))


def test_gallery_recipe_rejects_nonfive_source_phase_inventory(tmp_path: Path) -> None:
    payload = _payload()
    source_payload = yaml.safe_load(SOURCE_SERIES.read_text(encoding="utf-8"))
    source_payload["phase_order"] = source_payload["phase_order"][:-1]
    del source_payload["reflector_recipes"]["titanite"]
    _write_source_series(tmp_path, source_payload)

    with pytest.raises(ValueError, match="phase_order"):
        load_orientation_gallery_recipe(_write_recipe(tmp_path, payload))


def test_gallery_recipe_rejects_nonactive_orientation_frame(tmp_path: Path) -> None:
    payload = _payload()
    variants = payload["variants"]
    assert isinstance(variants, list)
    assert isinstance(variants[0], dict)
    orientation = variants[0]["orientation"]
    assert isinstance(orientation, dict)
    orientation["frame"] = "sample_to_crystal"

    with pytest.raises(ValueError, match="frame"):
        load_orientation_gallery_recipe(_write_recipe(tmp_path, payload))


def test_gallery_recipe_requires_the_source_series_reference(tmp_path: Path) -> None:
    payload = _payload()
    del payload["source_series_recipe"]

    with pytest.raises(ValueError, match="fields differ from the schema"):
        load_orientation_gallery_recipe(_write_recipe(tmp_path, payload))


def test_gallery_recipe_rejects_other_source_series_reference(tmp_path: Path) -> None:
    payload = _payload()
    payload["source_series_recipe"] = "missing-series.yml"

    with pytest.raises(ValueError, match="source_series_recipe"):
        load_orientation_gallery_recipe(_write_recipe(tmp_path, payload))


def test_gallery_recipe_rejects_any_inventory_other_than_three_variants(
    tmp_path: Path,
) -> None:
    payload = _payload()
    variants = payload["variants"]
    assert isinstance(variants, list)
    variants.pop()

    with pytest.raises(ValueError, match="three variants"):
        load_orientation_gallery_recipe(_write_recipe(tmp_path, payload))


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("schema_version",), 2, "schema_version"),
        (("name",), "five-phase-gallery", "name"),
        (("treatment",), "wide", "treatment"),
        (("variants", 0, "slug"), "rotation-a", "variant slugs"),
        (("variants", 0, "orientation", "euler_bunge_deg"), [17.0, 31.0, 43.0], "non-identity"),
        (("variants", 1, "orientation", "euler_bunge_deg"), [77.0, 31.0, 43.0], "distinct"),
    ],
)
def test_gallery_recipe_rejects_any_policy_drift(
    tmp_path: Path,
    path: tuple[str | int, ...],
    value: object,
    message: str,
) -> None:
    payload = deepcopy(_payload())
    target: object = payload
    for field in path[:-1]:
        if isinstance(field, str):
            assert isinstance(target, dict)
        else:
            assert isinstance(target, list)
        target = target[field]
    if isinstance(path[-1], str):
        assert isinstance(target, dict)
    else:
        assert isinstance(target, list)
    target[path[-1]] = value

    with pytest.raises(ValueError, match=message):
        load_orientation_gallery_recipe(_write_recipe(tmp_path, payload))


@pytest.mark.parametrize("mutation", ("missing", "unknown"))
def test_gallery_recipe_requires_exact_top_level_schema(
    tmp_path: Path,
    mutation: str,
) -> None:
    payload = _payload()
    if mutation == "missing":
        del payload["treatment"]
    else:
        payload["camera_rotation"] = "forbidden"

    with pytest.raises(ValueError, match="fields differ from the schema"):
        load_orientation_gallery_recipe(_write_recipe(tmp_path, payload))
