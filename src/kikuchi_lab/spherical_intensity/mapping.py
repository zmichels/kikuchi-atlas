"""Exact public-orix mapping of project-owned stereographic masters onto S2."""

from __future__ import annotations

import math
from importlib.metadata import version
from typing import Any

import numpy as np
from orix.crystal_map import Phase
from orix.projections import InverseStereographicProjection

from kikuchi_lab.kinematical.contracts import KinematicalSimulation
from kikuchi_lab.model.identity import plain_data
from kikuchi_lab.sources.structure import StructureRecord

from .contracts import (
    SphericalAxialField,
    SphericalIntensityBuild,
    SphericalIntensityField,
    SphericalIntensityRecipe,
)


_HEMISPHERE_ORDER = ["upper", "lower"]
_ROW_AXIS = "Y ascending -1 to +1"
_COLUMN_AXIS = "X ascending -1 to +1"
_SOURCE_GRID_FORMULA = "coordinate[k] = -1 + 2*k/(N-1)"
_X_FORMULA = "X(j) = -1 + 2*j/(N - 1)"
_Y_FORMULA = "Y(i) = -1 + 2*i/(N - 1)"
_DISK_EPSILON_MULTIPLIER = 32
_TRANSFORM_OWNER = "orix.projections.InverseStereographicProjection"


def _required_mapping(value: object, name: str) -> dict[str, Any]:
    plain = plain_data(value)
    if not isinstance(plain, dict):
        raise ValueError(f"{name} must be a mapping")
    return plain


def _validated_source(
    simulation: KinematicalSimulation,
    source: StructureRecord,
    recipe: SphericalIntensityRecipe,
) -> tuple[np.ndarray, dict[str, Any], float, dict[str, str]]:
    product = simulation.master_stereographic
    master = np.asarray(product.intensity)
    expected_size = 2 * recipe.profile.half_size + 1
    if master.shape != (2, expected_size, expected_size):
        raise ValueError(
            "stereographic master shape must be (2, 2*half_size+1, 2*half_size+1)"
        )
    if master.dtype != np.dtype(np.float32):
        raise ValueError("stereographic master intensity must use float32")
    if not np.isfinite(master).all():
        raise ValueError("stereographic master intensity must be finite")
    if recipe.tolerances.disk_epsilon_multiplier != _DISK_EPSILON_MULTIPLIER:
        raise ValueError("spherical disk epsilon multiplier must be 32")

    product_metadata = _required_mapping(product.metadata, "stereographic product metadata")
    if product.label != "master-stereographic":
        raise ValueError("spherical mapping source must be master-stereographic")
    if product_metadata.get("projection") != "stereographic":
        raise ValueError("spherical mapping source projection must be stereographic")
    if product_metadata.get("hemisphere") != "both":
        raise ValueError("spherical mapping source hemisphere must be both")
    master_source_id = product_metadata.get("source_id")
    if not isinstance(master_source_id, str) or not master_source_id.strip():
        raise ValueError("stereographic master source_id provenance is required")
    master_source_sha256 = product_metadata.get("source_sha256")
    if not isinstance(master_source_sha256, str) or not master_source_sha256.strip():
        raise ValueError("stereographic master source_sha256 provenance is required")
    kinematical_recipe_id = product_metadata.get("recipe_id")
    if not isinstance(kinematical_recipe_id, str) or not kinematical_recipe_id.strip():
        raise ValueError("stereographic master recipe_id provenance is required")
    energy = product_metadata.get("energy_kev")
    if (
        isinstance(energy, bool)
        or not isinstance(energy, (int, float))
        or not math.isfinite(float(energy))
        or float(energy) <= 0
    ):
        raise ValueError("stereographic source energy_kev must be positive and finite")

    ledger = _required_mapping(simulation.projection_ledger, "projection ledger")
    source_method = _required_mapping(
        ledger.get("source_method"),
        "projection ledger source method",
    )
    ledger_source_id = source_method.get("phase_source_id")
    if not isinstance(ledger_source_id, str) or not ledger_source_id.strip():
        raise ValueError("projection ledger phase_source_id provenance is required")
    if master_source_id != ledger_source_id:
        raise ValueError("master and projection ledger source identity must agree")
    supplied_source_id = source.source_record.source_id
    if master_source_id != supplied_source_id:
        raise ValueError(
            "stereographic master does not match supplied structure source identity"
        )
    if master_source_sha256 != source.sha256:
        raise ValueError("stereographic master does not match supplied structure source hash")

    reflector_catalog = _required_mapping(
        simulation.reflector_catalog,
        "reflection catalog",
    )
    master_reflections = _required_mapping(
        reflector_catalog.get("master"),
        "reflection catalog master",
    )
    reflection_energy = master_reflections.get("energy_kev")
    if (
        isinstance(reflection_energy, bool)
        or not isinstance(reflection_energy, (int, float))
        or not math.isfinite(float(reflection_energy))
        or float(reflection_energy) <= 0
    ):
        raise ValueError("reflection catalog master energy_kev must be positive and finite")
    if float(energy) != float(reflection_energy):
        raise ValueError("master and reflector catalog energy provenance must agree")

    projections = _required_mapping(ledger.get("projections"), "projection ledger projections")
    projection = _required_mapping(
        projections.get("stereographic"),
        "projection ledger stereographic projection",
    )
    if projection.get("hemisphere") != "both":
        raise ValueError("stereographic projection hemisphere must be both")
    if projection.get("hemisphere_order") != _HEMISPHERE_ORDER:
        raise ValueError("stereographic hemisphere order must be [upper, lower]")
    if projection.get("row_axis") != _ROW_AXIS:
        raise ValueError("stereographic row-axis convention is missing or unsupported")
    if projection.get("column_axis") != _COLUMN_AXIS:
        raise ValueError("stereographic column-axis convention is missing or unsupported")
    if projection.get("grid_formula") != _SOURCE_GRID_FORMULA:
        raise ValueError("stereographic grid formula is missing or unsupported")

    frames = _required_mapping(ledger.get("frames"), "projection ledger frames")
    frame_name = frames.get("crystal")
    if not isinstance(frame_name, str) or not frame_name.strip():
        raise ValueError("stereographic crystal frame must be non-empty text")
    if frames.get("handedness") != "right-handed":
        raise ValueError("stereographic frame must be right-handed")
    return (
        master,
        frames,
        float(energy),
        {
            "phase_source_id": master_source_id,
            "source_sha256": master_source_sha256,
            "kinematical_recipe_id": kinematical_recipe_id,
        },
    )


