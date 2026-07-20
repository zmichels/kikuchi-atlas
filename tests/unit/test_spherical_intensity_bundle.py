from __future__ import annotations

import hashlib
from importlib import import_module
import json
from dataclasses import dataclass, FrozenInstanceError, replace
from pathlib import Path
import sys
from typing import Mapping
import zipfile

import numpy as np
import pytest

from kikuchi_lab.model.identity import canonical_json, stable_id
from kikuchi_lab.spherical_intensity import (
    SphericalBundleExistsError,
    SphericalBundlePartialError,
    SphericalBundleStage,
    SphericalAxialField,
    SphericalIntensityBuild,
    SphericalIntensityField,
    build_spherical_intensity,
    finalize_spherical_bundle,
    stage_spherical_bundle,
)
sys.path.insert(0, str(Path(__file__).parents[1]))
_fixtures = import_module("spherical_fixtures")
fixture_source = _fixtures.fixture_source
noncentrosymmetric_source = _fixtures.noncentrosymmetric_source
small_spherical_build = _fixtures.small_spherical_build
spherical_recipe = _fixtures.spherical_recipe
symmetric_master = _fixtures.symmetric_master
synthetic_simulation = _fixtures.synthetic_simulation


BASE_FILES = {
    "forsterite-s2-intensity.csv",
    "forsterite-s2-intensity.npz",
    "forsterite-s2-intensity.json",
    "forsterite-s2-mtex.m",
    "forsterite-s2-axial.csv",
    "diagnostics/mtex-status.json",
}
DIRECTIONAL_HEADER = (
    "x,y,z,hemisphere,source_row,source_column,intensity_raw,"
    "intensity_normalized,density_weight"
)
AXIAL_HEADER = (
    "x,y,z,member_a_hemisphere,member_a_row,member_a_column,"
    "member_b_hemisphere,member_b_row,member_b_column,intensity_raw,"
    "intensity_normalized,density_weight"
)
NPZ_MEMBERS = [
    "density_weight.npy",
    "hemisphere.npy",
    "intensity_normalized.npy",
    "intensity_raw.npy",
    "source_column.npy",
    "source_row.npy",
    "xyz.npy",
]
MTEX_COMMON_OUTPUTS = {
    "forsterite-s2-density-vectors.csv",
    "forsterite-s2-mtex-preview.png",
    "diagnostics/mtex-result.json",
    "figures/exact-node-scatter.png",
    "figures/colored-sphere.png",
    "figures/density-cloud.png",
    "figures/raw-vs-density-channels.png",
}


@dataclass(frozen=True)
class FutureMtexRunResult:
    status: str
    command: tuple[str, ...]
    normalized_error: str | None
    metrics: Mapping[str, object]
    produced_files: tuple[str, ...]
    last_stage: str | None
    elapsed_seconds: float


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage(
    root: Path,
    *,
    build: SphericalIntensityBuild | None = None,
    recipe=None,
    source=None,
) -> SphericalBundleStage:
    return stage_spherical_bundle(
        root,
        build or small_spherical_build(),
        recipe or spherical_recipe(),
        source or fixture_source(),
    )


def _stage_with_registered_script(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    build: SphericalIntensityBuild | None = None,
    recipe=None,
    source=None,
) -> SphericalBundleStage:
    from kikuchi_lab.spherical_intensity import bundle as bundle_module

    monkeypatch.setattr(
        bundle_module,
        "_scientific_extensions",
        lambda _build, _recipe: {"forsterite-s2-mtex.m": b"% deterministic fixture\n"},
        raising=False,
    )
    return _stage(root, build=build, recipe=recipe, source=source)


def _nonpassed_mtex_result(
    status: str,
    *,
    command: tuple[str, ...] = ("/private/tools/matlab", "-batch", "run"),
    elapsed_seconds: float = 1.25,
    normalized_error: str = "normalized diagnostic /private/run",
) -> FutureMtexRunResult:
    return FutureMtexRunResult(
        status=status,
        command=command,
        normalized_error=normalized_error,
        metrics={"diagnostic_observation": "retained only"},
        produced_files=(),
        last_stage="triangulation",
        elapsed_seconds=elapsed_seconds,
    )


def _passed_mtex_result(
    stage: SphericalBundleStage,
    *,
    matlab_version: str = "24.2.0",
    mtex_version: str = "mtex-6.1.1",
    payload_tag: str = "canonical",
    command: tuple[str, ...] = ("/private/tools/matlab", "-batch", "run"),
    elapsed_seconds: float = 1.25,
) -> FutureMtexRunResult:
    ledger = json.loads(
        (stage.staging_path / "forsterite-s2-intensity.json").read_text(encoding="utf-8")
    )
    recipe = ledger["recipe"]["content"]
    axial_available = ledger["axial_available"]
    produced = set(MTEX_COMMON_OUTPUTS)
    if axial_available:
        produced.add("figures/directional-vs-axial.png")
    for relative in sorted(produced):
        path = stage.staging_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative == "forsterite-s2-density-vectors.csv":
            payload = b"x,y,z\n1,0,0\n"
        elif relative == "diagnostics/mtex-result.json":
            payload = canonical_json({"status": "passed", "tag": payload_tag}).encode()
        else:
            payload = f"fixture:{payload_tag}:{relative}\n".encode()
        path.write_bytes(payload)
    validated_files = {
        relative: {
            "bytes": (stage.staging_path / relative).stat().st_size,
            "sha256": _sha256(stage.staging_path / relative),
        }
        for relative in sorted(produced)
    }
    metrics = {
        "schema_version": 1,
        "profile": recipe["profile"]["name"],
        "node_count": ledger["metadata"]["diagnostics"]["point_count"],
        "node_normalized_error": 5.0e-9,
        "density_node_normalized_error": 6.0e-9,
        "point_count": recipe["profile"]["point_count"],
        "rng_seed": recipe["rng_seed"],
        "rng_generator": recipe["rng_generator"],
        "sampling_resolution_deg": recipe["profile"]["sampling_resolution_deg"],
        "display_resolution_deg": recipe["display_resolution_deg"],
        "axial_available": axial_available,
        "matlab_version": matlab_version,
        "mtex_version": mtex_version,
        "validated_files": validated_files,
    }
    return FutureMtexRunResult(
        status="passed",
        command=command,
        normalized_error=None,
        metrics=metrics,
        produced_files=tuple(sorted(produced)),
        last_stage="figure-export",
        elapsed_seconds=elapsed_seconds,
    )


