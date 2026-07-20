"""Scientific invariants for mapping stereographic masters onto S2."""

from __future__ import annotations

from dataclasses import replace
from importlib import import_module
from importlib.metadata import version
from pathlib import Path
import sys

import numpy as np
import pytest

from kikuchi_lab.spherical_intensity import build_spherical_intensity


sys.path.insert(0, str(Path(__file__).parents[1]))
_fixtures = import_module("spherical_fixtures")
centrosymmetric_source = _fixtures.centrosymmetric_source
noncentrosymmetric_source = _fixtures.noncentrosymmetric_source
spherical_recipe = _fixtures.spherical_recipe
symmetric_master = _fixtures.symmetric_master
synthetic_simulation = _fixtures.synthetic_simulation


def _disk_indices(size: int = 5) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    coordinate = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    x_grid, y_grid = np.meshgrid(coordinate, coordinate)
    radius_squared = x_grid * x_grid + y_grid * y_grid
    tolerance = 32 * np.finfo(np.float64).eps
    return radius_squared <= 1.0 + tolerance, np.abs(radius_squared - 1.0) <= tolerance, coordinate


def _same_seam_different_interior() -> np.ndarray:
    upper = np.arange(25, dtype=np.float32).reshape(5, 5)
    for row, column in ((0, 2), (2, 0), (2, 4), (4, 2)):
        upper[row, column] = np.float32(100.0)
    lower = np.flip(upper, axis=(0, 1)).copy()
    _, equator, _ = _disk_indices()
    lower[equator] = upper[equator]
    return np.stack([upper, lower])


def test_geometry_mask_keeps_zero_inside_and_discards_nonzero_outside() -> None:
    master = symmetric_master()
    master[:, 0, 0] = np.float32(1234.0)
    master[0, 2, 2] = np.float32(0.0)

    build = build_spherical_intensity(
        synthetic_simulation(master),
        centrosymmetric_source(),
        spherical_recipe(),
    )

    center = (
        (build.field.hemisphere == 1)
        & (build.field.source_row == 2)
        & (build.field.source_column == 2)
    )
    assert build.field.intensity_raw[center].tolist() == [0.0]
    assert not np.any((build.field.source_row == 0) & (build.field.source_column == 0))


def test_upper_owns_equator_and_count_is_exact() -> None:
    build = build_spherical_intensity(
        synthetic_simulation(symmetric_master()),
        centrosymmetric_source(),
        spherical_recipe(),
    )
    diagnostics = build.diagnostics_dict()

    assert diagnostics["point_count"] == (
        2 * diagnostics["inside_count"] - diagnostics["equator_count"]
    )
    assert diagnostics["equator_source_indices"] == [[0, 2], [2, 0], [2, 4], [4, 2]]
    for row, column in diagnostics["equator_source_indices"]:
        matches = (build.field.source_row == row) & (build.field.source_column == column)
        assert build.field.hemisphere[matches].tolist() == [1]


def test_directional_source_columns_have_exact_upper_then_lower_row_major_order() -> None:
    build = build_spherical_intensity(
        synthetic_simulation(symmetric_master()),
        centrosymmetric_source(),
        spherical_recipe(),
    )
    inside, equator, _ = _disk_indices()
    rows, columns = np.indices((5, 5))
    expected_rows = np.concatenate([rows[inside], rows[inside & ~equator]])
    expected_columns = np.concatenate([columns[inside], columns[inside & ~equator]])

    np.testing.assert_array_equal(build.field.source_row, expected_rows)
    np.testing.assert_array_equal(build.field.source_column, expected_columns)
    np.testing.assert_array_equal(
        build.field.hemisphere,
        np.concatenate(
            [
                np.ones(np.count_nonzero(inside), dtype=np.int8),
                -np.ones(np.count_nonzero(inside & ~equator), dtype=np.int8),
            ]
        ),
    )


def test_seam_and_antipodal_diagnostics_use_different_index_rules() -> None:
    master = _same_seam_different_interior()
    build = build_spherical_intensity(
        synthetic_simulation(master),
        centrosymmetric_source(),
        spherical_recipe(),
    )
    diagnostics = build.diagnostics_dict()

    assert diagnostics["seam"] == {
        "index_rule": "same-index-equator",
        "maximum_absolute": 0.0,
        "rms": 0.0,
        "normalized_max": 0.0,
        "normalized_rms": 0.0,
    }
    assert diagnostics["antipodal"]["index_rule"] == (
        "upper[i,j]-lower[N-1-i,N-1-j]"
    )
    assert diagnostics["antipodal"]["normalized_max"] == 0.0
    assert diagnostics["antipodal"]["normalized_rms"] == 0.0


