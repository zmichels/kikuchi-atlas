---
id: KIKU-T055
type: task
title: Demonstrate Ice Ih coarse-to-refined synthetic recovery
status: done
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
- [x] The validation output and nonclaims travel with the package.

## Progress Evidence

`ice-ih-spherical-candidate-v0.1.2` embeds the non-cache 3.54-degree rotation,
its observed spherical signal, expected coarse result, and the local
full-master diagnostics. The top coarse candidate has a 2.30-degree angular
diagnostic; a 1,331-entry, 5-degree-wide local grid improves that to 0.46
degrees. The independent verifier recomputes both ranking and refinement from
package bytes while retaining the explicit non-acquisition claim boundary.
