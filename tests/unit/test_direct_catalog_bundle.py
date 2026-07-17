from __future__ import annotations

import errno
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from kikuchi_lab.art_products import build_art_band_catalog_from_evidence
from kikuchi_lab.art_products.contracts import ArtBandCatalog
from kikuchi_lab.artifacts import BundleExistsError, PartialBundleError
from kikuchi_lab.kinematical.kikuchipy_adapter import build_direct_reflector_evidence
from kikuchi_lab.kinematical.reflector_evidence import (
    DirectReflectorEvidence,
    load_direct_reflector_recipe,
)
from kikuchi_lab.model.identity import canonical_json, stable_id
from kikuchi_lab.sources.structure import load_structure_record


ROOT = Path(__file__).parents[2]
INVENTORY = {
    "art-band-catalog.json",
    "catalog-ledger.json",
    "direct-reflector-recipe.json",
    "manifest.json",
    "reflector-evidence-ledger.json",
    "reflector-evidence.npz",
    "scientific-claim.txt",
}
NPZ_KEYS = (
    "bragg_half_width_rad",
    "dspacing_angstrom",
    "hkl",
    "normal_crystal",
    "normalized_weight",
    "structure_factor_magnitude",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def direct_inputs() -> dict[str, object]:
    recipe_path = ROOT / "recipes/reflectors/ice-ih-art-bands.yml"
    recipe = load_direct_reflector_recipe(recipe_path)
    source = load_structure_record(recipe_path.parent / recipe.source_record)
    evidence = build_direct_reflector_evidence(source, recipe)
    return {
        "source": source,
        "recipe": recipe,
        "evidence": evidence,
        "catalog": build_art_band_catalog_from_evidence(evidence),
    }


def test_direct_bundle_has_exact_inventory_npz_schema_and_linked_ledgers(
    direct_inputs: dict[str, object],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.direct_catalog_bundle import (
        write_direct_art_catalog_bundle,
    )

    result = write_direct_art_catalog_bundle(tmp_path, **direct_inputs)
    source = direct_inputs["source"]
    recipe = direct_inputs["recipe"]
    evidence = direct_inputs["evidence"]
    catalog = direct_inputs["catalog"]
    assert isinstance(evidence, DirectReflectorEvidence)
    assert isinstance(catalog, ArtBandCatalog)

    assert {path.name for path in result.path.iterdir()} == INVENTORY
    manifest_path = result.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_path.read_text(encoding="utf-8") == canonical_json(manifest)
    assert set(manifest["files"]) == INVENTORY - {"manifest.json"}
    assert list(manifest["files"]) == sorted(manifest["files"])
    assert result.run_id == stable_id("direct-art-catalog-run", manifest["run_identity"])
    assert result.path == tmp_path / result.run_id
    assert result.manifest_sha256 == _sha256(manifest_path)
    for relative, record in manifest["files"].items():
        path = result.path / relative
        assert record == {"bytes": path.stat().st_size, "sha256": _sha256(path)}

    with np.load(result.path / "reflector-evidence.npz", allow_pickle=False) as arrays:
        assert tuple(arrays.files) == NPZ_KEYS
        assert arrays["hkl"].dtype == np.dtype("<i4")
        for key in NPZ_KEYS:
            if key != "hkl":
                assert arrays[key].dtype == np.dtype("<f8")
        np.testing.assert_array_equal(arrays["hkl"], evidence.hkl)
        np.testing.assert_allclose(arrays["normal_crystal"], evidence.normal_crystal)
        np.testing.assert_allclose(arrays["dspacing_angstrom"], evidence.dspacing_angstrom)
        np.testing.assert_allclose(arrays["bragg_half_width_rad"], evidence.bragg_half_width_rad)
        np.testing.assert_allclose(
            arrays["structure_factor_magnitude"],
            evidence.structure_factor_magnitude,
        )
        np.testing.assert_allclose(arrays["normalized_weight"], evidence.normalized_weight)

    recipe_snapshot = json.loads(
        (result.path / "direct-reflector-recipe.json").read_text(encoding="utf-8")
    )
    evidence_ledger = json.loads(
        (result.path / "reflector-evidence-ledger.json").read_text(encoding="utf-8")
    )
    catalog_ledger = json.loads((result.path / "catalog-ledger.json").read_text(encoding="utf-8"))
    assert recipe_snapshot == {
        "calculation_id": recipe.calculation_id,
        "content": recipe.to_dict(),
        "weighting_id": recipe.weighting_id,
    }
    assert evidence_ledger["evidence_id"] == evidence.evidence_id
    assert evidence_ledger["source_structure_id"] == source.identifier
    assert evidence_ledger["source_structure_sha256"] == source.sha256
    assert evidence_ledger["calculation_id"] == recipe.calculation_id
    assert evidence_ledger["weighting_id"] == recipe.weighting_id
    assert evidence_ledger["ledger"]["simulation_count"] == 0
    assert catalog_ledger["evidence_id"] == evidence.evidence_id
    assert catalog_ledger["catalog_id"] == catalog.catalog_id
    assert catalog_ledger["member_count"] == len(catalog.members)
    assert catalog_ledger["eligible_member_count"] == sum(
        member.tattoo_eligible for member in catalog.members
    )
    claim = (result.path / "scientific-claim.txt").read_text(encoding="utf-8")
    assert "presentation-only" in claim
    assert "master-pattern simulation" in claim


@pytest.mark.parametrize(
    "forgery",
    ["catalog_id", "catalog_link", "source_checksum"],
)
def test_direct_bundle_rejects_forged_ids_and_linkage_before_output_mutation(
    direct_inputs: dict[str, object],
    tmp_path: Path,
    forgery: str,
) -> None:
    from kikuchi_lab.art_products.direct_catalog_bundle import (
        write_direct_art_catalog_bundle,
    )

    inputs = dict(direct_inputs)
    if forgery == "catalog_id":
        catalog = replace(inputs["catalog"])
        object.__setattr__(catalog, "catalog_id", "art-band-catalog-forged")
        inputs["catalog"] = catalog
    elif forgery == "catalog_link":
        evidence = inputs["evidence"]
        assert isinstance(evidence, DirectReflectorEvidence)
        inputs["evidence"] = replace(
            evidence,
            calculation_id="reflector-calculation-forged",
        )
    else:
        inputs["source"] = replace(inputs["source"], sha256="0" * 64)

    output_root = tmp_path / forgery
    with pytest.raises(ValueError):
        write_direct_art_catalog_bundle(output_root, **inputs)
    assert not output_root.exists()


def test_direct_bundle_requires_eleven_tattoo_eligible_members_before_publication(
    direct_inputs: dict[str, object],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.direct_catalog_bundle import (
        write_direct_art_catalog_bundle,
    )

    catalog = direct_inputs["catalog"]
    assert isinstance(catalog, ArtBandCatalog)
    too_small = replace(catalog, members=catalog.members[:10])
    output_root = tmp_path / "too-small"

    with pytest.raises(ValueError, match="at least 11 tattoo-eligible members"):
        write_direct_art_catalog_bundle(
            output_root,
            **{**direct_inputs, "catalog": too_small},
        )
    assert not output_root.exists()


def test_direct_bundle_identity_is_stable_across_output_roots(
    direct_inputs: dict[str, object],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.direct_catalog_bundle import (
        write_direct_art_catalog_bundle,
    )

    first = write_direct_art_catalog_bundle(tmp_path / "one", **direct_inputs)
    second = write_direct_art_catalog_bundle(tmp_path / "different" / "nested", **direct_inputs)

    assert first.run_id == second.run_id
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.path.parent != second.path.parent


def test_direct_bundle_refuses_completed_and_partial_publication_without_overwrite(
    direct_inputs: dict[str, object],
    tmp_path: Path,
) -> None:
    from kikuchi_lab.art_products.direct_catalog_bundle import (
        write_direct_art_catalog_bundle,
    )

    completed_root = tmp_path / "completed"
    result = write_direct_art_catalog_bundle(completed_root, **direct_inputs)
    manifest_before = (result.path / "manifest.json").read_bytes()
    with pytest.raises(BundleExistsError, match="completed bundle already exists"):
        write_direct_art_catalog_bundle(completed_root, **direct_inputs)
    assert (result.path / "manifest.json").read_bytes() == manifest_before

    partial_root = tmp_path / "partial"
    partial_root.mkdir()
    partial = partial_root / f".{result.run_id}.partial-retained"
    partial.mkdir()
    sentinel = partial / "diagnostic.txt"
    sentinel.write_text("retain me", encoding="utf-8")
    with pytest.raises(PartialBundleError, match="partial bundle already exists"):
        write_direct_art_catalog_bundle(partial_root, **direct_inputs)
    assert sentinel.read_text(encoding="utf-8") == "retain me"
    assert list(partial_root.iterdir()) == [partial]


def test_direct_bundle_mid_write_failure_retains_partial_and_blocks_retry(
    direct_inputs: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kikuchi_lab.art_products.direct_catalog_bundle as bundle_module

    def fail_write(root: Path, _payload: object) -> dict[str, dict[str, object]]:
        (root / "diagnostic.txt").write_text("write failed", encoding="utf-8")
        raise OSError("disk full")

    monkeypatch.setattr(bundle_module, "_write_contents", fail_write)
    output_root = tmp_path / "failed"
    with pytest.raises(OSError, match="disk full"):
        bundle_module.write_direct_art_catalog_bundle(output_root, **direct_inputs)

    partials = list(output_root.glob(".*.partial-*"))
    assert len(partials) == 1
    assert (partials[0] / "diagnostic.txt").read_text(encoding="utf-8") == "write failed"
    assert not list(output_root.glob("direct-art-catalog-run-*"))

    monkeypatch.undo()
    with pytest.raises(PartialBundleError, match="partial bundle already exists"):
        bundle_module.write_direct_art_catalog_bundle(output_root, **direct_inputs)


def test_direct_bundle_promotion_race_never_replaces_winner(
    direct_inputs: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kikuchi_lab.art_products.direct_catalog_bundle as bundle_module

    winner_payload = b"winner"

    def lose_race(partial: Path, completed: Path) -> None:
        completed.mkdir()
        (completed / "winner.txt").write_bytes(winner_payload)
        raise OSError(errno.EEXIST, "already exists")

    monkeypatch.setattr(bundle_module, "_promote_directory_no_replace", lose_race)

    with pytest.raises(BundleExistsError, match="completed bundle already exists"):
        bundle_module.write_direct_art_catalog_bundle(tmp_path, **direct_inputs)

    completed = next(tmp_path.glob("direct-art-catalog-run-*"))
    assert (completed / "winner.txt").read_bytes() == winner_payload
    assert len(list(tmp_path.glob(".*.partial-*"))) == 1
