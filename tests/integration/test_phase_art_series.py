from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from kikuchi_lab.art_products.catalog import build_art_band_catalog_from_evidence
from kikuchi_lab.art_products.frozen_selection import (
    bind_frozen_tattoo_selection,
    load_frozen_tattoo_selection,
)
from kikuchi_lab.art_products.hemisphere_bundle import (
    write_phase_hemisphere_bundle,
)
from kikuchi_lab.art_products.hemisphere_recipe import (
    load_hemisphere_series_recipe,
)
from kikuchi_lab.art_products.tattoo_bundle import DISCLAIMER_TEXT
from kikuchi_lab.art_products.tattoo_vector import (
    build_tattoo_geometry,
    render_primary_tattoo,
)
from kikuchi_lab.kinematical import kikuchipy_adapter
from kikuchi_lab.kinematical.kikuchipy_adapter import (
    build_direct_reflector_evidence,
)
from kikuchi_lab.kinematical.reflector_evidence import (
    load_direct_reflector_recipe,
)
from kikuchi_lab.kinematical.reflector_parity import compare_reflector_evidence
from kikuchi_lab.sources.structure import load_structure_record
from kikuchi_lab.workflows.phase_art_series import (
    IceStandardReferenceMismatch,
    render_phase_art_series,
)


ROOT = Path(__file__).parents[2]
SERIES_RECIPE = ROOT / "recipes/art/five-phase-hemisphere-series.yml"
REVIEWED_ICE_SELECTION = ROOT / "recipes/art/ice-ih-reviewed-selection-v2.yml"
CELL_ORDER = (
    "ice-ih:standard",
    "ice-ih:wide",
    "forsterite:standard",
    "forsterite:wide",
    "quartz:standard",
    "quartz:wide",
    "zircon:standard",
    "zircon:wide",
    "titanite:standard",
    "titanite:wide",
)

pytestmark = [
    pytest.mark.filterwarnings("ignore:.*abcABG.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*expandPosition.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*GetSpaceGroup.*:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:.*placeInLattice.*:DeprecationWarning"),
]


@dataclass(frozen=True)
class SeriesInputs:
    parity_root: Path
    ice_standard_reference: Path


