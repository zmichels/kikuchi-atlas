# Final branch review fix report

Date: 2026-07-18

## Important blocker resolution

1. Standalone globe provenance is now part of the existing six-file bundles.
   The ridge ledger carries tracked source/checksum, recovered catalog policy
   and package versions, 15 selected members with intrinsic and effective mesh
   evidence, and 15 rejected members with reasons. The intensity ledger and
   manifest carry master ID/checksum, tracked structure/setting, kinematical
   recipe, projection ledger, reflector evidence, disk sampling contract, and
   seam diagnostics. No upstream objects are serialized.
2. `ReflectorRecipe` now validates phase-neutral numeric domains with exact
   scalar types and preserves every policy value in recipe identity. The
   bounded Ice workflows separately enforce the recovered 0.03/0.22/2.0/0.08,
   tie-preserving, four-cohort policy.
3. Reflector-ridge recipe loading now rejects every geometry the workflow does
   not build: only the 80.0 mm, 3.0 mm outward, subdivision-7 icosphere is
   accepted. The generic intensity-globe geometry contract is unchanged.

## Acceptance artifacts

- Ridge: `reflector-ridge-globe-build-f07f822ff336b13e`
- Intensity: `ice-intensity-globe-build-9c2b6b2fdb845eea`
- The acceptance notes and `KIKU-F006` now describe the standalone provenance
  evidence and retain the pending user-preview and external-print gates.

## Validation

- `uv run pytest -q tests/unit/test_reflector_recipe.py tests/unit/test_reflector_contracts.py tests/unit/test_reflector_globe_recipe.py tests/integration/test_ice_reflector_catalog.py tests/adapters/test_ice_ih_kinematical.py` — 53 passed.
- `uv run pytest -q tests/unit/test_reflector_globe_bundle.py tests/integration/test_ice_reflector_globe.py tests/integration/test_ice_globe_workflows.py tests/scientific/test_ice_intensity_field.py` — 9 passed.
- `uv run pytest -q` — 685 passed, 1 skipped.
- Ruff passed for every touched Python file; `python3
  scripts/validate_work_items.py` validated all 43 work items; `git diff
  --check` passed.

## Remaining claim boundary

Automated mesh and provenance evidence is complete. User visual acceptance,
external slicer ingestion, and physical-print behavior remain explicitly
unclaimed.
