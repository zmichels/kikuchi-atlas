"""Selection-gated final rendering with explicit, reproducible clarity branches."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from kikuchi_lab.artifacts import (
    ArtifactBundleRequest,
    FloatProduct,
    write_artifact_bundle,
)
from kikuchi_lab.model import DetectorPatternProduct, DetectorRecipe, MasterPatternProduct
from kikuchi_lab.model.identity import canonical_json, plain_data, stable_id
from kikuchi_lab.model.recipes import Orientation
from kikuchi_lab.orientations.selection import (
    OrientationSelectionError,
    load_orientation_selection,
    verify_orientation_selection,
)
from kikuchi_lab.processing.stages import STAGE_FUNCTIONS, StageResult
from kikuchi_lab.projection import project_with_kikuchipy


Projector = Callable[..., DetectorPatternProduct]


class FinalRecipeError(ValueError):
    """The final-render recipe is malformed or violates the milestone contract."""


class FinalSelectionError(ValueError):
    """The supplied human decision is absent, invalid, or no longer current."""


class ReproductionMismatch(AssertionError):
    """Two final bundles violate the declared reproduction policy."""


@dataclass(frozen=True)
class FinalRecipe:
    schema_version: int
    name: str
    intent: str
    final_minimum_long_edge_px: int
    final_detector: DetectorRecipe
    source_contract: Mapping[str, Any]
    energy_kev: float
    reference_native_shape: tuple[int, int]
    reference_supersampled_shape: tuple[int, int]
    acquisition: Mapping[str, Any]
    scientific: tuple[Mapping[str, Any], ...]
    gallery: tuple[Mapping[str, Any], ...]
    clarity: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "intent": self.intent,
            "quality_contract": {
                "final_minimum_long_edge_px": self.final_minimum_long_edge_px,
                "final_profile": "production-target",
                "development_profile": "selected-proof-geometry",
            },
            "source_contract": plain_data(self.source_contract),
            "energy_kev": self.energy_kev,
            "final_detector": _detector_constructor_dict(self.final_detector),
            "processing": {
                "pixel_parameter_scaling": "linear-from-reference-shape",
                "reference_native_shape": list(self.reference_native_shape),
                "reference_supersampled_shape": list(self.reference_supersampled_shape),
                "acquisition": plain_data(self.acquisition),
                "scientific": plain_data(self.scientific),
                "gallery": plain_data(self.gallery),
            },
            "clarity": plain_data(self.clarity),
        }


@dataclass(frozen=True)
class ValidatedFinalSelection:
    selection_id: str
    proof_id: str
    candidate_id: str
    orientation: Orientation
    selected_detector: DetectorRecipe
    record: Mapping[str, Any]
    proof_root: Path
    current_unique_leaf: bool = True


@dataclass(frozen=True)
class FinalRunResult:
    run_id: str
    path: Path
    manifest_sha256: str
    profile: str
    selection_id: str
    not_final_quality: bool
    elapsed_seconds: float


@dataclass(frozen=True)
class ReproductionComparison:
    equal: bool
    first_run_id: str
    second_run_id: str
    first_manifest_identity: str
    second_manifest_identity: str
    source_comparison: str
    source_atol: float
    source_rtol: float
    cpu_processing_comparison: str = "exact"


@dataclass(frozen=True)
class FinalReproductionResult:
    run: FinalRunResult
    comparison: ReproductionComparison


def _detector_constructor_dict(detector: DetectorRecipe) -> dict[str, Any]:
    return {
        "shape": list(detector.shape),
        "pcx": detector.pcx,
        "pcy": detector.pcy,
        "pcz": detector.pcz,
        "pc_convention": detector.pc_convention,
        "sample_tilt_deg": detector.sample_tilt_deg,
        "detector_tilt_deg": detector.detector_tilt_deg,
        "detector_azimuth_deg": detector.detector_azimuth_deg,
        "detector_twist_deg": detector.detector_twist_deg,
        "pixel_size_um": detector.pixel_size_um,
        "binning": detector.binning,
        "supersampling": detector.supersampling,
    }


def _required_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FinalRecipeError(f"final recipe {field} must be an object")
    return value


def _positive_shape(value: Any, field: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(type(item) is not int or item <= 0 for item in value)
    ):
        raise FinalRecipeError(f"final recipe {field} must contain two positive integers")
    return value[0], value[1]


def _stage_record(value: Any, field: str) -> dict[str, Any]:
    stage = _required_mapping(value, field)
    if set(stage) != {"name", "parameters"}:
        raise FinalRecipeError(f"final recipe {field} requires only name and parameters")
    name = stage.get("name")
    parameters = stage.get("parameters")
    if not isinstance(name, str) or name not in STAGE_FUNCTIONS:
        raise FinalRecipeError(f"final recipe {field} names an unsupported processing stage")
    if "overlay" in name:
        raise FinalRecipeError("final recipe cannot contain hidden line overlays")
    if not isinstance(parameters, dict):
        raise FinalRecipeError(f"final recipe {field} parameters must be an object")
    plain_data(parameters)
    return {"name": name, "parameters": parameters}


def load_final_recipe(path: str | Path) -> FinalRecipe:
    """Load the version-controlled production target and clarity policy."""
    try:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise FinalRecipeError("final recipe YAML is invalid") from None
    if not isinstance(payload, dict):
        raise FinalRecipeError("final recipe must be an object")
    expected = {
        "schema_version",
        "name",
        "intent",
        "quality_contract",
        "source_contract",
        "energy_kev",
        "final_detector",
        "processing",
        "clarity",
    }
    if set(payload) != expected:
        raise FinalRecipeError("final recipe fields differ from the supported schema")
    if payload["schema_version"] != 1:
        raise FinalRecipeError("final recipe schema_version must be integer 1")
    for field in ("name", "intent"):
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise FinalRecipeError(f"final recipe {field} must be non-empty text")
    quality = _required_mapping(payload["quality_contract"], "quality_contract")
    if quality != {
        "final_minimum_long_edge_px": quality.get("final_minimum_long_edge_px"),
        "final_profile": "production-target",
        "development_profile": "selected-proof-geometry",
    }:
        raise FinalRecipeError("final recipe quality_contract is invalid")
    minimum = quality["final_minimum_long_edge_px"]
    if type(minimum) is not int or minimum < 2048:
        raise FinalRecipeError("final recipe minimum long edge must be at least 2048 pixels")
    try:
        detector = DetectorRecipe(**_required_mapping(payload["final_detector"], "final_detector"))
    except (TypeError, ValueError) as error:
        raise FinalRecipeError(f"final recipe final_detector is invalid: {error}") from None
    if max(detector.shape) < minimum:
        raise FinalRecipeError("final detector does not meet its minimum long-edge target")
    source = _required_mapping(payload["source_contract"], "source_contract")
    if set(source) != {"identifier", "source_id", "sha256", "phase"}:
        raise FinalRecipeError("final recipe source_contract fields are invalid")
    try:
        energy = float(payload["energy_kev"])
    except (TypeError, ValueError):
        raise FinalRecipeError("final recipe energy_kev must be positive and finite") from None
    if not np.isfinite(energy) or energy <= 0:
        raise FinalRecipeError("final recipe energy_kev must be positive and finite")
    processing = _required_mapping(payload["processing"], "processing")
    if set(processing) != {
        "pixel_parameter_scaling",
        "reference_native_shape",
        "reference_supersampled_shape",
        "acquisition",
        "scientific",
        "gallery",
    }:
        raise FinalRecipeError("final recipe processing fields are invalid")
    if processing["pixel_parameter_scaling"] != "linear-from-reference-shape":
        raise FinalRecipeError("final recipe pixel scaling policy is unsupported")
    reference_native = _positive_shape(
        processing["reference_native_shape"], "processing.reference_native_shape"
    )
    reference_super = _positive_shape(
        processing["reference_supersampled_shape"],
        "processing.reference_supersampled_shape",
    )
    acquisition = _stage_record(processing["acquisition"], "processing.acquisition")
    if acquisition["name"] != "background_divide":
        raise FinalRecipeError("final recipe acquisition stage must be background_divide")
    branches: dict[str, tuple[dict[str, Any], ...]] = {}
    for branch in ("scientific", "gallery"):
        values = processing[branch]
        if not isinstance(values, list) or not values:
            raise FinalRecipeError(f"final recipe processing.{branch} must be non-empty")
        stages = tuple(
            _stage_record(value, f"processing.{branch}[{index}]")
            for index, value in enumerate(values)
        )
        if stages[0]["name"] != "downsample":
            raise FinalRecipeError(
                f"final recipe {branch} branch must downsample before aesthetic processing"
            )
        branches[branch] = stages
    clarity = _required_mapping(payload["clarity"], "clarity")
    if clarity.get("line_overlays") is not False:
        raise FinalRecipeError("final recipe must explicitly prohibit line overlays")
    if clarity.get("reference_role") != "descriptive-only-not-calibrated-truth":
        raise FinalRecipeError("final recipe clarity references must remain descriptive only")
    return FinalRecipe(
        schema_version=1,
        name=payload["name"],
        intent=payload["intent"],
        final_minimum_long_edge_px=minimum,
        final_detector=detector,
        source_contract=source,
        energy_kev=energy,
        reference_native_shape=reference_native,
        reference_supersampled_shape=reference_super,
        acquisition=acquisition,
        scientific=branches["scientific"],
        gallery=branches["gallery"],
        clarity=clarity,
    )


def _detector_from_selection(record: Mapping[str, Any]) -> DetectorRecipe:
    detector = record["decision"]["selected_candidate"]["geometry"]["detector"]
    pc = detector["pc"]
    return DetectorRecipe(
        shape=tuple(detector["shape"]),
        pcx=pc["x"],
        pcy=pc["y"],
        pcz=pc["z"],
        pc_convention=pc["convention"],
        sample_tilt_deg=detector["sample_tilt_deg"],
        detector_tilt_deg=detector["detector_tilt_deg"],
        detector_azimuth_deg=detector["detector_azimuth_deg"],
        detector_twist_deg=detector["detector_twist_deg"],
        pixel_size_um=detector["pixel_size_um"],
        binning=detector["binning"],
        supersampling=detector["supersampling"],
    )


def _selection_records(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for directory in sorted(root.glob("orientation-selection-*")):
        if not directory.is_dir() or directory.is_symlink():
            raise FinalSelectionError("selection lineage contains an unsafe entry")
        path = directory / "selection.json"
        if not path.is_file() or path.is_symlink():
            raise FinalSelectionError("selection lineage contains an invalid artifact")
        try:
            records.append(load_orientation_selection(path))
        except OrientationSelectionError as error:
            raise FinalSelectionError(f"selection lineage is invalid: {error}") from error
    return records


def validate_final_selection(
    path: str | Path, *, proof_root: str | Path
) -> ValidatedFinalSelection:
    """Require intrinsic validity, external evidence, and the current linear leaf."""
    selection_path = Path(path).resolve()
    try:
        raw = json.loads(selection_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FinalSelectionError(f"orientation selection is unavailable or invalid: {error}") from error
    if isinstance(raw, dict) and raw.get("state") == "awaiting-human-selection":
        raise FinalSelectionError(
            "an awaiting-human-selection proof is not an orientation selection artifact"
        )
    try:
        record = load_orientation_selection(selection_path)
        verification = verify_orientation_selection(selection_path, proof_root=proof_root)
    except OrientationSelectionError as error:
        raise FinalSelectionError(f"orientation selection verification failed: {error}") from error
    proof_id = record["decision"]["proof"]["proof_id"]
    same_proof = {
        item["selection_id"]: item
        for item in _selection_records(selection_path.parent.parent)
        if item["decision"]["proof"]["proof_id"] == proof_id
    }
    successors = {selection_id: [] for selection_id in same_proof}
    for selection_id, item in same_proof.items():
        supersession = item["decision"]["supersession"]
        if supersession is None:
            continue
        predecessor = supersession["selection_id"]
        if predecessor not in same_proof:
            raise FinalSelectionError("selection lineage predecessor is absent")
        successors[predecessor].append(selection_id)
    if any(len(values) > 1 for values in successors.values()):
        raise FinalSelectionError("selection lineage contains a supersession fork")
    leaves = [selection_id for selection_id, values in successors.items() if not values]
    if len(leaves) != 1 or leaves[0] != record["selection_id"]:
        raise FinalSelectionError(
            "orientation selection is superseded and is not the current unique leaf"
        )
    selected = record["decision"]["selected_candidate"]
    orientation = selected["candidate"]["orientation"]
    return ValidatedFinalSelection(
        selection_id=record["selection_id"],
        proof_id=verification.proof_id,
        candidate_id=selected["candidate_id"],
        orientation=Orientation(tuple(orientation["euler_bunge_deg"]), orientation["frame"]),
        selected_detector=_detector_from_selection(record),
        record=record,
        proof_root=verification.proof_root,
    )


def _require_contract(master: MasterPatternProduct, recipe: FinalRecipe) -> None:
    metadata = master.metadata_dict()
    source = metadata["source_structure"]
    phase = metadata["phase"]
    expected = recipe.source_contract
    observed = {
        "identifier": source["identifier"],
        "source_id": source["source_id"],
        "sha256": source["sha256"],
        "phase": {
            "name": phase["name"],
            "formula": phase["formula"],
            "space_group_number": phase["space_group"]["number"],
            "space_group_setting": phase["space_group"]["setting"],
        },
    }
    if observed != expected:
        raise FinalRecipeError("master product differs from the selected source/phase contract")
    if float(metadata["energy_kev"]) != recipe.energy_kev:
        raise FinalRecipeError("master product differs from the selected energy contract")


def _same_selected_geometry(selected: DetectorRecipe, final: DetectorRecipe) -> None:
    scalar_fields = (
        "pcx",
        "pcy",
        "pcz",
        "sample_tilt_deg",
        "detector_tilt_deg",
        "detector_azimuth_deg",
        "detector_twist_deg",
    )
    if final.pc_convention != selected.pc_convention or final.binning != selected.binning:
        raise FinalRecipeError("final detector changes the selected detector convention")
    if any(not np.isclose(getattr(final, key), getattr(selected, key)) for key in scalar_fields):
        raise FinalRecipeError("final detector changes selected PC or angular geometry")
    if not np.allclose(final.physical_extent_um, selected.physical_extent_um):
        raise FinalRecipeError("final detector changes the selected physical extent")


def _scaled_parameters(
    stage: Mapping[str, Any],
    *,
    source_shape: tuple[int, int],
    target_shape: tuple[int, int],
    reference_shape: tuple[int, int],
) -> dict[str, Any]:
    parameters = plain_data(stage["parameters"])
    name = stage["name"]
    scale = max(target_shape) / max(reference_shape)
    if name == "downsample":
        parameters["shape"] = list(target_shape)
    if name == "background_divide":
        scale = max(source_shape) / max(reference_shape)
        parameters["sigma_px"] = float(parameters["sigma_px"]) * scale
    if name == "local_contrast":
        kernel = parameters["kernel_size"]
        parameters["kernel_size"] = [
            max(1, round(kernel[0] * target_shape[0] / reference_shape[0])),
            max(1, round(kernel[1] * target_shape[1] / reference_shape[1])),
        ]
    if name == "multiscale_detail":
        parameters["scales_px"] = [float(value) * scale for value in parameters["scales_px"]]
    if name == "unsharp":
        parameters["radius_px"] = float(parameters["radius_px"]) * scale
    return parameters


def _identified(kind: str, content: Mapping[str, Any], *, id_key: str, sha_key: str) -> dict[str, Any]:
    canonical = plain_data(content)
    checksum = hashlib.sha256(canonical_json(canonical).encode("utf-8")).hexdigest()
    return {"content": canonical, id_key: f"{kind}-{checksum[:16]}", sha_key: checksum}


def _stage_product(result: StageResult) -> FloatProduct:
    return FloatProduct(stable_id("stage", result.record.computational_dict()), result.intensity)


def _run_branch(
    acquisition: StageResult,
    stages: Sequence[Mapping[str, Any]],
    *,
    detector: DetectorRecipe,
    reference_shape: tuple[int, int],
) -> tuple[list[StageResult], list[dict[str, str]]]:
    current = acquisition.intensity
    results: list[StageResult] = []
    for stage in stages:
        parameters = _scaled_parameters(
            stage,
            source_shape=current.shape,
            target_shape=detector.shape,
            reference_shape=reference_shape,
        )
        result = STAGE_FUNCTIONS[stage["name"]](current, **parameters)
        results.append(result)
        current = result.intensity
    lineage = [
        {
            "name": acquisition.record.name,
            "input_id": acquisition.record.input_id,
            "output_id": acquisition.record.output_id,
        },
        *[
            {
                "name": result.record.name,
                "input_id": result.record.input_id,
                "output_id": result.record.output_id,
            }
            for result in results
        ],
    ]
    return results, lineage


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unavailable"


def _execution_context() -> dict[str, Any]:
    return {
        "environment": {
            "python": platform.python_version(),
            "machine": platform.machine(),
            "cwd": os.getcwd(),
        },
        "software": {
            "identities": {
                "kikuchi_lab": {"version": _package_version("kikuchi-lab")},
                "ebsdsim": {"version": _package_version("ebsdsim")},
                "kikuchipy": {"version": _package_version("kikuchipy")},
                "numpy": {"version": _package_version("numpy")},
                "scikit-image": {"version": _package_version("scikit-image")},
            }
        },
        "hardware": {"machine": platform.machine(), "processor": platform.processor()},
    }


def render_final(
    *,
    master: MasterPatternProduct,
    recipe_path: str | Path,
    selection_path: str | Path,
    proof_root: str | Path,
    output_root: str | Path,
    profile: str = "final",
    projector: Projector = project_with_kikuchipy,
    execution_context: Mapping[str, Any] | None = None,
) -> FinalRunResult:
    """Render one verified selection into scientific and clarity-forward products."""
    started = time.perf_counter()
    recipe = load_final_recipe(recipe_path)
    selection = validate_final_selection(selection_path, proof_root=proof_root)
    if profile not in {"final", "development"}:
        raise FinalRecipeError("profile must be 'final' or 'development'")
    detector = recipe.final_detector if profile == "final" else selection.selected_detector
    if profile == "final":
        _same_selected_geometry(selection.selected_detector, detector)
    _require_contract(master, recipe)
    projected = projector(
        master=master,
        orientation=selection.orientation,
        detector=detector,
        energy_kev=recipe.energy_kev,
    )
    if projected.intensity.shape != detector.supersampled_shape:
        raise FinalRecipeError("projector did not return the declared supersampled shape")

    acquisition_parameters = _scaled_parameters(
        recipe.acquisition,
        source_shape=projected.intensity.shape,
        target_shape=projected.intensity.shape,
        reference_shape=recipe.reference_supersampled_shape,
    )
    acquisition = STAGE_FUNCTIONS[recipe.acquisition["name"]](
        projected.intensity, **acquisition_parameters
    )
    scientific, scientific_lineage = _run_branch(
        acquisition,
        recipe.scientific,
        detector=detector,
        reference_shape=recipe.reference_native_shape,
    )
    gallery, gallery_lineage = _run_branch(
        acquisition,
        recipe.gallery,
        detector=detector,
        reference_shape=recipe.reference_native_shape,
    )
    if scientific[-1].intensity.shape != detector.shape or gallery[-1].intensity.shape != detector.shape:
        raise FinalRecipeError("final processing branches must terminate at detector-native shape")

    projected_product = FloatProduct(projected.product_id, projected.intensity)
    acquisition_product = _stage_product(acquisition)
    stages: dict[str, FloatProduct] = {"shared-00-background-divide": acquisition_product}
    for branch, results in (("scientific", scientific), ("gallery", gallery)):
        for index, result in enumerate(results, start=1):
            stages[f"{branch}-{index:02d}-{result.record.name}"] = _stage_product(result)
    scientific_recipe_content = {
        "profile": profile,
        "clarity_role": "scientific-clean",
        "stages": [scientific_lineage[0]["name"], *[result.record.to_dict() for result in scientific]],
        "resolved_processing": [acquisition.record.computational_dict(), *[result.record.computational_dict() for result in scientific]],
    }
    gallery_recipe_content = {
        "profile": profile,
        "clarity_role": "gallery-crisp",
        "stages": [gallery_lineage[0]["name"], *[result.record.to_dict() for result in gallery]],
        "resolved_processing": [acquisition.record.computational_dict(), *[result.record.computational_dict() for result in gallery]],
        "clarity_contract": plain_data(recipe.clarity),
    }
    scientific_final = FloatProduct(
        stable_id(
            "processed",
            {
                "source_projection_id": projected.product_id,
                "recipe": scientific_recipe_content,
                "final_image_id": scientific[-1].record.output_id,
            },
        ),
        scientific[-1].intensity,
    )
    gallery_final = FloatProduct(
        stable_id(
            "processed",
            {
                "source_projection_id": projected.product_id,
                "recipe": gallery_recipe_content,
                "final_image_id": gallery[-1].record.output_id,
            },
        ),
        gallery[-1].intensity,
    )
    selected_record = selection.record["decision"]["selected_candidate"]
    orientation_content = {
        "selected_candidate_id": selection.candidate_id,
        "selection_id": selection.selection_id,
        "selection_decision_sha256": selection.record["decision_sha256"],
        "proof_id": selection.proof_id,
        "candidate_sha256": selected_record["candidate_sha256"],
        "external_verification": {
            "proof_id": selection.proof_id,
            "proof_tree_sha256": selection.record["decision"]["proof"]["tree_digest"]["sha256"],
        },
        "lineage": {"current_unique_leaf": True},
        "rationale": selection.record["decision"]["rationale"],
    }
    orientation_decision = _identified(
        "decision",
        orientation_content,
        id_key="decision_id",
        sha_key="decision_sha256",
    )
    candidate_content = {
        "candidate_ids": [selection.candidate_id],
        "source_candidate_set_id": selection.record["decision"]["candidate_set"]["candidate_set_id"],
        "selected_candidate": selected_record["candidate"],
    }
    projection_content = {
        "workflow_schema_version": 1,
        "profile": profile,
        "quality_grade": "development" if profile == "development" else "final-target",
        "not_final_quality": profile == "development",
        "orientation": selection.orientation.to_dict(),
        "detector": _detector_constructor_dict(detector),
        "energy_kev": recipe.energy_kev,
        "selection_id": selection.selection_id,
        "proof_id": selection.proof_id,
        "final_recipe_snapshot": recipe.to_dict(),
    }
    projection_recipe = _identified(
        "recipe", projection_content, id_key="recipe_id", sha_key="recipe_sha256"
    )
    projection_recipe["geometry_id"] = stable_id("geometry", projection_content)
    simulation_content = plain_data(master.metadata_dict()["simulation"])
    recipes = {
        "simulation": _identified(
            "recipe", simulation_content, id_key="recipe_id", sha_key="recipe_sha256"
        ),
        "projection": projection_recipe,
        "scientific-clean": _identified(
            "recipe",
            scientific_recipe_content,
            id_key="recipe_id",
            sha_key="recipe_sha256",
        ),
        "gallery-crisp": _identified(
            "recipe", gallery_recipe_content, id_key="recipe_id", sha_key="recipe_sha256"
        ),
    }
    static_warnings: list[dict[str, Any]] = [
        {
            "code": "descriptive_clarity_references_only",
            "message": "Aesthetic references guide appearance but are not calibrated truth.",
            "details": {"reference_role": recipe.clarity["reference_role"]},
        }
    ]
    if profile == "development":
        static_warnings.append(
            {
                "code": "development_not_final_quality",
                "message": "DEVELOPMENT / NOT FINAL QUALITY: proof-grade master and geometry.",
                "details": {"profile": profile},
            }
        )
    processing_warnings = [
        warning.to_dict()
        for result in (acquisition, *scientific, *gallery)
        for warning in result.record.warnings
    ]
    context = plain_data(execution_context or _execution_context())
    request = ArtifactBundleRequest(
        source={
            **plain_data(master.metadata_dict()["source_structure"]),
            "quality_profile": profile,
            "selection_id": selection.selection_id,
        },
        environment=context["environment"],
        software=context["software"],
        hardware=context["hardware"],
        recipes=recipes,
        master_metadata={
            "product_id": master.product_id,
            "array_sha256": master.array_sha256,
            "metadata": master.metadata_dict(),
        },
        orientation_candidates=_identified(
            "candidate-set",
            candidate_content,
            id_key="candidate_set_id",
            sha_key="candidate_set_sha256",
        ),
        projected=projected_product,
        acquisition_corrected=acquisition_product,
        stages=stages,
        scientific_lineage=scientific_lineage,
        gallery_lineage=gallery_lineage,
        scientific_clean=scientific_final,
        gallery_crisp=gallery_final,
        warnings=[*static_warnings, *processing_warnings],
        timings={"elapsed_seconds": time.perf_counter() - started},
        resources={
            "materialized_float_bytes": sum(
                product.intensity.nbytes
                for product in (
                    projected_product,
                    acquisition_product,
                    *stages.values(),
                    scientific_final,
                    gallery_final,
                )
            )
        },
        orientation_decision=orientation_decision,
        decision_links={
            "orientation": orientation_decision["decision_id"],
            "processing": stable_id("decision", plain_data(recipe.clarity)),
            "source_selection": selection.selection_id,
        },
    )
    written = write_artifact_bundle(output_root, request)
    return FinalRunResult(
        run_id=written.run_id,
        path=written.path,
        manifest_sha256=written.manifest_sha256,
        profile=profile,
        selection_id=selection.selection_id,
        not_final_quality=profile == "development",
        elapsed_seconds=time.perf_counter() - started,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_bundle_manifest(root: str | Path) -> tuple[Path, dict[str, Any]]:
    bundle = Path(root).resolve()
    manifest_path = bundle / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReproductionMismatch(f"bundle manifest is unavailable or invalid: {error}") from error
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 2:
        raise ReproductionMismatch("bundle manifest schema is unsupported")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ReproductionMismatch("bundle manifest inventory is absent")
    for relative, record in files.items():
        if not isinstance(relative, str) or not isinstance(record, dict):
            raise ReproductionMismatch("bundle manifest inventory is malformed")
        path = bundle / relative
        try:
            resolved = path.resolve(strict=True)
        except OSError as error:
            raise ReproductionMismatch(f"bundle inventory entry is unavailable: {relative}") from error
        if bundle not in resolved.parents or not resolved.is_file() or resolved.is_symlink():
            raise ReproductionMismatch(f"bundle inventory entry is unsafe: {relative}")
        if record != {"bytes": path.stat().st_size, "sha256": _sha256(path)}:
            raise ReproductionMismatch(f"bundle inventory checksum disagrees: {relative}")
    return bundle, manifest


def _normalized_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalized_json(item)
            for key, item in value.items()
            if key not in {"captured_at", "created_at", "decided_at"}
        }
    if isinstance(value, list):
        return [_normalized_json(item) for item in value]
    if isinstance(value, str) and Path(value).is_absolute():
        return "<ABSOLUTE_LOCAL_PATH>"
    return value


def _manifest_comparison_identity(bundle: Path, manifest: Mapping[str, Any]) -> str:
    expected_exclusions = {
        "json_fields": ["**/captured_at", "**/created_at", "**/decided_at"],
        "json_documents": [
            "diagnostics/timings.json#/**",
            "diagnostics/resources.json#/**",
        ],
        "value_rules": [{"kind": "absolute_local_path", "scope": "**"}],
        "external_values": ["manifest_sha256"],
    }
    if manifest.get("comparison_exclusions") != expected_exclusions:
        raise ReproductionMismatch("bundle comparison exclusions differ from schema")
    excluded_documents = {"diagnostics/timings.json", "diagnostics/resources.json"}
    normalized_files: dict[str, Any] = {}
    for relative, record in manifest["files"].items():
        if relative in excluded_documents:
            continue
        if relative.endswith(".json"):
            try:
                payload = json.loads((bundle / relative).read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                raise ReproductionMismatch(
                    f"comparison JSON is invalid: {relative}"
                ) from error
            semantic = canonical_json(_normalized_json(payload))
            normalized_files[relative] = {
                "kind": "normalized-json",
                "semantic_sha256": hashlib.sha256(semantic.encode("utf-8")).hexdigest(),
            }
        else:
            normalized_files[relative] = record
    normalized_manifest = _normalized_json(dict(manifest))
    normalized_manifest["files"] = normalized_files
    return stable_id("manifest-comparison", normalized_manifest)


def _processing_paths(manifest: Mapping[str, Any]) -> list[str]:
    paths = [
        "products/acquisition-corrected.npy",
        "products/scientific-clean.npy",
        "products/gallery-crisp.npy",
    ]
    paths.extend(
        sorted(
            relative
            for relative in manifest["files"]
            if relative.startswith("products/stages/") and relative.endswith(".npy")
        )
    )
    return paths


def compare_final_bundles(
    first: str | Path,
    second: str | Path,
    *,
    source_mode: str = "exact",
    source_atol: float = 0.0,
    source_rtol: float = 0.0,
) -> ReproductionComparison:
    """Compare GPU source explicitly while keeping every CPU product byte-exact."""
    if source_mode not in {"exact", "gpu-tolerant"}:
        raise ValueError("source_mode must be 'exact' or 'gpu-tolerant'")
    if source_mode == "exact" and (source_atol != 0 or source_rtol != 0):
        raise ValueError("exact source comparison cannot declare tolerances")
    if source_atol < 0 or source_rtol < 0 or not np.isfinite([source_atol, source_rtol]).all():
        raise ValueError("source tolerances must be finite and non-negative")
    first_root, first_manifest = _load_bundle_manifest(first)
    second_root, second_manifest = _load_bundle_manifest(second)
    first_source = np.load(first_root / "products/projected.npy", allow_pickle=False)
    second_source = np.load(second_root / "products/projected.npy", allow_pickle=False)
    source_equal = (
        np.array_equal(first_source, second_source)
        if source_mode == "exact"
        else np.allclose(first_source, second_source, atol=source_atol, rtol=source_rtol)
    )
    if not source_equal:
        raise ReproductionMismatch(f"{source_mode} source projection comparison failed")
    first_processing = _processing_paths(first_manifest)
    second_processing = _processing_paths(second_manifest)
    if first_processing != second_processing:
        raise ReproductionMismatch("CPU processing inventories differ")
    for relative in first_processing:
        if not np.array_equal(
            np.load(first_root / relative, allow_pickle=False),
            np.load(second_root / relative, allow_pickle=False),
        ):
            raise ReproductionMismatch(
                f"CPU processing must remain exact; mismatch at {relative}"
            )
    first_exports = sorted(first_manifest.get("uint16_exports", {}))
    second_exports = sorted(second_manifest.get("uint16_exports", {}))
    if first_exports != second_exports:
        raise ReproductionMismatch("uint16 export inventories differ")
    for relative in first_exports:
        if source_mode == "gpu-tolerant" and relative.startswith("products/projected."):
            continue
        if (first_root / relative).read_bytes() != (second_root / relative).read_bytes():
            raise ReproductionMismatch(
                f"CPU processing uint16 exports must remain exact; mismatch at {relative}"
            )
    first_manifest_identity = _manifest_comparison_identity(first_root, first_manifest)
    second_manifest_identity = _manifest_comparison_identity(second_root, second_manifest)
    if first_manifest_identity != second_manifest_identity:
        raise ReproductionMismatch("manifest identity differs after schema exclusions")
    if first_manifest["run_id"] != second_manifest["run_id"]:
        raise ReproductionMismatch("content-addressed run identities differ")
    return ReproductionComparison(
        equal=True,
        first_run_id=first_manifest["run_id"],
        second_run_id=second_manifest["run_id"],
        first_manifest_identity=first_manifest_identity,
        second_manifest_identity=second_manifest_identity,
        source_comparison=source_mode,
        source_atol=float(source_atol),
        source_rtol=float(source_rtol),
    )


def reproduce_final(
    *,
    original_run: str | Path,
    master: MasterPatternProduct,
    selection_path: str | Path,
    proof_root: str | Path,
    output_root: str | Path,
    projector: Projector = project_with_kikuchipy,
    execution_context: Mapping[str, Any] | None = None,
    source_mode: str = "exact",
    source_atol: float = 0.0,
    source_rtol: float = 0.0,
) -> FinalReproductionResult:
    """Rebuild solely from an inventoried manifest recipe snapshot and selection."""
    original_root, manifest = _load_bundle_manifest(original_run)
    try:
        projection = json.loads(
            (original_root / "recipes/projection.json").read_text(encoding="utf-8")
        )
        content = projection["content"]
        recipe_snapshot = content["final_recipe_snapshot"]
        profile = content["profile"]
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ReproductionMismatch("original bundle lacks a valid final recipe snapshot") from error
    if content.get("selection_id") != load_orientation_selection(selection_path)["selection_id"]:
        raise ReproductionMismatch("supplied selection differs from the recorded selection")
    if profile not in {"final", "development"}:
        raise ReproductionMismatch("recorded render profile is invalid")
    with tempfile.TemporaryDirectory(prefix="kikuchi-final-reproduction-") as temporary:
        recipe_path = Path(temporary) / "forsterite-final.yml"
        recipe_path.write_text(
            yaml.safe_dump(recipe_snapshot, sort_keys=False),
            encoding="utf-8",
        )
        rebuilt = render_final(
            master=master,
            recipe_path=recipe_path,
            selection_path=selection_path,
            proof_root=proof_root,
            output_root=output_root,
            profile=profile,
            projector=projector,
            execution_context=execution_context,
        )
    comparison = compare_final_bundles(
        original_root,
        rebuilt.path,
        source_mode=source_mode,
        source_atol=source_atol,
        source_rtol=source_rtol,
    )
    if comparison.first_run_id != manifest["run_id"]:
        raise ReproductionMismatch("original manifest identity changed during reproduction")
    return FinalReproductionResult(run=rebuilt, comparison=comparison)
