# Kikuchi Atlas consolidation and Google mirror acceptance

Date: 2026-07-26

## Accepted outcome

The Atlas has one canonical local package tree, a live browser-safe GitHub
Pages catalogue, a public full-resolution Google Drive folder mirror, and a
public Google Site catalogue. The accepted inventory is 12 phases and 125
products. Legacy publishable copies were moved only after all publication
gates passed, and the final cleanup remains recoverable from one recorded
macOS Trash namespace.

The separately reviewed archival release and DOI are not complete. This
record accepts the distribution mirrors; it does not accept an archival DOI
release.

## Canonical inventory

Canonical root:
`/Users/Z/Documents/kikuchi/local/atlas/phases/`

| Phase slug | Products |
| --- | ---: |
| `calcite` | 9 |
| `diamond` | 9 |
| `diopside` | 9 |
| `enstatite` | 9 |
| `forsterite` | 13 |
| `ice-ih` | 13 |
| `muscovite-2m1` | 9 |
| `plagioclase-an52` | 9 |
| `pyrope` | 9 |
| `quartz` | 13 |
| `titanite` | 12 |
| `zircon` | 11 |
| **Total** | **125** |

The canonical tree contains:

- 12 validated `phase-package.yml` manifests;
- 125 validated `product-package.yml` manifests;
- 660 regular files totaling 7,206,478,751 bytes;
- 523 migration-ledger payload records; and
- no canonical symlinks.

The final migration ledger is schema 2, state `cleaned`, and records the
original path, recoverable Trash path, byte count, SHA-256, timestamp, and
every validated canonical destination for each cleaned file.

Final migration-ledger identity:

```text
path: docs/atlas/ATLAS_MIGRATION.yml
bytes: 870743
SHA-256: bb28b4626e7853c050240bd198c93e1108a4f595b69b2e1a5e5b85762b6b905f
```

## Quartz artist masters

The three authoritative MOV files remain in their canonical product packages;
their browser proxies are separate artifacts.

| Product | Authoritative MOV SHA-256 | Web MP4 SHA-256 |
| --- | --- | --- |
| `quartz-direct-reflector-artist-master-x-axis` | `f64e56e0352b58c50b83d0d76b675283057b82f48369e1fe6cb210e445bd24a0` | `83f86404867bbd957e46c2851d02f7e560c3f67536aaa93ff14a264dfb5b5fe0` |
| `quartz-near-depth-artist-master-identity-60fps` | `8c45c5dc7c220ba80f21b7716205e1197c8e9137114baed26d0d54da796a7b5a` | `6c4c1ca80a455ceb88f9a8457762025c7d8acdec16479feb063ac0f2362d939b` |
| `quartz-near-depth-artist-master-oblique-17-31-43-60fps` | `e7b3ed4f9b18b2f11daf3267e65d3aab8c021a01e9b0289ff62d301dbab77ac2` | `0fbfe4db378a6a526d24c63ccab964516acf8f3fff7846429b1c9df7631b6447` |

The identity and oblique MP4s are deterministic generated proxies. The
direct-reflector MP4 is the separately copied viewing export recorded by its
package.

## GitHub release and Pages

- Repository: <https://github.com/zmichels/kikuchi-atlas>
- Live Pages: <https://zmichels.github.io/kikuchi-atlas/>
- Current link-complete prerelease:
  <https://github.com/zmichels/kikuchi-atlas/releases/tag/atlas-gallery-web-0.2.0-draft.3>

Release transport history:

| Tag | ZIP bytes | Pinned ZIP SHA-256 | Disposition |
| --- | ---: | --- | --- |
| `atlas-gallery-web-0.2.0-draft.1` | 282,027,884 | `229f4f7263748b27c601e985b86d2f6f52f93455e693877129ab601e724762f6` | retained superseded transport |
| `atlas-gallery-web-0.2.0-draft.2` | 282,047,003 | `d32d21494ae2b9b078d3e59dee7dd241c8474914ade76db7226cbb410875a514` | first accepted 125-product Pages deployment |
| `atlas-gallery-web-0.2.0-draft.3` | 282,060,871 | `214f49f383596a42301f8d9ef05304f792f70bc929c4238a90f100ec891d16c3` | current public-link-complete deployment |

