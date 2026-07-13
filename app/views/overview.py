"""
Portfolioseite: aggregierte Kennzahlen, sortierbare Vergleichstabelle
ueber alle Projekte, Projektkacheln und darunter das Dashboard des
ausgewaehlten Projekts.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app import services
from app.config import STATE_SELECTED_PROJECT
from app.formatting import fmt_eur, fmt_kwp, fmt_number, fmt_pct
from app.views.project_detail import render_project_dashboard
from engine import AnlagenTyp
from engine.io_yaml import load_project_yaml


def render_overview() -> None:
    projects = services.list_project_files()
    if not projects:
        st.info("Noch keine Projekte angelegt. Starten Sie mit „Neues Projekt“.")
        return

    global_assumptions = services.get_global_assumptions()

    # Alle Projekte einmal bewerten (gecacht auf Datei-mtimes, siehe
    # services) - Grundlage fuer Portfolio-KPIs, Tabelle und Kacheln.
    zeilen = []
    for pid, path in projects.items():
        project = load_project_yaml(path)
        result = services.get_valuation(pid)
        zeilen.append(
            {
                "id": pid,
                "projekt": project,
                "kpis": result.kpis,
            }
        )

    # --- Portfolio-KPIs ------------------------------------------------------
    gesamt_kwp = sum(z["projekt"].nennleistung_kwp for z in zeilen)
    gesamt_capex = sum(z["kpis"].capex_total_eur for z in zeilen)
    irr_werte = [z["kpis"].equity_irr for z in zeilen if z["kpis"].equity_irr is not None]
    mittlere_irr = sum(irr_werte) / len(irr_werte) if irr_werte else None

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Projekte", f"{len(zeilen)}")
    col2.metric("Portfolio-Leistung", f"{fmt_number(gesamt_kwp / 1000, 1)} MWp")
    col3.metric("Investitionsvolumen gesamt", fmt_eur(gesamt_capex))
    col4.metric("Ø EK-Rendite", fmt_pct(mittlere_irr))

    # --- Vergleichstabelle ---------------------------------------------------
    with st.expander("Projektvergleich (Tabelle)", expanded=False):
        vergleich = pd.DataFrame(
            [
                {
                    "Projekt": z["projekt"].name,
                    "Typ": "Agri-PV"
                    if z["projekt"].anlagentyp == AnlagenTyp.AGRI_PV
                    else "Konventionell",
                    "Leistung (kWp)": round(z["projekt"].nennleistung_kwp),
                    "EK-Rendite (%)": round(z["kpis"].equity_irr * 100, 2)
                    if z["kpis"].equity_irr is not None
                    else None,
                    "NPV bei 5 % (€)": round(z["kpis"].npv_eur),
                    "Invest (€)": round(z["kpis"].capex_total_eur),
                    "Invest (€/kWp)": round(
                        z["kpis"].capex_total_eur / z["projekt"].nennleistung_kwp
                    )
                    if z["projekt"].nennleistung_kwp
                    else None,
                    "Min. DSCR (x)": round(z["kpis"].dscr_min, 2)
                    if z["kpis"].dscr_min is not None
                    else None,
                    "Payback (Jahr)": z["kpis"].payback_jahre,
                }
                for z in zeilen
            ]
        )
        st.dataframe(
            vergleich.sort_values("EK-Rendite (%)", ascending=False),
            width="stretch",
            hide_index=True,
        )

    # --- Projektkacheln ------------------------------------------------------
    st.subheader("Projekte")
    selected = st.session_state.get(STATE_SELECTED_PROJECT)
    cols = st.columns(min(len(zeilen), 4))
    for i, z in enumerate(zeilen):
        project = z["projekt"]
        kpis = z["kpis"]
        typ_label = (
            "Agri-PV" if project.anlagentyp == AnlagenTyp.AGRI_PV else "Konventionell"
        )
        with cols[i % len(cols)]:
            st.markdown(
                f"""<div class="project-card">
                <span class="card-title">{project.name}</span><br/>
                <span class="card-sub">{typ_label} · {fmt_kwp(project.nennleistung_kwp)}</span><br/>
                <span class="card-kpi">{fmt_pct(kpis.equity_irr)}</span>
                <span class="card-kpi-label"> EK-Rendite</span>
                </div>""",
                unsafe_allow_html=True,
            )
            if st.button("Öffnen", key=f"open_{z['id']}", width="stretch"):
                st.session_state[STATE_SELECTED_PROJECT] = z["id"]
                st.rerun()

    if not selected or selected not in projects:
        return

    st.divider()
    project = load_project_yaml(projects[selected])
    render_project_dashboard(project, global_assumptions, projects[selected])
