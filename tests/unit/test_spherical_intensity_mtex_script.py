from __future__ import annotations

from dataclasses import replace
import hashlib
from importlib import import_module
from pathlib import Path
import re
import sys

import pytest

from kikuchi_lab.spherical_intensity import generate_mtex_script
from kikuchi_lab.spherical_intensity.contracts import SphericalIntensityRecipe


sys.path.insert(0, str(Path(__file__).parents[1]))
_fixtures = import_module("spherical_fixtures")
spherical_recipe = _fixtures.spherical_recipe


def _acceptance_recipe() -> SphericalIntensityRecipe:
    recipe = spherical_recipe()
    return replace(
        recipe,
        profile=replace(
            recipe.profile,
            name="acceptance",
            half_size=1024,
            point_count=100_000,
            sampling_resolution_deg=0.25,
            timeout_seconds=900,
        ),
    )


def test_generated_mtex_script_is_portable_directional_and_exact_node() -> None:
    script = generate_mtex_script(
        spherical_recipe(), expected_node_count=97, axial_available=True
    )

    required = (
        "bundleRoot = fileparts(mfilename('fullpath'));",
        "mtexRoot = getenv('KIKUCHI_MTEX_ROOT');",
        "assert(isfolder(mtexRoot), 'KIKUCHI_MTEX_ROOT is missing or invalid');",
        "assert(isfile(fullfile(mtexRoot, 'startup_mtex.m')));",
        "startup_mtex('noMenu');",
        "nodes.antipodal = false;",
        "unique(nodes(:), 'stable', 'noAntipodal')",
        "rawField = interp(nodes, T.intensity_raw, 'linear');",
        "densityField = interp(nodes, T.density_weight, 'linear');",
        "assert(isa(rawField, 'S2FunTri'));",
        "assert(isa(densityField, 'S2FunTri'));",
        "assert(nodeError / nodeScale <= 1e-08);",
        "rng(20260713, 'twister');",
        "discreteSample(densityField, pointCount",
        "onCleanup(@() rng(oldRng))",
    )
    for statement in required:
        assert statement in script

    assert "MarkerAlpha" not in script
    assert not re.search(r"(?:^|[\s'(])/(?:Users|home|private|tmp)/", script)
    assert not re.search(r"[A-Za-z]:[\\/]", script)
    assert "file://" not in script
    assert "{{" not in script
    assert "}}" not in script
    assert script.endswith("\n")
    assert "\r" not in script


def test_generated_script_is_byte_deterministic_and_profile_bounded() -> None:
    smoke_recipe = spherical_recipe()
    first = generate_mtex_script(
        smoke_recipe, expected_node_count=97, axial_available=False
    )
    second = generate_mtex_script(
        smoke_recipe, expected_node_count=97, axial_available=False
    )
    acceptance = generate_mtex_script(
        _acceptance_recipe(), expected_node_count=97, axial_available=False
    )

    assert first.encode("utf-8") == second.encode("utf-8")
    assert hashlib.sha256(first.encode()).hexdigest() == hashlib.sha256(
        second.encode()
    ).hexdigest()
    assert "pointCount = 10000;" in first
    assert "sampleResolutionDeg = 1;" in first
    assert "pointCount = 100000;" in acceptance
    assert "sampleResolutionDeg = 0.25;" in acceptance
    assert "displayResolutionDeg = 1;" in first
    assert "nodeTolerance = 1e-08;" in first

    normalized_smoke = first.replace("pointCount = 10000;", "pointCount = PROFILE;").replace(
        "sampleResolutionDeg = 1;", "sampleResolutionDeg = PROFILE;"
    ).replace("'profile', 'smoke'", "'profile', 'PROFILE'")
    normalized_acceptance = acceptance.replace(
        "pointCount = 100000;", "pointCount = PROFILE;"
    ).replace("sampleResolutionDeg = 0.25;", "sampleResolutionDeg = PROFILE;").replace(
        "'profile', 'acceptance'", "'profile', 'PROFILE'"
    )
    assert normalized_smoke == normalized_acceptance


def test_directional_and_optional_axial_semantics_are_explicit_and_separate() -> None:
    directional = generate_mtex_script(
        spherical_recipe(), expected_node_count=97, axial_available=False
    )
    axial = generate_mtex_script(
        spherical_recipe(), expected_node_count=97, axial_available=True
    )

    assert "nodes.antipodal = false;" in directional
    assert "rawField.antipodal = true" not in directional
    assert "densityField.antipodal = true" not in directional
    assert "forsterite-s2-axial.csv" not in directional
    assert "directional-vs-axial.png" not in directional

    assert "AT = readtable(fullfile(bundleRoot, 'forsterite-s2-axial.csv'));" in axial
    assert "axialNodes.antipodal = true;" in axial
    assert "axialField = interp(axialNodes, AT.intensity_raw, 'linear');" in axial
    assert "axialField.antipodal = true;" in axial
    assert "nodes.antipodal = false;" in axial
    assert "rawField.antipodal = true" not in axial
    assert "densityField.antipodal = true" not in axial
    load_end = axial.index("writeHeartbeat(progressPath, 'load', 'end');")
    triangulation_start = axial.index(
        "writeHeartbeat(progressPath, 'triangulation', 'start');"
    )
    axial_triangulation = axial.index(
        "axialField = interp(axialNodes, AT.intensity_raw, 'linear');"
    )
    triangulation_end = axial.index(
        "writeHeartbeat(progressPath, 'triangulation', 'end');"
    )
    node_evaluation_start = axial.index(
        "writeHeartbeat(progressPath, 'node-evaluation', 'start');"
    )
    axial_node_evaluation = axial.index(
        "axialNodeError = max(abs(axialField.eval(axialNodes) - AT.intensity_raw));"
    )
    node_evaluation_end = axial.index(
        "writeHeartbeat(progressPath, 'node-evaluation', 'end');"
    )
    assert load_end < triangulation_start < axial_triangulation < triangulation_end
    assert (
        triangulation_end
        < node_evaluation_start
        < axial_node_evaluation
        < node_evaluation_end
    )


