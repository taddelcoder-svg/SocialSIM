"""DeGroot-Lernen: gewichtete Mittelung von Nachbarmeinungen (Framework-Abschnitt 5).

Anders als Bounded Confidence gibt es keinen Schwellenwert, der entfernte
Meinungen ausblendet - jeder Nachbar zaehlt, aber nicht zwangslaeufig gleich
stark. Optional traegt jeder Agent ein `credibility`-Attribut (z.B. Reichweite
oder wahrgenommene Glaubwuerdigkeit einer Quelle); Nachbarn mit hoeherer
Glaubwuerdigkeit wiegen dann staerker in der Mittelung - relevant fuer
Szenario D im Framework-Dokument (Falschinformationskampagne, unterschiedliche
Glaubwuerdigkeitsgewichte fuer Quellen).

`self_weight` steuert, wie stark ein Agent an der eigenen bisherigen Meinung
festhaelt (0 = vollstaendige Neubildung aus den Nachbarn, nahe 1 = kaum
Veraenderung).

Quelle: DeGroot 1974, "Reaching a Consensus", Journal of the American
Statistical Association 69(345).
"""

from __future__ import annotations

from .base import Mechanic


class DeGrootMechanic(Mechanic):
    def __init__(self, self_weight: float = 0.5, credibility_key: str | None = None, topic: str = "opinion"):
        if not 0 <= self_weight <= 1:
            raise ValueError("self_weight muss in [0, 1] liegen")
        self.self_weight = self_weight
        self.credibility_key = credibility_key
        self.topic = topic

    def _neighbor_weights(self, neighbors) -> list[float]:
        if self.credibility_key is None:
            return [1.0] * len(neighbors)
        return [max(float(n.extra.get(self.credibility_key, 1.0)), 0.0) for n in neighbors]

    def step(self, model) -> None:
        agents = list(model.agents)
        current = {a.unique_id: a.opinions[self.topic] for a in agents}

        new_opinions: dict[int, float] = {}
        for agent in agents:
            neighbors = agent.neighbors()
            own = current[agent.unique_id]
            if not neighbors:
                new_opinions[agent.unique_id] = own
                continue

            weights = self._neighbor_weights(neighbors)
            total_weight = sum(weights)
            if total_weight <= 0:
                neighbor_avg = own
            else:
                neighbor_avg = sum(
                    w * current[n.unique_id] for w, n in zip(weights, neighbors)
                ) / total_weight

            new_opinions[agent.unique_id] = self.self_weight * own + (1 - self.self_weight) * neighbor_avg

        for agent in agents:
            agent.opinions[self.topic] = new_opinions[agent.unique_id]
