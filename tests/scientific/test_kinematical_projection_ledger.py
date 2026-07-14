from dataclasses import replace
from importlib.metadata import version
from pathlib import Path

import pytest

from kikuchi_lab.kinematical import load_kinematical_recipe
from kikuchi_lab.kinematical.kikuchipy_adapter import (
    _projection_ledger,
    simulate_kinematical_arrays,
)
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "phases/forsterite/source.yml"
RECIPE = ROOT / "recipes/kinematical/forsterite-etched-master.yml"


@pytest.fixture(scope="module")
def small_simulation():
    recipe = replace(load_kinematical_recipe(RECIPE), half_size=32)
    record = load_structure_record(SOURCE)
    simulation, _ = simulate_kinematical_arrays(record, recipe)
    return record, recipe, simulation


def test_projection_ledger_centers_selected_metric_aware_011_axis(
    small_simulation,
) -> None:
    _, _, simulation = small_simulation

    check = simulation.projection_ledger["known_axis_check"]
    assert check["zone_axis_uvw"] == [0, 1, 1]
    assert check["expected_sample_direction"] == [0.0, 0.0, 1.0]
    assert check["misalignment_deg"] < 1e-6


def test_projection_ledger_records_source_methods_frames_and_coordinates(
    small_simulation,
) -> None:
    record, recipe, simulation = small_simulation

    ledger = simulation.projection_ledger
    assert set(ledger) == {
        "schema_version",
        "source_method",
        "frames",
        "projections",
        "known_axis_check",
        "presentation_space",
    }
    assert ledger["schema_version"] == 1
    assert ledger["source_method"] == {
        "phase_source_id": record.source_record.source_id,
        "reflection_engine": {"name": "diffsims", "version": version("diffsims")},
        "projection_engine": {
            "name": "kikuchipy",
            "version": version("kikuchipy"),
        },
    }
    assert ledger["frames"]["orientation"] == recipe.orientation.to_dict()
    assert ledger["frames"]["sample"] == "EDAX-TSL [RD, TD, ND]"
    assert ledger["frames"]["handedness"] == "right-handed"
    assert ledger["frames"]["units"] == {
        "direct_lattice": "angstrom",
        "reciprocal_lattice": "angstrom^-1",
    }
    assert ledger["frames"]["source_to_crystal"] == {
        "source_setting": "P b n m",
        "target_setting": "P n m a",
        "lattice_transform": {
            "target_from_source": ["b", "c", "a"],
            "equation": "(a', b', c') = (b, c, a)",
        },
        "fractional_coordinate_transform": {
            "target_from_source": ["y", "z", "x"],
            "equation": "(x', y', z') = (y, z, x)",
        },
    }
    assert ledger["frames"]["transform_owners"] == {
        "source_to_crystal": "kikuchi_lab.kinematical.kikuchipy_adapter._phase_from_record",
        "crystal_to_sample": (
            "kikuchi_lab.projection.kikuchipy_adapter."
            "_active_crystal_to_sample_rotation using orix"
        ),
        "sample_to_detector": "kikuchipy.EBSDDetector.sample_to_detector",
    }
    assert ledger["projections"]["stereographic"]["grid_formula"] == (
        "coordinate[k] = -1 + 2*k/(N-1)"
    )
    assert ledger["projections"]["detector"] == {
        "projection": "gnomonic",
        "pc_convention": "tsl",
        "coordinate_units": {
            "pixel": "pixel",
            "gnomonic": "dimensionless",
            "projection_center": "fraction",
        },
        "transform_owner": "kikuchipy.EBSDMasterPattern.get_patterns",
    }
    assert list(ledger["presentation_space"]) == [
        "labels",
        "minimum stroke width",
        "rim stroke",
    ]


@pytest.mark.parametrize(
    ("hemisphere", "expected_order"),
    [
        ("upper", ["upper"]),
        ("lower", ["lower"]),
        ("both", ["upper", "lower"]),
    ],
)
def test_projection_ledger_derives_hemisphere_order_from_recipe(
    hemisphere: str, expected_order: list[str]
) -> None:
    recipe = replace(load_kinematical_recipe(RECIPE), hemisphere=hemisphere)
    ledger = _projection_ledger(load_structure_record(SOURCE), recipe)

    for projection in ("stereographic", "lambert"):
        assert ledger["projections"][projection]["hemisphere"] == hemisphere
        assert ledger["projections"][projection]["hemisphere_order"] == expected_order


def test_projection_ledger_names_projection_transform_owners(small_simulation) -> None:
    _, _, simulation = small_simulation
    projections = simulation.projection_ledger["projections"]

    assert projections["stereographic"]["transform_owner"] == (
        "kikuchipy.KikuchiPatternSimulator.calculate_master_pattern"
    )
    assert projections["lambert"]["transform_owner"] == (
        "kikuchipy.EBSDMasterPattern.as_lambert"
    )


def test_array_products_record_complete_reproducibility_metadata(
    small_simulation,
) -> None:
    record, recipe, simulation = small_simulation

    for label, product in simulation.products().items():
        metadata = product.metadata
        assert metadata["source_id"] == record.source_record.source_id
        assert metadata["source_sha256"] == record.sha256
        assert metadata["recipe_id"] == recipe.recipe_id
        assert metadata["generators"] == {
            "reflection": {"name": "diffsims", "version": version("diffsims")},
            "projection": {
                "name": "kikuchipy",
                "version": version("kikuchipy"),
            },
        }
        assert metadata["energy_kev"] == 20.0
        assert metadata["threshold"]["relative_factor"] == 0.03
        assert metadata["hemisphere"] == "both"
        assert metadata["orientation"] == recipe.orientation.to_dict()
        assert metadata["detector"] == recipe.detector.to_dict()
        assert set(metadata["provenance_links"]) == {
            record.source_record.source_id,
            recipe.recipe_id,
            f"sha256:{record.sha256}",
        }
        assert metadata["projection"] == {
            "master-stereographic": "stereographic",
            "master-lambert": "lambert-square-equal-area",
            "detector": "gnomonic",
        }[label]
