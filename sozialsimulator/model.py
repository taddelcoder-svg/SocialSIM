"""Simulationsmodell: verbindet Konfiguration (config.py) mit Mesa (Framework-Abschnitt 2).

`SocialSimulationModel` baut aus einer `ScenarioConfig` Population, Netzwerk und
eine oder mehrere Mechaniken auf und fuehrt die Simulation Schritt fuer Schritt
aus. Nichts davon ist an ein bestimmtes Szenario gebunden - andere Config,
anderes Ergebnis, ohne Codeaenderung. Sind mehrere Mechaniken konfiguriert,
laufen sie pro Zeitschritt in der angegebenen Reihenfolge: jede sieht bereits
die Aenderungen der vorherigen im selben Tick (Pipeline, keine gleichzeitige
Anwendung). `initial_state` kann mehrere Meinungs-Topics enthalten (Framework-
Abschnitt 4, "mehrdimensionale Meinungen") - jeder Mechanik-Eintrag waehlt per
`topic` (Standard "opinion"), welche Achse er bewegt.
"""

from __future__ import annotations

import statistics

import mesa
from mesa.space import NetworkGrid
import numpy as np

from .agents import SocialAgent
from .config import ConfigError, ScenarioConfig
from .distributions import sample
from .events import apply_event
from .mechanics import get_mechanic
from .networks import build_network


class SocialSimulationModel(mesa.Model):
    def __init__(self, config: ScenarioConfig):
        super().__init__(rng=config.seed)
        self.config = config
        self.rng = np.random.default_rng(config.seed)

        graph = build_network(config.network, n=config.population.size, seed=config.seed)
        self.grid = NetworkGrid(graph)
        self.agent_to_node: dict[int, int] = {}
        self.node_to_agent: dict[int, SocialAgent] = {}

        n = config.population.size
        sampled_topics = self._sample_initial_state(config, n)

        attribute_values = {
            name: sample(dist, self.rng, n) for name, dist in config.population.attributes.items()
        }

        nodes = list(graph.nodes())
        for i, node in enumerate(nodes):
            extra = {name: values[i] for name, values in attribute_values.items()}
            agent_opinions = {topic: float(values[i]) for topic, values in sampled_topics.items()}
            agent = SocialAgent(self, opinions=agent_opinions, extra=extra)
            self.agent_to_node[agent.unique_id] = node
            self.node_to_agent[node] = agent
            self.grid.place_agent(agent, node)

        self.mechanics: list[tuple[str, object]] = [
            (m.model, get_mechanic(m.model, {**m.params, "topic": m.topic})) for m in config.mechanics
        ]
        self.schedule_tick = 0
        self._confidence_restore: list[tuple[int, object, float]] = []

        self.datacollector = mesa.DataCollector(model_reporters=self._build_reporters(sampled_topics.keys()))
        self.datacollector.collect(self)

    def _sample_initial_state(self, config: ScenarioConfig, n: int) -> dict[str, np.ndarray]:
        """Zieht jeden Meinungs-Topic aus `initial_state`; ein Topic mit `correlated_with`
        wird nach seinem Referenz-Topic gezogen und dann zu `strength` mit dessen
        (bereits gezogenen) Werten gemischt - mehrdimensionale, optional korrelierte
        Meinungen im Sinne von Framework-Abschnitt 4."""
        topic_order = sorted(
            config.initial_state.keys(), key=lambda t: config.initial_state[t].correlated_with is not None
        )
        sampled: dict[str, np.ndarray] = {}
        for topic in topic_order:
            dist = config.initial_state[topic]
            values = sample(dist, self.rng, n)
            if dist.correlated_with:
                ref_topic = dist.correlated_with["topic"]
                if ref_topic not in sampled:
                    raise ConfigError(
                        f"initial_state.{topic}.correlated_with verweist auf '{ref_topic}', "
                        "das noch nicht gezogen wurde (Konfigurationsfehler)"
                    )
                strength = float(dist.correlated_with.get("strength", 0.5))
                values = strength * sampled[ref_topic] + (1 - strength) * values
            sampled[topic] = values
        return sampled

    @staticmethod
    def _build_reporters(topics) -> dict:
        def make_mean(topic: str):
            return lambda m: statistics.mean(a.opinions[topic] for a in m.agents)

        def make_std(topic: str):
            return lambda m: statistics.pstdev(a.opinions[topic] for a in m.agents)

        reporters = {}
        for topic in topics:
            reporters[f"mean_{topic}"] = make_mean(topic)
            reporters[f"std_{topic}"] = make_std(topic)
        return reporters

    def get_mechanic(self, name: str):
        """Erste konfigurierte Mechanik-Instanz mit diesem Modellnamen (z.B. 'bounded_confidence')."""
        for mechanic_name, instance in self.mechanics:
            if mechanic_name == name:
                return instance
        raise ConfigError(f"keine Mechanik '{name}' in diesem Szenario konfiguriert")

    def _apply_due_events(self) -> None:
        for event in self.config.events:
            if event.tick == self.schedule_tick:
                apply_event(self, event)

    def _restore_expired_confidence(self) -> None:
        still_pending = []
        for restore_tick, mechanic, original_epsilon in self._confidence_restore:
            if restore_tick <= self.schedule_tick:
                mechanic.epsilon = original_epsilon
            else:
                still_pending.append((restore_tick, mechanic, original_epsilon))
        self._confidence_restore = still_pending

    def step(self) -> None:
        self._apply_due_events()
        self._restore_expired_confidence()
        for _, mechanic in self.mechanics:
            mechanic.step(self)
        self.schedule_tick += 1
        self.datacollector.collect(self)

    def run(self):
        """Fuehrt die im Szenario konfigurierte Anzahl Zeitschritte aus."""
        for _ in range(self.config.time.steps):
            self.step()
        return self.datacollector.get_model_vars_dataframe()
