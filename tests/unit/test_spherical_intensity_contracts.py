from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import numpy as np
import pytest
import yaml

from kikuchi_lab.spherical_intensity import (
    SphericalAxialField,
    SphericalIntensityBuild,
    SphericalIntensityField,
    load_spherical_intensity_recipe,
)


ROOT = Path(__file__).parents[2]
RECIPE = ROOT / "recipes" / "spherical" / "forsterite-s2-intensity.yml"


def _recipe_payload() -> dict[str, object]:
    payload = yaml.safe_load(RECIPE.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _mapping(payload: dict[str, object], name: str) -> dict[str, object]:
    value = payload[name]
    assert isinstance(value, dict)
    return value


def _write_recipe(tmp_path: Path, payload: dict[str, object], name: str = "recipe.yml") -> Path:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def minimal_directional_metadata() -> dict[str, object]:
    return {
        "kind": "spherical_scalar_field",
        "domain": "S2",
        "domain_semantics": "directional",
        "source": {
            "product_id": "kinematical-0123456789abcdef",
            "array_sha256": "0" * 64,
            "shape": [2, 3, 3],
            "dtype": "float32",
            "energy_kev": 20.0,
        },
        "projection": {
            "name": "stereographic",
            "hemisphere_order": ["upper", "lower"],
            "poles": {"upper": -1, "lower": 1},
            "transform_owner": "orix.projections.InverseStereographicProjection",
            "transform_version": "0.14.3",
        },
        "frame": {
            "name": "standard-Pnma reciprocal Cartesian",
            "handedness": "right-handed",
            "vector_units": "dimensionless",
        },
        "grid": {
            "size": 3,
            "row_axis": "Y ascending -1 to +1",
            "column_axis": "X ascending -1 to +1",
            "X_formula": "X(j) = -1 + 2*j/(N - 1)",
            "Y_formula": "Y(i) = -1 + 2*i/(N - 1)",
        },
        "phase": {
            "space_group": 62,
            "point_group": "mmm",
            "contains_inversion": True,
        },
        "equator": {"owner": "upper"},
        "normalization": {"name": "quiet-density-v1"},
    }


def minimal_axial_metadata() -> dict[str, object]:
    metadata = minimal_directional_metadata()
    metadata["domain_semantics"] = "axial-derived"
    metadata["axial"] = {
        "representative_rule": "z>0; equator x>0 or x==0,y>=0",
        "source_pair_rule": "upper[i,j] with lower[N-1-i,N-1-j]",
    }
    return metadata


def _directional_field(
    *, metadata: dict[str, object] | None = None
) -> SphericalIntensityField:
    return SphericalIntensityField.from_columns(
        xyz=np.eye(3, dtype=np.float64),
        hemisphere=[1, 1, 1],
        source_row=[0, 1, 2],
        source_column=[2, 1, 0],
        intensity_raw=[1.0, 2.0, 3.0],
        intensity_normalized=[0.0, 0.5, 1.0],
        density_weight=[0.0, 0.5**1.5, 1.0],
        metadata=metadata or minimal_directional_metadata(),
    )


def _axial_field(*, metadata: dict[str, object] | None = None) -> SphericalAxialField:
    return SphericalAxialField.from_columns(
        xyz=np.eye(3, dtype=np.float64),
        source_pairs=[
            [[1, 0, 0], [-1, 2, 2]],
            [[1, 0, 1], [-1, 2, 1]],
            [[1, 1, 0], [-1, 1, 2]],
        ],
        intensity_raw=[1.0, 2.0, 3.0],
        intensity_normalized=[0.0, 0.5, 1.0],
        density_weight=[0.0, 0.5**1.5, 1.0],
        metadata=metadata or minimal_axial_metadata(),
    )


def test_forsterite_s2_recipe_fixes_bounded_profiles_and_density() -> None:
    smoke = load_spherical_intensity_recipe(RECIPE, profile="smoke")
    acceptance = load_spherical_intensity_recipe(RECIPE, profile="acceptance")

    assert (smoke.profile.half_size, smoke.profile.point_count) == (32, 10_000)
    assert (smoke.profile.sampling_resolution_deg, smoke.profile.timeout_seconds) == (
        1.0,
        300,
    )
    assert (acceptance.profile.half_size, acceptance.profile.point_count) == (
        128,
        100_000,
    )
    assert acceptance.profile.sampling_resolution_deg == 0.25
    assert acceptance.profile.timeout_seconds == 900
    assert acceptance.density.to_dict() == {
        "name": "quiet-density-v1",
        "low_percentile": 5.0,
        "high_percentile": 99.85,
        "exponent": 1.5,
    }
    assert acceptance.rng_seed == 20260713
    assert acceptance.rng_generator == "twister"


def test_forsterite_s2_recipe_fixes_tolerances_and_serialization() -> None:
    recipe = load_spherical_intensity_recipe(RECIPE, profile="acceptance")

    assert recipe.source_kinematical_recipe == "../kinematical/forsterite-etched-master.yml"
    assert recipe.tolerances.to_dict() == {
        "disk_epsilon_multiplier": 32,
        "unit_norm_max": 5.0e-13,
        "stereo_round_trip_rad_max": 1.0e-10,
        "equator_normalized_max": 1.0e-6,
        "axial_normalized_rms_max": 1.0e-6,
        "axial_normalized_max": 1.0e-5,
        "mtex_node_normalized_max": 1.0e-8,
    }
    assert recipe.csv_float_format == "%.17g"
    assert recipe.display_resolution_deg == 1.0
    assert recipe.emit_axial is True
    assert recipe.expected_mtex_version == "mtex-6.1.1"


@pytest.mark.parametrize(
    ("section", "nested"),
    [
        (None, None),
        ("profiles", None),
        ("profiles", "smoke"),
        ("density", None),
        ("tolerances", None),
    ],
)
def test_recipe_loader_rejects_unknown_keys_at_every_level(
    tmp_path: Path, section: str | None, nested: str | None
) -> None:
    payload = _recipe_payload()
    target = payload
    if section is not None:
        target = _mapping(payload, section)
    if nested is not None:
        target = _mapping(target, nested)
    target["unknown"] = "unsupported"

    with pytest.raises(ValueError, match="fields differ from the schema"):
        load_spherical_intensity_recipe(_write_recipe(tmp_path, payload), profile="smoke")


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("schema_version",), True),
        (("profiles", "smoke", "half_size"), True),
        (("profiles", "smoke", "point_count"), True),
        (("profiles", "smoke", "timeout_seconds"), True),
        (("tolerances", "disk_epsilon_multiplier"), True),
        (("rng_seed",), True),
    ],
)
def test_recipe_loader_rejects_bool_where_integer_is_required(
    tmp_path: Path, path: tuple[str, ...], value: object
) -> None:
    payload = _recipe_payload()
    target: dict[str, object] = payload
    for name in path[:-1]:
        target = _mapping(target, name)
    target[path[-1]] = value

    with pytest.raises(ValueError, match="integer"):
        load_spherical_intensity_recipe(_write_recipe(tmp_path, payload), profile="smoke")


