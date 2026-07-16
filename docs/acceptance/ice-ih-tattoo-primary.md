# Ice Ih Primary Tattoo Review

- Work items: [KIKU-T028](../work/KIKU-T028.md), [KIKU-T029](../work/KIKU-T029.md)
- Production state: machine-verified primary candidate retained locally
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

This science-art is not medical guidance or a skin-approved stencil and
requires qualified tattoo-artist review before any use on skin.

## Retained production invocations

Both output roots were absent before these commands. Each command completed
once, without deletion or retry.

```text
uv run kikuchi-lab build-ice-art-catalog --recipe recipes/art/ice-ih-band-catalog.yml --output local/ice-art-catalog-primary-proof
uv run kikuchi-lab render-ice-tattoo --catalog local/ice-art-catalog-primary-proof/ice-art-catalog-run-57478bf29894e175/art-band-catalog.json --recipe recipes/art/ice-ih-tattoo.yml --output local/ice-tattoo-primary-proof --treatment primary
```

| Product | Run ID | Manifest SHA-256 | Retained bundle |
| --- | --- | --- | --- |
| catalog | `ice-art-catalog-run-57478bf29894e175` | `f220a20b7a48a3113ca25067b721c6d5f94d9266a839eb246dc007be15819aeb` | `local/ice-art-catalog-primary-proof/ice-art-catalog-run-57478bf29894e175` |
| primary tattoo | `ice-tattoo-run-d158193b08f3668e` | `8f30394d69611e4fbd535cf491d5e7a4be08060a87bf781bf8df4db0e25ad635` | `local/ice-tattoo-primary-proof/ice-tattoo-run-d158193b08f3668e` |

## Catalog and geometry identities

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
| Tattoo recipe ID | `tattoo-recipe-76edfd115d69e177` |
| Selection ID | `tattoo-selection-b99eb402501a6323` |
| Geometry ID | `tattoo-geometry-c0516b6d20ff76a4` |
| Geometry snapshot SHA-256 | `b70fb47e9960da497736f4e35b3073c9688a9a05eb1716bde97e116ecbf66143` |
| Stroke-gap diagnostic ID | `tattoo-stroke-gap-diagnostic-382973366d9abf8c` |

The geometry is an exact 145 mm square with projection
`upper_specimen_stereographic_center_trace`. It contains 11 unique paths in the
ordered `4 dominant / 4 secondary / 3 fine` allocation. The ordered widths are
`4.8, 4.2, 3.6, 3.1, 2.5, 2.2, 1.9, 1.6, 1.2, 1.0, 0.8 mm`.

The diagnostic records hard minimums of `1.5 mm` for noncrossing edge gaps and
`2.0 mm` for unrelated endpoint clearance. All 55 pairs in this retained
great-circle network are true crystallographic crossings, so there are no
noncrossing pairs to which those two clearance measurements apply; the observed
minima are therefore `null`, not relaxed thresholds.

## Canonical primary inventory

All paths below are inside
`local/ice-tattoo-primary-proof/ice-tattoo-run-d158193b08f3668e`.

| Artifact | Dimensions | SHA-256 |
| --- | --- | --- |
| `ice-ih-tattoo-primary.svg` | `145 x 145 mm`, transparent canvas, 11 black paths | `ebec79d4a65b5e36f4477f6fb91f90566bcbefd6519c91957bb56d430c8c2084` |
| `ice-ih-tattoo-primary.pdf` | `145 x 145 mm` MediaBox | `0d1c0eec24bbb6898a384eea0a90144d8ff6a9ca59eeb855614d99158a8511e1` |
| `ice-ih-tattoo-mockup.png` | `1713 x 1713 px`, `300 dpi` | `746466054b0f23425f26a56327c490276fe1478218171f147c371cef7e9e2794` |
| `ice-ih-tattoo-stencil.png` | `1713 x 1713 px`, `300 dpi` | `e5f8a2980e1034a5094503b7f6237aa0adaf65c83fd097a6bc319ce839095c49` |
| `band-selection-ledger.json` | 11 selected paths with score/rejection provenance | `4d6b6ffe75c216273ae1a627eec9d27f27c80a606e4293ec66f591561be345b6` |
| `stroke-gap-diagnostic.json` | validation status `passed` | `292220d7d4c140519aa723a5ba1908aa91166c60428c4436bbe0e74ad1594aa8` |
| `tattoo-artist-review.txt` | required 136-byte disclaimer | `691a5269ba346bc5c09f69f6a149ecf2a4d06d69e4a9ed8d06638698dbd5ebe4` |

The bundle also contains canonical snapshots of the recipe, catalog, and path
geometry. Its manifest inventories those files plus every primary render and
was written last before atomic no-replace promotion.

## Test-driven and machine gates

| Gate | Result |
| --- | --- |
| Catalog-policy RED | Expected RED: tracked `0.10`, only 10 fixed-`4 degree` survivors, and exact-harmonic `FloatingPointError` |
| Catalog-policy focused GREEN | PASS: `3 passed in 3.03 s` |
| Task 2-4 regressions | PASS: `80 passed in 3.24 s` |
| Tattoo-policy RED | Expected RED: legacy `0.10` catalog reached the stale publisher guard |
| Task 7 focused GREEN | PASS: `36 passed in 20.33 s` |
| `uv run pytest -q` | PASS: `1053 passed, 1 skipped, 2095 warnings in 135.87 s`; warnings are upstream diffpy/orix/diffsims deprecations |
| `uv run ruff check .` | PASS: `All checks passed!` |
| `uv run python scripts/validate_work_items.py` | PASS: `Validated 37 work items in docs/work` |
| `git diff --check` | PASS: exit `0` |

The exact-harmonic regression runs with NumPy floating-point errors enabled and
runtime warnings promoted to errors. Parallel axial normals are rejected by the
unchanged angular-redundancy rule without normalizing a zero cross product.

## Controller visual inspection and open gate

The retained mockup and stencil were opened at their native 1713-pixel detail.
They show only the intended black path network: no rim, detector rectangle,
node glyph, halo, doubled edge, graywash, or spatially filtered image geometry.
The dominant/secondary/fine width hierarchy is visually apparent.

The network is deliberately dense. Several natural crystallographic crossings
form heavy black hubs, and some thick open strokes reach the visible crop edge.
These are not machine-validation failures, but their composition and practical
tattooability require the user's and a qualified tattoo artist's visual review.
KIKU-T029 therefore remains active, and no graywash/dotwork treatment is
authorized.
