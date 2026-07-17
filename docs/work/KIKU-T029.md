---
id: KIKU-T029
type: task
title: Build atomic habit bundles through the CLI
status: ready
parent: KIKU-F004
created: '2026-07-17'
priority: P1
tags:
- workflow
- cli
- artifacts
evidence:
- ../superpowers/plans/2026-07-17-crystal-habit-mesh-generator.md
---

# KIKU-T029: Build atomic habit bundles through the CLI

## Description

Orchestrate recipe, crystallography, solver, mesh, preview, validation, inventory,
and hashes into one atomic content-addressed bundle exposed by `habit build`.

## Acceptance Criteria

- [ ] Identical recipe/CIF inputs produce identical bundle IDs and file hashes in separate output roots.
- [ ] The CLI publishes a complete four-file quartz bundle or reports one concise failure without a traceback.
- [ ] The canonical STL has a maximum axis-aligned dimension of `60.0 mm` within `1e-8 mm`.
