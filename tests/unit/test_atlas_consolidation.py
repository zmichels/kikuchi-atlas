from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import time

import pytest
import yaml

import kikuchi_lab.atlas.consolidation as consolidation
from kikuchi_lab.atlas.consolidation import (
    MigrationLedger,
    build_migration_ledger,
    materialize_ledger,
    verify_canonical_tree,
    write_migration_ledger,
)
from kikuchi_lab.atlas.packages import validate_product_package


ROOT = Path(__file__).resolve().parents[2]
VERIFICATION_TAG = "atlas-gallery-web-0.2.0-draft.2"
VERIFICATION_RUN_ID = 30193991683
VERIFICATION_SITE_URL = "https://zmichels.github.io/kikuchi-atlas/"
VERIFICATION_ZIP_SHA256 = (
    "d32d21494ae2b9b078d3e59dee7dd241c8474914ade76db7226cbb410875a514"
)


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for directory in (
        "docs/atlas",
        "docs/products",
        "phases/quartz",
        "recipes/demo",
        "local/legacy/frames",
        "local/legacy/selection-bundle",
    ):
        (repo / directory).mkdir(parents=True, exist_ok=True)
    (repo / "phases/quartz/source.yml").write_text("phase: quartz\n", encoding="utf-8")
    (repo / "recipes/demo/quartz.yml").write_text("phase: quartz\n", encoding="utf-8")
    (repo / "local/legacy/demo.svg").write_text("<svg>media</svg>\n", encoding="utf-8")
    (repo / "local/legacy/demo.png").write_bytes(b"png-preview")
    (repo / "local/legacy/demo.json").write_text('{"source": "fixture"}\n', encoding="utf-8")
    (repo / "local/legacy/artist.png").write_bytes(b"artist-preview")
    (repo / "local/legacy/artist.mp4").write_bytes(b"artist-web")
    (repo / "local/legacy/artist.json").write_text('{"artist": true}\n', encoding="utf-8")
    (repo / "local/legacy/frames/frame-0001.png").write_bytes(b"intermediate")

    (repo / "docs/atlas/PHASE_REGISTRY.yml").write_text(
        """\
schema_version: 1
title: Fixture phases
claim_boundary: Fixture-only registry.
phases:
  - slug: quartz
    display_name: Alpha quartz
    family: silica polymorph
    formula: SiO2
    crystal_system: trigonal
    source_status: tracked-source
    source_record: phases/quartz/source.yml
    candidate_reference:
    scope_note: Fixture quartz.
""",
        encoding="utf-8",
    )
    (repo / "docs/atlas/PRODUCT_REGISTRY.yml").write_text(
        """\
schema_version: 1
title: Fixture products
claim_boundary: Fixture-only product registry.
product_families:
  - id: demo-family
    label: Demo family
    coverage: core
    description: Fixture products.
    claim_boundary: Fixture only.
products:
  - id: quartz-demo
    title: Quartz demo
    phase_slugs: [quartz]
    families: [demo-family]
    format: svg
    media_path: local/legacy/demo.svg
    preview_path: local/legacy/demo.png
    bundle_path: local/legacy
    provenance_path: local/legacy/demo.json
    recipe: recipes/demo/quartz.yml
    entrypoint: fixture
    tier: fixture
    state: local-published
    caption: Fixture product.
    orientation: identity
    hero: true
""",
        encoding="utf-8",
    )
    (repo / "docs/products/ARTIFACT_CATALOG.yml").write_text(
        """\
schema_version: 1
title: Fixture artifact catalog
claim_boundary: Fixture only.
entries:
  - id: quartz-artist
    tier: fixture
    phase: quartz
    artifact_path: local/legacy
    files: [artist.json, artist.png, demo.png, artist.mp4]
    recipe: recipes/demo/quartz.yml
    entrypoint: fixture
    state: local-published
""",
        encoding="utf-8",
    )
    (repo / "docs/atlas/CONSOLIDATION.yml").write_text(
        """\
schema_version: 1
canonical_root: local/atlas/phases
legacy_roots:
  - local/legacy
extra_products:
  - id: quartz-artist
    title: Quartz artist master
    phase_slugs: [quartz]
    families: [demo-family]
    format: png
    media_source: local/legacy/demo.png
    preview_source: local/legacy/artist.png
    web_source: local/legacy/artist.mp4
    provenance_source: local/legacy/artist.json
    recipe: recipes/demo/quartz.yml
    entrypoint: fixture
    tier: fixture
    state: local-published
    caption: Fixture intake product.
    orientation: identity
    hero: false
""",
        encoding="utf-8",
    )
    return repo


