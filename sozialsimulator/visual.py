"""Momentaufnahmen einer Simulation fuer die "Welt"-Ansicht der Rahmen-UI.

Nur fuer die Anzeige gedacht (Worldbox-artiges Live-Beobachten des Netzwerks,
siehe Framework-Dokument Abschnitt 10): ein einzelner Lauf - `time.runs` wird
ignoriert, da eine Animation ueber mehrere gemittelte Laeufe hinweg keinen Sinn
ergibt. Fuer jeden Zeitschritt wird eine Momentaufnahme der Meinungswerte je
Agent gespeichert, dazu eine feste, mit dem Szenario-Seed reproduzierbare
Netzwerk-Layout-Position je Knoten (networkx.spring_layout).
"""

from __future__ import annotations

import networkx as nx

from .config import ScenarioConfig
from .model import SocialSimulationModel


def run_visual(config: ScenarioConfig) -> dict:
    model = SocialSimulationModel(config)
    graph = model.grid.G
    node_ids = list(graph.nodes())
    layout = nx.spring_layout(graph, seed=config.seed if config.seed is not None else 0)
    topics = list(config.initial_state.keys())

    node_index = {node: i for i, node in enumerate(node_ids)}

    def snapshot() -> dict:
        return {
            topic: [float(model.node_to_agent[node].opinions[topic]) for node in node_ids]
            for topic in topics
        }

    frames = [snapshot()]
    for _ in range(config.time.steps):
        model.step()
        frames.append(snapshot())

    return {
        "topics": topics,
        "positions": [{"x": float(layout[node][0]), "y": float(layout[node][1])} for node in node_ids],
        "edges": [[node_index[u], node_index[v]] for u, v in graph.edges()],
        "frames": frames,
    }
