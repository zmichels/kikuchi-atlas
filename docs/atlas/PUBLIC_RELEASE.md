# Kikuchi Atlas public-release contract

## Status

Local pre-publication build only. No hosting account, public URL, DOI, domain,
or release license is assumed or created by this repository.

## Deliverables

`scripts/build_public_atlas.py --stage-archive` emits:

- `dist/atlas-public/site/` — a self-contained static browsing gallery;
- `dist/atlas-public/site/release-inventory.html` — a human-readable release
  inventory linked from every page;
- `dist/atlas-public/release-inventory.json` — machine-readable product,
  web-asset, archive-asset, SHA-256, recipe, and claim-boundary metadata; and
- `dist/atlas-public/archive/` — selected original media, previews,
  provenance records, tracked registries, recipes, checksums, and release
  notes suitable for a separately reviewed archival upload.

Tracked pre-publication metadata lives alongside the Atlas source:

- `CITATION.cff` and `.zenodo.json` describe the eventual code release;
- `RELEASE_METADATA.yml` records the still-unresolved public identity, URL,
  DOI, and project-license choices; and
- `STRUCTURAL_SOURCE_AUDIT.json` plus `STRUCTURAL_SOURCE_ATTRIBUTION.md`
  enumerate the exact source records, terms, checksums, and citations for all
  Atlas phases.

The gallery permits only PNG, SVG, JPEG, and MP4 assets at or below 25 MiB.
STL geometry and other heavier materials remain in the archive path rather
than being made implicit web-host dependencies. Canonical kinematical master
and relief-field exports are selected into the archive when their bundle has
them; redundant run intermediates stay recipe-reconstructible.

## Release gates

Before a public deployment or DOI release:

1. Rebuild the local Atlas and public package from a clean checkout.
2. Confirm that every public HTML file has no `local/` or workstation path.
3. Review the selected archive payload, checksums, structural-source terms,
   authorship, citation, and license terms.
4. Publish the static `site/` tree to the chosen host, then record its public
   URL in the next release metadata.
5. Publish the separately reviewed archive package, record its DOI, and add
   stable download links to a future public release registry.

## Claim boundary

The Atlas gallery contains modeled visualizations and printable geometry. It
does not claim to host acquired EBSD patterns, camera-calibrated detector
simulations, or a dictionary-indexing dataset unless a later release is
explicitly documented and validated as such.