Successful protected-environment observations:

- draft.2: workflow run `30193991683`, deployment `5608463646`;
- draft.3: workflow run `30221943796`, job `89845771696`, deployment
  `5614404611`, from `master` at
  `926995cce62fe2ded59e61b27735316fea4d3ecb`; and
- both terminal workflow and deployment conclusions were `success`.

Cookie-free draft.3 verification found the exact live index and all 12 phase
pages, 12 phases, 125 products, 212 web assets totaling 286,371,069 bytes,
125 exact unique public Drive package links, and no local path, wrong-account,
archive, or authoritative source-path leakage.

## UMN Google Drive and Google Site

- Account: `zmichels@umn.edu`
- Transport: Chrome folder upload
- Public Drive root:
  <https://drive.google.com/drive/folders/1aUvGSjpQsGqyAlmLcS_vafcHQ6jVciZ4>
- Public Google Site:
  <https://sites.google.com/umn.edu/kikuchi-atlas-publishing-test>

Quota observation at `2026-07-26T08:33:38.368Z`:

```text
total:             100,000,000,000 bytes
used:                7,820,000,000 bytes
free:               92,180,000,000 bytes
canonical upload:    7,206,478,751 bytes
required reserve:   10,737,418,240 bytes
post-upload headroom gate: passed
```

The observed upload queue reported `1212/1212`, `1 upload complete`, and no
failure signal. Folder reconciliation found one root, 12 phase folders, 125
product folders, zero missing identities, zero duplicate Drive IDs, and zero
duplicate URLs.

The user explicitly waived phase-archive downloads after the browser download
path was blocked. Accordingly:

- downloaded phase archives: 0;
- full package files compared by round-trip SHA-256: 0;
- disposition: `waived-by-user` at `2026-07-26T18:50:51Z`; and
- no per-product Drive package digest or `verified_at` claim is made.

This waiver was about verifying the uploaded Drive bytes, not recovering
missing local data; all canonical data already existed locally.

Cookie-free public checks recorded:

- Drive: 1 root, 12 phase folders, and 125 product folders; 138/138 HTTP 200
  with exact identities and inventory markers; zero denied signals;
- Site: 14/14 pages HTTP 200 with 12 exact phase targets;
- GitHub phase pages: 12/12 HTTP 200; and
- seven bounded-memory representative downloads with exact observed byte count
  and SHA-256: PNG, SVG, MP4, MOV, STL, YML, and NPZ. No temporary download was
  retained.

## Recoverable legacy cleanup

Final accepted cleanup:

```text
files moved: 347
bytes moved: 7,129,461,220
Trash namespace:
/Users/Z/.Trash/Kikuchi Atlas legacy cleanup 20260726T220756510434Z-e73a00517a38
```

Each move was an exact same-volume file rename into a collision-safe batch
tree. No legacy root was recursively deleted. The source and every canonical
destination were checked against the frozen ledger before the first move,
including both generated MP4 destinations that share their authoritative
quartz MOV source.
The Trash write/rename/restore preflight passed, and the final ledger is the
recovery journal.

All ten legacy roots remain as directories. All 12 explicitly retained source
paths remain. All 18 copied payloads below those retained bundles, totaling
742,176 bytes, exist at their original paths with exact planned hashes, as do
the unlisted intermediates, including 6,367 frame files observed immediately
after the initial move.

An initial dry run identified 365 candidates / 7,130,203,396 bytes. The first
full-suite run exposed one over-broad classification: the 2,443-byte pyrope
standard-template `manifest.json` was also required identity evidence for the
retained direct-reflector source bundle. That exact file, SHA-256
`309ba1d0689c29e62a38f84a1e6e148180ffa2afe3803dd47bf638c0e14c5d7d`,
was restored from its recorded Trash path; its ledger approval is now false,
and the final cleanup totals and journal exclude it.

