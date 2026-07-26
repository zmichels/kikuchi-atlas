# Kikuchi Atlas Consolidation and Google Mirror Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate every publishable Atlas artifact into 12 phase-slugged package trees, register the three completed quartz artist-master products for a 125-product Atlas, refresh GitHub Pages, and publish a verified full-resolution UMN Google Drive/Sites mirror.

**Architecture:** A strict package-manifest and migration-ledger layer sits between the curated registries and ignored binary products. The cutover copies and hashes first, switches the registries only after all 125 canonical packages validate, publishes the browser-safe catalogue separately from full-resolution Drive payloads, and deletes only ledger-approved legacy files after both public surfaces pass logged-out verification.

**Tech Stack:** Python 3.12, PyYAML, pathlib, hashlib, mimetypes, ffmpeg/ffprobe, pytest, Ruff, Git/GitHub CLI and Actions, macOS APFS clone-copy support, signed-in Chrome, Google Drive for Desktop or browser upload, Google Drive, Google Sites.

## Global Constraints

- Preserve all 12 existing Atlas phases and all 122 existing Atlas product IDs.
- Add exactly three completed quartz artist-master products; the accepted target is exactly 12 phases and 125 available products.
- Keep the five-phase orientation gallery as review evidence, not an individual Atlas product.
- Do not resume grossular, almandine, tremolite, or any other paused phase-expansion work.
- The canonical generated-product root is exactly `/Users/Z/Documents/kikuchi/local/atlas/phases/`.
- Every product package is `local/atlas/phases/<phase-slug>/products/<product-id>/` with `product-package.yml`, `media/`, `previews/`, `web/`, and `provenance/`.
- Tracked structural sources remain under `phases/<slug>/`; do not copy original third-party CIF payloads into the public product mirror unless their individual copying policy explicitly permits it.
- Treat artist-master MOV files and printable STL files as authoritative media. A browser proxy is a derived delivery file, not a replacement for authoritative media.
- Package manifests contain only repository-relative or package-relative paths. They may not contain `/Users/`, `/tmp/`, `file://`, symlinks, or hard links.
- Populate canonical packages with APFS clone copies when supported and ordinary copies otherwise. Never overwrite a same-name/different-byte destination.
- Record byte count, SHA-256, MIME type, role, source commit, registry identity, and intended destinations for every packaged file.
- Keep mutable Drive IDs and public URLs in `docs/atlas/GOOGLE_MIRROR.yml`, separate from scientific package identity.
- Never use `/Users/Z/Library/CloudStorage/GoogleDrive-mich0201@umn.edu` for this publication. The only approved account is `zmichels@umn.edu`.
- Stop before Drive upload if the canonical payload plus 10 GiB exceeds the currently reported free space. Re-read the live quota at upload time; do not rely only on the earlier 92.18 GB observation.
- Existing remote quartz files are deduplication candidates only after a byte-count and checksum or downloaded-byte match.
- Keep GitHub Pages as the fast browser catalogue and Google Drive as the full-resolution payload mirror. Google Sites is a landing/index mirror, not a replacement application or preservation archive.
- Do not change Drive access to public, change the Google Site audience to Public, or press the final Google Sites Publish control without a fresh action-time user confirmation.
- Do not remove a legacy publishable file until the canonical tree, 125-product local build, GitHub Pages, Drive mirror, Google Site, and checksums all pass.
- Delete only exact `cleanup_approved: true` source files from the migration ledger. Preserve nonpublishable intermediates and historical plans/specifications.
- Historical specifications and plans keep their historical paths. Update current registries, runtime docs, acceptance records, release docs, scripts, and tests only.
- A current script may retain a legacy-root path only when `docs/atlas/LEGACY_PATH_AUDIT.yml` classifies it as a nonpublishable scientific input or historical reproduction reference; no Atlas build may use it as a published-product fallback.
- Preserve unrelated dirty worktree changes. Each commit stages only the files named in its task.

---

## File and Responsibility Map

### New package and cutover core

- `src/kikuchi_lab/atlas/packages.py`: immutable package-file, product-package, phase-package, and validation contracts.
- `src/kikuchi_lab/atlas/consolidation.py`: deterministic migration planning, safe clone/copy materialization, registry rewriting, verification, and cleanup gating.
- `src/kikuchi_lab/atlas/mirror.py`: Drive mirror ledger, public-link validation, downloaded-mirror reconciliation, and Google Sites page inventory.
- `src/kikuchi_lab/atlas/web_proxy.py`: deterministic ffmpeg proxy profile and ffprobe validation for heavyweight motion products.
- `src/kikuchi_lab/atlas/__init__.py`: exports the new public seams.

### New command surfaces

- `scripts/consolidate_atlas_products.py`: `plan`, `materialize`, `verify`, `rewrite-registry`, `audit-paths`, `record-github-verification`, and `cleanup` subcommands.
- `scripts/build_atlas_web_proxy.py`: create and verify one package web proxy from authoritative media.
- `scripts/atlas_google_mirror.py`: `initialize`, `set-root`, `sync-filesystem`, `reconcile-downloaded`, `validate`, and `build-site-source` commands.

### New tracked publication records

- `docs/atlas/CONSOLIDATION.yml`: curated three-product intake and cutover policy.
- `docs/atlas/ATLAS_MIGRATION.yml`: generated pre-copy/post-copy/cleanup ledger for all packaged files.
- `docs/atlas/LEGACY_PATH_AUDIT.yml`: current-code/reference audit separating canonicalized publishable paths from permitted nonpublishable inputs and historical evidence.
- `docs/atlas/GOOGLE_MIRROR.yml`: mutable remote folder identities, URLs, verification states, and Site publication identity.
- `docs/acceptance/atlas-consolidation-and-google-mirror.md`: final counts, hashes, deployments, logged-out checks, cleanup proof, deviations, and nonclaims.
- `docs/work/KIKU-T085.md`: canonicalize 125 product packages.
- `docs/work/KIKU-T086.md`: refresh the 125-product GitHub Pages catalogue.
- `docs/work/KIKU-T087.md`: publish and verify the UMN Drive/Sites mirror.

### Existing files modified deliberately

- `docs/atlas/PRODUCT_REGISTRY.yml`: rewrite all product paths to canonical packages and add the three quartz records.
- `docs/products/ARTIFACT_CATALOG.yml`: retain the three completed quartz records and update their current canonical artifact paths after cutover.
- `docs/atlas/RELEASE_METADATA.yml`: record the draft release, GitHub deployment, Drive mirror, and Google Site URLs without inventing a DOI.
- `docs/atlas/PUBLIC_RELEASE.md`: document 12 phases, 125 products, authoritative/full-resolution versus web-proxy behavior, and mirror nonclaims.
- `docs/work/KIKU-F012.md`, `docs/work/KIKU-E001.md`: register the three new publication tasks and close only criteria actually met.
- Current quartz acceptance/work records: replace current artifact-root references with canonical paths while retaining explicit historical invocation paths where they describe the original run.
- `src/kikuchi_lab/atlas/catalog.py`: add optional `web_path`, MOV rendering, full availability validation, and optional remote product actions.
- `src/kikuchi_lab/atlas/publication.py`: prefer declared web proxies, include package manifests and mirror URLs in inventory, and keep heavy authoritative files out of Pages.
- `scripts/build_atlas.py`, `scripts/build_public_atlas.py`: accept an optional mirror ledger.
- `.github/workflows/deploy-atlas-pages.yml`: point at each verified candidate/final release payload and pin its exact ZIP SHA-256.
- `tests/unit/test_atlas_packages.py`, `tests/unit/test_atlas_consolidation.py`, `tests/unit/test_atlas_web_proxy.py`, `tests/unit/test_atlas_mirror.py`: new focused contracts.
- `tests/unit/test_atlas.py`, `tests/unit/test_atlas_publication.py`, `tests/unit/test_atlas_release_metadata.py`, `tests/unit/test_product_status.py`: 125-product, canonical-path, proxy, mirror, and current-catalog assertions.

---

### Task 1: Verify and commit the completed quartz artist-master evidence

**Files:**
- Modify: `tests/unit/test_product_status.py`
- Verify and commit existing in-scope changes: `docs/products/ARTIFACT_CATALOG.yml`
- Verify and commit existing in-scope changes: `docs/acceptance/quartz-artist-master.md`
- Verify and commit existing in-scope changes: `docs/acceptance/quartz-near-depth-artist-pair.md`
- Verify and commit existing in-scope changes: `docs/work/KIKU-E001.md`
- Verify and commit existing in-scope changes: `docs/work/KIKU-F006.md`
- Verify and commit existing in-scope changes: `docs/work/KIKU-F014.md`
- Verify and commit existing in-scope changes: `docs/work/KIKU-T056.md`
- Verify and commit existing in-scope changes: `docs/work/KIKU-T058.md`
- Verify and commit existing in-scope changes: `docs/work/KIKU-T059.md`
- Verify and commit existing in-scope changes: `scripts/render_retained_near_depth_rotation.py`
- Verify and commit existing in-scope changes: `tests/unit/test_retained_near_depth_rotation.py`

**Interfaces:**
- Consumes: the three completed local quartz roots and their accepted manifest/media hashes.
- Produces: a clean, tested tracked prerequisite in which `ARTIFACT_CATALOG.yml` names 12 records, including the three Atlas-intake candidates and the review-only orientation gallery.

- [ ] **Step 1: Confirm the dirty scope before changing it**

Run:

```bash
git status --short
git diff -- docs/products/ARTIFACT_CATALOG.yml docs/work/KIKU-E001.md docs/work/KIKU-F006.md scripts/render_retained_near_depth_rotation.py tests/unit/test_retained_near_depth_rotation.py
```

Expected: only the previously produced quartz artist-master/catalog/tracker changes appear in these paths. Stop if any unrelated change is interleaved in a named file.

- [ ] **Step 2: Update the catalog identity assertion**

Replace the expected set in `tests/unit/test_product_status.py` with:

```python
    assert {entry["id"] for entry in entries} == {
        "forsterite-dynamical-master-x-axis",
        "forsterite-direct-reflector-depth-x-axis",
        "ice-ih-direct-reflector-depth-x-axis",
        "titanite-retained-near-depth-x-axis",
        "zircon-retained-near-depth-x-axis",
        "forsterite-reflector-ridge-globe",
        "forsterite-intensity-relief-globe",
        "five-phase-standard-vector-family",
        "quartz-direct-reflector-artist-master-x-axis",
        "quartz-near-depth-artist-master-identity-60fps",
        "quartz-near-depth-artist-master-oblique-17-31-43-60fps",
        "five-phase-orientation-gallery",
    }
```

- [ ] **Step 3: Recompute and compare the six accepted media hashes**

Run:

```bash
shasum -a 256 \
  local/phase-general-direct-reflector-art/exports/quartz-x-axis-rotation-4k-24fps-24s-v1/quartz-x-axis-rotation-artist-master.mov \
  local/phase-general-direct-reflector-art/exports/quartz-x-axis-rotation-4k-24fps-24s-v1/quartz-x-axis-rotation-viewing-copy.mp4 \
  local/idealized-near-depth-rotation/quartz-identity-2k-60fps-24s-v1/quartz-near-depth-identity-60fps-x-axis-rotation-artist-master.mov \
  local/idealized-near-depth-rotation/quartz-identity-2k-60fps-24s-v1/quartz-near-depth-identity-60fps-x-axis-rotation-viewing-copy.mp4 \
  local/idealized-near-depth-rotation/quartz-oblique-17-31-43-2k-60fps-24s-v1/quartz-near-depth-oblique-17-31-43-60fps-x-axis-rotation-artist-master.mov \
  local/idealized-near-depth-rotation/quartz-oblique-17-31-43-2k-60fps-24s-v1/quartz-near-depth-oblique-17-31-43-60fps-x-axis-rotation-viewing-copy.mp4
```

