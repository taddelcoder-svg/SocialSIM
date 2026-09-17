import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sozialsimulator.config import ScenarioConfig
from sozialsimulator.model import SocialSimulationModel

SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def test_model_builds_correct_population_size():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_konsens.json")
    model = SocialSimulationModel(config)
    assert len(list(model.agents)) == config.population.size


def test_run_produces_one_row_per_tick_plus_initial():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_konsens.json")
    model = SocialSimulationModel(config)
    df = model.run()
    assert len(df) == config.time.steps + 1  # +1 fuer den Ausgangszustand


def test_same_seed_is_reproducible():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_konsens.json")
    df_a = SocialSimulationModel(config).run()
    df_b = SocialSimulationModel(config).run()
    assert (df_a["mean_opinion"] == df_b["mean_opinion"]).all()


def test_high_epsilon_reduces_opinion_spread():
    """Hoher Vertrauensradius sollte laut Bounded-Confidence-Theorie zu mehr
    Konsens (kleinerer Streuung) fuehren als ein sehr enger Radius."""
    base = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_konsens.json")

    narrow = ScenarioConfig.from_dict({**base.to_dict(), "mechanics": {"model": "bounded_confidence", "params": {"epsilon": 0.05, "mu": 0.5}}})
    wide = ScenarioConfig.from_dict({**base.to_dict(), "mechanics": {"model": "bounded_confidence", "params": {"epsilon": 1.5, "mu": 0.5}}})

    std_narrow = SocialSimulationModel(narrow).run()["std_opinion"].iloc[-1]
    std_wide = SocialSimulationModel(wide).run()["std_opinion"].iloc[-1]

    assert std_wide < std_narrow


def test_narrow_confidence_event_restores_epsilon_after_duration():
    config = ScenarioConfig.from_dict(
        {
            **ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_bounded_confidence.json").to_dict(),
            "time": {"steps": 40, "runs": 1},
        }
    )
    model = SocialSimulationModel(config)
    original_epsilon = model.get_mechanic("bounded_confidence").epsilon
    # Event ist auf tick=20 konfiguriert, duration=15 -> greift beim 21. step()-Aufruf.
    for _ in range(21):
        model.step()
    assert model.get_mechanic("bounded_confidence").epsilon != original_epsilon
    for _ in range(15):
        model.step()
    assert model.get_mechanic("bounded_confidence").epsilon == original_epsilon
