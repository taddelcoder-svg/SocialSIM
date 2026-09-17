# Sozialsimulator – Framework-Konzept

*Stand: 2026-09-17*

## 1. Vision & Zielsetzung

Der Sozialsimulator ist ein **konfigurierbares Framework**, mit dem man einen sozialen Kontext (Population, Umgebung, Regeln) definiert und daraus realistische, datengestützte Verlaufsszenarien ableiten lässt – statt eines Tools für genau eine Fragestellung.

**Kernidee:** Nicht "eine Simulation", sondern ein *Baukasten*, der drei Zutaten kombiniert:

1. **Reale Statistiken/Studien** als Ausgangswerte (z.B. Meinungsverteilungen, Netzwerkstrukturen, Verhaltensmuster)
2. **Wissenschaftlich etablierte Verhaltensmodelle** als Interaktionsregeln (wie beeinflussen sich Akteure gegenseitig?)
3. **Frei definierbarer Rahmen** durch den Nutzer (Wer? Wo? Welche Regeln? Wie lange?)

**Abgrenzung:** Kein reines Wirtschafts- oder Epidemiemodell (dafür gibt es spezialisierte Tools), sondern fokussiert auf *soziale* Dynamiken: Meinungsbildung, Gruppenverhalten, Normen, Diffusion von Verhalten/Ideen – optional angereichert um sozioökonomische Faktoren.

**Nicht-Ziel:** Präzise Vorhersage realer Ereignisse. Ziel ist ein *plausibles, in der Forschung verankertes "Was-wäre-wenn"* – explorativ, nicht prophetisch (das gilt für praktisch alle Agent-Based-Social-Simulationen in der Forschung).

## 2. Grundarchitektur

Der Simulator folgt dem etablierten **Agent-Based-Modeling**-Ansatz (ABM): viele individuelle Akteure mit eigenen Regeln interagieren in einer Umgebung, wodurch Muster auf Makro-Ebene *emergieren* – sie werden nicht vorgeschrieben, sondern entstehen aus vielen Mikro-Entscheidungen. Vier Bausteine:

| Baustein | Beschreibung |
| --- | --- |
| **Agenten** | Individuelle Akteure mit Attributen (siehe Abschnitt 4) und Entscheidungsregeln |
| **Umgebung** | Der Raum, in dem Agenten existieren: ein soziales Netzwerk (Graph), räumliches Raster, oder eine Mischung |
| **Regeln/Mechanik** | Wie Agenten sich pro Zeitschritt verhalten und beeinflussen (siehe Abschnitt 5) |
| **Zeit** | Diskrete Zeitschritte ("Ticks"), z.B. Tage/Monate; die Simulation läuft über N Schritte |

