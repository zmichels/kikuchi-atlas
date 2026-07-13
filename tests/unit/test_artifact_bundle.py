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


def _identified(kind: str, content: dict, *, id_key: str, sha_key: str) -> dict:
    checksum = hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()
    return {
        "content": content,
        id_key: f"{kind}-{checksum[:16]}",
        sha_key: checksum,
    }


def _request(*, elapsed: float = 1.25, created_at: str = "2026-07-12T12:00:00Z"):
    base = np.arange(48, dtype=np.float32).reshape(6, 8)
    projected = FloatProduct("detector-projected", base)
    acquisition_corrected = FloatProduct("stage-background", base + 1)
    normalized = FloatProduct("stage-normalize", base / 47)
    gallery = FloatProduct("processed-gallery", np.flipud(base) / 47)
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
            "simulation": _identified(
                "recipe",
                {"voltage_kv": 20.0, "halfw": 64},
                id_key="recipe_id",
                sha_key="recipe_sha256",
            ),
            "projection": {
                **_identified(
                    "recipe",
                    {"shape": [6, 8], "pc": [0.5, 0.5, 0.6]},
                    id_key="recipe_id",
                    sha_key="recipe_sha256",
                ),
                "geometry_id": stable_id("geometry", {"shape": [6, 8], "pc": [0.5, 0.5, 0.6]}),
            },
            "scientific-clean": _identified(
                "recipe",
                {"stages": ["background_divide", "robust_normalize"]},
                id_key="recipe_id",
                sha_key="recipe_sha256",
            ),
            "gallery-crisp": _identified(
                "recipe",
                {"stages": ["background_divide", "robust_normalize", "gallery_crisp_finish"]},
                id_key="recipe_id",
                sha_key="recipe_sha256",
            ),
        },
        master_metadata={
            "product_id": "master-abc",
            "array_sha256": "f" * 64,
            "phase": "forsterite",
        },
        orientation_candidates=_identified(
            "candidate-set",
            {"candidate_ids": ["orientation-1"]},
            id_key="candidate_set_id",
            sha_key="candidate_set_sha256",
        ),
        projected=projected,
        acquisition_corrected=acquisition_corrected,
        stages={"normalize": normalized},
        scientific_lineage=(
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
        gallery_lineage=(
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
            {
                "name": "gallery_crisp_finish",
                "input_id": normalized.content_id,
                "output_id": gallery.content_id,
            },
        ),
        scientific_clean=FloatProduct("processed-science", base / 47),
        gallery_crisp=gallery,
        warnings=[{"code": "example", "message": "test evidence"}],
        timings={"elapsed_seconds": elapsed, "captured_at": created_at},
        resources={"peak_rss_mb": 42.0, "sampled_at": created_at},
        orientation_decision={
            **_identified(
                "decision",
                {"selected_candidate_id": "orientation-1", "criterion": "band geometry"},
                id_key="decision_id",
                sha_key="decision_sha256",
            ),
            "decided_at": created_at,
        },
        decision_links={
            "orientation": _identified(
                "decision",
                {"selected_candidate_id": "orientation-1", "criterion": "band geometry"},
                id_key="decision_id",
                sha_key="decision_sha256",
            )["decision_id"]
        },
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
        "products/projected.tif",
        "products/projected.png",
        "products/acquisition-corrected.npy",
        "products/acquisition-corrected.tif",
        "products/acquisition-corrected.png",
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
    assert manifest["schema_version"] == 2
    assert manifest_path.read_text() == canonical_json(manifest)
    assert set(manifest["files"]) == expected
    assert "manifest.json" not in manifest["files"]
    for relative, record in manifest["files"].items():
        assert record["sha256"] == _sha256(bundle / relative)
        assert record["bytes"] == (bundle / relative).stat().st_size
    assert result.manifest_sha256 == _sha256(manifest_path)

    for relative in (
        "products/projected.tif",
        "products/acquisition-corrected.tif",
        "products/stages/normalize.tif",
        "products/scientific-clean.tif",
        "products/gallery-crisp.tif",
    ):
        assert tifffile.imread(bundle / relative).dtype == np.uint16
    for relative in (
        "products/projected.png",
        "products/acquisition-corrected.png",
        "products/scientific-clean.png",
        "products/gallery-crisp.png",
    ):
        assert iio.imread(bundle / relative).dtype == np.uint16
    assert iio.imread(bundle / "products/preview.png").dtype == np.uint8

    for relative, quantization in manifest["uint16_exports"].items():
        assert relative.endswith((".tif", ".png"))
        assert quantization["source_product_id"]
        assert set(quantization) == {
            "label",
            "source_product_id",
            "source_content_id",
            "source_array_sha256",
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
    assert manifest["products"]["projected"]["role"] == (
        "single_immutable_supersampled_projection"
    )
    assert manifest["run_identity_schema"]["schema_version"] == 3
    assert stable_id("run", manifest["run_identity"]) == result.run_id
    assert set(manifest["run_identity"]["orientation_candidate_set"]) == {
        "candidate_set_id",
        "candidate_set_sha256",
    }
    assert set(manifest["run_identity"]["orientation_decision"]) == {
        "decision_id",
        "decision_sha256",
    }
    assert set(manifest["processing_lineages"]) == {"scientific", "gallery"}
    assert manifest["run_identity"]["processing_lineages"] == manifest["processing_lineages"]
    assert json.loads((bundle / "metadata/processing-lineage.json").read_text()) == manifest[
        "processing_lineages"
    ]
    assert manifest["processing_lineages"]["scientific"][0]["name"] == "background_divide"
    assert manifest["processing_lineages"]["gallery"][0]["output_id"] == (
        _request().acquisition_corrected.content_id
    )
    assert manifest["processing_lineages"]["scientific"][-1]["output_id"] == (
        _request().scientific_clean.content_id
    )
    assert manifest["processing_lineages"]["gallery"][-1]["output_id"] == (
        _request().gallery_crisp.content_id
    )
    assert set(manifest["content_registry"]["labels"]) == {
        "projected",
        "acquisition-corrected",
        "stage:normalize",
        "scientific-clean",
        "gallery-crisp",
    }
    for path, quantization in manifest["uint16_exports"].items():
        registry = manifest["content_registry"]["labels"][quantization["label"]]
        assert quantization["source_content_id"] == registry["content_id"], path
        assert quantization["source_array_sha256"] == registry["array_sha256"], path
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
    content = {"shape": [6, 8], "pc": [0.52, 0.5, 0.6]}
    changed_recipes["projection"] = {
        **_identified(
            "recipe",
            content,
            id_key="recipe_id",
            sha_key="recipe_sha256",
        ),
        "geometry_id": stable_id("geometry", content),
    }
    changed = ArtifactBundleRequest(**{**original.__dict__, "recipes": changed_recipes})

    first = write_artifact_bundle(tmp_path / "first", original)
    second = write_artifact_bundle(tmp_path / "second", changed)

    assert first.run_id != second.run_id


@pytest.mark.parametrize("target", ["recipe", "candidates", "decision"])
def test_bundle_rejects_stale_asserted_content_identities(tmp_path: Path, target: str) -> None:
    request = _request()
    changes: dict[str, object] = {}
    if target == "recipe":
        recipes = {name: dict(recipe) for name, recipe in request.recipes.items()}
        recipes["simulation"]["content"] = {
            **recipes["simulation"]["content"],
            "voltage_kv": 30.0,
        }
        changes["recipes"] = recipes
    elif target == "candidates":
        changes["orientation_candidates"] = {
            **request.orientation_candidates,
            "content": {"candidate_ids": ["orientation-2"]},
        }
    else:
        changes["orientation_decision"] = {
            **request.orientation_decision,
            "content": {
                **request.orientation_decision["content"],
                "selected_candidate_id": "orientation-2",
            },
        }
    malformed = ArtifactBundleRequest(**{**request.__dict__, **changes})

    with pytest.raises(ValueError, match="checksum|identity|candidate|decision|recipe"):
        write_artifact_bundle(tmp_path, malformed)


def test_bundle_rejects_selection_outside_candidates_and_wrong_decision_link(tmp_path: Path) -> None:
    request = _request()
    decision = _identified(
        "decision",
        {"selected_candidate_id": "orientation-2", "criterion": "band geometry"},
        id_key="decision_id",
        sha_key="decision_sha256",
    )
    outside = ArtifactBundleRequest(
        **{
            **request.__dict__,
            "orientation_decision": decision,
            "decision_links": {"orientation": decision["decision_id"]},
        }
    )
    with pytest.raises(ValueError, match="candidate set"):
        write_artifact_bundle(tmp_path / "outside", outside)

    wrong_link = ArtifactBundleRequest(
        **{**request.__dict__, "decision_links": {"orientation": "decision-deadbeefdeadbeef"}}
    )
    with pytest.raises(ValueError, match="decision link"):
        write_artifact_bundle(tmp_path / "link", wrong_link)


def test_correct_content_identity_changes_change_run_id(tmp_path: Path) -> None:
    original = _request()
    recipes = {name: dict(recipe) for name, recipe in original.recipes.items()}
    recipes["simulation"] = _identified(
        "recipe",
        {**recipes["simulation"]["content"], "voltage_kv": 30.0},
        id_key="recipe_id",
        sha_key="recipe_sha256",
    )
    changed = ArtifactBundleRequest(**{**original.__dict__, "recipes": recipes})

    first = write_artifact_bundle(tmp_path / "first", original)
    second = write_artifact_bundle(tmp_path / "second", changed)

    assert first.run_id != second.run_id


@pytest.mark.parametrize("target", ["candidates", "selection"])
def test_correct_candidate_or_selection_content_changes_run_id(
    tmp_path: Path, target: str
) -> None:
    original = _request()
    candidate_content = {"candidate_ids": ["orientation-1", "orientation-2"]}
    candidates = _identified(
        "candidate-set",
        candidate_content,
        id_key="candidate_set_id",
        sha_key="candidate_set_sha256",
    )
    changes: dict[str, object] = {"orientation_candidates": candidates}
    if target == "selection":
        decision = _identified(
            "decision",
            {"selected_candidate_id": "orientation-2", "criterion": "band geometry"},
            id_key="decision_id",
            sha_key="decision_sha256",
        )
        changes["orientation_decision"] = decision
        changes["decision_links"] = {"orientation": decision["decision_id"]}
    changed = ArtifactBundleRequest(**{**original.__dict__, **changes})

    first = write_artifact_bundle(tmp_path / "first", original)
    second = write_artifact_bundle(tmp_path / "second", changed)

    assert first.run_id != second.run_id


def test_bundle_identity_includes_each_ordered_processing_branch(tmp_path: Path) -> None:
    original = _request()
    changed_lineage = list(original.gallery_lineage)
    changed_lineage[-1] = {**changed_lineage[-1], "name": "alternate_gallery_finish"}
    changed = ArtifactBundleRequest(
        **{**original.__dict__, "gallery_lineage": tuple(changed_lineage)}
    )

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
    lineage = list(request.scientific_lineage)
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
    malformed = ArtifactBundleRequest(
        **{**request.__dict__, "scientific_lineage": tuple(lineage)}
    )

    with pytest.raises(ValueError, match="background|lineage|acquisition"):
        write_artifact_bundle(tmp_path, malformed)


@pytest.mark.parametrize(
    "failure",
    ["arbitrary_final", "wrong_terminal", "divergent_background", "disconnected_root"],
)
def test_bundle_rejects_invalid_scientific_or_gallery_branch_terminals(
    tmp_path: Path, failure: str
) -> None:
    request = _request()
    changes: dict[str, object] = {}
    if failure == "arbitrary_final":
        changes["gallery_crisp"] = FloatProduct(
            request.gallery_crisp.product_id,
            np.fliplr(request.gallery_crisp.intensity),
        )
    elif failure == "wrong_terminal":
        lineage = list(request.gallery_lineage)
        lineage[-1] = {**lineage[-1], "output_id": request.scientific_clean.content_id}
        changes["gallery_lineage"] = tuple(lineage)
    elif failure == "divergent_background":
        lineage = list(request.gallery_lineage)
        divergent = request.gallery_crisp.content_id
        lineage[0] = {**lineage[0], "output_id": divergent}
        lineage[1] = {**lineage[1], "input_id": divergent}
        changes["gallery_lineage"] = tuple(lineage)
    else:
        lineage = list(request.scientific_lineage)
        lineage[0] = {**lineage[0], "input_id": request.gallery_crisp.content_id}
        changes["scientific_lineage"] = tuple(lineage)
    malformed = ArtifactBundleRequest(**{**request.__dict__, **changes})

    with pytest.raises(ValueError, match="scientific|gallery|background|root|terminal"):
        write_artifact_bundle(tmp_path, malformed)


def test_bundle_rejects_exported_intermediate_outside_both_branches(tmp_path: Path) -> None:
    request = _request()
    unattached = FloatProduct("stage-unattached", request.projected.intensity + 7.0)
    malformed = ArtifactBundleRequest(
        **{**request.__dict__, "stages": {**request.stages, "unattached": unattached}}
    )

    with pytest.raises(ValueError, match="both processing branches"):
        write_artifact_bundle(tmp_path, malformed)


def test_bundle_rejects_fabricated_but_connected_lineage_node(tmp_path: Path) -> None:
    request = _request()
    fabricated = "image-deadbeefdeadbeef"
    lineage = list(request.gallery_lineage)
    lineage.insert(
        -1,
        {
            "name": "fabricated_intermediate",
            "input_id": lineage[-1]["input_id"],
            "output_id": fabricated,
        },
    )
    lineage[-1] = {**lineage[-1], "input_id": fabricated}
    malformed = ArtifactBundleRequest(
        **{**request.__dict__, "gallery_lineage": tuple(lineage)}
    )

    with pytest.raises(ValueError, match="materialized|registry|retained"):
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
    changed_product = FloatProduct(changed_request.gallery_crisp.product_id, changed_gallery)
    changed_lineage = list(changed_request.gallery_lineage)
    changed_lineage[-1] = {**changed_lineage[-1], "output_id": changed_product.content_id}
    changed_request = ArtifactBundleRequest(
        **{
            **changed_request.__dict__,
            "gallery_crisp": changed_product,
            "gallery_lineage": tuple(changed_lineage),
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


def test_bundle_rejects_float_product_axis_below_two_before_staging(tmp_path: Path) -> None:
    request = _request()
    malformed = ArtifactBundleRequest(
        **{
            **request.__dict__,
            "projected": FloatProduct("detector-projected", np.zeros((1, 8), dtype=np.float32)),
        }
    )

    with pytest.raises(ValueError, match="axis.*at least 2"):
        write_artifact_bundle(tmp_path, malformed)
    assert list(tmp_path.glob("*.partial")) == []


def test_bundle_fsyncs_nested_directories_bottom_up_before_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import kikuchi_lab.artifacts.bundle as bundle_module

    calls: list[Path] = []
    monkeypatch.setattr(bundle_module, "_fsync_directory", lambda path: calls.append(Path(path)))

    result = write_artifact_bundle(tmp_path, _request())

    partial = tmp_path / f"{result.run_id}.partial"
    assert calls[-1] == tmp_path
    assert partial in calls
    partial_index = calls.index(partial)
    nested = [path for path in calls[:partial_index] if partial in path.parents]
    assert nested
    assert all(len(left.parts) >= len(right.parts) for left, right in zip(nested, nested[1:]))
