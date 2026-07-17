from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.art_products.catalog import _assign_cohorts
from kikuchi_lab.art_products.contracts import ArtBandCatalog, ArtBandMember
from kikuchi_lab.art_products.frozen_selection import (
    FrozenTattooPath,
    FrozenTattooSelection,
    bind_frozen_tattoo_selection,
)
from kikuchi_lab.art_products.hemisphere_recipe import (
    HemisphereCompositionRecipe,
    load_hemisphere_series_recipe,
)
from kikuchi_lab.art_products.tattoo_bundle import DISCLAIMER_TEXT
from kikuchi_lab.art_products.tattoo_selection import select_tattoo_paths
from kikuchi_lab.art_products.tattoo_vector import (
    build_tattoo_geometry,
    render_primary_tattoo,
)
from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.spherical_intensity.orientation import orientation_matrix


ROOT = Path(__file__).parents[2]
SERIES_RECIPE = ROOT / "recipes/art/five-phase-hemisphere-series.yml"
REVIEWED_ICE_SELECTION = ROOT / "recipes/art/ice-ih-reviewed-selection-v2.yml"
_STANDARD_ONLY_NORMALS = (
    (-0.8822169081200177, -0.43103320931943057, -0.18948271554669166),
    (-0.62261489607248, 0.6690776619956004, 0.4058149497088),
    (0.9204908526156985, 0.05873943120316735, 0.3863240472359349),
    (0.4848802958627257, -0.18096250938890962, 0.8556539422451955),
    (0.993271722413054, -0.08377357504342017, -0.07995794881717146),
    (0.8771583840922845, -0.40445184342530893, 0.2588665207524556),
    (-0.12602100248886397, -0.9601184193002196, 0.24958230676902862),
    (-0.1299378153244877, 0.5871568419644989, -0.7989762243540016),
    (0.24996756165060066, 0.5609960779570153, 0.7891765446586078),
    (0.56068800227223, -0.7419035220378951, 0.36770657880399993),
    (-0.5339669307007249, 0.8445494552607576, -0.04019371265266115),
)


def _catalog() -> ArtBandCatalog:
    recipe = load_hemisphere_series_recipe(SERIES_RECIPE).composition_for("quartz")
    inverse = orientation_matrix(recipe.orientation).T
    members = []
    for index in range(11):
        angle = index * math.pi / 11.0
        normal_sample = np.array([math.cos(angle), math.sin(angle), 0.0])
        members.append(
            ArtBandMember(
                hkl=(index + 1, 0, 1),
                normal_crystal=inverse @ normal_sample,
                bragg_half_width_rad=0.030 - index * 0.001,
                structure_factor_magnitude=100.0 - index,
                normalized_weight=1.0 - index * 0.05,
                globe_cohort=None,
                globe_eligible=True,
                tattoo_eligible=True,
                acceptance_state="unreviewed",
                acceptance_reason="synthetic phase-bundle candidate",
            )
        )
    members.sort(
        key=lambda member: (-member.normalized_weight, member.hkl, member.member_id)
    )
    cohort_by_member = _assign_cohorts(members)
    return ArtBandCatalog(
        schema_version=1,
        source_structure_id="structure-quartz-phase-bundle-fixture",
        source_structure_sha256="e" * 64,
        source_recipe_id="recipe-source-phase-bundle-fixture",
        presentation_recipe_id="recipe-presentation-phase-bundle-fixture",
        eligibility_min_weight=0.08,
        members=tuple(
            replace(member, globe_cohort=cohort_by_member[member.member_id])
            for member in members
        ),
    )


def _frozen_manifest(
    catalog: ArtBandCatalog,
    recipe: HemisphereCompositionRecipe,
) -> FrozenTattooSelection:
    assignments = [
        (tier, width)
        for tier in ("dominant", "secondary", "fine")
        for width in recipe.stroke_widths_mm[tier]
    ]
    return FrozenTattooSelection(
        schema_version=1,
        name="synthetic-reviewed-ice-selection",
        phase_slug="ice-ih",
        source_structure_id=catalog.source_structure_id,
        source_structure_sha256=catalog.source_structure_sha256,
        orientation_id=recipe.orientation.orientation_id,
        legacy_catalog_id="art-band-catalog-legacy-fixture",
        legacy_selection_id="tattoo-selection-legacy-fixture",
        policy="reviewed_hkl_rebind_under_corrected_physics",
        paths=tuple(
            FrozenTattooPath(
                hkl=member.hkl,
                tier=tier,
                width_mm=width,
                legacy_member_id=f"legacy-member-{index}",
            )
            for index, (member, (tier, width)) in enumerate(
                zip(catalog.members, assignments, strict=True)
            )
        ),
    )


