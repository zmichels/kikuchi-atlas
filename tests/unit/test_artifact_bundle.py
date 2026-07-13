from __future__ import annotations

import hashlib
import json
from pathlib import Path

import imageio.v3 as iio
import numpy as np
import pytest
import tifffile

from kikuchi_lab.artifacts import (
    ArtifactBundleRequest,
    BundleExistsError,
    FloatProduct,
    PartialBundleError,
    write_artifact_bundle,
)
from kikuchi_lab.model.identity import canonical_json, stable_id


def _request(*, elapsed: float = 1.25, created_at: str = "2026-07-12T12:00:00Z"):
    base = np.arange(48, dtype=np.float32).reshape(6, 8)
    projected = FloatProduct("detector-projected", base)
    acquisition_corrected = FloatProduct("stage-background", base + 1)
    normalized = FloatProduct("stage-normalize", base / 47)
    return ArtifactBundleRequest(
        source={"source_id": "source-abc", "sha256": "a" * 64, "created_at": created_at},
        environment={"python": "3.12", "cwd": "/private/local/kikuchi"},
        software={
            "identities": {
                "kikuchi_lab": {"version": "0.1.0"},
                "ebsdsim": {"version": "0.1.8"},
            }
        },
        hardware={"adapter": "Apple M2", "captured_at": created_at},
        recipes={
            "simulation": {
                "recipe_id": "recipe-sim",
                "recipe_sha256": "b" * 64,
                "voltage_kv": 20.0,
            },
            "projection": {
                "recipe_id": "recipe-proj",
                "recipe_sha256": "c" * 64,
                "geometry_id": "geometry-detector-1",
                "shape": [6, 8],
            },
            "scientific-clean": {
                "recipe_id": "recipe-science",
                "recipe_sha256": "d" * 64,
            },
            "gallery-crisp": {
                "recipe_id": "recipe-gallery",
                "recipe_sha256": "e" * 64,
            },
        },
        master_metadata={
            "product_id": "master-abc",
            "array_sha256": "f" * 64,
            "phase": "forsterite",
        },
        orientation_candidates={
            "candidate_set_id": "candidate-set-1",
            "candidate_ids": ["orientation-1"],
        },
        projected=projected,
        acquisition_corrected=acquisition_corrected,
        stages={"normalize": normalized},
        stage_lineage=(
            {
                "name": "background_divide",
                "input_id": projected.content_id,
                "output_id": acquisition_corrected.content_id,
            },
            {
                "name": "robust_normalize",
                "input_id": acquisition_corrected.content_id,
                "output_id": normalized.content_id,
            },
        ),
        scientific_clean=FloatProduct("processed-science", base / 47),
        gallery_crisp=FloatProduct("processed-gallery", np.flipud(base) / 47),
        warnings=[{"code": "example", "message": "test evidence"}],
        timings={"elapsed_seconds": elapsed, "captured_at": created_at},
        resources={"peak_rss_mb": 42.0, "sampled_at": created_at},
        orientation_decision={
            "decision_id": "decision-orientation-1",
            "selected": "orientation-1",
            "decided_at": created_at,
        },
        decision_links={"orientation": "decision-orientation-1"},
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_bundle_writes_complete_canonical_inventory_and_image_formats(tmp_path: Path) -> None:
    result = write_artifact_bundle(tmp_path, _request())
    bundle = result.path
    expected = {
        "provenance/source.json",
        "provenance/environment.json",
        "provenance/software.json",
        "provenance/hardware.json",
        "recipes/simulation.json",
        "recipes/projection.json",
        "recipes/scientific-clean.json",
        "recipes/gallery-crisp.json",
        "metadata/master-pattern.json",
        "metadata/orientation-candidates.json",
        "metadata/processing-lineage.json",
        "products/projected.npy",
        "products/acquisition-corrected.npy",
        "products/stages/normalize.npy",
        "products/stages/normalize.tif",
        "products/scientific-clean.npy",
        "products/gallery-crisp.npy",
        "products/scientific-clean.tif",
        "products/gallery-crisp.tif",
        "products/scientific-clean.png",
        "products/gallery-crisp.png",
        "products/preview.png",
        "diagnostics/metrics.json",
        "diagnostics/warnings.json",
        "diagnostics/timings.json",
        "diagnostics/resources.json",
        "decisions/orientation.json",
        "decisions/links.json",
    }
    actual = {
        str(path.relative_to(bundle))
        for path in bundle.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    assert actual == expected

    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest_path.read_text() == canonical_json(manifest)
    assert set(manifest["files"]) == expected
    assert "manifest.json" not in manifest["files"]
    for relative, record in manifest["files"].items():
        assert record["sha256"] == _sha256(bundle / relative)
        assert record["bytes"] == (bundle / relative).stat().st_size
    assert result.manifest_sha256 == _sha256(manifest_path)

    for relative in (
        "products/stages/normalize.tif",
        "products/scientific-clean.tif",
        "products/gallery-crisp.tif",
    ):
        assert tifffile.imread(bundle / relative).dtype == np.uint16
    for relative in ("products/scientific-clean.png", "products/gallery-crisp.png"):
        assert iio.imread(bundle / relative).dtype == np.uint16
    assert iio.imread(bundle / "products/preview.png").dtype == np.uint8

    for relative, quantization in manifest["uint16_exports"].items():
        assert relative.endswith((".tif", ".png"))
        assert quantization["source_product_id"]
        assert set(quantization) == {
            "source_product_id",
            "scale",
            "offset",
            "black_point",
            "white_point",
            "clipping_below_black",
            "clipping_above_white",
        }
    assert manifest["products"]["acquisition_corrected"]["role"] == (
        "background_model_corrected_before_aesthetic_processing"
    )
    assert manifest["run_identity_schema"]["schema_version"] == 1
    assert stable_id("run", manifest["run_identity"]) == result.run_id
    assert manifest["processing_stage_lineage"][0]["name"] == "background_divide"
    assert manifest["processing_stage_lineage"][0]["output_id"] == (
        _request().acquisition_corrected.content_id
    )
    assert manifest["comparison_exclusions"] == {
        "json_fields": ["**/captured_at", "**/created_at", "**/decided_at"],
        "json_documents": [
            "diagnostics/timings.json#/**",
            "diagnostics/resources.json#/**",
        ],
        "value_rules": [{"kind": "absolute_local_path", "scope": "**"}],
        "external_values": ["manifest_sha256"],
    }


def test_bundle_identity_excludes_wall_time_resource_measurements_and_local_paths(
    tmp_path: Path,
) -> None:
    first = write_artifact_bundle(tmp_path / "first", _request())
    changed = _request(elapsed=999.0, created_at="2030-01-01T00:00:00Z")
    changed = ArtifactBundleRequest(
        **{
            **changed.__dict__,
            "environment": {"python": "3.12", "cwd": "/another/local/path"},
            "resources": {"peak_rss_mb": 9999.0, "sampled_at": "2030-01-01T00:00:00Z"},
        }
    )
    second = write_artifact_bundle(tmp_path / "second", changed)

    assert first.run_id == second.run_id


def test_bundle_identity_ignores_adversarial_nested_paths_and_retrieval_times(tmp_path: Path) -> None:
    original = _request()
    changed = _request()
    changed = ArtifactBundleRequest(
        **{
            **changed.__dict__,
            "source": {
                **changed.source,
                "provenance": {
                    "artifact_location": "../../other/source.cif",
                    "retrieved_at": "2099-01-01T00:00:00Z",
                },
            },
            "master_metadata": {
                **changed.master_metadata,
                "cache": {
                    "artifact_location": "/tmp/other/master.npz",
                    "generated_at": "2099-01-01T00:00:00Z",
                },
            },
            "recipes": {
                name: {
                    **recipe,
                    "evidence": {
                        "artifact_location": f"../recipes/{name}.json",
                        "retrieved_at": "2099-01-01T00:00:00Z",
                    },
                }
                for name, recipe in changed.recipes.items()
            },
            "software": {
                **changed.software,
                "discovery": {
                    "artifact_location": "/Users/someone/.venv",
                    "generated_at": "2099-01-01T00:00:00Z",
                },
            },
        }
    )

    first = write_artifact_bundle(tmp_path / "first", original)
    second = write_artifact_bundle(tmp_path / "second", changed)

    assert first.run_id == second.run_id
    identity_text = canonical_json(
        json.loads((second.path / "manifest.json").read_text())["run_identity"]
    )
    assert "artifact_location" not in identity_text
    assert "retrieved_at" not in identity_text
    assert "generated_at" not in identity_text


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("source", {"source_id": "source-abc", "sha256": "9" * 64}),
        (
            "software",
            {"identities": {"kikuchi_lab": {"version": "0.2.0"}, "ebsdsim": {"version": "0.1.8"}}},
        ),
    ],
)
def test_bundle_identity_changes_for_whitelisted_scientific_identity_fields(
    tmp_path: Path, field: str, replacement: object
) -> None:
    original = _request()
    changed = ArtifactBundleRequest(**{**original.__dict__, field: replacement})

    first = write_artifact_bundle(tmp_path / "first", original)
    second = write_artifact_bundle(tmp_path / "second", changed)

    assert first.run_id != second.run_id