@pytest.fixture(scope="module")
def series_inputs(tmp_path_factory: pytest.TempPathFactory) -> SeriesInputs:
    temporary_root = tmp_path_factory.mktemp("phase-art-series-inputs")
    parity_root = temporary_root / "recursive" / "parity"
    series = load_hemisphere_series_recipe(SERIES_RECIPE)
    ice_catalog = None
    ice_evidence = None
    for phase_slug in series.phase_order:
        reflector_path = (
            SERIES_RECIPE.parent / series.reflector_recipes[phase_slug]
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
        if phase_slug == "ice-ih":
            ice_evidence = evidence
            ice_catalog = build_art_band_catalog_from_evidence(evidence)

    assert ice_catalog is not None and ice_evidence is not None
    composition = series.composition_for("ice-ih")
    frozen_manifest = load_frozen_tattoo_selection(REVIEWED_ICE_SELECTION)
    selection = bind_frozen_tattoo_selection(
        ice_catalog,
        composition,
        frozen_manifest,
    )
    standard = build_tattoo_geometry(selection, composition, width_scale=1.0)
    reference = write_phase_hemisphere_bundle(
        temporary_root / "corrected-ice-reference",
        phase_slug="ice-ih",
        treatment=series.treatments["standard"],
        catalog=ice_catalog,
        recipe=composition,
        selection=selection,
        geometry=standard,
        rendered=render_primary_tattoo(standard),
        disclaimer=DISCLAIMER_TEXT,
        frozen_manifest=frozen_manifest,
    )
    return SeriesInputs(
        parity_root=parity_root,
        ice_standard_reference=reference.path,
    )


def test_series_publishes_nine_new_bundles_and_ten_direct_review_cells(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    series_inputs: SeriesInputs,
) -> None:
    monkeypatch.setattr(
        kikuchipy_adapter,
        "KikuchiPatternSimulator",
        lambda *_args, **_kwargs: pytest.fail("series attempted master simulation"),
    )
    result = render_phase_art_series(
        recipe_path=SERIES_RECIPE,
        parity_root=series_inputs.parity_root,
        ice_standard_reference=series_inputs.ice_standard_reference,
        output_root=tmp_path,
    )

    assert len(result.new_bundles) == 9
    assert result.cell_order == CELL_ORDER
    assert result.simulation_count == 0
    assert tuple(
        f"{bundle.phase_slug}:{bundle.treatment}" for bundle in result.new_bundles
    ) == CELL_ORDER[1:]
    assert all(bundle.path.parent == tmp_path for bundle in result.new_bundles)
    assert result.path.parent == tmp_path
    assert len([path for path in tmp_path.iterdir() if path.is_dir()]) == 10

    with Image.open(result.comparison_sheet) as comparison:
        assert comparison.size == (4500, 1800)
        assert comparison.mode == "1"
        assert comparison.getextrema() == (0, 255)
    ledger = json.loads(
        (result.path / "comparison-ledger.json").read_text(encoding="utf-8")
    )
    assert tuple(ledger["cell_order"]) == CELL_ORDER
    assert ledger["cells"][0]["source_kind"] == "reference"
    assert ledger["cells"][0]["bundle_id"] == (
        series_inputs.ice_standard_reference.name
    )
    assert all(
        cell["source_kind"] == "bundle" for cell in ledger["cells"][1:]
    )
    assert [cell["bundle_id"] for cell in ledger["cells"][1:]] == [
        bundle.run_id for bundle in result.new_bundles
    ]

    manifest_path = result.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == result.series_id
    assert manifest["run_identity"]["simulation_count"] == 0
    assert manifest["run_identity"]["new_bundle_count"] == 9
    assert manifest["run_identity"]["cell_order"] == list(CELL_ORDER)
    assert result.manifest_sha256 == hashlib.sha256(
        manifest_path.read_bytes()
    ).hexdigest()
    for bundle in result.new_bundles:
        child_manifest = json.loads(
            (bundle.path / "manifest.json").read_text(encoding="utf-8")
        )
        assert child_manifest["run_id"] == bundle.run_id
        assert set(child_manifest["files"]) == {
            path.name for path in bundle.path.iterdir() if path.name != "manifest.json"
        }


def test_ice_reference_checksum_or_selection_mismatch_is_fatal_before_output(
    tmp_path: Path,
    series_inputs: SeriesInputs,
) -> None:
    damaged_reference = tmp_path / "damaged-reference"
    shutil.copytree(series_inputs.ice_standard_reference, damaged_reference)
    selection_path = damaged_reference / "band-selection-ledger.json"
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    selection["selected_paths"][0]["center_trace_sha256"] = "0" * 64
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    manifest_path = damaged_reference / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["band-selection-ledger.json"] = {
        "bytes": selection_path.stat().st_size,
        "sha256": hashlib.sha256(selection_path.read_bytes()).hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output_root = tmp_path / "must-not-exist"

    with pytest.raises(IceStandardReferenceMismatch, match="reviewed Ice"):
        render_phase_art_series(
            recipe_path=SERIES_RECIPE,
            parity_root=series_inputs.parity_root,
            ice_standard_reference=damaged_reference,
            output_root=output_root,
        )

    assert not output_root.exists()


def test_recursive_duplicate_phase_parity_is_fatal_before_output(
    tmp_path: Path,
    series_inputs: SeriesInputs,
) -> None:
    parity_root = tmp_path / "duplicate-parity"
    shutil.copytree(series_inputs.parity_root, parity_root)
    quartz_report = next(
        path
        for path in parity_root.rglob("reflector-parity-report.json")
        if "quartz" in path.parts
    )
    duplicate = parity_root / "other" / "nested" / "reflector-parity-report.json"
    duplicate.parent.mkdir(parents=True)
    shutil.copy2(quartz_report, duplicate)
    output_root = tmp_path / "must-not-exist"

    with pytest.raises(ValueError, match="exactly one.*quartz") as caught:
        render_phase_art_series(
            recipe_path=SERIES_RECIPE,
            parity_root=parity_root,
            ice_standard_reference=series_inputs.ice_standard_reference,
            output_root=output_root,
        )

    assert not output_root.exists()
    assert caught.value.phase_diagnostics["ice-ih"]["status"] == "passed"
    assert caught.value.phase_diagnostics["forsterite"]["status"] == "passed"
    assert caught.value.phase_diagnostics["quartz"] == {"status": "incomplete"}
    assert caught.value.phase_diagnostics["zircon"] == {"status": "incomplete"}
    assert caught.value.phase_diagnostics["titanite"] == {"status": "incomplete"}


def test_workflow_exports_series_contract() -> None:
    import kikuchi_lab.workflows as workflows
    from kikuchi_lab.workflows.phase_art_series import PhaseArtSeriesResult

    assert workflows.PhaseArtSeriesResult is PhaseArtSeriesResult
    assert workflows.render_phase_art_series is render_phase_art_series
