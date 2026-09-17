"""Dotted-Path-Zugriff auf verschachtelte Config-Dicts (fuer die Sensitivitaetsanalyse).

Ein Pfad wie "mechanics.0.params.epsilon" oder "network.params.k" adressiert
einen Wert in `ScenarioConfig.to_dict()` - Zahlen-Segmente sind Listenindizes,
alles andere ein Dict-Schluessel.
"""

from __future__ import annotations

import copy
from typing import Any


def _step(node: Any, part: str) -> Any:
    if isinstance(node, list):
        return node[int(part)]
    return node[part]


def get_by_path(data: dict, path: str) -> Any:
    node = data
    for part in path.split("."):
        node = _step(node, part)
    return node


def set_by_path(data: dict, path: str, value: Any) -> dict:
    """Gibt eine NEUE, tief kopierte Struktur mit dem geaenderten Wert zurueck."""
    result = copy.deepcopy(data)
    parts = path.split(".")
    node = result
    for part in parts[:-1]:
        node = _step(node, part)
    last = parts[-1]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value
    return result