def test_script_validates_exact_directional_and_axial_tables() -> None:
    script = generate_mtex_script(
        spherical_recipe(), expected_node_count=97, axial_available=True
    )

    assertions = (
        "assert(isequal(T.Properties.VariableNames, requiredColumns));",
        "assert(height(T) == 97);",
        "assert(all(isfinite(xyz), 'all'));",
        "assert(max(abs(vecnorm(xyz, 2, 2) - 1)) <= 5e-13);",
        "assert(all(isfinite(T.intensity_raw)));",
        "assert(all(isfinite(T.intensity_normalized)));",
        "assert(all(T.intensity_normalized >= 0 & T.intensity_normalized <= 1));",
        "assert(all(isfinite(T.density_weight) & T.density_weight >= 0));",
        "assert(any(T.density_weight > 0));",
        "assert(isequal(AT.Properties.VariableNames, axialRequiredColumns));",
        (
            "assert(height(AT) == "
            "ledger.metadata.diagnostics.axial.representative_count);"
        ),
        "assert(all(isfinite(axialXYZ), 'all'));",
        "assert(max(abs(vecnorm(axialXYZ, 2, 2) - 1)) <= 5e-13);",
        "assert(all(isfinite(AT.intensity_raw)));",
        "assert(all(isfinite(AT.intensity_normalized)));",
        "assert(all(AT.intensity_normalized >= 0 & AT.intensity_normalized <= 1));",
        "assert(all(isfinite(AT.density_weight) & AT.density_weight >= 0));",
        "assert(any(AT.density_weight > 0));",
    )
    for assertion in assertions:
        assert assertion in script


def test_script_has_fixed_atomic_outputs_evidence_and_flushed_heartbeats() -> None:
    script = generate_mtex_script(
        spherical_recipe(), expected_node_count=97, axial_available=True
    )

    for stage in (
        "startup",
        "load",
        "triangulation",
        "node-evaluation",
        "density-sampling",
        "figure-export",
    ):
        assert f"writeHeartbeat(progressPath, '{stage}', 'start');" in script
        assert f"writeHeartbeat(progressPath, '{stage}', 'end');" in script
    assert "function writeHeartbeat(path, stage, event)" in script
    assert "fopen(path, 'a')" in script
    assert "fprintf(file, '%s\\n', jsonencode(record));" in script

    required_outputs = (
        "forsterite-s2-density-vectors.partial.csv",
        "forsterite-s2-density-vectors.csv",
        "figures/exact-node-scatter.partial.png",
        "figures/exact-node-scatter.png",
        "figures/colored-sphere.partial.png",
        "figures/colored-sphere.png",
        "figures/density-cloud.partial.png",
        "figures/density-cloud.png",
        "figures/raw-vs-density-channels.partial.png",
        "figures/raw-vs-density-channels.png",
        "figures/directional-vs-axial.partial.png",
        "figures/directional-vs-axial.png",
        "forsterite-s2-mtex-preview.partial.png",
        "forsterite-s2-mtex-preview.png",
        "mtex-result.json.partial",
        "mtex-result.json",
    )
    for output in required_outputs:
        assert output in script

    assert "'Position', [100 100 1600 900]" in script
    assert "'Visible', 'off'" in script
    assert "'Color', 'w'" in script
    assert "axis vis3d" in script
    assert "drawnow" in script
    assert "exportgraphics" in script
    assert "scatter(nodes, T.intensity_raw, 'complete'" in script
    assert "plot3d(rawField, 'resolution', displayResolutionDeg * degree)" in script
    assert "scatter(densityVectors, 'complete'" in script
    assert "movefile(cloudPartial, cloudFinal, 'f');" in script
    assert "movefile(resultPartial, resultFinal, 'f');" in script
    assert script.index("movefile(resultPartial, resultFinal, 'f');") > script.index(
        "writeHeartbeat(progressPath, 'figure-export', 'end');"
    )


@pytest.mark.parametrize("expected_node_count", [True, 0, -1, 1.5])
def test_generator_rejects_invalid_node_counts(expected_node_count: object) -> None:
    with pytest.raises(ValueError, match="expected_node_count"):
        generate_mtex_script(
            spherical_recipe(),
            expected_node_count=expected_node_count,  # type: ignore[arg-type]
            axial_available=True,
        )


def test_generator_rejects_noncanonical_inputs() -> None:
    with pytest.raises(TypeError, match="recipe"):
        generate_mtex_script(object(), 97, True)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="axial_available"):
        generate_mtex_script(
            spherical_recipe(), 97, 1  # type: ignore[arg-type]
        )
