# Atlas Public Verification Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the fully observed public Atlas publication in an immutable, fail-closed schema-v3 ledger without converting the waived full Drive round trip into a cloud-byte verification claim.

**Architecture:** Extend the existing local mirror contract with a validated `public_verification` evidence block and one atomic `record_public_verification()` transition. The CLI consumes the actual observation JSON, recomputes counts and canonical representative-file matches, preserves Task 8 acceptance byte-for-byte, and changes public states only after validation succeeds.

**Tech Stack:** Python 3.12, PyYAML, existing `kikuchi_lab.atlas.mirror` atomic-write helpers, argparse CLI, pytest, Ruff, authenticated Chrome for the final Drive manifest version upload.

## Global Constraints

- Preserve `round_trip_verification.status: not-performed` and `disposition: waived-by-user` unchanged.
- Public verification proves all recorded public folders/pages plus seven exact representative files only; it does not prove complete cloud-byte equality.
- Require exactly 14 Site pages, 12 GitHub pages, 1 root + 12 phase + 125 product Drive folders, seven required file kinds, zero exceptions, and zero retained temporary files.
- Keep all existing opaque Drive IDs and URLs unchanged.
- Do not delete, move, or duplicate Drive content; upload the regenerated manifest as a new version of the existing file.
- Do not perform legacy cleanup or Task 10 Pages work.

---

### Task 1: Schema-v3 immutable evidence contract

**Files:**
- Modify: `src/kikuchi_lab/atlas/mirror.py`
- Test: `tests/unit/test_atlas_mirror.py`

**Interfaces:**
- Consumes: schema-2 uploaded-private ledger and a `Mapping[str, object]` observation.
- Produces: `MirrorLedger.public_verification: Mapping[str, object] | None` and `_validate_public_verification(value, ledger_context)`.

- [ ] **Step 1: Add a failing schema-v3 loader test**

Construct a public-verification fixture with exact Site/GitHub/Drive counts and seven representative records. Assert that a schema-v3 public ledger loads, exposes immutable evidence, and retains the Task 8 waiver. Assert failures for wrong counts, duplicate kinds, retained temp files, non-cookie-free transport, URL mismatch, and a representative SHA mismatch.

- [ ] **Step 2: Run the focused loader test and confirm RED**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_mirror.py::test_schema_v3_public_verification_is_fail_closed
```

Expected: failure because schema version 3 and `public_verification` are unsupported.

- [ ] **Step 3: Implement minimal schema-v3 parsing**

Add:

```python
@dataclass(frozen=True)
class MirrorLedger:
    ...
    public_verification: Mapping[str, object] | None
```

Extend exact schema fields only for version 3. Validate the observation shape, exact counts, exact public Site/root URLs, unique required representative kinds, HTTP/final-URL/content metadata, bounded-memory/zero-temp assertions, and canonical product-package bytes/SHA. Recompute public terminal invariants on every load.

- [ ] **Step 4: Run loader tests and confirm GREEN**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_mirror.py::test_schema_v3_public_verification_is_fail_closed
uv run pytest -q tests/unit/test_atlas_mirror.py
```

Expected: both commands pass.

### Task 2: Atomic public-verification transition and CLI

**Files:**
- Modify: `src/kikuchi_lab/atlas/mirror.py`
- Modify: `src/kikuchi_lab/atlas/__init__.py`
- Modify: `scripts/atlas_google_mirror.py`
- Test: `tests/unit/test_atlas_mirror.py`

**Interfaces:**
- Consumes: `record_public_verification(mirror_path, verification)`.
- Produces: an idempotent schema-v3 ledger with root/phases/products `public-link`/`public-verified`, Site `public`/`public-verified`, unchanged identities and Task 8 acceptance.

- [ ] **Step 1: Add a failing CLI transition test**

Run the command:

```text
record-public-verified --mirror <path> --verification-json <json>
```

Assert exact promotion, 125 `public_product_urls()`, null per-product digest/verified-at fields, unchanged Task 8 acceptance, idempotent replay, collision rejection, and no partial write after invalid evidence.

