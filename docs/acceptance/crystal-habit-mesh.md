# Crystal Habit Mesh Acceptance Ledger

- Status: Accepted
- Feature: [KIKU-F004](../work/KIKU-F004.md)
- MTEX parity task: [KIKU-T030](../work/KIKU-T030.md)
- Acceptance bundle: `habit-build-4a38bc559c829536`

## Scientific and mesh evidence

The quartz acceptance bundle was built from the tracked habit recipe and the
plain MTEX 6.1.1 reference ledger. Its polygon comparison passes without
vertex ordering, triangle ordering, or a fitted rotation: 32 vertices, 18
visible faces, labels `m`, `r`, and `z`, vertex Hausdorff distance
`2.5364330118318267e-14`, relative volume difference
`2.1562284150802615e-14`, and maximum matched face-normal angle `0.0 rad`.

- [Bundle directory](../../local/habits/quartz-acceptance/habit-build-4a38bc559c829536/)
- [Validation report](../../local/habits/quartz-acceptance/habit-build-4a38bc559c829536/mesh-validation.json)
- [MTEX parity report](../../local/habits/quartz-acceptance/habit-build-4a38bc559c829536/mtex-parity.json)
- [Labeled preview](../../local/habits/quartz-acceptance/habit-build-4a38bc559c829536/quartz-habit-preview.png)
- [Unmodified binary STL](../../local/habits/quartz-acceptance/habit-build-4a38bc559c829536/quartz-habit.stl)

The validation report proves one watertight, consistently wound, convex body
with a maximum dimension of exactly `60.0 mm`. Production validation and STL
export use `trimesh` with `process=False`; `process=True` remains confined to
the binary-STL round-trip regression. Build identity includes the recorded
runtime versions (`kikuchi-lab 0.1.0`, `matplotlib 3.11.0`, `numpy 2.4.6`,
`orix 0.14.3`, `scipy 1.18.0`, and `trimesh 4.12.2`).

## FlashForge-oriented slicer inspection

The unmodified STL was imported directly into Flash Studio 1.7.11
(`com.flashforge.orca-flashforge`) with the FlashForge AD5X selected. Flash
Studio registered `quartz-habit.stl` as one object with size
`18.9028 x 21.8271 x 60.0 mm`, volume `14180.1 mm^3`, and 60 triangles. No
repair prompt appeared, and no scale, rotation, mesh edit, or STL rewrite was
performed.

The source orientation places the `60.0 mm` crystal axis vertically, giving a
compact approximately `18.9 x 21.8 mm` bed footprint. The active slicer
profile had support generation enabled. Independently, the immutable
validation report identifies six downward faces at about `128.22 degrees`
from build-up, so support placement and an alternate print orientation remain
printer/operator decisions rather than properties silently baked into the
canonical mesh. This check confirms slicer ingestion and single-solid
topology; it does not claim a completed physical print.

## Milestone boundary

This acceptance closes the derived crystal-habit mesh feature only. The
original exceptional-forsterite milestone, its status, products, and
acceptance criteria are unchanged.