def _standard_only_catalog() -> ArtBandCatalog:
    recipe = load_hemisphere_series_recipe(SERIES_RECIPE).composition_for("quartz")
    inverse = orientation_matrix(recipe.orientation).T
    members = [
        ArtBandMember(
            hkl=(index + 1, 1, 0),
            normal_crystal=inverse @ np.asarray(normal_sample),
            bragg_half_width_rad=0.030 - index * 0.001,
            structure_factor_magnitude=100.0 - index,
            normalized_weight=1.0 - index * 0.05,
            globe_cohort=None,
            globe_eligible=True,
            tattoo_eligible=True,
            acceptance_state="unreviewed",
            acceptance_reason="standard-only clearance fixture",
        )
        for index, normal_sample in enumerate(_STANDARD_ONLY_NORMALS)
    ]
    members.sort(
        key=lambda member: (-member.normalized_weight, member.hkl, member.member_id)
    )
    cohort_by_member = _assign_cohorts(members)
    return ArtBandCatalog(
        schema_version=1,
        source_structure_id="structure-standard-only-phase-bundle-fixture",
        source_structure_sha256="f" * 64,
        source_recipe_id="recipe-source-standard-only-fixture",
        presentation_recipe_id="recipe-presentation-standard-only-fixture",
        eligibility_min_weight=0.08,
        members=tuple(
            replace(member, globe_cohort=cohort_by_member[member.member_id])
            for member in members
        ),
    )


def _reviewed_ice_catalog(
    manifest: FrozenTattooSelection,
) -> ArtBandCatalog:
    recipe = load_hemisphere_series_recipe(SERIES_RECIPE).composition_for("ice-ih")
    inverse = orientation_matrix(recipe.orientation).T
    members = []
    for index, path in enumerate(manifest.paths):
        angle = index * math.pi / len(manifest.paths)
        normal_sample = np.array([math.cos(angle), math.sin(angle), 0.0])
        members.append(
            ArtBandMember(
                hkl=path.hkl,
                normal_crystal=inverse @ normal_sample,
                bragg_half_width_rad=0.030 - index * 0.001,
                structure_factor_magnitude=100.0 - index,
                normalized_weight=1.0 - index * 0.05,
                globe_cohort=None,
                globe_eligible=True,
                tattoo_eligible=True,
                acceptance_state="unreviewed",
                acceptance_reason="reviewed Ice manifest fixture",
            )
        )
    members.sort(
        key=lambda member: (-member.normalized_weight, member.hkl, member.member_id)
    )
    cohort_by_member = _assign_cohorts(members)
    return ArtBandCatalog(
        schema_version=1,
        source_structure_id=manifest.source_structure_id,
        source_structure_sha256=manifest.source_structure_sha256,
        source_recipe_id="recipe-source-reviewed-ice-fixture",
        presentation_recipe_id="recipe-presentation-reviewed-ice-fixture",
        eligibility_min_weight=0.08,
        members=tuple(
            replace(member, globe_cohort=cohort_by_member[member.member_id])
            for member in members
        ),
    )


@pytest.fixture(scope="module")
def bundle_inputs() -> dict[str, object]:
    series = load_hemisphere_series_recipe(SERIES_RECIPE)
    recipe = series.composition_for("quartz")
    treatment = series.treatments["wide"]
    catalog = _catalog()
    selection = select_tattoo_paths(catalog, recipe)
    geometry = build_tattoo_geometry(
        selection,
        recipe,
        width_scale=treatment.arc_width_scale,
    )
    return {
        "phase_slug": "quartz",
        "treatment": treatment,
        "catalog": catalog,
        "recipe": recipe,
        "selection": selection,
        "geometry": geometry,
        "rendered": render_primary_tattoo(geometry),
        "disclaimer": DISCLAIMER_TEXT,
    }


