"""Float-preserving storage and explicit image quantization boundaries."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import imageio.v3 as iio
import numpy as np
import tifffile


def canonical_float_image(value: Any) -> np.ndarray:
    image = np.asarray(value, dtype=np.float32)
    if image.ndim != 2 or not image.size or not np.isfinite(image).all():
        raise ValueError("float product must be a non-empty finite two-dimensional array")
    return np.ascontiguousarray(image)


def quantize_uint16(image: np.ndarray, *, source_product_id: str) -> tuple[np.ndarray, dict]:
    black, white = (float(value) for value in np.percentile(image, [0.5, 99.5]))
    if white == black:
        white = black + 1.0
    normalized = np.clip((image.astype(np.float64) - black) / (white - black), 0.0, 1.0)
    quantized = np.rint(normalized * 65535.0).astype(np.uint16)
    return quantized, {
        "source_product_id": source_product_id,
        "scale": (white - black) / 65535.0,
        "offset": black,
        "black_point": black,
        "white_point": white,
        "clipping_below_black": float(np.count_nonzero(image < black) / image.size),
        "clipping_above_white": float(np.count_nonzero(image > white) / image.size),
    }


def write_npy(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        np.save(handle, canonical_float_image(image), allow_pickle=False)
        handle.flush()
        os.fsync(handle.fileno())


def write_uint16(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".tif":
        tifffile.imwrite(path, image, photometric="minisblack", metadata=None)
    elif path.suffix == ".png":
        iio.imwrite(path, image, extension=".png")
    else:
        raise ValueError(f"unsupported uint16 image format: {path.suffix}")
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def write_preview(path: Path, quantized: np.ndarray) -> None:
    preview = np.rint(quantized.astype(np.float64) / 257.0).astype(np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    iio.imwrite(path, preview, extension=".png")
    with path.open("rb") as handle:
        os.fsync(handle.fileno())
