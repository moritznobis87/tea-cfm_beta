"""
Service-Schicht zwischen UI und Engine.

Aufgaben:
- Datei-Zugriff buendeln (die Views kennen keine Pfade und kein YAML)
- Berechnungen cachen: Bewertungen werden nur neu gerechnet, wenn sich
  die Projekt-Datei ODER die Globalen Annahmen tatsaechlich geaendert
  haben (mtime als Cache-Schluessel). Ohne diesen Cache wuerde die
  Portfolioseite bei jedem Streamlit-Rerun jedes Projekt komplett neu
  durchrechnen.
- Projekt-Lebenszyklus: anlegen, aktualisieren, duplizieren, loeschen,
  eindeutige IDs vergeben.
"""

from __future__ import annotations

import io
import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

from engine import (
    GlobalAssumptions,
    PVProject,
    ValuationResult,
    run_eag_sensitivity,
    run_valuation,
)
from engine.io_yaml import (
    load_global_assumptions_yaml,
    load_project_yaml,
    save_global_assumptions_yaml,
    save_project_yaml,
)

from .config import GLOBAL_ASSUMPTIONS_PATH, PROJECTS_DIR

# ---------------------------------------------------------------------------
# Globale Annahmen
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _load_global_assumptions_cached(mtime: float) -> GlobalAssumptions:
    return load_global_assumptions_yaml(GLOBAL_ASSUMPTIONS_PATH)


def get_global_assumptions() -> GlobalAssumptions:
    """Laedt die Globalen Annahmen; mtime im Cache-Schluessel macht
    Aenderungen nach dem Speichern sofort sichtbar, ohne bei jedem Rerun
    von Platte zu lesen."""
    mtime = GLOBAL_ASSUMPTIONS_PATH.stat().st_mtime
    return _load_global_assumptions_cached(mtime)


def save_global_assumptions(assumptions: GlobalAssumptions) -> None:
    save_global_assumptions_yaml(assumptions, GLOBAL_ASSUMPTIONS_PATH)
    _load_global_assumptions_cached.clear()
    _run_valuation_cached.clear()
    _run_sensitivity_cached.clear()


# ---------------------------------------------------------------------------
# Projekte: Zugriff
# ---------------------------------------------------------------------------


def list_project_files() -> dict[str, Path]:
    """Alle Projekt-Dateien, alphabetisch, als {projekt_id: pfad}."""
    return {f.stem: f for f in sorted(PROJECTS_DIR.glob("*.yaml"))}


def get_project(project_id: str) -> PVProject | None:
    path = PROJECTS_DIR / f"{project_id}.yaml"
    if not path.exists():
        return None
    return load_project_yaml(path)


# ---------------------------------------------------------------------------
# Bewertung (gecacht auf Datei-Aenderungen)
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _run_valuation_cached(
    project_path: str, project_mtime: float, ga_mtime: float
) -> ValuationResult:
    project = load_project_yaml(project_path)
    return run_valuation(project, get_global_assumptions())


def get_valuation(project_id: str) -> ValuationResult | None:
    """Vollstaendige Projektbewertung - neu gerechnet nur bei geaenderter
    Projekt-Datei oder geaenderten Globalen Annahmen."""
    path = PROJECTS_DIR / f"{project_id}.yaml"
    if not path.exists():
        return None
    return _run_valuation_cached(
        str(path), path.stat().st_mtime, GLOBAL_ASSUMPTIONS_PATH.stat().st_mtime
    )


@st.cache_data(show_spinner=False)
def _run_sensitivity_cached(
    project_path: str, project_mtime: float, ga_mtime: float
) -> pd.DataFrame:
    project = load_project_yaml(project_path)
    return run_eag_sensitivity(project, get_global_assumptions())


