"""Integrity contracts for lightweight acquired-pattern reference packs."""

from .integrity import (
    SourceFileFingerprint,
    SourceInventoryManifest,
    SourceInventoryVerification,
    load_source_inventory_manifest,
    sha256_file,
    verify_exact_source_inventory,
)
from .ni_hough import HoughVariantSummary, summarize_variant

__all__ = [
    "SourceFileFingerprint",
    "SourceInventoryManifest",
    "SourceInventoryVerification",
    "HoughVariantSummary",
    "load_source_inventory_manifest",
    "sha256_file",
    "summarize_variant",
    "verify_exact_source_inventory",
]