def test_seam_mismatch_is_rejected() -> None:
    master = symmetric_master()
    master[1, 0, 2] += np.float32(1.0)

    with pytest.raises(
        ValueError,
        match="upper/lower equator intensity mismatch exceeds tolerance",
    ):
        build_spherical_intensity(
            synthetic_simulation(master),
            centrosymmetric_source(),
            spherical_recipe(),
        )


def test_noncentrosymmetric_field_preserves_directional_values_and_refuses_axial() -> None:
    master = _same_seam_different_interior()
    master[1, 2, 2] += np.float32(7.0)
    source = noncentrosymmetric_source()
    build = build_spherical_intensity(
        synthetic_simulation(master, source=source),
        source,
        spherical_recipe(),
    )

    assert build.field.metadata["domain_semantics"] == "directional"
    assert build.axial_field is None
    assert build.diagnostics["axial"]["status"] == "phase-has-no-inversion"
    center = (build.field.source_row == 2) & (build.field.source_column == 2)
    assert build.field.intensity_raw[center].tolist() == [master[0, 2, 2], master[1, 2, 2]]


def test_centrosymmetric_low_residual_builds_axial_pairs_before_equator_omission() -> None:
    master = _same_seam_different_interior()
    build = build_spherical_intensity(
        synthetic_simulation(master),
        centrosymmetric_source(),
        spherical_recipe(),
    )
    assert build.axial_field is not None
    axial = build.axial_field

    expected_upper = np.asarray(
        [
            [1, 1],
            [1, 2],
            [1, 3],
            [2, 1],
            [2, 2],
            [2, 3],
            [2, 4],
            [3, 1],
            [3, 2],
            [3, 3],
            [4, 2],
        ],
        dtype=np.int32,
    )
    expected_pairs = np.stack(
        [
            np.column_stack([np.ones(len(expected_upper), dtype=np.int32), expected_upper]),
            np.column_stack(
                [
                    -np.ones(len(expected_upper), dtype=np.int32),
                    4 - expected_upper[:, 0],
                    4 - expected_upper[:, 1],
                ]
            ),
        ],
        axis=1,
    )
    np.testing.assert_array_equal(axial.source_pairs, expected_pairs)
    expected_raw = np.asarray(
        [
            np.float32((master[0, row, column] + master[1, 4 - row, 4 - column]) / 2)
            for row, column in expected_upper
        ],
        dtype=np.float32,
    )
    np.testing.assert_array_equal(axial.intensity_raw, expected_raw)
    realized_low = build.field.metadata["normalization"]["realized_low"]
    realized_high = build.field.metadata["normalization"]["realized_high"]
    expected_normalized = np.clip(
        (expected_raw.astype(np.float64) - realized_low) / (realized_high - realized_low),
        0.0,
        1.0,
    )
    np.testing.assert_allclose(axial.intensity_normalized, expected_normalized)
    np.testing.assert_allclose(
        axial.density_weight,
        expected_normalized ** spherical_recipe().density.exponent,
    )
    upper_lookup = {
        (int(row), int(column)): vector
        for row, column, vector in zip(
            build.field.source_row[build.field.hemisphere == 1],
            build.field.source_column[build.field.hemisphere == 1],
            build.field.xyz[build.field.hemisphere == 1],
            strict=True,
        )
    }
    np.testing.assert_array_equal(
        axial.xyz,
        np.asarray([upper_lookup[tuple(index)] for index in expected_upper]),
    )
    assert axial.metadata["axial"] == {
        "representative_rule": (
            "upper z > tolerance; on equator X > 0 or (X == 0 and Y >= 0)"
        ),
        "source_pair_rule": (
            "[upper,i,j] paired with original [lower,N-1-i,N-1-j] before "
            "lower-equator omission"
        ),
    }
    assert build.diagnostics["axial"]["status"] == "emitted"


