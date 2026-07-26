# Pyrope Atlas Parity Design

Date approved: 2026-07-25

## Goal

Promote one exact 298.15 K Mg3Al2Si3O12 pyrope structure into the Kikuchi
Atlas with the same nine registered product roles as calcite and
orthoenstatite. Existing phases and products remain present and unchanged.

## Scientific source boundary

The structural source is COD 9000435, Meagher's 1975 refinement of pyrope at
25 degrees C:

- formula: Mg3Al2Si3O12;
- space group: 230, `I a -3 d`;
- cubic cell: 11.456 angstrom;
- source retrieval SHA-256:
  `90c7d0b964653c5d1e32aa944a45430e760f29f3910ff8997a0a3524d4f55932`;
- four independent sites: Mg, Al, Si, and O;
- conventional-cell multiplicities: 24, 16, 24, and 96.

This is one pure Mg garnet endmember reference. It is not a proxy for all
garnets, natural pyrope solid solutions, pressure-dependent structures,
detector acquisition, indexing validation, or orientation-accuracy
calibration.

## Thermal-factor derivative

The original COD CIF remains byte-for-byte preserved. Its Al site reports
Uiso directly, while Mg, Si, and O report anisotropic Uij tensors and `?` in
the Uiso column. Following the existing zircon precedent, a second
simulation-ready CIF will be generated deterministically:

- Al retains the reported Uiso of 0.00507 square angstrom;
- Mg Ueq is `(0.00479 + 0.01536 + 0.01536) / 3`;
- Si Ueq is `(0.00253 + 0.00253 + 0.00578) / 3`;
- O Ueq is `(0.01050 + 0.00253 + 0.00485) / 3`;
- all coordinates, occupancies, cell values, and symmetry operations remain
  unchanged;
- the original and derivative SHA-256 values, formula, setting,
  multiplicities, and per-site values are verified by automated tests.

The source record will retain the COD scientific-community attribution-use
notice and the original article citation. It will not silently relabel that
source-specific notice.

## Product architecture

Pyrope reuses the established parity pipeline without new engine behavior:

1. Verified source record and deterministic simulation CIF.
2. Zero-master direct-reflector catalog and one bounded simulator parity
   smoke.
3. Four standard-width direct-reflector templates: standard, azimuthal 60,
   tilt plus 20, and oblique high.
4. A 144-frame, 1024 px, 12 fps direct x-axis rotation.
5. A 20 keV retained kinematical master and a near-depth treatment bundle.
6. A 144-frame, 1024 px, 12 fps retained-field x-axis rotation.
7. A validated reflector-ridge globe and a validated kinematical
   intensity-relief globe.

Only a pyrope-specific ridge eligibility threshold may be adjusted, and only
to preserve the existing four-cohort presentation contract. Energy,
d-spacing cutoff, geometry resolution, and product-role semantics remain
aligned with the current parity phases.

## Publication contract

Atlas records are added only after every media, preview, bundle, provenance,
and recipe path exists. Publication adds one phase and nine products:

- phase count changes from 11 to 12;
- product count changes from 113 to 122;
- structural-source audit count changes from 11 to 12;
- the existing nine CC0-labelled source records remain nine because the
  pyrope record preserves the COD attribution-use notice.

The intake table moves pyrope from candidate coverage to retained Atlas
coverage. A new `KIKU-T084` task records exact source, build, validation, and
acceptance evidence while `KIKU-F031` remains active for the remaining
requested minerals.

## Testing and acceptance

Implementation follows red-green TDD for:

- original/derivative source integrity and the anisotropic-to-isotropic
  policy;
- parity recipe availability;
- direct-rotation source mapping;
- Atlas phase, product, hero, and page coverage;
- release-metadata source inventory.

Acceptance additionally requires exact manifest byte/SHA-256 verification,
watertight and winding-consistent mesh validations, a fresh Atlas build,
tracker validation, focused regression tests, and `git diff --check`.
Manufacturing advisories from mesh validation remain visible and do not
become universal printability claims.
