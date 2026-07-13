"""
Visuelles Fundament der App: Design-Tokens, CSS und ein zentrales
Plotly-Template.

Prinzip: Jede Farbe, jeder Abstand und jedes Diagramm bezieht seine
Gestaltung aus DIESEM Modul. Views und Komponenten enthalten keine
Hex-Codes - dadurch bleibt das Erscheinungsbild ueber die gesamte App
konsistent und laesst sich an einer Stelle umstellen (z.B. bei einem
Corporate-Design-Wechsel).
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ---------------------------------------------------------------------------
# Design-Tokens
# ---------------------------------------------------------------------------


class Colors:
    """Farbpalette: Trianel-Rot als Markenakzent auf ruhigem Tannengruen-Ink."""

    BRAND = "#BE172B"          # Trianel-Rot - Akzent, Primary-Buttons, Marker
    INK = "#163832"            # Tiefes Tannengruen - Ueberschriften, Linien
    MUTED = "#5B6B66"          # Sekundaertext
    LINE = "#E3E8E6"           # Rahmen, Trennlinien
    WASH = "#F7F9F8"           # Kartenhintergrund
    PAPER = "#FFFFFF"

    POSITIVE = "#2E7D32"       # Zufluesse, Erloese, "im gruenen Bereich"
    NEGATIVE = "#C0392B"       # Abfluesse, Unterdeckung
    NEUTRAL = "#8AA6A0"        # Sekundaere Serien (z.B. Tilgung, Varianten)

    #: Gestufte Warmtoene fuer gestapelte Kostenpositionen.
    OPEX_SCALE = [
        "#C0392B", "#E67E22", "#D68910", "#B9770E", "#A04000",
        "#873600", "#6E2C00", "#943126",
    ]


# ---------------------------------------------------------------------------
# Plotly-Template (einmal registrieren, ueberall nutzen)
# ---------------------------------------------------------------------------

_TEMPLATE_NAME = "tea"


def _register_plotly_template() -> None:
    if _TEMPLATE_NAME in pio.templates:
        return
    pio.templates[_TEMPLATE_NAME] = go.layout.Template(
        layout=go.Layout(
            font=dict(family="Inter, sans-serif", color=Colors.INK, size=13),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            # Deutsche Zahlendarstellung in Achsen und Hovern:
            # 1. Zeichen = Dezimaltrenner, 2. Zeichen = Tausendertrenner.
            separators=",.",
            colorway=[Colors.INK, Colors.BRAND, Colors.NEUTRAL, Colors.POSITIVE],
            margin=dict(t=24, b=24, l=8, r=8),
            hoverlabel=dict(
                bgcolor=Colors.PAPER,
                bordercolor=Colors.LINE,
                font=dict(family="Inter, sans-serif", color=Colors.INK),
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            xaxis=dict(
                gridcolor=Colors.LINE, zerolinecolor=Colors.LINE, linecolor=Colors.LINE
            ),
            yaxis=dict(
                gridcolor=Colors.LINE, zerolinecolor=Colors.LINE, linecolor=Colors.LINE
            ),
        )
    )
    pio.templates.default = f"plotly_white+{_TEMPLATE_NAME}"


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_CSS = f"""
<style>
    .block-container {{ padding-top: 1.6rem; max-width: 1240px; }}

    /* --- KPI-Kacheln --------------------------------------------------- */
    div[data-testid="stMetric"] {{
        background: {Colors.WASH};
        border: 1px solid {Colors.LINE};
        border-left: 3px solid {Colors.BRAND};
        border-radius: 10px;
        padding: 14px 18px 10px 18px;
    }}
    div[data-testid="stMetric"] label {{ color: {Colors.MUTED}; }}

    /* --- Projektkarten -------------------------------------------------- */
    .project-card {{
        border: 1px solid {Colors.LINE};
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 10px;
        background: {Colors.PAPER};
        transition: box-shadow 120ms ease, border-color 120ms ease;
    }}
    .project-card:hover {{
        border-color: {Colors.NEUTRAL};
        box-shadow: 0 2px 10px rgba(22, 56, 50, 0.08);
    }}
    .project-card .card-title {{ font-weight: 600; color: {Colors.INK}; }}
    .project-card .card-sub {{ color: {Colors.MUTED}; font-size: 0.86em; }}
    .project-card .card-kpi {{ font-size: 1.45em; font-weight: 650; color: {Colors.INK}; }}
    .project-card .card-kpi-label {{ color: {Colors.MUTED}; font-size: 0.86em; }}

    /* --- Typografie & Struktur ------------------------------------------ */
    h1, h2, h3 {{ color: {Colors.INK}; letter-spacing: -0.01em; }}
    .stTabs [data-baseweb="tab"] {{ font-weight: 500; }}
    .app-header-rule {{
        height: 3px;
        background: linear-gradient(90deg, {Colors.BRAND} 0, {Colors.BRAND} 96px,
                                    {Colors.LINE} 96px, {Colors.LINE} 100%);
        border: none; border-radius: 2px;
        margin: 0.1rem 0 1.1rem 0;
    }}
    section[data-testid="stSidebar"] .stRadio label {{ font-weight: 500; }}
</style>
"""


def apply_theme() -> None:
    """Registriert das Plotly-Template und injiziert das App-CSS.

    Muss einmal pro Rerun frueh aufgerufen werden (macht der Entry-Point).
    """
    _register_plotly_template()
    st.markdown(_CSS, unsafe_allow_html=True)
