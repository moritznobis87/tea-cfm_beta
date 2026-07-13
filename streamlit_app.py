"""
TEA PV-Projektbewertung - Einstiegspunkt.

Bewusst duenn gehalten: Seitenkonfiguration, Theme, Kopfzeile und
Navigation. Die eigentlichen Seiten leben in app/views/, wieder-
verwendbare Bausteine in app/components/, Datenzugriff und Caching in
app/services.py, die Fachlogik in engine/.
"""

from __future__ import annotations

import streamlit as st

from app.config import APP_TITLE, LOGO_PATH
from app.theme import apply_theme

st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "☀️",
)
apply_theme()

# Imports der Views erst NACH set_page_config - Streamlit verlangt, dass
# set_page_config der allererste Streamlit-Befehl des Skripts ist, und die
# Views fuehren beim Import bereits Streamlit-Code aus (Caching-Dekoratoren).
from app.components.sidebar import render_import_export  # noqa: E402
from app.views.assumptions import render_assumptions  # noqa: E402
from app.views.new_project import render_new_project  # noqa: E402
from app.views.overview import render_overview  # noqa: E402

# --- Kopfzeile ---------------------------------------------------------------
col_logo, col_title = st.columns([1, 8], vertical_alignment="center")
if LOGO_PATH.exists():
    col_logo.image(str(LOGO_PATH), width=84)
col_title.title(APP_TITLE)
st.markdown('<div class="app-header-rule"></div>', unsafe_allow_html=True)

# --- Navigation ----------------------------------------------------------------
nav = st.sidebar.radio(
    "Navigation",
    ["Portfolio", "Neues Projekt", "Globale Annahmen"],
    key="nav",
)
render_import_export()

if nav == "Portfolio":
    render_overview()
elif nav == "Neues Projekt":
    render_new_project()
else:
    render_assumptions()
