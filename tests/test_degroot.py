import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sozialsimulator.config import ScenarioConfig
from sozialsimulator.model import SocialSimulationModel

SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def test_zero_self_weight_moves_to_plain_neighbor_average():
    config = ScenarioConfig.from_dict(
        {
            "name": "t",
            "seed": 5,
            "population": {"size": 4, "attributes": {}},
            "network": {"type": "complete"},
            "initial_state": {"opinion": {"kind": "uniform", "params": {"min": -1, "max": 1}}},
            "mechanics": {"model": "degroot", "params": {"self_weight": 0.0}},
            "time": {"steps": 1, "runs": 1},
        }
    )
    model = SocialSimulationModel(config)
    before = {a.unique_id: a.opinion for a in model.agents}
    model.step()
    for agent in model.agents:
        neighbor_ids = [n.unique_id for n in agent.neighbors()]
        expected = sum(before[i] for i in neighbor_ids) / len(neighbor_ids)
        assert abs(agent.opinion - expected) < 1e-9


def test_high_self_weight_dampens_change():
    config = ScenarioConfig.from_dict(
        {
            "name": "t",
            "seed": 5,
            "population": {"size": 6, "attributes": {}},
            "network": {"type": "complete"},
            "initial_state": {"opinion": {"kind": "uniform", "params": {"min": -1, "max": 1}}},
            "mechanics": {"model": "degroot", "params": {"self_weight": 0.9}},
            "time": {"steps": 1, "runs": 1},
        }
    )
    model = SocialSimulationModel(config)
    before = {a.unique_id: a.opinion for a in model.agents}
    model.step()
    for agent in model.agents:
        assert abs(agent.opinion - before[agent.unique_id]) < 0.3


def test_credibility_weights_neighbor_influence():
    """Ein Nachbar mit 5x hoeherer Glaubwuerdigkeit soll das Ergebnis
    proportional staerker ziehen als ein gewoehnlicher Nachbar."""
    config = ScenarioConfig.from_dict(
        {
            "name": "t",
            "seed": 1,
            "population": {"size": 3, "attributes": {"credibility": {"kind": "constant", "params": {"value": 1.0}}}},
            "network": {"type": "complete"},
            "initial_state": {"opinion": {"kind": "constant", "params": {"value": 0.0}}},
            "mechanics": {"model": "degroot", "params": {"self_weight": 0.0, "credibility_key": "credibility"}},
            "time": {"steps": 1, "runs": 1},
        }
    )
    model = SocialSimulationModel(config)
    a0, a1, a2 = sorted(model.agents, key=lambda a: a.unique_id)

    a0.extra["credibility"] = 5.0
    a0.opinion = 1.0
    a1.extra["credibility"] = 1.0
    a1.opinion = 0.0
    # a2 ist der beobachtete Agent, seine Nachbarn sind a0 und a1

    model.get_mechanic("degroot").step(model)

    expected = (5.0 * 1.0 + 1.0 * 0.0) / (5.0 + 1.0)
    assert abs(a2.opinion - expected) < 1e-9


def test_example_scenario_moves_toward_consensus():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_degroot.json")
    df = SocialSimulationModel(config).run()
    assert df["std_opinion"].iloc[-1] < df["std_opinion"].iloc[0]
