"""Bounded real-Ice workflow for the shared science-art band catalog."""

from __future__ import annotations

import re
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

from kikuchi_lab.art_products.catalog import build_art_band_catalog
from kikuchi_lab.art_products.catalog_bundle import (
    IceArtCatalogRecipe,
    write_art_catalog_bundle,
)
from kikuchi_lab.kinematical.kikuchipy_adapter import simulate_kinematical_arrays
from kikuchi_lab.kinematical.recipe import load_kinematical_recipe
from kikuchi_lab.near_depth.recipe import load_near_depth_recipe
from kikuchi_lab.sources.structure import load_structure_record, verify_structure
from kikuchi_lab.spherical_intensity.presentation import build_presentation_source

from .oriented_spherical import _materialize_source_recipes
from kikuchi_lab.spherical_intensity.orientation import load_oriented_spherical_recipe


_RECIPE_FIELDS = {
    "schema_version",
    "name",
    "source_oriented_recipe",
    "eligibility_min_weight",
    "globe_cohort_count",
    "tie_policy",
    "ranking",
    "scientific_claim",
    "product_class",
}
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


class IceArtCatalogTimeoutError(RuntimeError):
    """Raised when the bounded Ice catalog exceeds its smoke deadline."""


@dataclass(frozen=True)
class IceArtCatalogResult:
    """Published result from one bounded real-Ice catalog build."""

    run_id: str
    path: Path
    catalog_id: str
    member_count: int
    manifest_sha256: str


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != _RECIPE_FIELDS:
        raise ValueError("catalog recipe fields differ from the supported schema")
    return value


def _relative_path(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or Path(value).is_absolute()
        or _WINDOWS_ABSOLUTE_PATH.match(value)
        or value.startswith("\\\\")
    ):
        raise ValueError("catalog recipe source_oriented_recipe must be a relative path")
    return value


def load_ice_art_catalog_recipe(path: str | Path) -> IceArtCatalogRecipe:
    """Load the strict, versioned shared-Ice catalog recipe."""
    try:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ValueError("catalog recipe YAML is invalid") from None
    root = _mapping(payload)
    name = root["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("catalog recipe name must be non-empty text")
    return IceArtCatalogRecipe(
        schema_version=root["schema_version"],
        name=name,
        source_oriented_recipe=_relative_path(root["source_oriented_recipe"]),
        eligibility_min_weight=root["eligibility_min_weight"],
        globe_cohort_count=root["globe_cohort_count"],
        tie_policy=root["tie_policy"],
        ranking=root["ranking"],
        scientific_claim=root["scientific_claim"],
        product_class=root["product_class"],
    )


def _deadline(started: float, timeout_seconds: int) -> Callable[[], None]:
    def check() -> None:
        elapsed = time.monotonic() - started
        if elapsed > timeout_seconds:
            raise IceArtCatalogTimeoutError(
                f"Ice art catalog smoke exceeded {timeout_seconds} seconds"
            )

    return check


def _log_stage(
    *,
    started: float,
    stage: str,
    event: str,
    check_deadline: Callable[[], None],
) -> None:
    check_deadline()
    print(
        "ice-art-catalog "
        f"stage={stage} event={event} profile=smoke "
        f"elapsed_seconds={time.monotonic() - started:.6f}",
        file=sys.stderr,
        flush=True,
    )


def build_ice_art_catalog(
    *,
    recipe_path: str | Path,
    output_root: str | Path,
) -> IceArtCatalogResult:
    """Build the smoke-bounded Ice presentation once and publish its catalog."""
    started = time.monotonic()
    recipe_file = Path(recipe_path).resolve()
    catalog_recipe = load_ice_art_catalog_recipe(recipe_file)
    oriented_path = (
        recipe_file.parent / catalog_recipe.source_oriented_recipe
    ).resolve()
    oriented_recipe = load_oriented_spherical_recipe(oriented_path, profile="smoke")
    spherical_recipe, simulation_recipe, _, source_recipe_path = (
        _materialize_source_recipes(oriented_path, oriented_recipe)
    )
    source_recipe = load_kinematical_recipe(source_recipe_path)
    presentation_path = (
        oriented_path.parent / oriented_recipe.presentation_recipe
    ).resolve()
    presentation_recipe = load_near_depth_recipe(presentation_path)
    if (
        presentation_recipe.expected_kinematical_recipe_id
        != source_recipe.recipe_id
    ):
        raise ValueError(
            "presentation recipe does not identify the tracked Ice base recipe"
        )
    presentation_source_path = (
        presentation_path.parent / presentation_recipe.source_kinematical_recipe
    ).resolve()
    if presentation_source_path != source_recipe_path:
        raise ValueError(
            "presentation recipe does not resolve to the tracked Ice base recipe"
        )
    source_path = (source_recipe_path.parent / source_recipe.source_record).resolve()
    source = load_structure_record(source_path)
    verify_structure(source)

    check = _deadline(started, oriented_recipe.profile.timeout_seconds)
    print(
        "ice-art-catalog finite-work "
        "profile=smoke "
        f"source_half_size={oriented_recipe.profile.source_half_size} "
        f"timeout_seconds={oriented_recipe.profile.timeout_seconds} "
        "simulation_count=1",
        file=sys.stderr,
        flush=True,
    )
    _log_stage(
        started=started,
        stage="simulation",
        event="start",
        check_deadline=check,
    )
    simulation, context = simulate_kinematical_arrays(source, simulation_recipe)
    _log_stage(
        started=started,
        stage="simulation",
        event="finish",
        check_deadline=check,
    )

    _log_stage(
        started=started,
        stage="presentation",
        event="start",
        check_deadline=check,
    )
    presentation = build_presentation_source(
        simulation.master_stereographic.intensity,
        context.master_simulator.reflectors,
        simulation_recipe,
        presentation_recipe,
    )
    _log_stage(
        started=started,
        stage="presentation",
        event="finish",
        check_deadline=check,
    )

    _log_stage(
        started=started,
        stage="catalog",
        event="start",
        check_deadline=check,
    )
    catalog = build_art_band_catalog(
        presentation,
        source_structure_id=source.identifier,
        source_structure_sha256=source.sha256,
        source_recipe_id=source_recipe.recipe_id,
        presentation_recipe_id=presentation_recipe.recipe_id,
        eligibility_min_weight=catalog_recipe.eligibility_min_weight,
    )
    _log_stage(
        started=started,
        stage="catalog",
        event="finish",
        check_deadline=check,
    )

    _log_stage(
        started=started,
        stage="publication",
        event="start",
        check_deadline=check,
    )
    bundle = write_art_catalog_bundle(
        output_root,
        catalog=catalog,
        catalog_recipe=catalog_recipe,
        oriented_recipe=oriented_recipe,
        spherical_recipe=spherical_recipe,
        source_recipe=source_recipe,
        presentation_recipe=presentation_recipe,
        source=source,
    )
    _log_stage(
        started=started,
        stage="publication",
        event="finish",
        check_deadline=check,
    )
    return IceArtCatalogResult(
        run_id=bundle.run_id,
        path=bundle.path,
        catalog_id=catalog.catalog_id,
        member_count=len(catalog.members),
        manifest_sha256=bundle.manifest_sha256,
    )


__all__ = [
    "IceArtCatalogRecipe",
    "IceArtCatalogResult",
    "IceArtCatalogTimeoutError",
    "build_ice_art_catalog",
    "load_ice_art_catalog_recipe",
]
