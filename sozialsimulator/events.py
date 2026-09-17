"""Externe Ereignisse zu festen Zeitschritten (Rahmen-Abschnitt 3, 'externe Ereignisse').

Ein Event greift von aussen in eine laufende Simulation ein - z.B. eine virale
Nachricht, die Vertrauensradien kurzzeitig verengt (Beispielszenario A im
Framework-Dokument), oder ein Schock, der einen Teil der Meinungen verschiebt.
"""

from __future__ import annotations

from .config import ConfigError, Event


def apply_event(model, event: Event) -> None:
    if event.type == "narrow_confidence":
        _narrow_confidence(model, event.params)
    elif event.type == "shift_opinion":
        _shift_opinion(model, event.params)
    else:
        raise ConfigError(f"unbekannter Event-Typ '{event.type}'")


def _narrow_confidence(model, params: dict) -> None:
    """Verengt `epsilon` einer Mechanik um `factor` fuer `duration` Ticks.

    `target` (optional) waehlt die Mechanik bei mehreren kombinierten Modulen
    (Framework-Abschnitt 5, 'kombinierbare Module') per Modellname, z.B.
    "bounded_confidence"; ohne `target` wird die erste konfigurierte Mechanik
    mit einem `epsilon`-Attribut verwendet.
    """
    factor = float(params.get("factor", 0.5))
    duration = int(params.get("duration", 10))
    target_name = params.get("target")

    if target_name is not None:
        mechanic = model.get_mechanic(target_name)
    else:
        mechanic = next((m for _, m in model.mechanics if hasattr(m, "epsilon")), None)
    if mechanic is None or not hasattr(mechanic, "epsilon"):
        raise ConfigError("'narrow_confidence' setzt eine Mechanik mit 'epsilon' voraus")

    original = mechanic.epsilon
    mechanic.epsilon = original * factor
    model._confidence_restore.append((model.schedule_tick + duration, mechanic, original))


def _shift_opinion(model, params: dict) -> None:
    """Verschiebt die Meinung eines Anteils zufaellig gewaehlter Agenten um `delta`."""
    delta = float(params.get("delta", 0.0))
    fraction = float(params.get("fraction", 1.0))
    agents = list(model.agents)
    n_affected = max(1, round(len(agents) * fraction))
    chosen = model.random.sample(agents, k=n_affected)
    for agent in chosen:
        agent.opinion += delta
