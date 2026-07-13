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

The run ID is canonical-JSON/SHA-256 derived through a versioned, explicit
whitelist. Version 2 includes source ID and checksum; master product ID and
array checksum; every resolved recipe ID and checksum; projection geometry ID;
software package versions and optional distribution checksums; candidate-set,
orientation-decision, and recognized decision-link IDs; separately ordered
scientific and gallery branch stage names and input/output content IDs; and
every named float product's product ID, content ID, and array checksum. No other
provenance dictionary value participates implicitly. Wall-clock, retrieval,
and generation times,
elapsed/resource measurements, hardware observations, and absolute or relative
local paths remain evidence regardless of their nesting or field names.
The normalized whitelist payload is embedded in the manifest, so consumers can
independently recompute the run ID instead of trusting an opaque implementation.

The bundle retains float32 NPY files for the projected pattern, the named
acquisition-corrected pattern, every processing stage, and both final products.
The acquisition-corrected name specifically means background-model correction
before aesthetic local contrast or detail enhancement. Processing stages and
final products additionally receive grayscale uint16 exports; the gallery and
scientific products receive both TIFF and PNG. Every uint16 file has a manifest
record containing its source float-product ID, scale, offset, black and white
points, and measured low/high clipping fractions. The preview is the only
uint8 scientific-image derivative.

That acquisition-corrected semantic is executable, not descriptive. The
bundle requires separate continuous scientific-clean and gallery-crisp branches
beginning at the same projected image content ID. Both branches must share an
identical first background-correction record whose output ID equals the
acquisition-corrected float array's computed content ID. They may diverge only
after that shared node. Each ordered branch must terminate at its corresponding
final float product's computed content ID, and every exported intermediate must
occur in at least one branch. Missing, reordered, disconnected, divergent, or
unrelated products are rejected before a partial directory is created.

Radial-frequency diagnostics are measured in physical cycles per pixel using
the independent FFT frequency coordinates of each image axis. The version 1
bands are low `[0, 0.15)`, mid `[0.15, 0.35)`, and high `[0.35, infinity)`
cycles per pixel. Consequently, classification does not vary with rectangular
aspect ratio or axis direction.

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
- Run-identity evolution is deliberate: adding a scientific identity field
  requires a schema-version change rather than a fragile exclusion-key patch.
- Acquisition-corrected or final branch products cannot be substituted without
  breaking the recorded computational graph.
- Bundle consumers must verify the externally supplied manifest checksum before
  trusting the internal inventory.
- Any future layout or identity change requires a manifest schema-version
  change and a new decision record.
