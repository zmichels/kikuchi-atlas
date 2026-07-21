---
id: KIKU-T051
type: task
title: Build a self-contained public Atlas gallery and archival staging package
status: done
parent: KIKU-F012
created: 2026-07-20
priority: P1
tags: [atlas, static-site, archive, checksums]
links:
  - ../atlas/PUBLIC_RELEASE.md
evidence:
  - ../../scripts/build_public_atlas.py
  - ../../src/kikuchi_lab/atlas/publication.py
  - ../../tests/unit/test_atlas_publication.py
---

# KIKU-T051: Build a self-contained public Atlas gallery and archival staging package

## Description

Generate a static gallery that can be deployed without relying on ignored
workspace paths, while retaining a separate local staging package for original
media, print geometry, provenance, checksums, and release review.

## Acceptance Criteria

- [x] The public site copies only allowed browser-safe media and does not
  retain `local/` or absolute workstation URLs.
- [x] Every Atlas product is represented in a machine-readable inventory with
  recipe, web-asset, archive-asset, and claim-boundary information.
- [x] The optional archive staging path copies selected original media,
  provenance records, and canonical master/relief fields when present
  content-addressably and writes SHA-256 checksums.
- [x] Unit tests cover public link rewriting and the STL gallery/archive split.

## Completion Evidence

- `scripts/build_public_atlas.py --stage-archive` builds `site/`,
  `release-inventory.json`, and `archive/` under `dist/atlas-public/`.
- The complete current release has 156 web assets (about 165 MiB) and 266
  staged archive artifacts (about 813 MiB), including nine canonical
  kinematical masters and nine parity relief fields; no public gallery asset
  exceeds 25 MiB.
- `tests/unit/test_atlas_publication.py` proves the public HTML contains no
  `local/` links and keeps STL media out of the web bundle while retaining it
  in the archive staging area.
