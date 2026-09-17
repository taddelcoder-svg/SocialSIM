"""Sensitivitaetsanalyse (Framework-Abschnitt 8, 'Sensitivitaetsanalyse').

Variiert einen einzelnen Konfigurationswert (per Dotted-Path, siehe paths.py)
ueber eine Liste von Werten und misst, wie stark sich ein Ergebnis dadurch
aendert - je flacher die Kurve, desto robuster das Szenario gegenueber
Unsicherheit in diesem Parameter.
"""

from __future__ import annotations

import pandas as pd

from .config import ConfigError, ScenarioConfig
from .paths import set_by_path
from .run import run_scenario


def run_sensitivity(
    config: ScenarioConfig,
    parameter_path: str,
    values: list,
    metric: str = "std_opinion",
    at: str | int = "last",
) -> pd.DataFrame:
    """Fuehrt das Szenario einmal je Wert aus (mit `config.time.runs` Wiederholungen
    pro Wert) und aggregiert `metric` zum Zeitpunkt `at` ('last' oder ein Tick)."""
    base_dict = config.to_dict()
    rows = []
    for value in values:
        try:
            modified = set_by_path(base_dict, parameter_path, value)
            variant = ScenarioConfig.from_dict(modified)
            results = run_scenario(variant)
        except (KeyError, IndexError, TypeError, ValueError, ConfigError) as exc:
            raise ConfigError(f"Parameter '{parameter_path}'={value!r} ungueltig: {exc}") from exc
        tick = variant.time.steps if at == "last" else int(at)
        per_run = results.loc[results["tick"] == tick, metric]
        if per_run.empty:
            raise ConfigError(f"Tick {tick} liegt ausserhalb von time.steps={variant.time.steps}")

        rows.append(
            {
                "value": value,
                "mean": per_run.mean(),
                "min": per_run.min(),
                "max": per_run.max(),
                "std_across_runs": per_run.std() if len(per_run) > 1 else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _parse_value(raw: str):
    try:
        return float(raw) if "." in raw or "e" in raw.lower() else int(raw)
    except ValueError:
        return raw


def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Sensitivitaetsanalyse fuer einen Config-Parameter")
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--param", required=True, help="Dotted Path, z.B. mechanics.0.params.epsilon")
    parser.add_argument("--values", required=True, help="Komma-getrennte Werte, z.B. 0.1,0.2,0.3,0.5,0.8")
    parser.add_argument("--metric", default="std_opinion", choices=["mean_opinion", "std_opinion"])
    parser.add_argument("--at", default="last", help="'last' oder ein Tick-Index")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    config = ScenarioConfig.from_file(args.scenario)
    values = [_parse_value(v.strip()) for v in args.values.split(",")]

    print(f"Szenario: {config.name}")
    print(f"Parameter: {args.param}  Metrik: {args.metric}  Zeitpunkt: {args.at}\n")

    df = run_sensitivity(config, args.param, values, metric=args.metric, at=args.at)
    print(df.to_string(index=False))

    spread = df["mean"].max() - df["mean"].min()
    print(f"\nSpannweite von '{args.metric}' ueber alle Werte: {spread:.4f}")

    if args.out:
        df.to_csv(args.out, index=False)
        print(f"Ergebnisse gespeichert: {args.out}")


if __name__ == "__main__":
    main()
