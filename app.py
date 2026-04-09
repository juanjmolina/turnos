"""
Sistema de Rotación de Turnos — app principal Streamlit
"""
import streamlit as st
from database.db import init_db
from modules.ui_helpers import render_header_css
from modules import ui_helpers

st.set_page_config(
    page_title="Sistema de Turnos",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inicializar base de datos y CSS
init_db()
render_header_css()

# ── Estado de sesión global ──────────────────────────────────────────────────
def _init_state():
    defaults = {
        "week_offset": 0,
        "current_tab": "tabla",
        "filter_grupo": "Todos",
        "filter_aus_tipo": "Todos",
        "filter_aus_est": "Todos",
        "filter_aus_wk": "Todos",
        "search_query": "",
        "search_he": "",
        "show_normativa": False,
        "aus_form_open": False,
        "edit_aus_id": None,
        "show_add_worker": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ── Header ───────────────────────────────────────────────────────────────────
ui_helpers.render_header()

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_labels = ["📋 Horario", "⏱️ Horas Extras", "📅 Ausencias", "👥 Personal"]
tabs = st.tabs(tab_labels)

with tabs[0]:
    ui_helpers.render_tabla()

with tabs[1]:
    ui_helpers.render_horas()

with tabs[2]:
    ui_helpers.render_ausencias()

with tabs[3]:
    ui_helpers.render_gestionar()