def test_bundle_identity_changes_for_recipe_checksum_and_geometry_id(tmp_path: Path) -> None:
    original = _request()
    changed_recipes = {name: dict(recipe) for name, recipe in original.recipes.items()}
    changed_recipes["projection"]["recipe_sha256"] = "8" * 64
    changed_recipes["projection"]["geometry_id"] = "geometry-detector-2"
    changed = ArtifactBundleRequest(**{**original.__dict__, "recipes": changed_recipes})

    first = write_artifact_bundle(tmp_path / "first", original)
    second = write_artifact_bundle(tmp_path / "second", changed)

    assert first.run_id != second.run_id


@pytest.mark.parametrize(
    "failure", ["missing", "wrong_name", "unrelated_output", "unknown_before_background"]
)
def test_bundle_rejects_missing_wrong_or_unrelated_background_lineage(
    tmp_path: Path, failure: str
) -> None:
    request = _request()
    lineage = list(request.stage_lineage)
    if failure == "missing":
        lineage = lineage[1:]
    elif failure == "wrong_name":
        lineage[0] = {**lineage[0], "name": "local_contrast"}
    else:
        if failure == "unrelated_output":
            lineage[0] = {**lineage[0], "output_id": request.projected.content_id}
        else:
            lineage.insert(
                0,
                {
                    "name": "opaque_preprocess",
                    "input_id": request.projected.content_id,
                    "output_id": request.projected.content_id,
                },
            )
    malformed = ArtifactBundleRequest(**{**request.__dict__, "stage_lineage": tuple(lineage)})

    with pytest.raises(ValueError, match="background|lineage|acquisition"):
        write_artifact_bundle(tmp_path, malformed)


