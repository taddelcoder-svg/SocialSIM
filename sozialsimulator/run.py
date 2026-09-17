"""CLI: laedt ein Szenario (JSON) und fuehrt es aus.

    python -m sozialsimulator.run scenarios/beispiel_bounded_confidence.json --out ergebnis.csv

`time.runs` in der Config steuert, wie oft das Szenario mit unterschiedlichem
Zufalls-Seed wiederholt wird (Framework-Abschnitt 8, 'Mehrfachlaeufe' fuer
robuste statt einzelner Ergebnisse).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .config import ScenarioConfig
from .model import SocialSimulationModel


def run_scenario(config: ScenarioConfig) -> pd.DataFrame:
    frames = []
    base_seed = config.seed
    for run_index in range(config.time.runs):
        run_config = config
        if base_seed is not None:
            run_config = ScenarioConfig.from_dict({**config.to_dict(), "seed": base_seed + run_index})
        model = SocialSimulationModel(run_config)
        df = model.run()
        df["run"] = run_index
        df["tick"] = df.index
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sozialsimulator: ein Szenario ausfuehren")
    parser.add_argument("scenario", type=Path, help="Pfad zur Szenario-JSON-Datei")
    parser.add_argument("--out", type=Path, default=None, help="CSV-Ausgabedatei (optional)")
    args = parser.parse_args()

    config = ScenarioConfig.from_file(args.scenario)
    print(f"Szenario: {config.name}")
    if config.notes:
        print(f"Notizen: {config.notes}")
    mechanic_names = " + ".join(m.model for m in config.mechanics)
    print(
        f"Population={config.population.size}  Netzwerk={config.network.type}  "
        f"Mechanik={mechanic_names}  Schritte={config.time.steps}  Laeufe={config.time.runs}"
    )

    results = run_scenario(config)
    summary = results.groupby("tick")[["mean_opinion", "std_opinion"]].mean()
    print("\nMittelwert ueber alle Laeufe (erste/letzte 3 Ticks):")
    print(pd.concat([summary.head(3), summary.tail(3)]))

    if args.out:
        results.to_csv(args.out, index=False)
        print(f"\nErgebnisse gespeichert: {args.out}")


if __name__ == "__main__":
    main()
