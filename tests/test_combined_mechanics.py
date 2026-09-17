import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sozialsimulator.config import ScenarioConfig
from sozialsimulator.model import SocialSimulationModel

SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def test_mechanics_field_accepts_single_object():
    """Bestehende Szenarien mit 'mechanics': {model, params} muessen weiter funktionieren."""
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_konsens.json")
    assert len(config.mechanics) == 1
    assert config.mechanics[0].model == "bounded_confidence"


def test_mechanics_field_accepts_list():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_kombiniert.json")
    assert [m.model for m in config.mechanics] == ["degroot", "bounded_confidence"]


def test_model_builds_one_instance_per_configured_mechanic():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_kombiniert.json")
    model = SocialSimulationModel(config)
    names = [name for name, _ in model.mechanics]
    assert names == ["degroot", "bounded_confidence"]
    assert type(model.get_mechanic("degroot")).__name__ == "DeGrootMechanic"
    assert type(model.get_mechanic("bounded_confidence")).__name__ == "BoundedConfidenceMechanic"


def test_mechanics_run_in_order_within_one_tick():
    """Die zweite Mechanik muss bereits das Ergebnis der ersten im selben Tick sehen.

    Ausgangslage (vollstaendiger Graph, 3 Agenten): a0=10, a1=0, a2=0.
    - DeGroot allein (self_weight=0) wuerde a0 auf 0 setzen, a1/a2 auf je 5 -
      keine Konvergenz in einem Schritt.
    - Bounded Confidence allein (epsilon=5) liesse a0 unveraendert bei 10, da
      der Abstand zu a1/a2 (10) ausserhalb des Vertrauensradius liegt.
    - Erst DIE VERKETTUNG (DeGroot zuerst, dann Bounded Confidence auf dessen
      Ergebnis 0/5/5, wo alle Abstaende <= 5 sind) fuehrt zu vollem Konsens
      bei 10/3 - ein Ergebnis, das keine der beiden Mechaniken allein liefert.
    """
    config = ScenarioConfig.from_dict(
        {
            "name": "t",
            "seed": 1,
            "population": {"size": 3, "attributes": {}},
            "network": {"type": "complete"},
            "initial_state": {"opinion": {"kind": "constant", "params": {"value": 0.0}}},
            "mechanics": [
                {"model": "degroot", "params": {"self_weight": 0.0}},
                {"model": "bounded_confidence", "params": {"epsilon": 5.0, "mu": 1.0}},
            ],
            "time": {"steps": 1, "runs": 1},
        }
    )
    model = SocialSimulationModel(config)
    a0, a1, a2 = sorted(model.agents, key=lambda a: a.unique_id)
    a0.opinion = 10.0

    model.step()

    expected = 10 / 3
    for agent in (a0, a1, a2):
        assert abs(agent.opinion - expected) < 1e-9


def test_event_target_narrows_only_the_named_mechanic():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_kombiniert.json")
    model = SocialSimulationModel(config)
    bc = model.get_mechanic("bounded_confidence")
    degroot = model.get_mechanic("degroot")
    original_epsilon = bc.epsilon
    degroot_self_weight_before = degroot.self_weight

    for _ in range(16):  # Event ist auf tick=15 konfiguriert
        model.step()

    assert bc.epsilon != original_epsilon
    assert degroot.self_weight == degroot_self_weight_before  # DeGroot hat kein epsilon, bleibt unberuehrt


def test_combined_scenario_runs_end_to_end():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_kombiniert.json")
    df = SocialSimulationModel(config).run()
    assert len(df) == config.time.steps + 1
