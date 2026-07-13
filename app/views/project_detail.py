"""
Projekt-Dashboard: KPI-Leiste, Cashflow-/DSCR-/NPV-/Sensitivitaets-Tabs,
Bearbeiten, Duplizieren, Loeschen und Excel-Export eines Einzelprojekts.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app import services
from app.components import charts
from app.components.kpi import render_kpi_row
from app.components.project_form import render_project_form
from app.config import MONATE_KURZ, STATE_DELETE_CANDIDATE, STATE_SELECTED_PROJECT
from app.formatting import fmt_ct_kwh, fmt_dscr, fmt_eur, fmt_kwp, fmt_number, fmt_pct
from engine import AnlagenTyp, GlobalAssumptions, NegativeStundenModus, PVProject
from engine.kpis import npv_at

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _typ_label(project: PVProject) -> str:
    return "Agri-PV" if project.anlagentyp == AnlagenTyp.AGRI_PV else "Konventionell"


def render_project_dashboard(
    project: PVProject, global_assumptions: GlobalAssumptions, file_path: Path
) -> None:
    result = services.get_valuation(file_path.stem)
    if result is None:
        st.error("Projekt konnte nicht geladen werden.")
        return
    df = result.cashflow.data
    kpis = result.kpis

    # --- Kopfzeile ---------------------------------------------------------
    st.markdown(f"### {project.name}")
    st.caption(
        f"{_typ_label(project)} · {fmt_kwp(project.nennleistung_kwp)} · "
        f"Inbetriebnahme {MONATE_KURZ[project.inbetriebnahme_monat - 1]} "
        f"{project.inbetriebnahme_jahr} · effektiver EAG-Zuschlag "
        f"{fmt_ct_kwh(project.eag_zuschlagswert_effektiv_ct_kwh)}"
    )

    # --- Aktionen ----------------------------------------------------------
    with st.expander("✏️ Projekt bearbeiten"):
        updated = render_project_form(existing=project, form_key=f"edit_{project.id}")
        if updated is not None:
            # Bewusst file_path statt project.id verwenden: id und Dateiname
            # koennen (z.B. durch manuelle YAML-Bearbeitung) auseinander-
            # laufen - wir wollen immer die tatsaechlich geoeffnete Datei
            # ueberschreiben, nicht versehentlich eine zweite erzeugen.
            services.save_project(updated, file_path)
            st.success("Projekt aktualisiert.")
            st.rerun()

    _, col_dup, col_del, col_export = st.columns([3, 1, 1, 2])
    with col_dup:
        if st.button("Duplizieren", key=f"dup_{project.id}", width="stretch"):
            kopie = services.duplicate_project(file_path.stem)
            if kopie is not None:
                st.session_state[STATE_SELECTED_PROJECT] = kopie.id
                st.rerun()
    with col_del:
        if st.button("Löschen", key=f"del_{project.id}", width="stretch"):
            st.session_state[STATE_DELETE_CANDIDATE] = file_path.stem
    with col_export:
        st.download_button(
            "⬇️ Cashflow als Excel",
            data=services.cashflow_to_excel(result),
            file_name=f"{project.id}_cashflow.xlsx",
            mime=_XLSX_MIME,
            width="stretch",
        )

    # Loeschen nur nach expliziter Bestaetigung - das ist nicht rueckholbar.
    if st.session_state.get(STATE_DELETE_CANDIDATE) == file_path.stem:
        st.warning(f"Projekt „{project.name}“ endgültig löschen?")
        col_ja, col_nein, _ = st.columns([1, 1, 4])
        if col_ja.button("Ja, löschen", type="primary", key=f"del_ok_{project.id}"):
            services.delete_project(file_path.stem)
            st.session_state.pop(STATE_DELETE_CANDIDATE, None)
            st.session_state.pop(STATE_SELECTED_PROJECT, None)
            st.rerun()
        if col_nein.button("Abbrechen", key=f"del_no_{project.id}"):
            st.session_state.pop(STATE_DELETE_CANDIDATE, None)
            st.rerun()

    # --- KPI-Leiste ----------------------------------------------------------
    # NPV-Diskontsatz frei waehlbar (gilt fuer die NPV-Kachel). Der Wert
    # wird exakt per XNPV berechnet - Interpolation zwischen Kurvenpunkten
    # ist nicht noetig. Die Einstellung gilt app-weit (Session-State), damit
    # Projekte zum selben Satz verglichen werden.
    st.session_state.setdefault("npv_diskontsatz_pct", 8.0)
    col_rate, _ = st.columns([1.3, 5])
    npv_satz_pct = col_rate.number_input(
        "NPV-Diskontsatz (%)",
        min_value=0.0,
        max_value=10.0,
        step=0.25,
        key="npv_diskontsatz_pct",
        help="Diskontsatz für die NPV-Kachel (0–10 %). Der Wert wird exakt "
             "aus der Cashflow-Zeitreihe berechnet (XNPV), auch zwischen den "
             "Stützstellen der NPV-Kurve.",
    )
    npv_wert = npv_at(result.cashflow, npv_satz_pct / 100)

    render_kpi_row(
        [
            ("EK-Rendite (IRR)", fmt_pct(kpis.equity_irr)),
            (f"NPV bei {fmt_number(npv_satz_pct, 2)} %", fmt_eur(npv_wert)),
            ("Min. DSCR (Kreditlaufzeit)", fmt_dscr(kpis.dscr_min)),
            ("Investitionsvolumen", fmt_eur(kpis.capex_total_eur)),
            ("Eigenkapitaleinsatz", fmt_eur(kpis.eigenkapital_eur)),
        ],
        group="projekt",
    )

    if kpis.dscr_min is not None and kpis.dscr_min < 1.0:
        st.warning(
            f"⚠️ Der minimale DSCR liegt bei {fmt_dscr(kpis.dscr_min)} und damit "
            f"unter 1,0x: Der operative Cashflow deckt den Schuldendienst in "
            f"mindestens einem Jahr der Kreditlaufzeit nicht vollständig. Mit den "
            f"aktuellen Annahmen müsste während der Fremdfinanzierungsphase "
            f"zusätzliches Eigenkapital nachgeschossen werden. Details siehe Tab "
            f"DSCR – meist hilft eine niedrigere Fremdkapitalquote oder eine "
            f"längere Kreditlaufzeit."
        )

    tab_cf, tab_dscr, tab_npv, tab_sens, tab_annahmen = st.tabs(
        [
            "Cashflow", "DSCR", "NPV-Sensitivität (Diskontsatz)",
            "Sensitivität EAG-Zuschlag", "Annahmen",
        ]
    )

    with tab_cf:
        _render_cashflow_tab(result, df)
    with tab_dscr:
        _render_dscr_tab(df)
    with tab_npv:
        _render_npv_tab(result, kpis)
    with tab_sens:
        _render_sensitivity_tab(file_path.stem)
    with tab_annahmen:
        _render_assumptions_tab(result)


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------


def _render_cashflow_tab(result, df) -> None:
    st.markdown("**Umsatzerlöse**")
    st.plotly_chart(charts.revenue_chart(df), width="stretch")

    st.markdown("**Betriebskosten (nach Position)**")
    st.caption(
        "Klicken Sie auf einzelne Positionen in der Legende, um sie "
        "ein-/auszublenden."
    )
    st.plotly_chart(
        charts.opex_stacked_chart(df, result.cashflow.opex_posten), width="stretch"
    )

    st.markdown("**Operativer Cashflow (Umsatzerlöse − Betriebskosten)**")
    st.caption(
        "Vereinfachte Betrachtung vor Zinsen und Steuer. Die für "
        "EK-Rendite/NPV massgebliche Cashflow-Definition (inkl. Zinsen und "
        "Steuer) finden Sie in der Tabelle unten."
    )
    st.plotly_chart(charts.operating_cashflow_chart(df), width="stretch")

    st.markdown("**Cashflow aus Finanzierungstätigkeit**")
    st.caption(
        "Aufgeschlüsselt nach Kreditaufnahme (Jahr 0) und Tilgung (laufend). "
        "Zinsen sind hier nicht enthalten - sie fliessen bereits in den "
        "operativen Cashflow ein. Die Investitionsauszahlung (CAPEX) ist "
        "bewusst nicht dargestellt, da dafür auch die Eigenkapitaleinlage "
        "gezeigt werden müsste."
    )
    st.plotly_chart(charts.financing_cashflow_chart(df), width="stretch")

    st.markdown("**Gesamt-Cashflow**")
    st.caption(
        "Summe aus operativem, Investitions- und Finanzierungs-Cashflow je "
        "Jahr (Balken) sowie kumuliert über die Zeit (Linie, rechte Achse)."
    )
    st.plotly_chart(charts.total_cashflow_chart(df), width="stretch")

    with st.expander("Detailtabelle (Erlöse, Betriebskosten, Zinsen, Steuer)"):
        detail_df = df[
            [
                "jahr", "marktwert_real_ct_kwh", "marktwert_nominal_ct_kwh",
                "verguetungssatz_ct_kwh", "erloes_eur", "opex_gesamt_eur",
                "gemeindeabgabe_eur", "direktvermarktungskosten_eur",
                "zinsen_eur", "tilgung_eur", "afa_eur",
                "steuerliches_ergebnis_vor_verlustvortrag_eur",
                "verlustvortrag_genutzt_eur", "verlustvortrag_bestand_eur",
                "steuerliches_ergebnis_eur", "steuer_eur",
            ]
        ].copy()
        for col in detail_df.columns:
            if col == "jahr":
                continue
            nachkommastellen = 3 if "ct_kwh" in col else 0
            detail_df[col] = detail_df[col].round(nachkommastellen)
        detail_df.columns = [
            "Jahr", "Marktwert real (ct/kWh)", "Marktwert nominal (ct/kWh)",
            "Vergütungssatz (ct/kWh)", "Erlöse (€)", "Betriebskosten gesamt (€)",
            "davon Gemeindeabgabe (€)", "davon Direktvermarktungskosten (€)",
            "Zinsen (€)", "Tilgung (€)", "AfA (€)",
            "Steuerl. Ergebnis vor Verlustvortrag (€)",
            "Verlustvortrag genutzt (€)", "Verlustvortrag-Bestand Ende Jahr (€)",
            "Steuerpflichtiges Ergebnis (€)", "Steuer (€)",
        ]
        st.dataframe(detail_df, width="stretch", hide_index=True)

    cf_spalten = [
        "cf_operativ_eur", "cf_invest_eur", "cf_finanzierung_eur",
        "cf_gesamt_eur", "cf_kumuliert_eur",
    ]
    display_df = df[["jahr", *cf_spalten]].copy()
    for col in cf_spalten:
        display_df[col] = display_df[col].round(0)
    display_df.columns = [
        "Jahr", "Operativ (€)", "Investition (€)", "Finanzierung (€)",
        "Gesamt (€)", "Kumuliert (€)",
    ]
    st.dataframe(display_df, width="stretch", hide_index=True)


def _render_dscr_tab(df) -> None:
    dscr_df = df.dropna(subset=["dscr"]).copy()
    if dscr_df.empty:
        st.info("Kein DSCR verfügbar (keine Fremdfinanzierung in diesem Projekt).")
        return
    st.plotly_chart(charts.dscr_chart(dscr_df), width="stretch")

    dscr_display = dscr_df[["jahr", "dscr"]].copy()
    dscr_display["dscr"] = dscr_display["dscr"].round(2)
    dscr_display.columns = ["Jahr", "DSCR (x)"]
    st.dataframe(dscr_display, width="stretch", hide_index=True)


def _render_npv_tab(result, kpis) -> None:
    npv_df = result.npv_curve.copy()
    st.plotly_chart(
        charts.npv_curve_chart(npv_df, kpis.equity_irr), width="stretch"
    )

    npv_display = npv_df.copy()
    npv_display["diskontsatz_pct"] = (npv_display["diskontsatz_pct"] * 100).round(1)
    npv_display["npv_eur"] = npv_display["npv_eur"].round(0)
    npv_display.columns = ["Diskontsatz (%)", "NPV (€)"]
    st.dataframe(npv_display, width="stretch", hide_index=True)


def _render_sensitivity_tab(project_id: str) -> None:
    sens_df = services.get_eag_sensitivity(project_id)
    if sens_df is None or sens_df.empty:
        st.info("Keine Sensitivitätsdaten verfügbar.")
        return
    st.plotly_chart(charts.eag_sensitivity_chart(sens_df), width="stretch")

    sens_display = sens_df.copy()
    sens_display["eag_zuschlagswert_ct_kwh"] = sens_display[
        "eag_zuschlagswert_ct_kwh"
    ].round(3)
    sens_display["equity_irr"] = sens_display["equity_irr"].apply(fmt_pct)
    sens_display["npv_eur"] = sens_display["npv_eur"].round(0)
    sens_display = sens_display[
        ["variante", "eag_zuschlagswert_ct_kwh", "equity_irr", "npv_eur"]
    ]
    sens_display.columns = [
        "Variante", "EAG-Zuschlag (ct/kWh)", "EK-Rendite", "NPV (€)",
    ]
    st.dataframe(sens_display, width="stretch", hide_index=True)


def _render_assumptions_tab(result) -> None:
    """Transparenz-Tab: der vollstaendig aufgeloeste Parametersatz, mit dem
    dieses Projekt tatsaechlich gerechnet wurde (Projektmaske + Globale
    Annahmen nach dem Merge)."""
    ea = result.effective_assumptions
    st.caption(
        "Vollständig aufgelöster Parametersatz dieser Berechnung "
        "(Projektmaske zusammengeführt mit den Globalen Annahmen). "
        f"Marktpreisszenario: **{ea.marktpreisszenario_name}**."
    )
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("**Anlage & Produktion**")
        st.markdown(
            f"- Leistung: {fmt_kwp(ea.nennleistung_kwp)}\n"
            f"- Vollbenutzungsstunden: {ea.vollbenutzungsstunden_kwh_kwp:.0f} kWh/kWp\n"
            f"- Degradation: {fmt_pct(ea.degradation_pct_pa)} p.a.\n"
            f"- Sicherheitsabschlag: {fmt_pct(ea.sicherheitsabschlag_pct)}\n"
            f"- Betrachtungsdauer: {ea.betriebsdauer_jahre} Jahre"
        )
    with col_b:
        st.markdown("**Erlöse & Förderung**")
        st.markdown(
            f"- EAG-Zuschlag (effektiv): {fmt_ct_kwh(ea.eag_zuschlagswert_effektiv_ct_kwh)}\n"
            f"- Förderdauer: {ea.eag_foerderdauer_jahre} Jahre\n"
            f"- Inflation Marktwerte: {fmt_pct(ea.marktpreis_inflation_pct_pa)} p.a. "
            f"ab {ea.marktpreis_inflation_basisjahr}\n"
            f"- Gewichtung neg. Stunden: {fmt_pct(ea.negative_stunden_gewichtung_pct, 0)}\n"
            f"- Negativstunden-Modus: "
            + (
                "Abregelung (Erlöse entfallen)"
                if ea.negative_stunden_modus == NegativeStundenModus.ABREGELUNG
                else "Rückfall auf Jahresmarktwert"
            )
        )
    with col_c:
        st.markdown("**Finanzierung & Steuer**")
        st.markdown(
            f"- Eigenkapitalquote: {fmt_pct(ea.eigenkapitalquote_pct, 0)}\n"
            f"- FK-Zins: {fmt_pct(ea.fremdkapitalzins_pct)}\n"
            f"- Kreditlaufzeit: {ea.kreditlaufzeit_jahre} Jahre "
            f"({ea.tilgungsart.value})\n"
            f"- Tilgungsfreies Anlaufjahr: "
            f"{'Ja' if ea.tilgungsfreies_anlaufjahr else 'Nein'}\n"
            f"- Steuermodus: {ea.tax_modus.value}\n"
            f"- Steuersatz: {fmt_pct(ea.steuersatz_pct, 0)}"
        )