def _python_only_bundle(
    root: Path, *, build: SphericalIntensityBuild | None = None
):
    return finalize_spherical_bundle(_stage(root, build=build), mtex_result=None)


def _without_axial_build() -> SphericalIntensityBuild:
    source = noncentrosymmetric_source()
    return build_spherical_intensity(
        synthetic_simulation(symmetric_master(), source=source),
        source,
        spherical_recipe(),
    )


def _build_with_axial_columns(
    build: SphericalIntensityBuild,
    *,
    source_pairs: np.ndarray | None = None,
    intensity_raw: np.ndarray | None = None,
    intensity_normalized: np.ndarray | None = None,
    density_weight: np.ndarray | None = None,
    metadata: Mapping[str, object] | None = None,
) -> SphericalIntensityBuild:
    assert build.axial_field is not None
    axial = build.axial_field
    replacement = SphericalAxialField.from_columns(
        xyz=axial.xyz,
        source_pairs=axial.source_pairs if source_pairs is None else source_pairs,
        intensity_raw=axial.intensity_raw if intensity_raw is None else intensity_raw,
        intensity_normalized=(
            axial.intensity_normalized
            if intensity_normalized is None
            else intensity_normalized
        ),
        density_weight=axial.density_weight if density_weight is None else density_weight,
        metadata=axial.metadata_dict() if metadata is None else metadata,
    )
    return SphericalIntensityBuild(
        field=build.field,
        axial_field=replacement,
        diagnostics=build.diagnostics,
    )


def _rebuild_with_diagnostics(
    build: SphericalIntensityBuild,
    diagnostics: Mapping[str, object],
    *,
    include_axial: bool,
) -> SphericalIntensityBuild:
    field_metadata = build.field.metadata_dict()
    field_metadata["diagnostics"] = diagnostics
    field = SphericalIntensityField.from_columns(
        xyz=build.field.xyz,
        hemisphere=build.field.hemisphere,
        source_row=build.field.source_row,
        source_column=build.field.source_column,
        intensity_raw=build.field.intensity_raw,
        intensity_normalized=build.field.intensity_normalized,
        density_weight=build.field.density_weight,
        metadata=field_metadata,
    )
    axial = None
    if include_axial:
        assert build.axial_field is not None
        axial_metadata = build.axial_field.metadata_dict()
        axial_metadata["diagnostics"] = diagnostics
        axial = SphericalAxialField.from_columns(
            xyz=build.axial_field.xyz,
            source_pairs=build.axial_field.source_pairs,
            intensity_raw=build.axial_field.intensity_raw,
            intensity_normalized=build.axial_field.intensity_normalized,
            density_weight=build.axial_field.density_weight,
            metadata=axial_metadata,
        )
    return SphericalIntensityBuild(
        field=field,
        axial_field=axial,
        diagnostics=diagnostics,
    )


