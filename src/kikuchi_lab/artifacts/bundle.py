"""Atomic publication of self-inventorying artifact directories."""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from kikuchi_lab.diagnostics import image_metrics
from kikuchi_lab.model.identity import canonical_json, plain_data, stable_id

from .images import canonical_float_image, quantize_uint16, write_npy, write_preview, write_uint16

_STAGE_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_RECIPE_NAMES = ("simulation", "projection", "scientific-clean", "gallery-crisp")


class BundleExistsError(FileExistsError):
    """Raised when a completed run already exists."""


class PartialBundleError(FileExistsError):
    """Raised when an incomplete run requires an explicit recovery choice."""


@dataclass(frozen=True)
class FloatProduct:
    product_id: str
    intensity: np.ndarray
    array_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.product_id, str) or not self.product_id:
            raise ValueError("float product requires a non-empty product_id")
        image = canonical_float_image(self.intensity)
        immutable = np.frombuffer(image.tobytes(order="C"), dtype=np.float32).reshape(image.shape)
        object.__setattr__(self, "intensity", immutable)
        object.__setattr__(self, "array_sha256", hashlib.sha256(immutable.tobytes()).hexdigest())


@dataclass(frozen=True)
class ArtifactBundleRequest:
    source: Mapping[str, Any]
    environment: Mapping[str, Any]
    software: Mapping[str, Any]
    hardware: Mapping[str, Any]
    recipes: Mapping[str, Mapping[str, Any]]
    master_metadata: Mapping[str, Any]
    orientation_candidates: Mapping[str, Any] | Sequence[Any]
    projected: FloatProduct
    acquisition_corrected: FloatProduct
    stages: Mapping[str, FloatProduct]
    scientific_clean: FloatProduct
    gallery_crisp: FloatProduct
    warnings: Sequence[Any]
    timings: Mapping[str, Any]
    resources: Mapping[str, Any]
    orientation_decision: Mapping[str, Any]
    decision_links: Mapping[str, Any]


@dataclass(frozen=True)
class BundleWriteResult:
    run_id: str
    path: Path
    manifest_sha256: str


def _without_evidence_fields(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _without_evidence_fields(item)
            for key, item in value.items()
            if key not in {"captured_at", "created_at", "decided_at", "cwd", "path"}
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_without_evidence_fields(item) for item in value]
    return value


def _validate(request: ArtifactBundleRequest) -> None:
    if set(request.recipes) != set(_RECIPE_NAMES):
        raise ValueError(f"recipes must contain exactly {', '.join(_RECIPE_NAMES)}")
    if not request.stages:
        raise ValueError("at least one processing stage is required")
    for name, product in request.stages.items():
        if not _STAGE_NAME.fullmatch(name) or not isinstance(product, FloatProduct):
            raise ValueError("stage names must be safe lowercase file names with FloatProduct values")
    products = (
        request.projected,
        request.acquisition_corrected,
        request.scientific_clean,
        request.gallery_crisp,
        *request.stages.values(),
    )
    if any(not isinstance(product, FloatProduct) for product in products):
        raise TypeError("all image products must be FloatProduct values")
    shapes = {product.intensity.shape for product in products}
    if len(shapes) != 1:
        raise ValueError("all bundle float products must share one detector shape")
    plain_data(
        {
            "source": request.source,
            "environment": request.environment,
            "software": request.software,
            "hardware": request.hardware,
            "recipes": request.recipes,
            "master_metadata": request.master_metadata,
            "orientation_candidates": request.orientation_candidates,
            "warnings": request.warnings,
            "timings": request.timings,
            "resources": request.resources,
            "orientation_decision": request.orientation_decision,
            "decision_links": request.decision_links,
        }
    )


def _run_id(request: ArtifactBundleRequest) -> str:
    payload = {
        "source": _without_evidence_fields(request.source),
        "software": _without_evidence_fields(request.software),
        "recipes": _without_evidence_fields(request.recipes),
        "master_product_id": request.master_metadata.get("product_id"),
        "orientation_candidates": _without_evidence_fields(request.orientation_candidates),
        "product_ids": {
            "projected": {
                "product_id": request.projected.product_id,
                "array_sha256": request.projected.array_sha256,
            },
            "acquisition_corrected": {
                "product_id": request.acquisition_corrected.product_id,
                "array_sha256": request.acquisition_corrected.array_sha256,
            },
            "stages": {
                name: {
                    "product_id": product.product_id,
                    "array_sha256": product.array_sha256,
                }
                for name, product in request.stages.items()
            },
            "scientific_clean": {
                "product_id": request.scientific_clean.product_id,
                "array_sha256": request.scientific_clean.array_sha256,
            },
            "gallery_crisp": {
                "product_id": request.gallery_crisp.product_id,
                "array_sha256": request.gallery_crisp.array_sha256,
            },
        },
        "orientation_decision": _without_evidence_fields(request.orientation_decision),
        "decision_links": _without_evidence_fields(request.decision_links),
    }
    return stable_id("run", payload)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(canonical_json(value))
        handle.flush()
        os.fsync(handle.fileno())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_product(
    root: Path,
    stem: str,
    product: FloatProduct,
    *,
    export_images: bool,
    quantizations: dict[str, Any],
) -> np.ndarray | None:
    write_npy(root / f"{stem}.npy", product.intensity)
    if not export_images:
        return None
    quantized, record = quantize_uint16(product.intensity, source_product_id=product.product_id)
    for suffix in ((".tif", ".png") if not stem.startswith("products/stages/") else (".tif",)):
        relative = f"{stem}{suffix}"
        write_uint16(root / relative, quantized)
        quantizations[relative] = record
    return quantized