Independent review then found that `retained_source_paths` names whole bundles,
not only exact directory markers. Exactly 17 additional journaled descendants
totaling 739,733 bytes were restored after their Trash identities were
verified. Their approvals are false and the final journal contains zero
retained-bundle descendants. Across both corrections, exactly 18 files /
742,176 bytes were restored and no other file was restored.

The cleanup implementation now groups all entries by exact source before
filtering. Copied records explicitly authorize cleanup; generated proxies
remain `cleanup_approved: false`, but every destination in the shared-source
group must validate and appear in the recovery journal. Cleanup also refuses
unless Git proves the exact worktree top-level and tracked inventory. Any
mid-move or ledger-publication failure rolls all moved files back, removes the
empty Trash batch and staging file, and proves the original ledger bytes are
unchanged.

## Post-cleanup verification

After the cleanup and exact correction:

- canonical verification: 12 phases, 125 products, 0 missing, 0 mismatched,
  0 symlinks;
- local Atlas build: 12 phases and 125 individual products;
- public build: 212 web assets / 286,371,069 bytes and 617 staged archive
  assets / 7,169,121,139 bytes;
- focused Atlas suite: 164 passed;
- consolidation unit suite: 57 passed;
- corrected cleanup/retained-bundle/shared-journal slice: 17 passed;
- work-item validation: 119 records valid;
- required Ruff scope: clean; and
- `git diff --check`: clean.

Fresh repository-wide result after the exact correction:

```text
1 failed, 1,701 passed, 1 skipped, 4,383 warnings in 587.40s
```

The remaining expected failure is outside this cleanup scope:
`tests/adapters/test_kikuchipy_kinematical.py::test_adapter_context_keeps_upstream_products_private_and_complete`.
Its assertion expects reflector-catalog keys exactly `master` and `overlays`;
the current adapter also carries the required `catalog_id` and
`source_structure_id` identity fields. A clean pre-cutover baseline reproduced
the same assertion failure. This record does not describe the full suite as
passing.

## Deviations and decisions

- Full Google Drive round-trip downloads were replaced by the user's explicit
  upload-only acceptance. Folder identities and logged-out public access are
  verified; cloud byte equality for every package is not claimed.
- No remote deduplication was accepted without downloaded-byte evidence.
  Existing remote quartz items were candidates only; no item was merged,
  overwritten, or called identical on filename or displayed-size evidence.
- The pyrope retained-source manifest and all 17 other copied descendants of
  retained bundles were restored and excluded from cleanup. The correction
  narrowed cleanup; it did not restore a legacy publication fallback.
- The earlier draft.1 workflow dispatch was blocked by the protected
  deployment branch policy. Later reviewed master deployments succeeded;
  existing tags/releases were retained rather than overwritten.

## Nonclaims

- Google Sites and My Drive are convenient public distribution mirrors, not a
  permanent research archive, CDN, or preservation guarantee.
- Public accessibility does not guarantee unlimited traffic or permanent URL
  stability.
- Browser-playable proxies are not the authoritative artist masters.
- A remote filename or displayed size is not proof of artifact identity.
- The Drive folder checks and representative file checks are not a complete
  per-product round-trip hash verification.
- The consolidation does not expand scientific scope, add new phases, imply
  that one structural reference represents an entire mineral group, or turn
  modeled products into acquired EBSD patterns, camera-calibrated detector
  simulations, or a validated dictionary-indexing dataset.
- Original third-party source payloads are not republished unless their
  individual rights and attribution permit it.
- Successful STL mesh checks are not physical-print, fit, metrology, or
  mechanical-performance validation.

## Remaining archival gate

`docs/atlas/RELEASE_METADATA.yml` retains:

```yaml
archive_doi: null
remaining_gate: assign a stable release version and publish the separately
  reviewed archive package with a DOI
```

The public gallery and mirrors are accepted. KIKU-F012 remains active until
that distinct archival DOI gate is resolved.
