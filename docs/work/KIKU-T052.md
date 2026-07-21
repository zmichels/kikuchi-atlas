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

Publish the already prepared gallery and archival package only after the user
chooses the public account/repository identity, hosting destination, version,
authorship, citation details, and license terms.

## Acceptance Criteria

- [ ] A reviewed public repository and static-host target are named.
- [x] Archive metadata, citation, structural-source terms, and release license
  are reviewed before upload.
- [ ] The deployed gallery URL and archival DOI are recorded in tracked release
  metadata.
- [ ] The public page links only to published, content-checked artifacts.

## Deferred Until

The user explicitly authorizes an external publication target and provides or
approves the required repository, account, and citation identity.

## Prepared Evidence

- `CITATION.cff`, `.zenodo.json`, and `docs/atlas/RELEASE_METADATA.yml` are
  aligned pre-publication metadata. The maintainer identity was confirmed from
  local Git configuration; code is MIT and project-owned media/geometry are
  CC BY 4.0.
- `docs/atlas/STRUCTURAL_SOURCE_AUDIT.json` records all nine exact source
  records: eight CC0 sources and the separately attributed muscovite source.
