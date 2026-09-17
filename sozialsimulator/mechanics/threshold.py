"""Granovetter-Schwellenwertmodell fuer kollektives Verhalten (Framework-Abschnitt 5).

Ein Agent uebernimmt ein Verhalten (opinion >= 0.5 = "hat uebernommen"), sobald
der Anteil seiner Nachbarn, die es bereits uebernommen haben, seinen
individuellen Schwellenwert erreicht. Uebernahme ist irreversibel (wie im
Originalmodell) - schon kleine Unterschiede in der Schwellenverteilung koennen
zu drastisch unterschiedlichen Endzustaenden fuehren.

Der Schwellenwert wird pro Agent aus `population.attributes.<threshold_key>`
gezogen (Default-Schluessel: "threshold"); fehlt das Attribut, gilt 0.5.

Quelle: Granovetter 1978, "Threshold Models of Collective Behavior",
American Journal of Sociology 83(6).
"""

from __future__ import annotations

from .base import Mechanic


class ThresholdMechanic(Mechanic):
    def __init__(self, threshold_key: str = "threshold", topic: str = "opinion"):
        self.threshold_key = threshold_key
        self.topic = topic

    def step(self, model) -> None:
        agents = list(model.agents)
        adopted = {a.unique_id: a.opinions[self.topic] >= 0.5 for a in agents}

        newly_adopted: list[int] = []
        for agent in agents:
            if adopted[agent.unique_id]:
                continue
            neighbors = agent.neighbors()
            if not neighbors:
                continue
            fraction_adopted = sum(1 for n in neighbors if adopted[n.unique_id]) / len(neighbors)
            threshold = agent.extra.get(self.threshold_key, 0.5)
            if fraction_adopted >= threshold:
                newly_adopted.append(agent.unique_id)

        if not newly_adopted:
            return
        by_id = {a.unique_id: a for a in agents}
        for agent_id in newly_adopted:
            by_id[agent_id].opinions[self.topic] = 1.0
