"""Deterministic orientation-proof rendering without an automated decision."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from kikuchi_lab.artifacts.bundle import BundleExistsError, FloatProduct
from kikuchi_lab.artifacts.contact_sheet import ContactSheetItem, write_contact_sheet
from kikuchi_lab.artifacts.images import quantize_uint16, write_npy, write_uint16
from kikuchi_lab.diagnostics import image_metrics
from kikuchi_lab.doctor import collect_doctor_report
from kikuchi_lab.model import DetectorPatternProduct, DetectorRecipe, MasterPatternProduct
from kikuchi_lab.model.identity import canonical_json, stable_id
from kikuchi_lab.orientations import OrientationCandidate, load_candidate_set
from kikuchi_lab.processing import load_processing_recipe, run_graph
from kikuchi_lab.projection import project_with_kikuchipy


Projector = Callable[..., DetectorPatternProduct]


@dataclass(frozen=True)
class ProofRecipe:
    schema_version: int
    name: str
    quality_grade: str
    intended_use: str
    not_final_quality: bool
    limitations: Mapping[str, Any]
    candidate_recipe: Path
    processing_recipe: Path
    energy_kev: float
    detector: DetectorRecipe
    contact_sheet_columns: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "quality_grade": self.quality_grade,
            "intended_use": self.intended_use,
            "not_final_quality": self.not_final_quality,
            "limitations": dict(self.limitations),
            "candidate_recipe": self.candidate_recipe.name,
            "processing_recipe": self.processing_recipe.name,
            "energy_kev": self.energy_kev,
            "detector": self.detector.to_dict(),
            "contact_sheet_columns": self.contact_sheet_columns,
        }


@dataclass(frozen=True)
class ProofRunResult:
    proof_id: str
    path: Path
    contact_sheet: Path
    state: str
    candidate_ids: tuple[str, ...]
    elapsed_seconds: float


@dataclass(frozen=True)
class _RenderedCandidate:
    candidate: OrientationCandidate
    raw: DetectorPatternProduct
    processed: Any
    raw_product: FloatProduct
    processed_product: FloatProduct
    metrics: Mapping[str, Any]
    warnings: tuple[Mapping[str, Any], ...]


def _relative_recipe(base: Path, value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"proof recipe requires non-empty {field}")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"proof recipe {field} must remain beside the proof recipe")
    return base / relative


def load_proof_recipe(path: str | Path) -> ProofRecipe:
    """Load the fixed detector/candidate/processing comparison contract."""
    recipe_path = Path(path).resolve()
    raw = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError("proof recipe schema_version must be supported version 1")
    expected = {
        "schema_version", "name", "quality_grade", "intended_use",
        "not_final_quality", "limitations", "candidate_recipe", "processing_recipe",
        "energy_kev", "detector", "contact_sheet_columns",
    }
    if set(raw) != expected:
        raise ValueError(
            f"proof recipe fields differ: missing={sorted(expected - set(raw))}, "
            f"unknown={sorted(set(raw) - expected)}"
        )
    if not isinstance(raw["name"], str) or not raw["name"].strip():
        raise ValueError("proof recipe requires non-empty name")
    if raw["quality_grade"] != "proof":
        raise ValueError("proof recipe quality_grade must be 'proof'")
    if raw["intended_use"] != "orientation-comparison":
        raise ValueError("proof recipe intended_use must be 'orientation-comparison'")
    if raw["not_final_quality"] is not True:
        raise ValueError("proof recipe not_final_quality must be true")
    limitations = raw["limitations"]
    expected_limitations = {
        "dmin_nm": 0.08,
        "energy_binwidth_kev": 20.0,
        "energy_integration": "one-bin",
        "rank": 8,
    }
    if limitations != expected_limitations:
        raise ValueError(f"proof recipe limitations must be exactly {expected_limitations}")
    detector = raw["detector"]
    if not isinstance(detector, dict):
        raise ValueError("proof recipe detector must be an object")
    columns = raw["contact_sheet_columns"]
    if isinstance(columns, bool) or not isinstance(columns, int) or columns <= 0:
        raise ValueError("contact_sheet_columns must be a positive integer")
    energy = float(raw["energy_kev"])
    if not np.isfinite(energy) or energy <= 0:
        raise ValueError("energy_kev must be finite and positive")
    return ProofRecipe(
        schema_version=1,
        name=raw["name"],
        quality_grade=raw["quality_grade"],
        intended_use=raw["intended_use"],
        not_final_quality=raw["not_final_quality"],
        limitations=limitations,
        candidate_recipe=_relative_recipe(recipe_path.parent, raw["candidate_recipe"], "candidate_recipe"),
        processing_recipe=_relative_recipe(recipe_path.parent, raw["processing_recipe"], "processing_recipe"),
        energy_kev=energy,
        detector=DetectorRecipe(**detector),
        contact_sheet_columns=columns,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value), encoding="utf-8")


def _preview(quantized: np.ndarray) -> np.ndarray:
    return np.rint(quantized.astype(np.float64) / 257.0).astype(np.uint8)


def _label(candidate: OrientationCandidate) -> str:
    phi1, phi, phi2 = candidate.orientation.euler_bunge_deg
    return (
        f"{candidate.candidate_id}  {candidate.zone_axis_label}  phi1={phi1:.3f} deg\n"
        f"Bunge Euler=({phi1:.3f}, {phi:.3f}, {phi2:.3f}) deg"
    )


def _rendered_candidate(
    *,
    master: MasterPatternProduct,
    candidate: OrientationCandidate,
    recipe: ProofRecipe,
    processing: Any,
    projector: Projector,
) -> _RenderedCandidate:
    raw = projector(
        master=master,
        orientation=candidate.orientation,
        detector=recipe.detector,
        energy_kev=recipe.energy_kev,
    )
    processed = run_graph(raw, processing)
    raw_product = FloatProduct(raw.product_id, raw.intensity)
    processed_product = FloatProduct(processed.product_id, processed.final_intensity)
    warnings = tuple(
        warning.to_dict()
        for stage in processed.stages
        for warning in stage.record.warnings
    )
    return _RenderedCandidate(
        candidate=candidate,
        raw=raw,
        processed=processed,
        raw_product=raw_product,
        processed_product=processed_product,
        metrics={
            "schema_version": 1,
            "raw": image_metrics(raw.intensity),
            "processed": image_metrics(processed.final_intensity),
        },
        warnings=warnings,
    )


def _product_identity(product: FloatProduct) -> dict[str, Any]:
    return {
        "product_id": product.product_id,
        "content_id": product.content_id,
        "array_sha256": product.array_sha256,
        "shape": list(product.intensity.shape),
        "dtype": "float32",
    }


def _comparison_contract(recipe: ProofRecipe, processing: Any) -> dict[str, Any]:
    return {
        "energy_kev": recipe.energy_kev,
        "detector_recipe_id": recipe.detector.recipe_id,
        "detector": recipe.detector.to_dict(),
        "processing_recipe_id": processing.recipe_id,
        "processing": processing.to_dict(),
        "processed_variant": processing.name,
        "metrics_schema": "kikuchi-lab-image-metrics-v1",
        "panels": ["raw", "processed"],
        "preview_quantization": {
            "scope": "per-panel-per-candidate",
            "method": "robust-percentile-linear",
            "percentiles": [0.5, 99.5],
            "comparison_use": "structural",
            "absolute_intensity_comparable": False,
        },
    }


def _contact_sheet_contract(processing: Any) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "processed_variant": processing.name,
        "processing_recipe_id": processing.recipe_id,
        "quality_banner": "ascii-proof-grade-v1",
    }


_SOFTWARE_DISTRIBUTIONS = {
    "kikuchi-lab": "kikuchi-lab",
    "kikuchipy": "kikuchipy",
    "scikit-image": "scikit-image",
    "numpy": "numpy",
    "orix": "orix",
    "pillow": "pillow",
    "ebsdsim": "ebsdsim",
    "wgpu": "wgpu",
}


def collect_execution_context(output_root: str | Path) -> dict[str, Any]:
    """Capture non-identity runtime evidence for a real CLI proof."""
    repository = Path(__file__).parents[3]

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    return {
        "software": {
            label: version(distribution)
            for label, distribution in _SOFTWARE_DISTRIBUTIONS.items()
        },
        "doctor": collect_doctor_report(output_root),
        "git": {
            "branch": git("branch", "--show-current"),
            "revision": git("rev-parse", "HEAD"),
            "dirty": bool(git("status", "--porcelain")),
        },
    }


def _validate_execution_context(value: Mapping[str, Any]) -> dict[str, Any]:
    context = json.loads(canonical_json(value))
    software = context.get("software")
    if not isinstance(software, dict) or set(software) != set(_SOFTWARE_DISTRIBUTIONS):
        raise ValueError("execution context requires the complete software version set")
    if any(not isinstance(item, str) or not item for item in software.values()):
        raise ValueError("execution context software versions must be non-empty strings")
    doctor = context.get("doctor")
    if not isinstance(doctor, dict) or not isinstance(doctor.get("checks"), dict):
        raise ValueError("execution context requires doctor checks")
    adapter = doctor["checks"].get("webgpu_adapter")
    if not isinstance(adapter, dict) or not isinstance(adapter.get("details"), dict):
        raise ValueError("execution context requires WebGPU hardware/backend details")
    git = context.get("git")
    if not isinstance(git, dict) or set(git) != {"branch", "revision", "dirty"}:
        raise ValueError("execution context requires branch, revision, and dirty state")
    if not isinstance(git["branch"], str) or not isinstance(git["revision"], str):
        raise ValueError("execution context git locators must be strings")
    if type(git["dirty"]) is not bool:
        raise ValueError("execution context dirty state must be boolean")
    return context


def _origin_evidence(
    *,
    master: MasterPatternProduct,
    master_locator: str | Path,
    source_locator: str | Path,
) -> dict[str, Any]:
    master_path = Path(master_locator).resolve()
    source_path = Path(source_locator).resolve()
    if not master_path.is_file() or not source_path.is_file():
        raise ValueError("master and source canonical locators must be files")
    recorded_source_sha256 = master.metadata["source_structure"]["sha256"]
    source_sha256 = _sha256(source_path)
    if source_sha256 != recorded_source_sha256:
        raise ValueError("source canonical locator checksum disagrees with master provenance")
    manifests = sorted(master_path.parent.glob("*.manifest.json"))
    if len(manifests) != 1:
        raise ValueError("originating master bundle must contain exactly one manifest")
    manifest_path = manifests[0].resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("master_product_id") != master.product_id:
        raise ValueError("originating master manifest references a different product")
    return {
        "source": {
            "canonical_path": str(source_path),
            "sha256": source_sha256,
            "source_id": master.metadata["source_structure"]["source_id"],
        },
        "master_product": {
            "canonical_path": str(master_path),
            "file_sha256": _sha256(master_path),
            "product_id": master.product_id,
            "array_sha256": master.array_sha256,
            "bundle_path": str(master_path.parent),
            "manifest_path": str(manifest_path),
            "manifest_sha256": _sha256(manifest_path),
        },
        "identity_exclusion": "local locators and execution context",
    }


def _write_candidate(
    root: Path,
    rendered: _RenderedCandidate,
    contract: Mapping[str, Any],
) -> ContactSheetItem:
    destination = root / "candidates" / rendered.candidate.candidate_id
    previews: dict[str, np.ndarray] = {}
    quantizations: dict[str, Any] = {}
    for label, product in (
        ("raw", rendered.raw_product),
        ("processed", rendered.processed_product),
    ):
        write_npy(destination / f"{label}.npy", product.intensity)
        quantized, quantization = quantize_uint16(
            product.intensity,
            label=label,
            source_product_id=product.product_id,
            source_content_id=product.content_id,
            source_array_sha256=product.array_sha256,
        )
        write_uint16(destination / f"{label}.tif", quantized)
        write_uint16(destination / f"{label}.png", quantized)
        previews[label] = _preview(quantized)
        quantizations[label] = quantization
    evidence = {
        "schema_version": 1,
        "candidate": rendered.candidate.to_dict(),
        "comparison_contract": contract,
        "products": {
            "raw": _product_identity(rendered.raw_product),
            "processed": _product_identity(rendered.processed_product),
        },
        "processing_evidence": rendered.processed.to_dict(),
        "metrics": rendered.metrics,
        "warnings": list(rendered.warnings),
        "quantization": quantizations,
    }
    _write_json(destination / "evidence.json", evidence)
    return ContactSheetItem(
        candidate_id=rendered.candidate.candidate_id,
        label=_label(rendered.candidate),
        raw=previews["raw"],
        processed=previews["processed"],
    )


def render_proof(
    *,
    master: MasterPatternProduct,
    recipe_path: str | Path,
    output_root: str | Path,
    master_locator: str | Path,
    source_locator: str | Path,
    projector: Projector = project_with_kikuchipy,
    execution_context: Mapping[str, Any] | None = None,
    invocation: list[str] | tuple[str, ...] | None = None,
) -> ProofRunResult:
    """Render all candidates in declared order and stop before human selection."""
    started = time.perf_counter()
    recipe = load_proof_recipe(recipe_path)
    candidates = load_candidate_set(recipe.candidate_recipe)
    processing = load_processing_recipe(recipe.processing_recipe)
    contract = _comparison_contract(recipe, processing)
    contact_contract = _contact_sheet_contract(processing)
    output = Path(output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    context = _validate_execution_context(
        execution_context if execution_context is not None else collect_execution_context(output)
    )
    invoked_as = list(invocation or ["python-api:kikuchi_lab.workflows.render_proof"])
    if not invoked_as or any(not isinstance(item, str) or not item for item in invoked_as):
        raise ValueError("proof invocation must contain non-empty argument strings")
    origin = _origin_evidence(
        master=master,
        master_locator=master_locator,
        source_locator=source_locator,
    )
    rendered = tuple(
        _rendered_candidate(
            master=master,
            candidate=candidate,
            recipe=recipe,
            processing=processing,
            projector=projector,
        )
        for candidate in candidates.candidates
    )
    identity = {
        "schema_version": 1,
        "state": "awaiting-human-selection",
        "quality_grade": recipe.quality_grade,
        "intended_use": recipe.intended_use,
        "not_final_quality": recipe.not_final_quality,
        "limitations": dict(recipe.limitations),
        "master": {
            "product_id": master.product_id,
            "array_sha256": master.array_sha256,
        },
        "candidate_set_id": candidates.candidate_set_id,
        "candidate_order": list(candidates.candidate_ids),
        "comparison_contract": contract,
        "contact_sheet_contract": contact_contract,
        "products": {
            item.candidate.candidate_id: {
                "raw": _product_identity(item.raw_product),
                "processed": _product_identity(item.processed_product),
            }
            for item in rendered
        },
    }
    proof_id = stable_id("proof", identity)
    completed = output / proof_id
    if completed.exists():
        raise BundleExistsError(f"completed proof bundle already exists: {completed}")
    staging = Path(tempfile.mkdtemp(prefix=f".{proof_id}.", dir=output))
    try:
        items = tuple(_write_candidate(staging, item, contract) for item in rendered)
        contact_metadata = write_contact_sheet(
            staging / "contact-sheet.png",
            items,
            columns=recipe.contact_sheet_columns,
            panel_shape=recipe.detector.shape,
            processed_variant={
                "name": processing.name,
                "recipe_id": processing.recipe_id,
                "short_id": processing.recipe_id.split("-", maxsplit=1)[1][:8],
            },
            quality_banner={
                "quality_grade": recipe.quality_grade,
                "intended_use": recipe.intended_use,
                "not_final_quality": recipe.not_final_quality,
                "text": (
                    "PROOF-GRADE / NOT FINAL QUALITY | orientation comparison | "
                    f"processed: {processing.name} [{processing.recipe_id.split('-', 1)[1][:8]}]"
                ),
            },
        )
        _write_json(staging / "contact-sheet.json", contact_metadata)
        _write_json(staging / "metadata/master-pattern.json", {
            "product_id": master.product_id,
            "array_sha256": master.array_sha256,
            "metadata": master.metadata_dict(),
        })
        _write_json(staging / "metadata/orientation-candidates.json", candidates.to_dict())
        _write_json(staging / "recipes/proof.json", recipe.to_dict())
        _write_json(staging / "provenance/execution.json", {
            **context,
            "invocation": invoked_as,
        })
        _write_json(staging / "provenance/master-origin.json", origin)
        elapsed = time.perf_counter() - started
        _write_json(staging / "diagnostics/run.json", {
            "elapsed_seconds": elapsed,
            "warnings": {
                item.candidate.candidate_id: list(item.warnings)
                for item in rendered
                if item.warnings
            },
        })
        files = {
            str(path.relative_to(staging)): {
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in sorted(staging.rglob("*"))
            if path.is_file()
        }
        manifest = {
            "schema_version": 1,
            "proof_id": proof_id,
            "state": "awaiting-human-selection",
            "quality_grade": recipe.quality_grade,
            "intended_use": recipe.intended_use,
            "not_final_quality": recipe.not_final_quality,
            "limitations": dict(recipe.limitations),
            "candidate_set_id": candidates.candidate_set_id,
            "candidate_order": list(candidates.candidate_ids),
            "comparison_contract": contract,
            "identity": identity,
            "contact_sheet": "contact-sheet.png",
            "evidence": {
                "execution": "provenance/execution.json",
                "master_origin": "provenance/master-origin.json",
            },
            "files": files,
            "selection_policy": "No candidate is selected or ranked by the proof workflow.",
        }
        _write_json(staging / "manifest.json", manifest)
        os.replace(staging, completed)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return ProofRunResult(
        proof_id=proof_id,
        path=completed,
        contact_sheet=completed / "contact-sheet.png",
        state="awaiting-human-selection",
        candidate_ids=candidates.candidate_ids,
        elapsed_seconds=time.perf_counter() - started,
    )
