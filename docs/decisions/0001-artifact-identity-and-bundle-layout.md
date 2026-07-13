# ADR 0001: Artifact Identity and Bundle Layout

- Status: Accepted
- Date: 2026-07-12
- Work item: [KIKU-T006](../work/KIKU-T006.md)

## Context

The first forsterite milestone needs scientific float products, display-ready
images, provenance, diagnostics, and human decisions to remain connected. A
directory assembled incrementally in place could silently mix two runs. A run
name derived from elapsed time would be irreproducible, while a run name that
ignored scientific inputs could collide. High-bit-depth exports also need an
auditable mapping back to the float product from which they were quantized.

## Decision

Each run is written to a same-root `<run-id>.partial` directory and published
with one directory rename only after all payload files and the manifest have
been flushed. A completed `<run-id>` is immutable and never overwritten. A
stale partial is also preserved by default. Explicit recovery first renames it
to `<run-id>.partial.<UTC timestamp>.abandoned`, retaining the interrupted
evidence, and only then starts a new partial.

The run ID is canonical-JSON/SHA-256 derived from source, recipe, software,
master-pattern, orientation, decision-link, and named float-product identities.
Wall-clock timestamps, elapsed/resource measurements, hardware observations,
and absolute local paths are evidence but do not affect run identity.

The bundle retains float32 NPY files for the projected pattern, the named
acquisition-corrected pattern, every processing stage, and both final products.
The acquisition-corrected name specifically means background-model correction
before aesthetic local contrast or detail enhancement. Processing stages and
final products additionally receive grayscale uint16 exports; the gallery and
scientific products receive both TIFF and PNG. Every uint16 file has a manifest
record containing its source float-product ID, scale, offset, black and white
points, and measured low/high clipping fractions. The preview is the only
uint8 scientific-image derivative.

`manifest.json` is canonical JSON and inventories the byte length and SHA-256
of every other file. It cannot inventory itself without recursion, so callers
receive its checksum separately. The manifest declares the comparison
exclusion schema: timestamp fields, elapsed/resource evidence, absolute local
paths, and the externally reported manifest checksum. Comparison tools should
not embed additional ad hoc exclusions in test or application code.

## Consequences

- A completed bundle cannot contain files from two attempts.
- Interrupted evidence survives unless a person explicitly requests recovery.
- Scientific comparisons can use float products and explicit exclusions,
  independent of display quantization and machine timing.
- Bundle consumers must verify the externally supplied manifest checksum before
  trusting the internal inventory.
- Any future layout or identity change requires a manifest schema-version
  change and a new decision record.
