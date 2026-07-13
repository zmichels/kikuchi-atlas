from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import imageio.v3 as iio
import numpy as np
import pytest
import tifffile

from kikuchi_lab.orientations.selection import OrientationSelectionError
from kikuchi_lab.cli.main import main
from kikuchi_lab.workflows.final import (
    FinalSelectionError,
    load_final_recipe,
    render_final,
    validate_final_selection,
)
from ..final_fixtures import canonical_master, fixture_projector, selected_proof


ROOT = Path(__file__).parents[2]


def test_final_workflow_materializes_shared_correction_and_both_clarity_branches(
    tmp_path: Path,
) -> None:
    proof, selection = selected_proof(tmp_path)
    recipe = load_final_recipe(ROOT / "recipes/gallery/forsterite-final.yml")
    assert max(recipe.final_detector.shape) >= 2048

    result = render_final(
        master=canonical_master(),
        recipe_path=ROOT / "recipes/gallery/forsterite-final.yml",
        selection_path=selection,
        proof_root=proof,
        output_root=tmp_path / "runs",
        profile="development",
        projector=fixture_projector,
        execution_context={
            "environment": {"python": "3.12", "cwd": "/local/test-a"},
            "software": {
                "identities": {
                    "kikuchi_lab": {"version": "0.1.0"},
                    "ebsdsim": {"version": "0.1.8"},
                    "kikuchipy": {"version": "0.13.0"},
                }
            },
            "hardware": {"adapter": "fixture GPU"},
        },
    )

    bundle = result.path
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert result.profile == "development"
    assert result.not_final_quality is True
    assert manifest["processing_lineages"]["scientific"][0] == manifest[
        "processing_lineages"
    ]["gallery"][0]
    assert manifest["processing_lineages"]["scientific"][0]["name"] == (
        "background_divide"
    )
    assert manifest["products"]["projected"]["role"] == (
        "single_immutable_supersampled_projection"
    )
    assert manifest["content_registry"]["labels"]["projected"]["shape"] == [36, 48]
    assert manifest["content_registry"]["labels"]["acquisition-corrected"][
        "shape"
    ] == [36, 48]
    assert manifest["content_registry"]["labels"]["scientific-clean"]["shape"] == [
        18,
        24,
    ]
    assert manifest["content_registry"]["labels"]["gallery-crisp"]["shape"] == [
        18,
        24,
    ]
    assert np.load(bundle / "products/projected.npy").shape == (36, 48)
    assert np.load(bundle / "products/acquisition-corrected.npy").shape == (36, 48)
    assert np.load(bundle / "products/scientific-clean.npy").shape == (18, 24)
    assert np.load(bundle / "products/gallery-crisp.npy").shape == (18, 24)

    for stem in (
        "projected",
        "acquisition-corrected",
        "scientific-clean",
        "gallery-crisp",
    ):
        assert tifffile.imread(bundle / f"products/{stem}.tif").dtype == np.uint16
        assert iio.imread(bundle / f"products/{stem}.png").dtype == np.uint16
    assert iio.imread(bundle / "products/preview.png").dtype == np.uint8

    stages = manifest["content_registry"]["labels"]
    stage_labels = {key for key in stages if key.startswith("stage:")}
    assert len(stage_labels) >= 9
    lineage_outputs = {
        stage["output_id"]
        for lineage in manifest["processing_lineages"].values()
        for stage in lineage
    }
    assert {stages[label]["content_id"] for label in stage_labels} <= lineage_outputs

    decision = json.loads((bundle / "decisions/orientation.json").read_text())
    assert decision["content"]["selection_id"].startswith("orientation-selection-")
    assert decision["content"]["selected_candidate_id"] == "fo-011-phi1-045"
    assert decision["content"]["external_verification"]["proof_id"].startswith("proof-")
    assert decision["content"]["lineage"]["current_unique_leaf"] is True
    warnings = json.loads((bundle / "diagnostics/warnings.json").read_text())
    assert any(warning["code"] == "development_not_final_quality" for warning in warnings)
    assert any(warning["code"] == "descriptive_clarity_references_only" for warning in warnings)
    assert all("overlay" not in stage["name"] for lineage in manifest["processing_lineages"].values() for stage in lineage)
    metrics = json.loads((bundle / "diagnostics/metrics.json").read_text())
    scientific_high = metrics["scientific-clean"]["radial_frequency_energy"]["high"]
    gallery_high = metrics["gallery-crisp"]["radial_frequency_energy"]["high"]
    assert gallery_high <= scientific_high * 1.25
    assert not any(
        warning["code"] in {"excessive_high_frequency_gain", "clipping_fraction"}
        for warning in warnings
    )


def test_final_selection_gate_rejects_proof_manifest_and_superseded_record(
    tmp_path: Path,
) -> None:
    proof, selection = selected_proof(tmp_path)
    with pytest.raises(FinalSelectionError, match="awaiting.*selection"):
        validate_final_selection(proof / "manifest.json", proof_root=proof)

    from kikuchi_lab.orientations.selection import create_orientation_selection

    first = json.loads(selection.read_text())
    successor = create_orientation_selection(
        run=proof,
        candidate_id="fo-011-phi1-045",
        author="Z",
        rationale="Same scientific choice, clarified record.",
        selected_on="2026-07-14",
        output_root=selection.parent.parent,
        supersedes=first["selection_id"],
        supersede_reason="Clarify the durable selection record.",
    )
    with pytest.raises(FinalSelectionError, match="superseded|current unique leaf"):
        validate_final_selection(selection, proof_root=proof)
    validated = validate_final_selection(successor.selection_path, proof_root=proof)
    assert validated.selection_id == successor.selection_id
    assert validated.current_unique_leaf is True


def test_final_selection_gate_requires_external_proof_verification(tmp_path: Path) -> None:
    proof, selection = selected_proof(tmp_path)
    (proof / "candidates/fo-011-phi1-045/raw.bin").write_bytes(b"tampered")

    with pytest.raises((FinalSelectionError, OrientationSelectionError), match="proof|tree"):
        validate_final_selection(selection, proof_root=proof)


def test_render_final_cli_requires_and_forwards_explicit_selection_and_proof_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import kikuchi_lab.model as model_module
    import kikuchi_lab.workflows as workflow_module

    observed = {}
    master = object()
    monkeypatch.setattr(model_module, "load_master_product", lambda path: master)

    def fake_render_final(**kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            run_id="run-0123456789abcdef",
            path=tmp_path / "run-0123456789abcdef",
            profile="development",
            selection_id="orientation-selection-0123456789abcdef",
            not_final_quality=True,
            elapsed_seconds=1.25,
        )

    monkeypatch.setattr(workflow_module, "render_final", fake_render_final)
    status = main(
        [
            "render-final",
            "--recipe",
            "recipes/gallery/forsterite-final.yml",
            "--selection",
            "local/decisions/example/selection.json",
            "--proof-root",
            "local/runs/proof-example",
            "--master-product",
            "local/master.npz",
            "--output",
            "local/runs",
            "--profile",
            "development",
        ]
    )

    assert status == 0
    assert observed["master"] is master
    assert observed["selection_path"] == "local/decisions/example/selection.json"
    assert observed["proof_root"] == "local/runs/proof-example"
    assert json.loads(capsys.readouterr().out)["not_final_quality"] is True
