# Task 6 Report: Source-agnostic globe mesh boundary

## Outcome

Added `kikuchi_lab.globe_mesh` as the source-neutral radial globe boundary.
It owns `GlobeGeometrySpec`, `ReliefGeometry`, `ReliefMeshValidation`,
`build_radial_geometry()`, and `validate_globe_mesh()`.  The existing relief
entry points remain compatibility adapters: `build_relief_geometry()` accepts
only 80.0 mm / 1.2 mm, and `validate_canonical_relief_mesh()` accepts only the
approved subdivision-7 topology with the same physical dimensions.

The forsterite workflow now constructs its geometry through the shared boundary,
then retains the canonical acceptance gate before any export.  It continues to
use the existing filenames, contracts, identity payloads, and exporter calls.

## Red evidence

Before this extraction, the only public construction path was
`build_relief_geometry()`, which explicitly rejected any dimensions other than
80.0 mm diameter and 1.2 mm maximum relief.  The new regression test preserves
that negative case by asserting that an 80.0 mm / 3.0 mm call still raises the
original canonical-geometry error.

## Green evidence

- `GlobeGeometrySpec(80.0, 3.0, 2)` with a subdivision-2 icosphere and all-one
  normalized values builds 43.0 mm radii and passes `validate_globe_mesh()`.
- `tests/scientific/test_globe_mesh.py` covers the generic 3 mm path and the
  legacy rejection path.
- `uv run pytest tests/scientific/test_globe_mesh.py -q` passed: 4 tests.
- `uv run pytest tests/scientific/relief/test_relief_mapping.py -q -m 'not slow'`
  passed: 28 tests, 1 intentionally deselected slow test.
- `uv run ruff check src/kikuchi_lab/globe_mesh.py src/kikuchi_lab/relief tests/scientific/test_globe_mesh.py`
  passed after formatting.

## Compatibility evidence

- `build_relief_geometry()` still checks the exact 80.0 mm / 1.2 mm contract.
- `validate_canonical_relief_mesh()` explicitly supplies
  `GlobeGeometrySpec(80.0, 1.2, 7)` after proving the approved topology.
- Canonical mesh fingerprints retain their existing `relief-topology-sha256-`
  and `relief-geometry-sha256-` payload format because the fingerprint payload
  and serialization contract were retained unchanged.
- The workflow remains guarded by `_require_canonical_publication_recipe()` and
  still calls the canonical validator before STL, field NPZ, preview, identity,
  and manifest production.

## Full-suite note

The repository uses `tests/integration/test_relief_globe_workflow.py` rather
than the brief's stale `tests/integration/test_relief_workflow.py` path.
The broader relief command was started with the actual integration path; this
environment returned progress output without a final pytest summary for the
long subdivision-7 integration stage, so it is not claimed as a completed
green check here.

Controller follow-up validation after commit:

```text
uv run pytest tests/scientific/test_globe_mesh.py tests/scientific/relief tests/integration/test_relief_globe_workflow.py -q
```

Result: `90 passed in 240.56s (0:04:00)`.

## Self-review

- Generic specs require positive finite dimensions and a nonnegative integer
  subdivision count; geometry and topology subdivision counts must agree.
- The generic validator rejects topology substitution, malformed arrays,
  non-radial vertices, values outside [0, 1], configured-range violations,
  non-manifold/degenerate geometry, and non-positive radial projection.
- The canonical wrapper remains stricter than the generic path and therefore
  does not admit the new 3 mm geometry into the forsterite publication route.

## Commit

`87c64c1 refactor: share validated globe mesh boundary`

## Review fix: remove dead relief validation duplicate

Removed the unreachable `_legacy_validate_relief_mesh()` implementation from
`src/kikuchi_lab/relief/mesh.py`, along with its private duplicate validation
helpers, fingerprint helpers, and validation-only tolerance constants. The
remaining public `validate_relief_mesh()` and
`validate_canonical_relief_mesh()` adapters continue to use
`kikuchi_lab.globe_mesh.validate_globe_mesh()`; `_edges()` remains because the
FDM-warning ledger still uses it.

Validation completed after the removal:

- `uv run pytest tests/scientific/test_globe_mesh.py tests/unit/relief/test_relief_mesh.py tests/scientific/relief/test_relief_mapping.py -q -m 'not slow'`
  - `87 passed, 2 deselected in 20.96s`
- `uv run ruff check src/kikuchi_lab/relief/mesh.py`
  - `All checks passed!`
- `git diff --check`
  - passed with no output

## Review fix: restore subdivision-7 strictness in the legacy geometry wrapper

`build_relief_geometry()` now rejects every topology other than subdivision 7
after its existing 80.0 mm / 1.2 mm physical-contract check. It delegates with
the explicit canonical `GlobeGeometrySpec(80.0, 1.2, 7)`. The generic
`build_radial_geometry()` path remains spec-driven and continues to accept the
subdivision-2, 80.0 mm / 3.0 mm globe.

Regression evidence:

- A subdivision-2 legacy wrapper call at 80.0 mm / 1.2 mm raises the canonical
  `approved subdivision-7 topology` error.
- The generic `GlobeGeometrySpec(80.0, 3.0, 2)` path still builds 43.0 mm radii
  and passes `validate_globe_mesh()`.
- Legacy mapping tests that exercise successful construction and invalid value
  inputs now use the canonical subdivision-7 fixture.

Validation completed:

- `uv run pytest tests/scientific/test_globe_mesh.py tests/scientific/relief/test_relief_mapping.py -q -m 'not slow'`
  - `33 passed, 1 deselected in 2.39s`
- `uv run ruff check src/kikuchi_lab/relief/mapping.py tests/scientific/test_globe_mesh.py tests/scientific/relief/test_relief_mapping.py`
  - `All checks passed!`
- `git diff --check`
  - passed with no output
