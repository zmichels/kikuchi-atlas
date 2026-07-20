# Five-Phase Direct-Reflector Hemisphere Art Acceptance

- Work item: [KIKU-T034](../work/KIKU-T034.md)
- Parent feature: [KIKU-F006](../work/KIKU-F006.md)
- Design: [phase-general direct-reflector art series](../superpowers/specs/2026-07-16-phase-general-direct-reflector-art-series-design.md)
- Production state: scientific and computational gates complete; human visual
  preference review pending
- Scientific claim: `presentation_only`

## Outcome

The first phase-general family is retained locally. It contains the approved
corrected Ice Ih standard as a read-only reference, a new 15-percent-wide Ice
companion, standard and wide pairs for forsterite, alpha-quartz, zircon, and
titanite, and one directly rendered 4500 x 1800 comparison sheet. The active
crystal-to-sample Bunge ZXZ orientation is `(17, 31, 43)` degrees for every
phase.

The production series command performed zero master-pattern simulations. Each
phase first passed one separately retained, bounded direct-versus-simulator
reflector-parity run. Every parity run used one simulation, zero retries, a
90-second ceiling, exact HKL identity, matching provenance, and passing numeric
residuals.

These are kinematical, presentation-oriented great-circle products. The
simulator parity establishes the project-owned pre-master reflector seam; it
does not make the black stroke hierarchy a dynamical EBSD intensity model.

## Input locks

| Phase | Source ID | Source file SHA-256 | Reflector recipe SHA-256 | Catalog ID used by series |
| --- | --- | --- | --- | --- |
| Ice Ih | `COD-1572233-O-sublattice` | `83a2287f30311bc409f4dfb43815db82c5cc66e4f9f3ff8d3be6ed170b690824` | `2c483bd651a0981c5d030e4d46cd29ba27e36bf7f5e35e677550db877b688b08` | `art-band-catalog-627acdd57e1aa127` |
| forsterite | `COD-9000319` | `59c1b40f9ef7189abe3306088678a7d1f4284b11ff8864c0f82b93ae2ff46122` | `85f2162a4fdb4130da6316fc7efbd0dc8bef3668d7c601f14d02b5ff330ab0b6` | `art-band-catalog-94ae354258f66b7e` |
| alpha-quartz | `COD-9012600` | `122f3bc6eec3e24ce5f1ecbe55cb244ef53a2d52fae227fb5e6d0028ae85f3e1` | `d2fbdea1206765d7d56f8fd5af2a993fcc83970fc539f7eae2e16094b741f68f` | `art-band-catalog-4f9fc8f1789aea65` |
| zircon | `COD-9000684-isotropic-U` | `73f23f3164e5cf5154b7643bc85d6285ecf71faed13bb03ed8a3ad8c386bb298` | `212f1598783a3e9f26778e159533fbbae92ec44645c09a806e7d92c42f55aa31` | `art-band-catalog-52a01924f3a8eee2` |
| titanite | `COD-9000509` | `fbe027c4849cfddde61e4261140452f725eb3636164bce02bd5628b2233c805e` | `ecbd2a28ad0b74d84dd0a0083064a1ff6e4bf23304af6bb681666c03e3457cfb` | `art-band-catalog-2c160b67af3953d5` |

Shared tracked recipe locks:

| Input | SHA-256 |
| --- | --- |
| `recipes/art/five-phase-hemisphere-series.yml` | `b7a51e4ffc1784dfedad38e30ef7a22a53c4f1977b729b33fc13daca7732964e` |
| `recipes/art/ice-ih-reviewed-selection-v2.yml` | `7972adf37019c73ac7e9cb0f6b593d622a49cd755a6af7efab92ef98446ae848` |
| `recipes/art/ice-ih-tattoo.yml` | `c60b511426ae0965d6d36aaa56c42a778924a4be09ab0e547b05c07333586a3f` |

## Retained parity invocations

Each command below was executed exactly once. No failed or timed-out parity
command was retried and no resolution or timeout was widened.

