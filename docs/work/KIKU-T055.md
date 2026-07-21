---
id: KIKU-T055
type: task
title: Demonstrate Ice Ih coarse-to-refined synthetic recovery
status: active
parent: KIKU-F013
created: 2026-07-20
priority: P0
tags: [ice-ih, dictionary, validation, refinement]
links:
  - ../dictionaries/ice-ih-flagship-design.md
evidence:
  - ../../tests/scientific/
  - ../../scripts/run_ice_ih_synthetic_recovery.py
  - ../../tests/unit/test_ice_ih_dictionary.py
---

# KIKU-T055: Demonstrate Ice Ih coarse-to-refined synthetic recovery

## Description

Use held-out synthetic orientations to prove the actual user-facing path:
candidate ranking first, then full-master local refinement. Record score and
angular diagnostics without conflating the result with acquired EBSD accuracy.

## Acceptance Criteria

- [x] At least one held-out orientation is not an entry in the coarse cache.
- [x] Coarse retrieval returns a documented nearby candidate under the named
  cosine-score preprocessing.
- [x] Local refinement on the full master improves the angular diagnostic.
- [ ] The validation output and nonclaims travel with the package.

## Progress Evidence

The versioned recovery proof uses a non-cache 3.54-degree rotation composed
from the cache entry nearest identity. Its top coarse candidate has a 2.30
degree angular diagnostic; a 1,331-entry, 5-degree-wide local full-master grid
improves that to 0.46 degrees. The proof bundle is checksum-bearing and linked
to the exact dictionary identity. The remaining task is to embed this proof in
the next immutable dictionary version rather than leave it as a companion
bundle.
