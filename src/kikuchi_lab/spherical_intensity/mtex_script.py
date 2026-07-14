"""Deterministic, path-neutral MATLAB/MTEX source generation."""

from __future__ import annotations

from .contracts import SphericalIntensityRecipe


_DIRECTIONAL_COLUMNS = (
    "'x','y','z','hemisphere','source_row','source_column', ...\n"
    "  'intensity_raw','intensity_normalized','density_weight'"
)
_AXIAL_COLUMNS = (
    "'x','y','z','member_a_hemisphere','member_a_row','member_a_column', ...\n"
    "  'member_b_hemisphere','member_b_row','member_b_column','intensity_raw', ...\n"
    "  'intensity_normalized','density_weight'"
)


_AXIAL_BLOCK = """\
AT = readtable(fullfile(bundleRoot, 'forsterite-s2-axial.csv'));
axialRequiredColumns = {{{axial_columns}}};
assert(isequal(AT.Properties.VariableNames, axialRequiredColumns));
ledger = jsondecode(fileread(fullfile(bundleRoot, 'forsterite-s2-intensity.json')));
assert(height(AT) == ledger.metadata.diagnostics.axial.representative_count);
axialXYZ = [AT.x, AT.y, AT.z];
assert(all(isfinite(axialXYZ), 'all'));
assert(max(abs(vecnorm(axialXYZ, 2, 2) - 1)) <= 5e-13);
assert(all(isfinite(AT.intensity_raw)));
assert(all(isfinite(AT.intensity_normalized)));
assert(all(AT.intensity_normalized >= 0 & AT.intensity_normalized <= 1));
assert(all(isfinite(AT.density_weight) & AT.density_weight >= 0));
assert(any(AT.density_weight > 0));
assert(all(isfinite([AT.member_a_hemisphere, AT.member_a_row, AT.member_a_column, ...
  AT.member_b_hemisphere, AT.member_b_row, AT.member_b_column]), 'all'));
assert(all(AT.member_a_hemisphere == 1));
assert(all(AT.member_b_hemisphere == -1));
"""


_AXIAL_TRIANGULATION_BLOCK = """\
axialNodes = vector3d(axialXYZ, 'normalize');
axialNodes.antipodal = true;
[uniqueAxialNodes, ~, ~] = unique(axialNodes(:), 'stable');
assert(length(uniqueAxialNodes) == length(axialNodes), ...
  'Duplicate axes would be averaged by S2FunTri');
axialField = interp(axialNodes, AT.intensity_raw, 'linear');
assert(isa(axialField, 'S2FunTri'));
axialField.antipodal = true;
"""


_AXIAL_NODE_EVALUATION_BLOCK = """\
axialNodeError = max(abs(axialField.eval(axialNodes) - AT.intensity_raw));
axialNodeScale = max(max(abs(AT.intensity_raw)), eps);
assert(axialNodeError / axialNodeScale <= nodeTolerance);
"""


_AXIAL_FIGURE_BLOCK = """\
[comparisonFigure, comparisonFigureCleanup, comparisonMtexFigure] = ...
  newMtexEvidenceFigure([2 2]);
comparisonLimits = finiteLimits([T.intensity_raw; AT.intensity_raw]);
directionalAxes = plotCompleteValues(comparisonMtexFigure, 1, nodes, ...
  T.intensity_raw, 'Directional raw intensity', comparisonLimits);
axialAxes = plotCompleteValues(comparisonMtexFigure, 3, axialNodes, ...
  AT.intensity_raw, 'Axial raw intensity', comparisonLimits);
assertIdenticalProjectionSettings(directionalAxes, axialAxes);
exportAtomicFigure(comparisonFigure, bundleRoot, ...
  'figures/directional-vs-axial.partial.png', ...
  'figures/directional-vs-axial.png');
clear comparisonFigureCleanup;
panelFiles{end + 1} = fullfile(bundleRoot, 'figures', ...
  'directional-vs-axial.png');
panelLabels{end + 1} = 'Directional vs axial';
"""