def get_eag_sensitivity(project_id: str) -> pd.DataFrame | None:
    """EAG-Zuschlag-Sensitivitaet (5 Bewertungslaeufe) - gecacht, weil sie
    sonst bei jedem Oeffnen des Sensitivitaets-Tabs neu laufen wuerde."""
    path = PROJECTS_DIR / f"{project_id}.yaml"
    if not path.exists():
        return None
    return _run_sensitivity_cached(
        str(path), path.stat().st_mtime, GLOBAL_ASSUMPTIONS_PATH.stat().st_mtime
    )


# ---------------------------------------------------------------------------
# Projekte: Lebenszyklus
# ---------------------------------------------------------------------------

_UMLAUT_MAP = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "ae", "Ö": "oe", "Ü": "ue", "ß": "ss"}
)


def make_project_id(name: str, existing_ids: set[str] | None = None) -> str:
    """Erzeugt eine dateisystem- und URL-sichere, eindeutige Projekt-ID.

    'Sonnenfeld Süd (Bauabschnitt 2)' -> 'sonnenfeld-sued-bauabschnitt-2'.
    Bei Kollision wird '-2', '-3', ... angehaengt statt still zu
    ueberschreiben.
    """
    slug = name.strip().translate(_UMLAUT_MAP)
    slug = unicodedata.normalize("NFKD", slug).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-") or "projekt"

    existing = existing_ids if existing_ids is not None else set(list_project_files())
    if slug not in existing:
        return slug
    laufnummer = 2
    while f"{slug}-{laufnummer}" in existing:
        laufnummer += 1
    return f"{slug}-{laufnummer}"


def save_project(project: PVProject, path: Path | None = None) -> Path:
    """Speichert ein Projekt (Standard: data/projects/<id>.yaml).

    `path` kann explizit uebergeben werden, wenn eine bereits geoeffnete
    Datei ueberschrieben werden soll - id und Dateiname koennen (z.B. durch
    manuelle YAML-Bearbeitung) auseinanderlaufen, und dann soll die
    tatsaechlich geoeffnete Datei aktualisiert werden, nicht versehentlich
    eine zweite entstehen.
    """
    target = path if path is not None else PROJECTS_DIR / f"{project.id}.yaml"
    save_project_yaml(project, target)
    _run_valuation_cached.clear()
    _run_sensitivity_cached.clear()
    return target


def duplicate_project(project_id: str) -> PVProject | None:
    """Legt eine Kopie eines Projekts mit neuer ID und '(Kopie)'-Namen an."""
    original = get_project(project_id)
    if original is None:
        return None
    kopie = original.model_copy(deep=True)
    kopie.name = f"{original.name} (Kopie)"
    kopie.id = make_project_id(kopie.name)
    save_project(kopie)
    return kopie


def delete_project(project_id: str) -> bool:
    path = PROJECTS_DIR / f"{project_id}.yaml"
    if not path.exists():
        return False
    path.unlink()
    _run_valuation_cached.clear()
    _run_sensitivity_cached.clear()
    return True


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def cashflow_to_excel(result: ValuationResult) -> bytes:
    """Exportiert die vollstaendige Cashflow-Zeitreihe eines Projekts als
    Excel-Arbeitsmappe (ein Blatt Cashflow, ein Blatt KPIs)."""
    kpis = result.kpis
    kpi_df = pd.DataFrame(
        [
            ("EK-Rendite (IRR)", kpis.equity_irr),
            ("NPV bei 5 %", kpis.npv_eur),
            ("Payback (Jahre)", kpis.payback_jahre),
            ("Investitionsvolumen (€)", kpis.capex_total_eur),
            ("Eigenkapitaleinsatz (€)", kpis.eigenkapital_eur),
            ("Min. DSCR", kpis.dscr_min),
        ],
        columns=["Kennzahl", "Wert"],
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        result.cashflow.data.to_excel(writer, sheet_name="Cashflow", index=False)
        kpi_df.to_excel(writer, sheet_name="KPIs", index=False)
    buffer.seek(0)
    return buffer.getvalue()
