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
from .visual import run_visual

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

    grouped = results.groupby("tick")
    numeric_cols = [c for c in results.columns if c not in ("run", "tick")]
    aggregated = grouped[numeric_cols].mean().reset_index()

    response = {
        "ticks": aggregated["tick"].tolist(),
        "runs": config.time.runs,
        "population_size": config.population.size,
        "mechanic": " + ".join(m.model for m in config.mechanics),
        "topics": list(config.initial_state.keys()),
    }
    # Jede Meinungsachse (mean_<topic>/std_<topic>, siehe model.py) generisch mitschicken -
    # deckt sowohl das klassische Einzelthema-Feld "mean_opinion"/"std_opinion" als auch
    # mehrdimensionale Szenarien mit mehreren Topics ab.
    for col in numeric_cols:
        response[col] = aggregated[col].tolist()

    if "mean_opinion" in results.columns:
        # Spannweite von mean_opinion UEBER die Wiederholungslaeufe je Tick (nicht
        # zu verwechseln mit std_opinion, das die Streuung ZWISCHEN Agenten misst) -
        # Grundlage fuer eine ehrliche Bandbreite statt einer einzelnen Zahl
        # (Framework-Abschnitt 8, 'Mehrfachlaeufe').
        mean_range = grouped["mean_opinion"].agg(["min", "max"]).reset_index()
        response["mean_opinion_min"] = mean_range["min"].tolist()
        response["mean_opinion_max"] = mean_range["max"].tolist()

    return jsonify(response)


@app.route("/api/run_visual", methods=["POST"])
def run_visual_route():
    """Fuer die "Welt"-Ansicht: pro Zeitschritt eine Momentaufnahme aller Agenten-
    Meinungswerte plus eine feste Netzwerk-Layout-Position je Knoten, damit das
    Frontend das Netzwerk animiert abspielen kann (siehe visual.py)."""
    body = request.get_json(force=True, silent=False)
    if body is None:
        return jsonify({"error": "Kein gueltiges JSON im Request-Body"}), 400

    try:
        config = ScenarioConfig.from_dict(body)
    except (ConfigError, ValueError, TypeError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        data = run_visual(config)
    except (ConfigError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(data)


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