def test_python_bundle_has_exact_inventory_and_hashes(tmp_path: Path) -> None:
    result = _python_only_bundle(tmp_path)
    manifest_path = result.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert set(manifest["files"]) == BASE_FILES
    actual = {
        str(path.relative_to(result.path))
        for path in result.path.rglob("*")
        if path.is_file()
    }
    assert actual == BASE_FILES | {"manifest.json"}
    assert manifest_path.read_text(encoding="utf-8") == canonical_json(manifest)
    assert "manifest.json" not in manifest["files"]
    for relative, record in manifest["files"].items():
        payload = (result.path / relative).read_bytes()
        assert record == {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    assert result.manifest_sha256 == _sha256(manifest_path)


def test_csv_headers_rows_numeric_format_and_lf_are_exact(tmp_path: Path) -> None:
    stage = _stage(tmp_path)
    directional = (stage.staging_path / "forsterite-s2-intensity.csv").read_bytes()
    axial = (stage.staging_path / "forsterite-s2-axial.csv").read_bytes()

    assert b"\r" not in directional + axial
    directional_lines = directional.decode("ascii").splitlines()
    axial_lines = axial.decode("ascii").splitlines()
    assert directional.endswith(b"\n")
    assert axial.endswith(b"\n")
    assert directional_lines[0] == DIRECTIONAL_HEADER
    assert directional_lines[1] == "0,-1,0,1,0,2,3,1,1"
    assert directional_lines[2] == (
        "-0.66666666666666663,-0.66666666666666663,0.33333333333333331,"
        "1,1,1,1.75,0.37106918238993714,0.22603845541715939"
    )
    assert axial_lines[0] == AXIAL_HEADER
    assert axial_lines[1] == (
        "-0.66666666666666663,-0.66666666666666663,0.33333333333333331,"
        "1,1,1,-1,3,3,1.75,0.37106918238993714,0.22603845541715939"
    )
    assert len(directional_lines) == len(small_spherical_build().field.xyz) + 1
    assert len(axial_lines) == len(small_spherical_build().axial_field.xyz) + 1


def test_npz_has_exact_sorted_members_dtypes_values_and_fixed_zip_metadata(
    tmp_path: Path,
) -> None:
    build = small_spherical_build()
    stage = _stage(tmp_path, build=build)
    path = stage.staging_path / "forsterite-s2-intensity.npz"

    with zipfile.ZipFile(path) as archive:
        assert archive.namelist() == NPZ_MEMBERS
        for info in archive.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.compress_type == zipfile.ZIP_DEFLATED
            assert info.external_attr == 0o600 << 16
    with np.load(path, allow_pickle=False) as arrays:
        assert sorted(arrays.files) == [name.removesuffix(".npy") for name in NPZ_MEMBERS]
        expected = {
            "density_weight": ("<f8", build.field.density_weight),
            "hemisphere": ("|i1", build.field.hemisphere),
            "intensity_normalized": ("<f8", build.field.intensity_normalized),
            "intensity_raw": ("<f4", build.field.intensity_raw),
            "source_column": ("<i4", build.field.source_column),
            "source_row": ("<i4", build.field.source_row),
            "xyz": ("<f8", build.field.xyz),
        }
        for name, (dtype, values) in expected.items():
            assert arrays[name].dtype.str == dtype
            np.testing.assert_array_equal(arrays[name], values)


def test_repeated_staging_writes_identical_scientific_artifact_bytes(
    tmp_path: Path,
) -> None:
    first = _stage(tmp_path / "first").staging_path
    second = _stage(tmp_path / "second").staging_path
    for relative in (
        "forsterite-s2-intensity.csv",
        "forsterite-s2-intensity.npz",
        "forsterite-s2-intensity.json",
        "forsterite-s2-mtex.m",
        "forsterite-s2-axial.csv",
    ):
        assert (first / relative).read_bytes() == (second / relative).read_bytes()


def test_stage_generates_script_exactly_once_before_ledger_and_registers_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kikuchi_lab.spherical_intensity import bundle as bundle_module

    build = small_spherical_build()
    recipe = spherical_recipe()
    calls: list[tuple[object, int, bool]] = []
    payload = b"% generated exactly once\n"

    def generate(recipe_arg, expected_node_count, axial_available):
        calls.append((recipe_arg, expected_node_count, axial_available))
        return payload.decode("utf-8")

    original_write_json = bundle_module._write_json

    def write_json(path: Path, value: object) -> None:
        if path.name == "forsterite-s2-intensity.json":
            assert (path.parent / "forsterite-s2-mtex.m").read_bytes() == payload
        original_write_json(path, value)

    monkeypatch.setattr(bundle_module, "generate_mtex_script", generate, raising=False)
    monkeypatch.setattr(bundle_module, "_write_json", write_json)
    stage = _stage(tmp_path, build=build, recipe=recipe)

    assert calls == [(recipe, len(build.field.xyz), True)]
    script = stage.staging_path / "forsterite-s2-mtex.m"
    assert script.read_bytes() == payload
    ledger = json.loads(
        (stage.staging_path / "forsterite-s2-intensity.json").read_text()
    )
    assert ledger["extension_artifacts"] == {
        "forsterite-s2-mtex.m": {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    }


def test_ledger_is_path_free_canonical_and_links_exact_scientific_identities(
    tmp_path: Path,
) -> None:
    build = small_spherical_build()
    recipe = spherical_recipe()
    source = fixture_source()
    stage = _stage(tmp_path, build=build)
    path = stage.staging_path / "forsterite-s2-intensity.json"
    ledger = json.loads(path.read_text(encoding="utf-8"))

    assert path.read_text(encoding="utf-8") == canonical_json(ledger)
    assert ledger["schema_version"] == 1
    assert ledger["field_id"] == build.field.field_id
    assert ledger["metadata"] == build.field.metadata_dict()
    assert ledger["channel_sha256"] == dict(build.field.channel_sha256)
    assert ledger["recipe"] == {"recipe_id": recipe.recipe_id, "content": recipe.to_dict()}
    assert ledger["verified_source_links"] == {
        "phase_source_id": source.source_record.source_id,
        "source_sha256": source.sha256,
        "source_uri": source.uri,
        "source_page_uri": source.page_uri,
    }
    assert ledger["axial_available"] is True
    assert ledger["axial_field_id"] == build.axial_field.field_id
    assert ledger["axial_channel_sha256"] == dict(build.axial_field.channel_sha256)
    script_payload = (stage.staging_path / "forsterite-s2-mtex.m").read_bytes()
    assert ledger["extension_artifacts"] == {
        "forsterite-s2-mtex.m": {
            "bytes": len(script_payload),
            "sha256": hashlib.sha256(script_payload).hexdigest(),
        }
    }
    assert set(ledger["artifacts"]) == {
        "forsterite-s2-intensity.csv",
        "forsterite-s2-intensity.npz",
        "forsterite-s2-axial.csv",
    }
    assert "manifest" not in canonical_json(ledger)
    assert str(tmp_path) not in canonical_json(ledger)
    assert str(source.record_path) not in canonical_json(ledger)
    for relative, record in ledger["artifacts"].items():
        payload = (stage.staging_path / relative).read_bytes()
        assert record == {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def test_noncentrosymmetric_bundle_omits_only_axial_csv_and_marks_absence(
    tmp_path: Path,
) -> None:
    source = noncentrosymmetric_source()
    build = _without_axial_build()
    stage = stage_spherical_bundle(tmp_path, build, spherical_recipe(), source)
    result = finalize_spherical_bundle(stage, mtex_result=None)

    assert not (result.path / "forsterite-s2-axial.csv").exists()
    actual = {
        str(path.relative_to(result.path))
        for path in result.path.rglob("*")
        if path.is_file()
    }
    assert actual == (BASE_FILES - {"forsterite-s2-axial.csv"}) | {"manifest.json"}
    ledger = json.loads((result.path / "forsterite-s2-intensity.json").read_text())
    assert ledger["axial_available"] is False
    assert ledger["axial_field_id"] is None
    assert ledger["axial_channel_sha256"] is None


def test_axial_absence_rejects_a_reserved_axial_file_added_after_staging(
    tmp_path: Path,
) -> None:
    source = noncentrosymmetric_source()
    stage = stage_spherical_bundle(
        tmp_path, _without_axial_build(), spherical_recipe(), source
    )
    (stage.staging_path / "forsterite-s2-axial.csv").write_text(
        "not-a-validated-axial-field\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="axial"):
        finalize_spherical_bundle(stage, mtex_result=None)


def test_valid_but_spliced_axial_metadata_is_rejected_before_staging(
    tmp_path: Path,
) -> None:
    build = small_spherical_build()
    assert build.axial_field is not None
    metadata = build.axial_field.metadata_dict()
    metadata["source"]["product_id"] = "kinematical-spliced000000"
    spliced = _build_with_axial_columns(build, metadata=metadata)
    output = tmp_path / "must-not-exist"

    with pytest.raises(ValueError, match="axial.*directional|coherence|metadata"):
        _stage(output, build=spliced)
    assert not output.exists()


@pytest.mark.parametrize("corruption", ["pair", "raw", "normalized", "density"])
def test_valid_axial_contract_with_corrupt_pair_or_channel_is_rejected(
    tmp_path: Path, corruption: str
) -> None:
    build = small_spherical_build()
    assert build.axial_field is not None
    axial = build.axial_field
    kwargs: dict[str, np.ndarray] = {}
    if corruption == "pair":
        pairs = axial.source_pairs.copy()
        pairs[0, 1, 1] = 2
        kwargs["source_pairs"] = pairs
    elif corruption == "raw":
        raw = axial.intensity_raw.copy()
        raw[0] += np.float32(0.125)
        kwargs["intensity_raw"] = raw
    elif corruption == "normalized":
        normalized = axial.intensity_normalized.copy()
        normalized[0] *= 0.5
        kwargs["intensity_normalized"] = normalized
    else:
        density = axial.density_weight.copy()
        density[0] *= 0.5
        kwargs["density_weight"] = density
    corrupted = _build_with_axial_columns(build, **kwargs)
    output = tmp_path / "must-not-exist"

    with pytest.raises(ValueError, match="axial|pair|normalization|density|mean"):
        _stage(output, build=corrupted)
    assert not output.exists()


@pytest.mark.parametrize(
    ("branch", "expected_status", "expected_axial"),
    [
        ("eligible", "emitted", True),
        ("disabled", "disabled-by-recipe", False),
        ("no-inversion", "phase-has-no-inversion", False),
        ("over-rms", "antipodal-residual-exceeds-tolerance", False),
        ("over-max", "antipodal-residual-exceeds-tolerance", False),
    ],
)
def test_bundle_recomputes_every_canonical_axial_eligibility_branch(
    tmp_path: Path, branch: str, expected_status: str, expected_axial: bool
) -> None:
    recipe = spherical_recipe()
    source = fixture_source()
    master = symmetric_master()
    if branch == "disabled":
        recipe = replace(recipe, emit_axial=False)
    elif branch == "no-inversion":
        source = noncentrosymmetric_source()
    elif branch in {"over-rms", "over-max"}:
        master = master.copy()
        master[1, 3, 3] += np.float32(0.01)
        if branch == "over-rms":
            recipe = replace(
                recipe,
                tolerances=replace(
                    recipe.tolerances,
                    axial_normalized_rms_max=1.0e-6,
                    axial_normalized_max=1.0,
                ),
            )
        else:
            recipe = replace(
                recipe,
                tolerances=replace(
                    recipe.tolerances,
                    axial_normalized_rms_max=1.0,
                    axial_normalized_max=1.0e-5,
                ),
            )
    build = build_spherical_intensity(
        synthetic_simulation(master, source=source), source, recipe
    )
    axial = build.diagnostics_dict()["axial"]
    antipodal = build.diagnostics_dict()["antipodal"]
    assert axial["status"] == expected_status
    assert (build.axial_field is not None) is expected_axial
    assert axial["contains_inversion"] == build.field.metadata["phase"][
        "contains_inversion"
    ]
    assert axial["observed_normalized_rms"] == antipodal["normalized_rms"]
    assert axial["observed_normalized_max"] == antipodal["normalized_max"]
    assert axial["normalized_rms_limit"] == recipe.tolerances.axial_normalized_rms_max
    assert axial["normalized_max_limit"] == recipe.tolerances.axial_normalized_max
    assert axial["representative_count"] == (
        len(build.axial_field.xyz) if build.axial_field is not None else 0
    )

    stage = stage_spherical_bundle(tmp_path / branch, build, recipe, source)
    assert stage.staging_path.is_dir()


@pytest.mark.parametrize(
    ("forged_status", "include_axial"),
    [
        ("disabled-by-recipe", True),
        ("emitted", False),
        ("antipodal-residual-exceeds-tolerance", True),
    ],
)
def test_bundle_rejects_contradictory_axial_status_or_field_presence(
    tmp_path: Path, forged_status: str, include_axial: bool
) -> None:
    build = small_spherical_build()
    diagnostics = build.diagnostics_dict()
    diagnostics["axial"]["status"] = forged_status
    diagnostics["axial"]["representative_count"] = (
        len(build.axial_field.xyz) if include_axial else 0
    )
    forged = _rebuild_with_diagnostics(
        build,
        diagnostics,
        include_axial=include_axial,
    )
    output = tmp_path / "must-not-exist"

    with pytest.raises(ValueError, match="axial.*status|eligibility|presence"):
        _stage(output, build=forged)
    assert not output.exists()


@pytest.mark.parametrize(
    ("diagnostic_key", "forged_value"),
    [
        ("contains_inversion", False),
        ("observed_normalized_rms", 0.5),
        ("observed_normalized_max", 0.5),
        ("normalized_rms_limit", 0.5),
        ("normalized_max_limit", 0.5),
    ],
)
def test_bundle_rejects_forged_axial_eligibility_diagnostics(
    tmp_path: Path, diagnostic_key: str, forged_value: object
) -> None:
    build = small_spherical_build()
    diagnostics = build.diagnostics_dict()
    diagnostics["axial"][diagnostic_key] = forged_value
    forged = _rebuild_with_diagnostics(build, diagnostics, include_axial=True)

    with pytest.raises(ValueError, match="axial.*diagnostic|eligibility|limit|observed"):
        _stage(tmp_path, build=forged)


def test_equator_axial_raw_is_bound_to_retained_upper_by_half_antipodal_residual(
    tmp_path: Path,
) -> None:
    build = small_spherical_build()
    assert build.axial_field is not None
    directional_keys = {
        (int(h), int(r), int(c))
        for h, r, c in zip(
            build.field.hemisphere,
            build.field.source_row,
            build.field.source_column,
            strict=True,
        )
    }
    equator_index = next(
        index
        for index, pair in enumerate(build.axial_field.source_pairs)
        if tuple(int(value) for value in pair[1]) not in directional_keys
    )
    raw = build.axial_field.intensity_raw.copy()
    assert raw[equator_index] != 0
    raw[equator_index] += np.float32(0.01)
    normalization = build.field.metadata["normalization"]
    normalized = np.clip(
        (raw.astype(np.float64) - normalization["realized_low"])
        / (normalization["realized_high"] - normalization["realized_low"]),
        0.0,
        1.0,
    )
    density = normalized**spherical_recipe().density.exponent
    corrupted = _build_with_axial_columns(
        build,
        intensity_raw=raw,
        intensity_normalized=normalized,
        density_weight=density,
    )

    with pytest.raises(ValueError, match="equator|antipodal|residual"):
        _stage(tmp_path, build=corrupted)


@pytest.mark.parametrize(
    "local_page_uri",
    ["/private/source.yml", "file:///private/source.yml", r"C:\\data\\source.yml"],
)
def test_nested_local_provenance_is_rejected_before_output_root_creation(
    tmp_path: Path, local_page_uri: str
) -> None:
    source = replace(fixture_source(), page_uri=local_page_uri)
    output = tmp_path / "must-not-exist"

    with pytest.raises(ValueError, match="local path"):
        stage_spherical_bundle(output, small_spherical_build(), spherical_recipe(), source)
    assert not output.exists()


def test_stage_validates_recipe_source_and_build_integrity_before_writing(
    tmp_path: Path,
) -> None:
    build = small_spherical_build()
    mismatched_recipe = replace(
        spherical_recipe(),
        density=replace(spherical_recipe().density, exponent=2.0),
    )
    with pytest.raises(ValueError, match="recipe"):
        stage_spherical_bundle(tmp_path / "recipe", build, mismatched_recipe, fixture_source())
    with pytest.raises(ValueError, match="source"):
        stage_spherical_bundle(
            tmp_path / "source", build, spherical_recipe(), noncentrosymmetric_source()
        )

    object.__setattr__(build.field, "field_id", "s2-field-corrupt")
    with pytest.raises(ValueError, match="corrupt|identity"):
        stage_spherical_bundle(tmp_path / "corrupt", build, spherical_recipe(), fixture_source())
    assert not (tmp_path / "recipe").exists()
    assert not (tmp_path / "source").exists()
    assert not (tmp_path / "corrupt").exists()


def test_finalization_rejects_scientific_artifact_corruption(tmp_path: Path) -> None:
    stage = _stage(tmp_path)
    with (stage.staging_path / "forsterite-s2-intensity.csv").open("ab") as handle:
        handle.write(b"corrupt\n")

    with pytest.raises(ValueError, match="corrupt"):
        finalize_spherical_bundle(stage, mtex_result=None)
    assert stage.staging_path.is_dir()
    assert not [path for path in tmp_path.iterdir() if path.name.startswith("s2-run-")]


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("unexpected.txt", "unregistered"),
        ("forsterite-s2-mtex.m", "extension|corrupt"),
    ],
)
def test_finalization_rejects_every_unregistered_non_diagnostic_file(
    tmp_path: Path, relative: str, expected: str
) -> None:
    stage = _stage(tmp_path)
    (stage.staging_path / relative).write_text("unregistered\n", encoding="utf-8")

    with pytest.raises(ValueError, match=expected):
        finalize_spherical_bundle(stage, mtex_result=None)
    assert stage.staging_path.is_dir()


def test_registered_script_hash_detects_post_stage_alteration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage = _stage_with_registered_script(tmp_path, monkeypatch)
    script = stage.staging_path / "forsterite-s2-mtex.m"
    assert script.is_file()
    script.write_text("% altered after registration\n", encoding="utf-8")

    with pytest.raises(ValueError, match="extension|script|corrupt"):
        finalize_spherical_bundle(stage, mtex_result=None)
    assert stage.staging_path.is_dir()


def test_passed_mtex_rejects_unregistered_extra_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage = _stage_with_registered_script(tmp_path, monkeypatch)
    result = _passed_mtex_result(stage)
    (stage.staging_path / "surprise-render.png").write_bytes(b"not registered")

    with pytest.raises(ValueError, match="unregistered"):
        finalize_spherical_bundle(stage, mtex_result=result)
    assert stage.staging_path.is_dir()


def test_failed_writer_leaves_diagnostic_partial_but_never_promotes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kikuchi_lab.spherical_intensity import bundle as bundle_module

    def raising_writer(*args, **kwargs) -> None:
        raise OSError("synthetic write failure")

    monkeypatch.setattr(bundle_module, "_write_csv", raising_writer)
    with pytest.raises(OSError, match="synthetic write failure"):
        _stage(tmp_path)
    children = list(tmp_path.iterdir())
    assert len(children) == 1
    assert children[0].name.startswith(".s2-partial-")
    assert children[0].is_dir()
    assert not [path for path in children if not path.name.startswith(".s2-partial-")]


@pytest.mark.parametrize(
    "status", ["passed", "not-requested", "unavailable", "failed", "timed-out"]
)
def test_active_partial_is_rejected_for_every_mtex_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
) -> None:
    if status == "passed":
        stage = _stage_with_registered_script(tmp_path, monkeypatch)
        mtex_result = _passed_mtex_result(stage)
    else:
        stage = _stage(tmp_path)
        mtex_result = (
            None if status == "not-requested" else _nonpassed_mtex_result(status)
        )
    (stage.staging_path / "future-output.partial").write_text("incomplete", encoding="utf-8")

    with pytest.raises(SphericalBundlePartialError, match=r"\.partial"):
        finalize_spherical_bundle(stage, mtex_result=mtex_result)
    assert stage.staging_path.is_dir()
    status_record = json.loads(
        (stage.staging_path / "diagnostics/mtex-status.json").read_text(encoding="utf-8")
    )
    assert status_record["status"] == "finalization-failed"
    assert status_record["failure_kind"] == "partial-artifact"
    assert not [path for path in tmp_path.iterdir() if path.name.startswith("s2-run-")]


@pytest.mark.parametrize(
    ("status", "may_publish"),
    [
        ("passed", False),
        ("not-requested", False),
        ("unavailable", False),
        ("failed", True),
        ("timed-out", True),
    ],
)
def test_quarantined_partial_requires_validated_failure_or_timeout_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    may_publish: bool,
) -> None:
    if status == "passed":
        stage = _stage_with_registered_script(tmp_path, monkeypatch)
        mtex_result = _passed_mtex_result(stage)
    else:
        stage = _stage(tmp_path)
        mtex_result = (
            None if status == "not-requested" else _nonpassed_mtex_result(status)
        )
    quarantine = stage.staging_path / "diagnostics/quarantine/density.partial"
    quarantine.parent.mkdir(parents=True, exist_ok=True)
    quarantine.write_text("retained partial evidence\n", encoding="utf-8")

    if not may_publish:
        (stage.staging_path / "diagnostics/mtex-status.json").write_text(
            canonical_json(
                {
                    "schema_version": 1,
                    "requested_profile": "smoke",
                    "status": "failed",
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(SphericalBundlePartialError, match="quarantined.*partial"):
            finalize_spherical_bundle(stage, mtex_result=mtex_result)
        assert stage.staging_path.is_dir()
        assert not list(tmp_path.glob("s2-run-*"))
        failure = json.loads(
            (stage.staging_path / "diagnostics/mtex-status.json").read_text()
        )
        assert failure["status"] == "finalization-failed"
        assert failure["failure_kind"] == "quarantined-partial-status"
        return

    result = finalize_spherical_bundle(stage, mtex_result=mtex_result)
    assert result.mtex_status == status
    assert (result.path / "diagnostics/quarantine/density.partial").read_text() == (
        "retained partial evidence\n"
    )
    manifest = json.loads((result.path / "manifest.json").read_text())
    assert "diagnostics/quarantine/density.partial" in manifest["files"]
    diagnostic = json.loads((result.path / "diagnostics/mtex-status.json").read_text())
    assert diagnostic["status"] == status


def test_manifest_is_written_last_and_never_self_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kikuchi_lab.spherical_intensity import bundle as bundle_module

    writes: list[str] = []
    original = bundle_module._write_json

    def recording_writer(path: Path, value: object) -> None:
        writes.append(path.name)
        original(path, value)

    monkeypatch.setattr(bundle_module, "_write_json", recording_writer)
    result = _python_only_bundle(tmp_path)
    manifest = json.loads((result.path / "manifest.json").read_text())
    assert writes[-1] == "manifest.json"
    assert "manifest.json" not in manifest["files"]
    assert result.manifest_sha256 not in canonical_json(manifest)


def test_finalizer_fsyncs_every_pre_manifest_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kikuchi_lab.spherical_intensity import bundle as bundle_module

    stage = _stage(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(
        bundle_module,
        "_fsync_existing_file",
        lambda path: calls.append(str(path.relative_to(stage.staging_path))),
    )
    finalize_spherical_bundle(stage, mtex_result=None)
    assert set(calls) == BASE_FILES


def test_existing_destination_is_never_replaced_even_at_final_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kikuchi_lab.spherical_intensity import bundle as bundle_module

    first = _python_only_bundle(tmp_path)
    sentinel = first.path / "sentinel.txt"
    sentinel.write_text("original", encoding="utf-8")
    second = _stage(tmp_path)
    with pytest.raises(SphericalBundleExistsError):
        finalize_spherical_bundle(second, mtex_result=None)
    assert sentinel.read_text(encoding="utf-8") == "original"

    collision_root = tmp_path / "late"
    stage = _stage(collision_root)
    real_promote = bundle_module._promote_directory_no_replace

    def colliding_promote(source: Path, destination: Path) -> None:
        destination.mkdir()
        (destination / "sentinel.txt").write_text("racer", encoding="utf-8")
        real_promote(source, destination)

    monkeypatch.setattr(bundle_module, "_promote_directory_no_replace", colliding_promote)
    with pytest.raises(SphericalBundleExistsError):
        finalize_spherical_bundle(stage, mtex_result=None)
    assert next(collision_root.glob("s2-run-*/sentinel.txt")).read_text() == "racer"
    assert stage.staging_path.is_dir()
    assert not list(collision_root.glob(".*.publishing"))


def test_run_id_is_path_neutral_and_only_stable_mtex_observations_affect_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _python_only_bundle(tmp_path / "relocated-a")
    second = _python_only_bundle(tmp_path / "relocated-b")
    assert first.run_id == second.run_id

    changed_recipe = spherical_recipe(half_size=3)
    changed_build = build_spherical_intensity(
        synthetic_simulation(symmetric_master(half_size=3)),
        fixture_source(),
        changed_recipe,
    )
    changed_stage = stage_spherical_bundle(
        tmp_path / "changed-science",
        changed_build,
        changed_recipe,
        fixture_source(),
    )
    changed_science = finalize_spherical_bundle(changed_stage, mtex_result=None)
    assert changed_science.run_id != first.run_id

    stage_a = _stage_with_registered_script(tmp_path / "mtex-a", monkeypatch)
    result_a = _passed_mtex_result(stage_a)
    success_a = finalize_spherical_bundle(stage_a, mtex_result=result_a)
    stage_b = _stage_with_registered_script(tmp_path / "mtex-b", monkeypatch)
    result_b = _passed_mtex_result(
        stage_b,
        command=("/different/local/matlab", "-batch", "run"),
        elapsed_seconds=99.0,
    )
    success_b = finalize_spherical_bundle(stage_b, mtex_result=result_b)
    assert success_a.run_id == success_b.run_id
    assert success_a.run_id != first.run_id

    stage_c = _stage_with_registered_script(tmp_path / "mtex-c", monkeypatch)
    changed_version = finalize_spherical_bundle(
        stage_c,
        mtex_result=_passed_mtex_result(stage_c, matlab_version="24.3.0"),
    )
    stage_d = _stage_with_registered_script(tmp_path / "mtex-d", monkeypatch)
    changed_status = finalize_spherical_bundle(
        stage_d,
        mtex_result=_nonpassed_mtex_result("failed"),
    )
    stage_e = _stage_with_registered_script(tmp_path / "mtex-e", monkeypatch)
    changed_output = finalize_spherical_bundle(
        stage_e,
        mtex_result=_passed_mtex_result(stage_e, payload_tag="different-content"),
    )
    stage_f = _stage_with_registered_script(tmp_path / "mtex-f", monkeypatch)
    changed_error_result = _passed_mtex_result(stage_f)
    changed_error_metrics = dict(changed_error_result.metrics)
    changed_error_metrics["node_normalized_error"] = 1.0e-9
    changed_error = finalize_spherical_bundle(
        stage_f,
        mtex_result=replace(changed_error_result, metrics=changed_error_metrics),
    )
    assert changed_version.run_id != success_a.run_id
    assert changed_status.run_id != success_a.run_id
    assert changed_output.run_id == success_a.run_id
    assert changed_error.run_id == success_a.run_id
    passed_manifest = json.loads((success_a.path / "manifest.json").read_text())
    assert passed_manifest["run_identity"]["mtex"] == {
        "requested_profile": "smoke",
        "status": "passed",
        "versions": {"matlab": "24.2.0", "mtex": "mtex-6.1.1"},
    }


@pytest.mark.parametrize("status", ["unavailable", "failed", "timed-out"])
def test_future_nonpassed_mtex_contract_is_diagnostic_but_status_stable(
    tmp_path: Path, status: str
) -> None:
    result = finalize_spherical_bundle(
        _stage(tmp_path),
        mtex_result=_nonpassed_mtex_result(status),
    )
    manifest = json.loads((result.path / "manifest.json").read_text())
    assert result.mtex_status == status
    assert manifest["run_identity"]["mtex"] == {
        "requested_profile": "smoke",
        "status": status,
    }
    diagnostic = json.loads((result.path / "diagnostics/mtex-status.json").read_text())
    assert diagnostic["command"][0] == "/private/tools/matlab"
    assert diagnostic["normalized_error"].startswith("normalized diagnostic")


@pytest.mark.parametrize("invalid_status", ["success", "cancelled", "passed "])
def test_future_mtex_contract_rejects_noncanonical_status(
    tmp_path: Path, invalid_status: str
) -> None:
    stage = _stage(tmp_path)
    with pytest.raises(ValueError, match="status"):
        finalize_spherical_bundle(
            stage,
            mtex_result=_nonpassed_mtex_result(invalid_status),
        )
    assert stage.staging_path.is_dir()


def test_future_mtex_seam_rejects_arbitrary_mapping(tmp_path: Path) -> None:
    stage = _stage(tmp_path)
    with pytest.raises(TypeError, match="MtexRunResult|contract"):
        finalize_spherical_bundle(stage, mtex_result={"status": "failed"})


@pytest.mark.parametrize(
    "corruption",
    [
        "missing-output",
        "hash",
        "point-count",
        "node-error",
        "density-node-error",
        "mtex-version",
    ],
)
def test_passed_mtex_requires_complete_validated_outputs_and_profile_constants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corruption: str
) -> None:
    stage = _stage_with_registered_script(tmp_path, monkeypatch)
    result = _passed_mtex_result(stage)
    metrics = dict(result.metrics)
    if corruption == "missing-output":
        (stage.staging_path / result.produced_files[0]).unlink()
    elif corruption == "hash":
        validated = dict(metrics["validated_files"])
        first = result.produced_files[0]
        validated[first] = {"bytes": 1, "sha256": "0" * 64}
        metrics["validated_files"] = validated
        result = replace(result, metrics=metrics)
    elif corruption == "point-count":
        metrics["point_count"] = int(metrics["point_count"]) + 1
        result = replace(result, metrics=metrics)
    elif corruption == "node-error":
        metrics["node_normalized_error"] = 1.1e-8
        result = replace(result, metrics=metrics)
    elif corruption == "density-node-error":
        metrics["density_node_normalized_error"] = 1.1e-8
        result = replace(result, metrics=metrics)
    else:
        metrics["mtex_version"] = "mtex-6.2.0"
        result = replace(result, metrics=metrics)

    with pytest.raises(ValueError, match="MTEX|mtex|output|hash|point|node|version"):
        finalize_spherical_bundle(stage, mtex_result=result)
    assert stage.staging_path.is_dir()


def test_passed_mtex_output_set_tracks_axial_absence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = noncentrosymmetric_source()
    build = _without_axial_build()
    stage = _stage_with_registered_script(
        tmp_path,
        monkeypatch,
        build=build,
        source=source,
    )
    mtex = _passed_mtex_result(stage)
    assert "figures/directional-vs-axial.png" not in mtex.produced_files
    result = finalize_spherical_bundle(stage, mtex_result=mtex)
    assert result.mtex_status == "passed"


def test_passed_mtex_requires_separate_density_node_error_metric(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage = _stage_with_registered_script(tmp_path, monkeypatch)
    result = _passed_mtex_result(stage)
    metrics = dict(result.metrics)
    metrics.pop("density_node_normalized_error", None)

    with pytest.raises(ValueError, match="density.*node|metric"):
        finalize_spherical_bundle(
            stage,
            mtex_result=replace(result, metrics=metrics),
        )
    assert stage.staging_path.is_dir()


def test_passed_mtex_validates_density_node_error_without_weakening_raw_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    valid_stage = _stage_with_registered_script(tmp_path / "valid", monkeypatch)
    valid_result = _passed_mtex_result(valid_stage)
    valid_metrics = dict(valid_result.metrics)
    valid_metrics["density_node_normalized_error"] = 7.0e-9
    passed = finalize_spherical_bundle(
        valid_stage,
        mtex_result=replace(valid_result, metrics=valid_metrics),
    )
    assert passed.mtex_status == "passed"

    density_stage = _stage_with_registered_script(tmp_path / "density", monkeypatch)
    density_result = _passed_mtex_result(density_stage)
    density_metrics = dict(density_result.metrics)
    density_metrics["density_node_normalized_error"] = 1.1e-8
    with pytest.raises(ValueError, match="density.*node|node.*density"):
        finalize_spherical_bundle(
            density_stage,
            mtex_result=replace(density_result, metrics=density_metrics),
        )

    raw_stage = _stage_with_registered_script(tmp_path / "raw", monkeypatch)
    raw_result = _passed_mtex_result(raw_stage)
    raw_metrics = dict(raw_result.metrics)
    raw_metrics["density_node_normalized_error"] = 7.0e-9
    raw_metrics["node_normalized_error"] = 1.1e-8
    with pytest.raises(ValueError, match="node"):
        finalize_spherical_bundle(
            raw_stage,
            mtex_result=replace(raw_result, metrics=raw_metrics),
        )


def test_same_passed_mtex_content_keeps_run_id_and_never_replaces_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_stage = _stage_with_registered_script(tmp_path, monkeypatch)
    first_mtex = _passed_mtex_result(first_stage)
    first = finalize_spherical_bundle(first_stage, mtex_result=first_mtex)
    sentinel = first.path / "winner.txt"
    sentinel.write_text("winner", encoding="utf-8")

    second_stage = _stage_with_registered_script(tmp_path, monkeypatch)
    second_mtex = _passed_mtex_result(
        second_stage,
        command=("/another/local/matlab", "-batch", "run"),
        elapsed_seconds=44.0,
    )
    with pytest.raises(SphericalBundleExistsError):
        finalize_spherical_bundle(second_stage, mtex_result=second_mtex)
    assert sentinel.read_text(encoding="utf-8") == "winner"
    assert second_stage.staging_path.is_dir()


def test_same_stable_id_with_different_derivatives_retains_investigation_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kikuchi_lab.spherical_intensity import bundle as bundle_module

    first_stage = _stage_with_registered_script(tmp_path, monkeypatch)
    first = finalize_spherical_bundle(
        first_stage,
        mtex_result=_passed_mtex_result(first_stage, payload_tag="winner"),
    )
    winner_manifest = first.manifest_sha256

    losing_stage = _stage_with_registered_script(tmp_path, monkeypatch)
    losing_result = _passed_mtex_result(losing_stage, payload_tag="different")
    with pytest.raises(bundle_module.SphericalBundleInvestigationError, match="investigat"):
        finalize_spherical_bundle(losing_stage, mtex_result=losing_result)

    assert losing_stage.staging_path.is_dir()
    assert _sha256(first.path / "manifest.json") == winner_manifest
    investigation = json.loads(
        (losing_stage.staging_path / "diagnostics/collision-investigation.json").read_text()
    )
    assert investigation["run_id"] == first.run_id
    assert investigation["status"] == "collision-requires-investigation"
    assert investigation["differing_output_records"]
    assert (losing_stage.staging_path / "diagnostics/mtex-status.json").is_file()


def test_manifest_run_identity_matches_path_and_excludes_diagnostic_prose(
    tmp_path: Path,
) -> None:
    result = finalize_spherical_bundle(
        _stage(tmp_path),
        mtex_result=_nonpassed_mtex_result(
            "failed",
            normalized_error="local error /private/tmp/example",
            elapsed_seconds=12.5,
        ),
    )
    manifest = json.loads((result.path / "manifest.json").read_text())
    assert manifest["run_identity"]["schema_version"] == 1
    assert stable_id("s2-run", manifest["run_identity"]) == result.run_id
    assert (
        "source_kinematical_recipe"
        not in manifest["run_identity"]["scientific_identity"]["recipe"]["content"]
    )
    assert manifest["run_identity"]["mtex"] == {
        "requested_profile": "smoke",
        "status": "failed",
    }
    assert "local error" not in canonical_json(manifest["run_identity"])
    assert manifest["identity_policy"] == {
        "scientific_files": "registered hashes included in stable run identity",
        "diagnostics": "inventoried by manifest and excluded from stable run identity",
    }
    status = json.loads((result.path / "diagnostics/mtex-status.json").read_text())
    assert status["normalized_error"] == "local error /private/tmp/example"


def test_diagnostic_files_are_inventoried_without_perturbing_run_identity(
    tmp_path: Path,
) -> None:
    first_stage = _stage(tmp_path / "first")
    first_log = first_stage.staging_path / "diagnostics/local.log"
    first_log.parent.mkdir(parents=True, exist_ok=True)
    first_log.write_text("machine-local first\n", encoding="utf-8")
    first = finalize_spherical_bundle(first_stage, mtex_result=None)

    second_stage = _stage(tmp_path / "second")
    second_log = second_stage.staging_path / "diagnostics/local.log"
    second_log.parent.mkdir(parents=True, exist_ok=True)
    second_log.write_text("machine-local second\n", encoding="utf-8")
    second = finalize_spherical_bundle(second_stage, mtex_result=None)

    assert first.run_id == second.run_id
    assert first.manifest_sha256 != second.manifest_sha256
    manifest = json.loads((first.path / "manifest.json").read_text())
    assert "diagnostics/local.log" in manifest["files"]


def test_successful_mtex_versions_cannot_smuggle_a_local_path_into_run_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage = _stage_with_registered_script(tmp_path, monkeypatch)
    result = _passed_mtex_result(stage, matlab_version="/Applications/MATLAB_R2024b.app")
    with pytest.raises(ValueError, match="local path"):
        finalize_spherical_bundle(stage, mtex_result=result)
    assert stage.staging_path.is_dir()
    assert not [path for path in tmp_path.iterdir() if path.name.startswith("s2-run-")]


def test_stage_and_build_are_deeply_immutable(tmp_path: Path) -> None:
    build = small_spherical_build()
    stage = _stage(tmp_path, build=build)
    with pytest.raises(FrozenInstanceError):
        stage.field_id = "changed"
    with pytest.raises(TypeError):
        stage.scientific_identity["field_id"] = "changed"
    with pytest.raises(TypeError):
        stage.scientific_identity["recipe"]["content"]["name"] = "changed"
    with pytest.raises(ValueError):
        build.field.xyz.setflags(write=True)