```text
uv run kikuchi-lab validate-reflector-parity --recipe recipes/reflectors/ice-ih-art-bands.yml --output local/phase-general-direct-reflector-art/parity --timeout-seconds 90
uv run kikuchi-lab validate-reflector-parity --recipe recipes/reflectors/forsterite-art-bands.yml --output local/phase-general-direct-reflector-art/parity --timeout-seconds 90
uv run kikuchi-lab validate-reflector-parity --recipe recipes/reflectors/quartz-art-bands.yml --output local/phase-general-direct-reflector-art/parity --timeout-seconds 90
uv run kikuchi-lab validate-reflector-parity --recipe recipes/reflectors/zircon-art-bands.yml --output local/phase-general-direct-reflector-art/parity --timeout-seconds 90
uv run kikuchi-lab validate-reflector-parity --recipe recipes/reflectors/titanite-art-bands.yml --output local/phase-general-direct-reflector-art/parity --timeout-seconds 90
```

| Phase | Run / report | Axial / enumerated / signed | Elapsed | Master-array SHA-256 | Report-file SHA-256 |
| --- | --- | --- | --- | --- | --- |
| Ice Ih | `reflector-parity-run-2fc04ef7acef94c4`; `reflector-parity-report-02ca6310f31b3480` | `514 / 1734 / 1206` | `2.819745 s` | `bf8a7ea43c8e73b29bf026dfc96b52af652993b264f3f92f7a93cf8312524a51` | `2e12df01b30475178673a222afbf906835c7896b22ca919835dbf324b4a81952` |
| forsterite | `reflector-parity-run-83f8b8e06f963665`; `reflector-parity-report-c5512a4eedee1455` | `1273 / 3540 / 2546` | `3.496594 s` | `a72f5bb5e4d9dc174ea68f6b3e6e2a42a0da8bdd4d6725974e18cf8d6d676fbf` | `536db79dd8bef298d335a30f9910d8983c666e7df20e601f7acbe66490162447` |
| alpha-quartz | `reflector-parity-run-e7a0912120a5df91`; `reflector-parity-report-d98098d829dd6039` | `620 / 1376 / 1240` | `2.144675 s` | `2a6ddb11c118abf04359773fc39d245c0e217bcbf5219a5ac209ac9f72d1897c` | `229ed08034b73d551c43642d7ab17530485d3121d554a8675642783182868579` |
| zircon | `reflector-parity-run-fb301916800e50e4`; `reflector-parity-report-5dd4e0888cee4596` | `696 / 1608 / 1392` | `2.254978 s` | `12f8bf2c15a83f121327c7f8db162bbd37ce4bffab221c7bf6588340526afe62` | `3091cc4beb8e1daa9a5307d3d519e68ba8c9edde466741ee3f9b5226efb33c3a` |
| titanite | `reflector-parity-run-fd5c960ece11c250`; `reflector-parity-report-2c870292a35a5d4a` | `1089 / 4472 / 2178` | `3.945719 s` | `dc3af67963fd3e37021029e91b4287ef008b01fc554b8a47ea4b6ca73c6fa5cc` | `f3da81e68d700167648d3b429c891af558466e954a28f7fb7fcff4accd2ae7e2` |

Every report is retained beneath
`local/phase-general-direct-reflector-art/parity/<run-id>/reflector-parity-report.json`.

## Retained production invocation

```text
uv run kikuchi-lab render-phase-art-series --recipe recipes/art/five-phase-hemisphere-series.yml --parity-root local/phase-general-direct-reflector-art/parity --ice-standard-reference /Users/Z/Documents/kikuchi/.worktrees/spherical-intensity/local/phase-general-direct-reflector-art/ice-ih-corrected-reviewed-v2/ice-tattoo-run-a4cecd7a5122f980 --output local/phase-general-direct-reflector-art/series
```

