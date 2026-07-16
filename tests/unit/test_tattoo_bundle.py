from __future__ import annotations

import errno
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from kikuchi_lab.art_products.catalog import _assign_cohorts
from kikuchi_lab.art_products.contracts import (
    ArtBandCatalog,
    ArtBandMember,
    TattooGeometry,
)
from kikuchi_lab.art_products.tattoo_recipe import load_tattoo_recipe
from kikuchi_lab.art_products.tattoo_selection import select_tattoo_paths
from kikuchi_lab.art_products.tattoo_vector import (
    build_tattoo_geometry,
    render_primary_tattoo,
)
from kikuchi_lab.artifacts import BundleExistsError, PartialBundleError
from kikuchi_lab.model.identity import canonical_json, stable_id
from kikuchi_lab.spherical_intensity.orientation import orientation_matrix


ROOT = Path(__file__).parents[2]
RECIPE = ROOT / "recipes/art/ice-ih-tattoo.yml"
PAYLOAD_FILES = {
    "ice-ih-tattoo-primary.svg",
    "ice-ih-tattoo-primary.pdf",
    "ice-ih-tattoo-mockup.png",
    "ice-ih-tattoo-stencil.png",
    "tattoo-recipe.json",
    "art-band-catalog.json",
    "band-selection-ledger.json",
    "path-geometry.json",
    "stroke-gap-diagnostic.json",
    "tattoo-artist-review.txt",
}
DISCLAIMER = (
    "This science-art is not medical guidance or a skin-approved stencil and "
    "requires qualified tattoo-artist review before any use on skin.\n"
)
WIDTHS = (4.8, 4.2, 3.6, 3.1, 2.5, 2.2, 1.9, 1.6, 1.2, 1.0, 0.8)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _catalog() -> ArtBandCatalog:
    recipe = load_tattoo_recipe(RECIPE)
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
                acceptance_reason="synthetic primary-bundle candidate",
            )
        )
    members.sort(key=lambda member: (-member.normalized_weight, member.hkl, member.member_id))
    cohort_by_member = _assign_cohorts(members)
    return ArtBandCatalog(
        schema_version=1,
        source_structure_id="structure-ice-ih-primary-bundle-fixture",
        source_structure_sha256="d" * 64,
        source_recipe_id="recipe-source-primary-bundle-fixture",
        presentation_recipe_id="recipe-presentation-primary-bundle-fixture",
        eligibility_min_weight=0.08,
        members=tuple(
            replace(member, globe_cohort=cohort_by_member[member.member_id])
            for member in members
        ),
    )


@pytest.fixture(scope="module")
def bundle_inputs() -> dict[str, object]:
    catalog = _catalog()
    recipe = load_tattoo_recipe(RECIPE)
    selection = select_tattoo_paths(catalog, recipe)
    geometry = build_tattoo_geometry(selection, recipe)
    return {
        "catalog": catalog,
        "recipe": recipe,
        "selection": selection,
        "geometry": geometry,
        "rendered": render_primary_tattoo(geometry),
        "treatment": "primary",
        "disclaimer": DISCLAIMER,
    }


def test_bundle_svg_validator_accepts_canonical_paths_then_boundary(
    bundle_inputs: dict[str, object],
) -> None:
    from kikuchi_lab.art_products.tattoo_bundle import _validate_svg

    payload = bundle_inputs["rendered"]["primary.svg"]
    root = ET.fromstring(payload)
    assert [child.tag.rsplit("}", 1)[-1] for child in root] == [
        *("path" for _ in range(11)),
        "circle",
    ]
    assert _validate_svg(payload) is None


