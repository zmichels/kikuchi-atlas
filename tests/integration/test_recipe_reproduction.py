from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.cli.main import main
from kikuchi_lab.workflows.final import (
    ReproductionMismatch,
    compare_final_bundles,
    render_final,
    reproduce_final,
)
from ..final_fixtures import canonical_master, fixture_projector, selected_proof


ROOT = Path(__file__).parents[2]


def _context(cwd: str) -> dict:
    return {
        "environment": {"python": "3.12", "cwd": cwd},
        "software": {
            "identities": {
                "kikuchi_lab": {"version": "0.1.0"},
                "ebsdsim": {"version": "0.1.8"},
                "kikuchipy": {"version": "0.13.0"},
            }
        },
        "hardware": {"adapter": "fixture GPU"},
    }


def test_identical_source_recipe_and_selection_reproduce_exact_bundle_products(
    tmp_path: Path,
) -> None:
    proof, selection = selected_proof(tmp_path)
    kwargs = {
        "master": canonical_master(),
        "recipe_path": ROOT / "recipes/gallery/forsterite-final.yml",
        "selection_path": selection,
        "proof_root": proof,
        "profile": "development",
        "projector": fixture_projector,
    }
    first = render_final(
        **kwargs,
        output_root=tmp_path / "first",
        execution_context=_context("/private/first"),
    )
    second = render_final(
        **kwargs,
        output_root=tmp_path / "second",
        execution_context=_context("/private/second"),
    )

    comparison = compare_final_bundles(first.path, second.path)
    assert comparison.equal is True
    assert comparison.source_comparison == "exact"
    assert comparison.cpu_processing_comparison == "exact"
    assert comparison.first_run_id == comparison.second_run_id == first.run_id == second.run_id
    assert comparison.first_manifest_identity == comparison.second_manifest_identity

    first_manifest = json.loads((first.path / "manifest.json").read_text())
    second_manifest = json.loads((second.path / "manifest.json").read_text())
    assert first_manifest["run_identity"] == second_manifest["run_identity"]
    for relative in (
        "products/projected.npy",
        "products/acquisition-corrected.npy",
        "products/scientific-clean.npy",
        "products/gallery-crisp.npy",
    ):
        np.testing.assert_array_equal(np.load(first.path / relative), np.load(second.path / relative))
    for relative in sorted(first_manifest["uint16_exports"]):
        assert (first.path / relative).read_bytes() == (second.path / relative).read_bytes()


def test_reproduction_rebuilds_from_manifest_snapshot_without_original_recipe_path(
    tmp_path: Path,
) -> None:
    proof, selection = selected_proof(tmp_path)
    original = render_final(
        master=canonical_master(),
        recipe_path=ROOT / "recipes/gallery/forsterite-final.yml",
        selection_path=selection,
        proof_root=proof,
        output_root=tmp_path / "original",
        profile="development",
        projector=fixture_projector,
        execution_context=_context("/private/original"),
    )

    reproduction = reproduce_final(
        original_run=original.path,
        master=canonical_master(),
        selection_path=selection,
        proof_root=proof,
        output_root=tmp_path / "reproduced",
        projector=fixture_projector,
        execution_context=_context("/private/reproduced"),
    )

    assert reproduction.run.run_id == original.run_id
    assert reproduction.comparison.equal is True
    assert reproduction.comparison.first_manifest_identity == (
        reproduction.comparison.second_manifest_identity
    )


