from __future__ import annotations

import time

import numpy as np
import pytest

from kikuchi_lab.model.products import MasterPatternProduct
from kikuchi_lab.relief.field import (
    build_spherical_scalar_field,
    interpolate_sample_ledger,
    sample_spherical_field,
)
from kikuchi_lab.relief.mapping import (
    build_relief_geometry,
    filter_spherical_values,
    map_source_field,
    sample_mapped_field,
)
from kikuchi_lab.relief.recipes import ReliefMappingSpec, SphericalFilterSpec
from kikuchi_lab.relief.topology import build_icosphere
from tests.relief_fixtures import analytic_master_product, expectation_for


def mapping_spec(*, gamma: float = 1.0) -> ReliefMappingSpec:
    return ReliefMappingSpec((1.0, 99.0), gamma, "bright_outward")


def filter_spec() -> SphericalFilterSpec:
    return SphericalFilterSpec("spherical_gaussian", 0.8, 3.0)


def field_with_north_range_and_brighter_south():
    original = analytic_master_product(size=17)
    intensity = np.array(original.intensity, copy=True)
    intensity[1, 1:-1, 1:-1] += 10.0
    metadata = original.metadata_dict()
    metadata.pop("array")
    master = MasterPatternProduct.from_array(intensity, metadata=metadata)
    return build_spherical_scalar_field(master, expectation_for(master))


def angular_gaussian(
    directions: np.ndarray, *, center: list[float], fwhm_mm: float, radius_mm: float
) -> np.ndarray:
    center_array = np.asarray(center, dtype=np.float64)
    center_array /= np.linalg.norm(center_array)
    angles = np.arccos(np.clip(directions @ center_array, -1.0, 1.0))
    sigma = (fwhm_mm / radius_mm) / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    return np.exp(-0.5 * (angles / sigma) ** 2)


def test_global_mapping_uses_one_both_hemisphere_percentile_range():
    field = field_with_north_range_and_brighter_south()

    mapped = map_source_field(field, mapping_spec())

    assert mapped.lower_value == pytest.approx(np.percentile(field.raw_values, 1.0))
    assert mapped.upper_value == pytest.approx(np.percentile(field.raw_values, 99.0))
    assert mapped.north_grid.max() < 1.0
    assert mapped.south_grid.max() == 1.0


def test_mapping_precedes_sampling_and_reuses_exact_interpolation_ledger():
    field = field_with_north_range_and_brighter_south()
    topology = build_icosphere(2)
    mapped = map_source_field(field, mapping_spec(gamma=1.7))

    samples = sample_mapped_field(mapped, topology)

    raw = sample_spherical_field(field, topology.directions)
    expected = interpolate_sample_ledger(mapped.north_grid, mapped.south_grid, samples)
    assert np.array_equal(samples.directions, raw.directions)
    assert np.array_equal(samples.raw_values, raw.raw_values)
    assert np.array_equal(samples.hemisphere, raw.hemisphere)
    assert np.array_equal(samples.source_rows, raw.source_rows)
    assert np.array_equal(samples.source_columns, raw.source_columns)
    assert np.array_equal(samples.weights, raw.weights)
    assert np.array_equal(samples.mapped_values, expected)
    assert np.all((samples.mapped_values >= 0.0) & (samples.mapped_values <= 1.0))
    assert all(
        not array.flags.writeable
        for array in (
            samples.directions,
            samples.raw_values,
            samples.mapped_values,
            samples.hemisphere,
            samples.source_rows,
            samples.source_columns,
            samples.weights,
        )
    )


@pytest.mark.parametrize("gamma", [0.0, -1.0, np.nan, True])
def test_mapping_rejects_invalid_gamma(gamma):
    with pytest.raises(ValueError, match="gamma"):
        map_source_field(field_with_north_range_and_brighter_south(), mapping_spec(gamma=gamma))


def test_mapping_rejects_constant_or_collapsed_percentile_ranges():
    original = analytic_master_product(size=9)
    metadata = original.metadata_dict()
    metadata.pop("array")
    constant = MasterPatternProduct.from_array(
        np.ones_like(original.intensity), metadata=metadata
    )
    field = build_spherical_scalar_field(constant, expectation_for(constant))
    with pytest.raises(ValueError, match="percentile range"):
        map_source_field(field, mapping_spec())

    variable = field_with_north_range_and_brighter_south()
    with pytest.raises(ValueError, match="percentile"):
        map_source_field(variable, ReliefMappingSpec((50.0, 50.0), 1.0, "bright_outward"))


def test_filter_preserves_constant_at_coarse_resolution():
    topology = build_icosphere(4)
    constant, diagnostics = filter_spherical_values(
        np.full(len(topology.directions), 0.375),
        topology.directions,
        40.0,
        filter_spec(),
    )
    assert np.allclose(constant, 0.375, atol=1e-12, rtol=0)
    assert diagnostics.fwhm_rad == pytest.approx(0.8 / 40.0)
    assert diagnostics.constant_residual <= 1e-12
    assert diagnostics.minimum_neighbor_count > 0
    assert diagnostics.maximum_neighbor_count >= diagnostics.minimum_neighbor_count


