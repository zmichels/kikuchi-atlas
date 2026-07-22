---
id: KIKU-F024
type: feature
title: Package observed Ice Ih detector inputs and an evidence dashboard
status: done
parent: KIKU-E001
children:
  - KIKU-T069
  - KIKU-T070
  - KIKU-T071
created: 2026-07-22
priority: P1
tags: [ice-ih, observation, preprocessing, detector, dictionary, dashboard]
links:
  - ../acceptance/ice-ih-observation-input-contract.md
  - ../acceptance/ice-ih-photometric-stress.md
evidence:
  - ../../src/kikuchi_lab/dictionary/observation.py
---

# KIKU-F024: Package observed Ice Ih detector inputs and an evidence dashboard

## Description

Build the input-side counterpart to the Ice Ih dictionary: a portable raw
detector observation package with named geometry and explicit preprocessing.
Use it to anchor transparent synthetic image-stress evidence and a browsable
local dashboard of the detector-to-dictionary pipeline.

## Acceptance Criteria

- [x] A portable package carries raw numeric detector values, detector
  geometry, explicit identity preprocessing, S2 directions, partial signal,
  coverage, manifest, and checksums.
- [x] The initial stress sheet declares every synthetic perturbation and never
  conflates it with a real preprocessing or detector-response model.
- [x] A local browsable dashboard links the visual diagnostics and
  machine-readable packages into one evidence ladder.

## Completion Evidence

The verified source-bound observation package has 308 covered directions. The
six-condition stress sheet preserves its named transforms and score records.
The generated dashboard makes all current major engine slices available from
one local opening page.
