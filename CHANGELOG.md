# Changelog

## 2.0.0 – Restrukturierung zu einer Programm-Bibliothek

Fachlich identische Ergebnisse (alle Berechnungen numerisch unverändert),
aber vollständig neue Struktur, Qualitätssicherung und Oberfläche.

### Architektur
- Der 1.200-Zeilen-Monolith `streamlit_app.py` wurde in eine
  UI-Schicht (`app/`) mit Views, Komponenten, Services, Theme und
  Formatierung zerlegt; der Entry-Point enthält nur noch Konfiguration
  und Navigation.
- Neue Service-Schicht (`app/services.py`) als einzige Brücke zwischen
  UI und Engine – inkl. Bewertungs-Cache auf Datei-mtimes: Die
  Portfolioseite rechnet Projekte nur noch bei tatsächlichen Änderungen
  neu statt bei jedem Streamlit-Rerun.
- `engine/__init__.py` definiert jetzt die vollständige öffentliche API
  (inkl. `MarktpreisSzenario`, `CashflowTimeseries`).

### Qualitätssicherung (neu)
- 46 Tests: Engine-Einheitstests mit handgerechneten Erwartungswerten
  (EAG-Prämienlogik, Verlustvortrag-Verrechnungsgrenze, Annuität/linear,
  Indexierung, Clamping), End-to-End-Pipeline, YAML-/Excel-Roundtrips,
  Formatierung/Slugs sowie UI-Smoke-Tests (Streamlit AppTest).
- `pyproject.toml` mit Projektmetadaten, Ruff- und Pytest-Konfiguration;
  GitHub-Actions-CI (Lint + Tests auf Python 3.11/3.12); Makefile.
- Ruff-sauber (u.a. `zip(..., strict=...)` durchgängig).

### Engine
- Robustere XIRR-Suche: Das Suchintervall wird schrittweise erweitert
  (10 → 100 → 1000), statt bei extremen Cashflows `None` zu liefern.
- Neue Kennzahl `eigenkapital_eur` (EK-Einsatz im Jahr 0) in `KPIs`.

### Usability
- Projekte können jetzt **dupliziert** und (mit Bestätigung)
  **gelöscht** werden; Projekt-IDs entstehen per Slugify mit
  Umlaut-Transliteration und Kollisions-Laufnummern statt naivem
  `lower().replace(" ", "-")`.
- **Cashflow-Export als Excel** direkt aus dem Projekt-Dashboard
  (Blätter „Cashflow" + „KPIs").
- Portfolioseite mit aggregierten Kennzahlen (Leistung,
  Investitionsvolumen, Ø EK-Rendite) und sortierbarer
  Vergleichstabelle inkl. spezifischer Investkosten (€/kWp).
- Neuer Dashboard-Tab **„Annahmen"**: der vollständig aufgelöste
  Parametersatz jeder Berechnung (Transparenz/Nachvollziehbarkeit).
- Cashflow-Übersichtstabelle mit sprechenden deutschen Spaltentiteln.

### Oberfläche
- Design-Token-System (`app/theme.py`): eine Farbquelle für CSS und
  Diagramme, Trianel-Rot als Akzent, KPI-Kacheln mit Markenkante,
  Karten-Hover, Header-Linie.
- Zentrales Plotly-Template: einheitliche Typografie, Legenden, Margins
  und **deutsche Zahlenformate auch in Achsen und Hovern**
  (`separators=",."`).
- Durchgängig deutsche Zahlenformatierung in der gesamten App
  (`app/formatting.py`): `7,43 %`, `1.234.567 €`, `1,25x` – statt
  gemischter US-/DE-Formate und `str.replace`-Hacks.

### Entfernt/ersetzt
- Direkte YAML-/Pfad-Zugriffe aus der UI (jetzt ausschließlich über
  Services), globales `st.cache_data.clear()` (jetzt gezielte
  Cache-Invalidierung).
