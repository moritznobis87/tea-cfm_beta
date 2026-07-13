"""
UI-Smoke-Tests mit Streamlits AppTest-Framework: rendert jede Seite der
App headless und stellt sicher, dass kein Rerun mit einer Exception endet.

Diese Tests sind bewusst grob (kein Pixel-Vergleich) - sie fangen die
haeufigste Fehlerklasse ab: eine Umstrukturierung, ein umbenannter
Session-State-Key oder ein geaendertes Engine-Schema, das erst beim
Rendern einer bestimmten Seite auffliegt.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402


@pytest.fixture
def at() -> AppTest:
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=60)
    app.run()
    assert not app.exception
    return app


class TestSeitenRendern:
    def test_portfolio_zeigt_kennzahlen_und_projekte(self, at: AppTest):
        # Portfolio-KPI-Leiste (Projekte, MWp, Invest, Ø IRR).
        assert len(at.metric) == 4
        oeffnen_buttons = [
            b for b in at.button if b.key and b.key.startswith("open_")
        ]
        assert len(oeffnen_buttons) >= 1

    def test_projekt_dashboard_oeffnet_ohne_fehler(self, at: AppTest):
        oeffnen_buttons = [
            b for b in at.button if b.key and b.key.startswith("open_")
        ]
        oeffnen_buttons[0].click()
        at.run()
        assert not at.exception
        # 4 Portfolio- + 5 Projekt-KPIs.
        assert len(at.metric) == 9

    def test_neues_projekt_zeigt_formular(self, at: AppTest):
        at.sidebar.radio[0].set_value("Neues Projekt")
        at.run()
        assert not at.exception
        assert len(at.get("number_input")) > 10

    def test_globale_annahmen_rendern(self, at: AppTest):
        at.sidebar.radio[0].set_value("Globale Annahmen")
        at.run()
        assert not at.exception
