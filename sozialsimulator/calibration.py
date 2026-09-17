"""Kalibrierungscheck (Framework-Abschnitt 8, 'Kalibrierung').

Zieht eine grosse Stichprobe aus jeder konfigurierten Verteilung
(`initial_state`, `population.attributes`) und vergleicht sie mit der
Zielverteilung, die die Konfiguration selbst vorgibt - Abweichungen zeigen
Fehler in der Config (z.B. falsch eingetragene Gewichte) oder schlicht
Stichprobenrauschen bei kleiner Population.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import Distribution, ScenarioConfig
from .distributions import sample


@dataclass
class CalibrationResult:
    field: str
    kind: str
    detail: str
    max_deviation: float

    @property
    def ok(self) -> bool:
        return self.max_deviation <= 0.03


def _theoretical_mean(dist: Distribution) -> float | None:
    p = dist.params
    if dist.kind == "normal":
        return p.get("mean", 0.0)
    if dist.kind == "uniform":
        return (p.get("min", 0.0) + p.get("max", 1.0)) / 2
    if dist.kind == "constant":
        return p.get("value", 0.0)
    if dist.kind == "beta":
        a, b = p.get("a", 2.0), p.get("b", 2.0)
        lo, hi = p.get("min", 0.0), p.get("max", 1.0)
        return lo + (a / (a + b)) * (hi - lo)
    return None


def _check_histogram(name: str, dist: Distribution, values: np.ndarray) -> CalibrationResult:
    bins = dist.params["bins"]
    weights = np.array([b["weight"] for b in bins], dtype=float)
    weights = weights / weights.sum()
    rows = []
    max_dev = 0.0
    for b, expected in zip(bins, weights):
        expected = float(expected)
        observed = float(((values >= b["min"]) & (values <= b["max"])).mean())
        max_dev = max(max_dev, abs(observed - expected))
        rows.append(f"[{b['min']},{b['max']}]: erwartet {expected:.1%}, gezogen {observed:.1%}")
    return CalibrationResult(name, dist.kind, "; ".join(rows), max_dev)


def _check_choice(name: str, dist: Distribution, values: np.ndarray) -> CalibrationResult:
    options = dist.params["options"]
    weights = dist.params.get("weights")
    if weights is None:
        weights = [1.0 / len(options)] * len(options)
    weights = np.array(weights, dtype=float)
    weights = weights / weights.sum()
    rows = []
    max_dev = 0.0
    for option, expected in zip(options, weights):
        expected = float(expected)
        observed = float((values == option).mean())
        max_dev = max(max_dev, abs(observed - expected))
        rows.append(f"{option}: erwartet {expected:.1%}, gezogen {observed:.1%}")
    return CalibrationResult(name, dist.kind, "; ".join(rows), max_dev)


def _check_continuous(name: str, dist: Distribution, values: np.ndarray) -> CalibrationResult:
    observed_mean = float(values.mean())
    expected_mean = _theoretical_mean(dist)
    detail = f"gezogener Mittelwert={observed_mean:.4f}, Streuung={float(values.std()):.4f}"
    if expected_mean is None:
        return CalibrationResult(name, dist.kind, detail, 0.0)
    detail += f" (theoretischer Mittelwert={expected_mean:.4f})"
    span = float(values.max() - values.min()) or 1.0
    relative_dev = abs(observed_mean - expected_mean) / span
    return CalibrationResult(name, dist.kind, detail, relative_dev)


def _check_distribution(name: str, dist: Distribution, rng: np.random.Generator, size: int) -> CalibrationResult:
    values = sample(dist, rng, size)
    if dist.kind == "histogram":
        return _check_histogram(name, dist, values)
    if dist.kind == "choice":
        return _check_choice(name, dist, values)
    return _check_continuous(name, dist, values)


def check_calibration(config: ScenarioConfig, sample_size: int = 20_000) -> list[CalibrationResult]:
    """Prueft jede konfigurierte Verteilung gegen ihre eigene Zielangabe.

    Nutzt eine eigene, grosse Stichprobe (unabhaengig von `population.size`) -
    eine kleine Population kann trotz korrekter Config von der Zielverteilung
    abweichen; das ist Stichprobenrauschen, kein Konfigurationsfehler.
    """
    rng = np.random.default_rng(config.seed)
    results = []
    for name, dist in config.initial_state.items():
        if dist.correlated_with:
            # Die eigene Marginalverteilung eines korrelierten Topics ist nicht das, was
            # die Population tatsaechlich sieht (model.py mischt sie mit dem Referenz-Topic) -
            # eine isolierte Stichprobe hier waere irrefuehrend, deshalb nur ein Hinweis.
            results.append(
                CalibrationResult(
                    f"initial_state.{name}",
                    dist.kind,
                    f"korreliert mit '{dist.correlated_with['topic']}' (Staerke "
                    f"{dist.correlated_with.get('strength', 0.5)}) - wird erst bei der "
                    "Populationserzeugung gemischt, hier nicht isoliert pruefbar",
                    0.0,
                )
            )
            continue
        results.append(_check_distribution(f"initial_state.{name}", dist, rng, sample_size))
    for name, dist in config.population.attributes.items():
        results.append(_check_distribution(f"population.attributes.{name}", dist, rng, sample_size))
    return results


def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Kalibrierung eines Szenarios pruefen")
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--sample-size", type=int, default=20_000)
    args = parser.parse_args()

    config = ScenarioConfig.from_file(args.scenario)
    print(f"Szenario: {config.name}\n")
    for result in check_calibration(config, args.sample_size):
        status = "OK" if result.ok else "ABWEICHUNG"
        print(f"[{status}] {result.field} ({result.kind})")
        print(f"    {result.detail}")


if __name__ == "__main__":
    main()
