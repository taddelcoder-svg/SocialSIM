"""Rahmen-UI: ein kleiner lokaler Webserver, um Szenarien zusammenzuklicken.

Die UI erzeugt nur ein Config-JSON, das exakt dem Format aus `scenarios/*.json`
entspricht - die Simulation selbst laeuft ueber denselben Code wie die CLI
(`config.py`, `model.py`, `run.py`). Kein Sonderpfad, keine Duplikation.

Start:
    python -m sozialsimulator.webapp
dann http://127.0.0.1:5000 im Browser oeffnen.
"""

from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .calibration import check_calibration
from .config import ConfigError, ScenarioConfig
from .data_sources import list_data_sources
from .run import run_scenario
from .sensitivity import run_sensitivity

STATIC_DIR = Path(__file__).resolve().parent / "static"
SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/examples")
def list_examples():
    """Beispielszenarien aus scenarios/*.json, damit die UI sie ins Formular laden kann."""
    examples = []
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        examples.append({"file": path.name, "config": path.read_text(encoding="utf-8")})
    return jsonify(examples)


@app.route("/api/run", methods=["POST"])
def run():
    body = request.get_json(force=True, silent=False)
    if body is None:
        return jsonify({"error": "Kein gueltiges JSON im Request-Body"}), 400

    try:
        config = ScenarioConfig.from_dict(body)
    except (ConfigError, ValueError, TypeError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        results = run_scenario(config)
    except (ConfigError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    aggregated = results.groupby("tick")[["mean_opinion", "std_opinion"]].mean().reset_index()

    return jsonify(
        {
            "ticks": aggregated["tick"].tolist(),
            "mean_opinion": aggregated["mean_opinion"].tolist(),
            "std_opinion": aggregated["std_opinion"].tolist(),
            "runs": config.time.runs,
            "population_size": config.population.size,
            "mechanic": " + ".join(m.model for m in config.mechanics),
        }
    )


@app.route("/api/data-sources")
def data_sources():
    """Katalog realer Verteilungen fuer eigene Szenarien (Framework-Abschnitt 6)."""
    return jsonify(list_data_sources(request.args.get("applies_to")))


@app.route("/api/calibrate", methods=["POST"])
def calibrate():
    """Zieht eine grosse Stichprobe je konfigurierter Verteilung und vergleicht
    sie mit den Zielgewichten der Config selbst (Framework-Abschnitt 8)."""
    body = request.get_json(force=True, silent=False)
    if body is None:
        return jsonify({"error": "Kein gueltiges JSON im Request-Body"}), 400

    try:
        config = ScenarioConfig.from_dict(body)
        results = check_calibration(config)
    except (ConfigError, ValueError, TypeError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        [
            {
                "field": r.field,
                "kind": r.kind,
                "detail": r.detail,
                "ok": bool(r.ok),
                "max_deviation": float(r.max_deviation),
            }
            for r in results
        ]
    )


@app.route("/api/sensitivity", methods=["POST"])
def sensitivity():
    """Variiert einen Config-Parameter ueber eine Werteliste (Framework-Abschnitt 8)."""
    body = request.get_json(force=True, silent=False)
    if body is None:
        return jsonify({"error": "Kein gueltiges JSON im Request-Body"}), 400

    config_dict = body.get("config")
    parameter_path = body.get("parameter")
    values = body.get("values")
    metric = body.get("metric", "std_opinion")

    if not config_dict or not parameter_path or not values:
        return jsonify({"error": "Body braucht 'config', 'parameter' und 'values'"}), 400

    try:
        config = ScenarioConfig.from_dict(config_dict)
        df = run_sensitivity(config, parameter_path, values, metric=metric)
    except (ConfigError, ValueError, TypeError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {
            "values": df["value"].tolist(),
            "mean": df["mean"].tolist(),
            "min": df["min"].tolist(),
            "max": df["max"].tolist(),
            "metric": metric,
        }
    )


def main() -> None:
    app.run(debug=True)


if __name__ == "__main__":
    main()
