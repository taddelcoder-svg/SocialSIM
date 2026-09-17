import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from sozialsimulator.config import ConfigError, ScenarioConfig

MINIMAL = {
    "name": "t",
    "population": {"size": 10, "attributes": {}},
    "network": {"type": "erdos_renyi", "params": {"p": 0.2}},
    "initial_state": {"opinion": {"kind": "uniform", "params": {"min": -1, "max": 1}}},
    "mechanics": {"model": "bounded_confidence", "params": {"epsilon": 0.3}},
}


def test_minimal_config_parses():
    config = ScenarioConfig.from_dict(MINIMAL)
    assert config.population.size == 10
    assert config.network.type == "erdos_renyi"
    assert config.time.steps == 100  # Default
    assert config.time.runs == 1


def test_missing_required_field_raises():
    bad = {k: v for k, v in MINIMAL.items() if k != "network"}
    with pytest.raises(ConfigError):
        ScenarioConfig.from_dict(bad)


def test_unknown_network_type_raises():
    bad = {**MINIMAL, "network": {"type": "does_not_exist"}}
    with pytest.raises(ConfigError):
        ScenarioConfig.from_dict(bad)


def test_roundtrip_to_dict_from_dict():
    config = ScenarioConfig.from_dict(MINIMAL)
    again = ScenarioConfig.from_dict(config.to_dict())
    assert again.to_dict() == config.to_dict()


def test_example_scenarios_load():
    scenarios_dir = Path(__file__).resolve().parents[1] / "scenarios"
    for path in scenarios_dir.glob("*.json"):
        config = ScenarioConfig.from_file(path)
        assert config.population.size > 0
