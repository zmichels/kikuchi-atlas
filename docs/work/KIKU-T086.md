---
id: KIKU-T086
type: task
title: Refresh the 125-product GitHub Pages catalogue
status: done
parent: KIKU-F012
children: []
created: 2026-07-25
priority: P1
tags: [atlas, github-pages, publication]
links:
  - ../atlas/PUBLIC_RELEASE.md
  - ../atlas/ATLAS_MIGRATION.yml
evidence:
  - ../../scripts/build_public_atlas.py
  - ../../src/kikuchi_lab/atlas/publication.py
  - ../acceptance/atlas-consolidation-and-google-mirror.md
---

# KIKU-T086: Refresh the 125-product GitHub Pages catalogue

## Description

Publish the browser-safe 125-product Atlas through the existing release-driven Pages workflow while keeping authoritative heavyweight media outside the Pages payload.

## Acceptance Criteria

- [x] The public build contains exactly 12 phases and 125 product records.
- [x] Every public asset is browser-safe, no larger than 25 MiB, and free of local paths.
- [x] The release ZIP checksum matches the workflow pin.
- [x] The live Pages index, all phase pages, and the three new quartz products pass HTTP and browser checks.

## Completion Evidence

The link-complete draft.3 release, protected workflow run, deployment ID,
pinned ZIP hash, 12/125 live inventory, 212 asset hashes, and cookie-free
checks are recorded in the final acceptance record.
