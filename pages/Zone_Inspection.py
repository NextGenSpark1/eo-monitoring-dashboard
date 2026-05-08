# ================================================================================
# pages/Zone_Inspection.py — Zone Inspection
# ================================================================================
# Developer  : Habiba Hassan (AI Analytics & Visualization)
# Description: Dedicated page to browse all monitored zones (Hydro + Agri)
#              and drill into any zone's full satellite dashboard.
# ================================================================================

import streamlit as st
import datetime

import pandas as pd

from utils.theme import DARK, LIGHT
from utils.styles import get_css
from src.gee_logic import RESERVOIR_CONFIG, FARM_CONFIG
from src.database import read_saved_zones, read_hydro_data, read_agri_data
from src.zone_dashboard import render_zone_dashboard

st.set_page_config(
    page_title="Zone Inspection — EO Dashboard",
    page_icon="🔎",
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
        <p class="dash-title">Zone Inspection</p>
        <p class="dash-sub">Browse all monitored zones and drill into full satellite analytics</p>
    </div></div>""", unsafe_allow_html=True)
with live_col:
    st.markdown(f"""<div style="display:flex;justify-content:flex-end;align-items:center;gap:14px;padding-top:16px;">
        <span class="meta-tag">Last update: {datetime.datetime.now().strftime("%d %b %Y, %H:%M")}</span>
        <span class="live-pill"><span class="live-dot-anim"></span>LIVE</span>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── Load Zones ───────────────────────────────────────────────
if "saved_zones" not in st.session_state:
    try:
        st.session_state["saved_zones"] = read_saved_zones()
    except Exception:
        st.session_state["saved_zones"] = []

saved_zones = st.session_state["saved_zones"]

hydro_zones = [
    {"zone_name": RESERVOIR_CONFIG["name"], "lat": RESERVOIR_CONFIG["lat"],
     "lon": RESERVOIR_CONFIG["lon"], "zone_type": "hydro", "added_at": ""},
] + [
    z for z in saved_zones
    if z.get("zone_type") in ("hydro", "both")
    and z["zone_name"] != RESERVOIR_CONFIG["name"]
]

agri_zones = [
    {"zone_name": FARM_CONFIG["name"], "lat": FARM_CONFIG["lat"],
     "lon": FARM_CONFIG["lon"], "zone_type": "agri", "added_at": ""},
] + [
    z for z in saved_zones
    if z.get("zone_type") in ("agri", "both")
    and z["zone_name"] != FARM_CONFIG["name"]
]

# ── Load latest readings for zone cards ──────────────────────
@st.cache_data(ttl=300)
def _latest_hydro():
    df = read_hydro_data()
    if df.empty:
        return {}
    df = df.sort_values("date")
    return {
        zone: grp.iloc[-1].to_dict()
        for zone, grp in df.groupby("zone")
    }

@st.cache_data(ttl=300)
def _latest_agri():
    df = read_agri_data()
    if df.empty:
        return {}
    df = df.sort_values("date")
    return {
        zone: grp.iloc[-1].to_dict()
        for zone, grp in df.groupby("zone")
    }

hydro_latest = _latest_hydro()
agri_latest  = _latest_agri()

# ── Zone card renderer ───────────────────────────────────────
def _zone_card(zone: dict, index_key: str, index_label: str, latest_lookup: dict):
    name    = zone["zone_name"]
    reading = latest_lookup.get(name, {})
    value   = reading.get(index_key)
    alert   = reading.get("alert_level", "normal")
    date    = reading.get("date", "")

    dot_color  = {"critical": t["red"], "warning": t["amber"], "normal": t["green"]}.get(alert, t["green"])
    val_color  = {"critical": "c-r",    "warning": "c-y",      "normal": "c-g"}.get(alert, "c-g")
    dot_class  = {"critical": "dot-r",  "warning": "dot-y",    "normal": "dot-g"}.get(alert, "dot-g")
    card_class = {"critical": "zcard-crit", "warning": "zcard-warn", "normal": ""}.get(alert, "")

    val_display = f"{value:.4f}" if value is not None else "—"
    date_display = f"Last reading: {date}" if date else "No data yet"

    st.markdown(f"""<div class="zcard {card_class}" style="margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
                <div class="zname"><span class="dot {dot_class}"></span>{name}</div>
                <div class="zmeta">{date_display}</div>
            </div>
            <div style="text-align:right;">
                <div class="zval {val_color}">{val_display}</div>
                <div style="font-size:10px;color:{t['text4']};">{index_label}</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    if st.button("Inspect", key=f"zi_btn_{name}", use_container_width=True):
        st.session_state["zi_selected"] = name
        st.rerun()


# ── Zone Lists ───────────────────────────────────────────────
hydro_col, agri_col = st.columns(2)

with hydro_col:
    st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
        <span class="panel-label" style="margin:0;">HYDRO ZONES</span>
        <span class="meta-tag">{len(hydro_zones)} monitored</span>
    </div>""", unsafe_allow_html=True)

    for zone in hydro_zones:
        _zone_card(zone, "ndti_mean", "NDTI", hydro_latest)

with agri_col:
    st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
        <span class="panel-label" style="margin:0;">AGRI ZONES</span>
        <span class="meta-tag">{len(agri_zones)} monitored</span>
    </div>""", unsafe_allow_html=True)

    for zone in agri_zones:
        _zone_card(zone, "ndvi_mean", "NDVI", agri_latest)


# ── Zone Detail ──────────────────────────────────────────────
_selected = st.session_state.get("zi_selected")
if _selected:
    all_zones  = hydro_zones + agri_zones
    _zone_dict = next((z for z in all_zones if z["zone_name"] == _selected), None)
    if _zone_dict:
        st.markdown("---")
        st.markdown(f"""<div style="margin-bottom:12px;">
            <span class="panel-label">ZONE DETAIL — {_selected}</span>
        </div>""", unsafe_allow_html=True)
        with st.expander(f"{_selected}", expanded=True):
            render_zone_dashboard(_zone_dict, t)

# ── Footer ────────────────────────────────────────────────────
st.markdown("")
st.markdown(f"""<div style="text-align:center;padding:24px 0 16px;border-top:1px solid {t['border']};margin-top:24px;">
    <span style="font-size:11px;color:{t['text4']};">NextGen Spark Sdn Bhd · EO Monitoring Prototype v1.0 · Powered by Sentinel-2 & Google Earth Engine</span>
</div>""", unsafe_allow_html=True)
