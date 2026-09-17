"""Agent des Sozialsimulators (Framework-Abschnitt 4).

Attribute kommen aus der Konfiguration, nicht aus dem Code: `extra` haelt alles,
was das Szenario unter `population.attributes` definiert hat (Alter, Bildung, ...).
`opinion` ist der von der aktiven Mechanik bewegte Zustand.
"""

from __future__ import annotations

from typing import Any

import mesa


class SocialAgent(mesa.Agent):
    def __init__(self, model: mesa.Model, opinion: float, extra: dict[str, Any] | None = None):
        super().__init__(model)
        self.opinion = opinion
        self.extra: dict[str, Any] = extra or {}

    def neighbors(self):
        """Alle Nachbarn im Sozialnetzwerk des Modells."""
        graph = self.model.grid.G
        neighbor_ids = graph.neighbors(self.model.agent_to_node[self.unique_id])
        node_to_agent = self.model.node_to_agent
        return [node_to_agent[n] for n in neighbor_ids]

    def __repr__(self) -> str:
        return f"SocialAgent(id={self.unique_id}, opinion={self.opinion:.3f})"
