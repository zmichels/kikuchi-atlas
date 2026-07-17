"""Reproducible, review-gated project workflows."""

from __future__ import annotations

from typing import Any

from .final import (
    FinalRecipe,
    FinalRecipeError,
    FinalReproductionResult,
    FinalRunResult,
    FinalSelectionError,
    ReproductionComparison,
    ReproductionMismatch,
    ValidatedFinalSelection,
    compare_final_bundles,
    load_final_recipe,
    reproduce_final,
    render_final,
    validate_final_selection,
)
from .proof import (
    ProofMasterError,
    ProofRecipeError,
    ProofRunResult,
    load_proof_recipe,
    render_proof,
)
from .kinematical import KinematicalRunResult, render_kinematical
from .near_depth import NearDepthRunResult, render_kinematical_depth
from .oriented_spherical import (
    OrientedSphericalRunResult,
    render_oriented_spherical_master,
)
from .ice_art_catalog import (
    IceArtCatalogRecipe,
    IceArtCatalogResult,
    IceArtCatalogTimeoutError,
    build_ice_art_catalog,
    load_ice_art_catalog_recipe,
)
from .ice_tattoo import IceTattooResult, render_ice_tattoo
from .direct_art_catalog import DirectArtCatalogResult, build_direct_art_catalog
from .phase_art_series import (
    IceStandardReferenceMismatch,
    PhaseArtSeriesResult,
    PhaseParityReportError,
    render_phase_art_series,
)

__all__ = [
    "FinalRecipe",
    "FinalRecipeError",
    "FinalReproductionResult",
    "FinalRunResult",
    "FinalSelectionError",
    "DirectArtCatalogResult",
    "IceArtCatalogRecipe",
    "IceArtCatalogResult",
    "IceArtCatalogTimeoutError",
    "IceTattooResult",
    "IceStandardReferenceMismatch",
    "KinematicalRunResult",
    "NearDepthRunResult",
    "OrientedSphericalRunResult",
    "PhaseArtSeriesResult",
    "PhaseParityReportError",
    "ReproductionComparison",
    "ReproductionMismatch",
    "ProofMasterError",
    "ProofRecipeError",
    "ProofRunResult",
    "ReflectorParityTimeoutError",
    "ReflectorParityWorkerError",
    "ValidatedFinalSelection",
    "compare_final_bundles",
    "build_direct_art_catalog",
    "build_ice_art_catalog",
    "load_final_recipe",
    "load_ice_art_catalog_recipe",
    "load_proof_recipe",
    "render_proof",
    "render_final",
    "render_kinematical",
    "render_kinematical_depth",
    "render_oriented_spherical_master",
    "render_phase_art_series",
    "render_ice_tattoo",
    "run_reflector_parity",
    "validate_final_selection",
    "reproduce_final",
]


def __getattr__(name: str) -> Any:
    if name in {
        "ReflectorParityTimeoutError",
        "ReflectorParityWorkerError",
        "run_reflector_parity",
    }:
        from .reflector_parity import (
            ReflectorParityTimeoutError,
            ReflectorParityWorkerError,
            run_reflector_parity,
        )

        return {
            "ReflectorParityTimeoutError": ReflectorParityTimeoutError,
            "ReflectorParityWorkerError": ReflectorParityWorkerError,
            "run_reflector_parity": run_reflector_parity,
        }[name]
    raise AttributeError(name)
