"""Canonical atomic publication for standalone near-depth render runs."""

from __future__ import annotations

import errno
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import numpy as np

from kikuchi_lab.artifacts import BundleExistsError, PartialBundleError
from kikuchi_lab.kinematical.bundle import (
    _fsync_directory,
    _fsync_directory_tree,
    _promote_directory_no_replace,
    _write_bytes,
    _write_json,
)
from kikuchi_lab.kinematical.contracts import KinematicalRecipe, KinematicalSimulation
from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.sources.structure import StructureRecord

from .contracts import NearDepthTreatmentRecipe
from .overlap import OverlapField
from .render import NearDepthRender


@dataclass(frozen=True)
class NearDepthBundleResult:
    run_id: str
    path: Path
    manifest_sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _array_sha256(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    return hashlib.sha256(value.tobytes(order="C")).hexdigest()


def _write_array(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        np.save(handle, np.asarray(array, dtype=np.float32, order="C"), allow_pickle=False)
        handle.flush()
        os.fsync(handle.fileno())


def _run_identity(
    render: NearDepthRender,
    overlap: OverlapField,
    simulation: KinematicalSimulation,
    treatment: NearDepthTreatmentRecipe,
    base_recipe: KinematicalRecipe,
    source: StructureRecord,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "treatment_recipe_id": treatment.recipe_id,
        "base_recipe_id": base_recipe.recipe_id,
        "source_id": source.source_record.source_id,
        "source_sha256": source.sha256,
        "base_stereographic_product_id": simulation.master_stereographic.product_id,
        "base_stereographic_array_sha256": (
            simulation.master_stereographic.array_sha256
        ),
        "overlap_raw_sha256": _array_sha256(overlap.raw),
        "overlap_normalized_sha256": _array_sha256(overlap.normalized),
        "overlap_metadata_id": stable_id("overlap-metadata", overlap.metadata),
        "depth_ledger_id": stable_id("depth-ledger", render.ledger),
    }


def _write_contents(
    root: Path,
    render: NearDepthRender,
    overlap: OverlapField,
    treatment: NearDepthTreatmentRecipe,
    run_id: str,
    run_identity: dict[str, object],
) -> dict[str, object]:
    for name, payload in render.figures.items():
        _write_bytes(root / "figures" / name, payload)
    _write_array(root / "diagnostics" / "overlap-additional-depth.npy", overlap.raw)
    _write_bytes(
        root / "diagnostics" / "overlap-additional-depth.png",
        render.diagnostic_png,
    )
    _write_json(root / "diagnostics" / "depth-render-ledger.json", render.ledger)
    _write_json(root / "recipes" / "near-depth.json", treatment.to_dict())
    files = {
        str(path.relative_to(root)): {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
    return {
        "schema_version": 1,
        "run_id": run_id,
        "run_identity": run_identity,
        "files": files,
    }


def write_near_depth_bundle(
    output_root: str | Path,
    render: NearDepthRender,
    overlap: OverlapField,
    simulation: KinematicalSimulation,
    treatment: NearDepthTreatmentRecipe,
    base_recipe: KinematicalRecipe,
    source: StructureRecord,
) -> NearDepthBundleResult:
    """Write, inventory, and atomically promote one immutable depth run."""
    if treatment.expected_kinematical_recipe_id != base_recipe.recipe_id:
        raise ValueError("near-depth treatment does not match the supplied base recipe ID")
    if simulation.master_stereographic.metadata.get("source_id") != source.source_record.source_id:
        raise ValueError("near-depth base product does not match the supplied source")
    run_identity = _run_identity(
        render,
        overlap,
        simulation,
        treatment,
        base_recipe,
        source,
    )
    run_id = stable_id("near-depth-run", run_identity)
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
        partial.mkdir()
        manifest = _write_contents(
            partial,
            render,
            overlap,
            treatment,
            run_id,
            run_identity,
        )
        manifest_path = partial / "manifest.json"
        _write_json(manifest_path, manifest)
        manifest_sha256 = _sha256(manifest_path)
        _fsync_directory_tree(partial)
        try:
            _promote_directory_no_replace(partial, completed)
        except OSError as error:
            if error.errno in {errno.EEXIST, errno.ENOTEMPTY} or completed.exists():
                raise BundleExistsError(f"completed bundle already exists: {completed}") from None
            raise PartialBundleError(
                f"partial bundle could not be promoted atomically: {partial}"
            ) from None
        return NearDepthBundleResult(
            run_id=run_id,
            path=completed,
            manifest_sha256=manifest_sha256,
        )
    finally:
        ownership.rmdir()
        _fsync_directory(root)


__all__ = ["NearDepthBundleResult", "write_near_depth_bundle"]