Expected SHA-256 values, in order:

```text
f64e56e0352b58c50b83d0d76b675283057b82f48369e1fe6cb210e445bd24a0
83f86404867bbd957e46c2851d02f7e560c3f67536aaa93ff14a264dfb5b5fe0
8c45c5dc7c220ba80f21b7716205e1197c8e9137114baed26d0d54da796a7b5a
a7e3928ad7e4f2236f02af941092497159d8d4dd78bd9dcdc49636ca39060595
e7b3ed4f9b18b2f11daf3267e65d3aab8c021a01e9b0289ff62d301dbab77ac2
eb1f6220435a2ecc5603479a3c6f16dfd0b98aec335097169407421360b33bc4
```

- [ ] **Step 4: Run the focused tracked and media-contract checks**

Run:

```bash
uv run pytest -q tests/unit/test_product_status.py tests/unit/test_retained_near_depth_rotation.py
uv run python scripts/product_status.py --require-present
uv run python scripts/validate_work_items.py
uv run ruff check scripts/render_retained_near_depth_rotation.py tests/unit/test_retained_near_depth_rotation.py tests/unit/test_product_status.py
git diff --check
```

Expected: all tests and validators pass; product status reports 12 present, 0 missing, 12 total.

- [ ] **Step 5: Commit only the verified quartz prerequisite**

```bash
git add \
  docs/products/ARTIFACT_CATALOG.yml \
  docs/acceptance/quartz-artist-master.md \
  docs/acceptance/quartz-near-depth-artist-pair.md \
  docs/work/KIKU-E001.md \
  docs/work/KIKU-F006.md \
  docs/work/KIKU-F014.md \
  docs/work/KIKU-T056.md \
  docs/work/KIKU-T058.md \
  docs/work/KIKU-T059.md \
  scripts/render_retained_near_depth_rotation.py \
  tests/unit/test_retained_near_depth_rotation.py \
  tests/unit/test_product_status.py
git commit -m "feat: publish quartz artist masters"
```

---

### Task 2: Define strict canonical package contracts

**Files:**
- Create: `src/kikuchi_lab/atlas/packages.py`
- Create: `tests/unit/test_atlas_packages.py`
- Modify: `src/kikuchi_lab/atlas/__init__.py`

**Interfaces:**
- Produces: `PackageFile`, `ProductPackage`, `PhasePackage`, `sha256_file(path)`, `load_product_package(path)`, `load_phase_package(path)`, `validate_product_package(path)`, and `validate_phase_package(path)`.
- Later tasks rely on `ProductPackage.package_sha256`, `ProductPackage.files`, and every file's `relative_path`, `role`, `byte_count`, `sha256`, `mime_type`, and `destinations`.

- [ ] **Step 1: Write failing package-schema and tamper tests**

Create `tests/unit/test_atlas_packages.py` with:

```python
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from kikuchi_lab.atlas.packages import validate_phase_package, validate_product_package


def _write_product(root: Path, *, digest: str | None = None) -> Path:
    media = root / "media/demo.png"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"demo")
    manifest = {
        "schema_version": 1,
        "phase_slug": "quartz",
        "product_id": "quartz-demo",
        "registry_id": "quartz-demo",
        "source_commit": "a" * 40,
        "tracked_references": {
            "phase_source": "phases/quartz/source.yml",
            "recipe": "recipes/reflectors/quartz-art-bands.yml",
            "product_registry": "docs/atlas/PRODUCT_REGISTRY.yml",
        },
        "files": [{
            "path": "media/demo.png",
            "role": "media",
            "bytes": 4,
            "sha256": digest or sha256(b"demo").hexdigest(),
            "mime_type": "image/png",
            "destinations": ["google-drive"],
        }],
    }
    path = root / "product-package.yml"
    path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return path


def test_product_package_validates_exact_files_and_identity(tmp_path: Path) -> None:
    package = validate_product_package(_write_product(tmp_path / "quartz-demo"))
    assert package.product_id == "quartz-demo"
    assert package.files[0].role == "media"
    assert package.package_sha256


def test_product_package_rejects_tampered_bytes(tmp_path: Path) -> None:
    path = _write_product(tmp_path / "quartz-demo", digest="0" * 64)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        validate_product_package(path)


def test_product_package_rejects_absolute_escape_and_symlink(tmp_path: Path) -> None:
    path = _write_product(tmp_path / "quartz-demo")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload["files"][0]["path"] = "/Users/Z/demo.png"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="relative"):
        validate_product_package(path)


def test_phase_package_binds_product_manifest_digest(tmp_path: Path) -> None:
    product_path = _write_product(tmp_path / "phase/products/quartz-demo")
    product = validate_product_package(product_path)
    phase_path = tmp_path / "phase/phase-package.yml"
    phase_path.write_text(yaml.safe_dump({
        "schema_version": 1,
        "phase_slug": "quartz",
        "source_record": "phases/quartz/source.yml",
        "products": [{
            "product_id": "quartz-demo",
            "manifest": "products/quartz-demo/product-package.yml",
            "manifest_sha256": product.package_sha256,
        }],
    }, sort_keys=False), encoding="utf-8")
    assert validate_phase_package(phase_path).product_ids == ("quartz-demo",)
```

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_packages.py
```

Expected: collection fails with `ModuleNotFoundError: kikuchi_lab.atlas.packages`.

- [ ] **Step 3: Implement the immutable contracts and validators**

Create `src/kikuchi_lab/atlas/packages.py` with these public shapes and validation order:

```python
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re