def test_bundle_rejects_acquisition_array_unrelated_to_recorded_background_output(
    tmp_path: Path,
) -> None:
    request = _request()
    unrelated = FloatProduct("stage-background", request.acquisition_corrected.intensity + 0.25)
    malformed = ArtifactBundleRequest(
        **{**request.__dict__, "acquisition_corrected": unrelated}
    )

    with pytest.raises(ValueError, match="acquisition-corrected"):
        write_artifact_bundle(tmp_path, malformed)


def test_bundle_identity_changes_when_float_bytes_change_despite_reused_label(tmp_path: Path) -> None:
    first_request = _request()
    changed_request = _request()
    changed_gallery = changed_request.gallery_crisp.intensity.copy()
    changed_gallery[0, 0] += 0.125
    changed_request = ArtifactBundleRequest(
        **{
            **changed_request.__dict__,
            "gallery_crisp": FloatProduct(
                changed_request.gallery_crisp.product_id,
                changed_gallery,
            ),
        }
    )

    first = write_artifact_bundle(tmp_path / "first", first_request)
    changed = write_artifact_bundle(tmp_path / "changed", changed_request)

    assert first.run_id != changed.run_id


def test_bundle_refuses_completed_and_partial_runs_and_resume_clean_preserves_evidence(
    tmp_path: Path,
) -> None:
    first = write_artifact_bundle(tmp_path, _request())
    with pytest.raises(BundleExistsError):
        write_artifact_bundle(tmp_path, _request())

    first.path.rename(tmp_path / f"{first.run_id}.saved")
    partial = tmp_path / f"{first.run_id}.partial"
    partial.mkdir()
    (partial / "evidence.txt").write_text("stale")
    with pytest.raises(PartialBundleError):
        write_artifact_bundle(tmp_path, _request())

    resumed = write_artifact_bundle(
        tmp_path,
        _request(),
        resume_clean=True,
        abandoned_at="20260712T120000Z",
    )
    abandoned = tmp_path / f"{first.run_id}.partial.20260712T120000Z.abandoned"
    assert (abandoned / "evidence.txt").read_text() == "stale"
    assert resumed.path.is_dir()


def test_malformed_request_leaves_no_partial_bundle(tmp_path: Path) -> None:
    request = _request()
    malformed = ArtifactBundleRequest(**{**request.__dict__, "warnings": [float("nan")]})

    with pytest.raises((TypeError, ValueError)):
        write_artifact_bundle(tmp_path, malformed)

    assert list(tmp_path.glob("*.partial")) == []
