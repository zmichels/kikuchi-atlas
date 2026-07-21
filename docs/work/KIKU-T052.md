---
id: KIKU-T052
type: task
title: Publish an approved Kikuchi Atlas static site and DOI archive
status: deferred
parent: KIKU-F012
created: 2026-07-20
priority: P2
tags: [atlas, hosting, zenodo, release]
links:
  - ../atlas/PUBLIC_RELEASE.md
evidence:
  - ../../dist/atlas-public/release-inventory.json
---

# KIKU-T052: Publish an approved Kikuchi Atlas static site and DOI archive

## Description

Publish the approved public gallery, then separately publish the archival
package only after its stable version, DOI, authorship, citation details, and
license terms have been reviewed.

## Acceptance Criteria

- [x] A reviewed public repository and static-host target are named.
- [x] Archive metadata, citation, structural-source terms, and release license
  are reviewed before upload.
- [x] The deployed gallery URL is recorded in tracked release metadata.
- [ ] The separately published archival DOI is recorded in tracked release
  metadata.
- [x] The public page links only to published, content-checked artifacts.

## Remaining gate

The archive has a reviewed stable version and DOI publication destination.

## Prepared Evidence

- `CITATION.cff`, `.zenodo.json`, and `docs/atlas/RELEASE_METADATA.yml` are
  aligned pre-publication metadata. The maintainer identity was confirmed from
  local Git configuration; code is MIT and project-owned media/geometry are
  CC BY 4.0.
- `docs/atlas/STRUCTURAL_SOURCE_AUDIT.json` records all nine exact source
  records: eight CC0 sources and the separately attributed muscovite source.
- Public source: `https://github.com/zmichels/kikuchi-atlas`.
- Public static gallery: `https://zmichels.github.io/kikuchi-atlas/`.
