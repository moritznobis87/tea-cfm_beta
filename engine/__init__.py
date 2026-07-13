"""
Bewertungs-Engine: reine Fachlogik ohne UI-Abhaengigkeiten.

Oeffentliche API dieses Pakets - die App (und Tests) importieren
ausschliesslich von hier, nicht aus den Untermodulen.
"""

from .cashflow import CashflowTimeseries
from .models import (
    AnlagenTyp,
    CapexBreakdown,
    EffectiveAssumptions,
    GlobalAssumptions,
    KPIs,
    MarktpreisSzenario,
    NegativeStundenModus,
    OpexItem,
    PVProject,
    TaxModus,
    TilgungsArt,
)
from .pipeline import ValuationResult, resolve_assumptions, run_valuation
from .sensitivity import run_eag_sensitivity

__all__ = [
    "AnlagenTyp",
    "CapexBreakdown",
    "CashflowTimeseries",
    "EffectiveAssumptions",
    "GlobalAssumptions",
    "KPIs",
    "MarktpreisSzenario",
    "NegativeStundenModus",
    "OpexItem",
    "PVProject",
    "TaxModus",
    "TilgungsArt",
    "ValuationResult",
    "resolve_assumptions",
    "run_valuation",
    "run_eag_sensitivity",
]