def _residual_diagnostic(delta: np.ndarray, scale: float, *, index_rule: str) -> dict[str, object]:
    maximum = float(np.max(np.abs(delta), initial=0.0))
    rms = float(np.sqrt(np.mean(delta * delta)))
    return {
        "index_rule": index_rule,
        "maximum_absolute": maximum,
        "rms": rms,
        "normalized_max": maximum / scale,
        "normalized_rms": rms / scale,
    }


def _common_metadata(
    *,
    simulation: KinematicalSimulation,
    source: StructureRecord,
    recipe: SphericalIntensityRecipe,
    master: np.ndarray,
    frames: dict[str, Any],
    source_provenance: dict[str, str],
    energy_kev: float,
    disk_tolerance: float,
    point_group: str,
    contains_inversion: bool,
    realized_low: float,
    realized_high: float,
    diagnostics: dict[str, object],
) -> dict[str, object]:
    product = simulation.master_stereographic
    size = master.shape[-1]
    return {
        "kind": "spherical_scalar_field",
        "domain": "S2",
        "domain_semantics": "directional",
        "recipe_id": recipe.recipe_id,
        "source": {
            "product_id": product.product_id,
            "array_sha256": product.array_sha256,
            **source_provenance,
            "shape": list(master.shape),
            "dtype": str(master.dtype),
            "energy_kev": energy_kev,
        },
        "projection": {
            "name": "stereographic",
            "hemisphere_order": list(_HEMISPHERE_ORDER),
            "poles": {"upper": -1, "lower": 1},
            "transform_owner": _TRANSFORM_OWNER,
            "transform_version": version("orix"),
        },
        "frame": {
            "name": frames["crystal"],
            "handedness": "right-handed",
            "vector_units": "dimensionless",
        },
        "grid": {
            "size": size,
            "row_axis": _ROW_AXIS,
            "column_axis": _COLUMN_AXIS,
            "X_formula": _X_FORMULA,
            "Y_formula": _Y_FORMULA,
        },
        "phase": {
            "space_group": source.space_group_number,
            "point_group": point_group,
            "contains_inversion": contains_inversion,
        },
        "equator": {
            "owner": "upper",
            "index_rule": "same-index-equator",
            "geometry_rule": "X^2 + Y^2 <= 1 + 32*eps(float64)",
            "tolerance": disk_tolerance,
            "lower_policy": "exclude equator",
        },
        "normalization": {
            "name": recipe.density.name,
            "low_percentile": recipe.density.low_percentile,
            "high_percentile": recipe.density.high_percentile,
            "realized_low": realized_low,
            "realized_high": realized_high,
            "clip": [0.0, 1.0],
            "exponent": recipe.density.exponent,
            "density_formula": "density_weight = intensity_normalized ** exponent",
            "semantics": "pointwise percentile clip; no smoothing or blur",
        },
        "diagnostics": diagnostics,
        "package_versions": {
            "kikuchi-lab": version("kikuchi-lab"),
            "numpy": version("numpy"),
            "orix": version("orix"),
        },
    }


