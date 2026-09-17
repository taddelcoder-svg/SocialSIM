"""Katalog realer Verteilungen fuer eigene Szenarien (Framework-Abschnitt 6).

Jeder Eintrag ist eine fertige `Distribution` (siehe config.py) mit Zitat -
die Rahmen-UI bietet ihn beim Bauen eines eigenen Szenarios als Alternative
zu einer frei geschaetzten Verteilung an. `applies_to` sagt, zu welcher
Wizard-Kategorie ein Eintrag passt: "opinion_continuous" (Meinungsbildung),
"initial_adoption" (Verhaltensverbreitung, Startanteil).

Fuer "Glaubwuerdigkeit einer Nachricht" gibt es bewusst keinen Eintrag: die
Ausgangsmeinung zu einer beliebigen, vom Nutzer erfundenen Nachricht hat
keine allgemeine reale Referenzverteilung (vgl. beispiel_degroot.json) - hier
bleibt nur die eigene Schaetzung, statt Daten falsch zu uebertragen.
"""

from __future__ import annotations

DATA_SOURCES: list[dict] = [
    {
        "id": "eurobarometer_climate_de_2023",
        "label": "Sorge um den Klimawandel (Deutschland, 2023)",
        "applies_to": "opinion_continuous",
        "citation": (
            "Special Eurobarometer 538 (Mai 2023), Deutschland: 71% 'sehr ernstes Problem', "
            "18% 'eher ernst', 11% 'nicht ernst' - auf eine Skala von -1 (nicht ernst) bis "
            "+1 (sehr ernst) abgebildet"
        ),
        "distribution": {
            "kind": "histogram",
            "params": {
                "bins": [
                    {"min": -1.0, "max": -0.333, "weight": 0.11},
                    {"min": -0.333, "max": 0.333, "weight": 0.18},
                    {"min": 0.333, "max": 1.0, "weight": 0.71},
                ]
            },
        },
    },
    {
        "id": "rogers_early_adopters_share",
        "label": "Anteil früher Übernehmer bei neuen Verhaltensweisen (Rogers)",
        "applies_to": "initial_adoption",
        "citation": (
            "Rogers (2003), Diffusion of Innovations: 'Innovators', die ein neues Verhalten "
            "unabhängig von sozialem Druck als Erste übernehmen (2.5% der Bevölkerung)"
        ),
        "distribution": {
            "kind": "choice",
            "params": {"options": [0.0, 1.0], "weights": [0.975, 0.025]},
        },
    },
]


def list_data_sources(applies_to: str | None = None) -> list[dict]:
    if applies_to is None:
        return DATA_SOURCES
    return [entry for entry in DATA_SOURCES if entry["applies_to"] == applies_to]
