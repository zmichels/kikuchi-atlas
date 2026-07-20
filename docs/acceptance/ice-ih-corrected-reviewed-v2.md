# Corrected Ice Ih Reviewed-Selection Acceptance

- Work item: [KIKU-T035](../work/KIKU-T035.md)
- Migration contract: [phase-general direct-reflector design](../superpowers/specs/2026-07-16-phase-general-direct-reflector-art-series-design.md)
- Production state: retained corrected-frame catalog and reviewed-HKL tattoo bundle
- Scientific claim: `presentation_only`

## Scientific migration boundary

The corrected reflector engine is authoritative for new products. It expands
the Ice Ih oxygen sublattice to four sites in the alignment-aware
crystallographic frame and assigns exact symmetry/Friedel magnitude ties before
selection. The earlier reviewed catalog and tattoo remain immutable legacy
presentation evidence; their calculated catalog/member identities are not
reused.

The versioned manifest
`recipes/art/ice-ih-reviewed-selection-v2.yml` preserves the exact reviewed
11-HKL order, orientation, tier, width, and legacy member link. Its tracked-file
SHA-256 is
`7972adf37019c73ac7e9cb0f6b593d622a49cd755a6af7efab92ef98446ae848`.
Corrected binding proves every HKL remains present and tattoo-eligible and
records `automatic_reselection: false`.

## Retained production invocations

Both commands completed once into previously absent content-identified child
directories. No retained product was deleted or overwritten.

```text
uv run kikuchi-lab build-direct-art-catalog --recipe recipes/reflectors/ice-ih-art-bands.yml --output local/phase-general-direct-reflector-art/ice-ih-corrected-catalog-v2
uv run kikuchi-lab render-ice-tattoo --catalog local/phase-general-direct-reflector-art/ice-ih-corrected-catalog-v2/direct-art-catalog-run-886bc7ef458d1e23/art-band-catalog.json --recipe recipes/art/ice-ih-tattoo.yml --selection-manifest recipes/art/ice-ih-reviewed-selection-v2.yml --output local/phase-general-direct-reflector-art/ice-ih-corrected-reviewed-v2 --treatment primary
```

| Product | Run ID | Manifest SHA-256 | Retained bundle |
| --- | --- | --- | --- |
| corrected direct catalog | `direct-art-catalog-run-886bc7ef458d1e23` | `0e4355c64fbd2512499381ab51b987f47c22c1a8ddf41fc520917f6d11a183ed` | `local/phase-general-direct-reflector-art/ice-ih-corrected-catalog-v2/direct-art-catalog-run-886bc7ef458d1e23` |
| corrected reviewed tattoo | `ice-tattoo-run-a4cecd7a5122f980` | `c540ecee7f4cf71b5d58aa83439f4b7320b37eead1a4c9dc8294c12b06ca2cf8` | `local/phase-general-direct-reflector-art/ice-ih-corrected-reviewed-v2/ice-tattoo-run-a4cecd7a5122f980` |

## Identities and selection proof

| Field | Corrected value |
| --- | --- |
| Source structure ID | `COD-1572233-O-sublattice` |
| Source structure SHA-256 | `4327a279e414a62f861d143e18570e9d741bbbb7d04dd2fb471c930988f95b81` |
| Reflector calculation ID | `reflector-calculation-c3c681a18380ee7f` |
| Evidence ID | `reflector-evidence-f408c540ea34de2e` |
| Catalog ID | `art-band-catalog-627acdd57e1aa127` |
| Catalog members / eligible / simulations | `514 / 144 / 0` |
| Frozen manifest ID | `frozen-tattoo-selection-f0e4f843362bab65` |
| Orientation ID | `orientation-fcc465bb0a3210c9` |
| Tattoo recipe ID | `tattoo-recipe-e972429e0106a476` |
| Selection ID | `tattoo-selection-840a9513fed41720` |
| Geometry ID | `tattoo-geometry-80ebbc224df034aa` |
| Boundary ID | `tattoo-boundary-da45c61d325de3be` |
| Diagnostic ID | `tattoo-stroke-gap-diagnostic-7ae79700c2edc8bc` |

The reviewed-to-corrected binding is:

