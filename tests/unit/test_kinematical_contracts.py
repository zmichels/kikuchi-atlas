from dataclasses import FrozenInstanceError
from pathlib import Path

import numpy as np
import pytest
import yaml

from kikuchi_lab.kinematical import (
    KinematicalArrayProduct,
    KinematicalExecution,
    KinematicalSimulation,
    load_kinematical_recipe,
)


RECIPE = (
    Path(__file__).parents[2]
    / "recipes"
    / "kinematical"
    / "forsterite-etched-master.yml"
)


def _recipe_payload() -> dict[str, object]:
    payload = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _section(payload: dict[str, object], name: str) -> dict[str, object]:
    section = payload[name]
    assert isinstance(section, dict)
    return section


def _write_recipe(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "kinematical.yml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _array_product(label: str, value: float) -> KinematicalArrayProduct:
    return KinematicalArrayProduct.from_array(
        label,
        np.full((2, 2), value, dtype=np.float32),
        metadata={"projection": label},
    )


def test_forsterite_kinematical_recipe_fixes_two_etched_styles() -> None:
    recipe = load_kinematical_recipe(RECIPE)
    assert recipe.energy_kev == 20.0
    assert recipe.orientation.euler_bunge_deg == (45.0, 51.50414783, 0.0)
    assert recipe.zone_axis_uvw == (0, 1, 1)
    assert recipe.min_dspacing_angstrom == 0.7
    assert recipe.master_relative_factor == 0.03
    assert recipe.promoted_style == "quiet"
    assert recipe.hemisphere == "both"
    assert [(style.name, style.overlay_relative_factor) for style in recipe.styles] == [
        ("balanced", 0.14),
        ("quiet", 0.22),
    ]


def test_kinematical_array_product_owns_finite_float32_data() -> None:
    source = np.arange(25, dtype=np.float64).reshape(5, 5)
    product = KinematicalArrayProduct.from_array(
        "master-stereographic",
        source,
        metadata={"projection": "stereographic", "hemisphere": "upper"},
    )
    source[:] = -1
    assert product.intensity.dtype == np.float32
    assert not product.intensity.flags.writeable
    assert product.intensity[0, 0] == 0
    assert product.product_id.startswith("kinematical-")


def test_kinematical_array_product_deeply_freezes_plain_metadata() -> None:
    metadata = {
        "projection": "stereographic",
        "coordinates": {"frames": ["crystal", {"target": "sample"}]},
    }
    product = KinematicalArrayProduct.from_array(
        "master-stereographic", np.ones((2, 2)), metadata=metadata
    )

    metadata["projection"] = "changed"
    metadata["coordinates"]["frames"][1]["target"] = "changed"

    assert product.metadata["projection"] == "stereographic"
    assert product.metadata["coordinates"]["frames"][1]["target"] == "sample"
    with pytest.raises(TypeError):
        product.metadata["projection"] = "changed"
    with pytest.raises(TypeError):
        product.metadata["coordinates"]["frames"][1]["target"] = "changed"


@pytest.mark.parametrize(
    "intensity",
    [
        np.array([], dtype=np.float32),
        np.array([1.0], dtype=np.float32),
        np.array([[np.nan]], dtype=np.float32),
        np.zeros((1, 1, 1, 1), dtype=np.float32),
    ],
)
def test_kinematical_array_product_rejects_empty_nonfinite_or_wrong_rank_data(
    intensity: np.ndarray,
) -> None:
    with pytest.raises(ValueError, match="finite, non-empty, and 2D or 3D"):
        KinematicalArrayProduct.from_array("invalid", intensity, metadata={})


def test_loader_rejects_unknown_top_level_fields(tmp_path: Path) -> None:
    payload = _recipe_payload()
    payload["unknown"] = "not-supported"

    with pytest.raises(ValueError, match="top-level fields differ"):
        load_kinematical_recipe(_write_recipe(tmp_path, payload))


def test_loader_rejects_unknown_nested_fields(tmp_path: Path) -> None:
    payload = _recipe_payload()
    _section(payload, "orientation")["unknown"] = "not-supported"

    with pytest.raises(ValueError, match="orientation fields differ"):
        load_kinematical_recipe(_write_recipe(tmp_path, payload))


@pytest.mark.parametrize("schema_version", [True, 2, "1"])
def test_loader_requires_integer_schema_version_one(
    tmp_path: Path, schema_version: object
) -> None:
    payload = _recipe_payload()
    payload["schema_version"] = schema_version

    with pytest.raises(ValueError, match="schema_version must be integer 1"):
        load_kinematical_recipe(_write_recipe(tmp_path, payload))


def test_loader_rejects_unsupported_hemisphere(tmp_path: Path) -> None:
    payload = _recipe_payload()
    _section(payload, "master")["hemisphere"] = "north"

    with pytest.raises(ValueError, match="hemisphere must be upper, lower, or both"):
        load_kinematical_recipe(_write_recipe(tmp_path, payload))


def test_loader_requires_square_master_scaling(tmp_path: Path) -> None:
    payload = _recipe_payload()
    _section(payload, "master")["scaling"] = "linear"

    with pytest.raises(ValueError, match="master scaling must be square"):
        load_kinematical_recipe(_write_recipe(tmp_path, payload))


def test_loader_requires_ordered_uniquely_named_styles(tmp_path: Path) -> None:
    payload = _recipe_payload()
    styles = payload["styles"]
    assert isinstance(styles, list)
    assert isinstance(styles[1], dict)
    styles[1]["name"] = "balanced"

    with pytest.raises(ValueError, match="style names must be unique"):
        load_kinematical_recipe(_write_recipe(tmp_path, payload))


def test_loader_requires_promoted_style_to_name_exactly_one_style(tmp_path: Path) -> None:
    payload = _recipe_payload()
    payload["promoted_style"] = "missing"

    with pytest.raises(ValueError, match="promoted_style must name exactly one style"):
        load_kinematical_recipe(_write_recipe(tmp_path, payload))


def test_loader_reports_that_zone_axis_indices_are_not_all_zero(tmp_path: Path) -> None:
    payload = _recipe_payload()
    _section(payload, "orientation")["zone_axis_uvw"] = [0, 0, 0]

    with pytest.raises(ValueError, match="three integer indices, not all zero"):
        load_kinematical_recipe(_write_recipe(tmp_path, payload))


def test_kinematical_simulation_deeply_freezes_catalog_and_ledger() -> None:
    catalog_entry = {"hkl": [0, 1, 1], "selection": {"retained": True}}
    ledger = {"frames": ["crystal", "sample"], "spot_check": {"aligned": True}}
    simulation = KinematicalSimulation(
        master_stereographic=_array_product("master-stereographic", 1.0),
        master_lambert=_array_product("master-lambert", 2.0),
        detector=_array_product("detector", 3.0),
        reflector_catalog=(catalog_entry,),
        projection_ledger=ledger,
    )

    catalog_entry["selection"]["retained"] = False
    ledger["spot_check"]["aligned"] = False

    assert simulation.reflector_catalog[0]["selection"]["retained"] is True
    assert simulation.projection_ledger["spot_check"]["aligned"] is True
    with pytest.raises(TypeError):
        simulation.reflector_catalog[0]["selection"]["retained"] = False
    with pytest.raises(TypeError):
        simulation.projection_ledger["spot_check"]["aligned"] = False


def test_kinematical_execution_owns_an_immutable_figure_mapping() -> None:
    simulation = KinematicalSimulation(
        master_stereographic=_array_product("master-stereographic", 1.0),
        master_lambert=_array_product("master-lambert", 2.0),
        detector=_array_product("detector", 3.0),
        reflector_catalog=(),
        projection_ledger={},
    )
    figures = {"master.svg": b"original"}
    execution = KinematicalExecution(simulation=simulation, figures=figures)

    figures["master.svg"] = b"changed"

    assert execution.figures == {"master.svg": b"original"}
    with pytest.raises(TypeError):
        execution.figures["master.svg"] = b"changed"
    with pytest.raises(FrozenInstanceError):
        execution.simulation = simulation


def test_kinematical_simulation_products_returns_the_exact_named_products() -> None:
    stereographic = _array_product("master-stereographic", 1.0)
    lambert = _array_product("master-lambert", 2.0)
    detector = _array_product("detector", 3.0)
    simulation = KinematicalSimulation(
        master_stereographic=stereographic,
        master_lambert=lambert,
        detector=detector,
        reflector_catalog=(),
        projection_ledger={},
    )

    products = simulation.products()

    assert list(products) == ["master-stereographic", "master-lambert", "detector"]
    assert products["master-stereographic"] is stereographic
    assert products["master-lambert"] is lambert
    assert products["detector"] is detector
