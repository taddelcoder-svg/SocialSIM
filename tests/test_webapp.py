import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sozialsimulator.config import ScenarioConfig
from sozialsimulator.webapp import app

SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def test_api_run_returns_min_max_range_across_runs():
    config = ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_konsens.json")
    client = app.test_client()

    response = client.post("/api/run", json=config.to_dict())
    assert response.status_code == 200
    data = response.get_json()

    assert "mean_opinion_min" in data
    assert "mean_opinion_max" in data
    assert len(data["mean_opinion_min"]) == len(data["ticks"])
    for lo, mean, hi in zip(data["mean_opinion_min"], data["mean_opinion"], data["mean_opinion_max"]):
        assert lo <= mean + 1e-9
        assert mean <= hi + 1e-9


def test_api_run_range_collapses_with_a_single_run():
    config = ScenarioConfig.from_dict(
        {
            **ScenarioConfig.from_file(SCENARIOS_DIR / "beispiel_konsens.json").to_dict(),
            "time": {"steps": 5, "runs": 1},
        }
    )
    client = app.test_client()
    response = client.post("/api/run", json=config.to_dict())
    data = response.get_json()
    for lo, mean, hi in zip(data["mean_opinion_min"], data["mean_opinion"], data["mean_opinion_max"]):
        assert abs(lo - mean) < 1e-9
        assert abs(hi - mean) < 1e-9


def test_api_data_sources_lists_new_entries():
    client = app.test_client()
    response = client.get("/api/data-sources")
    assert response.status_code == 200
    ids = [entry["id"] for entry in response.get_json()]
    assert "eurostat_homeoffice_de_2023" in ids
    assert "covid_vaccine_willingness_de_2021" in ids
    assert "reuters_trust_social_media_2026" in ids


def test_api_data_sources_filters_trust_media():
    client = app.test_client()
    response = client.get("/api/data-sources?applies_to=trust_media")
    entries = response.get_json()
    assert len(entries) == 1
    assert entries[0]["id"] == "reuters_trust_social_media_2026"
