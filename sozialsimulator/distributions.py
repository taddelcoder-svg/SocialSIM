"""Zieht Werte aus einer `Distribution`-Spezifikation (siehe config.py).

Trennt die Konfiguration (was soll gezogen werden) von der Zufallsquelle
(ein numpy-Generator, der pro Szenario aus dem Seed erzeugt wird -> reproduzierbar).
"""

from __future__ import annotations

import numpy as np

from .config import ConfigError, Distribution


def sample(dist: Distribution, rng: np.random.Generator, size: int) -> np.ndarray:
    """Zieht `size` Werte gemaess der Verteilung `dist`."""
    p = dist.params
    if dist.kind == "constant":
        value = p.get("value", 0.0)
        return np.full(size, value, dtype=float)

    if dist.kind == "normal":
        mean = p.get("mean", 0.0)
        std = p.get("std", 1.0)
        low = p.get("min")
        high = p.get("max")
        values = rng.normal(loc=mean, scale=std, size=size)
        if low is not None or high is not None:
            values = np.clip(values, low, high)
        return values

    if dist.kind == "uniform":
        low = p.get("min", 0.0)
        high = p.get("max", 1.0)
        return rng.uniform(low=low, high=high, size=size)

    if dist.kind == "beta":
        a = p.get("a", 2.0)
        b = p.get("b", 2.0)
        low = p.get("min", 0.0)
        high = p.get("max", 1.0)
        values = rng.beta(a, b, size=size)
        return low + values * (high - low)

    if dist.kind == "histogram":
        bins = p.get("bins")
        if not bins:
            raise ConfigError("distribution 'histogram' braucht 'params.bins' (Liste von {min,max,weight})")
        weights = np.array([float(b["weight"]) for b in bins], dtype=float)
        weights = weights / weights.sum()
        mins = np.array([float(b["min"]) for b in bins], dtype=float)
        maxs = np.array([float(b["max"]) for b in bins], dtype=float)
        chosen = rng.choice(len(bins), size=size, p=weights)
        return rng.uniform(mins[chosen], maxs[chosen])

    if dist.kind == "choice":
        options = p.get("options")
        if not options:
            raise ConfigError("distribution 'choice' braucht 'params.options'")
        weights = p.get("weights")
        if weights is not None:
            weights = np.array(weights, dtype=float)
            weights = weights / weights.sum()
        idx = rng.choice(len(options), size=size, p=weights)
        return np.array(options)[idx]

    raise ConfigError(f"unbekannte Verteilung '{dist.kind}'")