- [ ] **Step 2: Run the CLI test and confirm RED**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_mirror.py::test_cli_records_public_verification_without_overclaim
```

Expected: failure because the command does not exist.

- [ ] **Step 3: Implement the transition**

Implement one candidate mapping in memory:

```python
raw["schema_version"] = 3
raw["public_verification"] = normalized
raw["root"]["access"] = "public-link"
raw["root"]["state"] = "public-verified"
raw["site"]["audience"] = "public"
raw["site"]["state"] = "public-verified"
```

Set every phase/product access and state to public-link/public-verified while leaving product digest and verification timestamp fields unchanged. Validate the candidate before atomic replacement. If already terminal, return only for byte-equivalent evidence.

- [ ] **Step 4: Add and export the CLI command**

Expose `record_public_verification` from `kikuchi_lab.atlas`. Add argparse command `record-public-verified` with required mirror and JSON observation arguments. Print exact counts, representative count, Site state, and retained Task 8 round-trip disposition.

- [ ] **Step 5: Run focused and complete mirror tests**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_mirror.py::test_cli_records_public_verification_without_overclaim
uv run pytest -q tests/unit/test_atlas_mirror.py tests/unit/test_atlas_publication.py
```

Expected: all pass.

### Task 3: Record the observed publication and update the Drive manifest version

**Files:**
- Modify: `docs/atlas/GOOGLE_MIRROR.yml`
- Regenerate: `local/atlas/atlas-mirror.yml`
- Regenerate: `dist/google-site/`
- Modify locally: `.superpowers/sdd/task-9-report.md`

**Interfaces:**
- Consumes: the exact cookie-free observations and seven representative records from Task 9.
- Produces: validated public ledger and one new version of the existing Drive `atlas-mirror.yml`.

- [ ] **Step 1: Invoke the CLI with the exact observation**

Pass the observed UTC time, exact Site/root URLs, exact 14/12/138 counts, zero exceptions/temp files, and these required kinds:

```text
png svg mp4 mov stl yml npz
```

- [ ] **Step 2: Validate and export**

Run:

```bash
uv run python scripts/atlas_google_mirror.py validate \
  --mirror docs/atlas/GOOGLE_MIRROR.yml \
  --require-state public-verified
uv run python scripts/atlas_google_mirror.py export-local \
  --mirror docs/atlas/GOOGLE_MIRROR.yml \
  --output local/atlas/atlas-mirror.yml \
  --require-state public-verified
```

Expected: 12 phases, 125 products, 125 public product URLs, Site public-verified, and the waiver suffix unchanged.

- [ ] **Step 3: Upload a new Drive version**

In signed-in Chrome, select the existing root `atlas-mirror.yml`, open Manage versions, and upload the regenerated local file as a new version. Do not delete the previous version or create a second logical file.

- [ ] **Step 4: Verify the version and public bytes**

Confirm one logical root manifest, at least two versions, current content equals the regenerated ledger, and cookie-free public download succeeds. Record screenshot and exact manifest SHA.

- [ ] **Step 5: Append the Task 9 report**

Record permission UI, inheritance counts, Site publication, all cookie-free page/folder counts, seven representative URLs/status/content types/bytes/SHA values, zero exceptions, zero retained temp files, manifest version evidence, and the full-round-trip nonclaim.

### Task 4: Final verification and PR 5

**Files:**
- All changed source, tests, ledger, spec, and plan files.

**Interfaces:**
- Consumes: completed Tasks 1–3.
- Produces: pushed feature branch and draft PR 5 for independent review.

- [ ] **Step 1: Run formatting and lint**

```bash
uv run ruff format --check src/kikuchi_lab/atlas/mirror.py src/kikuchi_lab/atlas/__init__.py scripts/atlas_google_mirror.py tests/unit/test_atlas_mirror.py
uv run ruff check src/kikuchi_lab/atlas/mirror.py src/kikuchi_lab/atlas/__init__.py scripts/atlas_google_mirror.py tests/unit/test_atlas_mirror.py
```

- [ ] **Step 2: Run focused tests and public validation**

```bash
uv run pytest -q tests/unit/test_atlas_mirror.py tests/unit/test_atlas_publication.py
uv run python scripts/atlas_google_mirror.py validate --mirror docs/atlas/GOOGLE_MIRROR.yml --require-state public-verified
git diff --check
```

- [ ] **Step 3: Inspect and commit only scoped files**

Commit implementation and evidence as:

```text
atlas: record public Google mirror verification
```

- [ ] **Step 4: Push and open draft PR 5**

Push `codex/atlas-consolidation-google-mirror` and open a draft PR against `master`. Do not merge it.