def test_recipe_loader_rejects_invalid_profile_and_profile_half_size(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="profile must be smoke or acceptance"):
        load_spherical_intensity_recipe(RECIPE, profile="production")  # type: ignore[arg-type]

    payload = _recipe_payload()
    _mapping(_mapping(payload, "profiles"), "smoke")["half_size"] = 64
    with pytest.raises(ValueError, match="smoke half_size must be 32"):
        load_spherical_intensity_recipe(_write_recipe(tmp_path, payload), profile="smoke")


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("profiles", "smoke", "sampling_resolution_deg"), float("nan")),
        (("density", "low_percentile"), float("inf")),
        (("density", "exponent"), 0.0),
        (("tolerances", "unit_norm_max"), float("nan")),
        (("display_resolution_deg",), 0.0),
    ],
)
def test_recipe_loader_rejects_nonfinite_or_nonpositive_numbers(
    tmp_path: Path, path: tuple[str, ...], value: object
) -> None:
    payload = _recipe_payload()
    target: dict[str, object] = payload
    for name in path[:-1]:
        target = _mapping(target, name)
    target[path[-1]] = value

    with pytest.raises(ValueError, match="finite|positive"):
        load_spherical_intensity_recipe(_write_recipe(tmp_path, payload), profile="smoke")


