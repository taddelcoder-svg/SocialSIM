from __future__ import annotations

from abc import ABC, abstractmethod


class Mechanic(ABC):
    """Ein austauschbares Verhaltensmodell (Bounded Confidence, Schwellenwert, ...)."""

    @abstractmethod
    def step(self, model) -> None:
        """Fuehrt einen Zeitschritt der Mechanik auf `model.agents` aus."""
        raise NotImplementedError
