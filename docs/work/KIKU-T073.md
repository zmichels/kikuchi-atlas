---
id: KIKU-T073
type: task
title: Build the Ice Ih virtual-camera transfer evidence bundle
status: done
parent: KIKU-F026
created: 2026-07-23
priority: P1
tags: [ice-ih, detector-profiles, partial-s2, synthetic-recovery, visualization]
links:
  - ../acceptance/ice-ih-virtual-camera-transfer.md
evidence:
  - ../../tests/unit/test_detector_profiles.py
  - ../../tests/unit/test_ice_ih_virtual_camera_transfer.py
---

# KIKU-T073: Build the Ice Ih virtual-camera transfer evidence bundle

## Description

Introduce reusable named virtual camera profiles, run the full native detector
proof across two separated Ice orientations, and publish all detector fields,
partial-S2 signals, metadata, checksums, and the visual review sheet locally.

## Acceptance Criteria

- [x] Profile identity and detector geometry validation are unit tested.
- [x] Target selection deterministically includes identity and a separated
  cache orientation.
- [x] The runner fails loudly unless every declared profile returns both known
  targets first.

## Completion Evidence

The full native-resolution runner completes six deterministic detector
recoveries in one bundle. Its evidence sheet distinguishes raw detector fields
from the profile-specific sample-frame S2 support that each match actually
uses.
