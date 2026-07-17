# Quartz, Zircon, and Titanite Direct-Catalog Acceptance

- Work item: [KIKU-T033](../work/KIKU-T033.md)
- Design: [phase-general direct-reflector art series](../superpowers/specs/2026-07-16-phase-general-direct-reflector-art-series-design.md)
- Production state: source/catalog onboarding complete; bounded parity still pending
- Scientific claim: `presentation_only`

## Retained production invocations

Each command completed once into a previously absent output root. No retained
product was deleted, overwritten, retried, or resolution-grown.

```text
uv run kikuchi-lab build-direct-art-catalog --recipe recipes/reflectors/quartz-art-bands.yml --output local/phase-general-direct-reflector-art/quartz-catalog-v1
uv run kikuchi-lab build-direct-art-catalog --recipe recipes/reflectors/zircon-art-bands.yml --output local/phase-general-direct-reflector-art/zircon-catalog-v1
uv run kikuchi-lab build-direct-art-catalog --recipe recipes/reflectors/titanite-art-bands.yml --output local/phase-general-direct-reflector-art/titanite-catalog-v1
```

| Phase | Source identity | Catalog / evidence | Members / eligible / simulations | Retained bundle |
| --- | --- | --- | --- | --- |
| alpha-quartz | `COD-9012600`; `29176db9b50e42972646a43bd171e4cff1d6bc47cc2f93e265ff809ecadd85ef` | `art-band-catalog-4f9fc8f1789aea65`; `reflector-evidence-6687d384dee2f95c` | `620 / 87 / 0` | `local/phase-general-direct-reflector-art/quartz-catalog-v1/direct-art-catalog-run-2c7ad6fc6bccd796` |
| zircon | `COD-9000684-isotropic-U`; `ff30c03e88588a8d1a54a9a2a22b3b4e73a0230bf444120dc6eb236d4391739d` | `art-band-catalog-52a01924f3a8eee2`; `reflector-evidence-63de00f89e2e31d5` | `696 / 77 / 0` | `local/phase-general-direct-reflector-art/zircon-catalog-v1/direct-art-catalog-run-672d40a47371a633` |
| synthetic titanite, 298.15 K | `COD-9000509`; `ed45563f6621488f165373f2847c65acef197744322e0937d985518a3437be42` | `art-band-catalog-2c160b67af3953d5`; `reflector-evidence-86ed13ceb68628bc` | `1089 / 66 / 0` | `local/phase-general-direct-reflector-art/titanite-catalog-v1/direct-art-catalog-run-ffa0c0e8fd0c4f87` |

All three use the same first-series calculation identity
`reflector-calculation-c3c681a18380ee7f` and weighting identity
`reflector-weighting-78182ed16c073d9b`: 20 keV, minimum d-spacing 0.7
angstrom, `xtables`, candidate factor 0.03, squared art weight, and inclusive
eligibility floor 0.08.

## Setting and approximation boundaries

- Quartz is the right-handed ambient alpha-quartz `P 31 2 1` source in its
  source axes.
- Zircon retains the exact COD original and a deterministic isotropic-U
  derivative. The derivative changes no coordinate, occupancy, cell, or
  symmetry operation; simulation maps origin choice 2 to diffpy choice 1 with
  `[0, 1/4, -1/8]` and proves `4 Zr + 4 Si + 16 O`.
- Titanite is the 25 C synthetic stoichiometric `P 1 21/a 1` structure, not
  high-temperature A2/a and not a substituted natural specimen. Simulation
  maps it exactly to diffpy `P 1 21/c 1` by swapping `a/c` and `x/z`.
- Titanite's invalid upstream Cartesian pseudo-HKL orbit is rejected; its
  direct catalog uses exact integer reciprocal rotations from the fractional
  space-group operators. Existing reviewed upstream orbits remain unchanged
  when every HKL is integral.

## Retained inventories

### Quartz — `direct-art-catalog-run-2c7ad6fc6bccd796`

Manifest SHA-256:
`fbd0e6e7081213653b327fc2fe47ee41ebca7b814a29eedb66ed4520fb236b6d`.