| HKL | Legacy member | Corrected member |
| --- | --- | --- |
| `(0, 0, 2)` | `art-band-member-239b7cb5e485d442` | `art-band-member-724130e073473c13` |
| `(1, -2, 0)` | `art-band-member-d38532aafcf1ed7f` | `art-band-member-4b7d16aa00968ddb` |
| `(2, -1, 0)` | `art-band-member-3cb4167967631dcc` | `art-band-member-115a3069d65bbbf5` |
| `(1, 1, 0)` | `art-band-member-0a414c19f6ab8845` | `art-band-member-eaf69e72c7791772` |
| `(1, -2, 2)` | `art-band-member-b4647bcd2cbca9f6` | `art-band-member-f8253d4be14e9e87` |
| `(2, 0, 0)` | `art-band-member-b67c65e3bc542c16` | `art-band-member-ee9d3c844dde2607` |
| `(2, -1, -2)` | `art-band-member-263af8004ec3e279` | `art-band-member-4f023b159119865a` |
| `(2, -1, 2)` | `art-band-member-ef3609aba836233b` | `art-band-member-d781bf4f94ee50a8` |
| `(1, -2, -2)` | `art-band-member-4fdb2612d72a02c1` | `art-band-member-0ec8c347257494a5` |
| `(1, 1, -2)` | `art-band-member-2413565c4ba2c58d` | `art-band-member-d8a396bc862d0a03` |
| `(1, 1, 2)` | `art-band-member-c38e4b2859f9646d` | `art-band-member-91ac4004828ab124` |

All 11 paths retained their exact reviewed centerlines and width hierarchy. The
diagnostic reports `status: passed`, `stroke_containment: passed`, complete
hemisphere boundary, and all 11 required clips at the exact `63.8 mm` clip
radius inside the `66.0 mm` outer radius.

## Corrected catalog inventory

| Artifact | SHA-256 |
| --- | --- |
| `art-band-catalog.json` | `edc2d00a2407e4057bf34e0ff35f21bfc2342ee0501748b5d29be72170c12de6` |
| `catalog-ledger.json` | `77e8a794a91250d0bec7fc2d2c24abf3023e82e1b8c95ad213dfb5e7979e140d` |
| `direct-reflector-recipe.json` | `60a0dc0702ee7a9c1184c5ed866736900781ab24d299fd0c7aa0396916a86cb1` |
| `reflector-evidence-ledger.json` | `945929f10e43a1169f26a0b922c4641b754000a40358a3f8fe110d55f05e04bc` |
| `reflector-evidence.npz` | `134c475b1b1efef64f097038134ef70ce076a998004eb70e650279d18cb6e634` |
| `scientific-claim.txt` | `1e49c78b230034736dd28af3ccdad52bddb6bfd96603041def1275727c1b661c` |

## Corrected reviewed-tattoo inventory

| Artifact | SHA-256 |
| --- | --- |
| `art-band-catalog.json` | `edc2d00a2407e4057bf34e0ff35f21bfc2342ee0501748b5d29be72170c12de6` |
| `tattoo-recipe.json` | `a14906754b544167dbb4aa0983c76b41fe1cdd68fcf328003a2b1edddc41876a` |
| `frozen-selection-manifest.json` | `307bc98c386bc68489bcad90f22edf72f72d11bd3fec4b3d49ba48e7db7e4b92` |
| `band-selection-ledger.json` | `9b7d24a78e61c5f74289def0a6625ee6e07afacd99166957a6cd2e88a6aaacda` |
| `path-geometry.json` | `b607ff000ad70592cd92cf73ee4a4447889db5394fc26e92fa127e55e6108d1b` |
| `stroke-gap-diagnostic.json` | `02fedf51e438daca03c7b0e564cbaebfb0dfe9808e8302252bbf4efa58723487` |
| `ice-ih-tattoo-primary.svg` | `efacd3042cba75699a19fa58e6b484784a4739c59d1bf5fccda7230c2f6d7d70` |
| `ice-ih-tattoo-primary.pdf` | `5924f6a59ec472cbd0708a73fd3bbdbb84145c6f53b1c69f69ec42932cd6056c` |
| `ice-ih-tattoo-mockup.png` | `815fb04d77ac84e5cf3912debb6a1d855cac991abf73b51d229c12bdfb7efe64` |
| `ice-ih-tattoo-stencil.png` | `86ab4a6eb8d7d53b3ccc44695c71213b8043c8202e19d414dcf02d48187bda89` |
| `tattoo-artist-review.txt` | `691a5269ba346bc5c09f69f6a149ecf2a4d06d69e4a9ed8d06638698dbd5ebe4` |

## Visual and regression gates

The corrected mockup and stencil were opened at original resolution. They show
the full circle, unchanged 11-path composition, and the approved
dominant/secondary/fine hierarchy without raster blur. The corrected and legacy
mockup PNGs are byte-identical at SHA-256
`815fb04d77ac84e5cf3912debb6a1d855cac991abf73b51d229c12bdfb7efe64`;
the primary PDFs and stencil PNGs are also byte-identical. The corrected SVG
differs only because corrected content identities/provenance are embedded.

| Gate | Result |
| --- | --- |
| Focused migration/catalog/tattoo/CLI tests | PASS: `67 passed` |
| Full regression suite | PASS: `1191 passed, 1 skipped` |
| Scoped Ruff | PASS: `All checks passed!` |
| Work-item validation | PASS: `Validated 42 work items in docs/work` |
| `git diff --check` | PASS: exit `0` |
| Retained-product inspection | PASS: manifest inventories, 11 eligible HKLs, containment, and original-resolution visual comparison |
