# Ice Ih Primary Tattoo Review

- Work items: [KIKU-T028](../work/KIKU-T028.md), [KIKU-T029](../work/KIKU-T029.md)
- Boundary contract: [design](../superpowers/specs/2026-07-16-ice-tattoo-hemisphere-boundary-design.md), [implementation plan](../superpowers/plans/2026-07-16-ice-tattoo-hemisphere-boundary.md)
- Production state: machine-verified bounded primary candidate retained locally
- `presentation_status: awaiting_user_review`
- Scientific claim: `presentation_only`

## Scope and policy provenance

This candidate derives 11 center traces from the retained Ice Ih art-band
catalog after applying the approved active crystal-to-sample Bunge ZXZ
orientation `(17, 31, 43)` degrees. The tracked catalog eligibility floor is
exactly `0.08`; the tattoo selector retains the independent paths at the
unchanged hard `4.0 degree` axial-nonredundancy threshold.

The `0.08` floor is a science-art selection policy, not altered
crystallographic evidence. It is recorded in the tracked catalog recipe, the
catalog snapshot, and the catalog ledger. The source structure hash, HKLs,
normals, Bragg half widths, structure-factor magnitudes, and normalized weights
remain derived from the bounded Ice simulation.

The enclosing circle is separately identified as the noncrystallographic
projection primitive `stereographic_hemisphere_boundary`. It is not a twelfth
reflector, is excluded from catalog and selection counts, and carries no
crystallographic claim.

This science-art is not medical guidance or a skin-approved stencil and
requires qualified tattoo-artist review before any use on skin.

## Retained production invocations

The catalog command and first tattoo command below are the historical
invocations that produced the retained catalog and superseded rimless audit
bundle. Both output roots were absent before those commands, and each completed
once without deletion or retry.

```text
uv run kikuchi-lab build-ice-art-catalog --recipe recipes/art/ice-ih-band-catalog.yml --output local/ice-art-catalog-primary-proof
uv run kikuchi-lab render-ice-tattoo --catalog local/ice-art-catalog-primary-proof/ice-art-catalog-run-57478bf29894e175/art-band-catalog.json --recipe recipes/art/ice-ih-tattoo.yml --output local/ice-tattoo-primary-proof --treatment primary
```

Before the bounded publication, `local/ice-tattoo-primary-proof` contained only
`ice-tattoo-run-d158193b08f3668e`. The retained catalog existence check passed,
then the following command was invoked exactly once. Atomic no-replace
publication added one new child and did not mutate the old bundle.

```text
test -f local/ice-art-catalog-primary-proof/ice-art-catalog-run-57478bf29894e175/art-band-catalog.json
uv run kikuchi-lab render-ice-tattoo --catalog local/ice-art-catalog-primary-proof/ice-art-catalog-run-57478bf29894e175/art-band-catalog.json --recipe recipes/art/ice-ih-tattoo.yml --output local/ice-tattoo-primary-proof --treatment primary
```

| Product | Run ID | Manifest SHA-256 | Retained bundle |
| --- | --- | --- | --- |
| catalog | `ice-art-catalog-run-57478bf29894e175` | `f220a20b7a48a3113ca25067b721c6d5f94d9266a839eb246dc007be15819aeb` | `local/ice-art-catalog-primary-proof/ice-art-catalog-run-57478bf29894e175` |
| bounded primary tattoo | `ice-tattoo-run-59c4eb958d5f2ab9` | `8d784f34fcc64a32867c596653f087773a6ac82492e23d98956049112afcda9d` | `local/ice-tattoo-primary-proof/ice-tattoo-run-59c4eb958d5f2ab9` |

## Catalog, selection, and geometry identities

| Field | Retained value |
| --- | --- |
| Source structure ID | `COD-1572233-O-sublattice` |
| Source structure SHA-256 | `4327a279e414a62f861d143e18570e9d741bbbb7d04dd2fb471c930988f95b81` |
| Catalog recipe ID | `recipe-3b4e8c4e8d5d58e2` |
| Catalog ID | `art-band-catalog-05f58424b717d5ad` |
| Catalog snapshot SHA-256 | `7093d39775ffe6a20cd4f508d8ec6dd27e1340cb5240ec1b0ef19430cfff24a2` |
| Members / tattoo eligible / eligible weight blocks | `30 / 15 / 6` |
| Eligibility floor | `0.08` inclusive |
| Orientation ID | `orientation-fcc465bb0a3210c9` |
| Tattoo recipe ID | `tattoo-recipe-e972429e0106a476` |
| Selection ID | `tattoo-selection-211db31bbe061d6d` |
| Geometry ID | `tattoo-geometry-55aa84c7c4d78a1b` |
| Boundary ID | `tattoo-boundary-da45c61d325de3be` |
| Stroke-gap diagnostic ID | `tattoo-stroke-gap-diagnostic-d038b54b183e38c0` |

