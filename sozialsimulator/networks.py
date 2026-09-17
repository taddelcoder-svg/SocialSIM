"""Baut die Umgebung/das Netzwerk aus `NetworkConfig` (Framework-Abschnitt 3 & 4).

Reale soziale Netzwerke sind weder zufaellig noch vollstaendig verbunden -
Small-World- (watts_strogatz) und skalenfreie (barabasi_albert) Graphen bilden
die in der Forschung beobachteten Strukturen naeherungsweise ab
(vgl. Framework-Dokument Abschnitt 4, Homophilie/Small-World).
"""

from __future__ import annotations

import networkx as nx

from .config import ConfigError, NetworkConfig


def build_network(network: NetworkConfig, n: int, seed: int | None) -> nx.Graph:
    p = network.params

    if network.type == "watts_strogatz":
        k = int(p.get("k", 4))
        beta = float(p.get("beta", 0.1))
        k = min(k, n - 1 if (n - 1) % 2 == 0 else n - 2)
        k = max(k, 2)
        return nx.watts_strogatz_graph(n=n, k=k, p=beta, seed=seed)

    if network.type == "barabasi_albert":
        m = int(p.get("m", 3))
        m = max(1, min(m, n - 1))
        return nx.barabasi_albert_graph(n=n, m=m, seed=seed)

    if network.type == "erdos_renyi":
        prob = float(p.get("p", 0.05))
        return nx.erdos_renyi_graph(n=n, p=prob, seed=seed)

    if network.type == "grid":
        side = p.get("side")
        if side is None:
            side = max(1, round(n ** 0.5))
        graph = nx.grid_2d_graph(side, side, periodic=bool(p.get("periodic", True)))
        graph = nx.convert_node_labels_to_integers(graph)
        return graph

    if network.type == "complete":
        return nx.complete_graph(n)

    raise ConfigError(f"unbekannter Netzwerktyp '{network.type}'")