def _build_fixture_ledger(fixture_repo: Path) -> MigrationLedger:
    return build_migration_ledger(
        registry_path=fixture_repo / "docs/atlas/PHASE_REGISTRY.yml",
        product_registry_path=fixture_repo / "docs/atlas/PRODUCT_REGISTRY.yml",
        artifact_catalog_path=fixture_repo / "docs/products/ARTIFACT_CATALOG.yml",
        consolidation_path=fixture_repo / "docs/atlas/CONSOLIDATION.yml",
        source_commit="a" * 40,
    )


def _write_fixture_ledger(fixture_repo: Path) -> Path:
    ledger_path = fixture_repo / "docs/atlas/ATLAS_MIGRATION.yml"
    write_migration_ledger(_build_fixture_ledger(fixture_repo), ledger_path)
    return ledger_path


def _load_consolidation_cli():
    script = ROOT / "scripts/consolidate_atlas_products.py"
    spec = importlib.util.spec_from_file_location("_atlas_consolidation_cli", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _verification_cli_args(output: Path) -> list[str]:
    return [
        "record-github-verification",
        "--output",
        str(output),
        "--release-tag",
        VERIFICATION_TAG,
        "--workflow-run-id",
        str(VERIFICATION_RUN_ID),
        "--workflow-conclusion",
        "success",
        "--site-url",
        VERIFICATION_SITE_URL,
        "--phase-count",
        "12",
        "--product-count",
        "125",
        "--zip-sha256",
        VERIFICATION_ZIP_SHA256,
    ]


def _verification_kwargs(output: Path, repository_root: Path) -> dict[str, object]:
    return {
        "output_path": output,
        "repository_root": repository_root,
        "release_tag": VERIFICATION_TAG,
        "workflow_run_id": VERIFICATION_RUN_ID,
        "workflow_conclusion": "success",
        "site_url": VERIFICATION_SITE_URL,
        "phase_count": 12,
        "product_count": 125,
        "zip_sha256": VERIFICATION_ZIP_SHA256,
    }


def test_record_github_verification_cli_writes_exact_atomic_record(
    fixture_repo: Path,
) -> None:
    output = fixture_repo / "local/atlas/github-pages-verification.json"

    result = _load_consolidation_cli().main(
        _verification_cli_args(Path("local/atlas/github-pages-verification.json")),
        repository_root=fixture_repo,
    )

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert set(payload) == {
        "schema_version",
        "observed_at",
        "release_tag",
        "workflow_run_id",
        "workflow_conclusion",
        "site_url",
        "phase_count",
        "product_count",
        "zip_sha256",
    }
    assert payload == {
        "schema_version": 1,
        "observed_at": payload["observed_at"],
        "release_tag": VERIFICATION_TAG,
        "workflow_run_id": VERIFICATION_RUN_ID,
        "workflow_conclusion": "success",
        "site_url": VERIFICATION_SITE_URL,
        "phase_count": 12,
        "product_count": 125,
        "zip_sha256": VERIFICATION_ZIP_SHA256,
    }
    observed_at = datetime.fromisoformat(payload["observed_at"].replace("Z", "+00:00"))
    assert observed_at.tzinfo == timezone.utc
    assert not output.with_name(output.name + ".partial").exists()


def test_record_github_verification_normalizes_uppercase_digest(
    fixture_repo: Path,
) -> None:
    output = fixture_repo / "local/atlas/github-pages-verification.json"
    kwargs = _verification_kwargs(output, fixture_repo)
    kwargs["zip_sha256"] = VERIFICATION_ZIP_SHA256.upper()

    result = consolidation.record_github_pages_verification(**kwargs)

    assert result.zip_sha256 == VERIFICATION_ZIP_SHA256
    assert json.loads(output.read_text(encoding="utf-8"))["zip_sha256"] == (
        VERIFICATION_ZIP_SHA256
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("workflow_conclusion", "failure", "conclusion"),
        ("workflow_run_id", 0, "run ID"),
        ("workflow_run_id", "30193991683", "run ID"),
        ("phase_count", 11, "12 phases"),
        ("product_count", 124, "125 products"),
        ("release_tag", "", "release tag"),
        ("release_tag", "atlas-gallery-web-0.2.0", "release tag"),
        ("zip_sha256", "g" * 64, "SHA-256"),
        ("zip_sha256", "a" * 63, "SHA-256"),
        ("site_url", "http://zmichels.github.io/kikuchi-atlas/", "site URL"),
        ("site_url", "https://example.com/kikuchi-atlas/", "site URL"),
    ),
)
def test_record_github_verification_rejects_invalid_observation_without_debris(
    fixture_repo: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    output = fixture_repo / "local/atlas/github-pages-verification.json"
    kwargs = _verification_kwargs(output, fixture_repo)
    kwargs[field] = value

    with pytest.raises(ValueError, match=message):
        consolidation.record_github_pages_verification(**kwargs)

    assert not output.exists()
    assert not output.with_name(output.name + ".partial").exists()


def test_record_github_verification_refuses_symlink_output(
    fixture_repo: Path,
) -> None:
    output = fixture_repo / "local/atlas/github-pages-verification.json"
    output.parent.mkdir(parents=True)
    target = fixture_repo / "outside.json"
    target.write_text('{"preserve": true}\n', encoding="utf-8")
    output.symlink_to(target)

    with pytest.raises(ValueError, match="symlink"):
        consolidation.record_github_pages_verification(
            **_verification_kwargs(output, fixture_repo)
        )

    assert output.is_symlink()
    assert json.loads(target.read_text(encoding="utf-8")) == {"preserve": True}
    assert not output.with_name(output.name + ".partial").exists()


def test_record_github_verification_refuses_output_outside_local_atlas(
    fixture_repo: Path,
) -> None:
    output = fixture_repo / "outside.json"

    with pytest.raises(ValueError, match="local/atlas"):
        consolidation.record_github_pages_verification(
            **_verification_kwargs(output, fixture_repo)
        )

    assert not output.exists()
    assert not output.with_name(output.name + ".partial").exists()


def test_record_github_verification_refuses_symlinked_local_atlas_root(
    fixture_repo: Path,
) -> None:
    target = fixture_repo / "redirected-atlas"
    target.mkdir()
    safe_root = fixture_repo / "local/atlas"
    safe_root.symlink_to(target, target_is_directory=True)
    output = safe_root / "github-pages-verification.json"

    with pytest.raises(ValueError, match="local/atlas.*symlink"):
        consolidation.record_github_pages_verification(
            **_verification_kwargs(output, fixture_repo)
        )

    assert not (target / output.name).exists()
    assert not (target / f"{output.name}.partial").exists()


def test_plan_combines_registry_products_and_three_intake_products(fixture_repo: Path) -> None:
    ledger = _build_fixture_ledger(fixture_repo)
    assert ledger.phase_count == 1
    assert ledger.product_count == 2
    artist = next(item for item in ledger.products if item.product_id == "quartz-artist")
    assert artist.destination_root == (
        "local/atlas/phases/quartz/products/quartz-artist"
    )
    assert all(
        item.source_byte_count > 0 and len(item.source_sha256) == 64
        for item in ledger.files
    )
    assert ledger.retained_source_paths == ()


def test_retained_source_paths_round_trip_through_ledger(fixture_repo: Path) -> None:
    ledger_path = fixture_repo / "docs/atlas/ATLAS_MIGRATION.yml"
    ledger = replace(
        _build_fixture_ledger(fixture_repo),
        retained_source_paths=("local/legacy/selection-bundle",),
    )
    write_migration_ledger(ledger, ledger_path)

    loaded = consolidation._load_migration_ledger(ledger_path)

    assert loaded.retained_source_paths == ("local/legacy/selection-bundle",)


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


def test_plan_rejects_symlinked_source_that_escapes_approved_root(
    fixture_repo: Path,
) -> None:
    source = fixture_repo / "local/legacy/demo.svg"
    outside = fixture_repo / "outside.svg"
    outside.write_text("<svg>outside</svg>\n", encoding="utf-8")
    source.unlink()
    source.symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        _build_fixture_ledger(fixture_repo)


def test_plan_cli_rejects_output_inside_canonical_root_without_writing(
    fixture_repo: Path,
) -> None:
    output = fixture_repo / (
        "local/atlas/phases/quartz/products/escape/product-package.yml"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/consolidate_atlas_products.py"),
            "plan",
            "--registry",
            str(fixture_repo / "docs/atlas/PHASE_REGISTRY.yml"),
            "--products",
            str(fixture_repo / "docs/atlas/PRODUCT_REGISTRY.yml"),
            "--catalog",
            str(fixture_repo / "docs/products/ARTIFACT_CATALOG.yml"),
            "--policy",
            str(fixture_repo / "docs/atlas/CONSOLIDATION.yml"),
            "--output",
            str(output),
            "--source-commit",
            "a" * 40,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "canonical root" in result.stderr
    assert not output.exists()


def test_plan_cli_anchors_canonical_root_to_registry_with_relocated_policy(
    fixture_repo: Path,
) -> None:
    original_policy = fixture_repo / "docs/atlas/CONSOLIDATION.yml"
    relocated_policy = fixture_repo.parent / "relocated/CONSOLIDATION.yml"
    relocated_policy.parent.mkdir()
    relocated_policy.write_text(
        original_policy.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    policy_link = fixture_repo / "relocated-policy.yml"
    policy_link.symlink_to(relocated_policy)
    output = fixture_repo / (
        "local/atlas/phases/quartz/products/escape/product-package.yml"
    )
    output.parent.mkdir(parents=True)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/consolidate_atlas_products.py"),
            "plan",
            "--registry",
            str(fixture_repo / "docs/atlas/PHASE_REGISTRY.yml"),
            "--products",
            str(fixture_repo / "docs/atlas/PRODUCT_REGISTRY.yml"),
            "--catalog",
            str(fixture_repo / "docs/products/ARTIFACT_CATALOG.yml"),
            "--policy",
            str(policy_link),
            "--output",
            str(output),
            "--source-commit",
            "a" * 40,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "canonical root" in result.stderr
    assert not output.exists()


def test_materialize_copies_to_partial_then_verifies_and_publishes(
    fixture_repo: Path,
) -> None:
    ledger_path = _write_fixture_ledger(fixture_repo)

    result = materialize_ledger(ledger_path, repository_root=fixture_repo)

    package = fixture_repo / (
        "local/atlas/phases/quartz/products/quartz-demo/product-package.yml"
    )
    assert result.state == "materialized"
    assert validate_product_package(package).product_id == "quartz-demo"
    assert not tuple(package.parent.rglob("*.partial"))


def test_materialize_resumes_matching_destination_without_rewriting(
    fixture_repo: Path,
) -> None:
    ledger_path = _write_fixture_ledger(fixture_repo)
    first = materialize_ledger(ledger_path, repository_root=fixture_repo)
    media = fixture_repo / first.files[0].destination_path
    before = media.stat().st_mtime_ns
    time.sleep(0.001)

    materialize_ledger(ledger_path, repository_root=fixture_repo)

    assert media.stat().st_mtime_ns == before


def test_materialize_refuses_existing_different_bytes(fixture_repo: Path) -> None:
    ledger_path = _write_fixture_ledger(fixture_repo)
    destination = fixture_repo / (
        "local/atlas/phases/quartz/products/quartz-demo/media/demo.svg"
    )
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"different")

    with pytest.raises(ValueError, match="refusing to overwrite"):
        materialize_ledger(ledger_path, repository_root=fixture_repo)


def test_materialize_rejects_changed_source_before_copy(fixture_repo: Path) -> None:
    ledger_path = _write_fixture_ledger(fixture_repo)
    (fixture_repo / "local/legacy/demo.svg").write_text(
        "<svg>other</svg>\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="source SHA-256 changed"):
        materialize_ledger(ledger_path, repository_root=fixture_repo)


def test_verify_canonical_tree_reports_complete_inventory(fixture_repo: Path) -> None:
    ledger_path = _write_fixture_ledger(fixture_repo)
    materialize_ledger(ledger_path, repository_root=fixture_repo)

    result = verify_canonical_tree(ledger_path, repository_root=fixture_repo)

    assert result.phase_count == 1
    assert result.product_count == 2
    assert result.missing_count == 0
    assert result.mismatched_count == 0
    assert result.symlink_count == 0


def test_registry_rewrite_refuses_planned_ledger_without_touching_registry(
    fixture_repo: Path,
) -> None:
    ledger_path = _write_fixture_ledger(fixture_repo)
    products = fixture_repo / "docs/atlas/PRODUCT_REGISTRY.yml"
    before = products.read_bytes()

    with pytest.raises(ValueError, match="materialized"):
        consolidation.rewrite_product_registry(
            ledger_path=ledger_path,
            product_registry_path=products,
            consolidation_path=fixture_repo / "docs/atlas/CONSOLIDATION.yml",
            repository_root=fixture_repo,
        )

    assert products.read_bytes() == before
    assert not products.with_name(products.name + ".generated").exists()


def test_registry_cutover_order_adds_intakes_exactly_once() -> None:
    assert consolidation._registry_cutover_order(
        ("existing-a", "existing-b"),
        {"existing-a", "existing-b", "intake"},
        ("intake",),
    ) == ("existing-a", "existing-b", "intake")
    assert consolidation._registry_cutover_order(
        ("existing-a", "existing-b", "intake"),
        {"existing-a", "existing-b", "intake"},
        ("intake",),
    ) == ("existing-a", "existing-b", "intake")
    with pytest.raises(ValueError, match="partially"):
        consolidation._registry_cutover_order(
            ("existing-a", "intake"),
            {"existing-a", "existing-b", "intake"},
            ("intake", "other-intake"),
        )


def _initialize_fixture_git_repository(fixture_repo: Path) -> None:
    subprocess.run(
        ["git", "init", "-q"],
        cwd=fixture_repo,
        check=True,
    )
    subprocess.run(
        ["git", "add", "."],
        cwd=fixture_repo,
        check=True,
    )


def _prepare_allowed_audit_fixture(fixture_repo: Path) -> tuple[Path, Path]:
    ledger_path = _write_fixture_ledger(fixture_repo)
    materialize_ledger(ledger_path, repository_root=fixture_repo)
    products = yaml.safe_load(
        (fixture_repo / "docs/atlas/PRODUCT_REGISTRY.yml").read_text(encoding="utf-8")
    )
    record = products["products"][0]
    package = "local/atlas/phases/quartz/products/quartz-demo"
    record.update(
        {
            "media_path": f"{package}/media/demo.svg",
            "preview_path": f"{package}/previews/demo.png",
            "bundle_path": package,
            "provenance_path": f"{package}/product-package.yml",
        }
    )
    (fixture_repo / "docs/atlas/PRODUCT_REGISTRY.yml").write_text(
        yaml.safe_dump(products, sort_keys=False),
        encoding="utf-8",
    )
    (fixture_repo / "docs/products/ARTIFACT_CATALOG.yml").write_text(
        """\
schema_version: 1
title: Fixture artifact catalog
claim_boundary: Fixture only.
entries:
  - id: five-phase-orientation-gallery
    tier: review-proof
    phase: quartz
    artifact_path: local/legacy/orientation-gallery
    files: [comparison.png]
    recipe: recipes/demo/quartz.yml
    entrypoint: fixture
    state: tracked-review-proof
""",
        encoding="utf-8",
    )
    scripts = fixture_repo / "scripts"
    scripts.mkdir()
    (scripts / "render_direct_reflector_rotation.py").write_text(
        'SELECTION = Path("local/legacy/demo.svg")\n',
        encoding="utf-8",
    )
    acceptance = fixture_repo / "docs/acceptance"
    acceptance.mkdir()
    (acceptance / "historical.md").write_text(
        "Original production root: `local/legacy/original-run`.\n",
        encoding="utf-8",
    )
    _initialize_fixture_git_repository(fixture_repo)
    output = fixture_repo / "docs/atlas/LEGACY_PATH_AUDIT.yml"
    return ledger_path, output


def test_path_audit_rejects_publishable_registry_legacy_reference(
    fixture_repo: Path,
) -> None:
    ledger_path = _write_fixture_ledger(fixture_repo)
    materialize_ledger(ledger_path, repository_root=fixture_repo)
    _initialize_fixture_git_repository(fixture_repo)
    output = fixture_repo / "docs/atlas/LEGACY_PATH_AUDIT.yml"

    with pytest.raises(ValueError, match="publishable legacy references"):
        consolidation.audit_legacy_paths(
            ledger_path=ledger_path,
            repository_root=fixture_repo,
            output_path=output,
        )

    payload = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert payload["publishable_legacy_reference_count"] > 0


def test_path_audit_records_only_allowed_reference_classifications(
    fixture_repo: Path,
) -> None:
    ledger_path, output = _prepare_allowed_audit_fixture(fixture_repo)

    result = consolidation.audit_legacy_paths(
        ledger_path=ledger_path,
        repository_root=fixture_repo,
        output_path=output,
    )

    assert result.publishable_legacy_reference_count == 0
    payload = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert {item["classification"] for item in payload["allowed_references"]} == {
        "nonpublishable-scientific-input",
        "historical-reproduction-evidence",
    }
    assert all(item["reason"] for item in payload["allowed_references"])
    script_reference = next(
        item
        for item in payload["allowed_references"]
        if item["file"] == "scripts/render_direct_reflector_rotation.py"
    )
    assert script_reference["classification"] == "nonpublishable-scientific-input"
    canonical_provenance = next(
        item
        for item in payload["allowed_references"]
        if item["file"].endswith("/provenance/release-metadata.yml")
    )
    assert canonical_provenance["classification"] == "historical-reproduction-evidence"

    site = fixture_repo / "docs/atlas/site"
    site.mkdir()
    (site / "index.html").write_text(
        '<a href="../../../local/legacy/demo.svg">legacy publication</a>\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="publishable legacy references"):
        consolidation.audit_legacy_paths(
            ledger_path=ledger_path,
            repository_root=fixture_repo,
            output_path=output,
        )


def test_path_audit_discovers_tracked_readme_legacy_output(
    fixture_repo: Path,
) -> None:
    ledger_path, output = _prepare_allowed_audit_fixture(fixture_repo)
    (fixture_repo / "README.md").write_text(
        "Render with `--output local/legacy/readme-output`.\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "README.md"], cwd=fixture_repo, check=True)

    with pytest.raises(ValueError, match=r"first=README\.md:1"):
        consolidation.audit_legacy_paths(
            ledger_path=ledger_path,
            repository_root=fixture_repo,
            output_path=output,
        )


@pytest.mark.parametrize(
    "live_output_line",
    (
        '--output local/legacy/live-output',
        'default=ROOT / "local/legacy/live-output"',
        'else ROOT / "local/legacy/live-output"',
        'output_root = ROOT / "local/legacy/live-output"',
    ),
)
def test_path_audit_rejects_live_script_output_roots(
    fixture_repo: Path,
    live_output_line: str,
) -> None:
    ledger_path, output = _prepare_allowed_audit_fixture(fixture_repo)
    script = fixture_repo / "scripts/live_output.py"
    script.write_text(f"{live_output_line}\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "scripts/live_output.py"],
        cwd=fixture_repo,
        check=True,
    )

    with pytest.raises(ValueError, match=r"first=scripts/live_output\.py:1"):
        consolidation.audit_legacy_paths(
            ledger_path=ledger_path,
            repository_root=fixture_repo,
            output_path=output,
        )


@pytest.mark.parametrize(
    "source_paths",
    (
        (),
        (PurePosixPath("local/other/verified-source.dat"),),
        (
            PurePosixPath("local")
            / "relief-globes/future-publication/verified-source.dat",
        ),
    ),
)
def test_path_audit_rejects_unlisted_nonmarker_script_path(
    source_paths: tuple[PurePosixPath, ...],
) -> None:
    legacy_path = PurePosixPath("local") / "relief-globes/future-publication"
    classification = consolidation._allowed_reference(
        file=PurePosixPath("scripts/future_publication.py"),
        line_text=f'DESTINATION = Path("{legacy_path}")',
        legacy_path=legacy_path.as_posix(),
        source_paths=source_paths,
        orientation_gallery_root=None,
    )

    assert classification is None
