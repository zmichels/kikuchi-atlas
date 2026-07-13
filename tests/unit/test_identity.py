import math

import pytest

from kikuchi_lab.model.identity import canonical_json, stable_id


def test_recipe_identity_is_key_order_independent():
    left = stable_id("recipe", {"b": 2, "a": 1})
    right = stable_id("recipe", {"a": 1, "b": 2})

    assert left == right
    assert left.startswith("recipe-")
    assert len(left.removeprefix("recipe-")) == 16


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_canonical_json_rejects_nonfinite_floats(value):
    with pytest.raises(ValueError, match="finite"):
        canonical_json({"nested": [value]})


def test_canonical_json_is_compact_utf8_json():
    assert canonical_json({"phase": "forsterite", "b": 2}) == (
        '{"b":2,"phase":"forsterite"}'
    )


def test_stable_id_rejects_invalid_kind():
    with pytest.raises(ValueError, match="kind"):
        stable_id("Not A Kind", {"a": 1})