The exact unchanged ordered catalog-member contract is:

1. `art-band-member-239b7cb5e485d442`
2. `art-band-member-d38532aafcf1ed7f`
3. `art-band-member-3cb4167967631dcc`
4. `art-band-member-0a414c19f6ab8845`
5. `art-band-member-b4647bcd2cbca9f6`
6. `art-band-member-b67c65e3bc542c16`
7. `art-band-member-263af8004ec3e279`
8. `art-band-member-ef3609aba836233b`
9. `art-band-member-4fdb2612d72a02c1`
10. `art-band-member-2413565c4ba2c58d`
11. `art-band-member-c38e4b2859f9646d`

The geometry is an exact `145 x 145 mm` square with projection
`upper_specimen_stereographic_center_trace`. It contains the same 11 unique
paths in the ordered `4 dominant / 4 secondary / 3 fine` allocation. The
ordered widths remain `4.8, 4.2, 3.6, 3.1, 2.5, 2.2, 1.9, 1.6, 1.2, 1.0,
0.8 mm`.

The separate boundary has exact outer diameter `132.0 mm`, stroke width
`2.2 mm`, center `(72.5, 72.5) mm`, black ink `#000000`, and a `6.5 mm`
outer clear margin on every side of the artboard. The SVG contains exactly 11
`path` children followed by one `circle` child. The diagnostic reports
`complete_hemisphere_boundary: passed` and `boundary_endpoint_contact: passed`.

The diagnostic retains hard minimums of `1.5 mm` for noncrossing edge gaps and
`2.0 mm` for unrelated endpoint clearance. All 55 pairs in this great-circle
network are true crystallographic crossings, so there are no noncrossing pairs
to which those two clearance measurements apply; the observed minima are
therefore `null`, not relaxed thresholds.

## Bounded primary inventory

All paths below are inside
`local/ice-tattoo-primary-proof/ice-tattoo-run-59c4eb958d5f2ab9`.

| Artifact | Exact dimensions or role | SHA-256 |
| --- | --- | --- |
| `art-band-catalog.json` | `12,473 bytes`; immutable selected-catalog snapshot | `2cb0eae81cc18d1db088bcf0c0a139c9769d4789a16b211e71d517ff490ab385` |
| `tattoo-recipe.json` | `935 bytes`; bounded recipe snapshot | `a14906754b544167dbb4aa0983c76b41fe1cdd68fcf328003a2b1edddc41876a` |
| `band-selection-ledger.json` | `200,594 bytes`; 11 selected paths with score/rejection provenance | `ca9e2f7d74c631ac5051810d46b25593d661a9a4640a7c5be7fb57c710aa4f60` |
| `path-geometry.json` | `145,146 bytes`; 11 paths plus separate boundary | `6b5c0493a9ad15e079f68badfe2fb93e4ca50e16a8814865279627e74f5fe610` |
| `stroke-gap-diagnostic.json` | `3,040 bytes`; validation status `passed` | `62800064f807d2383220af13e46ba83f0274fbb0436d73f487f5cbabefd2f7dd` |
| `ice-ih-tattoo-primary.svg` | `145 x 145 mm`, transparent canvas, 11 paths plus 1 circle | `448dad7842b97a0d1d91787afc6b0136398afe7bdf252c054a2c42997405bef3` |
| `ice-ih-tattoo-primary.pdf` | `145 x 145 mm`; `411.024 x 411.024 pt` MediaBox | `87ae5dcc8de11e06804f8e82a232261df80717e1fbe7c165d9d251482949a921` |
| `ice-ih-tattoo-mockup.png` | `1713 x 1713 px`, embedded `299.9994 dpi`, RGB | `db034ee627671753b579a14ee88f508b4cbe3f91846b2eb312dcfd89fb68883e` |
| `ice-ih-tattoo-stencil.png` | `1713 x 1713 px`, embedded `299.9994 dpi`, RGB | `69ed8a819fe6e2a6beaaa857d4d7f6ee1aa82299008aa954161e2b6245ef196a` |
| `tattoo-artist-review.txt` | required `136-byte` disclaimer | `691a5269ba346bc5c09f69f6a149ecf2a4d06d69e4a9ed8d06638698dbd5ebe4` |
| `manifest.json` | `2,103 bytes`; written last before promotion | `8d784f34fcc64a32867c596653f087773a6ac82492e23d98956049112afcda9d` |

