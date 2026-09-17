"""Hegselmann-Krause Bounded-Confidence-Modell (Framework-Abschnitt 5).

Jeder Agent mittelt seine Meinung synchron mit den Nachbarn im Sozialnetzwerk,
deren Meinung innerhalb des Vertrauensradius `epsilon` liegt; weiter entfernte
Meinungen werden ignoriert. `mu` skaliert, wie stark sich ein Agent pro Schritt
in Richtung dieses Mittelwerts bewegt (1.0 = klassisches HK-Modell, Sprung auf
den Mittelwert; kleinere Werte = traegere Anpassung).

Quelle: Hegselmann & Krause 2002, "Opinion Dynamics and Bounded Confidence:
Models, Analysis and Simulation", JASSS 5(3).
"""

from __future__ import annotations

from .base import Mechanic


class BoundedConfidenceMechanic(Mechanic):
    def __init__(self, epsilon: float = 0.2, mu: float = 1.0):
        if not 0 < epsilon:
            raise ValueError("epsilon muss > 0 sein")
        if not 0 < mu <= 1:
            raise ValueError("mu muss in (0, 1] liegen")
        self.epsilon = epsilon
        self.mu = mu

    def step(self, model) -> None:
        agents = list(model.agents)
        current = {a.unique_id: a.opinion for a in agents}

        new_opinions: dict[int, float] = {}
        for agent in agents:
            own = current[agent.unique_id]
            in_confidence = [own]
            for neighbor in agent.neighbors():
                other = current[neighbor.unique_id]
                if abs(other - own) <= self.epsilon:
                    in_confidence.append(other)
            target = sum(in_confidence) / len(in_confidence)
            new_opinions[agent.unique_id] = own + self.mu * (target - own)

        for agent in agents:
            agent.opinion = new_opinions[agent.unique_id]