def build_spherical_intensity(
    simulation: KinematicalSimulation,
    source: StructureRecord,
    recipe: SphericalIntensityRecipe,
) -> SphericalIntensityBuild:
    """Map one two-hemisphere stereographic master onto a directional S2 field."""
    master, frames, energy_kev, source_provenance = _validated_source(
        simulation,
        source,
        recipe,
    )
    size = master.shape[-1]
    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    x_grid, y_grid = np.meshgrid(coordinate, coordinate)
    radius_squared = x_grid * x_grid + y_grid * y_grid
    disk_tolerance = _DISK_EPSILON_MULTIPLIER * np.finfo(np.float64).eps
    inside = radius_squared <= 1.0 + disk_tolerance
    equator = np.abs(radius_squared - 1.0) <= disk_tolerance
    lower_keep = inside & ~equator
    rows, columns = np.indices((size, size))

    upper_vectors = np.asarray(
        InverseStereographicProjection(pole=-1)
        .xy2vector(x_grid[inside], y_grid[inside])
        .data,
        dtype=np.float64,
    )
    lower_vectors = np.asarray(
        InverseStereographicProjection(pole=1)
        .xy2vector(x_grid[lower_keep], y_grid[lower_keep])
        .data,
        dtype=np.float64,
    )
    xyz = np.concatenate([upper_vectors, lower_vectors])
    source_row = np.concatenate([rows[inside], rows[lower_keep]])
    source_column = np.concatenate([columns[inside], columns[lower_keep]])
    hemisphere = np.concatenate(
        [
            np.ones(np.count_nonzero(inside), dtype=np.int8),
            -np.ones(np.count_nonzero(lower_keep), dtype=np.int8),
        ]
    )

    inside_count = int(np.count_nonzero(inside))
    equator_count = int(np.count_nonzero(equator))
    point_count = int(xyz.shape[0])
    assert point_count == 2 * inside_count - equator_count
    unit_norm_max = float(np.max(np.abs(np.linalg.norm(xyz, axis=1) - 1.0), initial=0.0))
    if unit_norm_max > recipe.tolerances.unit_norm_max:
        raise ValueError("public-orix spherical vectors exceed the unit-norm tolerance")

    upper_diagnostic = np.asarray(master[0], dtype=np.float64)
    lower_diagnostic = np.asarray(master[1], dtype=np.float64)
    scale = max(float(np.max(master) - np.min(master)), np.finfo(np.float64).eps)
    seam_delta = upper_diagnostic[equator] - lower_diagnostic[equator]
    antipodal_delta = upper_diagnostic[inside] - np.flip(
        lower_diagnostic,
        axis=(0, 1),
    )[inside]
    seam = _residual_diagnostic(
        seam_delta,
        scale,
        index_rule="same-index-equator",
    )
    antipodal = _residual_diagnostic(
        antipodal_delta,
        scale,
        index_rule="upper[i,j]-lower[N-1-i,N-1-j]",
    )
    if seam["normalized_max"] > recipe.tolerances.equator_normalized_max:
        raise ValueError("upper/lower equator intensity mismatch exceeds tolerance")

    raw = np.concatenate([master[0][inside], master[1][lower_keep]])
    low, high = np.percentile(
        raw,
        [recipe.density.low_percentile, recipe.density.high_percentile],
    )
    realized_low = float(low)
    realized_high = float(high)
    if not realized_high > realized_low:
        raise ValueError("density percentile window must be non-degenerate")
    normalized = np.clip(
        (raw.astype(np.float64) - realized_low) / (realized_high - realized_low),
        0.0,
        1.0,
    )
    density_weight = normalized**recipe.density.exponent

    phase = Phase(name=source.name, space_group=source.space_group_number)
    point_group = phase.point_group.name
    contains_inversion = bool(phase.point_group.contains_inversion)
    axial_residual_allowed = (
        antipodal["normalized_rms"] <= recipe.tolerances.axial_normalized_rms_max
        and antipodal["normalized_max"] <= recipe.tolerances.axial_normalized_max
    )
    if not recipe.emit_axial:
        axial_status = "disabled-by-recipe"
    elif not contains_inversion:
        axial_status = "phase-has-no-inversion"
    elif not axial_residual_allowed:
        axial_status = "antipodal-residual-exceeds-tolerance"
    else:
        axial_status = "emitted"

    upper_z = upper_vectors[:, 2]
    upper_x = upper_vectors[:, 0]
    upper_y = upper_vectors[:, 1]
    representative = (upper_z > disk_tolerance) | (
        (np.abs(upper_z) <= disk_tolerance)
        & ((upper_x > 0) | ((upper_x == 0) & (upper_y >= 0)))
    )
    representative_count = int(np.count_nonzero(representative))
    diagnostics: dict[str, object] = {
        "point_count": point_count,
        "inside_count": inside_count,
        "equator_count": equator_count,
        "equator_source_indices": np.column_stack(
            [rows[equator], columns[equator]]
        ).tolist(),
        "unit_norm_max": unit_norm_max,
        "source_range_scale": scale,
        "seam": seam,
        "antipodal": antipodal,
        "axial": {
            "status": axial_status,
            "contains_inversion": contains_inversion,
            "observed_normalized_rms": antipodal["normalized_rms"],
            "observed_normalized_max": antipodal["normalized_max"],
            "normalized_rms_limit": recipe.tolerances.axial_normalized_rms_max,
            "normalized_max_limit": recipe.tolerances.axial_normalized_max,
            "representative_count": representative_count if axial_status == "emitted" else 0,
        },
    }
    metadata = _common_metadata(
        simulation=simulation,
        source=source,
        recipe=recipe,
        master=master,
        frames=frames,
        source_provenance=source_provenance,
        energy_kev=energy_kev,
        disk_tolerance=disk_tolerance,
        point_group=point_group,
        contains_inversion=contains_inversion,
        realized_low=realized_low,
        realized_high=realized_high,
        diagnostics=diagnostics,
    )
    field = SphericalIntensityField.from_columns(
        xyz=xyz,
        hemisphere=hemisphere,
        source_row=source_row,
        source_column=source_column,
        intensity_raw=raw,
        intensity_normalized=normalized,
        density_weight=density_weight,
        metadata=metadata,
    )

    axial_field: SphericalAxialField | None = None
    if axial_status == "emitted":
        upper_rows = rows[inside][representative]
        upper_columns = columns[inside][representative]
        lower_rows = size - 1 - upper_rows
        lower_columns = size - 1 - upper_columns
        axial_raw = np.asarray(
            (
                master[0, upper_rows, upper_columns].astype(np.float64)
                + master[1, lower_rows, lower_columns].astype(np.float64)
            )
            / 2.0,
            dtype=np.float32,
        )
        axial_normalized = np.clip(
            (axial_raw.astype(np.float64) - realized_low)
            / (realized_high - realized_low),
            0.0,
            1.0,
        )
        axial_density = axial_normalized**recipe.density.exponent
        source_pairs = np.stack(
            [
                np.column_stack(
                    [
                        np.ones(representative_count, dtype=np.int32),
                        upper_rows,
                        upper_columns,
                    ]
                ),
                np.column_stack(
                    [
                        -np.ones(representative_count, dtype=np.int32),
                        lower_rows,
                        lower_columns,
                    ]
                ),
            ],
            axis=1,
        )
        axial_metadata = dict(metadata)
        axial_metadata["domain_semantics"] = "axial-derived"
        axial_metadata["axial"] = {
            "representative_rule": (
                "upper z > tolerance; on equator X > 0 or (X == 0 and Y >= 0)"
            ),
            "source_pair_rule": (
                "[upper,i,j] paired with original [lower,N-1-i,N-1-j] before "
                "lower-equator omission"
            ),
        }
        axial_field = SphericalAxialField.from_columns(
            xyz=upper_vectors[representative],
            source_pairs=source_pairs,
            intensity_raw=axial_raw,
            intensity_normalized=axial_normalized,
            density_weight=axial_density,
            metadata=axial_metadata,
        )

    return SphericalIntensityBuild(
        field=field,
        axial_field=axial_field,
        diagnostics=diagnostics,
    )
