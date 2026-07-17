from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.art_products.orientation_gallery_sheet import (
    ORIENTATION_GALLERY_CELL_ORDER,
)
from kikuchi_lab.art_products.orientation_gallery_recipe import (
    OrientationGalleryRecipe,
    load_orientation_gallery_recipe,
)
from kikuchi_lab.kinematical import kikuchipy_adapter
from kikuchi_lab.kinematical.kikuchipy_adapter import (
    build_direct_reflector_evidence,
)
from kikuchi_lab.kinematical.reflector_evidence import (
    load_direct_reflector_recipe,
)
from kikuchi_lab.kinematical.reflector_parity import (
    ReflectorParityReport,
    compare_reflector_evidence,
)
from kikuchi_lab.sources.structure import load_structure_record
from kikuchi_lab.workflows.phase_art_orientation_gallery import (
    render_phase_art_orientation_gallery,
)
from kikuchi_lab.workflows.phase_art_series import PhaseParityReportError


ROOT = Path(__file__).parents[2]
GALLERY_RECIPE = ROOT / "recipes/art/five-phase-standard-orientation-gallery.yml"

pytestmark = [
    pytest.mark.filterwarnings("ignore:.*abcABG.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*expandPosition.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*GetSpaceGroup.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*placeInLattice.*:DeprecationWarning"),
]


@dataclass(frozen=True)
class GalleryInputs:
    recipe: OrientationGalleryRecipe
    parity_root: Path


@pytest.fixture(scope="module")
def gallery_inputs(tmp_path_factory: pytest.TempPathFactory) -> GalleryInputs:
    temporary_root = tmp_path_factory.mktemp("phase-art-orientation-gallery-inputs")
    parity_root = temporary_root / "recursive" / "parity"
    recipe = load_orientation_gallery_recipe(GALLERY_RECIPE)
    for phase_slug in recipe.phase_order:
        reflector_path = (
            GALLERY_RECIPE.parent
            / recipe.source_series.reflector_recipes[phase_slug]
        ).resolve()
        reflector_recipe = load_direct_reflector_recipe(reflector_path)
        source = load_structure_record(
            (reflector_path.parent / reflector_recipe.source_record).resolve()
        )
        evidence = build_direct_reflector_evidence(source, reflector_recipe)
        report = compare_reflector_evidence(evidence, evidence).with_master(
            np.zeros((2, 65, 65), dtype=np.float64)
        )
        report.validate_for_publication()
        report_path = (
            parity_root
            / phase_slug
            / "retained"
            / report.run_id
            / "reflector-parity-report.json"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report.to_json(), encoding="utf-8")
    return GalleryInputs(recipe=recipe, parity_root=parity_root)


def test_gallery_preflights_and_publishes_fifteen_real_standard_cells_without_master_simulation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    gallery_inputs: GalleryInputs,
) -> None:
    import kikuchi_lab.workflows.phase_art_orientation_gallery as gallery_workflow

    monkeypatch.setattr(
        kikuchipy_adapter,
        "KikuchiPatternSimulator",
        lambda *_args, **_kwargs: pytest.fail("gallery attempted master simulation"),
    )
    standard_selection_calls: list[tuple[object, object]] = []
    original_standard_selection = gallery_workflow.select_standard_clearance_valid_tattoo_paths

    def observe_standard_selection(*args: object, **kwargs: object) -> object:
        standard_selection_calls.append(args)
        return original_standard_selection(*args, **kwargs)

    monkeypatch.setattr(
        gallery_workflow,
        "select_standard_clearance_valid_tattoo_paths",
        observe_standard_selection,
    )
    output_root = tmp_path / "gallery"

    result = render_phase_art_orientation_gallery(
        recipe_path=GALLERY_RECIPE,
        parity_root=gallery_inputs.parity_root,
        output_root=output_root,
    )

    assert result.path == output_root
    assert result.cell_order == ORIENTATION_GALLERY_CELL_ORDER
    assert result.simulation_count == 0
    assert len(result.cell_bundles) == 15
    assert [bundle.path.parent for bundle in result.cell_bundles] == [output_root] * 15
    assert result.comparison_sheet.parent == output_root / result.comparison_id
    assert result.ledger_path.parent == output_root / result.comparison_id
    assert len([path for path in output_root.iterdir() if path.is_dir()]) == 16

    ledger = json.loads(result.ledger_path.read_text(encoding="utf-8"))
    assert tuple(ledger["cell_order"]) == ORIENTATION_GALLERY_CELL_ORDER
    assert [record["euler_bunge_deg"] for record in ledger["cells"]] == [
        list(variant.orientation.euler_bunge_deg)
        for variant in gallery_inputs.recipe.variants
        for _phase_slug in gallery_inputs.recipe.phase_order
    ]
    assert all(record["orientation_frame"] == "crystal_to_sample" for record in ledger["cells"])
    assert all(record["treatment"] == "standard" for record in ledger["cells"])
    assert all(record["arc_width_scale"] == 1.0 for record in ledger["cells"])
    assert all(record["simulation_count"] == 0 for record in ledger["cells"])
    assert len(standard_selection_calls) == 15

    for bundle in result.cell_bundles:
        selection_ledger = json.loads(
            (bundle.path / "band-selection-ledger.json").read_text(encoding="utf-8")
        )
        assert "wide_clearance_search" not in selection_ledger["ledger"]


def test_gallery_stale_parity_preflight_leaves_requested_root_absent(
    tmp_path: Path,
    gallery_inputs: GalleryInputs,
) -> None:
    parity_root = tmp_path / "stale-parity"
    shutil.copytree(gallery_inputs.parity_root, parity_root)
    titanite_report = next(
        path
        for path in parity_root.rglob("reflector-parity-report.json")
        if "titanite" in path.parts
    )
    report = ReflectorParityReport.from_json(titanite_report.read_text(encoding="utf-8"))
    stale = replace(report, direct_evidence_id="direct-reflector-evidence-stale")
    stale.validate_for_publication()
    titanite_report.write_text(stale.to_json(), encoding="utf-8")
    output_root = tmp_path / "must-not-exist"

    with pytest.raises(PhaseParityReportError, match="stale reflector parity report.*titanite"):
        render_phase_art_orientation_gallery(
            recipe_path=GALLERY_RECIPE,
            parity_root=parity_root,
            output_root=output_root,
        )

    assert not output_root.exists()


def test_gallery_late_geometry_preflight_leaves_requested_root_absent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    gallery_inputs: GalleryInputs,
) -> None:
    import kikuchi_lab.workflows.phase_art_orientation_gallery as gallery_workflow

    original = gallery_workflow.build_tattoo_geometry

    def reject_final_geometry(*args: object, **kwargs: object) -> object:
        recipe = args[1]
        if (
            recipe.phase_slug == "titanite"
            and recipe.orientation == gallery_inputs.recipe.variants[-1].orientation
        ):
            raise ValueError("deliberate gallery geometry failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(gallery_workflow, "build_tattoo_geometry", reject_final_geometry)
    output_root = tmp_path / "must-not-exist"

    with pytest.raises(ValueError, match="deliberate gallery geometry failure"):
        render_phase_art_orientation_gallery(
            recipe_path=GALLERY_RECIPE,
            parity_root=gallery_inputs.parity_root,
            output_root=output_root,
        )

    assert not output_root.exists()