import yaml

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_ROLES = {"media", "preview", "web", "provenance"}
_ROLE_DIRECTORIES = {
    "media": "media",
    "preview": "previews",
    "web": "web",
    "provenance": "provenance",
}
_DESTINATIONS = {"github-pages", "google-drive"}


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(value: object, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.startswith("file://"):
        raise ValueError(f"{label} must be a package-relative path")
    return path


@dataclass(frozen=True)
class PackageFile:
    relative_path: PurePosixPath
    role: str
    byte_count: int
    sha256: str
    mime_type: str
    destinations: tuple[str, ...]


@dataclass(frozen=True)
class ProductPackage:
    manifest_path: Path
    phase_slug: str
    product_id: str
    registry_id: str
    source_commit: str
    tracked_references: dict[str, str]
    files: tuple[PackageFile, ...]

    @property
    def package_sha256(self) -> str:
        identity = {
            "phase_slug": self.phase_slug,
            "product_id": self.product_id,
            "registry_id": self.registry_id,
            "source_commit": self.source_commit,
            "tracked_references": self.tracked_references,
            "files": [{
                "path": item.relative_path.as_posix(),
                "role": item.role,
                "bytes": item.byte_count,
                "sha256": item.sha256,
                "mime_type": item.mime_type,
                "destinations": list(item.destinations),
            } for item in self.files],
        }
        encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class PhasePackage:
    manifest_path: Path
    phase_slug: str
    source_record: str
    product_ids: tuple[str, ...]
    manifest_sha256_by_product: dict[str, str]
```

Implement `load_product_package()` to require exactly schema version 1 and the six top-level keys shown in the test. Reject duplicate paths, duplicate roles for the same path, invalid SHA/commit strings, empty MIME types, duplicate/unknown destinations, and paths whose first directory does not match `_ROLE_DIRECTORIES[role]`.

Implement `validate_product_package()` to reject symlinks, hard links (`st_nlink != 1`), non-files, byte-count mismatches, SHA-256 mismatches, and any manifest whose parent is not exactly:

```text
/Users/Z/Documents/kikuchi/local/atlas/phases/<phase_slug>/products/<product_id>/
```

Implement `load_phase_package()` and `validate_phase_package()` to require unique product IDs, relative `products/<id>/product-package.yml` paths, matching phase/product IDs, and exact product-manifest SHA-256 values. Export every public name through `src/kikuchi_lab/atlas/__init__.py`.

- [ ] **Step 4: Run package tests and lint**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_packages.py
uv run ruff check src/kikuchi_lab/atlas/packages.py tests/unit/test_atlas_packages.py src/kikuchi_lab/atlas/__init__.py
```

Expected: all package tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 5: Commit the package contracts**

```bash
git add src/kikuchi_lab/atlas/packages.py src/kikuchi_lab/atlas/__init__.py tests/unit/test_atlas_packages.py
git commit -m "feat: define Atlas product packages"
```

---

### Task 3: Plan all 125 package migrations without copying

**Files:**
- Create: `src/kikuchi_lab/atlas/consolidation.py`
- Create: `scripts/consolidate_atlas_products.py`
- Create: `docs/atlas/CONSOLIDATION.yml`
- Create: `docs/atlas/ATLAS_MIGRATION.yml`
- Create: `tests/unit/test_atlas_consolidation.py`
- Create: `docs/work/KIKU-T085.md`
- Create: `docs/work/KIKU-T086.md`
- Create: `docs/work/KIKU-T087.md`
- Modify: `docs/work/KIKU-F012.md`
- Modify: `docs/work/KIKU-E001.md`
- Modify: `src/kikuchi_lab/atlas/__init__.py`

**Interfaces:**
- Consumes: `load_phase_registry()`, `load_product_registry()`, `scripts.product_status.load_catalog()`, and `docs/atlas/CONSOLIDATION.yml`.
- Produces: `MigrationFile`, `MigrationProduct`, `MigrationLedger`, `build_migration_ledger(registry_path, product_registry_path, artifact_catalog_path, consolidation_path, source_commit)`, `write_migration_ledger(ledger, output_path)`, and a CLI that emits a frozen, hash-bearing 125-product plan without mutating `local/atlas/phases/`.

- [ ] **Step 1: Write failing deterministic-plan tests**

Add fixture helpers and these assertions to `tests/unit/test_atlas_consolidation.py`:

```python
def _build_fixture_ledger(fixture_repo: Path) -> MigrationLedger:
    return build_migration_ledger(
        registry_path=fixture_repo / "docs/atlas/PHASE_REGISTRY.yml",
        product_registry_path=fixture_repo / "docs/atlas/PRODUCT_REGISTRY.yml",
        artifact_catalog_path=fixture_repo / "docs/products/ARTIFACT_CATALOG.yml",
        consolidation_path=fixture_repo / "docs/atlas/CONSOLIDATION.yml",
        source_commit="a" * 40,
    )


def test_plan_combines_registry_products_and_three_intake_products(fixture_repo: Path) -> None:
    ledger = _build_fixture_ledger(fixture_repo)
    assert ledger.phase_count == 1
    assert ledger.product_count == 2
    assert ledger.products[1].destination_root == (
        "local/atlas/phases/quartz/products/quartz-artist"
    )
    assert all(
        item.source_byte_count > 0 and len(item.source_sha256) == 64
        for item in ledger.files
    )


def test_plan_classifies_only_exact_publishable_files(fixture_repo: Path) -> None:
    ledger = _build_fixture_ledger(fixture_repo)
    paths = {item.source_path for item in ledger.files if item.source_path is not None}
    assert "local/legacy/frames/frame-0001.png" not in paths
    assert {item.role for item in ledger.files} == {
        "media", "preview", "provenance", "web"
    }
    assert all(item.cleanup_approved for item in ledger.files if item.kind == "copied")


def test_plan_rejects_same_destination_with_different_bytes(fixture_repo: Path) -> None:
    policy = fixture_repo / "docs/atlas/CONSOLIDATION.yml"
    payload = yaml.safe_load(policy.read_text(encoding="utf-8"))
    payload["extra_products"][0]["preview_destination"] = "media/demo.png"
    policy.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="destination collision"):
        _build_fixture_ledger(fixture_repo)
```

The fixture must contain one normal registry product, one configured intake product, one unlisted frame intermediate, and exact source files. Spell out the fixture YAML in the test rather than reading the real Atlas.

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_consolidation.py
```

Expected: collection fails because `kikuchi_lab.atlas.consolidation` does not exist.

- [ ] **Step 3: Add the curated consolidation policy and three complete intake records**

Create `docs/atlas/CONSOLIDATION.yml` with schema version 1, canonical root `local/atlas/phases`, the ten approved legacy roots, and these complete extra-product records:

```yaml
schema_version: 1
canonical_root: local/atlas/phases
legacy_roots:
  - local/atlas-expansion
  - local/atlas-extension-parity
  - local/phase-general-direct-reflector-art
  - local/reflector-ridge-series
  - local/dynamical-master-rotation
  - local/ice-intensity-globes-fixed
  - local/ice-reflector-globes
  - local/idealized-direct-reflector-depth-rotation
  - local/idealized-near-depth-rotation
  - local/relief-globes
extra_products:
  - id: quartz-direct-reflector-artist-master-x-axis
    title: Alpha quartz — 4K direct-reflector artist-master x-axis rotation
    phase_slugs: [quartz]
    families: [x-axis-motion]
    format: mov
    media_source: local/phase-general-direct-reflector-art/exports/quartz-x-axis-rotation-4k-24fps-24s-v1/quartz-x-axis-rotation-artist-master.mov
    preview_source: local/phase-general-direct-reflector-art/exports/quartz-x-axis-rotation-4k-24fps-24s-v1/preview.png
    web_source: local/phase-general-direct-reflector-art/exports/quartz-x-axis-rotation-4k-24fps-24s-v1/quartz-x-axis-rotation-viewing-copy.mp4
    provenance_source: local/phase-general-direct-reflector-art/exports/quartz-x-axis-rotation-4k-24fps-24s-v1/manifest.json
    recipe: recipes/reflectors/quartz-art-bands.yml
    entrypoint: scripts/render_direct_reflector_rotation.py
    tier: direct-reflector-art
    state: local-published
    caption: Edit-friendly 4K ProRes direct-reflector science-art master with a browser-safe H.264 viewing copy; not a detector acquisition.
    orientation: active sample-frame x-axis rotation from Bunge ZXZ (17, 31, 43) degrees
    hero: false
  - id: quartz-near-depth-artist-master-identity-60fps
    title: Alpha quartz — 60 fps near-depth identity artist master
    phase_slugs: [quartz]
    families: [depth-field-motion]
    format: mov
    media_source: local/idealized-near-depth-rotation/quartz-identity-2k-60fps-24s-v1/quartz-near-depth-identity-60fps-x-axis-rotation-artist-master.mov
    preview_source: local/idealized-near-depth-rotation/quartz-identity-2k-60fps-24s-v1/preview.png
    web_transform:
      profile: h264-square-1280-6500k
      filename: quartz-near-depth-identity-60fps-x-axis-rotation-web.mp4
    provenance_source: local/idealized-near-depth-rotation/quartz-identity-2k-60fps-24s-v1/manifest.json
    recipe: recipes/presentation/quartz-near-depth-atlas-parity.yml
    entrypoint: scripts/render_retained_near_depth_rotation.py
    tier: retained-near-depth-field
    state: local-published
    caption: Edit-friendly 2K 60 fps ProRes retained-field master with a derived browser proxy; not a detector acquisition or per-frame diffraction simulation.
    orientation: active sample-frame x-axis rotation from identity
    hero: false
  - id: quartz-near-depth-artist-master-oblique-17-31-43-60fps
    title: Alpha quartz — 60 fps near-depth oblique artist master
    phase_slugs: [quartz]
    families: [depth-field-motion]
    format: mov
    media_source: local/idealized-near-depth-rotation/quartz-oblique-17-31-43-2k-60fps-24s-v1/quartz-near-depth-oblique-17-31-43-60fps-x-axis-rotation-artist-master.mov
    preview_source: local/idealized-near-depth-rotation/quartz-oblique-17-31-43-2k-60fps-24s-v1/preview.png
    web_transform:
      profile: h264-square-1280-6500k
      filename: quartz-near-depth-oblique-17-31-43-60fps-x-axis-rotation-web.mp4
    provenance_source: local/idealized-near-depth-rotation/quartz-oblique-17-31-43-2k-60fps-24s-v1/manifest.json
    recipe: recipes/presentation/quartz-near-depth-atlas-parity.yml
    entrypoint: scripts/render_retained_near_depth_rotation.py
    tier: retained-near-depth-field
    state: local-published
    caption: Edit-friendly 2K 60 fps ProRes retained-field master with a derived browser proxy; not a detector acquisition or per-frame diffraction simulation.
    orientation: active sample-frame x-axis rotation from Bunge ZXZ (17, 31, 43) degrees
    hero: false
```

- [ ] **Step 4: Implement deterministic planning**

In `src/kikuchi_lab/atlas/consolidation.py`, define:

```python
@dataclass(frozen=True)
class MigrationFile:
    product_id: str
    phase_slug: str
    source_path: str | None
    destination_path: str
    role: str
    kind: str
    source_byte_count: int
    source_sha256: str
    destination_byte_count: int | None
    destination_sha256: str | None
    mime_type: str
    destinations: tuple[str, ...]
    cleanup_approved: bool


@dataclass(frozen=True)
class MigrationProduct:
    product_id: str
    phase_slug: str
    destination_root: str
    registry_record: dict[str, object]


@dataclass(frozen=True)
class MigrationLedger:
    state: str
    source_commit: str
    canonical_root: str
    products: tuple[MigrationProduct, ...]
    files: tuple[MigrationFile, ...]

    @property
    def product_count(self) -> int:
        return len(self.products)

    @property
    def phase_count(self) -> int:
        return len({item.phase_slug for item in self.products})
```

`build_migration_ledger()` must:

1. Load the 122 registry products and the three extra products.
2. Require each product to resolve to exactly one phase for package ownership.
3. Map media to `media/<original-name>`, preview to `previews/<original-name>`, declared web files to `web/<original-name>`, and original provenance to `provenance/<original-name>`.
4. Select canonical kinematical masters and relief fields with the same bounded rules currently implemented by `_supplemental_archive_sources()`, placing them in `provenance/scientific-fields/`.
5. Add one `kind: generated-metadata` `provenance/release-metadata.yml` entry per product. Store its exact UTF-8 YAML in the ledger and compute its source byte count/SHA-256 from those generated bytes.
6. Record `source_byte_count` and `source_sha256` for every entry. For `web_transform` entries with `kind: generated-proxy`, keep `destination_byte_count` and `destination_sha256` null in the planned ledger; fill them before the ledger state becomes `materialized`. For byte copies, the planned destination values equal the source values.
7. Reject source paths outside the ten approved legacy roots, missing files, duplicate product IDs, unknown phases/families, and destination collisions with different source hashes.
8. Sort products by `(phase_slug, product_id)` and files by `(phase_slug, product_id, role, destination_path)` before YAML serialization.

The CLI command:

```bash
uv run python scripts/consolidate_atlas_products.py plan \
  --registry docs/atlas/PHASE_REGISTRY.yml \
  --products docs/atlas/PRODUCT_REGISTRY.yml \
  --catalog docs/products/ARTIFACT_CATALOG.yml \
  --policy docs/atlas/CONSOLIDATION.yml \
  --output docs/atlas/ATLAS_MIGRATION.yml \
  --source-commit "$(git rev-parse HEAD)"
```

must write `state: planned`, `phase_count: 12`, `product_count: 125`, the complete file ledger, and no canonical binary file.

- [ ] **Step 5: Add publication work items**

Create KIKU-T085/T086/T087 as children of KIKU-F012. Their criteria are, respectively:

```markdown
# KIKU-T085: Canonicalize Atlas product packages

## Description

Copy every publishable 12-phase Atlas artifact into the phase-slugged canonical package hierarchy and prove byte identity before registry cutover.

## Acceptance Criteria

- [ ] Exactly 125 product manifests and 12 phase manifests validate.
- [ ] Every copied destination matches its frozen source SHA-256 and byte count.
- [ ] The 125-product Atlas builds without a legacy-root fallback.
- [ ] No legacy file has been deleted before all external publication gates pass.
```

```markdown
# KIKU-T086: Refresh the 125-product GitHub Pages catalogue

## Description

Publish the browser-safe 125-product Atlas through the existing release-driven Pages workflow while keeping authoritative heavyweight media outside the Pages payload.

## Acceptance Criteria

- [ ] The public build contains exactly 12 phases and 125 product records.
- [ ] Every public asset is browser-safe, no larger than 25 MiB, and free of local paths.
- [ ] The release ZIP checksum matches the workflow pin.
- [ ] The live Pages index, all phase pages, and the three new quartz products pass HTTP and browser checks.
```

```markdown
# KIKU-T087: Publish and verify the UMN Drive and Sites mirror

## Description

Mirror canonical full-resolution product packages through `zmichels@umn.edu`, publish the Google Site after action-time confirmation, and verify logged-out access before legacy cleanup.

## Acceptance Criteria

- [ ] The verified account and remaining quota pass the 10 GiB headroom gate.
- [ ] Every phase and product package is uploaded and reconciled against canonical hashes.
- [ ] Drive and Site public-access changes occur only after action-time user confirmation.
- [ ] Logged-out Site navigation and representative media downloads pass.
- [ ] Post-cleanup local and public rebuilds prove no legacy fallback.
```

Use the existing frontmatter schema, priorities `P1`, tags `[atlas, publication, consolidation]`, `[atlas, github-pages, publication]`, and `[atlas, google-drive, google-sites, publication]`, and add all three IDs to `docs/work/KIKU-F012.md` and its parent evidence.

- [ ] **Step 6: Run RED-to-GREEN planning checks and emit the real ledger**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_consolidation.py
uv run python scripts/consolidate_atlas_products.py plan \
  --registry docs/atlas/PHASE_REGISTRY.yml \
  --products docs/atlas/PRODUCT_REGISTRY.yml \
  --catalog docs/products/ARTIFACT_CATALOG.yml \
  --policy docs/atlas/CONSOLIDATION.yml \
  --output docs/atlas/ATLAS_MIGRATION.yml \
  --source-commit "$(git rev-parse HEAD)"
uv run python scripts/validate_work_items.py
uv run ruff check src/kikuchi_lab/atlas/consolidation.py scripts/consolidate_atlas_products.py tests/unit/test_atlas_consolidation.py
git diff --check
```

Expected: tests and validators pass; the CLI reports `planned phases=12 products=125`; the ledger has `state: planned`; no `local/atlas/phases/*/products/*/product-package.yml` has been created.

- [ ] **Step 7: Commit the frozen migration plan**

```bash
git add \
  src/kikuchi_lab/atlas/consolidation.py \
  src/kikuchi_lab/atlas/__init__.py \
  scripts/consolidate_atlas_products.py \
  docs/atlas/CONSOLIDATION.yml \
  docs/atlas/ATLAS_MIGRATION.yml \
  docs/work/KIKU-E001.md \
  docs/work/KIKU-F012.md \
  docs/work/KIKU-T085.md \
  docs/work/KIKU-T086.md \
  docs/work/KIKU-T087.md \
  tests/unit/test_atlas_consolidation.py
git commit -m "feat: plan Atlas package consolidation"
```

---

### Task 4: Materialize byte-verified packages and heavyweight web proxies

**Files:**
- Create: `src/kikuchi_lab/atlas/web_proxy.py`
- Create: `scripts/build_atlas_web_proxy.py`
- Create: `tests/unit/test_atlas_web_proxy.py`
- Modify: `src/kikuchi_lab/atlas/consolidation.py`
- Modify: `scripts/consolidate_atlas_products.py`
- Modify: `tests/unit/test_atlas_consolidation.py`
- Modify: `src/kikuchi_lab/atlas/__init__.py`
- Generate: `local/atlas/phases/<slug>/phase-package.yml`
- Generate: `local/atlas/phases/<slug>/products/<product-id>/product-package.yml`
- Modify generated ledger: `docs/atlas/ATLAS_MIGRATION.yml`

**Interfaces:**
- Consumes: a `state: planned` `MigrationLedger`.
- Produces: `materialize_ledger(ledger_path, repository_root) -> MigrationLedger`, `verify_canonical_tree(ledger_path, repository_root) -> CanonicalVerification`, `build_web_proxy(source, destination, profile) -> WebProxyResult`, and 125 verified product packages plus 12 verified phase manifests.

- [ ] **Step 1: Write failing clone/copy, resumability, collision, and proxy tests**

Add these behaviors to the focused tests:

```python
def test_materialize_copies_to_partial_then_verifies_and_publishes(
    fixture_repo: Path,
) -> None:
    result = materialize_ledger(
        fixture_repo / "docs/atlas/ATLAS_MIGRATION.yml",
        repository_root=fixture_repo,
    )
    package = fixture_repo / (
        "local/atlas/phases/quartz/products/quartz-demo/product-package.yml"
    )
    assert result.state == "materialized"
    assert validate_product_package(package).product_id == "quartz-demo"
    assert not tuple(package.parent.rglob("*.partial"))


def test_materialize_resumes_matching_destination_without_rewriting(
    fixture_repo: Path,
) -> None:
    ledger_path = fixture_repo / "docs/atlas/ATLAS_MIGRATION.yml"
    first = materialize_ledger(ledger_path, repository_root=fixture_repo)
    media = fixture_repo / first.files[0].destination_path
    before = media.stat().st_mtime_ns
    materialize_ledger(ledger_path, repository_root=fixture_repo)
    assert media.stat().st_mtime_ns == before


def test_materialize_refuses_existing_different_bytes(fixture_repo: Path) -> None:
    destination = fixture_repo / "local/atlas/phases/quartz/products/quartz-demo/media/demo.png"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"different")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        materialize_ledger(
            fixture_repo / "docs/atlas/ATLAS_MIGRATION.yml",
            repository_root=fixture_repo,
        )
```

Create `tests/unit/test_atlas_web_proxy.py` so a fake subprocess records the exact ffmpeg arguments and a fixture ffprobe result proves that the validator requires H.264, `yuv420p`, square 1280 pixels, original frame rate/duration, full decode, and a file no larger than 25 MiB.

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_consolidation.py tests/unit/test_atlas_web_proxy.py
```

Expected: failures for missing `materialize_ledger` and `kikuchi_lab.atlas.web_proxy`.

- [ ] **Step 3: Implement the safe publication primitive**

Use this sequence for every copied destination:

```python
def _clone_or_copy_verified(source: Path, destination: Path, expected_sha256: str) -> None:
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"source must be a regular file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.is_symlink() or sha256_file(destination) != expected_sha256:
            raise ValueError(f"refusing to overwrite different destination: {destination}")
        return
    partial = destination.with_name(destination.name + ".partial")
    if partial.exists():
        partial.unlink()
    cloned = subprocess.run(
        ["cp", "-c", str(source), str(partial)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0
    if not cloned:
        shutil.copy2(source, partial)
    if partial.stat().st_size != source.stat().st_size:
        partial.unlink()
        raise ValueError(f"byte-count mismatch after copy: {destination}")
    if sha256_file(partial) != expected_sha256:
        partial.unlink()
        raise ValueError(f"SHA-256 mismatch after copy: {destination}")
    os.replace(partial, destination)
```

Reject destinations outside `local/atlas/phases`, any symlink in a package, and any file whose source hash has changed since planning.

- [ ] **Step 4: Implement and run the exact web-proxy profile**

`build_web_proxy()` constructs these exact argument lists from its `source`, `destination`, and `partial = destination.with_name(destination.name + ".partial")` parameters:

```python
encode_command = [
    "ffmpeg", "-v", "error", "-y", "-i", str(source),
    "-vf", "scale=1280:1280:flags=lanczos",
    "-c:v", "libx264", "-preset", "slow",
    "-b:v", "6500k", "-maxrate", "7000k", "-bufsize", "14000k",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(partial),
]
probe_command = [
    "ffprobe", "-v", "error", "-select_streams", "v:0",
    "-show_entries",
    "stream=codec_name,pix_fmt,width,height,avg_frame_rate,nb_frames:format=duration,size",
    "-of", "json", str(partial),
]
decode_command = [
    "ffmpeg", "-v", "error", "-i", str(partial), "-f", "null", "-",
]
```

Require codec `h264`, pixel format `yuv420p`, 1280 by 1280, 60 fps, 1,440 frames, 24.000 seconds within 0.01 seconds, full decode success, and size at or below 26,214,400 bytes before `os.replace()`.

Run the two real proxies:

```bash
uv run python scripts/build_atlas_web_proxy.py \
  --source local/idealized-near-depth-rotation/quartz-identity-2k-60fps-24s-v1/quartz-near-depth-identity-60fps-x-axis-rotation-artist-master.mov \
  --destination local/atlas/phases/quartz/products/quartz-near-depth-artist-master-identity-60fps/web/quartz-near-depth-identity-60fps-x-axis-rotation-web.mp4 \
  --profile h264-square-1280-6500k
uv run python scripts/build_atlas_web_proxy.py \
  --source local/idealized-near-depth-rotation/quartz-oblique-17-31-43-2k-60fps-24s-v1/quartz-near-depth-oblique-17-31-43-60fps-x-axis-rotation-artist-master.mov \
  --destination local/atlas/phases/quartz/products/quartz-near-depth-artist-master-oblique-17-31-43-60fps/web/quartz-near-depth-oblique-17-31-43-60fps-x-axis-rotation-web.mp4 \
  --profile h264-square-1280-6500k
```

Expected: both commands report 1,440 frames, 60 fps, 24.000 seconds, and a size below 25 MiB.

- [ ] **Step 5: Materialize all packages and write manifests**

Run:

```bash
uv run python scripts/consolidate_atlas_products.py materialize \
  --ledger docs/atlas/ATLAS_MIGRATION.yml \
  --root /Users/Z/Documents/kikuchi
uv run python scripts/consolidate_atlas_products.py verify \
  --ledger docs/atlas/ATLAS_MIGRATION.yml \
  --root /Users/Z/Documents/kikuchi
```

The materializer writes:

```yaml
schema_version: 1
phase_slug: quartz
product_id: quartz-direct-reflector-artist-master-x-axis
registry_id: quartz-direct-reflector-artist-master-x-axis
source_commit: 0123456789abcdef0123456789abcdef01234567
tracked_references:
  phase_source: phases/quartz/source.yml
  recipe: recipes/reflectors/quartz-art-bands.yml
  product_registry: docs/atlas/PRODUCT_REGISTRY.yml
files:
  - path: media/quartz-x-axis-rotation-artist-master.mov
    role: media
    bytes: 1114663430
    sha256: f64e56e0352b58c50b83d0d76b675283057b82f48369e1fe6cb210e445bd24a0
    mime_type: video/quicktime
    destinations: [google-drive]
```

The displayed source commit is a schema-valid example; the writer must use `ledger.source_commit` verbatim. The remaining actual files are appended in stable role/path order. The materializer writes one `phase-package.yml` with every product ID and product-manifest digest, and changes the tracked ledger to `state: materialized` only after all 125 product and 12 phase manifests pass.

Expected CLI summary:

```text
verified phases=12 products=125 missing=0 mismatched=0 symlinks=0
```

- [ ] **Step 6: Run focused verification and commit code plus the finalized ledger**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_packages.py tests/unit/test_atlas_consolidation.py tests/unit/test_atlas_web_proxy.py
uv run ruff check \
  src/kikuchi_lab/atlas/packages.py \
  src/kikuchi_lab/atlas/consolidation.py \
  src/kikuchi_lab/atlas/web_proxy.py \
  scripts/consolidate_atlas_products.py \
  scripts/build_atlas_web_proxy.py \
  tests/unit/test_atlas_packages.py \
  tests/unit/test_atlas_consolidation.py \
  tests/unit/test_atlas_web_proxy.py
git diff --check
```

Expected: all focused tests pass, Ruff passes, and the ledger contains output hashes for both generated proxies.

```bash
git add \
  src/kikuchi_lab/atlas/consolidation.py \
  src/kikuchi_lab/atlas/web_proxy.py \
  src/kikuchi_lab/atlas/__init__.py \
  scripts/consolidate_atlas_products.py \
  scripts/build_atlas_web_proxy.py \
  tests/unit/test_atlas_consolidation.py \
  tests/unit/test_atlas_web_proxy.py \
  docs/atlas/ATLAS_MIGRATION.yml
git commit -m "feat: materialize Atlas product packages"
```

---

### Task 5: Cut the registries and local Atlas over to 125 canonical packages

**Files:**
- Modify: `src/kikuchi_lab/atlas/catalog.py`
- Modify: `src/kikuchi_lab/atlas/consolidation.py`
- Modify: `scripts/consolidate_atlas_products.py`
- Modify: `scripts/build_atlas.py`
- Modify: `docs/atlas/PRODUCT_REGISTRY.yml`
- Modify: `docs/products/ARTIFACT_CATALOG.yml`
- Modify: `tests/unit/test_atlas.py`
- Modify: `tests/unit/test_atlas_consolidation.py`
- Modify: current quartz acceptance/work records named in Task 1
- Create: `docs/atlas/LEGACY_PATH_AUDIT.yml`
- Regenerate: `docs/atlas/site/`

**Interfaces:**
- Consumes: a fully verified `state: materialized` migration ledger.
- Produces: `AtlasProduct.web_path: Path | None`, `AtlasProduct.required_paths()`, a 125-record canonical registry, and a local Atlas that resolves no product path through a legacy root.

- [ ] **Step 1: Write failing MOV, web-path, availability, and 125-product tests**

Update `tests/unit/test_atlas.py` with:

```python
def test_all_products_resolve_only_to_canonical_packages() -> None:
    phases = load_phase_registry(REGISTRY)
    _, products = load_product_registry(PRODUCTS, phase_slugs={phase.slug for phase in phases})
    assert len(products) == 125
    assert all(product.is_available() for product in products)
    assert all(
        "local/atlas/phases/" in path.relative_to(ROOT).as_posix()
        for product in products
        for path in product.required_paths()
        if path.is_relative_to(ROOT / "local")
    )
    assert {
        product.identifier
        for product in products
        if product.identifier.startswith("quartz-") and product.media_format == "mov"
    } == {
        "quartz-direct-reflector-artist-master-x-axis",
        "quartz-near-depth-artist-master-identity-60fps",
        "quartz-near-depth-artist-master-oblique-17-31-43-60fps",
    }
    assert all(product.web_path and product.web_path.suffix == ".mp4"
               for product in products if product.media_format == "mov")
```

Change build-count assertions from 122 to 125, the quartz phase card count from 10 to 13, and the all-products card count from 122 to 125. Add a test that deleting a declared package manifest or web proxy makes `is_available()` false.

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```bash
uv run pytest -q tests/unit/test_atlas.py tests/unit/test_atlas_consolidation.py
```

Expected: failures because `AtlasProduct` has no `web_path` or `required_paths()` and the registry still contains 122 records with legacy paths.

- [ ] **Step 3: Extend the product schema without weakening existing records**

In `src/kikuchi_lab/atlas/catalog.py`:

```python
_PRODUCT_FIELDS = {
    "id", "title", "phase_slugs", "families", "format", "media_path",
    "preview_path", "web_path", "bundle_path", "provenance_path", "recipe",
    "entrypoint", "tier", "state", "caption", "orientation", "hero",
}
_FORMATS = {"png", "svg", "mp4", "mov", "stl"}
```

Add the dataclass field and availability contract:

```python
    web_path: Path | None

    def required_paths(self) -> tuple[Path, ...]:
        return tuple(
            path for path in (
                self.media_path,
                self.preview_path,
                self.web_path,
                self.bundle_path,
                self.provenance_path,
            )
            if path is not None
        )

    def is_available(self) -> bool:
        return (
            self.media_path.is_file()
            and self.bundle_path.is_dir()
            and (self.preview_path is None or self.preview_path.is_file())
            and (self.web_path is None or self.web_path.is_file())
            and (self.provenance_path is None or self.provenance_path.is_file())
        )
```

Make `web_path` optional in `_product_from_mapping()`. Render both `mp4` and `mov` through `<video>`; use MIME `video/mp4` for MP4 and `video/quicktime` for MOV. Add a local `web copy` action when `web_path` exists while keeping the authoritative media action first.

- [ ] **Step 4: Rewrite the product registry from the verified ledger**

Implement `rewrite_product_registry()` so it refuses any ledger state other than `materialized`, preserves product IDs/titles/families/claims, adds the three complete intake records, and writes these canonical fields for each product:

```yaml
media_path: local/atlas/phases/<slug>/products/<id>/media/<authoritative-filename>
preview_path: local/atlas/phases/<slug>/products/<id>/previews/<preview-filename>
web_path: local/atlas/phases/<slug>/products/<id>/web/<proxy-filename>
bundle_path: local/atlas/phases/<slug>/products/<id>
provenance_path: local/atlas/phases/<slug>/products/<id>/product-package.yml
```

Omit `web_path` when the authoritative media itself is a Pages-safe file or no browser media exists. Write to `PRODUCT_REGISTRY.yml.generated`, load and validate it, assert 125 available products, then atomically replace the tracked registry.

Run:

```bash
uv run python scripts/consolidate_atlas_products.py rewrite-registry \
  --ledger docs/atlas/ATLAS_MIGRATION.yml \
  --products docs/atlas/PRODUCT_REGISTRY.yml \
  --policy docs/atlas/CONSOLIDATION.yml \
  --root /Users/Z/Documents/kikuchi
```

Expected: `registry cutover products=125 available=125 legacy_paths=0`.

- [ ] **Step 5: Update current catalog and acceptance paths**

Rewrite every artifact-catalog entry that identifies a publishable Atlas product to its canonical package root and role-relative filenames. For the three quartz entries use:

```yaml
artifact_path: local/atlas/phases/quartz/products/quartz-direct-reflector-artist-master-x-axis
files:
  - product-package.yml
  - previews/preview.png
  - media/quartz-x-axis-rotation-artist-master.mov
  - web/quartz-x-axis-rotation-viewing-copy.mp4
```

and:

```yaml
artifact_path: local/atlas/phases/quartz/products/quartz-near-depth-artist-master-identity-60fps
files:
  - product-package.yml
  - previews/preview.png
  - media/quartz-near-depth-identity-60fps-x-axis-rotation-artist-master.mov
  - web/quartz-near-depth-identity-60fps-x-axis-rotation-web.mp4
```

with the oblique product using its exact canonical ID and oblique media/proxy filenames. Point `five-phase-standard-vector-family` at `local/atlas/phases` with its five canonical per-phase standard SVG paths. Keep `five-phase-orientation-gallery` at its original review-proof root and classify it as `historical-reproduction-evidence`; it is not an individual Atlas product or a cleanup target.

In current acceptance/work prose, distinguish:

```markdown
Original production root (historical invocation evidence):
`local/idealized-near-depth-rotation/quartz-identity-2k-60fps-24s-v1`

Current canonical publication packages:
`local/atlas/phases/quartz/products/quartz-direct-reflector-artist-master-x-axis/`,
`local/atlas/phases/quartz/products/quartz-near-depth-artist-master-identity-60fps/`,
and
`local/atlas/phases/quartz/products/quartz-near-depth-artist-master-oblique-17-31-43-60fps/`.
```

Do not rewrite the retained original command or imply that the canonical package was the original render output.

- [ ] **Step 6: Build and verify the local Atlas entirely from canonical paths**

Run:

```bash
uv run pytest -q tests/unit/test_atlas.py tests/unit/test_product_status.py tests/unit/test_atlas_consolidation.py
uv run python scripts/product_status.py --require-present
uv run python scripts/build_atlas.py
rg -n \
  'local/(atlas-expansion|atlas-extension-parity|phase-general-direct-reflector-art|reflector-ridge-series|dynamical-master-rotation|ice-intensity-globes-fixed|ice-reflector-globes|idealized-direct-reflector-depth-rotation|idealized-near-depth-rotation|relief-globes)' \
  docs/atlas/site docs/atlas/PRODUCT_REGISTRY.yml
rg -n 'orientation-gallery' docs/products/ARTIFACT_CATALOG.yml
```

Expected:

```text
atlas built phases=12 individual_products=125
Catalog: 12 present, 0 missing, 12 total
```

The legacy-root `rg` returns no matches. The catalog query returns exactly the review-only orientation gallery; `audit-paths` checks that exception in the next step.

- [ ] **Step 7: Audit every remaining current legacy-root reference**

Add an `audit-paths` subcommand that searches tracked current code, scripts, tests, acceptance records, tracker records, and release docs while excluding `docs/superpowers/plans/`, `docs/superpowers/specs/`, generated sites, `ATLAS_MIGRATION.yml`, and `LEGACY_PATH_AUDIT.yml`. It writes this record shape with actual repository line numbers and paths:

```yaml
schema_version: 1
publishable_legacy_reference_count: 0
allowed_references:
  - file: scripts/render_direct_reflector_rotation.py
    line: 31
    legacy_path: local/phase-general-direct-reflector-art/series/quartz-hemisphere-standard-run-c8e68d027682d562
    classification: nonpublishable-scientific-input
    reason: The renderer consumes the retained selection bundle; the Atlas registry does not publish the bundle as an individual product.
```

Allowed classifications are exactly `nonpublishable-scientific-input` and `historical-reproduction-evidence`. Any current reference that is a registry media/preview/bundle/provenance path, generated site link, current artifact-catalog root, or runtime publication output makes the command fail.

Run:

```bash
uv run python scripts/consolidate_atlas_products.py audit-paths \
  --ledger docs/atlas/ATLAS_MIGRATION.yml \
  --root /Users/Z/Documents/kikuchi \
  --output docs/atlas/LEGACY_PATH_AUDIT.yml
```

Expected: `publishable legacy references=0`; every retained reference has one allowed classification and reason.

- [ ] **Step 8: Commit the registry cutover**

```bash
git add \
  src/kikuchi_lab/atlas/catalog.py \
  src/kikuchi_lab/atlas/consolidation.py \
  scripts/consolidate_atlas_products.py \
  scripts/build_atlas.py \
  docs/atlas/PRODUCT_REGISTRY.yml \
  docs/atlas/LEGACY_PATH_AUDIT.yml \
  docs/products/ARTIFACT_CATALOG.yml \
  docs/acceptance/quartz-artist-master.md \
  docs/acceptance/quartz-near-depth-artist-pair.md \
  docs/work/KIKU-T056.md \
  docs/work/KIKU-T058.md \
  docs/work/KIKU-T059.md \
  tests/unit/test_atlas.py \
  tests/unit/test_atlas_consolidation.py \
  tests/unit/test_product_status.py
git commit -m "feat: cut Atlas over to canonical packages"
```

---

### Task 6: Add mirror ledgers, full-resolution links, and Google Sites source pages

**Files:**
- Create: `src/kikuchi_lab/atlas/mirror.py`
- Create: `scripts/atlas_google_mirror.py`
- Create: `tests/unit/test_atlas_mirror.py`
- Create: `docs/atlas/GOOGLE_MIRROR.yml`
- Modify: `src/kikuchi_lab/atlas/catalog.py`
- Modify: `src/kikuchi_lab/atlas/publication.py`
- Modify: `src/kikuchi_lab/atlas/__init__.py`
- Modify: `scripts/build_atlas.py`
- Modify: `scripts/build_public_atlas.py`
- Modify: `tests/unit/test_atlas.py`
- Modify: `tests/unit/test_atlas_publication.py`
- Generate: `dist/google-site/site-inventory.json`
- Generate: `dist/google-site/index.md`
- Generate: `dist/google-site/about.md`
- Generate: `dist/google-site/phases/<slug>.md`

**Interfaces:**
- Produces: `MirrorLedger`, `MirrorProduct`, `load_mirror_ledger(path)`, `public_product_urls(ledger)`, `reconcile_downloaded_phase(canonical_phase_root, downloaded_phase_root)`, `build_google_site_source(registry_path, product_registry_path, mirror_registry_path, output_root)`, and optional `product_urls: Mapping[str, str]` inputs to Atlas builders.
- Public builders use a mirror URL only when its ledger state is `public-verified`; private or merely uploaded links are never emitted into Pages.

- [ ] **Step 1: Write failing mirror safety and page-generation tests**

Create `tests/unit/test_atlas_mirror.py` with:

```python
def test_mirror_ledger_rejects_wrong_account_and_local_mount(tmp_path: Path) -> None:
    path = write_ledger(
        tmp_path,
        account="mich0201@umn.edu",
        local_mount="/Users/Z/Library/CloudStorage/GoogleDrive-mich0201@umn.edu",
    )
    with pytest.raises(ValueError, match="zmichels@umn.edu"):
        load_mirror_ledger(path)


def test_public_urls_include_only_public_verified_products(tmp_path: Path) -> None:
    ledger = load_mirror_ledger(write_mixed_state_ledger(tmp_path))
    assert public_product_urls(ledger) == {
        "quartz-demo": "https://drive.google.com/drive/folders/verified-id"
    }


def test_downloaded_phase_reconciles_every_package_file(
    canonical_phase: Path, downloaded_phase: Path
) -> None:
    result = reconcile_downloaded_phase(
        canonical_phase_root=canonical_phase,
        downloaded_phase_root=downloaded_phase,
    )
    assert result.expected_files == result.verified_files
    assert result.missing == ()
    assert result.mismatched == ()


def test_google_site_source_has_landing_about_and_twelve_phase_pages(
    real_registry_paths: RegistryPaths, complete_verified_mirror: Path, tmp_path: Path
) -> None:
    result = build_google_site_source(
        registry_path=real_registry_paths.phases,
        product_registry_path=real_registry_paths.products,
        mirror_registry_path=complete_verified_mirror,
        output_root=tmp_path,
    )
    assert len(result.phase_pages) == 12
    assert "125 products" in result.index_path.read_text(encoding="utf-8")
    assert "not acquired EBSD patterns" in result.about_path.read_text(encoding="utf-8")
```

Extend publication tests so a MOV product with `web_path` stages the MP4 into Pages, archives the MOV, and records its `full_resolution_url`. Add a package-backed product fixture and assert that archive staging includes every file named by `product-package.yml`, including original provenance and scientific fields, while Pages still contains only web-safe files.

- [ ] **Step 2: Run tests and confirm RED**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_mirror.py tests/unit/test_atlas_publication.py
```

Expected: mirror module collection failure and a publication failure because `web_path` is not preferred.

- [ ] **Step 3: Define the mirror ledger contract**

Initialize `docs/atlas/GOOGLE_MIRROR.yml` as:

```yaml
schema_version: 1
provider: google-drive
account: zmichels@umn.edu
local_mount:
transport: undecided
quota:
  observed_at:
  total_bytes:
  used_bytes:
  free_bytes:
  required_headroom_bytes: 10737418240
root:
  drive_id:
  url:
  access: private
  state: planned
phases: {}
site:
  draft_url: https://sites.google.com/umn.edu/kikuchi-atlas-publishing-test
  public_url:
  audience: university-only
  state: draft
```

The loader must require the exact account, reject a `local_mount` containing `GoogleDrive-mich0201@umn.edu`, validate Google Drive folder URLs/opaque IDs without deriving one from the other, require all 12 phases and all 125 products before state `complete`, and expose public links only at state `public-verified`.

- [ ] **Step 4: Make Atlas and public builders consume verified mirror links**

Add optional parameters:

```python
def build_atlas(
    *,
    registry_path: str | Path,
    product_registry_path: str | Path,
    anchor_catalog_path: str | Path,
    output_root: str | Path,
    product_urls: Mapping[str, str] | None = None,
) -> AtlasBuildResult:
```

and:

```python
def build_public_atlas(
    *,
    registry_path: str | Path,
    product_registry_path: str | Path,
    anchor_catalog_path: str | Path,
    output_root: str | Path,
    stage_archive: bool = False,
    max_web_asset_bytes: int = _DEFAULT_MAX_WEB_ASSET_BYTES,
    mirror_registry_path: str | Path | None = None,
) -> PublicAtlasBuildResult:
```

When `web_path` exists, the public builder uses it as `web.media_path`; it still archives and hashes the authoritative `media_path`. Add:

```python
"delivery": {
    "authoritative_media_format": product.media_format,
    "browser_media_path": web_entry(product.web_path or product.media_path),
    "full_resolution_url": product_urls.get(product.identifier),
}
```

to each inventory record. Append an `open full-resolution package` action only for a public-verified URL.

When `provenance_path.name == "product-package.yml"`, load and validate that package and make `_archive_sources()` return every declared package file plus the manifest itself. Deduplicate identical source paths before content-addressed staging. Do not copy the entire legacy run directory.

- [ ] **Step 5: Generate the initial private mirror skeleton and Site copy**

Implement:

```bash
uv run python scripts/atlas_google_mirror.py initialize \
  --phases docs/atlas/PHASE_REGISTRY.yml \
  --products docs/atlas/PRODUCT_REGISTRY.yml \
  --output docs/atlas/GOOGLE_MIRROR.yml
uv run python scripts/atlas_google_mirror.py build-site-source \
  --phases docs/atlas/PHASE_REGISTRY.yml \
  --products docs/atlas/PRODUCT_REGISTRY.yml \
  --mirror docs/atlas/GOOGLE_MIRROR.yml \
  --output dist/google-site \
  --allow-private-links
```

Expected: the ledger lists 12 phase slugs and 125 product IDs in `planned` state; the generated Site source contains a landing page, about/provenance page, and 12 phase pages but does not claim public verification.

- [ ] **Step 6: Run focused tests and commit**

Run:

```bash
uv run pytest -q tests/unit/test_atlas.py tests/unit/test_atlas_publication.py tests/unit/test_atlas_mirror.py
uv run ruff check \
  src/kikuchi_lab/atlas/catalog.py \
  src/kikuchi_lab/atlas/publication.py \
  src/kikuchi_lab/atlas/mirror.py \
  scripts/build_atlas.py \
  scripts/build_public_atlas.py \
  scripts/atlas_google_mirror.py \
  tests/unit/test_atlas.py \
  tests/unit/test_atlas_publication.py \
  tests/unit/test_atlas_mirror.py
git diff --check
```

Expected: all focused tests pass; no private Drive URL appears in a public build.

```bash
git add \
  src/kikuchi_lab/atlas/catalog.py \
  src/kikuchi_lab/atlas/publication.py \
  src/kikuchi_lab/atlas/mirror.py \
  src/kikuchi_lab/atlas/__init__.py \
  scripts/build_atlas.py \
  scripts/build_public_atlas.py \
  scripts/atlas_google_mirror.py \
  docs/atlas/GOOGLE_MIRROR.yml \
  tests/unit/test_atlas.py \
  tests/unit/test_atlas_publication.py \
  tests/unit/test_atlas_mirror.py
git commit -m "feat: add Atlas mirror publication contracts"
```

---

### Task 7: Build and deploy the first 125-product GitHub Pages release

**Files:**
- Modify: `docs/atlas/RELEASE_METADATA.yml`
- Modify: `docs/atlas/PUBLIC_RELEASE.md`
- Modify: `.github/workflows/deploy-atlas-pages.yml`
- Modify: `tests/unit/test_atlas_release_metadata.py`
- Generate: `dist/atlas-public/site/`
- Generate: `dist/atlas-public/release-inventory.json`
- Generate: `dist/atlas-public/archive/`
- Generate: `dist/atlas-public/kikuchi-atlas-gallery-web-0.2.0-draft.1.zip`
- Generate: `local/atlas/github-pages-verification.json`

**Interfaces:**
- Consumes: the canonical 125-product registry and web-proxy-aware public builder.
- Produces: prerelease tag `atlas-gallery-web-0.2.0-draft.1`, a workflow-pinned candidate Pages deployment, and a verified live 125-product catalogue. This first deployment intentionally has no public Drive links because the Drive permission gate has not passed.

- [ ] **Step 1: Update release-metadata tests before metadata**

Require:

```python
assert metadata["release"]["version"] == "0.2.0-draft"
assert metadata["publication"]["static_site_url"] == (
    "https://zmichels.github.io/kikuchi-atlas/"
)
assert metadata["publication"]["google_drive_root_url"] is None
assert metadata["publication"]["google_site_url"] is None
assert metadata["publication"]["archive_doi"] is None
```

Add a public-inventory assertion for 125 products, all declared web files at or below 26,214,400 bytes, exactly three MOV authoritative records, and no `local/`, `/Users/`, or `file://` string anywhere under `dist/atlas-public/site`.

- [ ] **Step 2: Run release tests and confirm RED**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_release_metadata.py tests/unit/test_atlas_publication.py
```

Expected: version and count failures until release metadata/build output are refreshed.

- [ ] **Step 3: Build the complete candidate**

Update release version to `0.2.0-draft`, add null `google_drive_root_url` and `google_site_url` keys, preserve the null DOI, and document that the new draft is a 12-phase/125-product browser catalogue whose full-resolution UMN mirror is still private.

Run:

```bash
uv run python scripts/build_public_atlas.py --stage-archive
uv run pytest -q tests/unit/test_atlas_publication.py tests/unit/test_atlas_release_metadata.py
rg -n 'local/|/Users/|file://' dist/atlas-public/site
find dist/atlas-public/site/assets -type f -size +26214400c -print
```

Expected: tests pass; the two searches print nothing; build summary reports 125 products in the inventory.

- [ ] **Step 4: Zip, split, and hash the exact Pages site**

Run:

```bash
cd dist/atlas-public/site
zip -qry ../kikuchi-atlas-gallery-web-0.2.0-draft.1.zip .
cd ..
shasum -a 256 kikuchi-atlas-gallery-web-0.2.0-draft.1.zip \
  > kikuchi-atlas-gallery-web-0.2.0-draft.1.zip.sha256
split -b 90m -d -a 3 \
  kikuchi-atlas-gallery-web-0.2.0-draft.1.zip \
  kikuchi-atlas-gallery-web-0.2.0-draft.1.zip.part-
test "$(find . -name 'kikuchi-atlas-gallery-web-0.2.0-draft.1.zip.part-*' | wc -l | tr -d ' ')" -gt 1
cd ../..
```

Expected: the SHA file contains one 64-hex digest and at least two ordered chunks exist.

- [ ] **Step 5: Publish the candidate prerelease and pin the workflow**

Run:

```bash
gh auth status
gh release create atlas-gallery-web-0.2.0-draft.1 \
  dist/atlas-public/kikuchi-atlas-gallery-web-0.2.0-draft.1.zip.part-* \
  dist/atlas-public/kikuchi-atlas-gallery-web-0.2.0-draft.1.zip.sha256 \
  --repo zmichels/kikuchi-atlas \
  --title "Kikuchi Atlas gallery 0.2.0 draft 1" \
  --notes "Twelve-phase, 125-product browser catalogue from canonical phase packages. The full-resolution UMN mirror remains private until its separate access gate." \
  --prerelease
```

Read the literal digest from the SHA file. With `apply_patch`, change workflow defaults to:

```yaml
default: atlas-gallery-web-0.2.0-draft.1
```

and:

```yaml
default: kikuchi-atlas-gallery-web-0.2.0-draft.1.zip.part-*
```

and replace the old pinned digest with the new literal 64-hex digest. Do not use an unexpanded shell variable in YAML.

- [ ] **Step 6: Commit, push, dispatch, and verify**

```bash
git add \
  docs/atlas/RELEASE_METADATA.yml \
  docs/atlas/PUBLIC_RELEASE.md \
  .github/workflows/deploy-atlas-pages.yml \
  tests/unit/test_atlas_release_metadata.py
git commit -m "release: publish 125-product Atlas candidate"
git push origin HEAD
gh workflow run deploy-atlas-pages.yml \
  --repo zmichels/kikuchi-atlas \
  -f release_tag=atlas-gallery-web-0.2.0-draft.1 \
  -f asset_glob='kikuchi-atlas-gallery-web-0.2.0-draft.1.zip.part-*'
RUN_ID="$(gh run list --repo zmichels/kikuchi-atlas \
  --workflow deploy-atlas-pages.yml --limit 1 \
  --json databaseId --jq '.[0].databaseId')"
gh run watch "$RUN_ID" --repo zmichels/kikuchi-atlas --exit-status
```

Then verify:

```bash
curl -fsSL https://zmichels.github.io/kikuchi-atlas/ > /tmp/kikuchi-atlas-index.html
test "$(rg -o '125 individual products' /tmp/kikuchi-atlas-index.html | wc -l | tr -d ' ')" -ge 1
curl -fsSL https://zmichels.github.io/kikuchi-atlas/phases/quartz.html \
  > /tmp/kikuchi-atlas-quartz.html
rg -n 'artist master|60 fps' /tmp/kikuchi-atlas-quartz.html
uv run python scripts/consolidate_atlas_products.py record-github-verification \
  --output local/atlas/github-pages-verification.json \
  --release-tag atlas-gallery-web-0.2.0-draft.1 \
  --workflow-run-id "$RUN_ID" \
  --workflow-conclusion success \
  --site-url https://zmichels.github.io/kikuchi-atlas/ \
  --phase-count 12 \
  --product-count 125 \
  --zip-sha256 "$(awk '{print $1}' dist/atlas-public/kikuchi-atlas-gallery-web-0.2.0-draft.1.zip.sha256)"
```

Expected: workflow succeeds, live index advertises 125 products, and the quartz page names all three new artist-master entries. Also open representative PNG, SVG, MP4, and provenance links in a browser before continuing.

---

### Task 8: Upload and reconcile the private UMN Drive mirror

**Files:**
- Modify: `docs/atlas/GOOGLE_MIRROR.yml`
- Generate locally or remotely: `local/atlas/atlas-mirror.yml`
- Create remotely: `Kikuchi Atlas/atlas-mirror.yml`
- Create remotely: `Kikuchi Atlas/phases/<slug>/products/<product-id>/`

**Interfaces:**
- Consumes: all 12 validated canonical phase trees and the signed-in `zmichels@umn.edu` Google session.
- Produces: a complete, still-private Drive hierarchy whose 12 downloaded phase copies reconcile file-for-file with the canonical package manifests, plus stable root/phase/product folder IDs in `GOOGLE_MIRROR.yml`.

- [ ] **Step 1: Re-read quota and choose the verified transport**

Using the signed-in Chrome session, confirm the visible account is exactly `zmichels@umn.edu` and record the current total, used, and free bytes with an ISO-8601 observation time. Compute:

```bash
CANONICAL_BYTES="$(du -sk local/atlas/phases | awk '{print $1 * 1024}')"
printf '%s\n' "$CANONICAL_BYTES"
```

The upload gate is:

```python
canonical_bytes + 10 * 1024**3 <= live_free_bytes
```

Stop without uploading if false.

If Drive for Desktop is used, add the correct account with user participation and then require:

```bash
CORRECT_MOUNT="/Users/Z/Library/CloudStorage/GoogleDrive-zmichels@umn.edu"
test -d "$CORRECT_MOUNT"
test ! -e "/Users/Z/Library/CloudStorage/GoogleDrive-mich0201@umn.edu/My Drive/Kikuchi Atlas"
```

If the exact correct mount does not exist, use Chrome folder upload instead. Never substitute the existing `mich0201@umn.edu` mount.

- [ ] **Step 2: Create the private root and folder hierarchy**

In My Drive for `zmichels@umn.edu`, create `Kikuchi Atlas`, `phases`, the 12 slug folders, and all product-ID folders. Keep access `Restricted` during upload. Record each opaque folder ID and URL exactly as returned by Drive; do not derive or reformat IDs.

Copy the exact opaque root folder ID and URL shown by Drive into shell variables, then run:

```bash
DRIVE_ROOT_ID='paste-the-exact-opaque-root-id-shown-by-drive'
DRIVE_ROOT_URL='paste-the-exact-root-folder-url-shown-by-drive'
uv run python scripts/atlas_google_mirror.py set-root \
  --mirror docs/atlas/GOOGLE_MIRROR.yml \
  --transport drive-for-desktop \
  --drive-id "$DRIVE_ROOT_ID" \
  --url "$DRIVE_ROOT_URL" \
  --access private \
  --state created
```

Use `--transport chrome-folder-upload` if that is the actual transport. The quoted values are populated from Google's returned values at execution time; do not derive or reformat them.

- [ ] **Step 3: Upload phase by phase without overwriting mismatches**

For a mounted correct account, add a `sync-filesystem` command to `scripts/atlas_google_mirror.py` that:

1. Accepts an explicit source phase and explicit destination phase.
2. Validates the source `phase-package.yml`.
3. Copies absent files through `.partial`.
4. Accepts already-present files only when byte count and SHA-256 match.
5. Writes a same-name/different-byte collision beside the original with `-canonical-<sha16>` before its suffix; it never overwrites or deletes.
6. Marks a product `uploaded` only after every package file is present.

Run it separately for each slug:

```bash
uv run python scripts/atlas_google_mirror.py sync-filesystem \
  --canonical-root local/atlas/phases \
  --destination-root "$CORRECT_MOUNT/My Drive/Kikuchi Atlas/phases" \
  --phase forsterite
```

Run the same exact command once for each of:

```text
ice-ih quartz zircon titanite diamond plagioclase-an52 muscovite-2m1 diopside calcite enstatite pyrope
```

For browser upload, upload the already validated phase folder, wait for Drive's upload queue to finish, and record the same `uploaded` state. Upload `local/atlas/atlas-mirror.yml` last.

- [ ] **Step 4: Reconcile cloud downloads against canonical packages**

Download each remote phase folder into:

```text
local/atlas/remote-verification/<slug>/
```

Then run:

```bash
uv run python scripts/atlas_google_mirror.py reconcile-downloaded \
  --canonical-root local/atlas/phases \
  --download-root local/atlas/remote-verification \
  --mirror docs/atlas/GOOGLE_MIRROR.yml
```

Expected:

```text
reconciled phases=12 products=125 missing=0 mismatched=0
```

The command changes each product to `verified-private`, records the package-manifest digest and verification time, and changes the root to `complete-private`. A displayed filename or displayed size alone may not set this state.

- [ ] **Step 5: Commit the private mirror identities**

Run:

```bash
uv run pytest -q tests/unit/test_atlas_mirror.py
uv run python scripts/atlas_google_mirror.py validate \
  --mirror docs/atlas/GOOGLE_MIRROR.yml \
  --require-state complete-private
git diff --check
```

Expected: tests pass and the ledger reports 12 phases/125 verified-private products.

```bash
git add docs/atlas/GOOGLE_MIRROR.yml
git commit -m "docs: record verified private Atlas mirror"
git push origin HEAD
```

---

### Task 9: Build the Google Site draft and pause at the public permission gate

**Files:**
- Modify: `docs/atlas/GOOGLE_MIRROR.yml`
- Regenerate: `dist/google-site/`
- Modify in Google Sites: existing `Kikuchi Atlas publishing test` draft

**Interfaces:**
- Consumes: `complete-private` Drive mirror, generated landing/about/phase copy, and current live GitHub Pages URLs.
- Produces before the pause: a complete unpublished Google Site draft with 14 pages and tested signed-in links.
- Produces after confirmation: public-verified Drive access and a public-verified Google Site.

- [ ] **Step 1: Regenerate Site copy from the complete private inventory**

Run:

```bash
uv run python scripts/atlas_google_mirror.py build-site-source \
  --phases docs/atlas/PHASE_REGISTRY.yml \
  --products docs/atlas/PRODUCT_REGISTRY.yml \
  --mirror docs/atlas/GOOGLE_MIRROR.yml \
  --output dist/google-site \
  --allow-private-links
```

Expected: landing page says 12 phases/125 products; about page includes source/recipe/checksum/license boundaries; each phase page links to its GitHub Pages phase and private Drive phase folder.

- [ ] **Step 2: Build the draft through signed-in Chrome**

Use the `chrome:control-chrome` skill because this task depends on the user's existing authenticated Chrome profile. Reuse and rename the draft to `Kikuchi Atlas`; keep the proposed path `kikuchi-atlas-publishing-test` unless Google permits a cleaner unused `kikuchi-atlas` path without breaking existing draft state.

Create:

```text
Home
About and provenance
Forsterite
Ice Ih
Quartz
Zircon
Titanite
Diamond
Plagioclase An52
Muscovite 2M1
Diopside
Calcite
Enstatite
Pyrope
```

Paste the generated page copy, add ordinary links to the live GitHub Pages phase and exact Drive phase folder, and optionally add a GitHub Pages embed only if it renders cleanly. Every page must still work without the embed.

- [ ] **Step 3: Test the complete draft while it remains unpublished**

Open all 14 draft pages through Preview. Test every GitHub link and every Drive phase link in the authenticated session. Record the exact draft URL and selected public URL in `GOOGLE_MIRROR.yml`, but retain:

```yaml
site:
  audience: university-only
  state: draft-complete
```

- [ ] **Step 4: Stop and obtain action-time user confirmation**

Present this exact scope before any permission mutation:

```text
Ready for the public gate:
- Change the Kikuchi Atlas Drive root, inherited phase folders, and product folders from Restricted to Anyone with the link / Viewer.
- Change the Google Site audience from University of Minnesota Twin Cities to Public.
- Press Publish for the completed 14-page Site.
No legacy local files will be deleted until logged-out verification passes.
```

Do not continue until the user explicitly confirms this action-time scope.

- [ ] **Step 5: After confirmation, publish Drive and Site**

Through the verified `zmichels@umn.edu` Chrome session:

1. Change only the `Kikuchi Atlas` Drive root to `Anyone with the link` and role `Viewer`; confirm children inherit or explicitly repair exceptions.
2. Change the Google Site published audience to `Public`.
3. Press Publish and confirm the exact public URL.
4. Record root access `public-link`, every phase/product state `public`, Site audience `public`, and Site state `published` in the ledger.
5. Regenerate `local/atlas/atlas-mirror.yml` from the public ledger and upload it as a new Drive version of the existing root manifest.

- [ ] **Step 6: Verify logged-out access before declaring public-verified**

Use a logged-out browser context. Verify:

- Google Site home, About, and all 12 phase pages.
- Drive root and all 12 phase folders.
- At least one public PNG, SVG, MP4, MOV, STL, YAML manifest, and NPZ scientific field where present.
- All GitHub Pages links from the Site.
- All Drive links from the Site.

Download the representative files and compare their SHA-256 values to their canonical package manifests. Only then set the corresponding products and Site to `public-verified`.

Run:

```bash
uv run python scripts/atlas_google_mirror.py validate \
  --mirror docs/atlas/GOOGLE_MIRROR.yml \
  --require-state public-verified
```

Expected: `public mirror phases=12 products=125 site=public-verified`.

- [ ] **Step 7: Commit and push public identities**

```bash
git add docs/atlas/GOOGLE_MIRROR.yml
git commit -m "docs: record public Atlas Google mirror"
git push origin HEAD
```

---

### Task 10: Publish the final link-complete GitHub Pages release

**Files:**
- Modify: `docs/atlas/RELEASE_METADATA.yml`
- Modify: `docs/atlas/PUBLIC_RELEASE.md`
- Modify: `.github/workflows/deploy-atlas-pages.yml`
- Modify: `tests/unit/test_atlas_release_metadata.py`
- Regenerate: `dist/atlas-public/`
- Generate: `dist/atlas-public/kikuchi-atlas-gallery-web-0.2.0-draft.2.zip`
- Modify generated evidence: `local/atlas/github-pages-verification.json`

**Interfaces:**
- Consumes: a `public-verified` mirror ledger.
- Produces: prerelease `atlas-gallery-web-0.2.0-draft.2` and the final live Pages deployment with verified full-resolution package links.

- [ ] **Step 1: Require exact public mirror metadata**

Write the exact public-verified Drive root and Google Site URLs from `GOOGLE_MIRROR.yml` into `RELEASE_METADATA.yml`. Update tests so `google_drive_root_url` and `google_site_url` equal those exact ledger values, and every inventory product has a nonempty `delivery.full_resolution_url`. Preserve `archive_doi: null`.

- [ ] **Step 2: Build and verify the link-complete site**

Run:

```bash
uv run python scripts/build_public_atlas.py \
  --stage-archive \
  --mirror-registry docs/atlas/GOOGLE_MIRROR.yml
uv run pytest -q tests/unit/test_atlas_publication.py tests/unit/test_atlas_release_metadata.py
rg -n 'local/|/Users/|file://' dist/atlas-public/site
```

Expected: tests pass, local-path search returns nothing, and all 125 inventory records carry public Drive URLs.

- [ ] **Step 3: Package and publish draft 2**

Use the Task 7 ZIP/split commands with filename and tag `0.2.0-draft.2`. Create the prerelease with:

```bash
gh release create atlas-gallery-web-0.2.0-draft.2 \
  dist/atlas-public/kikuchi-atlas-gallery-web-0.2.0-draft.2.zip.part-* \
  dist/atlas-public/kikuchi-atlas-gallery-web-0.2.0-draft.2.zip.sha256 \
  --repo zmichels/kikuchi-atlas \
  --title "Kikuchi Atlas gallery 0.2.0 draft 2" \
  --notes "Final 12-phase, 125-product draft catalogue with public-verified UMN Drive full-resolution package links and Google Sites mirror." \
  --prerelease
```

Patch workflow tag, chunk glob, and literal SHA-256 to draft 2.

- [ ] **Step 4: Commit, push, deploy, and verify public links**

```bash
git add \
  docs/atlas/RELEASE_METADATA.yml \
  docs/atlas/PUBLIC_RELEASE.md \
  .github/workflows/deploy-atlas-pages.yml \
  tests/unit/test_atlas_release_metadata.py
git commit -m "release: link the public Atlas mirror"
git push origin HEAD
gh workflow run deploy-atlas-pages.yml \
  --repo zmichels/kikuchi-atlas \
  -f release_tag=atlas-gallery-web-0.2.0-draft.2 \
  -f asset_glob='kikuchi-atlas-gallery-web-0.2.0-draft.2.zip.part-*'
RUN_ID="$(gh run list --repo zmichels/kikuchi-atlas \
  --workflow deploy-atlas-pages.yml --limit 1 \
  --json databaseId --jq '.[0].databaseId')"
gh run watch "$RUN_ID" --repo zmichels/kikuchi-atlas --exit-status
uv run python scripts/consolidate_atlas_products.py record-github-verification \
  --output local/atlas/github-pages-verification.json \
  --release-tag atlas-gallery-web-0.2.0-draft.2 \
  --workflow-run-id "$RUN_ID" \
  --workflow-conclusion success \
  --site-url https://zmichels.github.io/kikuchi-atlas/ \
  --phase-count 12 \
  --product-count 125 \
  --zip-sha256 "$(awk '{print $1}' dist/atlas-public/kikuchi-atlas-gallery-web-0.2.0-draft.2.zip.sha256)"
```

In a logged-out browser, open the live quartz page, follow all three new artist-master full-resolution links, and confirm the Google Site links back to the live catalogue.

---

### Task 11: Delete only verified legacy publishables and close acceptance

**Files:**
- Modify: `src/kikuchi_lab/atlas/consolidation.py`
- Modify: `scripts/consolidate_atlas_products.py`
- Modify: `tests/unit/test_atlas_consolidation.py`
- Create: `docs/acceptance/atlas-consolidation-and-google-mirror.md`
- Modify: `docs/work/KIKU-T085.md`
- Modify: `docs/work/KIKU-T086.md`
- Modify: `docs/work/KIKU-T087.md`
- Modify: `docs/work/KIKU-F012.md`
- Modify: `docs/atlas/ATLAS_MIGRATION.yml`
- Regenerate: `docs/atlas/site/`
- Regenerate: `dist/atlas-public/`

**Interfaces:**
- Consumes: `state: materialized` migration ledger, 125 canonical packages, successful live GitHub deployment, and `public-verified` Drive/Site mirror.
- Produces: a guarded cleanup report, `state: cleaned` ledger, two successful post-delete builds, and a durable acceptance record.

- [ ] **Step 1: Write failing cleanup-gate tests**

Add:

```python
def test_cleanup_refuses_until_all_publication_gates_are_verified(
    fixture_repo: Path,
) -> None:
    with pytest.raises(ValueError, match="publication gates"):
        cleanup_legacy_files(
            ledger_path=fixture_repo / "docs/atlas/ATLAS_MIGRATION.yml",
            mirror_path=fixture_repo / "docs/atlas/GOOGLE_MIRROR.yml",
            github_verification_path=fixture_repo / "missing.json",
            dry_run=False,
        )


def test_cleanup_deletes_only_exact_approved_files(fixture_repo: Path) -> None:
    approved = fixture_repo / "local/legacy/media.png"
    intermediate = fixture_repo / "local/legacy/frames/frame-0001.png"
    cleanup_legacy_files(
        ledger_path=fixture_repo / "docs/atlas/ATLAS_MIGRATION.yml",
        mirror_path=fixture_repo / "docs/atlas/GOOGLE_MIRROR.yml",
        github_verification_path=fixture_repo / "github-verification.json",
        dry_run=False,
    )
    assert not approved.exists()
    assert intermediate.exists()


def test_cleanup_stops_on_source_hash_change(fixture_repo: Path) -> None:
    source = fixture_repo / "local/legacy/media.png"
    source.write_bytes(b"changed after planning")
    with pytest.raises(ValueError, match="source changed"):
        cleanup_legacy_files(
            ledger_path=fixture_repo / "docs/atlas/ATLAS_MIGRATION.yml",
            mirror_path=fixture_repo / "docs/atlas/GOOGLE_MIRROR.yml",
            github_verification_path=fixture_repo / "github-verification.json",
            dry_run=False,
        )
    assert source.exists()
```

- [ ] **Step 2: Implement the complete cleanup gate**

`cleanup_legacy_files()` must require:

```python
assert ledger.state == "materialized"
assert canonical_verification.phase_count == 12
assert canonical_verification.product_count == 125
assert canonical_verification.missing == ()
assert canonical_verification.mismatched == ()
assert mirror.root_state == "public-verified"
assert mirror.site_state == "public-verified"
assert mirror.public_product_count == 125
assert github_verification.phase_count == 12
assert github_verification.product_count == 125
assert github_verification.workflow_conclusion == "success"
```

Group ledger entries by exact source path so a source shared by multiple product packages is handled once. Before moving it, require every canonical destination in that group to validate. Recompute the source hash against `source_sha256`, each canonical hash against `destination_sha256`, require `cleanup_approved: true` on every grouped entry, and move the source to macOS Trash through a collision-safe explicit path rather than recursively deleting a root. Record `trashed_at`, original path, Trash path, digest, and all verified destinations. If Trash is unavailable, stop without deleting.

- [ ] **Step 3: Run a dry-run and inspect the exact cleanup list**

Run:

```bash
uv run python scripts/consolidate_atlas_products.py cleanup \
  --ledger docs/atlas/ATLAS_MIGRATION.yml \
  --mirror docs/atlas/GOOGLE_MIRROR.yml \
  --github-verification local/atlas/github-pages-verification.json \
  --root /Users/Z/Documents/kikuchi \
  --dry-run \
  > local/atlas/cleanup-dry-run.txt
```

Expected: every listed path is an exact ledger file under one of the ten approved roots; no `frames/` sequence, unlisted intermediate, tracked file, entire legacy root, or canonical path appears.

- [ ] **Step 4: Execute the recoverable cleanup**

After inspecting the dry-run:

```bash
uv run python scripts/consolidate_atlas_products.py cleanup \
  --ledger docs/atlas/ATLAS_MIGRATION.yml \
  --mirror docs/atlas/GOOGLE_MIRROR.yml \
  --github-verification local/atlas/github-pages-verification.json \
  --root /Users/Z/Documents/kikuchi
```

Expected: the command reports the exact count and bytes moved to Trash, changes the ledger to `state: cleaned`, and preserves all nonpublishable intermediates. Report the Trash location and recoverability to the user.

- [ ] **Step 5: Prove there is no hidden legacy fallback**

Run:

```bash
uv run python scripts/consolidate_atlas_products.py verify \
  --ledger docs/atlas/ATLAS_MIGRATION.yml \
  --root /Users/Z/Documents/kikuchi
uv run python scripts/build_atlas.py
uv run python scripts/build_public_atlas.py \
  --stage-archive \
  --mirror-registry docs/atlas/GOOGLE_MIRROR.yml
uv run pytest -q \
  tests/unit/test_atlas_packages.py \
  tests/unit/test_atlas_consolidation.py \
  tests/unit/test_atlas_web_proxy.py \
  tests/unit/test_atlas.py \
  tests/unit/test_atlas_publication.py \
  tests/unit/test_atlas_mirror.py \
  tests/unit/test_atlas_release_metadata.py \
  tests/unit/test_product_status.py
uv run python scripts/validate_work_items.py
uv run ruff check \
  src/kikuchi_lab/atlas \
  scripts/build_atlas.py \
  scripts/build_public_atlas.py \
  scripts/build_atlas_web_proxy.py \
  scripts/consolidate_atlas_products.py \
  scripts/atlas_google_mirror.py \
  tests/unit/test_atlas.py \
  tests/unit/test_atlas_packages.py \
  tests/unit/test_atlas_consolidation.py \
  tests/unit/test_atlas_web_proxy.py \
  tests/unit/test_atlas_publication.py \
  tests/unit/test_atlas_mirror.py \
  tests/unit/test_atlas_release_metadata.py \
  tests/unit/test_product_status.py
git diff --check
```

Expected: 12 phases, 125 available products, 125 valid product packages, 12 valid phase packages, no local URLs in the public site, all focused tests pass, work items validate, Ruff passes on the touched scope, and no deleted legacy path is required.

Run the full suite:

```bash
uv run pytest
```

Expected: no regression from the recorded pre-cutover baseline. If the known unrelated adapter failure still reproduces unchanged, record its exact node ID and error in the acceptance record; do not describe the full suite as passing.

- [ ] **Step 6: Write the final acceptance record and close only proven work**

`docs/acceptance/atlas-consolidation-and-google-mirror.md` must record:

- 12 phase slugs and per-phase product counts totaling 125.
- Canonical root and manifest counts.
- Migration-ledger SHA-256 and cleaned file/byte totals.
- The three quartz artist-master authoritative and proxy hashes.
- GitHub repository, release tags, workflow run IDs, pinned ZIP hashes, and live Pages URL.
- Exact public Drive root URL and Google Site URL.
- Drive account, transport, live quota observation, and remaining headroom.
- Download reconciliation results and logged-out media-type checks.
- Cleanup Trash location and recovery note.
- Post-cleanup local/public build summaries and focused/full test results.
- Deviations, especially any dedupe candidate rejected for nonmatching bytes.
- Nonclaims from the approved design.

Mark KIKU-T085, KIKU-T086, and KIKU-T087 `done` only when every checkbox has evidence. Keep KIKU-F012 active if the separate archival DOI remains unresolved; do not mark a DOI criterion complete.

- [ ] **Step 7: Commit and push final acceptance**

```bash
git add \
  src/kikuchi_lab/atlas/consolidation.py \
  scripts/consolidate_atlas_products.py \
  tests/unit/test_atlas_consolidation.py \
  docs/atlas/ATLAS_MIGRATION.yml \
  docs/acceptance/atlas-consolidation-and-google-mirror.md \
  docs/work/KIKU-T085.md \
  docs/work/KIKU-T086.md \
  docs/work/KIKU-T087.md \
  docs/work/KIKU-F012.md
git commit -m "docs: accept Atlas consolidation and mirrors"
git push origin HEAD
```

The final handoff reports the canonical local root, 12/125 counts, live GitHub Pages URL, public Google Site URL, public Drive root URL, cleanup count/recoverability, and any remaining DOI gate.