def test_primary_bundle_has_exact_inventory_manifest_last_and_auditable_content(
    bundle_inputs: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import kikuchi_lab.art_products.tattoo_bundle as bundle_module
    from kikuchi_lab.art_products.tattoo_bundle import write_tattoo_bundle

    writes: list[str] = []
    real_write_bytes = bundle_module._write_bytes
    real_write_json = bundle_module._write_json

    def record_bytes(path: Path, payload: bytes) -> None:
        writes.append(path.name)
        real_write_bytes(path, payload)

    def record_json(path: Path, payload: object) -> None:
        writes.append(path.name)
        real_write_json(path, payload)

    monkeypatch.setattr(bundle_module, "_write_bytes", record_bytes)
    monkeypatch.setattr(bundle_module, "_write_json", record_json)
    result = write_tattoo_bundle(tmp_path, **bundle_inputs)

    manifest_path = result.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selection = bundle_inputs["selection"]
    geometry = bundle_inputs["geometry"]

    assert {path.name for path in result.path.iterdir()} == PAYLOAD_FILES | {
        "manifest.json"
    }
    assert set(manifest["files"]) == PAYLOAD_FILES
    assert writes[-1] == "manifest.json"
    assert manifest_path.read_text(encoding="utf-8") == canonical_json(manifest)
    assert result.run_id == stable_id("ice-tattoo-run", manifest["run_identity"])
    assert result.path == tmp_path / result.run_id
    assert result.manifest_sha256 == _sha256(manifest_path)
    for relative, record in manifest["files"].items():
        artifact = result.path / relative
        assert record == {"bytes": artifact.stat().st_size, "sha256": _sha256(artifact)}

    assert manifest["run_identity"]["treatment"] == "primary"
    assert manifest["run_identity"]["selection_id"] == selection.selection_id
    assert manifest["run_identity"]["geometry_id"] == geometry.geometry_id
    assert (result.path / "tattoo-artist-review.txt").read_text() == DISCLAIMER

    recipe_snapshot = json.loads((result.path / "tattoo-recipe.json").read_text())
    catalog_snapshot = json.loads((result.path / "art-band-catalog.json").read_text())
    selection_snapshot = json.loads(
        (result.path / "band-selection-ledger.json").read_text()
    )
    geometry_snapshot = json.loads((result.path / "path-geometry.json").read_text())
    diagnostic = json.loads((result.path / "stroke-gap-diagnostic.json").read_text())
    assert recipe_snapshot["recipe_id"] == bundle_inputs["recipe"].recipe_id
    assert catalog_snapshot["catalog_id"] == bundle_inputs["catalog"].catalog_id
    assert selection_snapshot["selection_id"] == selection.selection_id
    assert geometry_snapshot["geometry_id"] == geometry.geometry_id
    assert [path["width_mm"] for path in geometry_snapshot["content"]["paths"]] == list(
        WIDTHS
    )
    assert diagnostic["validation"] == {
        "minimum_endpoint_clearance_mm": 2.0,
        "minimum_noncrossing_edge_gap_mm": 1.5,
        "status": "passed",
    }
    assert diagnostic["geometry_id"] == geometry.geometry_id
    assert [record["points_sha256"] for record in diagnostic["paths"]] == [
        path.points_sha256 for path in geometry.paths
    ]

    svg = (result.path / "ice-ih-tattoo-primary.svg").read_text()
    assert svg.count('stroke="#000000"') == 12
    assert re.search(r'stroke="(?!#000000)', svg) is None
    assert (result.path / "ice-ih-tattoo-primary.pdf").read_bytes().startswith(b"%PDF-")
    for name, size, corner in (
        ("ice-ih-tattoo-mockup.png", (1713, 1713), (216, 181, 154)),
        ("ice-ih-tattoo-stencil.png", (1713, 1713), (255, 255, 255)),
    ):
        with Image.open(result.path / name) as image:
            assert image.format == "PNG"
            assert image.size == size
            assert image.convert("RGB").getpixel((0, 0)) == corner


def test_bundle_run_identity_is_path_neutral(
    bundle_inputs: dict[str, object],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.tattoo_bundle import write_tattoo_bundle

    first = write_tattoo_bundle(tmp_path / "first", **bundle_inputs)
    second = write_tattoo_bundle(tmp_path / "second/nested", **bundle_inputs)

    assert first.run_id == second.run_id
    assert first.manifest_sha256 == second.manifest_sha256


def test_bundle_rejects_legacy_catalog_threshold_before_output_mutation(
    bundle_inputs: dict[str, object],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.tattoo_bundle import write_tattoo_bundle

    legacy_catalog = replace(
        bundle_inputs["catalog"],
        eligibility_min_weight=0.10,
    )
    output_root = tmp_path / "legacy-threshold" / "runs"

    with pytest.raises(
        ValueError,
        match="tattoo catalog threshold must be exactly 0.08",
    ):
        write_tattoo_bundle(
            output_root,
            **{**bundle_inputs, "catalog": legacy_catalog},
        )

    assert not output_root.exists()


@pytest.mark.parametrize(
    ("field", "message"),
    (
        ("catalog_id", "catalog_id does not match catalog content"),
        ("selection_id", "selection_id does not match selection content"),
        ("geometry_id", "geometry_id does not match geometry content"),
    ),
)
def test_forged_identities_are_rejected_before_output_mutation(
    bundle_inputs: dict[str, object],
    field: str,
    message: str,
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.tattoo_bundle import write_tattoo_bundle

    inputs = dict(bundle_inputs)
    owner = {
        "catalog_id": inputs["catalog"],
        "selection_id": inputs["selection"],
        "geometry_id": inputs["geometry"],
    }[field]
    object.__setattr__(owner, field, f"{field}-forged")
    output_root = tmp_path / field / "runs"
    try:
        with pytest.raises(ValueError, match=message):
            write_tattoo_bundle(output_root, **inputs)
    finally:
        object.__setattr__(owner, field, f"{field}-forged")
        if field == "catalog_id":
            object.__setattr__(owner, field, stable_id("art-band-catalog", owner.to_dict()))
        elif field == "selection_id":
            object.__setattr__(
                owner,
                field,
                stable_id(
                    "tattoo-selection",
                    {
                        "catalog_id": owner.catalog_id,
                        "recipe_id": owner.recipe_id,
                        "orientation_id": owner.orientation_id,
                        "selected_paths": [
                            path.identity_dict() for path in owner.selected_paths
                        ],
                    },
                ),
            )
        else:
            object.__setattr__(owner, field, stable_id("tattoo-geometry", owner.to_dict()))
    assert not output_root.exists()


def test_coherent_wrong_orientation_and_path_count_fail_before_output_mutation(
    bundle_inputs: dict[str, object],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.tattoo_bundle import write_tattoo_bundle

    geometry = bundle_inputs["geometry"]
    wrong_orientation = TattooGeometry(
        schema_version=geometry.schema_version,
        catalog_id=geometry.catalog_id,
        orientation_id="orientation-coherent-forgery",
        artboard_size_mm=geometry.artboard_size_mm,
        boundary=geometry.boundary,
        paths=geometry.paths,
        projection=geometry.projection,
    )
    wrong_count = replace(geometry, paths=geometry.paths[:-1])
    cases = (
        (wrong_orientation, "geometry orientation does not match the tattoo recipe"),
        (wrong_count, "exactly 11 open polylines"),
    )
    for index, (forged, message) in enumerate(cases):
        output_root = tmp_path / f"case-{index}" / "runs"
        with pytest.raises(ValueError, match=message):
            write_tattoo_bundle(
                output_root,
                **{**bundle_inputs, "geometry": forged},
            )
        assert not output_root.exists()


@pytest.mark.parametrize("mutation", ("width", "coordinates"))
def test_coherent_width_or_coordinate_hash_change_fails_before_output_mutation(
    bundle_inputs: dict[str, object],
    mutation: str,
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.contracts import TattooPath
    from kikuchi_lab.art_products.tattoo_bundle import write_tattoo_bundle

    geometry = bundle_inputs["geometry"]
    original = geometry.paths[0]
    changed = TattooPath(
        member_id=original.member_id,
        tier=original.tier,
        width_mm=original.width_mm + (0.01 if mutation == "width" else 0.0),
        points_mm=(
            original.points_mm
            if mutation == "width"
            else np.array(original.points_mm[::-1], dtype="<f8", copy=True)
        ),
        score_components=original.score_components,
        selection_reason=original.selection_reason,
    )
    forged = replace(geometry, paths=(changed, *geometry.paths[1:]))
    assert forged.geometry_id != geometry.geometry_id
    assert changed.path_id != original.path_id
    output_root = tmp_path / mutation / "runs"

    with pytest.raises(
        ValueError,
        match=("ordered path widths" if mutation == "width" else "coordinate hashes"),
    ):
        write_tattoo_bundle(
            output_root,
            **{**bundle_inputs, "geometry": forged},
        )

    assert not output_root.exists()


def test_coherent_gap_violation_fails_before_output_mutation(
    bundle_inputs: dict[str, object],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.contracts import TattooPath
    from kikuchi_lab.art_products.tattoo_bundle import write_tattoo_bundle

    geometry = bundle_inputs["geometry"]

    def horizontal(path, y: float) -> TattooPath:
        center_x, center_y = geometry.boundary.center_mm
        inner_radius = (
            geometry.boundary.outer_diameter_mm / 2.0
            - geometry.boundary.width_mm
        )
        half_chord = math.sqrt(inner_radius**2 - (y - center_y) ** 2)
        return TattooPath(
            member_id=path.member_id,
            tier=path.tier,
            width_mm=path.width_mm,
            points_mm=[
                [center_x - half_chord, y],
                [center_x + half_chord, y],
            ],
            score_components=path.score_components,
            selection_reason=path.selection_reason,
        )

    first = horizontal(geometry.paths[0], 40.0)
    second = horizontal(geometry.paths[1], 45.99)
    forged = replace(geometry, paths=(first, second, *geometry.paths[2:]))
    assert forged.geometry_id != geometry.geometry_id
    output_root = tmp_path / "gap" / "runs"

    with pytest.raises(
        ValueError,
        match=r"noncrossing edge gap 1\.490000 mm is below 1\.500000 mm",
    ):
        write_tattoo_bundle(
            output_root,
            **{**bundle_inputs, "geometry": forged},
        )

    assert not output_root.exists()


def test_nonblack_svg_and_absent_disclaimer_fail_before_output_mutation(
    bundle_inputs: dict[str, object],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.tattoo_bundle import write_tattoo_bundle

    rendered = dict(bundle_inputs["rendered"])
    rendered["primary.svg"] = rendered["primary.svg"].replace(
        b"#000000", b"#123456"
    )
    cases = (
        ({**bundle_inputs, "rendered": rendered}, "primary SVG must use only black ink"),
        ({**bundle_inputs, "disclaimer": ""}, "tattoo-artist disclaimer is required"),
    )
    for index, (inputs, message) in enumerate(cases):
        output_root = tmp_path / f"invalid-{index}" / "runs"
        with pytest.raises(ValueError, match=message):
            write_tattoo_bundle(output_root, **inputs)
        assert not output_root.exists()


def test_completed_and_partial_collisions_preserve_existing_state(
    bundle_inputs: dict[str, object],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.tattoo_bundle import write_tattoo_bundle

    completed_root = tmp_path / "completed"
    result = write_tattoo_bundle(completed_root, **bundle_inputs)
    with pytest.raises(BundleExistsError, match="completed bundle already exists"):
        write_tattoo_bundle(completed_root, **bundle_inputs)
    assert (result.path / "manifest.json").is_file()

    partial_root = tmp_path / "partial"
    partial_root.mkdir()
    stale = partial_root / f".{result.run_id}.partial-stale"
    stale.mkdir()
    marker = stale / "retained.txt"
    marker.write_text("retained")
    with pytest.raises(PartialBundleError, match="partial bundle already exists"):
        write_tattoo_bundle(partial_root, **bundle_inputs)
    assert marker.read_text() == "retained"


def test_atomic_promotion_collision_preserves_rival_and_recoverable_partial(
    bundle_inputs: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import kikuchi_lab.art_products.tattoo_bundle as bundle_module
    from kikuchi_lab.art_products.tattoo_bundle import write_tattoo_bundle

    reference = write_tattoo_bundle(tmp_path / "reference", **bundle_inputs)
    root = tmp_path / "collision"

    def collide(source: Path, destination: Path) -> None:
        destination.mkdir()
        (destination / "rival.txt").write_text("rival")
        raise OSError(errno.EEXIST, "injected no-replace collision")

    monkeypatch.setattr(bundle_module, "_promote_directory_no_replace", collide)
    with pytest.raises(BundleExistsError, match="completed bundle already exists"):
        write_tattoo_bundle(root, **bundle_inputs)

    destination = root / reference.run_id
    assert (destination / "rival.txt").read_text() == "rival"
    partials = list(root.glob(f".{reference.run_id}.partial-*"))
    assert len(partials) == 1
    assert (partials[0] / "manifest.json").is_file()
    assert not (root / f".{reference.run_id}.publishing").exists()
