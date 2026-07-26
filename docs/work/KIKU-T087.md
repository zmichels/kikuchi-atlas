---
id: KIKU-T087
type: task
title: Publish and verify the UMN Drive and Sites mirror
status: ready
parent: KIKU-F012
children: []
created: 2026-07-25
priority: P1
tags: [atlas, google-drive, google-sites, publication]
links:
  - ../atlas/CONSOLIDATION.yml
  - ../atlas/ATLAS_MIGRATION.yml
evidence:
  - ../atlas/ATLAS_MIGRATION.yml
---

# KIKU-T087: Publish and verify the UMN Drive and Sites mirror

## Description

Mirror canonical full-resolution product packages through `zmichels@umn.edu`, publish the Google Site after action-time confirmation, and verify logged-out access before legacy cleanup.

## Acceptance Criteria

- [ ] The verified account and remaining quota pass the 10 GiB headroom gate.
- [ ] Every phase and product package is uploaded and reconciled against canonical hashes.
- [ ] Drive and Site public-access changes occur only after action-time user confirmation.
- [ ] Logged-out Site navigation and representative media downloads pass.
- [ ] Post-cleanup local and public rebuilds prove no legacy fallback.
