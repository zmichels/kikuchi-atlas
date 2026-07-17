function export_mtex_habit_reference(requestPath, outputPath)
%EXPORT_MTEX_HABIT_REFERENCE Export a plain polygon ledger from MTEX 6.1.1.

requestPath = char(java.io.File(requestPath).getCanonicalPath());
outputPath = char(java.io.File(outputPath).getCanonicalPath());
request = jsondecode(fileread(requestPath));
mtexRoot = getenv('KIKUCHI_MTEX_ROOT');
assert(isfolder(mtexRoot), 'KIKUCHI_MTEX_ROOT must name MTEX 6.1.1');
oldFolder = pwd;
restoreFolder = onCleanup(@() cd(oldFolder)); %#ok<NASGU>
cd(mtexRoot);
addpath(mtexRoot);
startup_mtex('noMenu');
mtexVersion = erase(getMTEXpref('version'), 'mtex-');
assert(strcmp(mtexVersion, request.mtex_version));

requestRoot = fileparts(requestPath);
cifPath = char(java.io.File(requestRoot, request.cif).getCanonicalPath());
cs = loadCIF(cifPath);
familyNormals = cell(numel(request.families), 1);
for k = 1:numel(request.families)
  item = request.families(k);
  values = num2cell(double(item.indices));
  familyNormals{k} = item.normal_multiplier * Miller(values{:}, cs);
end
N = [familyNormals{:}];
cS = crystalShape(N);
expanded = unique(vector3d(N.symmetrise), 'stable');

faces = struct('vertex_indices', {}, 'normal', {}, 'family_label', {});
for k = 1:size(cS.F, 1)
  ids = cS.F(k, ~isnan(cS.F(k, :)));
  if isempty(ids)
    continue;
  end
  faces(end + 1).vertex_indices = int32(ids - 1); %#ok<AGROW>
  faces(end).normal = expanded(k).xyz;
  faces(end).family_label = matchFamilyLabel(expanded(k), request.families, cs);
end

ledger.schema = 'kikuchi.mtex-habit-reference/v1';
ledger.mtex.version = mtexVersion;
ledger.frame = 'X||a*, Y||cross(c,a*), Z||c';
ledger.request_sha256 = sha256File(requestPath);
ledger.cif_sha256 = sha256File(cifPath);
ledger.vertices = cS.V.xyz;
ledger.faces = faces;
mtexVolume = cS.volume;
if isfinite(mtexVolume)
  ledger.non_authoritative_crystal_shape_volume = mtexVolume;
  ledger.non_authoritative_volume_diagnostic = ...
    'crystalShape.volume is recorded for diagnostics only';
else
  ledger.non_authoritative_crystal_shape_volume = [];
  ledger.non_authoritative_volume_diagnostic = 'crystalShape.volume returned NaN';
end
assert(all(isfinite(ledger.vertices), 'all'), ...
  'Refusing to write non-finite MTEX vertices');
assert(all(arrayfun(@(face) all(isfinite(face.normal)), ledger.faces)), ...
  'Refusing to write non-finite MTEX face normals');
writeCanonicalJson(outputPath, ledger);
end


function label = matchFamilyLabel(normal, families, cs)
normalXYZ = normal.xyz;
normalXYZ = normalXYZ ./ norm(normalXYZ);
for k = 1:numel(families)
  item = families(k);
  values = num2cell(double(item.indices));
  candidate = Miller(values{:}, cs);
  symmetrized = unique(vector3d(candidate.symmetrise));
  candidateXYZ = symmetrized.xyz;
  candidateXYZ = candidateXYZ ./ vecnorm(candidateXYZ, 2, 2);
  if max(candidateXYZ * normalXYZ.') >= 1 - 1e-10
    label = item.label;
    return;
  end
end
error('Unable to assign visible MTEX face to an input family');
end


function digest = sha256File(path)
fileId = fopen(path, 'rb');
assert(fileId ~= -1, 'Unable to open file for SHA-256: %s', path);
restoreFile = onCleanup(@() fclose(fileId)); %#ok<NASGU>
bytes = fread(fileId, Inf, '*uint8');
engine = java.security.MessageDigest.getInstance('SHA-256');
engine.update(bytes);
digest = lower(reshape(dec2hex(typecast(engine.digest(), 'uint8'), 2).', 1, []));
end


function writeCanonicalJson(path, ledger)
payload = jsonencode(ledger);
fileId = fopen(path, 'wt');
assert(fileId ~= -1, 'Unable to open MTEX ledger for writing: %s', path);
restoreFile = onCleanup(@() fclose(fileId)); %#ok<NASGU>
written = fprintf(fileId, '%s\n', payload);
assert(written == strlength(payload) + 1, 'Incomplete MTEX ledger write');
end
