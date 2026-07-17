from __future__ import annotations

import importlib
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import replace
from types import ModuleType

import numpy as np
import pytest

from kikuchi_lab.art_products.contracts import (
    TattooBoundary,
    TattooGeometry,
    TattooPath,
)
from kikuchi_lab.art_products.tattoo_recipe import load_tattoo_recipe
from kikuchi_lab.art_products.tattoo_selection import (
    SelectedTattooPath,
    TattooSelection,
)


RECIPE = "recipes/art/ice-ih-tattoo.yml"
WIDTHS = (4.8, 4.2, 3.6, 3.1, 2.5, 2.2, 1.9, 1.6, 1.2, 1.0, 0.8)
TIERS = ("dominant",) * 4 + ("secondary",) * 4 + ("fine",) * 3


def _vector() -> ModuleType:
    return importlib.import_module("kikuchi_lab.art_products.tattoo_vector")


def _selection() -> TattooSelection:
    recipe = load_tattoo_recipe(RECIPE)
    selected = []
    for index, (tier, width) in enumerate(zip(TIERS, WIDTHS, strict=True)):
        angle = index * math.pi / 11.0
        direction = np.array([math.cos(angle), math.sin(angle)])
        selected.append(
            SelectedTattooPath(
                member_id=f"member-{index:02d}",
                tier=tier,
                width_mm=width,
                normal_sample=(0.0, 0.0, 1.0),
                center_trace=np.vstack((-1.2 * direction, 1.2 * direction)),
                score_components={
                    "strength": 1.0 - index / 20.0,
                    "angular_width": 0.5,
                    "nonredundancy": 1.0,
                    "coverage": 1.0,
                    "zone_relationship": 1.0,
                },
                total_score=1.0 - index / 40.0,
                selection_reason="deliberately crossing physical fixture",
            )
        )
    return TattooSelection(
        catalog_id="catalog-test",
        recipe_id=recipe.recipe_id,
        orientation_id=recipe.orientation.orientation_id,
        candidates=(),
        selected_paths=tuple(selected),
        ledger={"fixture": "eleven transverse diameters"},
    )


def _boundary() -> TattooBoundary:
    return TattooBoundary(
        schema_version=1,
        role="stereographic_hemisphere_boundary",
        scientific_claim="noncrystallographic_projection_primitive",
        center_mm=(72.5, 72.5),
        outer_diameter_mm=132.0,
        width_mm=2.2,
        ink="#000000",
    )


def test_build_preserves_order_widths_and_centered_crop_without_mutation() -> None:
    vector = _vector()
    recipe = load_tattoo_recipe(RECIPE)
    selection = _selection()
    source_points = tuple(path.center_trace.copy() for path in selection.selected_paths)

    geometry = vector.build_tattoo_geometry(selection, recipe)
    repeated = vector.build_tattoo_geometry(selection, recipe)

    assert isinstance(geometry, TattooGeometry)
    assert geometry.geometry_id == repeated.geometry_id
    assert geometry.catalog_id == selection.catalog_id
    assert geometry.orientation_id == selection.orientation_id
    assert geometry.artboard_size_mm == 145.0
    assert [path.member_id for path in geometry.paths] == [
        path.member_id for path in selection.selected_paths
    ]
    assert [path.tier for path in geometry.paths] == list(TIERS)
    assert [path.width_mm for path in geometry.paths] == list(WIDTHS)
    assert [path.path_id for path in geometry.paths] == [path.path_id for path in repeated.paths]
    np.testing.assert_allclose(
        geometry.paths[0].points_mm,
        [[8.7, 72.5], [136.3, 72.5]],
        rtol=0.0,
        atol=1e-12,
    )
    for path in geometry.paths:
        assert path.points_mm.dtype == np.dtype("<f8")
        assert not np.array_equal(path.points_mm[0], path.points_mm[-1])
        assert np.all(np.linalg.norm(np.diff(path.points_mm, axis=0), axis=1) > 0.0)
    for selected, before in zip(selection.selected_paths, source_points, strict=True):
        assert np.array_equal(selected.center_trace, before)
        assert not selected.center_trace.flags.writeable


def test_geometry_contains_complete_boundary_and_unchanged_path_hierarchy() -> None:
    selection = _selection()
    geometry = _vector().build_tattoo_geometry(selection, load_tattoo_recipe(RECIPE))

    assert geometry.boundary.to_dict() == {
        "boundary_id": geometry.boundary.boundary_id,
        "schema_version": 1,
        "role": "stereographic_hemisphere_boundary",
        "scientific_claim": "noncrystallographic_projection_primitive",
        "center_mm": [72.5, 72.5],
        "outer_diameter_mm": 132.0,
        "width_mm": 2.2,
        "ink": "#000000",
    }
    assert len(geometry.paths) == 11
    assert [path.member_id for path in geometry.paths] == [
        path.member_id for path in selection.selected_paths
    ]
    assert [path.tier for path in geometry.paths] == [
        "dominant",
        "dominant",
        "dominant",
        "dominant",
        "secondary",
        "secondary",
        "secondary",
        "secondary",
        "fine",
        "fine",
        "fine",
    ]


