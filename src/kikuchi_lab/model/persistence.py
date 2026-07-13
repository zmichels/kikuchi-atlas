"""Versioned persistence for canonical pattern products."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import numpy as np

from .identity import canonical_json
from .products import MasterPatternProduct

MASTER_PRODUCT_SCHEMA_VERSION = 1


def _npz_path(path: str | Path) -> Path:
    resolved = Path(path)
    if resolved.suffix != ".npz":
        resolved = resolved.with_name(f"{resolved.name}.npz")
    return resolved


def save_master_product(path: str | Path, product: MasterPatternProduct) -> Path:
    """Write a canonical master product to a versioned NPZ container."""
    destination = _npz_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    envelope = {
        "schema_version": MASTER_PRODUCT_SCHEMA_VERSION,
        "product_id": product.product_id,
        "array_sha256": product.array_sha256,
        "metadata": product.metadata_dict(),
    }
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            np.savez_compressed(
                handle,
                intensity=np.asarray(product.intensity, dtype=np.float32, order="C"),
                meta_json=np.array(canonical_json(envelope)),
            )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def load_master_product(path: str | Path) -> MasterPatternProduct:
    """Load and fully validate a canonical master product NPZ."""
    with np.load(_npz_path(path), allow_pickle=False) as archive:
        if set(archive.files) != {"intensity", "meta_json"}:
            raise ValueError("master product NPZ must contain exactly intensity and meta_json")
        intensity = np.array(archive["intensity"], copy=True)
        raw_metadata = archive["meta_json"]
        if raw_metadata.ndim != 0:
            raise ValueError("meta_json must be a scalar UTF-8 JSON string")
        try:
            envelope = json.loads(str(raw_metadata.item()))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError("meta_json is not valid JSON") from error
    if not isinstance(envelope, dict):
        raise ValueError("meta_json envelope must be a JSON object")
    if envelope.get("schema_version") != MASTER_PRODUCT_SCHEMA_VERSION:
        raise ValueError(f"unsupported master product schema version: {envelope.get('schema_version')}")
    product = MasterPatternProduct.from_array(intensity, metadata=envelope.get("metadata", {}))
    if product.array_sha256 != envelope.get("array_sha256"):
        raise ValueError("master product array checksum mismatch")
    if product.product_id != envelope.get("product_id"):
        raise ValueError("master product identity mismatch")
    return product
