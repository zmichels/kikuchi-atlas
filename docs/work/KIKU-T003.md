---
id: KIKU-T003
type: task
title: Validate Forsterite and Isolate ebsdsim
status: ready
parent: KIKU-F001
created: 2026-07-12
priority: P0
tags: [forsterite, ebsdsim, gpu]
---

# KIKU-T003: Validate Forsterite and Isolate ebsdsim

## Description

Track and validate the COD 9000319 structure, isolate the ebsdsim boundary,
and expose environment diagnostics without backend substitution.

## Acceptance Criteria

- [ ] `tests/adapters/test_forsterite_source.py` verifies the tracked source and catalog evidence.
- [ ] Adapter tests preserve both master-pattern hemispheres and simulation metadata.
- [ ] The GPU smoke result and `kikuchi-lab doctor --json` evidence are linked here.
