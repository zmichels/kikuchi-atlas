# Atlas public-verification ledger design

Date: 2026-07-26

## Scope

Record the already observed public publication of the Kikuchi Atlas Google
Drive mirror and Google Site without weakening the Task 8 evidence boundary.
The implementation must preserve the user-waived, not-performed full Drive
round trip byte-for-byte. Public verification means that all recorded folders
and pages were accessible without authentication and that seven specifically
identified representative files matched their canonical manifests; it does
not mean that every cloud byte was downloaded or compared.

No legacy cleanup, file move, Drive deletion, permission expansion beyond the
approved public Viewer access, or Task 10 Pages rebuild is in scope.

## Selected approach

Promote the mirror ledger to schema version 3 and embed one immutable
`public_verification` block. Add an atomic, idempotent
`record-public-verified` CLI command that accepts the complete observation as
JSON, validates it against the current ledger and canonical product manifests,
and performs the terminal state transition only after every invariant passes.

Embedding the evidence keeps the state and its proof inseparable. A separate
evidence file was rejected because the terminal ledger could outlive or drift
from its justification. Manual YAML mutation was rejected because it would not
fail closed or preserve a reproducible transition.

## Public-verification evidence

The immutable block records:

- UTC observation time and `cookie-free-http` transport;
- exact public Site and Drive root URLs;
- Site access counts: 14 pages checked, 14 HTTP 200 responses, 14 exact final
  URLs, and 12 phase pages with the exact GitHub and Drive targets;
- GitHub access counts: 12 pages checked, 12 HTTP 200 responses, 12 exact final
  URLs, and 12 registry display names observed;
- Drive access counts: 1 root, 12 phase folders, and 125 product folders;
  138 HTTP 200 responses, 138 exact final URLs, 138 expected identities, 138
  expected inventory markers, and zero denied signals;
- exactly seven representative records covering PNG, SVG, MP4, MOV, STL, YAML,
  and NPZ;
- for each representative: product ID, canonical relative path, exact public
  download URL, HTTP status, content type, content disposition, observed byte
  count, observed SHA-256, and canonical expected byte count/SHA-256;
- zero public-access exceptions and zero retained temporary files;
- an explicit statement that streaming used bounded memory chunks and retained
  no duplicate downloads.

## Fail-closed transition

`record-public-verified` accepts only a schema-2 `uploaded-private` ledger whose
root, 12 phases, and 125 products already have exact opaque Drive identities.
It must:

1. Revalidate the complete Task 8 `upload_acceptance` block and retain it
   unchanged, including `round_trip_verification.status: not-performed` and
   `disposition: waived-by-user`.
2. Require the exact recorded Drive root URL and exact proposed Site public
   URL in the observation.
3. Require the exact Site, GitHub, and Drive counts above, with no exceptions
   or denied signals.
4. Require exactly one representative for each of the seven file kinds.
5. Resolve each representative to an existing ledger product and canonical
   `product-package.yml` file record. Observed and expected byte counts and
   SHA-256 values must equal the canonical manifest.
6. Require HTTP 200, an exact final download URL, a non-empty content type and
   disposition, bounded-memory streaming, and zero retained temporary files
   for every representative.
7. Reject replacement of any terminal public-verification evidence. Repeating
   the identical command is idempotent.

Only after validation succeeds does one atomic write:

- set schema version 3 and store `public_verification`;
- set root, all phases, and all products to `access: public-link` and
  `state: public-verified`;
- leave product manifest digest/`verified_at` fields null because they refer to
  the waived complete round trip, not public accessibility;
- set the Site audience to `public` and state to `public-verified`;
- preserve every Drive ID, Drive URL, quota field, and Task 8 acceptance field.

## Validation and publication contract

Loading a schema-3 public ledger recomputes the same invariants. The existing
`validate --require-state public-verified` command must additionally require:

- 12 public-verified phases and 125 public-verified products;
- 125 exposed public product URLs;
- Site audience/state `public`/`public-verified`;
- a valid immutable `public_verification` block;
- the unchanged Task 8 waived-round-trip nonclaim.

After the transition, regenerate `local/atlas/atlas-mirror.yml` from the exact
validated public ledger. In signed-in Drive, use Manage versions on the
existing root manifest to upload it as a new version, preserving the prior
version and one logical `atlas-mirror.yml` item. Verify the public file reflects
the new ledger and that the prior version remains available.

## Testing

Test-driven coverage begins with a failing CLI test. The green suite covers:

- exact public promotion and 125 public URLs;
- idempotent replay;
- wrong Site/root URL;
- non-cookie-free transport;
- wrong page/folder counts or denied/exception signals;
- missing, duplicate, or extra representative kinds;
- unknown product/path;
- manifest byte or SHA mismatch;
- non-200 status, empty content metadata, non-exact final URL;
- retained temporary files or non-bounded streaming;
- Task 8 waiver mutation;
- terminal evidence replacement;
- atomic failure with no partial ledger write.

Focused mirror/publication tests, Ruff, generated-source checks, public-state
validation, and `git diff --check` must pass before the feature branch is
pushed and draft PR 5 is opened for independent review.
