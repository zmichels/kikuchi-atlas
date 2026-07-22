---
id: KIKU-T069
type: task
title: Publish and verify explicit detector observation packages
status: done
parent: KIKU-F024
created: 2026-07-22
priority: P1
tags: [observation, detector-to-s2, provenance, checksums]
links:
  - ../acceptance/ice-ih-observation-input-contract.md
evidence:
  - ../../src/kikuchi_lab/dictionary/observation.py
  - ../../tests/unit/test_detector_observation.py
---

# KIKU-T069: Publish and verify explicit detector observation packages

## Description

Implement the portable raw detector observation package with one deliberately
narrow preprocessing contract: explicit identity only. Verify package hashes,
array compatibility, coverage, and the absence of unrecorded processing.

## Acceptance Criteria

- [x] A package writes detector data, exact direction grid, partial-S2 arrays,
  manifest, README, and checksums atomically.
- [x] The verifier rejects checksum and dimensional incompatibility and
  confirms finite covered values.
- [x] Tests reject a hidden blur stage and an incorrectly shaped detector.

## Completion Evidence

Unit tests publish and independently verify a small portable package. The Ice
source fixture then publishes a 1,946-direction/308-covered observation
package with named TSL geometry and identity preprocessing.
