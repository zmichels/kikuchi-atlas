from __future__ import annotations

import hashlib

import numpy as np

from kikuchi_lab.model.identity import canonical_json
from kikuchi_lab.model.products import MasterPatternProduct
from kikuchi_lab.model.provenance import SourceRecord
from kikuchi_lab.relief.field import lambert_square_to_directions
from kikuchi_lab.relief.recipes import ReliefSourceExpectation


def canonical_master_metadata(*, projection: str) -> dict[str, object]:
    source = SourceRecord(
        uri="https://example.invalid/forsterite.cif",
        sha256="1" * 64,
        license="CC0-1.0",
        citation="Deterministic spherical-field test fixture.",
    )
    recipe_payload = {"fixture": "spherical-field", "voltage_kv": 20.0}
    recipe_sha256 = hashlib.sha256(canonical_json(recipe_payload).encode()).hexdigest()
    recipe_id = f"recipe-{recipe_sha256[:16]}"
    return {
        "phase": {
            "name": "forsterite",
            "formula": "Mg2SiO4",
            "space_group": {"number": 62, "setting": "P n m a"},
            "lattice": {
                "values": [10.207, 5.980, 4.756, 90.0, 90.0, 90.0],
                "units": "angstrom",
            },
        },
        "source_structure": {
            "identifier": "spherical-field-fixture",
            "sha256": source.sha256,
            "source_id": source.source_id,
            "provenance": source.to_dict(),
        },
        "generator": {"name": "test-fixture", "version": "1"},
        "simulation": {
            "recipe_id": recipe_id,
            "recipe_sha256": recipe_sha256,
            "voltage_kv": 20.0,
        },
        "projection": projection,
        "hemisphere_order": ["north", "south"],
        "energy_kev": 20.0,
        "intensity_units": "raw dynamical intensity",
        "coordinate_frame": "crystal:Pnma-derived-from-Pbnm",
        "provenance_links": [source.source_id, recipe_id],
    }


def analytic_master_product(size: int = 9, *, seam_offset: float = 0.0):
    grid = np.linspace(-1.0, 1.0, size)
    x, y = np.meshgrid(grid, grid)
    upper_dirs = lambert_square_to_directions(x.ravel(), y.ravel(), hemisphere=1)
    lower_dirs = lambert_square_to_directions(x.ravel(), y.ravel(), hemisphere=-1)

    def field(d):
        return 2.0 + 0.25 * d[:, 0] - 0.4 * d[:, 1] + 0.6 * d[:, 2] ** 2

    upper = field(upper_dirs).reshape(size, size)
    lower = field(lower_dirs).reshape(size, size)
    if seam_offset:
        lower[[0, -1], :] += seam_offset
        lower[:, [0, -1]] += seam_offset
    return MasterPatternProduct.from_array(
        np.stack((upper, lower)).astype(np.float32),
        metadata=canonical_master_metadata(projection="Lambert square equal-area"),
    )


def expectation_for(master: MasterPatternProduct) -> ReliefSourceExpectation:
    return ReliefSourceExpectation(
        product_id=master.product_id,
        array_sha256=master.array_sha256,
        file_sha256="f" * 64,
    )
