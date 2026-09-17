import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sozialsimulator.config import ConfigError, ScenarioConfig
from sozialsimulator.model import SocialSimulationModel

SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def _two_topic_config(**overrides):
    base = {
        "name": "t",
        "seed": 1,
        "population": {"size": 50, "attributes": {}},
        "network": {"type": "complete"},
        "initial_state": {
            "a": {"kind": "constant", "params": {"value": -1.0}},
            "b": {"kind": "constant", "params": {"value": 1.0}},
        },
        "mechanics": [
            {"model": "bounded_confidence", "topic": "a", "params": {"epsilon": 5.0, "mu": 1.0}},
            {"model": "bounded_confidence", "topic": "b", "params": {"epsilon": 5.0, "mu": 1.0}},
        ],
        "time": {"steps": 1, "runs": 1},
    }
    base.update(overrides)
    return ScenarioConfig.from_dict(base)


def test_agent_opinion_property_still_works_for_single_topic_scenarios():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_konsens.json")
    model = SocialSimulationModel(config)
    agent = next(iter(model.agents))
    assert agent.opinion == agent.opinions["opinion"]
    agent.opinion = 0.42
    assert agent.opinions["opinion"] == 0.42


def test_two_topics_evolve_independently():
    config = _two_topic_config()
    model = SocialSimulationModel(config)
    model.step()
    for agent in model.agents:
        # epsilon=5 auf einem vollstaendigen Graphen -> beide Topics konvergieren
        # jeweils auf ihren eigenen Mittelwert, unabhaengig voneinander.
        assert agent.opinions["a"] == pytest.approx(-1.0)
        assert agent.opinions["b"] == pytest.approx(1.0)


def test_datacollector_reports_one_column_pair_per_topic():
    config = _two_topic_config()
    df = SocialSimulationModel(config).run()
    assert "mean_a" in df.columns
    assert "std_a" in df.columns
    assert "mean_b" in df.columns
    assert "std_b" in df.columns


def test_mechanic_topic_must_exist_in_initial_state():
    with pytest.raises(ConfigError):
        _two_topic_config(
            mechanics=[{"model": "bounded_confidence", "topic": "does_not_exist", "params": {"epsilon": 0.3}}]
        )


def test_correlated_with_unknown_topic_raises():
    with pytest.raises(ConfigError):
        _two_topic_config(
            initial_state={
                "a": {"kind": "constant", "params": {"value": 0.0}},
                "b": {
                    "kind": "constant",
                    "params": {"value": 0.0},
                    "correlated_with": {"topic": "nope", "strength": 0.5},
                },
            }
        )


def test_correlated_with_self_raises():
    with pytest.raises(ConfigError):
        _two_topic_config(
            initial_state={
                "a": {
                    "kind": "constant",
                    "params": {"value": 0.0},
                    "correlated_with": {"topic": "a", "strength": 0.5},
                },
            },
            mechanics=[{"model": "bounded_confidence", "topic": "a", "params": {"epsilon": 0.3}}],
        )


def test_chained_correlation_rejected():
    with pytest.raises(ConfigError):
        _two_topic_config(
            initial_state={
                "a": {"kind": "constant", "params": {"value": 0.0}},
                "b": {
                    "kind": "constant",
                    "params": {"value": 0.0},
                    "correlated_with": {"topic": "a", "strength": 0.5},
                },
                "c": {
                    "kind": "constant",
                    "params": {"value": 0.0},
                    "correlated_with": {"topic": "b", "strength": 0.5},
                },
            },
            mechanics=[{"model": "bounded_confidence", "topic": "a", "params": {"epsilon": 0.3}}],
        )


def test_correlation_pulls_values_toward_reference_topic():
    """Mit strength=1.0 sollte das korrelierte Topic exakt dem Referenz-Topic folgen."""
    config = ScenarioConfig.from_dict(
        {
            "name": "t",
            "seed": 7,
            "population": {"size": 200, "attributes": {}},
            "network": {"type": "complete"},
            "initial_state": {
                "klima": {"kind": "uniform", "params": {"min": -1.0, "max": 1.0}},
                "energie": {
                    "kind": "normal",
                    "params": {"mean": 0.0, "std": 1.0, "min": -1.0, "max": 1.0},
                    "correlated_with": {"topic": "klima", "strength": 1.0},
                },
            },
            "mechanics": [{"model": "bounded_confidence", "topic": "klima", "params": {"epsilon": 0.01}}],
            "time": {"steps": 1, "runs": 1},
        }
    )
    model = SocialSimulationModel(config)  # Korrelation gilt schon beim Aufbau, vor jedem step()
    for agent in model.agents:
        assert agent.opinions["klima"] == pytest.approx(agent.opinions["energie"])


def test_example_scenario_runs_end_to_end():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_mehrdimensional.json")
    df = SocialSimulationModel(config).run()
    assert "mean_klima" in df.columns
    assert "mean_energiepolitik" in df.columns
    assert len(df) == config.time.steps + 1