_TEMPLATE = """\
bundleRoot = fileparts(mfilename('fullpath'));
mtexRoot = getenv('KIKUCHI_MTEX_ROOT');
assert(isfolder(mtexRoot), 'KIKUCHI_MTEX_ROOT is missing or invalid');
assert(isfile(fullfile(mtexRoot, 'startup_mtex.m')));

diagnosticsRoot = fullfile(bundleRoot, 'diagnostics');
figuresRoot = fullfile(bundleRoot, 'figures');
if ~isfolder(diagnosticsRoot), mkdir(diagnosticsRoot); end
if ~isfolder(figuresRoot), mkdir(figuresRoot); end
progressPath = fullfile(bundleRoot, 'diagnostics', 'mtex-progress.jsonl');
writeHeartbeat(progressPath, 'startup', 'start');
originalFolder = pwd;
restoreFolder = onCleanup(@() cd(originalFolder));
cd(mtexRoot);
addpath(mtexRoot);
startup_mtex('noMenu');
matlabVersion = version;
mtexVersion = getMTEXpref('version');
cd(bundleRoot);
writeHeartbeat(progressPath, 'startup', 'end');

expectedNodeCount = {expected_node_count};
pointCount = {point_count};
sampleResolutionDeg = {sample_resolution};
displayResolutionDeg = {display_resolution};
nodeTolerance = {node_tolerance};
seed = {rng_seed};

writeHeartbeat(progressPath, 'load', 'start');
T = readtable(fullfile(bundleRoot, 'forsterite-s2-intensity.csv'));
requiredColumns = {{{directional_columns}}};
assert(isequal(T.Properties.VariableNames, requiredColumns));
assert(height(T) == {expected_node_count});
xyz = [T.x, T.y, T.z];
assert(all(isfinite(xyz), 'all'));
assert(max(abs(vecnorm(xyz, 2, 2) - 1)) <= 5e-13);
assert(all(isfinite(T.hemisphere)));
assert(all(T.hemisphere == 1 | T.hemisphere == -1));
assert(all(isfinite(T.source_row) & T.source_row >= 0));
assert(all(isfinite(T.source_column) & T.source_column >= 0));
assert(all(isfinite(T.intensity_raw)));
assert(all(isfinite(T.intensity_normalized)));
assert(all(T.intensity_normalized >= 0 & T.intensity_normalized <= 1));
assert(all(isfinite(T.density_weight) & T.density_weight >= 0));
assert(any(T.density_weight > 0));
{axial_block}writeHeartbeat(progressPath, 'load', 'end');

writeHeartbeat(progressPath, 'triangulation', 'start');
nodes = vector3d(xyz, 'normalize');
nodes.antipodal = false;
[uniqueNodes, ~, ~] = unique(nodes(:), 'stable', 'noAntipodal');
assert(length(uniqueNodes) == length(nodes), ...
  'Duplicate directions would be averaged by S2FunTri');
rawField = interp(nodes, T.intensity_raw, 'linear');
assert(isa(rawField, 'S2FunTri'));
densityField = interp(nodes, T.density_weight, 'linear');
assert(isa(densityField, 'S2FunTri'));
{axial_triangulation_block}writeHeartbeat(progressPath, 'triangulation', 'end');

writeHeartbeat(progressPath, 'node-evaluation', 'start');
nodeError = max(abs(rawField.eval(nodes) - T.intensity_raw));
nodeScale = max(max(abs(T.intensity_raw)), eps);
nodeNormalizedError = nodeError / nodeScale;
assert(nodeNormalizedError <= 1e-08);
assert(nodeNormalizedError <= nodeTolerance);
densityNodeError = max(abs(densityField.eval(nodes) - T.density_weight));
densityNodeScale = max(max(abs(T.density_weight)), eps);
densityNodeNormalizedError = densityNodeError / densityNodeScale;
assert(densityNodeNormalizedError <= 1e-08);
assert(densityNodeNormalizedError <= nodeTolerance);
{axial_node_evaluation_block}writeHeartbeat(progressPath, 'node-evaluation', 'end');

writeHeartbeat(progressPath, 'density-sampling', 'start');
oldRng = rng;
restoreRng = onCleanup(@() rng(oldRng));
rng({rng_seed}, '{rng_generator}');
densityVectors = discreteSample(densityField, pointCount, ...
  'resolution', sampleResolutionDeg * degree);
cloudXYZ = densityVectors.xyz;
clear restoreRng;
assert(size(cloudXYZ, 1) == pointCount);
assert(size(cloudXYZ, 2) == 3);
assert(all(isfinite(cloudXYZ), 'all'));
assert(max(abs(vecnorm(cloudXYZ, 2, 2) - 1)) <= 5e-13);

cloudPartial = fullfile(bundleRoot, 'forsterite-s2-density-vectors.partial.csv');
cloudFinal = fullfile(bundleRoot, 'forsterite-s2-density-vectors.csv');
cloudFile = fopen(cloudPartial, 'w');
assert(cloudFile >= 0);
cloudCleanup = onCleanup(@() fclose(cloudFile));
fprintf(cloudFile, 'x,y,z\\n');
fprintf(cloudFile, '%.17g,%.17g,%.17g\\n', cloudXYZ.');
clear cloudCleanup;
movefile(cloudPartial, cloudFinal, 'f');
writeHeartbeat(progressPath, 'density-sampling', 'end');

writeHeartbeat(progressPath, 'figure-export', 'start');
rawLimits = finiteLimits(T.intensity_raw);
densityLimits = finiteLimits(T.density_weight);
channelLimits = finiteLimits([T.intensity_raw; T.density_weight]);
panelFiles = {{}};
panelLabels = {{}};

[nodeFigure, nodeFigureCleanup, nodeMtexFigure] = ...
  newMtexEvidenceFigure([1 2]);
plotCompleteValues(nodeMtexFigure, 1, nodes, T.intensity_raw, ...
  'Exact directional nodes', rawLimits);
exportAtomicFigure(nodeFigure, bundleRoot, ...
  'figures/exact-node-scatter.partial.png', ...
  'figures/exact-node-scatter.png');
clear nodeFigureCleanup;
panelFiles{{end + 1}} = fullfile(bundleRoot, 'figures', ...
  'exact-node-scatter.png');
panelLabels{{end + 1}} = 'Exact nodes';

[sphereFigure, sphereFigureCleanup, sphereMtexFigure] = ...
  newMtexEvidenceFigure([1 1]);
plotOwnedSphere(sphereMtexFigure, rawField, displayResolutionDeg, ...
  'Triangulated raw intensity', rawLimits);
exportAtomicFigure(sphereFigure, bundleRoot, ...
  'figures/colored-sphere.partial.png', 'figures/colored-sphere.png');
clear sphereFigureCleanup;
panelFiles{{end + 1}} = fullfile(bundleRoot, 'figures', 'colored-sphere.png');
panelLabels{{end + 1}} = 'Colored sphere';

[densityFigure, densityFigureCleanup, densityMtexFigure] = ...
  newMtexEvidenceFigure([1 2]);
plotCompletePoints(densityMtexFigure, 1, densityVectors, ...
  'Density sampled vectors', densityLimits);
exportAtomicFigure(densityFigure, bundleRoot, ...
  'figures/density-cloud.partial.png', 'figures/density-cloud.png');
clear densityFigureCleanup;
panelFiles{{end + 1}} = fullfile(bundleRoot, 'figures', 'density-cloud.png');
panelLabels{{end + 1}} = 'Density cloud';

[channelFigure, channelFigureCleanup, channelMtexFigure] = ...
  newMtexEvidenceFigure([2 2]);
rawChannelAxes = plotCompleteValues(channelMtexFigure, 1, nodes, ...
  T.intensity_raw, 'Raw intensity', channelLimits);
densityChannelAxes = plotCompleteValues(channelMtexFigure, 3, nodes, ...
  T.density_weight, 'Density weight', channelLimits);
assertIdenticalProjectionSettings(rawChannelAxes, densityChannelAxes);
exportAtomicFigure(channelFigure, bundleRoot, ...
  'figures/raw-vs-density-channels.partial.png', ...
  'figures/raw-vs-density-channels.png');
clear channelFigureCleanup;
panelFiles{{end + 1}} = fullfile(bundleRoot, 'figures', ...
  'raw-vs-density-channels.png');
panelLabels{{end + 1}} = 'Raw vs density';

{axial_figure_block}[previewFigure, previewFigureCleanup] = newEvidenceFigure();
previewLayout = tiledlayout(previewFigure, 2, 3, ...
  'TileSpacing', 'compact', 'Padding', 'compact');
for panelIndex = 1:numel(panelFiles)
  previewAxis = nexttile(previewLayout);
  panelImage = imread(panelFiles{{panelIndex}});
  image(previewAxis, panelImage);
  axis(previewAxis, 'image');
  axis(previewAxis, 'off');
  title(previewAxis, panelLabels{{panelIndex}});
end
exportAtomicFigure(previewFigure, bundleRoot, ...
  'forsterite-s2-mtex-preview.partial.png', ...
  'forsterite-s2-mtex-preview.png');
clear previewFigureCleanup;
writeHeartbeat(progressPath, 'figure-export', 'end');

completedStages = {{'startup','load','triangulation','node-evaluation', ...
  'density-sampling','figure-export'}};
outputPaths = {{ ...
  'forsterite-s2-density-vectors.csv', ...
  'forsterite-s2-mtex-preview.png', ...
  'figures/exact-node-scatter.png', ...
  'figures/colored-sphere.png', ...
  'figures/density-cloud.png', ...
  'figures/raw-vs-density-channels.png'{axial_result_path} ...
}};
outputHashes = repmat(struct('path', '', 'sha256', ''), numel(outputPaths), 1);
for outputIndex = 1:numel(outputPaths)
  outputHashes(outputIndex).path = outputPaths{{outputIndex}};
  outputHashes(outputIndex).sha256 = sha256File( ...
    fullfile(bundleRoot, outputPaths{{outputIndex}}));
end
result = struct( ...
  'schema_version', 1, ...
  'profile', '{profile_name}', ...
  'node_count', expectedNodeCount, ...
  'node_normalized_error', nodeNormalizedError, ...
  'density_node_normalized_error', densityNodeNormalizedError, ...
  'point_count', pointCount, ...
  'rng_seed', seed, ...
  'rng_generator', '{rng_generator}', ...
  'sampling_resolution_deg', sampleResolutionDeg, ...
  'display_resolution_deg', displayResolutionDeg, ...
  'axial_available', {axial_boolean}, ...
  'matlab_version', matlabVersion, ...
  'mtex_version', mtexVersion, ...
  'completed_stages', {{completedStages}}, ...
  'output_hashes', outputHashes);
resultPartial = fullfile(bundleRoot, 'diagnostics', 'mtex-result.json.partial');
resultFinal = fullfile(bundleRoot, 'diagnostics', 'mtex-result.json');
resultFile = fopen(resultPartial, 'w');
assert(resultFile >= 0);
resultCleanup = onCleanup(@() fclose(resultFile));
fprintf(resultFile, '%s', jsonencode(result));
clear resultCleanup;
movefile(resultPartial, resultFinal, 'f');
clear restoreFolder;

function [figureHandle, figureCleanup] = newEvidenceFigure()
figureHandle = figure('Visible', 'off', 'Color', 'w', ...
  'Position', [100 100 1600 900]);
figureCleanup = onCleanup(@() closeEvidenceFigure(figureHandle));
end

function [figureHandle, figureCleanup, mtexFig] = newMtexEvidenceFigure(layout)
[figureHandle, figureCleanup] = newEvidenceFigure();
mtexFig = mtexFigure('layout', layout, 'Visible', 'off');
assert(isequal(mtexFig.parent, figureHandle));
set(mtexFig.parent, 'Visible', 'off');
end

function axesHandles = plotCompleteValues(mtexFig, startAxis, vectors, ...
  values, label, colorLimits)
activateMtexFigure(mtexFig);
mtexFig.nextAxis(startAxis);
[~, axesHandles] = scatter(vectors, values, 'complete', ...
  'projection', 'earea', 'MarkerSize', 8);
assertOwnedAxes(mtexFig, axesHandles);
mtexFig.drawNow('figSize', 'large');
applyFixedProjection(axesHandles, colorLimits);
applyAxesTitle(axesHandles, label);
set(mtexFig.parent, 'Visible', 'off');
end

function axesHandles = plotCompletePoints(mtexFig, startAxis, vectors, ...
  label, colorLimits)
activateMtexFigure(mtexFig);
mtexFig.nextAxis(startAxis);
[~, axesHandles] = scatter(vectors, 'complete', ...
  'projection', 'earea', 'MarkerSize', 2);
assertOwnedAxes(mtexFig, axesHandles);
mtexFig.drawNow('figSize', 'large');
applyFixedProjection(axesHandles, colorLimits);
applyAxesTitle(axesHandles, label);
set(mtexFig.parent, 'Visible', 'off');
end

function plotOwnedSphere(mtexFig, rawField, displayResolutionDeg, ...
  label, colorLimits)
activateMtexFigure(mtexFig);
sphereAxis = mtexFig.nextAxis(1);
plot3d(rawField, 'resolution', displayResolutionDeg * degree, ...
  'parent', sphereAxis);
assertOwnedAxes(mtexFig, sphereAxis);
mtexFig.drawNow('figSize', 'large');
applyFixedCamera3d(sphereAxis, colorLimits);
title(sphereAxis, label);
set(mtexFig.parent, 'Visible', 'off');
end

function activateMtexFigure(mtexFig)
set(groot, 'CurrentFigure', mtexFig.parent);
set(mtexFig.parent, 'Visible', 'off');
end

function assertOwnedAxes(mtexFig, axesHandles)
for axisIndex = 1:numel(axesHandles)
  ax = axesHandles(axisIndex);
  assert(isequal(ancestor(ax, 'figure'), mtexFig.parent));
end
end

function applyFixedProjection(axesHandles, colorLimits)
for axisIndex = 1:numel(axesHandles)
  ax = axesHandles(axisIndex);
  axis(ax, 'equal');
  axis(ax, 'manual');
  view(ax, 2);
  xlim(ax, [-1.45 1.45]);
  ylim(ax, [-1.45 1.45]);
  colormap(ax, gray(256));
  clim(ax, colorLimits);
  set(ax, 'Color', 'w');
end
drawnow;
end

function applyFixedCamera3d(ax, colorLimits)
axis(ax, 'equal');
axis(ax, 'vis3d');
xlim(ax, [-1.05 1.05]);
ylim(ax, [-1.05 1.05]);
zlim(ax, [-1.05 1.05]);
view(ax, 135, 25);
camup(ax, [0 0 1]);
camtarget(ax, [0 0 0]);
camproj(ax, 'orthographic');
colormap(ax, gray(256));
clim(ax, colorLimits);
set(ax, 'Color', 'w');
drawnow;
end

function applyAxesTitle(axesHandles, label)
for axisIndex = 1:numel(axesHandles)
  title(axesHandles(axisIndex), label);
end
end

function assertIdenticalProjectionSettings(leftAxes, rightAxes)
assert(numel(leftAxes) == numel(rightAxes));
for axisIndex = 1:numel(leftAxes)
  assert(isequal(xlim(leftAxes(axisIndex)), xlim(rightAxes(axisIndex))));
  assert(isequal(ylim(leftAxes(axisIndex)), ylim(rightAxes(axisIndex))));
  assert(isequal(clim(leftAxes(axisIndex)), clim(rightAxes(axisIndex))));
  assert(isequal(view(leftAxes(axisIndex)), view(rightAxes(axisIndex))));
end
end

function closeEvidenceFigure(figureHandle)
if isgraphics(figureHandle, 'figure')
  close(figureHandle);
end
end

function limits = finiteLimits(values)
limits = [min(values), max(values)];
if limits(1) == limits(2)
  padding = max(abs(limits(1)), 1) * eps;
  limits = limits + [-padding, padding];
end
end

function exportAtomicFigure(figureHandle, bundleRoot, partialName, finalName)
drawnow;
partialPath = fullfile(bundleRoot, partialName);
finalPath = fullfile(bundleRoot, finalName);
exportgraphics(figureHandle, partialPath, 'Resolution', 150, ...
  'BackgroundColor', 'white');
movefile(partialPath, finalPath, 'f');
end

function digestText = sha256File(path)
file = fopen(path, 'rb');
assert(file >= 0);
fileCleanup = onCleanup(@() fclose(file));
payload = fread(file, Inf, '*uint8');
clear fileCleanup;
digest = java.security.MessageDigest.getInstance('SHA-256');
digest.update(payload);
digestBytes = typecast(digest.digest(), 'uint8');
digestText = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end

function writeHeartbeat(path, stage, event)
record = struct('stage', stage, 'event', event, ...
  'timestamp_utc', char(datetime('now', 'TimeZone', 'UTC', ...
  'Format', 'yyyy-MM-dd''T''HH:mm:ss.SSSXXX')));
file = fopen(path, 'a');
assert(file >= 0);
fileCleanup = onCleanup(@() fclose(file));
fprintf(file, '%s\\n', jsonencode(record));
clear fileCleanup;
end
"""


