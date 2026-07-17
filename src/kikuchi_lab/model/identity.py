"""Canonical serialization and content-derived identities."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

_KIND = re.compile(r"^[a-z][a-z0-9_-]*$")

CANONICAL_JSON_SERIALIZATION_CONTRACT = "canonical-json/sorted-compact-unicode/v1"


def plain_data(value: Any) -> Any:
    """Return JSON-compatible Python values, rejecting ambiguous values."""
    if isinstance(value, np.generic):
        value = value.item()
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON requires finite floating-point values")
        return value
    if isinstance(value, Mapping):
        converted: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical JSON object keys must be strings")
            converted[key] = plain_data(item)
        return converted
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [plain_data(item) for item in value]
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize *value* deterministically as compact Unicode JSON."""
    return json.dumps(
        plain_data(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def stable_id(kind: str, payload: Any) -> str:
    """Return a short, namespaced SHA-256 identity for canonical *payload*."""
    if not _KIND.fullmatch(kind):
        raise ValueError("identity kind must be lowercase ASCII with optional digits, _ or -")
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"{kind}-{digest[:16]}"