## Superseded rimless audit evidence

The rimless `ice-tattoo-run-d158193b08f3668e` bundle is superseded as the
visual candidate but deliberately retained as immutable audit evidence. Its
complete file hash inventory was identical before and after bounded
publication:

| Artifact | SHA-256 |
| --- | --- |
| `art-band-catalog.json` | `2cb0eae81cc18d1db088bcf0c0a139c9769d4789a16b211e71d517ff490ab385` |
| `band-selection-ledger.json` | `4d6b6ffe75c216273ae1a627eec9d27f27c80a606e4293ec66f591561be345b6` |
| `ice-ih-tattoo-mockup.png` | `746466054b0f23425f26a56327c490276fe1478218171f147c371cef7e9e2794` |
| `ice-ih-tattoo-primary.pdf` | `0d1c0eec24bbb6898a384eea0a90144d8ff6a9ca59eeb855614d99158a8511e1` |
| `ice-ih-tattoo-primary.svg` | `ebec79d4a65b5e36f4477f6fb91f90566bcbefd6519c91957bb56d430c8c2084` |
| `ice-ih-tattoo-stencil.png` | `e5f8a2980e1034a5094503b7f6237aa0adaf65c83fd097a6bc319ce839095c49` |
| `manifest.json` | `8f30394d69611e4fbd535cf491d5e7a4be08060a87bf781bf8df4db0e25ad635` |
| `path-geometry.json` | `b70fb47e9960da497736f4e35b3073c9688a9a05eb1716bde97e116ecbf66143` |
| `stroke-gap-diagnostic.json` | `292220d7d4c140519aa723a5ba1908aa91166c60428c4436bbe0e74ad1594aa8` |
| `tattoo-artist-review.txt` | `691a5269ba346bc5c09f69f6a149ecf2a4d06d69e4a9ed8d06638698dbd5ebe4` |
| `tattoo-recipe.json` | `6767e753624dbc5ed5006b5a961ca7b362c97cbf74a71a7504204aa450b7c1f1` |

## Test-driven and machine gates

| Gate | Result |
| --- | --- |
| Ordered-member sensitivity check | Expected RED: a temporary wrong first member failed at index `0` against `art-band-member-239b7cb5e485d442`; the required tuple was restored |
| `uv run pytest tests/integration/test_ice_tattoo.py -q` | PASS: `2 passed` |
| `uv run pytest -q` | PASS: `1077 passed, 1 skipped, 2095 warnings`; warnings are upstream diffpy/orix/diffsims deprecations |
| `uv run ruff check .` | PASS: `All checks passed!` |
| `uv run python scripts/validate_work_items.py` | PASS: `Validated 37 work items in docs/work` |
| `git diff --check` | PASS: exit `0` |
| Retained JSON/SVG probe | PASS: exactly one non-audit candidate, 11 geometry paths, `132.0 mm` outer diameter, and SVG child order `11 path, 1 circle` |

The exact-harmonic regression continues to run with NumPy floating-point
errors enabled and runtime warnings promoted to errors. Parallel axial normals
remain rejected by the unchanged angular-redundancy rule without normalizing a
zero cross product.

## Controller visual inspection and open gate

The bounded mockup and stencil were opened at their original `1713 x 1713 px`
resolution. Both show the full circular projection boundary with clear canvas
margin on every side. The 11 path contacts merge into the boundary, the circle
reads continuously above them, and no black geometry extends beyond its outer
edge. The dominant/secondary/fine width hierarchy remains visually apparent.

The outputs contain no detector rectangle, node glyph, halo, doubled boundary,
graywash, or spatially filtered image geometry. The network remains deliberately
dense: several natural crystallographic crossings form heavy black hubs, and
several path-to-boundary contacts are visually substantial. These are not
machine-validation failures, but their composition and practical tattooability
require the user's and a qualified tattoo artist's visual review. KIKU-T029
therefore remains active, and no graywash/dotwork treatment is authorized.
