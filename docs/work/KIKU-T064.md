---
id: KIKU-T064
type: task
title: Reproject the checked Ice Ih master across the declared detector
status: done
parent: KIKU-F019
created: 2026-07-21
priority: P0
tags: [ice-ih, gnomonic, stereographic-master, reprojection, verification]
links:
  - ../acceptance/ice-ih-master-detector-congruence.md
evidence:
  - ../../src/kikuchi_lab/dictionary/detector_to_s2.py
  - ../../tests/unit/test_detector_to_s2_adapter.py
---

# KIKU-T064: Reproject the checked Ice Ih master across the declared detector

## Description

Create a bounded reprojection primitive that converts detector pixels to
sample-frame rays, pulls them into the master crystal frame using a declared
orientation, and bilinearly samples the raw upper/lower master in batches.

## Acceptance Criteria

- [x] Unit tests verify detector-sized finite output, orientation sensitivity,
  and invalid batch/rotation rejection.
- [x] The proof checks that the dictionary master is byte-identical to the
  source run master before using it.
- [x] The rendered figure preserves same-source and non-acquisition
  boundaries alongside its raw detector comparison.

## Completion Evidence

`reproject_stereographic_master_to_detector()` samples all detector pixels in
bounded row batches. The checked Ice Ih proof produces the local image and
data bundle without intensity fitting or detector preprocessing.
