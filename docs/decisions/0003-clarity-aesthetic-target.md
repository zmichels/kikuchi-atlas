# ADR 0003: Preserve Realism While Adding a Clarity-Forward Gallery Target

- Status: Accepted
- Date: 2026-07-13
- Work item: [KIKU-T010](../work/KIKU-T010.md)
- Reference catalog:
  [aesthetic-clarity.yml](../../reference/catalog/aesthetic-clarity.yml)

## Context

The proof-grade forsterite run demonstrates convincing dynamical geometry, but
its `scientific-clean` proof processing amplifies too much mid- and
high-frequency texture. The user supplied four image references and one
spherical STL that clarify a second desired aesthetic: bright continuous bands,
legible zone-axis nodes, and crisp large-scale organization without replacing
the physically derived band intensities with a geometric drawing.

The references have unknown acquisition, simulation, resampling, processing,
source, and licensing histories. They therefore cannot serve as quantitative
truth or tracked redistribution assets. Their local paths, hashes, dimensions,
observed traits, and descriptive diagnostic snapshots are cataloged without
copying them into the repository.

## Decision

Milestone one retains two deliberately related outputs from one immutable final
detector projection:

1. `scientific-clean` remains the realism anchor. It preserves smooth
   dynamical intensity structure, band pairing, physically derived asymmetry,
   and acquisition-like tonal continuity with restrained enhancement.
2. `gallery-crisp` becomes the clarity-forward interpretation. It may increase
   separation between broad bands and their background, emphasize stable
   zone-axis nodes, and improve band-trace readability, but every transform
   remains explicit and it is never labeled as a quantitative raw simulation.

The gallery treatment should achieve clarity primarily through scale
separation:

- suppress proof-grade speckle and unstable pixel-scale texture before adding
  detail;
- retain broad light/dark band pairing and smooth band interiors;
- enhance coherent ridges and crossings at scales supported by the master
  pattern rather than outlining every local gradient;
- allow restrained node emphasis or bloom without clipping nodes into flat
  white discs;
- preserve the orientation composition and the unchanged scientific source;
- avoid synthetic line overlays, Hough-like band traces, or hidden geometry
  unless emitted later as a separately named diagrammatic product.

The proof references suggest that apparent crispness does not require dominant
pixel-scale energy. After independent robust display normalization, the three
detector-like image references have high-frequency energy near `0.003` to
`0.024`, while the current proof `scientific-clean` `[011]` candidate is about
`0.030` with unusually large mid-frequency energy (`0.244`). These values are
soft diagnostic evidence only: resolution, compression, and provenance differ.
They motivate reducing indiscriminate texture amplification, not optimizing to
reference numbers.

The circular map and STL inform future map/print products. They do not change
the planar final-pattern acceptance contract. The STL is a valid 57,800-face
spherical shell with no degenerate triangles and modest relief relative to its
approximately 150-unit diameter; its usefulness is geometric continuity and
print readability, not a relief-height recipe for forsterite.

## Acceptance implications

Task 10 must produce a small, explicit comparison ledger for the selected
orientation containing raw, acquisition-corrected, scientific-clean, and
gallery-crisp metrics plus stage images. Human review should compare the
gallery result against the cataloged traits at both fit-to-window and 100%,
while checking that:

- the scientific-clean product remains recognizably dynamical and smoother;
- gallery clarity comes from coherent structures rather than gritty texture;
- bright nodes retain internal tonal shape;
- no conspicuous halos or artificial single-line band outlines appear;
- both outputs reference the same projection and orientation selection;
- the reference files are never presented as calibrated targets or bundled for
  redistribution.

## Consequences

- The new references refine final processing but do not reopen the selected
  simulation/projection architecture.
- Proof-grade processing remains evidence of what to improve, not the final
  aesthetic.
- A future diagrammatic or spherical-map renderer remains a separate product
  with its own scientific labeling and promotion gate.
- Unknown source/license status prevents copying the supplied reference files
  into tracked repository assets.

