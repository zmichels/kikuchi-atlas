# Decision-State Diagnostics

- Status: Incubating
- Boundary: inspectable reasoning support, not automated scientific authority

## Motivation

Scientific runs accumulate alternatives, diagnostics, rejections, selections,
supersessions, and promotion gates. Richer linked state could make that history
queryable: what changed, which evidence moved a decision, what remains
unresolved, and which later ideas depend on it. Decision-PGA-inspired thinking
is useful here as a design prompt for trajectories and state relationships,
not as an implemented method or correctness claim.

## Current evidence

- The repository already separates architecture ADRs, machine-readable run
  decisions, and incubator records
  ([approved design](../superpowers/specs/2026-07-12-kikuchi-companion-design.md)).
- Artifact manifests retain versioned identities, diagnostic records, warnings,
  scientific/gallery lineages, and declared comparison exclusions
  ([ADR 0001](../decisions/0001-artifact-identity-and-bundle-layout.md)).
- Orientation selection uses immutable proof-scoped records, explicit external
  verification, serialized supersession, and a unique current leaf
  ([KIKU-T009](../work/KIKU-T009.md)).
- Current ledgers are durable but do not yet expose a shared decision graph,
  state-vector schema, movement diagnostic, or cross-run query model.

## Dependencies

- A minimal vocabulary for proposal, experiment, observation, decision,
  rejection, supersession, dependency, and promotion.
- Stable links to content identities and evidence without duplicating or
  weakening source manifests.
- A privacy and portability policy for local paths, author notes, and
  machine-specific evidence.

## Unresolved questions

- Which states and transitions are genuinely useful beyond the current
  tracker, ADR, manifest, and selection records?
- Should diagnostics describe changes in parameters, outputs, human judgments,
  or all three through separate linked views?
- How can a ledger surface contradictory or stale evidence without pretending
  to compute the scientifically correct decision?

## Linked decisions and experiments

- [ADR 0001](../decisions/0001-artifact-identity-and-bundle-layout.md) provides
  the current content-addressed evidence and lineage foundations.
- [KIKU-T009](../work/KIKU-T009.md) is the concrete immutable decision and
  supersession experiment.
- [ADR 0003](../decisions/0003-clarity-aesthetic-target.md) demonstrates a
  durable human-aesthetic decision that remains distinct from quantitative
  truth.

## Promotion trigger

Promote when two retained run decisions require a cross-run question that the current ADR, manifest, tracker, and selection records cannot answer without manual reconstruction.

## Present non-goals

- Automatically choosing orientations, recipes, or aesthetic winners.
- Assigning statistical meaning to decision-PGA language without a defined
  state space and validation study.
- Replacing repo-native work tracking, ADRs, or artifact manifests.
- Making chat history an authoritative decision store.