def test_phase_bundle_has_dynamic_inventory_and_content_identity(
    tmp_path: Path,
    bundle_inputs: dict[str, object],
) -> None:
    from kikuchi_lab.art_products.hemisphere_bundle import (
        write_phase_hemisphere_bundle,
    )

    result = write_phase_hemisphere_bundle(tmp_path, **bundle_inputs)
    manifest_path = result.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_files = {
        "quartz-hemisphere-wide.svg",
        "quartz-hemisphere-wide.pdf",
        "quartz-hemisphere-wide-mockup.png",
        "quartz-hemisphere-wide-stencil.png",
        "hemisphere-composition-recipe.json",
        "hemisphere-treatment-recipe.json",
        "art-band-catalog.json",
        "band-selection-ledger.json",
        "path-geometry.json",
        "stroke-gap-diagnostic.json",
        "tattoo-artist-review.txt",
    }
    assert set(manifest["files"]) == expected_files
    assert result.phase_slug == "quartz"
    assert result.treatment == "wide"
    assert result.selection_id == bundle_inputs["selection"].selection_id
    assert result.geometry_id == bundle_inputs["geometry"].geometry_id
    assert result.run_id == stable_id(
        "quartz-hemisphere-wide-run",
        manifest["run_identity"],
    )
    assert result.manifest_sha256 == hashlib.sha256(
        manifest_path.read_bytes()
    ).hexdigest()
    assert manifest["run_identity"]["phase_slug"] == "quartz"
    assert manifest["run_identity"]["treatment"] == "wide"
    assert manifest["run_identity"]["arc_width_scale"] == 1.15
    assert manifest["run_identity"]["treatment_id"] == bundle_inputs[
        "treatment"
    ].treatment_id


def test_phase_bundle_rejects_geometry_from_the_wrong_width_treatment(
    tmp_path: Path,
    bundle_inputs: dict[str, object],
) -> None:
    from kikuchi_lab.art_products.hemisphere_bundle import (
        write_phase_hemisphere_bundle,
    )

    standard_geometry = build_tattoo_geometry(
        bundle_inputs["selection"],
        bundle_inputs["recipe"],
        width_scale=1.0,
    )
    output = tmp_path / "wrong-width"
    with pytest.raises(ValueError, match="geometry content does not match"):
        write_phase_hemisphere_bundle(
            output,
            **{
                **bundle_inputs,
                "geometry": standard_geometry,
                "rendered": render_primary_tattoo(standard_geometry),
            },
        )
    assert not output.exists()


