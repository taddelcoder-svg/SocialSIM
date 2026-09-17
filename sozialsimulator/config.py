"""Konfigurationsschicht des Sozialsimulators (Rahmen-Abschnitt 3 im Framework-Dokument).

Ein Szenario wird als Daten beschrieben, nicht als Code: Population, Netzwerk,
Ausgangszustand, Mechanik (welches Verhaltensmodell), externe Ereignisse sowie
Zeit-/Zufallssteuerung. `ScenarioConfig.from_dict` validiert die Struktur, damit
ein fehlerhaftes Szenario beim Laden auffliegt statt mitten in der Simulation.

Jeder Wert kann ein `source`-Feld tragen (z.B. "World Values Survey 2022"), damit
sichtbar bleibt, was aus echten Daten stammt und was Annahme ist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json


class ConfigError(ValueError):
    """Ein Szenario ist strukturell ungueltig oder unvollstaendig."""


@dataclass
class Distribution:
    """Eine Verteilung, aus der ein Agentenattribut gezogen wird.

    `kind` waehlt die Ziehungsart: "normal", "uniform", "beta", "choice"
    (kategorial mit Gewichten), "constant" oder "histogram" (reale, binnierte
    Verteilungen wie Alterskohorten oder Umfrage-Antwortkategorien - jeder Bin
    traegt `min`, `max`, `weight`; innerhalb eines gezogenen Bins wird
    gleichverteilt gezogen).
    """

    kind: str
    params: dict[str, Any] = field(default_factory=dict)
    source: str | None = None
    correlated_with: dict[str, Any] | None = None
    """Nur fuer initial_state-Eintraege: {"topic": <anderes Topic>, "strength": 0..1}.
    Nach dem unabhaengigen Ziehen wird der Wert zu `strength` mit dem bereits
    gezogenen Wert des Referenz-Topics gemischt - eine einfache, transparente
    Korrelation statt einer vollen gemeinsamen Verteilung (siehe model.py).
    Nur eine Korrelationsebene wird unterstuetzt (das Referenz-Topic darf
    selbst nicht korreliert sein)."""

    _ALLOWED_KINDS = {"normal", "uniform", "beta", "choice", "constant", "histogram"}

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, path: str) -> "Distribution":
        if "kind" not in data:
            raise ConfigError(f"{path}: 'kind' fehlt (z.B. 'normal', 'uniform', 'choice')")
        kind = data["kind"]
        if kind not in cls._ALLOWED_KINDS:
            raise ConfigError(f"{path}: unbekannte Verteilung '{kind}' (erlaubt: {sorted(cls._ALLOWED_KINDS)})")
        correlated_with = data.get("correlated_with")
        if correlated_with is not None and "topic" not in correlated_with:
            raise ConfigError(f"{path}.correlated_with braucht 'topic'")
        return cls(
            kind=kind,
            params=dict(data.get("params", {})),
            source=data.get("source"),
            correlated_with=dict(correlated_with) if correlated_with else None,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"kind": self.kind, "params": self.params}
        if self.source:
            out["source"] = self.source
        if self.correlated_with:
            out["correlated_with"] = self.correlated_with
        return out


@dataclass
class PopulationConfig:
    size: int
    attributes: dict[str, Distribution] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PopulationConfig":
        if "size" not in data:
            raise ConfigError("population.size fehlt")
        size = int(data["size"])
        if size <= 1:
            raise ConfigError("population.size muss > 1 sein")
        attrs_raw = data.get("attributes", {})
        attributes = {
            name: Distribution.from_dict(spec, path=f"population.attributes.{name}")
            for name, spec in attrs_raw.items()
        }
        return cls(size=size, attributes=attributes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "attributes": {name: dist.to_dict() for name, dist in self.attributes.items()},
        }


@dataclass
class NetworkConfig:
    """Umgebung/Netzwerktyp (Rahmen-Abschnitt 3, Zeile 'Umgebung')."""

    type: str
    params: dict[str, Any] = field(default_factory=dict)

    _ALLOWED_TYPES = {"watts_strogatz", "barabasi_albert", "erdos_renyi", "grid", "complete"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NetworkConfig":
        if "type" not in data:
            raise ConfigError("network.type fehlt")
        net_type = data["type"]
        if net_type not in cls._ALLOWED_TYPES:
            raise ConfigError(f"network.type '{net_type}' unbekannt (erlaubt: {sorted(cls._ALLOWED_TYPES)})")
        return cls(type=net_type, params=dict(data.get("params", {})))

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "params": self.params}


@dataclass
class MechanicConfig:
    """Welches Verhaltensmodell aktiv ist (Framework-Abschnitt 5) plus seine Parameter.

    `topic` waehlt, welche Meinungsachse aus `initial_state` diese Mechanik bewegt
    (Standard: "opinion", der Topic-Name aller bisherigen Einzelthema-Szenarien) -
    mehrdimensionale Meinungen laufen als mehrere Mechanik-Eintraege mit
    unterschiedlichem `topic` in derselben `mechanics`-Liste.
    """

    model: str
    params: dict[str, Any] = field(default_factory=dict)
    topic: str = "opinion"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MechanicConfig":
        if "model" not in data:
            raise ConfigError("mechanics.model fehlt (z.B. 'bounded_confidence')")
        return cls(model=data["model"], params=dict(data.get("params", {})), topic=data.get("topic", "opinion"))

    def to_dict(self) -> dict[str, Any]:
        return {"model": self.model, "params": self.params, "topic": self.topic}


def _parse_mechanics(raw: Any) -> list["MechanicConfig"]:
    """`mechanics` ist entweder ein einzelnes Objekt oder eine Liste davon.

    Mehrere Eintraege werden im Modell in Reihenfolge pro Zeitschritt
    ausgefuehrt (Framework-Abschnitt 5, 'kombinierbare Module') - jede
    weitere Mechanik sieht bereits die Aenderungen der vorherigen im selben
    Tick.
    """
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not raw:
        raise ConfigError("mechanics muss ein Objekt oder eine nicht-leere Liste von Objekten sein")
    return [MechanicConfig.from_dict(m) for m in raw]


@dataclass
class Event:
    """Ein externes Ereignis zu einem festen Zeitschritt (Rahmen-Abschnitt 3)."""

    tick: int
    type: str
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, index: int) -> "Event":
        if "tick" not in data or "type" not in data:
            raise ConfigError(f"events[{index}]: 'tick' und 'type' sind Pflicht")
        return cls(tick=int(data["tick"]), type=data["type"], params=dict(data.get("params", {})))

    def to_dict(self) -> dict[str, Any]:
        return {"tick": self.tick, "type": self.type, "params": self.params}


@dataclass
class TimeConfig:
    steps: int = 100
    runs: int = 1

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimeConfig":
        steps = int(data.get("steps", 100))
        runs = int(data.get("runs", 1))
        if steps < 1:
            raise ConfigError("time.steps muss >= 1 sein")
        if runs < 1:
            raise ConfigError("time.runs muss >= 1 sein")
        return cls(steps=steps, runs=runs)

    def to_dict(self) -> dict[str, Any]:
        return {"steps": self.steps, "runs": self.runs}


@dataclass
class ScenarioConfig:
    """Ein vollstaendiges Szenario: alles, was der Rahmen (Abschnitt 3) einstellbar macht."""

    name: str
    population: PopulationConfig
    network: NetworkConfig
    initial_state: dict[str, Distribution]
    mechanics: list[MechanicConfig]
    time: TimeConfig
    events: list[Event] = field(default_factory=list)
    seed: int | None = None
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScenarioConfig":
        for required in ("name", "population", "network", "initial_state", "mechanics"):
            if required not in data:
                raise ConfigError(f"Pflichtfeld '{required}' fehlt im Szenario")

        initial_state_raw = data["initial_state"]
        if not initial_state_raw:
            raise ConfigError("initial_state braucht mindestens einen Meinungs-Topic")
        initial_state = {
            name: Distribution.from_dict(spec, path=f"initial_state.{name}")
            for name, spec in initial_state_raw.items()
        }
        for topic, dist in initial_state.items():
            if not dist.correlated_with:
                continue
            ref = dist.correlated_with["topic"]
            if ref == topic:
                raise ConfigError(f"initial_state.{topic}.correlated_with darf nicht auf sich selbst verweisen")
            if ref not in initial_state:
                raise ConfigError(f"initial_state.{topic}.correlated_with verweist auf unbekanntes Topic '{ref}'")
            if initial_state[ref].correlated_with:
                raise ConfigError(
                    f"initial_state.{topic}.correlated_with verweist auf '{ref}', das selbst korreliert ist - "
                    "nur eine Korrelationsebene wird unterstuetzt"
                )

        mechanics = _parse_mechanics(data["mechanics"])
        for m in mechanics:
            if m.topic not in initial_state:
                raise ConfigError(f"mechanics-Topic '{m.topic}' hat keinen passenden Eintrag in initial_state")

        events = [Event.from_dict(evt, index=i) for i, evt in enumerate(data.get("events", []))]

        return cls(
            name=data["name"],
            population=PopulationConfig.from_dict(data["population"]),
            network=NetworkConfig.from_dict(data["network"]),
            initial_state=initial_state,
            mechanics=mechanics,
            time=TimeConfig.from_dict(data.get("time", {})),
            events=events,
            seed=data.get("seed"),
            notes=data.get("notes"),
        )

    @classmethod
    def from_json(cls, text: str) -> "ScenarioConfig":
        return cls.from_dict(json.loads(text))

    @classmethod
    def from_file(cls, path: str | Path) -> "ScenarioConfig":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "population": self.population.to_dict(),
            "network": self.network.to_dict(),
            "initial_state": {name: dist.to_dict() for name, dist in self.initial_state.items()},
            "mechanics": [m.to_dict() for m in self.mechanics],
            "time": self.time.to_dict(),
            "events": [e.to_dict() for e in self.events],
            "seed": self.seed,
            "notes": self.notes,
        }