def _write_contents(root: Path, request: ArtifactBundleRequest, run_id: str) -> dict[str, Any]:
    for name, value in (
        ("provenance/source.json", request.source),
        ("provenance/environment.json", request.environment),
        ("provenance/software.json", request.software),
        ("provenance/hardware.json", request.hardware),
        ("metadata/master-pattern.json", request.master_metadata),
        ("metadata/orientation-candidates.json", request.orientation_candidates),
        ("diagnostics/warnings.json", request.warnings),
        ("diagnostics/timings.json", request.timings),
        ("diagnostics/resources.json", request.resources),
        ("decisions/orientation.json", request.orientation_decision),
        ("decisions/links.json", request.decision_links),
    ):
        _write_json(root / name, value)
    for name in _RECIPE_NAMES:
        _write_json(root / f"recipes/{name}.json", request.recipes[name])

    quantizations: dict[str, Any] = {}
    _write_product(
        root, "products/projected", request.projected, export_images=False,
        quantizations=quantizations,
    )
    _write_product(
        root, "products/acquisition-corrected", request.acquisition_corrected,
        export_images=False, quantizations=quantizations,
    )
    for name, product in sorted(request.stages.items()):
        _write_product(
            root, f"products/stages/{name}", product, export_images=True,
            quantizations=quantizations,
        )
    _write_product(
        root, "products/scientific-clean", request.scientific_clean, export_images=True,
        quantizations=quantizations,
    )
    gallery = _write_product(
        root, "products/gallery-crisp", request.gallery_crisp, export_images=True,
        quantizations=quantizations,
    )
    assert gallery is not None
    write_preview(root / "products/preview.png", gallery)

    metrics = {
        "projected": image_metrics(request.projected.intensity),
        "acquisition-corrected": image_metrics(request.acquisition_corrected.intensity),
        "stages": {
            name: image_metrics(product.intensity) for name, product in sorted(request.stages.items())
        },
        "scientific-clean": image_metrics(request.scientific_clean.intensity),
        "gallery-crisp": image_metrics(request.gallery_crisp.intensity),
    }
    _write_json(root / "diagnostics/metrics.json", metrics)

    files = {
        str(path.relative_to(root)): {"sha256": _sha256(path), "bytes": path.stat().st_size}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
    return {
        "schema_version": 1,
        "run_id": run_id,
        "files": files,
        "uint16_exports": quantizations,
        "products": {
            "projected": {"product_id": request.projected.product_id},
            "acquisition_corrected": {
                "product_id": request.acquisition_corrected.product_id,
                "role": "background_model_corrected_before_aesthetic_processing",
            },
            "scientific_clean": {"product_id": request.scientific_clean.product_id},
            "gallery_crisp": {"product_id": request.gallery_crisp.product_id},
        },
        "comparison_exclusions": {
            "json_fields": ["**/captured_at", "**/created_at", "**/decided_at"],
            "json_documents": [
                "diagnostics/timings.json#/**",
                "diagnostics/resources.json#/**",
            ],
            "value_rules": [{"kind": "absolute_local_path", "scope": "**"}],
            "external_values": ["manifest_sha256"],
        },
    }


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_artifact_bundle(
    output_root: str | Path,
    request: ArtifactBundleRequest,
    *,
    resume_clean: bool = False,
    abandoned_at: str | None = None,
) -> BundleWriteResult:
    """Write, inventory, and atomically publish one immutable run bundle."""
    _validate(request)
    run_id = _run_id(request)
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    completed = root / run_id
    partial = root / f"{run_id}.partial"
    if completed.exists():
        raise BundleExistsError(f"completed bundle already exists: {completed}")
    if partial.exists():
        if not resume_clean:
            raise PartialBundleError(f"partial bundle requires resume_clean: {partial}")
        timestamp = abandoned_at or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z", timestamp):
            raise ValueError("abandoned_at must use YYYYMMDDTHHMMSSZ")
        abandoned = root / f"{run_id}.partial.{timestamp}.abandoned"
        if abandoned.exists():
            raise PartialBundleError(f"abandoned evidence destination exists: {abandoned}")
        partial.rename(abandoned)
        _fsync_directory(root)
    partial.mkdir()
    manifest = _write_contents(partial, request, run_id)
    manifest_path = partial / "manifest.json"
    _write_json(manifest_path, manifest)
    manifest_sha256 = _sha256(manifest_path)
    _fsync_directory(partial)
    partial.rename(completed)
    _fsync_directory(root)
    return BundleWriteResult(run_id=run_id, path=completed, manifest_sha256=manifest_sha256)