def test_mixed_source_master_is_rejected_before_phase_symmetry_is_applied() -> None:
    master_source = centrosymmetric_source()
    other_source = noncentrosymmetric_source()
    simulation = synthetic_simulation(symmetric_master(), source=master_source)

    with pytest.raises(ValueError, match="supplied structure source identity"):
        build_spherical_intensity(simulation, other_source, spherical_recipe())


def test_missing_master_source_identity_is_rejected() -> None:
    simulation = synthetic_simulation(symmetric_master())
    metadata = dict(simulation.master_stereographic.metadata)
    del metadata["source_id"]
    object.__setattr__(simulation.master_stereographic, "metadata", metadata)

    with pytest.raises(ValueError, match="source_id provenance"):
        build_spherical_intensity(simulation, centrosymmetric_source(), spherical_recipe())


def test_master_and_ledger_source_identity_must_agree() -> None:
    simulation = synthetic_simulation(symmetric_master())
    ledger = {
        **simulation.projection_ledger,
        "source_method": {"phase_source_id": noncentrosymmetric_source().source_record.source_id},
    }
    object.__setattr__(simulation, "projection_ledger", ledger)

    with pytest.raises(ValueError, match="master and projection ledger source identity"):
        build_spherical_intensity(simulation, centrosymmetric_source(), spherical_recipe())


def test_master_and_reflection_catalog_energy_must_agree() -> None:
    simulation = synthetic_simulation(symmetric_master())
    object.__setattr__(simulation, "reflector_catalog", {"master": {"energy_kev": 21.0}})

    with pytest.raises(ValueError, match="master and reflector catalog energy"):
        build_spherical_intensity(simulation, centrosymmetric_source(), spherical_recipe())


def test_inversion_with_large_antipodal_residual_does_not_emit_axial() -> None:
    master = _same_seam_different_interior()
    master[1, 2, 2] += np.float32(7.0)

    build = build_spherical_intensity(
        synthetic_simulation(master),
        centrosymmetric_source(),
        spherical_recipe(),
    )

    assert build.axial_field is None
    assert build.diagnostics["axial"]["status"] == "antipodal-residual-exceeds-tolerance"


def test_axial_diagnostics_distinguish_observed_residuals_from_limits() -> None:
    recipe = spherical_recipe()
    build = build_spherical_intensity(
        synthetic_simulation(_same_seam_different_interior()),
        centrosymmetric_source(),
        recipe,
    )
    diagnostics = build.diagnostics

    assert diagnostics["axial"]["observed_normalized_rms"] == diagnostics["antipodal"][
        "normalized_rms"
    ]
    assert diagnostics["axial"]["observed_normalized_max"] == diagnostics["antipodal"][
        "normalized_max"
    ]
    assert diagnostics["axial"]["normalized_rms_limit"] == (
        recipe.tolerances.axial_normalized_rms_max
    )
    assert diagnostics["axial"]["normalized_max_limit"] == (
        recipe.tolerances.axial_normalized_max
    )


def test_channels_use_only_realized_percentiles_and_pointwise_power() -> None:
    master = _same_seam_different_interior()
    build = build_spherical_intensity(
        synthetic_simulation(master),
        centrosymmetric_source(),
        spherical_recipe(),
    )
    inside, equator, _ = _disk_indices()
    expected_raw = np.concatenate([master[0][inside], master[1][inside & ~equator]])
    expected_low, expected_high = np.percentile(expected_raw, [5.0, 99.85])
    expected_normalized = np.clip(
        (expected_raw.astype(np.float64) - expected_low) / (expected_high - expected_low),
        0.0,
        1.0,
    )

    assert build.field.intensity_raw.dtype == np.dtype("<f4")
    np.testing.assert_array_equal(build.field.intensity_raw, expected_raw)
    np.testing.assert_allclose(build.field.intensity_normalized, expected_normalized)
    np.testing.assert_allclose(build.field.density_weight, expected_normalized**1.5)
    normalization = build.field.metadata["normalization"]
    assert normalization["realized_low"] == pytest.approx(expected_low)
    assert normalization["realized_high"] == pytest.approx(expected_high)
    assert normalization["semantics"] == "pointwise percentile clip; no smoothing or blur"


def test_degenerate_percentile_window_is_rejected() -> None:
    master = np.ones((2, 5, 5), dtype=np.float32)
    with pytest.raises(ValueError, match="density percentile window must be non-degenerate"):
        build_spherical_intensity(
            synthetic_simulation(master),
            centrosymmetric_source(),
            spherical_recipe(),
        )


