import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sozialsimulator.config import ScenarioConfig
from sozialsimulator.model import SocialSimulationModel

SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def _load():
    return ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_schwellenwert.json")


def test_adoption_is_irreversible_and_non_decreasing():
    model = SocialSimulationModel(_load())
    df = model.run()
    diffs = df["mean_opinion"].diff().dropna()
    assert (diffs >= -1e-12).all()  # Adoptionsrate darf nie sinken


def test_lower_thresholds_lead_to_more_adoption():
    base = _load()

    low = ScenarioConfig.from_dict(
        {**base.to_dict(), "population": {**base.to_dict()["population"], "attributes": {
            "threshold": {"kind": "constant", "params": {"value": 0.05}}
        }}}
    )
    high = ScenarioConfig.from_dict(
        {**base.to_dict(), "population": {**base.to_dict()["population"], "attributes": {
            "threshold": {"kind": "constant", "params": {"value": 0.9}}
        }}}
    )

    final_low = SocialSimulationModel(low).run()["mean_opinion"].iloc[-1]
    final_high = SocialSimulationModel(high).run()["mean_opinion"].iloc[-1]

    assert final_low > final_high


def test_threshold_and_bounded_confidence_are_independent_modules():
    """Zwei Szenarien mit unterschiedlicher Mechanik laufen ueber denselben Code
    (model.py, config.py) - nur die Config unterscheidet sich (Baukasten-Prinzip)."""
    threshold_config = _load()
    bc_config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_konsens.json")

    threshold_model = SocialSimulationModel(threshold_config)
    bc_model = SocialSimulationModel(bc_config)

    assert type(threshold_model.get_mechanic("threshold")).__name__ == "ThresholdMechanic"
    assert type(bc_model.get_mechanic("bounded_confidence")).__name__ == "BoundedConfidenceMechanic"
