---
id: KIKU-T087
type: task
title: Publish and verify the UMN Drive and Sites mirror
status: done
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
  - ../atlas/GOOGLE_MIRROR.yml
  - ../acceptance/atlas-consolidation-and-google-mirror.md
---

# KIKU-T087: Publish and verify the UMN Drive and Sites mirror

## Description

Mirror canonical full-resolution product packages through `zmichels@umn.edu`, publish the Google Site after action-time confirmation, and verify logged-out access before legacy cleanup.

## Acceptance Criteria

- [x] The verified account and remaining quota pass the 10 GiB headroom gate.
- [x] Every phase and product folder identity is uploaded and hierarchy-reconciled; the user-approved waiver and absence of per-package round-trip hash claims are explicit.
- [x] Drive and Site public-access changes occurred only after action-time user confirmation.
- [x] Logged-out Site navigation and representative media downloads pass.
- [x] Post-cleanup local and public rebuilds prove no legacy fallback.

## Completion Evidence

The schema-3 mirror ledger and final acceptance record identify the exact
account, quota, 138 public Drive identities, 14 public Site pages, seven
bounded representative file checks, upload-only waiver, cleanup, and
post-cleanup builds. No unperformed Drive package round-trip is claimed.
