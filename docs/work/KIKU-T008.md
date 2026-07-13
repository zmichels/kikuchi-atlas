---
id: KIKU-T008
type: task
title: Render the Deterministic Proof Comparison
status: done
parent: KIKU-F001
created: 2026-07-12
priority: P1
tags: [proof, contact-sheet, comparison]
evidence:
  - ../../tests/integration/test_proof_workflow.py
  - ../../recipes/proof/forsterite-proof.yml
  - ../../src/kikuchi_lab/artifacts/contact_sheet.py
  - ../../local/runs/
---

# KIKU-T008: Render the Deterministic Proof Comparison

## Description

Render the fixed candidate set into matched acquisition/gallery comparisons
and a legible contact sheet for human orientation selection.

## Acceptance Criteria

- [x] Proof integration tests reproduce bundle identities and contact-sheet layout.
- [x] Each tile exposes orientation and processing identity without obscuring bands.
- [x] The proof bundle and contact sheet are linked here.

## Evidence

- Deterministic integration test:
  `uv run pytest tests/integration/test_proof_workflow.py -q` (2 passed).
- Focused proof/CLI suite:
  `uv run pytest tests/unit/test_proof_recipe.py tests/unit/test_cli.py tests/integration/test_proof_workflow.py -q`
  (8 passed).
- Full fast suite: `uv run pytest -q` (303 passed; 23 upstream deprecation
  warnings).
- Static checks: `uv run ruff check src tests` (clean).
- Validated proof master manifest:
  `../../local/master-patterns/forsterite-proof/COD-9000319-ebsdsim.bundle/COD-9000319-ebsdsim.manifest.json`.
- Current real proof bundle: `../../local/runs/proof-bb3c2766ff577427/`.
- Real contact sheet:
  `../../local/runs/proof-bb3c2766ff577427/contact-sheet.png`.
- The authoritative bundle was regenerated from clean revision
  `1a612f47cdd074a767cc9e2860533e69d80921cf` on branch
  `codex/exceptional-forsterite`; `provenance/execution.json` records
  `dirty=false` and the exact `kikuchi-lab proof` command.
- The previous clean proof is preserved at
  `../../local/runs/proof-034550efeb6bf89a.superseded-pre-master-contract-31a1956/`;
  it predates the explicit master-admissibility and complete contact-rendering
  identity contracts.
- The earlier bundle with the same scientific proof ID but dirty execution
  context is preserved at
  `../../local/runs/proof-034550efeb6bf89a.superseded-dirty-303e0d0/`.
- Superseded proof evidence is preserved at
  `../../local/runs/proof-e0fbf70a07913a27/` (before explicit proof-grade and
  processing labels) and `../../local/runs/proof-517f23a016733775/` (Unicode
  banner separators rendered poorly in the bundled bitmap font).
- Smoke-master comparison retained at `../../local/runs/proof-200408b6ef117f36/`;
  its 17 x 17 master was visibly faceted and was rejected as orientation-proof
  evidence without selecting or ranking any candidate.

The successful orientation-proof master is deliberately not a final-quality
master: 257 x 257 Lambert sampling (`halfw=128`), `dmin=0.08 nm`, one 20 keV
energy bin, rank 8, and 262,144 requested/minimum Monte Carlo trajectories. The
validated upstream artifact reports convergence after 786,432 trajectories.
Generation took 532.77 s internally (533.07 s wall time); the 12-candidate proof
authoritative clean render took 1.30 s internally. Raw candidate products are
360 x 480 float32 and processed products are 180 x 240 float32. The paired,
labeled contact sheet is 1484 x 1026 uint8 and the proof bundle contains 92
inventoried evidence files (21 MB locally).

The current recipe declares and the workflow verifies, before projection, the
exact forsterite phase/formula, space group 62 Pnma setting, transformed lattice
within absolute tolerance, COD source identifier/checksum/source ID, requested
and resolved simulation controls, backend and evidence classifications, product
shape/projection/hemisphere order, and generator identity. The run identity,
manifest, and visible contact-sheet banner
all state `quality_grade=proof`, `intended_use=orientation-comparison`, and
`not_final_quality=true`, with the `dmin`, one-bin energy integration, and rank
limitations encoded machine-readably. Every tile names the processed variant
as `scientific-clean [b8b420e0]`, and the banner repeats its full recipe ID in
metadata. Preview display mapping is explicitly per panel and per candidate at
the 0.5th/99.5th percentiles; each black/white point is retained, and the
contract disallows absolute-intensity comparison of the previews.

The bundle also records exact CLI arguments, software versions, the Apple M2
Metal doctor report, git branch/revision/dirty state, canonical source path and
checksum, and the originating master bundle, manifest locator, and checksum.
Local locators and execution context are evidence excluded from scientific run
identity. The versioned contact-sheet contract includes columns, panel/card
dimensions, gutters, padding, banner/footer sizing, colors, exact text
templates, label policy, renderer version, Pillow version, font name/sizes, and
a glyph-atlas hash. Changing columns, font identity, layout, quality, intended
use, processing recipe, or the admitted master contract changes the proof
identity.

All 12 candidates carry the same advisory `clipping_fraction` warning at 0.02,
caused by the explicit 1st/99th percentile normalization before CLAHE. This is
preserved as comparable evidence rather than suppressed. The run state remains
`awaiting-human-selection`; this task creates no selection, winner, score, or
ranking.

## GPU launch observations

- The original `chunk_size=256` proof recipe failed immediately because
  ebsdsim 0.1.8 requested 1,281,424 one-dimensional dispatch groups, beyond
  WebGPU's 65,535 limit. `chunk_size=8` is the validated Apple M2 Metal bound.
- A final-intent control set (`dmin=0.05 nm`, 1 keV bins, rank 20) remained in
  active Metal work for 1,174.74 s without reaching a checkpoint. Observed GPU
  device utilization was 99%, renderer/tiler utilization 73%, recovery count
  zero, and peak process RSS approximately 596 MB. It was intentionally stopped;
  transactional staging was cleaned and no completed artifact was published.
- These observations are diagnostics for later performance and final-master
  planning, not a completed proof artifact and not evidence that the
  proof-grade master meets final scientific-quality requirements.