def test_every_trace_is_contained_and_terminates_on_inner_limb() -> None:
    geometry = _vector().build_tattoo_geometry(_selection(), load_tattoo_recipe(RECIPE))
    center = np.asarray(geometry.boundary.center_mm)
    inner_radius = (
        geometry.boundary.outer_diameter_mm / 2.0 - geometry.boundary.width_mm
    )
    for path in geometry.paths:
        radii = np.linalg.norm(path.points_mm - center, axis=1)
        assert radii[0] == pytest.approx(inner_radius, abs=1e-8)
        assert radii[-1] == pytest.approx(inner_radius, abs=1e-8)
        assert np.all(radii <= inner_radius + 1e-8)


def test_build_rejects_coherently_forged_tier_and_width_order() -> None:
    vector = _vector()
    recipe = load_tattoo_recipe(RECIPE)
    selection = _selection()
    forged_paths = list(selection.selected_paths)
    first = forged_paths[0]
    last = forged_paths[-1]
    forged_paths[0] = replace(first, tier=last.tier, width_mm=last.width_mm)
    forged_paths[-1] = replace(last, tier=first.tier, width_mm=first.width_mm)
    forged = TattooSelection(
        catalog_id=selection.catalog_id,
        recipe_id=selection.recipe_id,
        orientation_id=selection.orientation_id,
        candidates=selection.candidates,
        selected_paths=tuple(forged_paths),
        ledger=selection.ledger,
    )

    with pytest.raises(
        ValueError,
        match="ordered tier/width assignments must match the tattoo recipe",
    ):
        vector.build_tattoo_geometry(forged, recipe)


def test_circle_clipping_handles_endpoint_tangent_and_crossing_segments() -> None:
    clip = _vector()._clip_polyline_to_circle

    endpoint = clip(np.array([[0.0, 0.0], [0.9, 0.0]]), 0.9)
    tangent = clip(np.array([[-1.0, 0.9], [1.0, 0.9]]), 0.9)
    crossing = clip(np.array([[-1.0, 0.0], [1.0, 0.0]]), 0.9)

    assert len(endpoint) == 1
    np.testing.assert_allclose(endpoint[0], [[0.0, 0.0], [0.9, 0.0]], atol=1e-15)
    assert tangent == ()
    assert len(crossing) == 1
    np.testing.assert_allclose(crossing[0], [[-0.9, 0.0], [0.9, 0.0]], atol=1e-15)


def test_validate_requires_exactly_eleven_open_nonduplicated_polylines() -> None:
    vector = _vector()
    path = TattooPath(
        member_id="only-member",
        tier="fine",
        width_mm=0.8,
        points_mm=[[10.0, 10.0], [20.0, 20.0]],
        score_components={"strength": 1.0},
        selection_reason="count fixture",
    )
    geometry = TattooGeometry(
        schema_version=1,
        catalog_id="catalog-test",
        orientation_id="orientation-test",
        artboard_size_mm=145.0,
        boundary=_boundary(),
        paths=(path,),
        projection="upper_specimen_stereographic_center_trace",
    )

    with pytest.raises(ValueError, match="exactly 11 open polylines"):
        vector.validate_tattoo_geometry(geometry)


def test_primary_svg_is_canonical_black_transparent_and_deterministic() -> None:
    vector = _vector()
    geometry = vector.build_tattoo_geometry(_selection(), load_tattoo_recipe(RECIPE))
    geometry_id = geometry.geometry_id
    point_hashes = tuple(path.points_sha256 for path in geometry.paths)

    first = vector.primary_svg_bytes(geometry)
    repeated = vector.primary_svg_bytes(geometry)

    assert first == repeated
    assert geometry.geometry_id == geometry_id
    assert tuple(path.points_sha256 for path in geometry.paths) == point_hashes
    svg = first.decode("utf-8")
    assert svg.startswith(
        '<svg height="145.000000mm" version="1.1" '
        'viewBox="0 0 145.000000 145.000000" width="145.000000mm" '
        'xmlns="http://www.w3.org/2000/svg">\n'
    )
    assert svg.endswith("</svg>\n")
    assert svg.count("<path ") == 11
    assert svg.count("<circle ") == 2
    assert svg.count("<clipPath ") == 1
    assert "<rect" not in svg
    assert "background" not in svg
    assert "rim" not in svg
    assert "node" not in svg

    root = ET.fromstring(first)
    definitions = list(root)[0]
    assert definitions.tag == "{http://www.w3.org/2000/svg}defs"
    paths = list(root)[1:-1]
    assert len(paths) == 11
    for element, path in zip(paths, geometry.paths, strict=True):
        assert element.tag == "{http://www.w3.org/2000/svg}path"
        assert element.attrib["id"] == path.path_id
        assert element.attrib["clip-path"] == "url(#tattoo-band-layer-clip)"
        assert element.attrib["fill"] == "none"
        assert element.attrib["stroke"] == "#000000"
        assert element.attrib["stroke-linecap"] == "round"
        assert element.attrib["stroke-linejoin"] == "round"
        assert element.attrib["stroke-width"] == f"{path.width_mm:.6f}"
        coordinate_tokens = re.findall(r"-?\d+\.\d+", element.attrib["d"])
        assert coordinate_tokens
        assert all(re.fullmatch(r"-?\d+\.\d{6}", value) for value in coordinate_tokens)

    path_lines = [line for line in svg.splitlines() if line.startswith("  <path ")]
    for line in path_lines:
        assert re.findall(r" ([A-Za-z:-]+)=", line) == [
            "clip-path",
            "d",
            "fill",
            "id",
            "stroke",
            "stroke-linecap",
            "stroke-linejoin",
            "stroke-width",
        ]
