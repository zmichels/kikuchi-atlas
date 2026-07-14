---
id: KIKU-T024
type: task
title: Deliver forsterite spherical intensity proof
status: ready
parent: KIKU-F003
created: 2026-07-13
priority: P1
tags: [workflow, cli, acceptance, figures]
evidence:
  - ../superpowers/plans/2026-07-13-spherical-intensity-and-mtex-density-bridge.md
---

# KIKU-T024: Deliver forsterite spherical intensity proof

## Description

Expose the bounded workflow and CLI, run smoke before acceptance, and present
the exact-node, 3D sphere, density, channel, and axial comparison evidence.

## Acceptance Criteria

- [ ] The workflow consumes the completed `KIKU-F002` contract without changing existing products or schemas.
- [ ] Smoke passes before one `128` acceptance run; no `256` or `1024` run starts automatically.
- [ ] Numeric evidence and five fixed-view figures are reviewed before task and feature closure.