def test_recipe_identity_is_stable_and_independent_of_recipe_file_location(
    tmp_path: Path,
) -> None:
    payload = _recipe_payload()
    first = load_spherical_intensity_recipe(
        _write_recipe(tmp_path, payload, "first.yml"), profile="acceptance"
    )
    second_directory = tmp_path / "elsewhere"
    second_directory.mkdir()
    second = load_spherical_intensity_recipe(
        _write_recipe(second_directory, payload, "second.yml"), profile="acceptance"
    )

    assert first.to_dict() == second.to_dict()
    assert first.recipe_id == second.recipe_id
    assert first.recipe_id.startswith("recipe-")
    relocated_source = replace(
        first, source_kinematical_recipe="../../relocated/forsterite-etched-master.yml"
    )
    assert relocated_source.to_dict() != first.to_dict()
    assert relocated_source.recipe_id == first.recipe_id
    with pytest.raises(FrozenInstanceError):
        first.rng_seed = 1


def test_recipe_loader_requires_source_recipe_path_to_remain_relative(tmp_path: Path) -> None:
    payload = _recipe_payload()
    payload["source_kinematical_recipe"] = "/tmp/local/forsterite.yml"

    with pytest.raises(ValueError, match="relative path"):
        load_spherical_intensity_recipe(_write_recipe(tmp_path, payload), profile="smoke")

    recipe = load_spherical_intensity_recipe(RECIPE, profile="smoke")
    with pytest.raises(ValueError, match="relative path"):
        replace(recipe, source_kinematical_recipe="/tmp/local/forsterite.yml")


def test_directional_field_owns_typed_byte_backed_immutable_columns() -> None:
    xyz = np.eye(3, dtype=np.float64)
    raw = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    field = SphericalIntensityField.from_columns(
        xyz=xyz,
        hemisphere=[1, 1, 1],
        source_row=[0, 1, 2],
        source_column=[2, 1, 0],
        intensity_raw=raw,
        intensity_normalized=[0.0, 0.5, 1.0],
        density_weight=[0.0, 0.5**1.5, 1.0],
        metadata=minimal_directional_metadata(),
    )
    xyz[:] = -1
    raw[:] = -1

    assert field.xyz.dtype.str == "<f8"
    assert field.hemisphere.dtype.str == "|i1"
    assert field.source_row.dtype.str == "<i4"
    assert field.source_column.dtype.str == "<i4"
    assert field.intensity_raw.dtype.str == "<f4"
    assert field.intensity_normalized.dtype.str == "<f8"
    assert field.density_weight.dtype.str == "<f8"
    assert field.xyz[0].tolist() == [1.0, 0.0, 0.0]
    assert field.intensity_raw.tolist() == [1.0, 2.0, 3.0]
    for column in (
        field.xyz,
        field.hemisphere,
        field.source_row,
        field.source_column,
        field.intensity_raw,
        field.intensity_normalized,
        field.density_weight,
    ):
        assert not column.flags.writeable
        with pytest.raises(ValueError):
            column.setflags(write=True)


def test_directional_field_metadata_is_deeply_frozen_and_safely_thawed() -> None:
    metadata = minimal_directional_metadata()
    field = _directional_field(metadata=metadata)
    _mapping(metadata, "projection")["name"] = "changed"

    assert field.metadata["projection"]["name"] == "stereographic"
    with pytest.raises(TypeError):
        field.metadata["projection"]["name"] = "changed"
    thawed = field.metadata_dict()
    _mapping(thawed, "projection")["name"] = "changed-again"
    assert field.metadata["projection"]["name"] == "stereographic"
    assert field.metadata_dict()["projection"]["hemisphere_order"] == ["upper", "lower"]


@pytest.mark.parametrize(
    "changes",
    [
        {"xyz": [[1.0, 0.0]]},
        {"hemisphere": [1, 1]},
        {"source_row": [0, 1]},
        {"source_column": [0, 1]},
        {"intensity_raw": [1.0, 2.0]},
        {"intensity_normalized": [0.0, 1.0]},
        {"density_weight": [0.0, 1.0]},
        {"intensity_raw": [1.0, float("nan"), 3.0]},
    ],
)
def test_directional_field_rejects_wrong_shapes_lengths_and_nonfinite_columns(
    changes: dict[str, object],
) -> None:
    columns: dict[str, object] = {
        "xyz": np.eye(3),
        "hemisphere": [1, 1, 1],
        "source_row": [0, 1, 2],
        "source_column": [2, 1, 0],
        "intensity_raw": [1.0, 2.0, 3.0],
        "intensity_normalized": [0.0, 0.5, 1.0],
        "density_weight": [0.0, 0.5, 1.0],
    }
    columns.update(changes)

    with pytest.raises(ValueError, match="shape|equal length|finite"):
        SphericalIntensityField.from_columns(
            **columns, metadata=minimal_directional_metadata()
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("xyz", [[2.0, 0.0, 0.0]], "unit vectors"),
        ("hemisphere", [0], "hemisphere"),
        ("density_weight", [-0.1], "nonnegative"),
    ],
)
def test_directional_field_rejects_invalid_vector_hemisphere_or_density(
    field: str, value: object, message: str
) -> None:
    columns: dict[str, object] = {
        "xyz": [[1.0, 0.0, 0.0]],
        "hemisphere": [1],
        "source_row": [0],
        "source_column": [0],
        "intensity_raw": [1.0],
        "intensity_normalized": [1.0],
        "density_weight": [1.0],
    }
    columns[field] = value

    with pytest.raises(ValueError, match=message):
        SphericalIntensityField.from_columns(
            **columns, metadata=minimal_directional_metadata()
        )


