# Ice Ih Oriented Spherical-Master Review

- Work item: [KIKU-T027](../work/KIKU-T027.md)
- Production state: machine-verified review candidate retained locally
- `presentation_status: awaiting_user_review`
- Scientific claim: `presentation_only`

## Scientific scope

This candidate rotates the exact Ice Ih oxygen-sublattice directional field on
`S2` with the repository's active crystal-to-sample Bunge ZXZ orientation
`(17, 31, 43)` degrees. The exact oriented-node NPZ is authoritative; the
fixed specimen-frame hemispheres and complementary sphere views are display
derivatives evaluated through the explicit pullback
`I_sample(s) = I_crystal(G_cs^-1 s)`.

This is a kinematical, presentation-only orientation proof. It does not claim
dynamical-scattering fidelity, experimental-pattern fidelity, or a complete
ordered-hydrogen Ice model.

## Single bounded production invocation

The output root was absent before the command. One invocation was made, with
no deletion or retry:

```text
uv run kikuchi-lab render-oriented-spherical --recipe recipes/spherical/ice-ih-oriented-s2-proof.yml --output local/runs/ice-ih-oriented-s2 --profile review
```

The workflow completed the smoke profile before starting the review profile.
Both were below their recorded `180 s` and `600 s` deadlines.

| Profile | Run ID | CLI elapsed seconds | Stage-timing elapsed seconds | Manifest SHA-256 |
| --- | --- | ---: | ---: | --- |
| smoke | `oriented-spherical-run-97270c298d394306` | `2.7192983340355568` | `2.689925042039249` | `682e680ef5e1c4a9693e0e86b4847ad8844853b1b6953504211ba95c2074219a` |
| review | `oriented-spherical-run-8549033ce3fcc800` | `42.812521790969186` | `40.05164841597434` | `0bcc451740982ce8a8ff71afe5ba0ad4d4ef1770e99cf61f4cd4b321e80c1588` |

Bundle roots:

- smoke: `local/runs/ice-ih-oriented-s2/smoke/oriented-spherical-run-97270c298d394306`
- review: `local/runs/ice-ih-oriented-s2/review/oriented-spherical-run-8549033ce3fcc800`

## Exact oriented-field evidence

| Field | Smoke | Review |
| --- | --- | --- |
| Orientation ID | `orientation-fcc465bb0a3210c9` | `orientation-fcc465bb0a3210c9` |
| Source structure ID | `source-f306aaa577129b9e` | `source-f306aaa577129b9e` |
| Source field ID | `s2-field-fb1349b99eb4f190` | `s2-field-b121f4fc69111f17` |
| Identity field ID | `s2-field-b606992a7cd92ffc` | `s2-field-f6cf44d5c6bfd328` |
| Oriented field ID | `s2-field-0c0a4d9e00fa422d` | `s2-field-3126c476808da813` |
| Oriented NPZ SHA-256 | `7e8a53f96527d3b740317458bfc206ec7cea39beef906d48bae2007e7b69e7f5` | `c47c0e1130173b5600747d183b0148a519b27c88507d39f422095ec7b37eaa44` |

The review NPZ is at
`local/runs/ice-ih-oriented-s2/review/oriented-spherical-run-8549033ce3fcc800/data/oriented-s2-field.npz`.
It contains `1,646,942` finite nodes. The inspected specimen-coordinate array
has maximum unit-norm error `2.220446049250313e-16`. The orientation ledger
records determinant `1.0`, orthonormal maximum error
`2.220446049250313e-16`, and maximum inverse error
`3.3306690738754696e-16`.

The ledger's before/after SHA-256 values are identical for raw intensity,
normalized intensity, density weight, source row, source column, and source
hemisphere. Only the coordinate hash changes under the non-identity rotation,
so node ordering, values, and source provenance remain attached exactly.

## Native-scale review inventory

All paths below are inside
`local/runs/ice-ih-oriented-s2/review/oriented-spherical-run-8549033ce3fcc800`.

| Review figure | Native dimensions | SHA-256 |
| --- | --- | --- |
| `figures/identity-vs-oriented-upper.png` | `4800 x 2400` | `794e9a5347e71ddc78b33fb586f4088e085737c76ed02c027877e0682f16a333` |
| `figures/oriented-upper.png` | `2400 x 2400` | `11c4d65f25538dd28b2c1f019ef3e5769ce70446ba42f45bc12334edde0fbf34` |
| `figures/oriented-lower.png` | `2400 x 2400` | `4e0696a8eb1250be9fed97ba1ccd13e3a42d77433823d100c587918d4e838f99` |
| `figures/oriented-sphere-front.png` | `2400 x 2400` | `fda5f1e6dc9bde553007596587bfed075e9d182cb9eff73af50b5521e8553fce` |
| `figures/oriented-sphere-rear.png` | `2400 x 2400` | `3bb47a7359f775eca04c1e39bee4d3d1ec381177b83ef05ab16116cdd7afa92a` |
| `figures/orientation-axes.png` | `2400 x 2400` | `7c3af30c3ef355f442ac7f6bb0ee666b6988074421e8ccdd838849a9e8e321ee` |

## Controller visual inspection

All six figures were opened at original/native detail. The identity comparison
keeps the specimen-frame circular canvas fixed while the complete band and
intersection network moves coherently. The oriented upper and lower
hemispheres and the complementary front/rear sphere views show consistent
field organization. The field remains crisp rather than blurred; the native
nearest-raster treatment exposes bounded staircase texture rather than a
spatially smoothed edge.

No center-line or band-boundary overlay appears in the art figures. This agrees
with the figure and presentation ledgers, which record `center_overlay: false`,
`boundary_overlay: false`, `spatial_filter: none`, and `image_rotation: false`.
The circular rim is the only display boundary. This controller inspection does
not replace the open user visual-review gate.

## Machine gates

| Gate | Result |
| --- | --- |
| Focused oriented scientific/unit suite | PASS: `134 passed, 116 warnings in 7.55 s`; warnings are upstream diffpy/orix/diffsims deprecations |
| `uv run pytest -q` | PASS: `918 passed, 1 skipped, 2095 warnings in 151.18 s`; warnings are upstream diffpy/orix/diffsims deprecations |
| `uv run ruff check src tests` | PASS: `All checks passed!` |
| `uv run python scripts/validate_work_items.py` | PASS: `Validated 32 work items in docs/work` |

## Review gate

The machine-verifiable orientation, reprojection, bundle, runtime, and
presentation constraints are satisfied. Promotion beyond presentation-proof
status remains blocked on explicit user review of the six retained figures.
