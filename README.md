# Sozialsimulator – Konfigurationsschicht (Prototyp)

[![CI](https://github.com/taddelcoder-svg/SocialSIM/actions/workflows/ci.yml/badge.svg)](https://github.com/taddelcoder-svg/SocialSIM/actions/workflows/ci.yml)

Implementiert Abschnitt 2–5 des Framework-Konzepts: ein Szenario wird komplett
als JSON-Konfiguration beschrieben (Population, Netzwerk, Ausgangszustand,
Mechanik, Ereignisse, Zeit) – ohne Code zu ändern.

## Installation

```bash
pip install -r requirements.txt
```

## Ein Szenario ausführen

```bash
python -m sozialsimulator.run scenarios/beispiel_bounded_confidence.json --out ergebnis.csv
python -m sozialsimulator.run scenarios/beispiel_konsens.json
python -m sozialsimulator.run scenarios/beispiel_schwellenwert.json
python -m sozialsimulator.run scenarios/beispiel_degroot.json
python -m sozialsimulator.run scenarios/beispiel_kombiniert.json
python -m sozialsimulator.run scenarios/beispiel_mehrdimensional.json
```

## Rahmen-UI (Szenario zusammenklicken)

```bash
python -m sozialsimulator.webapp
```

Startet einen lokalen Server unter `http://127.0.0.1:5000` mit zwei Modi (oben rechts umschaltbar):

- **Einfach** (Standard): EIN Formular ohne Klick-Schritte. Thema eintippen
  (optional), eine von drei Kategorien waehlen (Meinungsbildung /
  Verhaltensverbreitung / Glaubwuerdigkeit einer Nachricht), EIN Regler plus
  EIN Prozentwert einstellen - alles andere (Gruppengroesse, Dauer, Ereignis)
  steht mit sinnvollen Standardwerten unter "Weitere Einstellungen (optional)".
  Passt ein Eintrag aus dem Datenquellen-Katalog zur Kategorie (z.B.
  Eurobarometer-Klimasorge zu "Meinungsbildung"), erscheint eine Checkbox
  "Stattdessen echte Daten nutzen" - per Default zaehlt die eigene Prozent-
  Schätzung, damit reale Daten nie versehentlich auf ein unpassendes Thema
  übertragen werden. "Simulieren" antwortet als Klartext-Satz ("Die Gruppe
  bleibt gespalten...") statt mit Rohzahlen.
- **Datenquellen-Katalog** (`/api/data-sources`, sechs Eintr&auml;ge, siehe
  n&auml;chster Abschnitt) - erweiterbar durch neue Eintr&auml;ge in
  `data_sources.py` (Distribution + Zitat + `applies_to`); je Kategorie
  k&ouml;nnen mehrere Quellen zur Auswahl stehen.
- **Zukunftsprojektion**: nach jeder Simulation ein Feld "1 Zeitschritt &asymp;
  X Tage/Wochen/Monate" - rechnet die Simulationsl&auml;nge in eine reale
  Zeitspanne um und nennt die Bandbreite (nicht nur den Mittelwert!) &uuml;ber
  die `time.runs`-Wiederholungsl&auml;ufe am Ende, inklusive Caveat, dass dies
  eine modellbasierte Spekulation und keine Vorhersage ist (Framework-Abschnitt 1
  & 8). Rein clientseitig aus der schon geladenen Antwort berechnet, kein
  erneuter Simulationslauf n&ouml;tig, wenn nur die Zeiteinheit ge&auml;ndert wird.
- **Erweitert**: das volle Formular (Population, Netzwerk, Meinungsthemen,
  mehrere Mechaniken, Ereignisse, Kalibrierung, Sensitivitaetsanalyse). "Aus
  dem Wizard heraus oeffnen" uebernimmt die gerade simulierte Konfiguration
  1:1 in dieses Formular zum Weiterschrauben. Der Abschnitt "Meinungsthemen"
  erlaubt beliebig viele benannte Topics per "+ Thema" (siehe naechster
  Abschnitt) - jedes mit eigener Verteilung/Quelle und optional per Checkbox
  "mit einem anderen Thema korreliert" an ein bereits vorhandenes Thema
  gekoppelt (Ziel-Dropdown + Staerke 0-1). Jede Mechanik-Zeile bekommt ein
  "Thema"-Dropdown, das automatisch alle aktuell definierten Themen anbietet,
  damit unterschiedliche Mechaniken gezielt unterschiedliche Achsen bewegen
  koennen. Ergebnis-Chart und -Zusammenfassung zeigen dann jedes Thema als
  eigene Linie/Zeile statt nur "opinion".

Beide Modi rufen dieselben `/api/*`-Endpunkte auf, die intern denselben Code
wie die CLI nutzen (`run_scenario`, `check_calibration`, `run_sensitivity`) -
keine Logik ist in JavaScript dupliziert.

Falls `OpenBLAS error: Memory allocation still failed` beim Start erscheint:
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m sozialsimulator.webapp`
(betrifft numpy/BLAS in eingeschraenkten Umgebungen, nicht den Simulator selbst).

## Mehrere Mechaniken kombinieren

`mechanics` in der Szenario-JSON akzeptiert entweder ein einzelnes Objekt
(`{"model": ..., "params": ...}`) oder eine Liste davon. Bei mehreren laeuft
jede Mechanik pro Zeitschritt in der angegebenen Reihenfolge - als Pipeline:
die zweite sieht bereits das Ergebnis der ersten im selben Tick, nicht den
Zustand vom Tick davor. Siehe `scenarios/beispiel_kombiniert.json` (DeGroot,
dann Bounded Confidence auf demselben Meinungswert).

Ein Event wie `narrow_confidence` kann bei mehreren Mechaniken per `"target":
"<modellname>"` gezielt eine davon ansprechen (z.B. nur `bounded_confidence`
verengen, `degroot` unberuehrt lassen); ohne `target` wird die erste Mechanik
mit einem `epsilon`-Attribut verwendet. Programmatischer Zugriff auf eine
bestimmte Instanz: `model.get_mechanic("bounded_confidence")`.

## Mehrdimensionale Meinungen

`initial_state` kann mehrere benannte Meinungs-Topics enthalten statt nur
`"opinion"` (z.B. `"klima"` und `"energiepolitik"`); jeder `mechanics`-Eintrag
waehlt per `"topic"` (Standard `"opinion"`), welche Achse er bewegt - so lassen
sich mehrere Themen mit unterschiedlichen Mechaniken/Parametern gleichzeitig
auf derselben Population simulieren. Ein Topic kann optional
`"correlated_with": {"topic": "<anderes Topic>", "strength": 0.0-1.0}` tragen:
nach dem unabhaengigen Ziehen wird der Wert zu `strength` mit dem (bereits
gezogenen) Referenz-Topic gemischt - eine einfache, transparente Korrelation,
keine volle gemeinsame Verteilung; nur eine Korrelationsebene wird unterstuetzt
(das Referenz-Topic darf selbst nicht korreliert sein). Siehe
`scenarios/beispiel_mehrdimensional.json`. `SocialAgent.opinion` bleibt als
Bequemlichkeits-Alias fuer `opinions["opinion"]` erhalten - alle Einzelthema-
Szenarien und bestehender Code laufen unveraendert weiter.

`check_calibration` prueft ein korreliertes Topic nicht isoliert (die
Mischung passiert erst bei der Populationserzeugung) und weist das explizit
aus, statt eine irrefuehrende Zahl zu zeigen.

## Echte Daten statt Platzhalter

Drei der vier Beispielszenarien ziehen Attribute/Ausgangswerte inzwischen aus
echten, zitierten Quellen statt aus frei gewaehlten Verteilungen (neue
Distribution `"histogram"` in `distributions.py`: binnierte reale Verteilungen,
z.B. Alterskohorten oder Umfrage-Antwortkategorien; jeder Bin = `{min, max, weight}`):

| Szenario | Attribut | Quelle |
| --- | --- | --- |
| `beispiel_bounded_confidence.json` | Alter | Destatis, Bevoelkerung nach Altersgruppen, Deutschland 2023 |
| `beispiel_bounded_confidence.json` | Meinung (Klimawandel) | Special Eurobarometer 538 (Mai 2023), Deutschland: 71% "sehr ernst", 18% "eher ernst", 11% "nicht ernst" |
| `beispiel_bounded_confidence.json` | Netzwerk (k=15) | Dunbar (1992) "sympathy group"-Schicht |
| `beispiel_schwellenwert.json` | Schwellenwert + Startadoption | Rogers (2003), Diffusion of Innovations: Adopterkategorien (2.5/13.5/34/34/16%) |
| `beispiel_degroot.json` | Glaubwuerdigkeit | Nielsen (2006), 90-9-1-Regel der Beteiligungsungleichheit |

Wo es keine passende reale Referenzverteilung gibt (z.B. Ausgangsmeinung zu einer
hypothetischen Falschinformation in `beispiel_degroot.json`), steht das explizit
als "Annahme" im `source`-Feld - genau die in Framework-Abschnitt 6 geforderte
Trennung zwischen echten Daten und Annahmen. `beispiel_konsens.json` bleibt
bewusst rein synthetisch, um Bounded-Confidence-Theorie isoliert zu testen.

Zusaetzlich zu den Beispielszenarien gibt es den **Datenquellen-Katalog**
(`data_sources.py`, ueber `/api/data-sources` abrufbar), der bei Bedarf weiter
waechst - aktuell:

| Quelle | `applies_to` | Zahl |
| --- | --- | --- |
| Special Eurobarometer 538 (2023), Klimasorge Deutschland | `opinion_continuous` | 71% / 18% / 11% |
| Rogers (2003), fruehe Uebernehmer | `initial_adoption` | 2.5% |
| Destatis/Eurostat, Homeoffice-Nutzung Deutschland 2023 | `initial_adoption` | 23.5% |
| Umfrage August 2021, Impfbereitschaft COVID-19 Deutschland | `initial_adoption` | 83% |
| Nielsen (2006), 90-9-1-Regel | `credibility` | 90/9/1% |
| Reuters Institute Digital News Report 2026, Vertrauen in News auf Social Media | `trust_media` | 22% |

Neue Quelle hinzufuegen: ein Dict mit `id`, `label`, `applies_to`, `citation`
und `distribution` an `DATA_SOURCES` in `data_sources.py` anhaengen - kein
weiterer Code noetig, die Rahmen-UI und `/api/data-sources` ziehen automatisch nach.

## Kalibrierung & Sensitivitätsanalyse

```bash
python -m sozialsimulator.calibration scenarios/beispiel_bounded_confidence.json
python -m sozialsimulator.sensitivity scenarios/beispiel_bounded_confidence.json \
    --param mechanics.0.params.epsilon --values 0.1,0.3,0.5,0.8,1.2 --metric std_opinion
```

**Kalibrierung** (`calibration.py`) zieht eine grosse, unabhaengige Stichprobe je
konfigurierter Verteilung (`initial_state`, `population.attributes`) und
vergleicht sie mit den Zielgewichten der Config selbst - deckt Tippfehler in
Gewichten/Bins auf, bevor eine Simulation ueberhaupt laeuft. Er prueft NICHT
gegen eine externe Wahrheit; ob die Zielverteilung selbst realistisch ist,
regelt die Quellenangabe aus dem vorigen Abschnitt.

**Sensitivitätsanalyse** (`sensitivity.py`) variiert einen Parameter per
Dotted-Path (z.B. `mechanics.0.params.epsilon`, `network.params.k`) ueber eine
Werteliste und misst eine Metrik (`mean_opinion`/`std_opinion`) am Ende (oder
einem gewaehlten Tick), gemittelt ueber `time.runs` Wiederholungen je Wert -
zeigt, wie robust ein Ergebnis gegenueber Unsicherheit in diesem Parameter ist.
Beispiel: bei `beispiel_bounded_confidence.json` bleibt die Meinungsstreuung
zwischen epsilon=0.1 und 0.5 durchgehend hoch (kein Konsens), kippt aber
zwischen 0.5 und 1.2 abrupt auf nahe Null - ein klarer Hinweis, dass das
Ergebnis "keine Einigung" nur bis zu einem kritischen epsilon robust ist.

Beide sind auch in der Rahmen-UI verfuegbar ("Kalibrierung pruefen"-Button,
Abschnitt "Sensitivitätsanalyse" im Formular).

## Struktur

- `sozialsimulator/config.py` – Konfigurationsschicht: `ScenarioConfig`, Validierung, JSON laden/speichern
- `sozialsimulator/distributions.py` – zieht Attribut-/Meinungswerte aus einer `Distribution`-Spezifikation (inkl. `"histogram"` fuer reale, binnierte Verteilungen)
- `sozialsimulator/networks.py` – baut das Sozialnetzwerk (Small-World, skalenfrei, ...) aus der Config
- `sozialsimulator/agents.py` – der Agent (Meinung + frei konfigurierbare Zusatzattribute)
- `sozialsimulator/mechanics/` – austauschbare Verhaltensmodelle: Bounded Confidence (Hegselmann-Krause), Schwellenwertmodell (Granovetter), DeGroot-Lernen
- `sozialsimulator/events.py` – externe Ereignisse zu festen Zeitschritten
- `sozialsimulator/model.py` – verbindet alles zu einem lauffähigen Mesa-Modell
- `sozialsimulator/run.py` – CLI: Szenario laden, mehrfach ausführen (`time.runs`), Ergebnis als CSV
- `sozialsimulator/webapp.py` + `sozialsimulator/static/` – Rahmen-UI (gefuehrter Wizard + erweitertes Formular): `/api/run`, `/api/calibrate`, `/api/sensitivity`, `/api/data-sources` fuehren denselben Code wie die CLI aus
- `sozialsimulator/data_sources.py` – Katalog realer, zitierter Verteilungen fuer eigene Szenarien (Framework-Abschnitt 6)
- `sozialsimulator/paths.py` – Dotted-Path-Zugriff auf ein Config-Dict (fuer die Sensitivitaetsanalyse)
- `sozialsimulator/calibration.py` – vergleicht gezogene Stichproben mit den Zielgewichten der Config (Framework-Abschnitt 8)
- `sozialsimulator/sensitivity.py` – variiert einen Parameter ueber eine Werteliste und misst die Auswirkung auf eine Metrik (Framework-Abschnitt 8)
- `scenarios/*.json` – sechs Beispielszenarien als Testfälle für die Konfigurationsschicht (zwei Bounded-Confidence-Varianten, ein Schwellenwert-Diffusionsszenario, ein DeGroot-Falschinformationsszenario, ein Szenario mit zwei kombinierten Mechaniken, ein Szenario mit zwei korrelierten Meinungsachsen)
- `tests/` – pytest-Suite (`python -m pytest`)

## Ein neues Verhaltensmodell hinzufügen

1. Neue Klasse in `sozialsimulator/mechanics/`, die von `Mechanic` erbt und `step(model)` implementiert
2. In `sozialsimulator/mechanics/__init__.py` unter einem Namen in `_REGISTRY` eintragen
3. In einer Szenario-JSON unter `mechanics.model` diesen Namen verwenden

Kein anderer Teil der Konfigurationsschicht muss angefasst werden – das ist der
Kern des Baukasten-Ansatzes aus dem Framework-Dokument (Abschnitt 5).

## Bezug zum Framework-Dokument

Siehe [KONZEPT.md](KONZEPT.md) für Vision, wissenschaftliche Grundlage
(ODD-Protokoll, Hegselmann-Krause, Granovetter, Homophilie, DeGroot),
weitere Szenariobeispiele, den aktuellen Umsetzungsstand (Abschnitt 10)
und die Grenzen/Risiken des Ansatzes (Abschnitt 11).