@pytest.mark.parametrize("normalized", [[-1.0e-12], [1.0 + 1.0e-12]])
def test_directional_field_rejects_normalized_intensity_outside_closed_unit_interval(
    normalized: list[float],
) -> None:
    with pytest.raises(ValueError, match=r"intensity_normalized.*\[0, 1\]"):
        SphericalIntensityField.from_columns(
            xyz=[[1.0, 0.0, 0.0]],
            hemisphere=[1],
            source_row=[0],
            source_column=[0],
            intensity_raw=[1.0],
            intensity_normalized=normalized,
            density_weight=[1.0],
            metadata=minimal_directional_metadata(),
        )


@pytest.mark.parametrize(
    "key", ["source", "projection", "frame", "grid", "phase", "equator", "normalization"]
)
def test_directional_field_requires_all_semantic_metadata(key: str) -> None:
    metadata = minimal_directional_metadata()
    del metadata[key]

    with pytest.raises(ValueError, match=key):
        _directional_field(metadata=metadata)


@pytest.mark.parametrize(
    ("section", "key"),
    [
        ("source", "shape"),
        ("source", "dtype"),
        ("source", "energy_kev"),
        ("projection", "transform_owner"),
        ("projection", "transform_version"),
        ("frame", "vector_units"),
        ("grid", "X_formula"),
        ("grid", "Y_formula"),
    ],
)
def test_directional_field_requires_complete_source_and_transform_provenance(
    section: str, key: str
) -> None:
    metadata = minimal_directional_metadata()
    del _mapping(metadata, section)[key]

    with pytest.raises(ValueError, match=rf"metadata {section}\.{key}"):
        _directional_field(metadata=metadata)


@pytest.mark.parametrize(
    "absolute_path",
    [
        "/tmp/local/source.npy",
        "file:///tmp/local/source.npy",
        r"C:\local\source.npy",
    ],
)
def test_directional_field_rejects_nested_absolute_local_paths(
    absolute_path: str,
) -> None:
    metadata = minimal_directional_metadata()
    _mapping(metadata, "source")["runtime_reference"] = {
        "nested": {"candidate": absolute_path}
    }

    with pytest.raises(
        ValueError, match=r"metadata\.source\.runtime_reference\.nested\.candidate.*absolute"
    ):
        _directional_field(metadata=metadata)


def test_directional_field_accepts_nested_non_path_provenance_text() -> None:
    metadata = minimal_directional_metadata()
    _mapping(metadata, "source")["runtime_reference"] = {
        "nested": {"candidate": "runtime-independent scientific provenance"}
    }

    field = _directional_field(metadata=metadata)

    assert (
        field.metadata["source"]["runtime_reference"]["nested"]["candidate"]
        == "runtime-independent scientific provenance"
    )


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("kind", "image"),
        ("domain", "SO3"),
        ("domain_semantics", "axial-derived"),
    ],
)
def test_directional_field_requires_exact_domain_semantics(key: str, value: str) -> None:
    metadata = minimal_directional_metadata()
    metadata[key] = value

    with pytest.raises(ValueError, match=key):
        _directional_field(metadata=metadata)


def test_directional_field_hashes_every_channel_and_has_stable_identity() -> None:
    first = _directional_field()
    second = _directional_field(metadata=minimal_directional_metadata())

    assert set(first.channel_sha256) == {
        "xyz",
        "hemisphere",
        "source_row",
        "source_column",
        "intensity_raw",
        "intensity_normalized",
        "density_weight",
    }
    assert all(len(value) == 64 for value in first.channel_sha256.values())
    assert first.field_id == second.field_id
    assert first.field_id.startswith("s2-field-")