| Artifact | SHA-256 |
| --- | --- |
| `art-band-catalog.json` | `81efa6933e06ffa46bc941e8f7d4213b767c701b306b3cd4d2cfab86bd3938d7` |
| `catalog-ledger.json` | `9c7d1351ca9054fd6750c26a7635c5f55e6a6c2725632eee892de434b24dd865` |
| `direct-reflector-recipe.json` | `68f6ef34ce750bfa02516763a0e9d4a7f445378ce3806df0d14624c3621b0049` |
| `reflector-evidence-ledger.json` | `3cadd45a8d7a5af8ef08ca44ab6931b0b7359c937c63ddb7d81b54b871123741` |
| `reflector-evidence.npz` | `a1de070779e1b78a749fd20849fabc3da87aa84486917431c147cda34ebe7d40` |
| `scientific-claim.txt` | `1e49c78b230034736dd28af3ccdad52bddb6bfd96603041def1275727c1b661c` |

### Zircon — `direct-art-catalog-run-672d40a47371a633`

Manifest SHA-256:
`a636d3ec2c80585ef73cfa181bc826e0aabccb7e8e11f75b209287d63a9f14aa`.

| Artifact | SHA-256 |
| --- | --- |
| `art-band-catalog.json` | `9a2d56fdb16be584cf4bc66ca71097434c3dcd9fe8d370a4c58dda5c59c9846b` |
| `catalog-ledger.json` | `898b357003e21c1c88504c6a9289813364c05cffb9732a70e30ef4fe99741be5` |
| `direct-reflector-recipe.json` | `308a538a090ab418dfec2a09a1adb0a2da053f204dc070a02d2ac4d1f0121b9e` |
| `reflector-evidence-ledger.json` | `69b1caaa15c91f2f6b2e3405e2a0238e2f4ae7550080d792c8f66005297fef69` |
| `reflector-evidence.npz` | `7bff0d30617dd4fe5461c4f5b1c86189afc6a8b1fdedef2d5070db26595e232b` |
| `scientific-claim.txt` | `1e49c78b230034736dd28af3ccdad52bddb6bfd96603041def1275727c1b661c` |

### Titanite — `direct-art-catalog-run-ffa0c0e8fd0c4f87`

Manifest SHA-256:
`6b683520817ae583bf14ba23b05a5301968588665e29d24c18419fc4eb5aacec`.

| Artifact | SHA-256 |
| --- | --- |
| `art-band-catalog.json` | `b85d1353a0e42ddf2c33982ff4609bd1c81b2f1918c5d4e2ee1b5e9abf74ae53` |
| `catalog-ledger.json` | `36855c2e695477e4a4b28fdfc99c873eac9c57f8c473d0b720b4d3bb1c6281b1` |
| `direct-reflector-recipe.json` | `031a1cac53fcb0b122e317d865cf4bfecfc76f18cebbd7616531cd0e759f5809` |
| `reflector-evidence-ledger.json` | `dc8367e92a5f15c6269460e3b24cc02cb6fde4f1ba4182d587c1d9ff427dda5f` |
| `reflector-evidence.npz` | `06dbaa9eea77fde02bacdf5424fd874f109ec0040d6ccc13ba10c73aa37a336c` |
| `scientific-claim.txt` | `1e49c78b230034736dd28af3ccdad52bddb6bfd96603041def1275727c1b661c` |

## Verification gates

| Gate | Result |
| --- | --- |
| Source/direct-catalog TDD tests | PASS for quartz, zircon, and titanite; all retain at least 11 eligible bands |
| Shared adapter/scientific regression | PASS: `269 passed` before titanite; focused titanite/core/Ice regression `21 passed` |
| Full regression suite | PASS: `1197 passed, 1 skipped` |
| Scoped Ruff | PASS: `All checks passed!` |
| Work-item validation | PASS: `Validated 42 work items in docs/work` |
| `git diff --check` | PASS: exit `0` |

The work item remains active because the independently bounded
direct-versus-simulator parity products are intentionally deferred to the
series acceptance step; no parity claim is made here.
