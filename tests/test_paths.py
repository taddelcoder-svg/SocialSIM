import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sozialsimulator.paths import get_by_path, set_by_path


def test_get_by_path_dict_and_list():
    data = {"mechanics": [{"model": "bounded_confidence", "params": {"epsilon": 0.3}}]}
    assert get_by_path(data, "mechanics.0.model") == "bounded_confidence"
    assert get_by_path(data, "mechanics.0.params.epsilon") == 0.3


def test_set_by_path_returns_new_object_and_leaves_original_untouched():
    data = {"network": {"type": "watts_strogatz", "params": {"k": 4}}}
    updated = set_by_path(data, "network.params.k", 20)
    assert updated["network"]["params"]["k"] == 20
    assert data["network"]["params"]["k"] == 4  # Original unveraendert


def test_set_by_path_on_list_index():
    data = {"mechanics": [{"model": "a", "params": {}}, {"model": "b", "params": {"self_weight": 0.5}}]}
    updated = set_by_path(data, "mechanics.1.params.self_weight", 0.9)
    assert updated["mechanics"][1]["params"]["self_weight"] == 0.9
    assert updated["mechanics"][0] == data["mechanics"][0]


def test_get_by_path_invalid_key_raises():
    with pytest.raises(KeyError):
        get_by_path({"a": 1}, "b")