Um Vergleichbarkeit und wissenschaftliche Seriosität sicherzustellen, wird jedes Simulationsmodell nach dem **ODD-Protokoll** (Overview, Design concepts, Details) dokumentiert – dem in der Agentenmodellierung etablierten Standard für reproduzierbare Modellbeschreibungen ([Grimm et al., ODD Protocol](https://www.jasss.org/23/2/7.html)). Das zwingt dazu, für jedes Szenario explizit zu machen: Was wird beobachtet? Welche Zufallselemente gibt es? Wie wird das Modell initialisiert?

## 3. Szenario-Rahmen – was der Nutzer einstellt

Der Rahmen ist die Konfigurationsschicht, über die man ein Szenario definiert, ohne Code zu schreiben:

| Kategorie | Beispiel-Parameter |
| --- | --- |
| **Population** | Größe (z.B. 500–10.000 Agenten), demografische Verteilung (Alter, Bildung, Einkommen – kalibriert an echten Zensus-/Umfragedaten) |
| **Umgebung** | Netzwerktyp (z.B. Small-World, Skalenfrei, räumliches Raster einer Stadt), Verbindungsdichte |
| **Ausgangszustand** | Anfangsverteilung von Meinungen/Verhalten (z.B. "30% Impfskeptiker", kalibriert an Umfragedaten) |
| **Regeln/Mechanik** | Welches Verhaltensmodell aktiv ist (Meinungsdynamik, Schwellenwertverhalten, Diffusion – Abschnitt 5), Parameter wie Beeinflussbarkeit oder Homophilie-Stärke |
| **externe Ereignisse** | z.B. eine "Schock"-Nachricht zu Tick 50, eine neue Regel/Politikmaßnahme |
| **Zeit & Wiederholungen** | Anzahl Zeitschritte, Anzahl Simulationsläufe (für statistische Robustheit, da ABMs stochastisch sind) |
| **Zufalls-Seed** | Fixierbar für Reproduzierbarkeit oder variabel für Sensitivitätsanalysen |

Wichtig: Jeder Parameter sollte, wo möglich, einen **Default-Wert aus echten Daten** und eine **Quellenangabe** tragen (siehe Abschnitt 6) – der Nutzer kann davon abweichen, sieht aber immer, was der realistische Ausgangspunkt wäre.

## 4. Agentenmodell

Jeder Agent trägt einen Attributsatz, der die Heterogenität echter Bevölkerungen abbildet – Homogenität würde die Ergebnisse verfälschen (viele reale Effekte, z.B. Polarisierung, entstehen gerade aus Unterschieden zwischen Agenten):

- **Demografie:** Alter, Bildungsniveau, Einkommen, Wohnort/Region – Basis für Verteilungen: Zensusdaten oder Umfragen wie **World Values Survey** / **European Social Survey**
- **Meinungen/Werte:** ein oder mehrere kontinuierliche Werte (z.B. -1 bis +1 auf einer Themenachse), initialisiert aus realen Umfrageverteilungen statt Gleichverteilung
- **Psychologische Parameter:** Beeinflussbarkeit/Offenheit ("bounded confidence"-Radius), Risikoscheu, Konformitätsneigung – typischerweise als Verteilung, nicht als fixer Wert pro Typ
- **Netzwerkposition:** wie viele/welche Nachbarn ein Agent hat – reale soziale Netzwerke sind nicht zufällig, sondern zeigen **Homophilie** (ähnliche Menschen sind eher verbunden) und Small-World-Eigenschaften ([McPherson, Smith-Lovin & Cook 2001, "Birds of a Feather"](https://www.annualreviews.org/content/journals/10.1146/annurev.soc.27.1.415))
- **Ressourcen (optional):** verfügbare Zeit, Geld, Status – relevant bei sozioökonomischen Szenarien

Agenten können zu **Typen/Personas** gruppiert werden (z.B. "junge Urbane", "ländlich, älter"), deren Verteilungsparameter aus Studien stammen – innerhalb eines Typs bleibt aber Streuung erhalten, um keine Karikaturen zu erzeugen.

## 5. Simulationsmechanik – etablierte Modelle als Baukasten

Statt eigene Regeln zu erfinden, nutzt das Framework **empirisch etablierte Modelle der Sozialforschung** als austauschbare Module. Der Nutzer wählt eines oder kombiniert mehrere:

| Modell | Was es abbildet | Kernmechanik |
| --- | --- | --- |
| **Bounded-Confidence-Modell** (Hegselmann-Krause / Deffuant-Weisbuch) | Meinungsbildung, Polarisierung, Konsens vs. Fragmentierung | Ein Agent passt seine Meinung nur an Nachbarn an, deren Meinung innerhalb eines "Vertrauensradius" liegt – zu weit entfernte Meinungen werden ignoriert ([Hegselmann & Krause 2002](https://www.jasss.org/5/3/2.html)) |
| **Schwellenwertmodell** (Granovetter) | Kollektives Verhalten: Proteste, Trends, "Kipppunkte" | Jeder Agent handelt erst, wenn ein individueller Anteil seiner Umgebung bereits gehandelt hat – kleine Unterschiede in der Schwellenverteilung können zu drastisch unterschiedlichen Ergebnissen führen ([Granovetter 1978, "Threshold Models of Collective Behavior"](https://sociology.stanford.edu/publications/threshold-models-collective-behavior)) |
| **Homophilie-Netzwerkbildung** | Wie sich soziale Netzwerke selbst formen/verändern | Verbindungen entstehen bevorzugt zwischen ähnlichen Agenten; strukturiert, wer wen überhaupt beeinflussen kann ([McPherson et al. 2001](https://www.annualreviews.org/content/journals/10.1146/annurev.soc.27.1.415)) |
| **Diffusionsmodelle** (z.B. Bass-Diffusion, SIR-artig) | Ausbreitung von Verhalten, Produkten, Gerüchten | Kombination aus interner Adoption und Ansteckung über Netzwerkkontakte |
| **DeGroot-Lernen** | Wie Gruppen durch wiederholten Meinungsaustausch zu gemeinsamen Einschätzungen kommen | Gewichteter Mittelwert der Nachbarmeinungen pro Zeitschritt |

Diese Module sind bewusst **kombinierbar**: z.B. Homophilie bestimmt das Netzwerk, auf dem dann ein Bounded-Confidence-Prozess läuft, unterbrochen von einem externen Schock-Ereignis aus dem Szenario-Rahmen.

## 6. Wissens- und Datenbasis

**Offene Datensätze für realistische Ausgangswerte:**

| Quelle | Liefert | Zugang |
| --- | --- | --- |
| [World Values Survey](https://www.worldvaluessurvey.org/) | Werte, Einstellungen, Religiosität, Politik in 120+ Ländern, alle 5 Jahre seit 1981 | Kostenlos, Rohdaten |
| [European Social Survey (ESS)](https://www.europeansocialsurvey.org/) | Einstellungen, Verhalten, Demografie europaweit, vergleichbar über Zeit | Kostenlos |
| [European Values Study (EVS)](https://europeanvaluesstudy.eu/) | Ähnlich WVS, Fokus Europa, bei GESIS gehostet | Kostenlos |
| Nationale Zensus-/Statistikamt-Daten | Demografische Grundverteilungen (Alter, Bildung, Einkommen, Region) | Länderabhängig, meist offen |

**Wissenschaftliche Modelle als methodische Grundlage** (siehe auch Abschnitt 5):

- Grimm et al., **ODD Protocol** – Standard zur Dokumentation von Agentenmodellen: [jasss.org/23/2/7](https://www.jasss.org/23/2/7.html)
- Hegselmann & Krause 2002, **Bounded Confidence Opinion Dynamics**: [jasss.org/5/3/2](https://www.jasss.org/5/3/2.html)
- Granovetter 1978, **Threshold Models of Collective Behavior**, American Journal of Sociology: [Stanford Soziologie](https://sociology.stanford.edu/publications/threshold-models-collective-behavior)
- McPherson, Smith-Lovin & Cook 2001, **Birds of a Feather: Homophily in Social Networks**, Annual Review of Sociology: [annualreviews.org](https://www.annualreviews.org/content/journals/10.1146/annurev.soc.27.1.415)

**Prinzip:** Jedes Szenario im Framework sollte dokumentieren, *welche* Zahl/Verteilung aus *welcher* Quelle stammt (Stand/Jahr angeben) – und wo stattdessen eine Annahme getroffen wurde. Das macht Ergebnisse nachvollziehbar und verhindert, dass ein plausibel wirkendes Diagramm als "harte Prognose" missverstanden wird.

**Im Prototyp bereits konkret eingebunden** (statt Platzhalter, siehe `scenarios/*.json` im Code): Destatis-Altersverteilung Deutschland 2023, Special Eurobarometer 538 (Klimawandel, Mai 2023) für die Startmeinung, Rogers' Adopterkategorien für Schwellenwerte, Nielsens 90-9-1-Regel für Glaubwürdigkeitsgewichte, sowie Dunbars Netzwerk-Schichten für die Kontaktzahl. Wo keine passende reale Verteilung existiert, steht das explizit als "Annahme" im Quellenfeld.

Der Katalog wächst laufend weiter (`data_sources.py`, aktuell sechs Einträge) – u.a. um Destatis/Eurostat-Zahlen zur Homeoffice-Nutzung (23.5%, 2023), eine Umfrage zur COVID-19-Impfbereitschaft (83%, August 2021) und den Reuters Institute Digital News Report zum Vertrauen in Nachrichten auf sozialen Medien (22%, 2026).

**Zukunftsprojektion statt Vorhersage:** Die Rahmen-UI rechnet die simulierte Schrittzahl in eine reale Zeitspanne um ("1 Zeitschritt ≈ X Wochen") und nennt am Ende die Bandbreite über die Wiederholungsläufe (nicht nur den Mittelwert) – immer mit dem Hinweis, dass dies eine modellbasierte Spekulation ist, keine Vorhersage. Das hält sich bewusst an das in Abschnitt 1 formulierte Nicht-Ziel: eine Bandbreite aus tatsächlicher Simulationsstreuung ist etwas anderes als eine erfundene präzise Zahl.

**Mechaniken sind jetzt auch kombinierbar** (siehe `scenarios/beispiel_kombiniert.json`): `mechanics` akzeptiert eine Liste, die pro Zeitschritt als Pipeline läuft (spätere Mechaniken sehen bereits das Ergebnis früherer im selben Tick). Events können über `target` gezielt eine bestimmte Mechanik ansprechen.

## 7. Beispielszenarien – wie der Rahmen konfiguriert würde

**A) Polarisierung in einer Kleinstadt**

- Population: 2.000 Agenten, Altersverteilung aus Zensusdaten
- Umgebung: Small-World-Netzwerk + Homophilie nach Bildung/Alter
- Mechanik: Bounded-Confidence-Modell, Startmeinungen aus einer realen Umfrage zu einem Streitthema
- Ereignis: Zu Tick 30 eine "virale" Nachricht, die die Konfidenzradien temporär verengt
- Frage: Führt das zu zwei stabilen Lagern oder zu Konsens?

**B) Verbreitung eines neuen Verhaltens** (z.B. Impfbereitschaft, Umweltverhalten)

- Mechanik: Schwellenwertmodell + Diffusion über das Netzwerk
- Parameter: Schwellenverteilung aus Verhaltensstudien, Ausgangsanteil "früher Übernehmer" aus Umfragedaten
- Frage: Ab welchem Anteil überzeugter Erstakteure kippt die Mehrheit?

**C) Soziale Ungleichheit über Generationen**

- Population: Haushalte statt Einzelpersonen, mit Einkommen/Bildung aus Sozialstatistik
- Mechanik: Ressourcenweitergabe + Netzwerkeffekte auf Bildungschancen
- Frage: Wie stark verstärkt Homophilie (ähnliche Nachbarschaften) bestehende Ungleichheit über Zeit?

**D) Reaktion auf eine Falschinformationskampagne**

- Mechanik: DeGroot-Lernen + Bounded Confidence, unterschiedliche "Glaubwürdigkeitsgewichte" für Quellen
- Frage: Wie schnell und wie weit verbreitet sich eine Falschinformation je nach Netzwerkstruktur?

Diese vier zeigen, dass **derselbe Rahmen** (Abschnitt 3) mit unterschiedlicher Mechanik (Abschnitt 5) und Datenbasis (Abschnitt 6) völlig verschiedene Fragestellungen abdeckt.

## 8. Validierung & Kalibrierung

Damit "realistisch" mehr als ein Versprechen ist, braucht jedes Szenario einen Abgleich mit echten Daten:

- **Kalibrierung:** Anfangsverteilungen (Meinungen, Demografie, Netzwerkstruktur) werden aus den Quellen aus Abschnitt 6 gezogen, nicht frei erfunden
- **Sensitivitätsanalyse:** Jeder unsichere Parameter (z.B. Beeinflussbarkeit) wird über einen plausiblen Bereich variiert – zeigt, wie robust ein Ergebnis ist
- **Mehrfachläufe:** Da ABMs stochastisch sind, werden Szenarien mehrfach mit unterschiedlichen Zufalls-Seeds wiederholt; berichtet wird eine Verteilung/Bandbreite, kein Einzelergebnis
- **Face Validity:** Stimmen bekannte Grundmuster (z.B. dass höhere Homophilie zu mehr Fragmentierung führt)? Falls nicht, ist das Modell fehlerhaft
- **Historischer Abgleich (wo möglich):** Lässt sich ein bereits beobachtetes reales Ereignis (z.B. eine bekannte Meinungsverschiebung) mit dem Modell annähernd reproduzieren?

Das Ergebnis ist immer als **Bandbreite plausibler Verläufe** zu kommunizieren, nicht als einzelne Vorhersage – im Einklang mit dem in Abschnitt 1 formulierten Nicht-Ziel.

**Im Prototyp umgesetzt** (`calibration.py`, `sensitivity.py`, auch als Rahmen-UI-Buttons): Der Kalibrierungscheck zieht eine große Stichprobe je konfigurierter Verteilung und vergleicht sie mit den Zielgewichten der Config selbst – er prüft also interne Konsistenz, nicht externe Wahrheit (die regelt die Quellenangabe). Die Sensitivitätsanalyse variiert einen Parameter per Dotted-Path (z.B. `mechanics.0.params.epsilon`) über eine Werteliste und zeigt die Auswirkung auf eine Metrik. Erster Befund am Klimawandel-Szenario: die Meinungsstreuung bleibt für epsilon zwischen 0.1 und 0.5 durchgehend hoch (kein Konsens), kippt aber zwischen 0.5 und 1.2 abrupt auf nahe Null – ein klassischer Phasenübergang, der zeigt, dass das Szenario-Ergebnis nur innerhalb eines bestimmten Wertebereichs robust ist.

## 9. Technische Umsetzungsoptionen

| Option | Stärken | Grenzen |
| --- | --- | --- |
| **Mesa** (Python) | Ausgereiftes ABM-Framework, gute Netzwerk-/Datenanbindung (pandas, networkx), leicht mit realen Datensätzen zu füttern, gut visualisierbar | Erfordert Python-Kenntnisse |
| **NetLogo** | Sehr etabliert in der Forschung, viele fertige Modelle (inkl. Hegselmann-Krause, Schwellenwertmodelle) als Vorlage, eingebaute Visualisierung | Eigene Skriptsprache, weniger flexibel für Datenimport |
| **Custom (Python/JS)** | Volle Kontrolle, gut für eine interaktive Web-Oberfläche später | Mehr Aufwand, "das Rad neu erfinden" |

**Empfehlung:** Start mit **Mesa**, da es (a) Python-Ökosystem für Datenanbindung an WVS/ESS nutzt, (b) NetworkX für die Netzwerkmodelle mitbringt, und (c) sich später leicht hinter eine Web-Oberfläche legen lässt. NetLogo eignet sich gut, um zunächst schnell mit vorhandenen Beispielmodellen (Hegselmann-Krause, Schelling-Segregation) zu experimentieren, bevor eigener Code entsteht.

**Umgesetzt:** Die Empfehlung wurde befolgt – der Prototyp läuft auf Mesa 3.x + NetworkX + pandas, mit Flask als dünner Web-Schicht darüber (`webapp.py`). Diese Sektion ist damit dokumentierte Entscheidung, nicht mehr offene Frage.

## 10. Nächste Schritte

**Umgesetzt** (Stand: `sozialsimulator/`, Python/Mesa-Prototyp):

1. Konfigurationsschicht (Abschnitt 3) vollständig, inkl. der Verteilung `"histogram"` für reale Bin-Daten (Altersgruppen, Umfrage-Antwortkategorien)
2. Drei Mechaniken aus Abschnitt 5 – Bounded Confidence, Schwellenwertmodell, DeGroot – austauschbar UND kombinierbar (`mechanics` als Liste, läuft als Pipeline pro Zeitschritt)
3. Kalibrierung & Sensitivitätsanalyse (Abschnitt 8) als eigene Module plus Rahmen-UI-Bedienelemente
4. Datenquellen-Katalog (`data_sources.py`, aktuell sechs Einträge) statt einmaliger Platzhalter-Ersetzung – wächst laufend weiter
5. Rahmen-UI: von "alle Parameter gleichzeitig" über einen mehrstufigen Wizard zu einem einzigen, vorbelegten Formular mit optionalen Detaileinstellungen (mehrere Iterationen nach Nutzer-Feedback zur Bedienbarkeit)
6. Zukunftsprojektion: reale Zeitspanne + Bandbreite über Wiederholungsläufe statt einer einzelnen Zahl, mit explizitem Vorhersage-Caveat

**Noch offen:**

1. **Mehrdimensionale Meinungen** – Abschnitt 4 sieht "ein oder mehrere" Meinungsachsen pro Agent vor; der Prototyp hat bisher nur eine (`opinion`). Mehrere Themen gleichzeitig (ggf. korreliert) wäre der nächste Schritt zu realistischeren Agenten.
2. **Dynamische Netzwerke** – Abschnitt 5 nennt "Homophilie-Netzwerkbildung" als Modell; der Prototyp baut Netzwerke bisher nur einmal beim Start. Ein Modell, das Verbindungen während der Simulation neu knüpft oder kappt, fehlt noch.
3. **Historischer Abgleich** (Abschnitt 8) – bisher nicht umgesetzt: ein Szenario an einem bereits bekannten, dokumentierten realen Verlauf testen, um Face Validity über reine Plausibilität hinaus zu prüfen.
4. **Geografische Einseitigkeit des Datenkatalogs** – alle sechs Einträge stammen aus Deutschland/EU bzw. global aggregierten Studien; siehe Abschnitt 11.
5. **Szenarien speichern & vergleichen** – aktuell wird jede Simulation isoliert betrachtet; ein Vergleich mehrerer ganzer Szenario-Varianten nebeneinander existiert nicht (nur Sensitivitätsanalyse für einen einzelnen Parameter).

Der Prototyp bleibt ein Konfigurations- und Analysewerkzeug, kein Orakel – jeder weitere Ausbauschritt sollte an Abschnitt 8 (Kalibrierung/Sensitivität) und Abschnitt 11 (Grenzen) gemessen werden, bevor er als "fertig" gilt.

## 11. Grenzen, Verzerrungen & verantwortungsvoller Einsatz

Ein Framework, das "echte Daten" und "wissenschaftliche Modelle" im Namen trägt, kann leicht mehr Autorität ausstrahlen, als ihm zusteht. Diese Grenzen gehören deshalb genauso zum Konzept wie die Fähigkeiten:

- **Datenverzerrung (Bias):** Der aktuelle Datenkatalog bildet fast ausschließlich Deutschland/EU-Kontexte ab (Destatis, Eurobarometer) bzw. global aggregierte Studien (Reuters, Nielsen), die selbst meist aus WEIRD-Gesellschaften (Western, Educated, Industrialized, Rich, Democratic) stammen. Ein Szenario zu einem anderen kulturellen Kontext mit diesen Zahlen zu füttern, wäre genau die Art von Fehlanwendung, die das `source`-Feld eigentlich sichtbar machen soll – Sichtbarkeit ersetzt aber keine Sorgfalt bei der Auswahl.
- **Modellwahl ist eine Annahme:** Dass sich Meinungsbildung wie Bounded Confidence verhält, ist eine unter mehreren konkurrierenden Theorien, keine bewiesene Tatsache. Andere Modelle (z.B. soziale Identitätstheorie, Echo-Chamber-Modelle mit aktiver Vermeidung Andersdenkender) würden andere Ergebnisse liefern. Die Auswahl in Abschnitt 5 ist eine Startbibliothek, kein abschließender Kanon.
- **Kleine Regeländerungen, große Effekte:** Die Sensitivitätsanalyse hat bereits gezeigt (Abschnitt 8), dass Ergebnisse an Schwellenwerten kippen können (Phasenübergänge). Ein einzelner Simulationslauf ohne Sensitivitätscheck ist deshalb praktisch immer irreführend.
- **Kein Ersatz für echte Forschung:** Simulationsergebnisse sind Hypothesen, die eine echte Studie (Umfrage, Feldexperiment, historische Fallanalyse) stützen oder in Frage stellen kann – niemals umgekehrt. Das Framework erzeugt Was-wäre-wenn-Erzählungen, keine Evidenz.
- **Missbrauchsrisiko:** Eine plausibel aussehende Grafik mit echten Quellenangaben kann benutzt werden, um eine vorgefasste Meinung zu untermauern ("die Simulation zeigt, dass..."). Die durchgängige Kennzeichnung von Quelle vs. Annahme (Abschnitt 6) und der Spekulations-Hinweis bei der Zukunftsprojektion sind Gegenmaßnahmen, aber kein vollständiger Schutz gegen selektive oder bewusst irreführende Nutzung.

**Faustregel:** Je politischer oder folgenreicher die Frage, an die ein Szenario andocken soll, desto mehr Gewicht sollten Kalibrierung, Sensitivitätsanalyse und eine explizite Diskussion dieser Grenzen bekommen – nie das Simulationsergebnis allein.
