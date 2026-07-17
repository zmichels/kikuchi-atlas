"""Strict validation and atomic publication for phase hemisphere art bundles."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from kikuchi_lab.model.identity import stable_id

from .catalog_bundle import _validate_catalog_members
from .contracts import ArtBandCatalog, TattooGeometry
from .frozen_selection import FrozenTattooSelection, bind_frozen_tattoo_selection
from .hemisphere_recipe import HemisphereCompositionRecipe, HemisphereTreatment
from .tattoo_bundle import (
    DISCLAIMER_TEXT,
    _ValidatedPayload,
    _gap_diagnostic,
    _geometry_identity,
    _publish_validated_payload,
    _selection_identity,
    _selection_snapshot,
    _sha256_bytes,
    _validate_rendered,
)
from .tattoo_selection import TattooSelection, select_tattoo_paths
from .tattoo_vector import (
    build_tattoo_geometry,
    render_primary_tattoo,
    validate_tattoo_geometry,
)


_AUTHORITATIVE_ICE_FROZEN_MANIFEST_ID = (
    "frozen-tattoo-selection-f0e4f843362bab65"
)


@dataclass(frozen=True)
class PhaseHemisphereBundleResult:
    """Published identity and location for one immutable phase treatment."""

    run_id: str
    path: Path
    phase_slug: str
    treatment: str
    selection_id: str
    geometry_id: str
    manifest_sha256: str


def _render_names(phase_slug: str, treatment: str) -> dict[str, str]:
    prefix = f"{phase_slug}-hemisphere-{treatment}"
    return {
        "primary.svg": f"{prefix}.svg",
        "primary.pdf": f"{prefix}.pdf",
        "mockup.png": f"{prefix}-mockup.png",
        "stencil.png": f"{prefix}-stencil.png",
    }


def _validated_phase_payload(
    *,
    phase_slug: str,
    treatment: HemisphereTreatment,
    catalog: ArtBandCatalog,
    recipe: HemisphereCompositionRecipe,
    selection: TattooSelection,
    geometry: TattooGeometry,
    rendered: Mapping[str, bytes],
    disclaimer: str,
    frozen_manifest: FrozenTattooSelection | None,
) -> _ValidatedPayload:
    expected_types = (
        (treatment, HemisphereTreatment, "treatment"),
        (catalog, ArtBandCatalog, "catalog"),
        (recipe, HemisphereCompositionRecipe, "recipe"),
        (selection, TattooSelection, "selection"),
        (geometry, TattooGeometry, "geometry"),
    )
    for value, expected, name in expected_types:
        if not isinstance(value, expected):
            raise TypeError(f"{name} must be a {expected.__name__}")
    if phase_slug != recipe.phase_slug:
        raise ValueError("phase_slug does not match the composition recipe")
    if phase_slug == "ice-ih" and frozen_manifest is None:
        raise ValueError("Ice Ih requires a frozen selection manifest")
    if phase_slug != "ice-ih" and frozen_manifest is not None:
        raise ValueError("frozen selection manifests are reserved for Ice Ih")
    if frozen_manifest is not None and frozen_manifest.phase_slug != phase_slug:
        raise ValueError("frozen selection phase does not match phase_slug")
    if (
        phase_slug == "ice-ih"
        and frozen_manifest is not None
        and frozen_manifest.manifest_id != _AUTHORITATIVE_ICE_FROZEN_MANIFEST_ID
    ):
        raise ValueError(
            "Ice Ih publication requires the authoritative reviewed manifest"
        )
    if disclaimer != DISCLAIMER_TEXT:
        raise ValueError(
            "tattoo-artist disclaimer is required and must match the approved text"
        )

    if catalog.catalog_id != stable_id("art-band-catalog", catalog.to_dict()):
        raise ValueError("catalog_id does not match catalog content")
    if catalog.eligibility_min_weight != 0.08:
        raise ValueError("hemisphere catalog threshold must be exactly 0.08")
    _validate_catalog_members(catalog)

    if selection.selection_id != _selection_identity(selection):
        raise ValueError("selection_id does not match selection content")
    if selection.catalog_id != catalog.catalog_id:
        raise ValueError("selection catalog_id does not match the catalog")
    if selection.recipe_id != recipe.recipe_id:
        raise ValueError("selection recipe_id does not match the composition recipe")
    if selection.orientation_id != recipe.orientation.orientation_id:
        raise ValueError("selection orientation does not match the composition recipe")
    if len(selection.selected_paths) != 11:
        raise ValueError("hemisphere selection must contain exactly 11 paths")

    if frozen_manifest is None:
        expected_selection = select_tattoo_paths(catalog, recipe)
    else:
        expected_selection = bind_frozen_tattoo_selection(
            catalog,
            recipe,
            frozen_manifest,
        )
    if _selection_snapshot(selection) != _selection_snapshot(expected_selection):
        raise ValueError("selection content does not match strict catalog selection")

    if treatment.name == "standard":
        try:
            build_tattoo_geometry(
                expected_selection,
                recipe,
                width_scale=1.15,
            )
        except ValueError as error:
            raise ValueError(f"wide geometry preflight failed: {error}") from error

    if geometry.boundary.boundary_id != stable_id(
        "tattoo-boundary", geometry.boundary.identity_dict()
    ):
        raise ValueError("boundary_id does not match boundary content")
    if geometry.geometry_id != _geometry_identity(geometry):
        raise ValueError("geometry_id does not match geometry content")
    if geometry.catalog_id != catalog.catalog_id:
        raise ValueError("geometry catalog_id does not match the catalog")
    if geometry.orientation_id != recipe.orientation.orientation_id:
        raise ValueError("geometry orientation does not match the composition recipe")
    validate_tattoo_geometry(geometry)

    expected_geometry = build_tattoo_geometry(
        expected_selection,
        recipe,
        width_scale=treatment.arc_width_scale,
    )
    if geometry.to_dict() != expected_geometry.to_dict():
        raise ValueError("geometry content does not match the treatment recipe")

    rendered_payloads = _validate_rendered(
        rendered,
        render_primary_tattoo(expected_geometry),
        boundary_id=expected_geometry.boundary.boundary_id,
    )
    render_names = _render_names(phase_slug, treatment.name)
    target_rendered = {
        target: rendered_payloads[source]
        for source, target in render_names.items()
    }
    disclaimer_bytes = disclaimer.encode("utf-8")
    diagnostic = _gap_diagnostic(geometry)
    run_identity: dict[str, object] = {
        "schema_version": 1,
        "phase_slug": phase_slug,
        "catalog_id": catalog.catalog_id,
        "recipe_id": recipe.recipe_id,
        "treatment_id": treatment.treatment_id,
        "selection_id": selection.selection_id,
        "geometry_id": geometry.geometry_id,
        "boundary_id": geometry.boundary.boundary_id,
        "treatment": treatment.name,
        "arc_width_scale": treatment.arc_width_scale,
        "diagnostic_id": diagnostic["diagnostic_id"],
        "rendered_sha256": {
            name: _sha256_bytes(payload)
            for name, payload in target_rendered.items()
        },
        "disclaimer_sha256": _sha256_bytes(disclaimer_bytes),
    }
    if frozen_manifest is not None:
        run_identity["frozen_manifest_id"] = frozen_manifest.manifest_id

    files: dict[str, bytes | object] = {
        **target_rendered,
        "hemisphere-composition-recipe.json": {
            "recipe_id": recipe.recipe_id,
            "content": recipe.to_dict(),
        },
        "hemisphere-treatment-recipe.json": {
            "treatment_id": treatment.treatment_id,
            "content": treatment.to_dict(),
        },
        "art-band-catalog.json": {
            "catalog_id": catalog.catalog_id,
            "content": catalog.to_dict(),
        },
    }
    if frozen_manifest is not None:
        files["frozen-selection-manifest.json"] = {
            "manifest_id": frozen_manifest.manifest_id,
            "content": frozen_manifest.to_dict(),
        }
    files.update(
        {
            "band-selection-ledger.json": _selection_snapshot(selection),
            "path-geometry.json": {
                "geometry_id": geometry.geometry_id,
                "content": geometry.to_dict(),
            },
            "stroke-gap-diagnostic.json": diagnostic,
            "tattoo-artist-review.txt": disclaimer_bytes,
        }
    )
    return _ValidatedPayload(
        run_identity=run_identity,
        files=files,
        payload_order=tuple(files),
    )


def write_phase_hemisphere_bundle(
    output_root: str | Path,
    *,
    phase_slug: str,
    treatment: HemisphereTreatment,
    catalog: ArtBandCatalog,
    recipe: HemisphereCompositionRecipe,
    selection: TattooSelection,
    geometry: TattooGeometry,
    rendered: Mapping[str, bytes],
    disclaimer: str,
    frozen_manifest: FrozenTattooSelection | None = None,
) -> PhaseHemisphereBundleResult:
    """Preflight and atomically publish one phase/treatment hemisphere bundle."""
    payload = _validated_phase_payload(
        phase_slug=phase_slug,
        treatment=treatment,
        catalog=catalog,
        recipe=recipe,
        selection=selection,
        geometry=geometry,
        rendered=rendered,
        disclaimer=disclaimer,
        frozen_manifest=frozen_manifest,
    )
    run_id = stable_id(
        f"{phase_slug}-hemisphere-{treatment.name}-run",
        payload.run_identity,
    )
    path, manifest_sha256 = _publish_validated_payload(
        output_root,
        run_id=run_id,
        payload=payload,
    )
    return PhaseHemisphereBundleResult(
        run_id=run_id,
        path=path,
        phase_slug=phase_slug,
        treatment=treatment.name,
        selection_id=selection.selection_id,
        geometry_id=geometry.geometry_id,
        manifest_sha256=manifest_sha256,
    )


__all__ = ["PhaseHemisphereBundleResult", "write_phase_hemisphere_bundle"]
