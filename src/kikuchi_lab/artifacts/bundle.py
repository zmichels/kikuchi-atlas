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
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RECIPE_NAMES = ("simulation", "projection", "scientific-clean", "gallery-crisp")
_BACKGROUND_STAGE_NAMES = {"background_divide", "background_subtract"}
_AESTHETIC_STAGE_NAMES = {
    "robust_normalize",
    "local_contrast",
    "multiscale_detail",
    "unsharp",
    "tone_map",
    "downsample",
}
RUN_IDENTITY_SCHEMA = {
    "schema_version": 1,
    "included_fields": [
        "source.{source_id,sha256}",
        "master_metadata.{product_id,array_sha256}",
        "recipes.*.{recipe_id,recipe_sha256}",
        "recipes.projection.geometry_id",
        "software.identities.*.{version,distribution_sha256?}",
        "orientation_candidates.candidate_set_id",
        "products.*.{product_id,content_id,array_sha256}",
        "stage_lineage.*.{name,input_id,output_id}",
        "orientation_decision.decision_id",
        "decision_links.{orientation,processing,source_selection}?",
    ],
    "excluded_classes": [
        "unlisted provenance fields",
        "absolute or relative local paths",
        "retrieval or generation timestamps",
        "elapsed time and resource observations",
    ],
}


class BundleExistsError(FileExistsError):
    """Raised when a completed run already exists."""


class PartialBundleError(FileExistsError):
    """Raised when an incomplete run requires an explicit recovery choice."""


@dataclass(frozen=True)
class FloatProduct:
    product_id: str
    intensity: np.ndarray
    array_sha256: str = field(init=False)
    content_id: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.product_id, str) or not self.product_id:
            raise ValueError("float product requires a non-empty product_id")
        image = canonical_float_image(self.intensity)
        immutable = np.frombuffer(image.tobytes(order="C"), dtype=np.float32).reshape(image.shape)
        object.__setattr__(self, "intensity", immutable)
        checksum = hashlib.sha256(immutable.tobytes()).hexdigest()
        object.__setattr__(self, "array_sha256", checksum)
        object.__setattr__(
            self,
            "content_id",
            stable_id(
                "image",
                {"shape": list(immutable.shape), "dtype": "float32", "sha256": checksum},
            ),
        )


@dataclass(frozen=True)
class ArtifactBundleRequest:
    source: Mapping[str, Any]
    environment: Mapping[str, Any]
    software: Mapping[str, Any]
    hardware: Mapping[str, Any]
    recipes: Mapping[str, Mapping[str, Any]]
    master_metadata: Mapping[str, Any]
    orientation_candidates: Mapping[str, Any]
    projected: FloatProduct
    acquisition_corrected: FloatProduct
    stages: Mapping[str, FloatProduct]
    stage_lineage: Sequence[Mapping[str, Any]]
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