def test_filter_is_invariant_under_rigid_rotation():
    topology = build_icosphere(3)
    values = 0.5 + 0.2 * topology.directions[:, 0] - 0.1 * topology.directions[:, 2]
    rotation = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], dtype=float)
    original, _ = filter_spherical_values(values, topology.directions, 40.0, filter_spec())
    rotated, _ = filter_spherical_values(
        values, topology.directions @ rotation.T, 40.0, filter_spec()
    )
    assert np.allclose(rotated, original, atol=2e-14, rtol=0)


@pytest.mark.parametrize(
    ("values", "directions", "radius", "match"),
    [
        ([0.0, np.nan], [[1, 0, 0], [0, 1, 0]], 40.0, "finite and aligned"),
        ([0.0], [[1, 0, 0], [0, 1, 0]], 40.0, "finite and aligned"),
        ([0.0], [[2, 0, 0]], 40.0, "unit"),
        ([0.0], [[1, 0, 0]], 0.0, "base radius"),
        ([0.0], [[1, 0, 0]], True, "base radius"),
    ],
)
def test_filter_rejects_invalid_inputs(values, directions, radius, match):
    with pytest.raises(ValueError, match=match):
        filter_spherical_values(values, directions, radius, filter_spec())


@pytest.mark.parametrize(
    "spec",
    [
        SphericalFilterSpec("other", 0.8, 3.0),
        SphericalFilterSpec("spherical_gaussian", 0.0, 3.0),
        SphericalFilterSpec("spherical_gaussian", 0.8, np.inf),
    ],
)
def test_filter_rejects_invalid_direct_specs(spec):
    with pytest.raises(ValueError, match="filter"):
        filter_spherical_values([0.0], [[1, 0, 0]], 40.0, spec)


def test_relief_geometry_is_outward_only_and_preserves_topology():
    topology = build_icosphere(3)
    values = np.linspace(0.0, 1.0, len(topology.directions))
    geometry = build_relief_geometry(
        topology, values, base_diameter_mm=80.0, maximum_relief_mm=1.2
    )
    assert np.array_equal(geometry.faces, topology.faces)
    assert not np.shares_memory(geometry.faces, topology.faces)
    assert np.array_equal(geometry.directions, topology.directions)
    assert not np.shares_memory(geometry.directions, topology.directions)
    assert np.linalg.norm(geometry.vertices, axis=1).min() == pytest.approx(40.0, abs=1e-10)
    assert np.linalg.norm(geometry.vertices, axis=1).max() == pytest.approx(41.2, abs=1e-10)
    assert all(
        not array.flags.writeable
        for array in (
            geometry.directions,
            geometry.faces,
            geometry.filtered_values,
            geometry.radii_mm,
            geometry.vertices,
        )
    )


@pytest.mark.parametrize(
    ("values", "diameter", "relief", "match"),
    [
        ([-0.01], 80.0, 1.2, r"\[0, 1\]"),
        ([1.01], 80.0, 1.2, r"\[0, 1\]"),
        ([np.nan], 80.0, 1.2, "finite and align"),
        ([0.5], 0.0, 1.2, "base diameter"),
        ([0.5], True, 1.2, "base diameter"),
        ([0.5], 80.0, 0.0, "maximum relief"),
        ([0.5], 80.0, True, "maximum relief"),
        ([0.5], 81.0, 1.2, "canonical geometry"),
        ([0.5], 80.0, 1.3, "canonical geometry"),
    ],
)
def test_relief_geometry_rejects_invalid_inputs(values, diameter, relief, match):
    topology = build_icosphere(0)
    full_values = np.full(len(topology.directions), values[0])
    with pytest.raises(ValueError, match=match):
        build_relief_geometry(topology, full_values, diameter, relief)


def test_relief_geometry_rejects_value_length_mismatch():
    topology = build_icosphere(1)
    with pytest.raises(ValueError, match="finite and align"):
        build_relief_geometry(topology, [0.5], 80.0, 1.2)


@pytest.mark.slow
def test_subdivision_seven_filter_completes_with_bounded_finite_output():
    topology = build_icosphere(7)
    narrow = angular_gaussian(
        topology.directions, center=[0, 0, 1], fwhm_mm=0.3, radius_mm=40
    )
    broad = angular_gaussian(
        topology.directions, center=[0, 0, 1], fwhm_mm=4.0, radius_mm=40
    )

    started = time.perf_counter()
    filtered_narrow, diagnostics = filter_spherical_values(
        narrow, topology.directions, 40.0, filter_spec()
    )
    filtered_broad, _ = filter_spherical_values(
        broad, topology.directions, 40.0, filter_spec()
    )
    elapsed = time.perf_counter() - started

    print(
        f"subdivision=7 vertices={len(narrow)} elapsed_s={elapsed:.6f} "
        f"neighbors={diagnostics.minimum_neighbor_count}:"
        f"{diagnostics.maximum_neighbor_count} "
        f"narrow_peak_ratio={filtered_narrow.max() / narrow.max():.12f} "
        f"broad_peak_ratio={filtered_broad.max() / broad.max():.12f}"
    )
    assert elapsed < 60.0
    assert np.isfinite(filtered_narrow).all()
    assert np.isfinite(filtered_broad).all()
    assert filtered_narrow.min() >= narrow.min()
    assert filtered_narrow.max() <= narrow.max()
    assert filtered_broad.min() >= broad.min()
    assert filtered_broad.max() <= broad.max()
    assert filtered_narrow.max() <= 0.5 * narrow.max()
    assert filtered_broad.max() >= 0.9 * broad.max()
