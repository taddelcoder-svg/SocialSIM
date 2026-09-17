"""Austauschbare Verhaltensmodelle (Framework-Abschnitt 5).

Jede Mechanik implementiert `Mechanic.step(model)` und wird per Namen aus
`MechanicConfig.model` ausgewaehlt (`get_mechanic`). Neue Modelle (Schwellenwert,
Diffusion, DeGroot) werden hier nur registriert, ohne dass Config, Agenten oder
Netzwerkaufbau angefasst werden muessen.
"""

from __future__ import annotations

from .base import Mechanic
from .bounded_confidence import BoundedConfidenceMechanic
from .degroot import DeGrootMechanic
from .threshold import ThresholdMechanic

_REGISTRY: dict[str, type[Mechanic]] = {
    "bounded_confidence": BoundedConfidenceMechanic,
    "threshold": ThresholdMechanic,
    "degroot": DeGrootMechanic,
}


def get_mechanic(name: str, params: dict) -> Mechanic:
    try:
        cls = _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"unbekannte Mechanik '{name}' (verfuegbar: {sorted(_REGISTRY)})") from exc
    return cls(**params)


__all__ = [
    "Mechanic",
    "BoundedConfidenceMechanic",
    "ThresholdMechanic",
    "DeGrootMechanic",
    "get_mechanic",
]
