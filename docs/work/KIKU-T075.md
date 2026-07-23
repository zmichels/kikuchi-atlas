---
id: KIKU-T075
type: task
title: Audit Ni gain source rights, raw files, calibration metadata, and master provenance
status: done
parent: KIKU-F028
children: []
created: 2026-07-23
priority: P1
tags: [nickel, source-intake, zenodo, nordif, provenance]
links:
  - ../acceptance/ni-gain24db-reference-pack-intake.md
evidence:
  - ../../recipes/reference-pack/ni-gain24db-calibration-hough-v0.1.yml
  - ../acceptance/ni-gain24db-reference-pack-intake.md
---

# KIKU-T075: Audit Ni gain source rights, raw files, calibration metadata, and master provenance

## Description

Inspect the actual downloaded Ni source payload and upstream documentation to
establish what can be redistributed or referenced, which acquisition and
calibration fields persist, and which geometry/master values must be declared
externally.

## Acceptance Criteria

- [x] The selected Ni gain and calibration source exposes a clear CC BY 4.0
  license and durable upstream location.
- [x] The retained local source files include raw patterns, NORDIF settings,
  static backgrounds, and calibration images with hashes.
- [x] The audit distinguishes raw metadata from the PC and master details
  supplied by the cited upstream workflow.

## Completion Evidence

The selected dataset stores 26 source files locally; the final PC is
deliberately marked as an upstream workflow value rather than a raw NORDIF
header field.