def _matlab_number(value: int | float) -> str:
    return format(value, ".17g")


def generate_mtex_script(
    recipe: SphericalIntensityRecipe,
    expected_node_count: int,
    axial_available: bool,
) -> str:
    """Return one deterministic MATLAB script for a staged spherical bundle."""
    if not isinstance(recipe, SphericalIntensityRecipe):
        raise TypeError("recipe must be a SphericalIntensityRecipe")
    if type(expected_node_count) is not int or expected_node_count <= 0:
        raise ValueError("expected_node_count must be a positive integer")
    if type(axial_available) is not bool:
        raise TypeError("axial_available must be a boolean")
    if recipe.rng_generator != "twister":
        raise ValueError("recipe rng_generator must be twister")

    axial_block = (
        _AXIAL_BLOCK.format(axial_columns=_AXIAL_COLUMNS)
        if axial_available
        else ""
    )
    axial_figure_block = _AXIAL_FIGURE_BLOCK if axial_available else ""
    axial_triangulation_block = (
        _AXIAL_TRIANGULATION_BLOCK if axial_available else ""
    )
    axial_node_evaluation_block = (
        _AXIAL_NODE_EVALUATION_BLOCK if axial_available else ""
    )
    axial_result_path = (
        ", ...\n  'figures/directional-vs-axial.png'" if axial_available else ""
    )
    script = _TEMPLATE.format(
        expected_node_count=expected_node_count,
        point_count=recipe.profile.point_count,
        sample_resolution=_matlab_number(recipe.profile.sampling_resolution_deg),
        display_resolution=_matlab_number(recipe.display_resolution_deg),
        node_tolerance=_matlab_number(recipe.tolerances.mtex_node_normalized_max),
        rng_seed=recipe.rng_seed,
        rng_generator=recipe.rng_generator,
        profile_name=recipe.profile.name,
        axial_boolean="true" if axial_available else "false",
        directional_columns=_DIRECTIONAL_COLUMNS,
        axial_block=axial_block,
        axial_triangulation_block=axial_triangulation_block,
        axial_node_evaluation_block=axial_node_evaluation_block,
        axial_figure_block=axial_figure_block,
        axial_result_path=axial_result_path,
    )
    if "\r" in script or not script.endswith("\n"):
        raise AssertionError("generated MTEX script must use LF and end with newline")
    return script


__all__ = ["generate_mtex_script"]
