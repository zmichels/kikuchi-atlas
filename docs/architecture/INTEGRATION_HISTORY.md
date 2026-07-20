# Integration history and worktree boundary

## 2026-07-19 local integration release

Commit `1a5ab9d` joins two independent implementation lineages:

- `codex/dynamical-master-rotation-proof`: dynamical-master rotation,
  crystallographic habit, intensity-relief, and reflector-ridge globe work.
- `codex/spherical-intensity-implementation`: kinematical masters,
  direct-reflector phase art, tattoo/vector products, retained near-depth
  fields, and their active rotations.

The merge retains both parents, their source trees, their tests, and their
local bundle references. The current working tree is the connected engine
surface; historical branches remain readable provenance, not competing
products.

## Historical work-item collision

Both lineages independently allocated `KIKU-F004` through `KIKU-F006` and
`KIKU-T025` through `KIKU-T036`; both also used `KIKU-T038`. A flat tracker
cannot truthfully contain duplicate identifiers. The phase-general tracker
lineage is the canonical active ledger because it contains the continuing
phase-art and rotation roadmap. The dynamical/habit/relief work records remain
unchanged and reachable in the first parent of `1a5ab9d`, while their code,
tests, recipes, and cataloged products are retained in this stable branch.

This is a namespace resolution, not a deletion or a scientific supersession.
New work must allocate fresh identifiers from the canonical `docs/work/`
ledger.

## Workbench held outside the release

`codex/spherical-intensity-workbench` at `3a6a587` preserves the unaccepted
MTEX runner, high-resolution S2-density examples, and related tests as one
coherent WIP snapshot. It was intentionally excluded from the stable merge.
Promote it only through a dedicated feature branch after its runtime contract,
MTEX recovery behavior, and scientific acceptance evidence are reviewed.

## Local product-store migration

The source tree is merged by Git. Generated media remain in the ignored
`local/` store and are indexed by `docs/products/ARTIFACT_CATALOG.yml`.
The primary checkout is now on `master`, and the selected published media have
been moved into its `local/` tree. `scripts/product_status.py --require-present`
verifies the nine catalog anchors there. The old fully merged spherical
checkout was removed; its MTEX scratch data remains only with the explicitly
experimental workbench. No worktree-relative symlinks are used.