The first publication preflight correctly left the output root absent when it
found that the new lock expected a generic standard-bundle schema while the
real immutable approved reference is the earlier `primary` tattoo schema. The
diagnostic is retained as
`local/phase-general-direct-reflector-art/series-command-initial-schema-mismatch.log`
with SHA-256
`af2a6e501910adc9d89018fb97fccfa0ace64703c59beb1d9a3e5239e8d86821`.
A test-first correction made the lock rebuild and validate the real artifact's
recipe, exact inventory, ordered selection, geometry, render bytes, hashes,
run ID, and path. Only the zero-master publication was then rerun; no parity
simulation was repeated. The successful log SHA-256 is
`96377ed521f9ba3d8a20fed9d17196041bbd601fea8fbf638fcceb13f774dab1`.

## Retained vector and raster bundles

Every child manifest inventories and checksums its SVG, PDF, mockup PNG,
stencil PNG, catalog snapshot, recipe snapshots, selection ledger, geometry,
clearance diagnostic, and review disclaimer. Paths below are relative to
`local/phase-general-direct-reflector-art/series/` except for the read-only Ice
standard.

| Cell | Run ID | Selection / geometry | Manifest SHA-256 |
| --- | --- | --- | --- |
| Ice standard, reference | `ice-tattoo-run-a4cecd7a5122f980` | `tattoo-selection-840a9513fed41720`; `tattoo-geometry-80ebbc224df034aa` | `c540ecee7f4cf71b5d58aa83439f4b7320b37eead1a4c9dc8294c12b06ca2cf8` |
| Ice wide | `ice-ih-hemisphere-wide-run-397dac85475bbb46` | `tattoo-selection-e4e8527987c6044c`; `tattoo-geometry-37a6a441fedfe2dc` | `b6d9bee5de22e5a99f8c8e61629c7db7af49cdd4b9d64c95468db3731dce6c0b` |
| forsterite standard | `forsterite-hemisphere-standard-run-1c34e517644729c5` | `tattoo-selection-830e3e1363ec7db3`; `tattoo-geometry-e32836dfb31df938` | `7c88ffa4452fe0d67927953d9c713245093891b19e04d7c0fe2f908b93dd8b7e` |
| forsterite wide | `forsterite-hemisphere-wide-run-a8d00a3c23f57bcf` | `tattoo-selection-830e3e1363ec7db3`; `tattoo-geometry-099ffe4f98b71b0d` | `7ef85a8de679a9a82ff51e4656a818b25789bd301c9d3dcfd820abf0ebfd32ea` |
| quartz standard | `quartz-hemisphere-standard-run-c8e68d027682d562` | `tattoo-selection-e0757d38bd4bd549`; `tattoo-geometry-37268afbf386e19a` | `2a1e6b07da5e9ea1a038a7037ed9b502a64254d108bfec2672005bdfcbbd3aae` |
| quartz wide | `quartz-hemisphere-wide-run-8bd3d82040b2453e` | `tattoo-selection-e0757d38bd4bd549`; `tattoo-geometry-0808ce7a0dd585e0` | `c0b95644354b52f7fa5453c6756f9bc9da2143145cde5c7c62bf6aae3a2066a8` |
| zircon standard | `zircon-hemisphere-standard-run-ad71aeef33302d99` | `tattoo-selection-b0c00e717bf8f932`; `tattoo-geometry-0d077c7cb5b9fb63` | `a3b4f10cfded8105b04e96205fa8660310428bd2fa494022d7b6b44a5173c4c9` |
| zircon wide | `zircon-hemisphere-wide-run-606cb887da272636` | `tattoo-selection-b0c00e717bf8f932`; `tattoo-geometry-3b9afacb2311da2a` | `ea1ab1065b93c902ffa1a50ef0ca6900d948792d4c25a8705fbe8338956416d4` |
| titanite standard | `titanite-hemisphere-standard-run-7a58d5c09fe6273c` | `tattoo-selection-e2a87a863e7872bc`; `tattoo-geometry-30b9e36ec63c0c9a` | `01fdaf8e6979c89cd4d58f1e53b5306c56dc06a891acf3087022b1f373c04735` |
| titanite wide | `titanite-hemisphere-wide-run-8df920091052a121` | `tattoo-selection-e2a87a863e7872bc`; `tattoo-geometry-9ea44689879cc105` | `cc96dd0b69b999e9ea2b72650ac390b0774037e13f3d2a8e2f58fd7feb1ee356` |