def _required_text(mapping: Mapping[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context} requires non-empty {key}")
    return value


def _required_sha256(mapping: Mapping[str, Any], key: str, context: str) -> str:
    value = _required_text(mapping, key, context)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{context} {key} must be a lowercase SHA-256")
    return value


def _software_identities(software: Mapping[str, Any]) -> dict[str, Any]:
    identities = software.get("identities")
    if not isinstance(identities, Mapping) or not identities:
        raise ValueError("software requires a non-empty identities mapping")
    stable: dict[str, Any] = {}
    for name, record in identities.items():
        if not isinstance(name, str) or not name or not isinstance(record, Mapping):
            raise ValueError("software identity records require package names and mappings")
        entry = {"version": _required_text(record, "version", f"software identity {name}")}
        distribution_sha256 = record.get("distribution_sha256")
        if distribution_sha256 is not None:
            entry["distribution_sha256"] = _required_sha256(
                record, "distribution_sha256", f"software identity {name}"
            )
        stable[name] = entry
    return stable


def _validated_lineage(request: ArtifactBundleRequest) -> list[dict[str, str]]:
    lineage = plain_data(request.stage_lineage)
    if not isinstance(lineage, list) or not lineage:
        raise ValueError("processing stage lineage is required")
    normalized: list[dict[str, str]] = []
    previous = request.projected.content_id
    background_seen = False
    for index, raw_record in enumerate(lineage):
        if not isinstance(raw_record, Mapping):
            raise ValueError("processing stage lineage entries must be objects")
        record = {
            key: _required_text(raw_record, key, f"processing stage lineage entry {index}")
            for key in ("name", "input_id", "output_id")
        }
        if record["input_id"] != previous:
            raise ValueError("processing stage lineage identity chain is discontinuous")
        if index == 0 and record["name"] not in _BACKGROUND_STAGE_NAMES:
            raise ValueError("background correction must be the first processing stage")
        if record["name"] in _AESTHETIC_STAGE_NAMES and not background_seen:
            raise ValueError("background correction must precede aesthetic processing stages")
        if record["name"] in _BACKGROUND_STAGE_NAMES:
            if background_seen:
                raise ValueError("processing stage lineage contains multiple background corrections")
            if record["output_id"] != request.acquisition_corrected.content_id:
                raise ValueError(
                    "acquisition-corrected product disagrees with background stage output"
                )
            background_seen = True
        normalized.append(record)
        previous = record["output_id"]
    if not background_seen:
        raise ValueError("processing stage lineage requires a named background correction stage")
    lineage_outputs = {record["output_id"] for record in normalized}
    missing = [
        name for name, product in request.stages.items() if product.content_id not in lineage_outputs
    ]
    if missing:
        raise ValueError(f"stage products are absent from processing lineage: {', '.join(missing)}")
    return normalized


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
    _required_text(request.source, "source_id", "source")
    _required_sha256(request.source, "sha256", "source")
    _required_text(request.master_metadata, "product_id", "master metadata")
    _required_sha256(request.master_metadata, "array_sha256", "master metadata")
    _required_text(request.orientation_candidates, "candidate_set_id", "orientation candidates")
    _required_text(request.orientation_decision, "decision_id", "orientation decision")
    for key in ("orientation", "processing", "source_selection"):
        if key in request.decision_links:
            _required_text(request.decision_links, key, "decision links")
    _software_identities(request.software)
    for name, recipe in request.recipes.items():
        _required_text(recipe, "recipe_id", f"{name} recipe")
        _required_sha256(recipe, "recipe_sha256", f"{name} recipe")
    _required_text(request.recipes["projection"], "geometry_id", "projection recipe")
    _validated_lineage(request)
    plain_data(
        {
            "source": request.source,
            "environment": request.environment,
            "software": request.software,
            "hardware": request.hardware,
            "recipes": request.recipes,
            "master_metadata": request.master_metadata,
            "orientation_candidates": request.orientation_candidates,
            "stage_lineage": request.stage_lineage,
            "warnings": request.warnings,
            "timings": request.timings,
            "resources": request.resources,
            "orientation_decision": request.orientation_decision,
            "decision_links": request.decision_links,
        }
    )


def _run_identity_payload(request: ArtifactBundleRequest) -> dict[str, Any]:
    lineage = _validated_lineage(request)
    recipe_identities = {
        name: {
            "recipe_id": recipe["recipe_id"],
            "recipe_sha256": recipe["recipe_sha256"],
        }
        for name, recipe in request.recipes.items()
    }
    recipe_identities["projection"]["geometry_id"] = request.recipes["projection"][
        "geometry_id"
    ]

    def product_identity(product: FloatProduct) -> dict[str, str]:
        return {
            "product_id": product.product_id,
            "content_id": product.content_id,
            "array_sha256": product.array_sha256,
        }

    return {
        "identity_schema_version": RUN_IDENTITY_SCHEMA["schema_version"],
        "source": {"source_id": request.source["source_id"], "sha256": request.source["sha256"]},
        "software": _software_identities(request.software),
        "recipes": recipe_identities,
        "master": {
            "product_id": request.master_metadata["product_id"],
            "array_sha256": request.master_metadata["array_sha256"],
        },
        "orientation_candidate_set_id": request.orientation_candidates["candidate_set_id"],
        "products": {
            "projected": product_identity(request.projected),
            "acquisition_corrected": product_identity(request.acquisition_corrected),
            "stages": {
                name: product_identity(product)
                for name, product in request.stages.items()
            },
            "scientific_clean": product_identity(request.scientific_clean),
            "gallery_crisp": product_identity(request.gallery_crisp),
        },
        "stage_lineage": lineage,
        "orientation_decision_id": request.orientation_decision["decision_id"],
        "decision_links": {
            key: request.decision_links[key]
            for key in ("orientation", "processing", "source_selection")
            if key in request.decision_links
        },
    }


def _run_id(request: ArtifactBundleRequest) -> str:
    return stable_id("run", _run_identity_payload(request))


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
        ("metadata/processing-lineage.json", _validated_lineage(request)),
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
        "run_identity": _run_identity_payload(request),
        "run_identity_schema": RUN_IDENTITY_SCHEMA,
        "processing_stage_lineage": _validated_lineage(request),
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
