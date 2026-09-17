"""Agent des Sozialsimulators (Framework-Abschnitt 4).

Attribute kommen aus der Konfiguration, nicht aus dem Code: `extra` haelt alles,
was das Szenario unter `population.attributes` definiert hat (Alter, Bildung, ...).
`opinions` haelt eine oder mehrere Meinungsachsen (Topics), von der aktiven
Mechanik(en) pro Zeitschritt bewegt - mehrdimensionale Meinungen im Sinne von
Framework-Abschnitt 4 ("ein oder mehrere kontinuierliche Werte").
"""

from __future__ import annotations

from typing import Any

import mesa


class SocialAgent(mesa.Agent):
    def __init__(self, model: mesa.Model, opinions: dict[str, float], extra: dict[str, Any] | None = None):
        super().__init__(model)
        self.opinions: dict[str, float] = dict(opinions)
        self.extra: dict[str, Any] = extra or {}

    @property
    def opinion(self) -> float:
        """Bequemlichkeitszugriff auf den Topic 'opinion' fuer Szenarien mit nur einer Meinungsachse."""
        return self.opinions["opinion"]

    @opinion.setter
    def opinion(self, value: float) -> None:
        self.opinions["opinion"] = value

    def neighbors(self):
        """Alle Nachbarn im Sozialnetzwerk des Modells."""
        graph = self.model.grid.G
        neighbor_ids = graph.neighbors(self.model.agent_to_node[self.unique_id])
        node_to_agent = self.model.node_to_agent
        return [node_to_agent[n] for n in neighbor_ids]

    def __repr__(self) -> str:
        return f"SocialAgent(id={self.unique_id}, opinions={self.opinions})"