@pytest.mark.parametrize(
    ("simulation", "message"),
    [
        (
            synthetic_simulation(np.ones((2, 4, 4), dtype=np.float32)),
            "stereographic master shape must be",
        ),
        (
            synthetic_simulation(symmetric_master(), hemisphere_order=["lower", "upper"]),
            "hemisphere order",
        ),
        (
            synthetic_simulation(symmetric_master(), row_axis="Y descending"),
            "row-axis convention",
        ),
        (
            synthetic_simulation(symmetric_master(), column_axis="X descending"),
            "column-axis convention",
        ),
        (
            synthetic_simulation(symmetric_master(), grid_formula="coordinate[k] = k"),
            "grid formula",
        ),
        (
            synthetic_simulation(symmetric_master(), handedness="left-handed"),
            "right-handed",
        ),
    ],
)
def test_source_geometry_contract_is_validated(simulation, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build_spherical_intensity(simulation, centrosymmetric_source(), spherical_recipe())


def test_nonfinite_source_intensity_is_rejected_by_mapper() -> None:
    simulation = synthetic_simulation(symmetric_master())
    invalid = simulation.master_stereographic.intensity.copy()
    invalid[0, 2, 2] = np.nan
    object.__setattr__(simulation.master_stereographic, "intensity", invalid)

    with pytest.raises(ValueError, match="stereographic master intensity must be finite"):
        build_spherical_intensity(simulation, centrosymmetric_source(), spherical_recipe())


def test_source_energy_must_be_verified_product_metadata() -> None:
    simulation = synthetic_simulation(symmetric_master())
    object.__setattr__(
        simulation.master_stereographic,
        "metadata",
        {
            key: value
            for key, value in simulation.master_stereographic.metadata.items()
            if key != "energy_kev"
        },
    )

    with pytest.raises(ValueError, match="source energy_kev"):
        build_spherical_intensity(simulation, centrosymmetric_source(), spherical_recipe())


def test_directional_metadata_is_complete_and_path_neutral() -> None:
    simulation = synthetic_simulation(symmetric_master())
    source = centrosymmetric_source()
    build = build_spherical_intensity(simulation, source, spherical_recipe())
    metadata = build.field.metadata_dict()

    assert metadata["source"] == {
        "product_id": simulation.master_stereographic.product_id,
        "array_sha256": simulation.master_stereographic.array_sha256,
        "phase_source_id": source.source_record.source_id,
        "source_sha256": source.sha256,
        "kinematical_recipe_id": simulation.master_stereographic.metadata["recipe_id"],
        "shape": [2, 5, 5],
        "dtype": "float32",
        "energy_kev": 20.0,
    }
    assert metadata["projection"] == {
        "name": "stereographic",
        "hemisphere_order": ["upper", "lower"],
        "poles": {"upper": -1, "lower": 1},
        "transform_owner": "orix.projections.InverseStereographicProjection",
        "transform_version": version("orix"),
    }
    assert metadata["frame"] == {
        "name": "standard-Pnma direct and reciprocal Cartesian frames",
        "handedness": "right-handed",
        "vector_units": "dimensionless",
    }
    assert metadata["grid"] == {
        "size": 5,
        "row_axis": "Y ascending -1 to +1",
        "column_axis": "X ascending -1 to +1",
        "X_formula": "X(j) = -1 + 2*j/(N - 1)",
        "Y_formula": "Y(i) = -1 + 2*i/(N - 1)",
    }
    assert metadata["phase"] == {
        "space_group": source.space_group_number,
        "point_group": "mmm",
        "contains_inversion": True,
    }
    assert metadata["equator"]["owner"] == "upper"
    assert metadata["equator"]["index_rule"] == "same-index-equator"
    assert metadata["package_versions"] == {
        "kikuchi-lab": version("kikuchi-lab"),
        "numpy": version("numpy"),
        "orix": version("orix"),
    }
    assert "/Users/" not in repr(metadata)


def test_emit_axial_false_is_an_explicit_diagnostic_status() -> None:
    recipe = replace(spherical_recipe(), emit_axial=False)
    build = build_spherical_intensity(
        synthetic_simulation(symmetric_master()),
        centrosymmetric_source(),
        recipe,
    )
    assert build.axial_field is None
    assert build.diagnostics["axial"]["status"] == "disabled-by-recipe"