The Ice standard path is
`local/phase-general-direct-reflector-art/ice-ih-corrected-reviewed-v2/ice-tattoo-run-a4cecd7a5122f980`.
Each other retained path is exactly its run ID under the series root.

## Comparison bundle

| Artifact | Identity or SHA-256 |
| --- | --- |
| Series ID | `phase-art-series-88b3d0d1b9aa9169` |
| Series manifest | `f65787127eef29af4f38c7d53140a5855b687f0b342777d88e55500ae8d9b478` |
| `comparison.png` | `bd29d64698e3a7677059eb1420e500acbe70dbcbf3d77a48799932537eb01e39` |
| `comparison-ledger.json` | `44eda87b6e63f1ca4f590e375b9e32248ee7361acb3f9b0155fb2d46cf9543ee` |

Retained path:
`local/phase-general-direct-reflector-art/series/phase-art-series-88b3d0d1b9aa9169`.
The comparison is binary black/white, uses ten vector-direct 900 px panels,
and applies no resize, blur, Gaussian operation, or post-render smoothing.

## Pair invariance proof

The retained JSON ledgers were compared after publication. For all five phase
pairs:

- ordered selected member IDs and center-trace SHA-256 values are identical;
- ordered geometry point hashes are identical;
- every crystallographic path width has exact ratio `1.15`;
- the 2.20 mm hemisphere boundary is identical.

Ice's standard and wide selection IDs differ because the immutable reference
uses the earlier `TattooRecipe` identity while the new generic wide bundle uses
the phase-series composition identity. Their ordered crystallographic paths,
coordinates, standard geometry, and visual bytes are explicitly cross-locked.

## Catalog anchors

Earlier independently published catalog bundles remain retained and are not
duplicated or replaced:

| Phase | Catalog run | Manifest SHA-256 |
| --- | --- | --- |
| corrected Ice Ih | `direct-art-catalog-run-886bc7ef458d1e23` | `0e4355c64fbd2512499381ab51b987f47c22c1a8ddf41fc520917f6d11a183ed` |
| alpha-quartz | `direct-art-catalog-run-2c7ad6fc6bccd796` | `fbd0e6e7081213653b327fc2fe47ee41ebca7b814a29eedb66ed4520fb236b6d` |
| zircon | `direct-art-catalog-run-672d40a47371a633` | `a636d3ec2c80585ef73cfa181bc826e0aabccb7e8e11f75b209287d63a9f14aa` |
| titanite | `direct-art-catalog-run-ffa0c0e8fd0c4f87` | `6b683520817ae583bf14ba23b05a5301968588665e29d24c18419fc4eb5aacec` |

Forsterite's direct catalog snapshot and all five phase catalogs used in this
publication are also retained inside every corresponding child manifest.

## Verification gates

| Gate | Result |
| --- | --- |
| Pre-production unit/scientific/adapter suite | PASS: `1187 passed` |
| Real parity products | PASS: five one-shot reports, `simulation_count = 1`, `retry_count = 0` each |
| Production series | PASS: nine new bundles, ten cells, `simulation_count = 0` |
| Series integration file after real-schema correction | PASS: `8 passed` |
| Affected post-production integration suites | PASS: `21 passed` |
| Final full regression suite | PASS: `1242 passed, 1 skipped` |
| Ruff | PASS: `All checks passed!` |
| Work-item validation | PASS after tracker update |
| `git diff --check` | PASS |

The comparison and representative full-resolution stencils were opened at
native resolution. Computational review found complete circular boundaries,
binary sharp paths, preserved line hierarchy, and visibly distinct phase
compositions. Final human aesthetic preference between standard and wide—and
any phase-specific follow-up—is intentionally left open.
