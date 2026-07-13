# Richer Detector and Acquisition Model

- Status: Incubating
- Boundary: explicit instrument-response evidence, not cosmetic realism

## Motivation

The current detector projection and background correction capture the geometry
and a restrained acquisition-like appearance, but real EBSD systems also
contain point-spread, gain, offset, distortion, noise, saturation, binning, and
energy-response effects. Modeling selected effects could improve realism and
help processing research if each effect is calibrated or clearly labeled as a
synthetic experiment.

## Current evidence

- `DetectorRecipe` and the kikuchipy adapter explicitly retain shape,
  fractional PC convention, sample and detector rotations, pixel size,
  binning, and supersampling ([KIKU-T004](../work/KIKU-T004.md)).
- The processing graph names background correction, local contrast, detail,
  tone mapping, and downsampling while retaining intermediates and warnings
  ([KIKU-T005](../work/KIKU-T005.md)).
- The final recipe uses one shared acquisition correction before the scientific
  and gallery branches, with no claim that it is a calibrated detector response
  ([KIKU-T010](../work/KIKU-T010.md)).

## Dependencies

- Real acquisition metadata or a controlled calibration dataset with known
  detector settings and redistribution terms.
- Separate contracts for physical response, stochastic acquisition, and
  display processing.
- Seeded stochastic components and identity rules when noise is introduced.

## Unresolved questions

- Which response terms materially improve the target appearance or scientific
  comparisons at the available evidence quality?
- Which effects belong before projection integration, after ideal projection,
  or only in display processing?
- How should calibration uncertainty and vendor-specific conventions be
  retained in bundles?

## Linked decisions and experiments

- [ADR 0001](../decisions/0001-artifact-identity-and-bundle-layout.md) defines
  the current acquisition-corrected boundary and immutable graph lineage.
- [ADR 0003](../decisions/0003-clarity-aesthetic-target.md) separates
  acquisition-like scientific continuity from gallery presentation.
- The [final recipe](../../recipes/gallery/forsterite-final.yml) is the current
  explicit but deliberately limited acquisition model.

## Promotion trigger

Promote when one detector-response term is supported by calibrated or controlled evidence and can be isolated from display processing in a reproducible experiment.

## Present non-goals

- Inventing vendor-specific response parameters for visual plausibility.
- Folding noise, distortion, or point-spread into an opaque realism preset.
- Treating gallery enhancement as detector physics.
- Requiring richer acquisition modeling for the first milestone.
