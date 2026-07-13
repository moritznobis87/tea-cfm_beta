# TEA PV-Projektbewertung

Wirtschaftlichkeitsrechnung für PV-Projekte nach dem **österreichischen
EAG-Marktprämienmodell** (gleitende Marktprämie) – ausgerichtet am
Arbeitsablauf eines Projektentwicklers: Ein neues Projekt ist in unter
zwei Minuten angelegt, alles selten Geänderte (Preiskurven,
Standardbetriebskosten, Finanzierungs- und Steuerlogik) wird zentral in
den Globalen Annahmen gepflegt und automatisch angewendet.

## Schnellstart

```bash
# Nutzung
pip install -r requirements.txt
streamlit run streamlit_app.py

# Entwicklung
pip install -e ".[dev]"
make test      # Test-Suite (Engine + UI-Smoke-Tests)
make lint      # Statische Analyse (ruff)
make run       # App starten
```

## Funktionsumfang

- **Portfolio**: aggregierte Kennzahlen (Leistung, Investitionsvolumen,
  Ø EK-Rendite), sortierbare Vergleichstabelle über alle Projekte,
  Projektkacheln mit Kern-KPI.
- **Projekt-Dashboard**: EK-Rendite (XIRR), NPV, min. DSCR,
  Investitionsvolumen und Eigenkapitaleinsatz; Cashflow-Diagramme
  (Erlöse, Betriebskosten nach Position, operativ, Finanzierung,
  gesamt + kumuliert), DSCR-Verlauf mit Deckungsgrenze, NPV-Kurve über
  Diskontsätze 0–10 % mit markierter IRR-Nullstelle, automatische
  EAG-Zuschlag-Sensitivität (±5 %/±10 %) und ein Transparenz-Tab mit dem
  vollständig aufgelösten Parametersatz der Berechnung.
- **Projektverwaltung**: Anlegen, Bearbeiten, Duplizieren, Löschen (mit
  Bestätigung), Cashflow-Export als Excel, Sichern/Wiederherstellen von
  Projekten und Globalen Annahmen über Excel-Dateien.
- **Fachlogik**: EAG-Marktprämie `MAX(Marktwert Solar, Zuschlagswert)`
  während der Förderdauer, danach reiner Marktverkauf; Ausfall der
  Förderung in Stunden negativer Preise; Inflationierung realer
  Marktwert-Kurven (der EAG-Zuschlag bleibt gesetzlich nominal fix);
  Annuitäten-/lineare Tilgung; KöSt mit AfA, Freibetrag und
  Verlustvortrag inkl. 75-%-Verrechnungsgrenze (§8 Abs. 4 Z 2 KStG).
- **Geschäftsregel**: Konventionelle Anlagen erhalten automatisch einen
  Abschlag von 25 % auf den EAG-Zuschlagswert gegenüber Agri-PV
  (`KONVENTIONELL_ZUSCHLAG_ABSCHLAG_PCT` in `engine/models.py`).

## Architektur

```
streamlit_app.py        Entry-Point: Seitenkonfiguration, Theme, Navigation
app/                    UI-Schicht (kennt die Engine, aber keine Dateiformate)
  config.py             Pfade, Konstanten, Session-State-Schlüssel
  theme.py              Design-Tokens, CSS, zentrales Plotly-Template
  formatting.py         Deutsche Zahlenformatierung (einzige Stelle dafür)
  services.py           Gecachter Datenzugriff, Bewertungs-Cache,
                        Projekt-Lebenszyklus (anlegen/duplizieren/löschen)
  components/           Wiederverwendbare Bausteine
    charts.py           Alle Plotly-Diagramme (DataFrame rein, Figure raus)
    project_form.py     Projektmaske (Neuanlage + Bearbeiten)
    sidebar.py          Excel-Import/-Export
  views/                Die Seiten der App
    overview.py         Portfolio + ausgewähltes Projekt-Dashboard
    project_detail.py   Dashboard mit Tabs und Aktionen
    new_project.py      Neuanlage
    assumptions.py      Globale Annahmen
engine/                 Reine Fachlogik – kein Streamlit-Import
  models.py             PVProject, GlobalAssumptions, EffectiveAssumptions
  pipeline.py           resolve_assumptions() (Merge), run_valuation()
  timeline / energy / revenue / opex / financing / tax / cashflow / kpis
  sensitivity.py        EAG-Zuschlag ±5/±10 %
  io_yaml.py, io_excel.py   Persistenz und Austauschformate
data/                   global_assumptions.yaml + ein YAML pro Projekt
tests/                  46 Tests: Engine-Einheiten, Pipeline-E2E,
                        IO-Roundtrips, Formatierung, UI-Smoke (AppTest)
```

Details und Begründungen der Designentscheidungen: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Datenhaltung

Projekte und Globale Annahmen liegen als YAML unter `data/` – bewusst
keine Datenbank (siehe ARCHITECTURE.md). **Streamlit Cloud hat kein
dauerhaftes Dateisystem**: Neu angelegte Projekte gehen bei einem
Reboot/Redeploy verloren, wenn sie nicht im Repo liegen. Der
Excel-Download in der Sidebar ist der vorgesehene Sicherungsweg.

## Qualitätssicherung

| Werkzeug | Zweck |
| --- | --- |
| `pytest` (46 Tests) | Fachlogik (handgerechnete Erwartungswerte), E2E-Pipeline, IO-Roundtrips, UI-Smoke-Tests |
| `ruff` | Lint + Import-Sortierung (Konfiguration in `pyproject.toml`) |
| GitHub Actions | CI auf Python 3.11/3.12: Lint + Tests bei jedem Push/PR |

## Bekannte Einschränkungen

- Die Beispiel-Preiskurven in `data/global_assumptions.yaml` sind
  plausible Platzhalter, keine validierten Marktprognosen – vor echtem
  Einsatz durch aktuelle Marktwert-Solar-/Preisszenario-Daten ersetzen.
- Betriebsperioden werden als volle Kalenderjahre modelliert (das erste
  Jahr anteilig); der Excel-Sonderfall „Vertragsende am Jahrestag" ist
  bewusst nicht abgebildet.
- Kein Nutzer-/Rechtemodell, kein Mehrbenutzerbetrieb.
- `pyarrow` ist auf `<25` gepinnt: Version 25.0.0 hat einen
  reproduzierbaren Segmentation Fault beim Rendern von `st.dataframe()`.

## Roadmap

1. Reale Marktpreiskurven statt Platzhalter
2. Portfoliovergleich/Ranking als eigene Auswertungsseite
3. Monte-Carlo-Simulation auf Basis von P15/P50/P85-Bandbreiten
