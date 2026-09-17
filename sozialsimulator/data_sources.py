"""Katalog realer Verteilungen fuer eigene Szenarien (Framework-Abschnitt 6).

Jeder Eintrag ist eine fertige `Distribution` (siehe config.py) mit Zitat -
die Rahmen-UI bietet ihn beim Bauen eines eigenen Szenarios als Alternative
zu einer frei geschaetzten Verteilung an. `applies_to` sagt, zu welcher
Wizard-Kategorie ein Eintrag passt: "opinion_continuous" (Meinungsbildung),
"initial_adoption" (Verhaltensverbreitung, Startanteil).

Fuer die Ausgangsmeinung zu einer konkreten, vom Nutzer erfundenen Nachricht
gibt es keine allgemeine reale Referenzverteilung (vgl. beispiel_degroot.json);
"trust_media" bildet stattdessen das allgemeine Grundvertrauen in Nachrichten
auf sozialen Medien ab - ein plausibler Ausgangspunkt, aber kein Ersatz fuer
eine Studie zur konkreten Nachricht selbst.

Diese Sammlung soll bei Bedarf weiter wachsen: neuer Eintrag = neues Dict mit
`id`, `label`, `applies_to`, `citation` (Quelle + Jahr + exakte Zahl) und
`distribution` (siehe config.py `Distribution`), kein Code sonst noetig.
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
    {
        "id": "eurostat_homeoffice_de_2023",
        "label": "Homeoffice-Nutzung (Deutschland, 2023)",
        "applies_to": "initial_adoption",
        "citation": (
            "Statistisches Bundesamt / Eurostat (Arbeitskraefteerhebung, Reihe lfsa_ehomp), 2023: "
            "23.5% der Erwerbstaetigen in Deutschland arbeiteten (teilweise) im Homeoffice "
            "(13.2% ueberwiegend, 10.4% an weniger als der Haelfte der Arbeitstage)"
        ),
        "distribution": {
            "kind": "choice",
            "params": {"options": [0.0, 1.0], "weights": [0.765, 0.235]},
        },
    },
    {
        "id": "covid_vaccine_willingness_de_2021",
        "label": "Impfbereitschaft gegen COVID-19 (Deutschland, August 2021)",
        "applies_to": "initial_adoption",
        "citation": (
            "Umfrage August 2021 (Statista): 83% der Befragten in Deutschland gaben an, sich "
            "sicher gegen COVID-19 impfen lassen zu wollen bzw. bereits geimpft zu sein"
        ),
        "distribution": {
            "kind": "choice",
            "params": {"options": [0.0, 1.0], "weights": [0.17, 0.83]},
        },
    },
    {
        "id": "nielsen_90_9_1",
        "label": "Beteiligungsungleichheit in Online-Communities (Nielsen)",
        "applies_to": "credibility",
        "citation": (
            "Nielsen (2006), 'Participation Inequality: The 90-9-1 Rule for Social Features': "
            "ca. 90% Lurker (kaum Reichweite), 9% gelegentliche Beitragende, 1% sehr aktive "
            "Vielposter/Multiplikatoren mit ueberproportionaler Reichweite"
        ),
        "distribution": {
            "kind": "histogram",
            "params": {
                "bins": [
                    {"min": 0.1, "max": 0.5, "weight": 0.90},
                    {"min": 0.5, "max": 2.0, "weight": 0.09},
                    {"min": 2.0, "max": 5.0, "weight": 0.01},
                ]
            },
        },
    },
    {
        "id": "eurobarometer_inflation_concern_de_2024",
        "label": "Sorge um steigende Preise/Inflation (Deutschland, 2024)",
        "applies_to": "opinion_continuous",
        "citation": (
            "Eurobarometer Standard 2024: 29% nennen steigende Preise/Inflation/Lebenshaltungskosten "
            "als wichtigstes Problem Deutschlands (Mehrfachauswahl unter mehreren Problemfeldern, keine "
            "Intensitaetsskala wie bei der Klimafrage) - hier vereinfacht als Zwei-Bin-Naeherung auf "
            "-1 (nicht das wichtigste Problem) bis +1 (wichtigstes Problem) abgebildet"
        ),
        "distribution": {
            "kind": "histogram",
            "params": {
                "bins": [
                    {"min": -1.0, "max": 0.0, "weight": 0.71},
                    {"min": 0.0, "max": 1.0, "weight": 0.29},
                ]
            },
        },
    },
    {
        "id": "yougov_ai_concern_de_2024",
        "label": "Sorge vor der wachsenden Bedeutung von KI im Alltag (Deutschland, 2024)",
        "applies_to": "opinion_continuous",
        "citation": (
            "YouGov (2024), 15-Laender-Vergleich: 37% der Deutschen sind skeptisch/besorgt gegenueber "
            "der wachsenden Bedeutung von KI im Alltag der naechsten 10 Jahre - im Vergleich "
            "ueberdurchschnittlich negativ; hier auf -1 (unbesorgt) bis +1 (besorgt) abgebildet"
        ),
        "distribution": {
            "kind": "histogram",
            "params": {
                "bins": [
                    {"min": -1.0, "max": 0.0, "weight": 0.63},
                    {"min": 0.0, "max": 1.0, "weight": 0.37},
                ]
            },
        },
    },
    {
        "id": "kba_elektroauto_bestand_de_2024",
        "label": "Elektroauto-Anteil am Pkw-Bestand (Deutschland, 2024)",
        "applies_to": "initial_adoption",
        "citation": (
            "Kraftfahrt-Bundesamt (KBA), Bestand 2024: 3.3% aller zugelassenen Pkw in Deutschland "
            "sind rein batterieelektrisch (+0.4 Prozentpunkte gegenueber 2023)"
        ),
        "distribution": {
            "kind": "choice",
            "params": {"options": [0.0, 1.0], "weights": [0.967, 0.033]},
        },
    },
    {
        "id": "reuters_trust_social_media_2026",
        "label": "Grundvertrauen in Nachrichten auf sozialen Medien (weltweit, 2026)",
        "applies_to": "trust_media",
        "citation": (
            "Reuters Institute Digital News Report 2026 (~100.000 Befragte, 48 Laender): nur 22% "
            "vertrauen Nachrichten auf sozialen Medien, 78% tun das nicht"
        ),
        "distribution": {
            "kind": "histogram",
            "params": {
                "bins": [
                    {"min": 0.0, "max": 0.4, "weight": 0.78},
                    {"min": 0.6, "max": 1.0, "weight": 0.22},
                ]
            },
        },
    },
]


def list_data_sources(applies_to: str | None = None) -> list[dict]:
    if applies_to is None:
        return DATA_SOURCES
    return [entry for entry in DATA_SOURCES if entry["applies_to"] == applies_to]