def test_gpu_tolerance_is_explicit_and_never_weakens_cpu_processing_checks(
    tmp_path: Path,
) -> None:
    proof, selection = selected_proof(tmp_path)
    common = {
        "master": canonical_master(),
        "recipe_path": ROOT / "recipes/gallery/forsterite-final.yml",
        "selection_path": selection,
        "proof_root": proof,
        "profile": "development",
        "execution_context": _context("/private/same"),
    }
    exact = render_final(
        **common,
        output_root=tmp_path / "exact",
        projector=fixture_projector,
    )
    tolerant_exact = compare_final_bundles(
        exact.path,
        exact.path,
        source_mode="gpu-tolerant",
        source_atol=1e-5,
        source_rtol=1e-6,
    )
    assert tolerant_exact.equal is True
    assert tolerant_exact.source_comparison == "gpu-tolerant"
    assert tolerant_exact.cpu_processing_comparison == "exact"

    def perturbed_projector(**kwargs):
        product = fixture_projector(**kwargs)
        changed = np.array(product.intensity, copy=True)
        changed[0, 0] += np.float32(5e-6)
        from kikuchi_lab.model import DetectorPatternProduct

        metadata = product.metadata_dict()
        metadata.pop("array")

        return DetectorPatternProduct.from_array(
            changed,
            master_product_id=product.master_product_id,
            projection_recipe_id=product.projection_recipe_id,
            metadata=metadata,
        )

    perturbed = render_final(
        **common,
        output_root=tmp_path / "perturbed",
        projector=perturbed_projector,
    )
    with pytest.raises(ReproductionMismatch, match="CPU processing.*exact"):
        compare_final_bundles(
            exact.path,
            perturbed.path,
            source_mode="gpu-tolerant",
            source_atol=1e-5,
            source_rtol=1e-6,
        )


def test_gpu_tolerance_accepts_distinct_source_bytes_when_cpu_products_are_exact(
    tmp_path: Path,
) -> None:
    proof, selection = selected_proof(tmp_path)
    common = {
        "master": canonical_master(),
        "recipe_path": ROOT / "recipes/gallery/forsterite-final.yml",
        "selection_path": selection,
        "proof_root": proof,
        "profile": "development",
        "execution_context": _context("/private/same"),
    }
    baseline = render_final(
        **common,
        output_root=tmp_path / "baseline",
        projector=fixture_projector,
    )

    def one_ulp_projector(**kwargs):
        from kikuchi_lab.model import DetectorPatternProduct

        product = fixture_projector(**kwargs)
        changed = np.array(product.intensity, copy=True)
        changed[0, 0] = np.nextafter(changed[0, 0], np.float32(np.inf))
        metadata = product.metadata_dict()
        metadata.pop("array")
        return DetectorPatternProduct.from_array(
            changed,
            master_product_id=product.master_product_id,
            projection_recipe_id=product.projection_recipe_id,
            metadata=metadata,
        )

    variant = render_final(
        **common,
        output_root=tmp_path / "variant",
        projector=one_ulp_projector,
    )
    assert not np.array_equal(
        np.load(baseline.path / "products/projected.npy"),
        np.load(variant.path / "products/projected.npy"),
    )
    baseline_manifest = json.loads((baseline.path / "manifest.json").read_text())
    for relative in (
        "products/acquisition-corrected.npy",
        "products/scientific-clean.npy",
        "products/gallery-crisp.npy",
        *sorted(
            path
            for path in baseline_manifest["files"]
            if path.startswith("products/stages/") and path.endswith(".npy")
        ),
    ):
        np.testing.assert_array_equal(
            np.load(baseline.path / relative),
            np.load(variant.path / relative),
        )
    for relative in sorted(baseline_manifest["uint16_exports"]):
        if relative.startswith("products/projected."):
            continue
        assert (baseline.path / relative).read_bytes() == (variant.path / relative).read_bytes()

    with pytest.raises(ReproductionMismatch, match="exact source projection"):
        compare_final_bundles(baseline.path, variant.path)
    comparison = compare_final_bundles(
        baseline.path,
        variant.path,
        source_mode="gpu-tolerant",
        source_atol=1e-6,
        source_rtol=0.0,
    )
    assert comparison.equal is True
    assert comparison.first_run_id != comparison.second_run_id
    assert comparison.first_manifest_identity == comparison.second_manifest_identity
    assert comparison.cpu_processing_comparison == "exact"


