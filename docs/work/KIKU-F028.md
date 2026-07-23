---
id: KIKU-F028
type: feature
title: Qualify the Ni 24 dB calibration Hough baseline for a Reference Pack
status: done
parent: KIKU-E001
children:
  - KIKU-T075
  - KIKU-T076
created: 2026-07-23
priority: P1
tags: [reference-pack, nickel, acquired-ebsd, hough, provenance]
links:
  - ../acceptance/ni-gain24db-reference-pack-intake.md
  - ../../recipes/reference-pack/ni-gain24db-calibration-hough-v0.1.yml
evidence:
  - ../../scripts/build_ni_gain24db_reference_baseline.py
  - ../acceptance/ni-gain24db-reference-pack-intake.md
---

# KIKU-F028: Qualify the Ni 24 dB calibration Hough baseline for a Reference Pack

## Description

Perform the first bounded acquired-data intake after the needs/gap review.
Establish whether the openly licensed Ni gain dataset can supply a
provenance-rich calibration baseline while retaining the boundary between a
source-bound reproduction and an independently validated public benchmark.

## Acceptance Criteria

- [x] Rights, raw-source inventory, detector/calibration metadata, and master
  provenance are inspected rather than inferred from a thumbnail or phase name.
- [x] A recipe pins source APIs, gain number, phase/master source, PC
  convention/value, preprocessing, reflector selection, and optional Hough
  dependency.
- [x] A local evidence bundle records checksums, runtime versions, numeric
  result, diagnostic overlay, and clear nonclaims.

## Completion Evidence

The ni_gain(number=10) and matching seven calibration patterns are CC BY 4.0
source inputs. The source-bound CPU Hough baseline indexes all seven
calibration patterns, with fit 0.26731613278388977 and confidence
0.7579495310783386. Gates 1–5 are passed; a public release remains pending
the user's v0.1 scope decision.
