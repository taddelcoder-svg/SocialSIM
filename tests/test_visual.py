import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sozialsimulator.config import ScenarioConfig
from sozialsimulator.visual import run_visual

SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def test_run_visual_returns_one_frame_per_tick_plus_start():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_bounded_confidence.json")
    data = run_visual(config)
    assert data["topics"] == ["opinion"]
    assert len(data["positions"]) == config.population.size
    assert len(data["frames"]) == config.time.steps + 1
    for frame in data["frames"]:
        assert len(frame["opinion"]) == config.population.size


def test_run_visual_edges_reference_valid_node_indices():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_bounded_confidence.json")
    data = run_visual(config)
    n = config.population.size
    for u, v in data["edges"]:
        assert 0 <= u < n
        assert 0 <= v < n


def test_run_visual_supports_multiple_topics():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_mehrdimensional.json")
    data = run_visual(config)
    assert set(data["topics"]) == {"klima", "energiepolitik"}
    assert len(data["frames"][0]["klima"]) == config.population.size
    assert len(data["frames"][0]["energiepolitik"]) == config.population.size