def test_axial_field_owns_typed_columns_and_records_source_pair_semantics() -> None:
    pairs = np.array(
        [
            [[1, 0, 0], [-1, 2, 2]],
            [[1, 0, 1], [-1, 2, 1]],
            [[1, 1, 0], [-1, 1, 2]],
        ],
        dtype=np.int64,
    )
    field = SphericalAxialField.from_columns(
        xyz=np.eye(3),
        source_pairs=pairs,
        intensity_raw=[1.0, 2.0, 3.0],
        intensity_normalized=[0.0, 0.5, 1.0],
        density_weight=[0.0, 0.5, 1.0],
        metadata=minimal_axial_metadata(),
    )
    pairs[:] = 0

    assert field.xyz.dtype.str == "<f8"
    assert field.source_pairs.dtype.str == "<i4"
    assert field.source_pairs.shape == (3, 2, 3)
    assert field.source_pairs[0].tolist() == [[1, 0, 0], [-1, 2, 2]]
    assert field.metadata["domain_semantics"] == "axial-derived"
    assert set(field.channel_sha256) == {
        "xyz",
        "source_pairs",
        "intensity_raw",
        "intensity_normalized",
        "density_weight",
    }
    for column in (
        field.xyz,
        field.source_pairs,
        field.intensity_raw,
        field.intensity_normalized,
        field.density_weight,
    ):
        with pytest.raises(ValueError):
            column.setflags(write=True)


@pytest.mark.parametrize(
    "source_pairs",
    [
        [[1, 0, 0]],
        [[[1, 0, 0], [0, 2, 2]]],
        [[[1, 0, 0], [-1, -1, 2]]],
    ],
)
def test_axial_field_rejects_invalid_source_pair_shape_or_values(
    source_pairs: object,
) -> None:
    with pytest.raises(ValueError, match="shape|hemisphere|indices"):
        SphericalAxialField.from_columns(
            xyz=[[1.0, 0.0, 0.0]],
            source_pairs=source_pairs,
            intensity_raw=[1.0],
            intensity_normalized=[1.0],
            density_weight=[1.0],
            metadata=minimal_axial_metadata(),
        )


def test_axial_field_requires_axial_derived_metadata_and_pair_rules() -> None:
    metadata = minimal_axial_metadata()
    del metadata["axial"]
    with pytest.raises(ValueError, match="axial"):
        _axial_field(metadata=metadata)

    directional = minimal_directional_metadata()
    with pytest.raises(ValueError, match="domain_semantics"):
        _axial_field(metadata=directional)


@pytest.mark.parametrize("normalized", [[-1.0e-12], [1.0 + 1.0e-12]])
def test_axial_field_rejects_normalized_intensity_outside_closed_unit_interval(
    normalized: list[float],
) -> None:
    with pytest.raises(ValueError, match=r"intensity_normalized.*\[0, 1\]"):
        SphericalAxialField.from_columns(
            xyz=[[1.0, 0.0, 0.0]],
            source_pairs=[[[1, 0, 0], [-1, 2, 2]]],
            intensity_raw=[1.0],
            intensity_normalized=normalized,
            density_weight=[1.0],
            metadata=minimal_axial_metadata(),
        )


def test_spherical_intensity_build_deeply_freezes_diagnostics() -> None:
    diagnostics = {"counts": {"directional": 3}, "checks": ["unit", "finite"]}
    build = SphericalIntensityBuild(
        field=_directional_field(), axial_field=_axial_field(), diagnostics=diagnostics
    )
    _mapping(diagnostics, "counts")["directional"] = 0

    assert build.diagnostics["counts"]["directional"] == 3
    with pytest.raises(TypeError):
        build.diagnostics["counts"]["directional"] = 0
    thawed = build.diagnostics_dict()
    _mapping(thawed, "counts")["directional"] = 0
    assert build.diagnostics["counts"]["directional"] == 3
    with pytest.raises(FrozenInstanceError):
        build.axial_field = None


def test_spherical_intensity_build_requires_diagnostics_mapping() -> None:
    with pytest.raises(TypeError, match="diagnostics must be a mapping"):
        SphericalIntensityBuild(
            field=_directional_field(),
            axial_field=None,
            diagnostics=["not", "a", "mapping"],  # type: ignore[arg-type]
        )
