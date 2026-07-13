# ADR 0002: Forsterite Proof Candidate Set

- Status: Accepted
- Date: 2026-07-13
- Work item: [KIKU-T007](../work/KIKU-T007.md)
- Recipe: [forsterite-candidates.yml](../../recipes/proof/forsterite-candidates.yml)

## Context

The first proof comparison needs enough orientation variety to make an
informed visual choice without turning the milestone into an orientation-space
survey. Forsterite is orthorhombic `Pnma` (No. 62) with point group `mmm`, so
different Bunge triples can describe crystal-symmetry-equivalent physical
orientations. Retaining such duplicates would spend rendering time on the same
view and could make a visual selection appear more strongly supported than it
is.

The public project convention is an active crystal-to-sample rotation expressed
as Bunge ZXZ Euler angles in degrees. Sample axes remain fixed in EDAX-TSL
`[RD, TD, ND]` order. Reduction must preserve that convention at the project
boundary even though orix represents orientations using its passive
sample-to-crystal convention.

## Decision

The accepted recipe contains twelve explicitly ordered candidates. The suffix
of each ID reports the explicit first Bunge Euler angle (`phi1`), not a derived
roll angle:

1. `[001]` at `phi1 = 0` and `35` degrees;
2. `[100]` at `phi1 = 180` and `220` degrees;
3. `[010]` at `phi1 = 15` and `55` degrees; and
4. `[110]`, `[101]`, `[011]`, `[111]`, `[210]`, and `[012]` at `phi1 = 100`,
   `205`, `45`, `90`, `120`, and `60` degrees respectively.

The square-bracket labels are direct-lattice direction indices `[uvw]`, not
plane indices `(hkl)`. Zone directions are metric-aware using the verified
standard-Pnma simulation cell lengths `a = 10.207`, `b = 5.980`, and
`c = 4.756` angstrom. These are intentionally in the repository's transformed
Pnma axis order, not the differently ordered source-Pbnm CIF axes; `a` is the
longest, `b` is intermediate, and `c` is the shortest axis. The complete Euler
triple, rather than `phi1` alone, centers each stated direction on sample ND.
Executable tests verify the rounded explicit triples retain that alignment
within `1e-6` degrees.

`bunge_phi1_deg` exactly duplicates the first value of each Bunge triple so its
meaning can be inspected without parsing an array. It is a reproducible
in-plane composition choice, not an absolute roll measured from a generated
zone-axis zero frame; this task neither defines nor claims such a zero frame.
Every candidate records both its zone-axis intent and a visual composition
hypothesis. Those hypotheses guide comparison but do not assert which
orientation will produce the final artwork.

Symmetry reduction is contained in the orientation helper. It converts each
project-owned active crystal-to-sample `Orientation` to the inverse passive
sample-to-crystal orix orientation, assigns orix `D2h` (`mmm`) crystal
symmetry, and uses orix disorientation. In that passive representation,
crystal symmetry acts on the left and the sample frame remains fixed. No sample
symmetry is introduced. A regression test demonstrates both sides of this
boundary: a crystal twofold-equivalent representation reduces to zero while a
one-degree sample-frame rotation remains one degree.

The recipe convention string is an executable enum: it must exactly state
active crystal-to-sample Bunge ZXZ Euler angles in degrees with EDAX-TSL
`[RD, TD, ND]` sample axes. Passive, radians, or otherwise contradictory text
is rejected rather than retained as untrusted prose.

Two candidates are considered equivalent when their reduced disorientation is
at most `0.01` degrees. The loader rejects a set containing such a pair. For
the accepted recipe, all 66 unordered pairs pass; the closest pair is
`fo-110-phi1-100` versus `fo-111-phi1-090` at approximately `24.0515`
degrees. Stable recipe order, explicit candidate IDs, content-derived
orientation IDs, and the content-derived candidate-set ID make the exact
comparison set serializable and reproducible. The accepted set ID is
`candidate-set-770010a96a2dbf3e`. This exact identity is pinned by an
executable regression test and in this decision record.

The candidate set owns an immutable tuple copied from its constructor input,
and every member must be an `OrientationCandidate`; later mutation of a caller's
list therefore cannot change set length or identity. Identity retains the
scientific `[uvw]` indices but excludes the derived `zone_axis_label` display
string. Display serialization still includes that label, and a regression test
proves that changing only its formatting leaves the set ID unchanged.

Schema parsing is strict rather than coercive. `schema_version` is the actual
non-boolean integer `1`. Euler angles, `bunge_phi1_deg`, lattice lengths, and
the equivalence tolerance must be finite YAML numeric scalars, while `[uvw]`
entries must be actual integer scalars. Booleans, numeric strings, nulls, and
non-finite values are rejected with field-specific errors. Top-level and
nested mapping and sequence shapes are checked before access or iteration.

This is deliberately a bounded, non-exhaustive proof set. It is not a uniform
SO(3) sample, an inverse-pole-figure fundamental-zone grid, an optimization
result, or evidence that untested orientations are inferior. Schema v1
requires `exhaustive` to be the actual YAML boolean `false`; true, string, and
numeric substitutes are rejected. Phase-general sampling and denser local
exploration belong after the first proof comparison.

## Consequences

- Task 8 can render one deterministic order without importing orix types into
  its workflow contract.
- Every displayed candidate has a documented scientific and compositional
  reason for inclusion.
- Changing an angle, intent, lattice metric, order, or tolerance changes the
  candidate-set identity.
- Changing only derived zone-axis label punctuation does not change scientific
  identity.
- The final orientation choice remains a separate human decision with its own
  evidence; this ADR only accepts the comparison population.
- Future phase-general work must choose and document its own symmetry and
  sampling strategy rather than treating this bounded set as exhaustive.
