# ================================================================================
# pages/Live_Lookup.py — Live Location Analysis
# ================================================================================
# Developer  : Habiba Hassan (AI Analytics & Visualization)
# Description: Separate page for on-demand GEE analysis of any Malaysian location.
# ================================================================================

import streamlit as st
import datetime

from utils.theme import DARK, LIGHT
from utils.styles import get_css
from src.dynamic_zone import render_search_ui

st.set_page_config(
    page_title="Live Lookup — EO Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px;">
        <div style="width:34px;height:34px;border-radius:10px;
            background:linear-gradient(135deg,#4f8df5,#34d399);
            display:flex;align-items:center;justify-content:center;
            font-size:13px;font-weight:700;color:#fff;
            box-shadow:0 3px 10px rgba(79,141,245,0.25);">NS</div>
        <div>
            <div style="font-size:14px;font-weight:600;" class="sb-header-title">Control Panel</div>
            <div style="font-size:10px;color:#94a3b8;">NextGen Spark EO</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if "_theme" not in st.session_state:
        st.session_state["_theme"] = "Light"
    theme_choice = st.radio("Theme", ["Light", "Dark"], horizontal=True,
                            label_visibility="collapsed",
                            index=0 if st.session_state["_theme"] == "Light" else 1)
    st.session_state["_theme"] = theme_choice

    _t_sidebar = LIGHT if theme_choice == "Light" else DARK
    st.markdown("---")
    st.markdown(f"""<div style="font-size:10px;color:{_t_sidebar['text4']};line-height:1.7;padding-top:6px;">
        <strong style="color:{_t_sidebar['text3']};">Data Source:</strong> Sentinel-2 L2A<br>
        <strong style="color:{_t_sidebar['text3']};">Revisit:</strong> 5-day cycle<br>
        <strong style="color:{_t_sidebar['text3']};">Processing:</strong> Google Earth Engine<br>
        <strong style="color:{_t_sidebar['text3']};">Coverage:</strong> All of Malaysia</div>""",
        unsafe_allow_html=True)

t = LIGHT if theme_choice == "Light" else DARK

# ── CSS ──────────────────────────────────────────────────────
st.markdown(get_css(t, theme_choice), unsafe_allow_html=True)

# ── Page Header ──────────────────────────────────────────────
header_col, live_col = st.columns([3, 1])
with header_col:
    st.markdown(f"""<div class="dash-header"><div class="dash-logo">NS</div><div>
        <p class="dash-title">Live Lookup</p>
        <p class="dash-sub">Analyse any location in Malaysia using live Sentinel-2 satellite data</p>
    </div></div>""", unsafe_allow_html=True)
with live_col:
    st.markdown(f"""<div style="display:flex;justify-content:flex-end;align-items:center;gap:14px;padding-top:16px;">
        <span class="meta-tag">Last update: {datetime.datetime.now().strftime("%d %b %Y, %H:%M")}</span>
        <span class="live-pill"><span class="live-dot-anim"></span>LIVE</span>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── Live Lookup UI ────────────────────────────────────────────
render_search_ui()

# ── Footer ────────────────────────────────────────────────────
st.markdown("")
st.markdown(f"""<div style="text-align:center;padding:24px 0 16px;border-top:1px solid {t['border']};margin-top:24px;">
    <span style="font-size:11px;color:{t['text4']};">NextGen Spark Sdn Bhd · EO Monitoring Prototype v1.0 · Powered by Sentinel-2 & Google Earth Engine</span>
</div>""", unsafe_allow_html=True)
