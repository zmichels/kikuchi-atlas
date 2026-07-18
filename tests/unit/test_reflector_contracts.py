from __future__ import annotations

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from kikuchi_lab.reflectors.contracts import ReflectorCatalog, ReflectorMember


def test_member_requires_unit_normal_and_stable_intrinsic_id() -> None:
    member = ReflectorMember((1, 0, 0), [1.0, 0.0, 0.0], 2.0, 0.01, 12.0, 1.0)

    assert member.member_id.startswith("reflector-member-")
    assert member.member_id == ReflectorMember(
        (1, 0, 0), [1.0, 0.0, 0.0], 2.0, 0.01, 12.0, 1.0
    ).member_id
    with pytest.raises(ValueError, match="unit normal"):
        ReflectorMember((1, 0, 0), [2.0, 0.0, 0.0], 2.0, 0.01, 12.0, 1.0)


def test_member_owns_an_immutable_little_endian_normal() -> None:
    normal = np.array([1.0, 0.0, 0.0], dtype=">f8")
    member = ReflectorMember((1, 0, 0), normal, 2.0, 0.01, 12.0, 1.0)
    normal[0] = 0.0

    assert member.normal_crystal.dtype == np.dtype("<f8")
    assert member.normal_crystal.tolist() == [1.0, 0.0, 0.0]
    assert not member.normal_crystal.flags.writeable
    with pytest.raises(ValueError, match="read-only"):
        member.normal_crystal[0] = 0.0


def test_catalog_identity_uses_content_not_local_paths() -> None:
    member = ReflectorMember((1, 0, 0), [1.0, 0.0, 0.0], 2.0, 0.01, 12.0, 1.0)
    catalog = ReflectorCatalog(
        "ice-ih",
        "a" * 64,
        20.0,
        "reflector-recipe-1234",
        {"eligibility_min_weight": 0.08},
        [member],
    )

    assert catalog.catalog_id.startswith("reflector-catalog-")
    assert catalog.members == (member,)
    with pytest.raises(FrozenInstanceError):
        catalog.energy_kev = 30.0