def test_comparison_rejects_stage_omitted_from_both_inventories_even_if_manifests_match(
    tmp_path: Path,
) -> None:
    proof, selection = selected_proof(tmp_path)
    rendered = render_final(
        master=canonical_master(),
        recipe_path=ROOT / "recipes/gallery/forsterite-final.yml",
        selection_path=selection,
        proof_root=proof,
        output_root=tmp_path / "rendered",
        profile="development",
        projector=fixture_projector,
        execution_context=_context("/private/same"),
    )
    first = tmp_path / "first"
    second = tmp_path / "second"
    shutil.copytree(rendered.path, first)
    shutil.copytree(rendered.path, second)
    manifest = json.loads((first / "manifest.json").read_text())
    omitted = sorted(
        path
        for path in manifest["files"]
        if path.startswith("products/stages/") and path.endswith(".npy")
    )[0]
    manifest["files"].pop(omitted)
    for root in (first, second):
        (root / "manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
    (second / omitted).write_bytes((second / omitted).read_bytes() + b"undeclared drift")

    with pytest.raises(ReproductionMismatch, match="inventory|undeclared|tree|stage"):
        compare_final_bundles(first, second)


def test_comparison_rejects_symlink_or_extra_regular_file_outside_inventory(
    tmp_path: Path,
) -> None:
    proof, selection = selected_proof(tmp_path)
    rendered = render_final(
        master=canonical_master(),
        recipe_path=ROOT / "recipes/gallery/forsterite-final.yml",
        selection_path=selection,
        proof_root=proof,
        output_root=tmp_path / "rendered",
        profile="development",
        projector=fixture_projector,
        execution_context=_context("/private/same"),
    )
    (rendered.path / "undeclared.bin").write_bytes(b"extra")
    with pytest.raises(ReproductionMismatch, match="inventory|undeclared|tree"):
        compare_final_bundles(rendered.path, rendered.path)

    (rendered.path / "undeclared.bin").unlink()
    (rendered.path / "unsafe-link").symlink_to("manifest.json")
    with pytest.raises(ReproductionMismatch, match="symbolic|symlink|unsafe"):
        compare_final_bundles(rendered.path, rendered.path)


def test_comparison_rejects_declared_file_outside_canonical_bundle_schema(
    tmp_path: Path,
) -> None:
    proof, selection = selected_proof(tmp_path)
    rendered = render_final(
        master=canonical_master(),
        recipe_path=ROOT / "recipes/gallery/forsterite-final.yml",
        selection_path=selection,
        proof_root=proof,
        output_root=tmp_path / "rendered",
        profile="development",
        projector=fixture_projector,
        execution_context=_context("/private/same"),
    )
    extra = rendered.path / "declared-extra.bin"
    extra.write_bytes(b"declared but outside schema")
    manifest_path = rendered.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][extra.name] = {
        "bytes": extra.stat().st_size,
        "sha256": hashlib.sha256(extra.read_bytes()).hexdigest(),
    }
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    with pytest.raises(ReproductionMismatch, match="canonical|extra|schema"):
        compare_final_bundles(rendered.path, rendered.path)


def test_reproduce_final_cli_rebuilds_from_recorded_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from types import SimpleNamespace

    import kikuchi_lab.model as model_module
    import kikuchi_lab.workflows as workflow_module

    observed = {}
    monkeypatch.setattr(model_module, "load_master_product", lambda path: object())

    def fake_reproduce_final(**kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            run=SimpleNamespace(
                run_id="run-0123456789abcdef",
                path=tmp_path / "run-0123456789abcdef",
            ),
            comparison=SimpleNamespace(
                equal=True,
                source_comparison="exact",
                cpu_processing_comparison="exact",
                first_manifest_identity="manifest-comparison-a",
                second_manifest_identity="manifest-comparison-a",
            ),
        )

    monkeypatch.setattr(workflow_module, "reproduce_final", fake_reproduce_final)
    status = main(
        [
            "reproduce-final",
            "--run",
            "local/runs/run-original",
            "--selection",
            "local/decisions/example/selection.json",
            "--proof-root",
            "local/runs/proof-example",
            "--master-product",
            "local/master.npz",
            "--output",
            "local/reproductions",
        ]
    )

    assert status == 0
    assert observed["original_run"] == "local/runs/run-original"
    assert observed["proof_root"] == "local/runs/proof-example"
    report = json.loads(capsys.readouterr().out)
    assert report["reproduced"] is True
    assert report["cpu_processing_comparison"] == "exact"
