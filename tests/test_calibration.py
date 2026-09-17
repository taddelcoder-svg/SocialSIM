import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sozialsimulator.calibration import check_calibration
from sozialsimulator.config import ScenarioConfig

SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def test_real_data_scenarios_are_well_calibrated():
    """Die histogram-basierten Verteilungen aus echten Quellen sollten bei
    grosser Stichprobe nah an ihren eigenen Zielgewichten liegen."""
    for filename in ["beispiel_bounded_confidence.json", "beispiel_schwellenwert.json", "beispiel_degroot.json"]:
        config = ScenarioConfig.from_file(SCENARIOS_DIR / filename)
        results = check_calibration(config, sample_size=20_000)
        assert results, f"{filename} hat keine ueberpruefbaren Verteilungen"
        for result in results:
            assert result.ok, f"{filename}: {result.field} weicht ab ({result.max_deviation:.3f}): {result.detail}"


def test_histogram_weights_recovered_precisely_with_large_sample():
    """Der Check prueft die Stichprobe gegen die Zielgewichte der Config selbst
    (nicht gegen eine externe Wahrheit) - bei grosser Stichprobe muss die
    beobachtete Bin-Haeufigkeit nah an den konfigurierten Gewichten liegen."""
    config = ScenarioConfig.from_dict(
        {
            "name": "t",
            "seed": 1,
            "population": {
                "size": 10,
                "attributes": {
                    "x": {
                        "kind": "histogram",
                        "params": {
                            "bins": [
                                {"min": 0, "max": 1, "weight": 0.2},
                                {"min": 100, "max": 101, "weight": 0.8},
                            ]
                        },
                    }
                },
            },
            "network": {"type": "complete"},
            "initial_state": {"opinion": {"kind": "constant", "params": {"value": 0.0}}},
            "mechanics": {"model": "bounded_confidence", "params": {}},
            "time": {"steps": 1, "runs": 1},
        }
    )
    results = check_calibration(config, sample_size=20_000)
    x_result = next(r for r in results if r.field == "population.attributes.x")
    assert x_result.ok
    assert "erwartet 20.0%" in x_result.detail
    assert "erwartet 80.0%" in x_result.detail


def test_calibration_result_ok_threshold():
    from sozialsimulator.calibration import CalibrationResult

    good = CalibrationResult("f", "histogram", "detail", 0.01)
    bad = CalibrationResult("f", "histogram", "detail", 0.5)
    assert good.ok is True
    assert bad.ok is False
