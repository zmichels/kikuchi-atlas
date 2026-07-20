"""Canonical, atomic publication of standalone kinematical runs."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np

from kikuchi_lab.artifacts import BundleExistsError, PartialBundleError
from kikuchi_lab.artifacts.images import quantize_uint16, write_npy, write_uint16
from kikuchi_lab.model.identity import canonical_json, plain_data, stable_id
from kikuchi_lab.model.persistence import save_master_product
from kikuchi_lab.sources.structure import StructureRecord

from .contracts import (
    KinematicalArrayProduct,
    KinematicalExecution,
    KinematicalRecipe,
)
from .master_product import canonical_master_product


_FIGURE_NAMES = {
    "kinematical-stereographic-bands.svg",
    "kinematical-spherical-bands.png",
    "kinematical-detector-overlay.png",
    "etched-master-balanced.png",
    "etched-master-quiet.png",
    "reflector-selection.png",
}
_PRODUCT_STEMS = {
    "master-stereographic": "products/kinematical-master-stereographic",
    "master-lambert": "products/kinematical-master-lambert",
    "detector": "products/kinematical-detector",
}

# macOS SDK sys/fcntl.h and sys/stdio.h definitions used by renameatx_np(2).
_AT_FDCWD = -2
_RENAME_EXCL = 0x00000004


@dataclass(frozen=True)
class KinematicalBundleResult:
    run_id: str
    path: Path
    manifest_sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(canonical_json(value))
        handle.flush()
        os.fsync(handle.fileno())


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _write_hemisphere_array(path: Path, intensity: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        np.save(
            handle,
            np.asarray(intensity, dtype=np.float32, order="C"),
            allow_pickle=False,
        )
        handle.flush()
        os.fsync(handle.fileno())


def _source_payload(source: StructureRecord) -> dict[str, object]:
    return {
        "schema_version": 1,
        "identifier": source.identifier,
        "source_id": source.source_record.source_id,
        "sha256": source.sha256,
        "retrieved": source.retrieved,
        "page_uri": source.page_uri,
        "license_uri": source.license_uri,
        "copying_policy": source.copying_policy,
        "provenance": source.source_record.to_dict(),
        "phase": {
            "name": source.name,
            "formula": source.formula,
            "space_group_number": source.space_group_number,
            "setting": source.setting,
            "lattice_angstrom": list(source.lattice_angstrom),
        },
        "sites": [
            {
                "label": site.label,
                "element": site.element,
                "fract": list(site.fract),
                "occupancy": site.occupancy,
                "u_iso_angstrom_sq": site.u_iso_angstrom_sq,
            }
            for site in source.sites
        ],
        "thermal_factor_policy": source.thermal_factor_policy,
        "simulation_setting": source.simulation_setting,
    }


def _canonical_master(
    execution: KinematicalExecution,
    recipe: KinematicalRecipe,
    source: StructureRecord,
):
    master = execution.simulation.master_lambert
    if master.intensity.ndim != 3:
        return None
    return canonical_master_product(master, source=source, recipe=recipe)


def _run_identity(
    execution: KinematicalExecution,
    recipe: KinematicalRecipe,
    source: StructureRecord,
    canonical_master,
) -> dict[str, object]:
    simulation = execution.simulation
    return {
        "schema_version": 1,
        "recipe_id": recipe.recipe_id,
        "source_id": source.source_record.source_id,
        "source_sha256": source.sha256,
        "products": {
            label: {
                "product_id": product.product_id,
                "array_sha256": product.array_sha256,
            }
            for label, product in simulation.products().items()
        },
        "reflection_catalog_id": stable_id("reflection-catalog", simulation.reflector_catalog),
        "projection_ledger_id": stable_id("projection-ledger", simulation.projection_ledger),
        **(
            {
                "canonical_master": {
                    "product_id": canonical_master.product_id,
                    "array_sha256": canonical_master.array_sha256,
                }
            }
            if canonical_master is not None
            else {}
        ),
    }


def _hemisphere_order(
    execution: KinematicalExecution, label: str, product: KinematicalArrayProduct
) -> list[str]:
    if label == "detector":
        if product.intensity.ndim != 2:
            raise ValueError("detector product must be a two-dimensional array")
        return []
    projection_name = {
        "master-stereographic": "stereographic",
        "master-lambert": "lambert",
    }.get(label)
    projections = execution.simulation.projection_ledger.get("projections")
    if projection_name is None or not isinstance(projections, Mapping):
        raise ValueError(f"{label} lacks recorded hemisphere order")
    projection = projections.get(projection_name)
    if not isinstance(projection, Mapping):
        raise ValueError(f"{label} lacks recorded hemisphere order")
    order = plain_data(projection.get("hemisphere_order"))
    metadata_hemisphere = plain_data(product.metadata.get("hemisphere"))
    expected_order = {
        "upper": ["upper"],
        "lower": ["lower"],
        "both": ["upper", "lower"],
    }.get(metadata_hemisphere)
    ledger_hemisphere = projection.get("hemisphere")
    if (
        expected_order is None
        or order != expected_order
        or (ledger_hemisphere is not None and ledger_hemisphere != metadata_hemisphere)
    ):
        raise ValueError(f"{label} metadata disagrees with projection ledger hemisphere")
    plane_count = 1 if product.intensity.ndim == 2 else product.intensity.shape[0]
    if len(order) != plane_count:
        raise ValueError(f"{label} hemisphere array disagrees with projection ledger")
    return order


def _quantize_plane(
    product: KinematicalArrayProduct,
    image: np.ndarray,
    *,
    label: str,
) -> tuple[np.ndarray, dict[str, Any]]:
    quantized, record = quantize_uint16(
        image,
        label=label,
        source_product_id=product.product_id,
        source_content_id=product.product_id,
        source_array_sha256=product.array_sha256,
    )
    return quantized, record


def _write_product(
    root: Path,
    execution: KinematicalExecution,
    label: str,
    product: KinematicalArrayProduct,
) -> dict[str, object]:
    stem = _PRODUCT_STEMS[label]
    array_path = root / f"{stem}.npy"
    if product.intensity.ndim == 2:
        write_npy(array_path, product.intensity)
    else:
        _write_hemisphere_array(array_path, product.intensity)

    order = _hemisphere_order(execution, label, product)
    images = (
        [product.intensity]
        if product.intensity.ndim == 2
        else [product.intensity[index] for index in range(product.intensity.shape[0])]
    )
    names = order or ["detector"]
    mapped: list[np.ndarray] = []
    planes: list[dict[str, Any]] = []
    for name, image in zip(names, images, strict=True):
        quantized, record = _quantize_plane(product, image, label=f"{label}:{name}")
        mapped.append(quantized)
        planes.append({"hemisphere": name, **record})
    preview = mapped[0] if len(mapped) == 1 else np.concatenate(mapped, axis=1)
    write_uint16(root / f"{stem}.png", preview)
    return {
        "source_product_id": product.product_id,
        "source_array_sha256": product.array_sha256,
        "hemisphere_order": order,
        "composition": (
            "single-plane"
            if len(mapped) == 1
            else "pointwise-mapped planes concatenated side-by-side"
        ),
        "planes": planes,
    }


def _write_contents(
    root: Path,
    execution: KinematicalExecution,
    recipe: KinematicalRecipe,
    source: StructureRecord,
    run_id: str,
    run_identity: Mapping[str, object],
    canonical_master,
) -> dict[str, object]:
    _write_json(root / "provenance/source.json", _source_payload(source))
    _write_json(root / "recipes/kinematical.json", recipe.to_dict())
    _write_json(
        root / "models/reflection-catalog.json",
        execution.simulation.reflector_catalog,
    )
    _write_json(
        root / "diagnostics/projection-ledger.json",
        execution.simulation.projection_ledger,
    )

    png_exports = {
        f"{_PRODUCT_STEMS[label]}.png": _write_product(root, execution, label, product)
        for label, product in execution.simulation.products().items()
    }
    if canonical_master is not None:
        save_master_product(
            root / "products/canonical-kinematical-master.npz", canonical_master
        )
    for name, payload in execution.figures.items():
        _write_bytes(root / "figures" / name, payload)

    files = {
        str(path.relative_to(root)): {
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
    return {
        "schema_version": 1,
        "run_id": run_id,
        "run_identity": run_identity,
        **(
            {
                "canonical_master": {
                    "product_id": canonical_master.product_id,
                    "array_sha256": canonical_master.array_sha256,
                    "path": "products/canonical-kinematical-master.npz",
                }
            }
            if canonical_master is not None
            else {}
        ),
        "files": files,
        "png_exports": png_exports,
    }


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory_tree(root: Path) -> None:
    directories = sorted(
        (path for path in root.rglob("*") if path.is_dir()),
        key=lambda path: (-len(path.relative_to(root).parts), str(path.relative_to(root))),
    )
    for directory in directories:
        _fsync_directory(directory)
    _fsync_directory(root)


def _promote_directory_no_replace(source: Path, destination: Path) -> None:
    if sys.platform != "darwin":
        raise NotImplementedError(
            "atomic no-replace directory promotion requires macOS renameatx_np"
        )
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        renameatx_np = libc.renameatx_np
    except AttributeError:
        raise NotImplementedError(
            "macOS libc does not export renameatx_np for atomic no-replace promotion"
        ) from None
    renameatx_np.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameatx_np.restype = ctypes.c_int
    ctypes.set_errno(0)
    result = renameatx_np(
        _AT_FDCWD,
        os.fsencode(source),
        _AT_FDCWD,
        os.fsencode(destination),
        _RENAME_EXCL,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(
            error_number,
            os.strerror(error_number),
            str(source),
            str(destination),
        )


def _validate_execution(execution: KinematicalExecution) -> None:
    if set(execution.figures) != _FIGURE_NAMES:
        raise ValueError("kinematical execution figure inventory is not canonical")
    if set(execution.simulation.products()) != set(_PRODUCT_STEMS):
        raise ValueError("kinematical execution product inventory is not canonical")


def write_kinematical_bundle(
    output_root: str | Path,
    execution: KinematicalExecution,
    recipe: KinematicalRecipe,
    source: StructureRecord,
) -> KinematicalBundleResult:
    """Write, inventory, and atomically promote one immutable kinematical run."""
    _validate_execution(execution)
    canonical_master = _canonical_master(execution, recipe, source)
    run_identity = _run_identity(execution, recipe, source, canonical_master)
    run_id = stable_id("kinematical-run", run_identity)
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    completed = root / run_id
    ownership = root / f".{run_id}.publishing"
    try:
        ownership.mkdir()
    except FileExistsError:
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}") from None
        raise PartialBundleError(f"same-run publication already in progress: {ownership}") from None

    try:
        _fsync_directory(root)
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}")
        existing_partials = sorted(root.glob(f".{run_id}.partial-*"))
        if existing_partials:
            raise PartialBundleError(f"partial bundle already exists: {existing_partials[0]}")

        partial = root / f".{run_id}.partial-{uuid4().hex}"
        try:
            partial.mkdir()
        except FileExistsError:
            raise PartialBundleError(f"partial bundle already exists: {partial}") from None

        manifest = _write_contents(
            partial,
            execution,
            recipe,
            source,
            run_id,
            run_identity,
            canonical_master,
        )
        manifest_path = partial / "manifest.json"
        _write_json(manifest_path, manifest)
        manifest_sha256 = _sha256(manifest_path)
        _fsync_directory_tree(partial)
        if completed.exists():
            raise BundleExistsError(f"completed bundle already exists: {completed}")
        try:
            _promote_directory_no_replace(partial, completed)
        except OSError as error:
            if error.errno in {errno.EEXIST, errno.ENOTEMPTY} or completed.exists():
                raise BundleExistsError(f"completed bundle already exists: {completed}") from None
            raise PartialBundleError(
                f"partial bundle could not be promoted atomically: {partial}"
            ) from None
        return KinematicalBundleResult(
            run_id=run_id,
            path=completed,
            manifest_sha256=manifest_sha256,
        )
    finally:
        ownership.rmdir()
        _fsync_directory(root)


__all__ = ["KinematicalBundleResult", "write_kinematical_bundle"]
