"""Contain kikuchipy and orix types at the detector-projection boundary."""

from __future__ import annotations

import math
from importlib.metadata import version
from typing import Any

import numpy as np
from diffpy.structure import Lattice, Structure
from kikuchipy.detectors import EBSDDetector
from kikuchipy.signals import EBSDMasterPattern
from orix.crystal_map import Phase
from orix.quaternion import Rotation
from orix.vector import Vector3d

from kikuchi_lab.model.identity import stable_id
from kikuchi_lab.model.products import DetectorPatternProduct, MasterPatternProduct
from kikuchi_lab.model.recipes import DetectorRecipe, Orientation


def _active_crystal_to_sample_rotation(orientation: Orientation) -> Rotation:
    """Return the public active crystal-to-EDAX-TSL-sample rotation."""
    return Rotation.from_euler(
        orientation.euler_bunge_deg,
        degrees=True,
        direction="crystal2lab",
    )


def _to_kikuchipy_rotation(orientation: Orientation) -> Rotation:
    """Convert active crystal-to-sample into kikuchipy's passive convention."""
    return ~_active_crystal_to_sample_rotation(orientation)


def transform_crystal_direction_to_sample(
    direction: tuple[float, float, float] | list[float] | np.ndarray,
    orientation: Orientation,
) -> np.ndarray:
    """Transform a crystal direction into EDAX TSL sample coordinates.

    Returned coordinates are ordered ``[RD, TD, ND]``.
    """
    vector = np.asarray(direction, dtype=float)
    if vector.shape != (3,) or not np.isfinite(vector).all():
        raise ValueError("crystal direction must contain three finite values")
    transformed = _active_crystal_to_sample_rotation(orientation) * Vector3d(vector)
    return np.asarray(transformed.data[0], dtype=float)


def _to_kikuchipy_master_pattern(master: MasterPatternProduct) -> EBSDMasterPattern:
    metadata = master.metadata_dict()
    phase_metadata = metadata["phase"]
    lattice_values = phase_metadata["lattice"]["values"]
    lattice = Lattice(*lattice_values)
    structure = Structure(lattice=lattice, title=phase_metadata["name"])
    phase = Phase(
        name=phase_metadata["name"],
        space_group=phase_metadata["space_group"]["number"],
        structure=structure,
    )
    return EBSDMasterPattern(
        np.asarray(master.intensity, dtype=np.float32),
        phase=phase,
        projection="lambert",
        hemisphere="both",
    )


def _to_kikuchipy_detector(recipe: DetectorRecipe) -> EBSDDetector:
    return EBSDDetector(
        shape=recipe.supersampled_shape,
        px_size=recipe.pixel_size_um / recipe.supersampling,
        binning=recipe.binning,
        tilt=recipe.detector_tilt_deg,
        azimuthal=recipe.detector_azimuth_deg,
        twist=recipe.detector_twist_deg,
        sample_tilt=recipe.sample_tilt_deg,
        pc=(recipe.pcx, recipe.pcy, recipe.pcz),
        convention=recipe.pc_convention,
    )


def _projection_recipe_id(
    orientation: Orientation,
    detector: DetectorRecipe,
    energy_kev: float,
) -> str:
    return stable_id(
        "recipe",
        {
            "backend": "kikuchipy",
            "orientation": orientation.to_dict(),
            "detector": detector.to_dict(),
            "energy_kev": energy_kev,
        },
    )


def _projection_metadata(
    *,
    master: MasterPatternProduct,
    orientation: Orientation,
    detector: DetectorRecipe,
    energy_kev: float,
) -> dict[str, Any]:
    master_metadata = master.metadata_dict()
    metadata = {
        "backend": {"name": "kikuchipy", "version": version("kikuchipy")},
        "master_product_id": master.product_id,
        "master_array_sha256": master.array_sha256,
        "source_id": master_metadata["source_structure"]["source_id"],
        "provenance_links": master_metadata["provenance_links"],
        "phase": master_metadata["phase"],
        "orientation": orientation.to_dict(),
        "orientation_frame": orientation.frame,
        "detector": detector.to_dict(),
        "detector_frame": "EDAX-TSL:RD-TD-ND",
        "pc_convention": detector.pc_convention,
        "energy_kev": energy_kev,
        "intensity_units": master_metadata["intensity_units"],
        "supersampling": detector.supersampling,
        "downsampled": False,
    }
    upstream_checksum = master_metadata["simulation"].get("upstream_npz_sha256")
    if upstream_checksum is not None:
        metadata["upstream_artifact_sha256"] = upstream_checksum
    return metadata


def project_with_kikuchipy(
    *,
    master: MasterPatternProduct,
    orientation: Orientation,
    detector: DetectorRecipe,
    energy_kev: float,
) -> DetectorPatternProduct:
    """Project an integrated canonical master pattern without reloading NPZ."""
    energy = float(energy_kev)
    master_energy = float(master.metadata["energy_kev"])
    if not math.isfinite(energy) or energy <= 0:
        raise ValueError("projection energy must be finite and positive")
    if not math.isclose(energy, master_energy, rel_tol=1e-9, abs_tol=0.0):
        raise ValueError("projection energy is inconsistent with integrated master energy")

    master_signal = _to_kikuchipy_master_pattern(master)
    rotation = _to_kikuchipy_rotation(orientation)
    detector_model = _to_kikuchipy_detector(detector)
    signal = master_signal.get_patterns(
        rotation,
        detector_model,
        energy=energy,
        dtype_out="float32",
        compute=True,
        show_progressbar=False,
    )
    intensity = np.asarray(signal.data, dtype=np.float32)
    if intensity.shape != detector.supersampled_shape:
        singleton_shape = (1, *detector.supersampled_shape)
        if intensity.shape != singleton_shape:
            raise ValueError(
                "kikuchipy returned an unexpected detector pattern shape: "
                f"{intensity.shape!r}"
            )
        intensity = intensity[0]
    projection_recipe_id = _projection_recipe_id(orientation, detector, energy)
    return DetectorPatternProduct.from_array(
        intensity,
        master_product_id=master.product_id,
        projection_recipe_id=projection_recipe_id,
        metadata=_projection_metadata(
            master=master,
            orientation=orientation,
            detector=detector,
            energy_kev=energy,
        ),
    )
