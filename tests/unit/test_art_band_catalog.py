from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from kikuchi_lab.near_depth.overlap import AxialBandSet
from kikuchi_lab.spherical_intensity.presentation import PresentationSource


RECIPE = (
    Path(__file__).resolve().parents[2] / "recipes" / "art" / "ice-ih-band-catalog.yml"
)
WEIGHTS = np.array(
    [0.8, 1.0, 0.8, 0.7, 0.5, 0.6, 0.5, 0.4, 0.1, 0.3, 0.05, 0.2],
    dtype=np.float64,
)
HKLS = np.array(
    [
        [4, 0, 0],
        [2, 0, 0],
        [3, 0, 0],
        [1, 0, 0],
        [2, 1, 0],
        [1, 1, 0],
        [3, 1, 0],
        [1, 2, 0],
        [2, 2, 1],
        [1, 0, 1],
        [2, 0, 1],
        [3, 0, 1],
    ],
    dtype=np.int32,
)


def _source(
    *,
    weights: np.ndarray = WEIGHTS,
    hkls: np.ndarray = HKLS,
) -> PresentationSource:
    angles = np.linspace(0.0, 2.0 * np.pi, len(hkls), endpoint=False)
    normals = np.column_stack((np.cos(angles), np.sin(angles), np.zeros(len(hkls))))
    axial_bands = AxialBandSet(
        hkl=hkls,
        normals=normals,
        theta_radian=np.linspace(0.01, 0.021, len(hkls)),
        structure_factor_abs=np.linspace(24.0, 13.0, len(hkls)),
    )
    valid = np.zeros((3, 3), dtype=bool)
    valid[1, 1] = True
    return PresentationSource(
        toned_master=np.zeros((2, 3, 3), dtype=np.float32),
        axial_bands=axial_bands,
        band_weights=weights,
        overlap_normalization=1.0,
        upper_directions=np.array([[0.0, 0.0, 1.0]]),
        upper_valid=valid,
        gain=0.0,
        ceiling=0.9,
        ledger={"scientific_claim": "presentation_only"},
    )


def _build(source: PresentationSource | None = None, *, threshold: float = 0.10):
    from kikuchi_lab.art_products.catalog import build_art_band_catalog

    return build_art_band_catalog(
        source or _source(),
        source_structure_id="structure-ice-ih",
        source_structure_sha256="a" * 64,
        source_recipe_id="recipe-source-0123456789abcdef",
        presentation_recipe_id="recipe-presentation-0123456789abcdef",
        eligibility_min_weight=threshold,
    )


def _write_snapshot(path: Path) -> dict[str, Any]:
    from kikuchi_lab.art_products.catalog import write_art_band_catalog

    write_art_band_catalog(path, _build())
    return json.loads(path.read_text(encoding="utf-8"))


def test_catalog_snapshot_is_canonical_and_round_trips(tmp_path: Path) -> None:
    from kikuchi_lab.art_products.catalog import (
        load_art_band_catalog,
        write_art_band_catalog,
    )

    path = tmp_path / "catalog.json"
    catalog = _build()

    write_art_band_catalog(path, catalog)
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    loaded = load_art_band_catalog(path)

    assert set(payload) == {"catalog_id", "content"}
    assert payload == {"catalog_id": catalog.catalog_id, "content": catalog.to_dict()}
    assert raw == json.dumps(payload, indent=2, sort_keys=True) + "\n"
    assert hashlib.sha256(raw.encode("utf-8")).hexdigest() == (
        "571702ba869de8f26135689c244e091fd38631e7c86e6372465ae3420d436105"
    )
    assert loaded.catalog_id == catalog.catalog_id
    assert loaded.to_dict() == catalog.to_dict()


@pytest.mark.parametrize("id_field", ["catalog_id", "member_id"])
def test_catalog_snapshot_rejects_forged_ids(tmp_path: Path, id_field: str) -> None:
    from kikuchi_lab.art_products.catalog import load_art_band_catalog

    path = tmp_path / "catalog.json"
    payload = _write_snapshot(path)
    if id_field == "catalog_id":
        payload["catalog_id"] = "art-band-catalog-forged"
    else:
        payload["content"]["members"][0]["member_id"] = "art-band-member-forged"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=id_field):
        load_art_band_catalog(path)


def _drop_envelope_key(payload: dict[str, Any]) -> None:
    del payload["catalog_id"]


def _add_envelope_key(payload: dict[str, Any]) -> None:
    payload["extra"] = True


def _drop_content_key(payload: dict[str, Any]) -> None:
    del payload["content"]["presentation_recipe_id"]


def _add_content_key(payload: dict[str, Any]) -> None:
    payload["content"]["extra"] = True


def _drop_member_key(payload: dict[str, Any]) -> None:
    del payload["content"]["members"][0]["normal_crystal"]


def _add_member_key(payload: dict[str, Any]) -> None:
    payload["content"]["members"][0]["extra"] = True


@pytest.mark.parametrize(
    "mutate",
    [
        _drop_envelope_key,
        _add_envelope_key,
        _drop_content_key,
        _add_content_key,
        _drop_member_key,
        _add_member_key,
    ],
)
def test_catalog_snapshot_rejects_missing_and_additional_keys(
    tmp_path: Path,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    from kikuchi_lab.art_products.catalog import load_art_band_catalog

    path = tmp_path / "catalog.json"
    payload = _write_snapshot(path)
    mutate(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="keys"):
        load_art_band_catalog(path)


def test_catalog_builder_rejects_fewer_than_four_unique_eligible_weight_blocks() -> None:
    weights = np.array([1.0] * 4 + [0.5] * 4 + [0.1] * 4)

    with pytest.raises(ValueError, match="four unique eligible weight blocks"):
        _build(_source(weights=weights))


def test_catalog_builder_rejects_duplicate_hkls() -> None:
    duplicate_hkls = HKLS.copy()
    duplicate_hkls[-1] = duplicate_hkls[0]

    with pytest.raises(ValueError, match="duplicate HKL"):
        _build(_source(hkls=duplicate_hkls))


@pytest.mark.parametrize("threshold", [0.0, -0.1])
def test_catalog_builder_rejects_nonpositive_threshold(threshold: float) -> None:
    with pytest.raises(ValueError, match="eligibility_min_weight.*positive"):
        _build(threshold=threshold)


def test_catalog_builder_rejects_source_weight_length_mismatch() -> None:
    source = _source()
    object.__setattr__(source, "band_weights", source.band_weights[:-1])

    with pytest.raises(ValueError, match="source.*weight.*length"):
        _build(source)


def test_ice_catalog_recipe_tracks_the_approved_policy() -> None:
    assert yaml.safe_load(RECIPE.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "name": "ice-ih-band-catalog",
        "source_oriented_recipe": "../spherical/ice-ih-oriented-s2-proof.yml",
        "eligibility_min_weight": 0.08,
        "globe_cohort_count": 4,
        "tie_policy": "keep_equal_weights_together",
        "ranking": "normalized_structure_factor_weight",
        "scientific_claim": "presentation_only",
        "product_class": "science_art",
    }