def test_standard_bundle_requires_the_same_selection_to_pass_wide_preflight(
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.hemisphere_bundle import (
        write_phase_hemisphere_bundle,
    )

    series = load_hemisphere_series_recipe(SERIES_RECIPE)
    recipe = series.composition_for("quartz")
    treatment = series.treatments["standard"]
    catalog = _standard_only_catalog()
    selection = select_tattoo_paths(catalog, recipe)
    geometry = build_tattoo_geometry(selection, recipe, width_scale=1.0)
    with pytest.raises(ValueError, match="wide geometry preflight"):
        write_phase_hemisphere_bundle(
            tmp_path / "standard",
            phase_slug="quartz",
            treatment=treatment,
            catalog=catalog,
            recipe=recipe,
            selection=selection,
            geometry=geometry,
            rendered=render_primary_tattoo(geometry),
            disclaimer=DISCLAIMER_TEXT,
        )
    assert not (tmp_path / "standard").exists()


def test_standard_bundle_publishes_after_the_wide_preflight_passes(
    tmp_path: Path,
    bundle_inputs: dict[str, object],
) -> None:
    from kikuchi_lab.art_products.hemisphere_bundle import (
        write_phase_hemisphere_bundle,
    )

    series = load_hemisphere_series_recipe(SERIES_RECIPE)
    treatment = series.treatments["standard"]
    geometry = build_tattoo_geometry(
        bundle_inputs["selection"],
        bundle_inputs["recipe"],
        width_scale=1.0,
    )
    result = write_phase_hemisphere_bundle(
        tmp_path,
        **{
            **bundle_inputs,
            "treatment": treatment,
            "geometry": geometry,
            "rendered": render_primary_tattoo(geometry),
        },
    )

    assert result.treatment == "standard"
    assert result.path.is_dir()


def test_generic_ice_bundle_requires_reviewed_frozen_selection(
    tmp_path: Path,
    bundle_inputs: dict[str, object],
) -> None:
    from kikuchi_lab.art_products.hemisphere_bundle import (
        write_phase_hemisphere_bundle,
    )

    recipe = replace(bundle_inputs["recipe"], phase_slug="ice-ih")
    output = tmp_path / "ice"
    with pytest.raises(ValueError, match="Ice Ih requires a frozen selection manifest"):
        write_phase_hemisphere_bundle(
            output,
            **{
                **bundle_inputs,
                "phase_slug": "ice-ih",
                "recipe": recipe,
            },
        )
    assert not output.exists()


def test_frozen_selection_accepts_structural_hemisphere_recipe() -> None:
    series = load_hemisphere_series_recipe(SERIES_RECIPE)
    recipe = series.composition_for("ice-ih")
    catalog = _catalog()
    manifest = _frozen_manifest(catalog, recipe)

    selection = bind_frozen_tattoo_selection(catalog, recipe, manifest)

    assert selection.recipe_id == recipe.recipe_id
    assert selection.ledger["automatic_reselection"] is False


def test_generic_ice_bundle_rejects_a_self_consistent_substitute_manifest(
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.hemisphere_bundle import (
        write_phase_hemisphere_bundle,
    )

    series = load_hemisphere_series_recipe(SERIES_RECIPE)
    recipe = series.composition_for("ice-ih")
    treatment = series.treatments["wide"]
    catalog = _catalog()
    frozen_manifest = _frozen_manifest(catalog, recipe)
    selection = bind_frozen_tattoo_selection(catalog, recipe, frozen_manifest)
    geometry = build_tattoo_geometry(
        selection,
        recipe,
        width_scale=treatment.arc_width_scale,
    )

    output = tmp_path / "substitute"
    with pytest.raises(ValueError, match="authoritative reviewed manifest"):
        write_phase_hemisphere_bundle(
            output,
            phase_slug="ice-ih",
            treatment=treatment,
            catalog=catalog,
            recipe=recipe,
            selection=selection,
            geometry=geometry,
            rendered=render_primary_tattoo(geometry),
            disclaimer=DISCLAIMER_TEXT,
            frozen_manifest=frozen_manifest,
        )
    assert not output.exists()


def test_generic_ice_bundle_records_the_authoritative_frozen_manifest(
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.frozen_selection import (
        load_frozen_tattoo_selection,
    )
    from kikuchi_lab.art_products.hemisphere_bundle import (
        write_phase_hemisphere_bundle,
    )

    series = load_hemisphere_series_recipe(SERIES_RECIPE)
    recipe = series.composition_for("ice-ih")
    treatment = series.treatments["wide"]
    frozen_manifest = load_frozen_tattoo_selection(REVIEWED_ICE_SELECTION)
    catalog = _reviewed_ice_catalog(frozen_manifest)
    selection = bind_frozen_tattoo_selection(catalog, recipe, frozen_manifest)
    geometry = build_tattoo_geometry(
        selection,
        recipe,
        width_scale=treatment.arc_width_scale,
    )

    result = write_phase_hemisphere_bundle(
        tmp_path,
        phase_slug="ice-ih",
        treatment=treatment,
        catalog=catalog,
        recipe=recipe,
        selection=selection,
        geometry=geometry,
        rendered=render_primary_tattoo(geometry),
        disclaimer=DISCLAIMER_TEXT,
        frozen_manifest=frozen_manifest,
    )

    manifest = json.loads((result.path / "manifest.json").read_text())
    assert "frozen-selection-manifest.json" in manifest["files"]
    assert manifest["run_identity"]["frozen_manifest_id"] == (
        "frozen-tattoo-selection-f0e4f843362bab65"
    )
