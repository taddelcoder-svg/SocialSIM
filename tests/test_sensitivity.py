import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sozialsimulator.config import ConfigError, ScenarioConfig
from sozialsimulator.sensitivity import run_sensitivity

SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def test_epsilon_sweep_reduces_final_spread_monotonically_ish():
    """Fuer Bounded Confidence sollte ein groesserer Vertrauensradius tendenziell
    zu weniger Meinungsstreuung am Ende fuehren (Theorie: mehr Konsens)."""
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_konsens.json")
    df = run_sensitivity(config, "mechanics.0.params.epsilon", [0.1, 0.5, 1.5], metric="std_opinion")

    assert list(df["value"]) == [0.1, 0.5, 1.5]
    assert df.loc[df["value"] == 1.5, "mean"].iloc[0] < df.loc[df["value"] == 0.1, "mean"].iloc[0]


def test_original_config_is_not_mutated():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_konsens.json")
    original_epsilon = config.mechanics[0].params["epsilon"]
    run_sensitivity(config, "mechanics.0.params.epsilon", [0.05, 2.0])
    assert config.mechanics[0].params["epsilon"] == original_epsilon


def test_invalid_path_raises_config_error():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_konsens.json")
    with pytest.raises(ConfigError):
        run_sensitivity(config, "mechanics.0.params.does_not_exist_and_breaks_nothing", [1])


def test_invalid_value_raises_config_error():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_konsens.json")
    with pytest.raises(ConfigError):
        run_sensitivity(config, "mechanics.0.params.epsilon", [-1.0])  # epsilon muss > 0 sein


def test_at_specific_tick_instead_of_last():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_konsens.json")
    df_at_0 = run_sensitivity(config, "mechanics.0.params.epsilon", [0.3], at=0)
    # Bei Tick 0 (Ausgangszustand) hat epsilon noch gar nicht gewirkt -
    # das Ergebnis muss unabhaengig vom epsilon-Wert sein.
    df_at_0_other = run_sensitivity(config, "mechanics.0.params.epsilon", [1.5], at=0)
    assert abs(df_at_0["mean"].iloc[0] - df_at_0_other["mean"].iloc[0]) < 1e-9
