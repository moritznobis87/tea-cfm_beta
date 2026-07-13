"""
Alle Plotly-Diagramme der App als reine Builder-Funktionen
(DataFrame rein, Figure raus - kein Streamlit-Import).

Vorteile dieser Trennung:
- Views bleiben schlank und lesbar,
- jedes Diagramm ist isoliert testbar,
- Farb- und Formatentscheidungen kommen zentral aus app.theme.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from app.formatting import fmt_pct
from app.theme import Colors

_EUR_HOVER = "%{y:,.0f} €"


def _signed_colors(values: pd.Series) -> list[str]:
    """Gruen fuer Zufluesse, Rot fuer Abfluesse - einheitlich in allen
    Cashflow-Darstellungen."""
    return [Colors.POSITIVE if v >= 0 else Colors.NEGATIVE for v in values]


def revenue_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        x=df["jahr"], y=df["erloes_eur"], name="Umsatzerlöse",
        marker_color=Colors.POSITIVE, hovertemplate=_EUR_HOVER + "<extra></extra>",
    )
    fig.update_layout(
        yaxis_title="€", xaxis_title="Betriebsjahr", height=360, showlegend=False
    )
    return fig


def opex_stacked_chart(df: pd.DataFrame, opex_posten: list[str]) -> go.Figure:
    """Betriebskosten als gestapelte Balken - eine Position je
    Legendeneintrag (per Klick ein-/ausblendbar), Gemeindeabgabe und
    Direktvermarktung als eigene produktionsbasierte Positionen."""
    fig = go.Figure()
    for i, posten in enumerate(opex_posten):
        fig.add_bar(
            x=df["jahr"], y=df[posten], name=posten,
            marker_color=Colors.OPEX_SCALE[i % len(Colors.OPEX_SCALE)],
            hovertemplate=_EUR_HOVER + "<extra>%{fullData.name}</extra>",
        )
    fig.add_bar(
        x=df["jahr"], y=df["gemeindeabgabe_eur"], name="Gemeindeabgabe",
        marker_color="#7B241C",
        hovertemplate=_EUR_HOVER + "<extra>Gemeindeabgabe</extra>",
    )
    fig.add_bar(
        x=df["jahr"], y=df["direktvermarktungskosten_eur"], name="Direktvermarktung",
        marker_color="#4D5656",
        hovertemplate=_EUR_HOVER + "<extra>Direktvermarktung</extra>",
    )
    fig.update_layout(
        barmode="stack", yaxis_title="€", xaxis_title="Betriebsjahr", height=420
    )
    return fig


def operating_cashflow_chart(df: pd.DataFrame) -> go.Figure:
    """Vereinfachter operativer Cashflow (Erloese - Betriebskosten), vor
    Zinsen und Steuer."""
    werte = df["erloes_eur"] - df["opex_gesamt_eur"]
    fig = go.Figure()
    fig.add_bar(
        x=df["jahr"], y=werte, name="Operativer Cashflow",
        marker_color=_signed_colors(werte),
        hovertemplate=_EUR_HOVER + "<extra></extra>",
    )
    fig.update_layout(
        yaxis_title="€", xaxis_title="Betriebsjahr", height=360, showlegend=False
    )
    return fig


def financing_cashflow_chart(df: pd.DataFrame) -> go.Figure:
    """Kreditaufnahme (Jahr 0) vs. laufende Tilgung. Zinsen sind bewusst
    nicht enthalten - sie sind Teil des operativen Cashflows."""
    kreditaufnahme = df["cf_finanzierung_eur"] + df["tilgung_eur"]
    fig = go.Figure()
    fig.add_bar(
        x=df["jahr"], y=kreditaufnahme, name="Kreditaufnahme",
        marker_color=Colors.POSITIVE, hovertemplate=_EUR_HOVER + "<extra></extra>",
    )
    fig.add_bar(
        x=df["jahr"], y=-df["tilgung_eur"], name="Tilgung",
        marker_color=Colors.NEUTRAL, hovertemplate=_EUR_HOVER + "<extra></extra>",
    )
    fig.update_layout(
        barmode="relative", yaxis_title="€", xaxis_title="Jahr", height=420
    )
    return fig


def total_cashflow_chart(df: pd.DataFrame) -> go.Figure:
    """Gesamt-Cashflow je Jahr (Balken) plus kumulierte Kurve (Linie,
    rechte Achse)."""
    fig = go.Figure()
    fig.add_bar(
        x=df["jahr"], y=df["cf_gesamt_eur"], name="Cashflow (Jahr)",
        marker_color=_signed_colors(df["cf_gesamt_eur"]),
        hovertemplate=_EUR_HOVER + "<extra></extra>",
    )
    fig.add_scatter(
        x=df["jahr"], y=df["cf_kumuliert_eur"], name="Kumulierter Cashflow",
        mode="lines+markers", line=dict(color=Colors.INK, width=2), yaxis="y2",
        hovertemplate=_EUR_HOVER + "<extra>kumuliert</extra>",
    )
    fig.update_layout(
        yaxis=dict(title="Cashflow (Jahr) in €"),
        yaxis2=dict(
            title="Kumuliert in €", overlaying="y", side="right", showgrid=False
        ),
        xaxis_title="Jahr",
        height=440,
    )
    return fig


def dscr_chart(dscr_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        x=dscr_df["jahr"], y=dscr_df["dscr"], name="DSCR",
        marker_color=[
            Colors.NEGATIVE if v < 1.0 else Colors.POSITIVE for v in dscr_df["dscr"]
        ],
        hovertemplate="%{y:,.2f}x<extra></extra>",
    )
    fig.add_hline(
        y=1.0, line_dash="dot", line_color="gray",
        annotation_text="DSCR = 1,0x (Deckungsgrenze)",
    )
    fig.update_layout(
        xaxis_title="Betriebsjahr", yaxis_title="DSCR (x)",
        height=420, showlegend=False,
    )
    return fig


def npv_curve_chart(npv_df: pd.DataFrame, equity_irr: float | None) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(
        x=npv_df["diskontsatz_pct"] * 100, y=npv_df["npv_eur"],
        mode="lines+markers", name="NPV", line=dict(color=Colors.INK),
        hovertemplate="Diskontsatz %{x:,.1f} %: %{y:,.0f} €<extra></extra>",
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    if equity_irr is not None:
        # IRR ist per Definition die Nullstelle der NPV-Kurve.
        fig.add_vline(
            x=equity_irr * 100, line_dash="dot", line_color=Colors.POSITIVE,
            annotation_text="IRR",
        )
    fig.update_layout(
        xaxis_title="Diskontsatz (%)", yaxis_title="NPV (€)", height=420
    )
    return fig


def eag_sensitivity_chart(sens_df: pd.DataFrame) -> go.Figure:
    """IRR ueber dem variierten EAG-Zuschlagswert (±10 %/±5 %/Basis).

    Defensiv: einzelne Varianten koennen eine nicht berechenbare IRR
    (None) liefern, wenn der Cashflow keinen Vorzeichenwechsel mehr hat
    (z.B. durchgehend negativ bei einem -10%-Downside).
    """
    irr_werte = pd.to_numeric(sens_df["equity_irr"], errors="coerce")
    irr_pct = (irr_werte * 100).tolist()
    eag_werte = sens_df["eag_zuschlagswert_ct_kwh"].astype(float).tolist()
    varianten = sens_df["variante"].astype(str).tolist()
    beschriftungen = [
        fmt_pct(v) if v is not None and pd.notna(v) else "n/a"
        for v in sens_df["equity_irr"]
    ]

    fig = go.Figure()
    fig.add_bar(
        x=eag_werte,
        y=irr_pct,
        width=0.15,
        marker_color=[
            Colors.POSITIVE if v == "Basis" else Colors.NEUTRAL for v in varianten
        ],
        customdata=varianten,
        hovertemplate="%{customdata}: %{x:,.2f} ct/kWh → %{text}<extra></extra>",
        text=beschriftungen,
        # Sichtbare Beschriftung kommt ausschliesslich ueber die
        # Annotationen unten - "textposition=outside" wuerde bei negativer
        # IRR unterhalb des Balkens landen (Plotly richtet sich nach dem
        # Vorzeichen); yshift ist dagegen ein reiner Pixel-Offset und sitzt
        # immer oberhalb der Balkenspitze.
        textposition="none",
    )
    for x_wert, y_wert, text in zip(eag_werte, irr_pct, beschriftungen, strict=True):
        fig.add_annotation(
            x=x_wert, y=y_wert if pd.notna(y_wert) else 0,
            text=text, showarrow=False, yshift=14,
            font=dict(size=12, color=Colors.INK),
        )
    fig.update_layout(
        xaxis=dict(
            title="EAG-Zuschlagswert (ct/kWh)",
            tickmode="array", tickvals=eag_werte, tickformat=".2f",
        ),
        yaxis=dict(title="EK-Rendite", ticksuffix=" %"),
        height=380,
        showlegend=False,
    )
    return fig
