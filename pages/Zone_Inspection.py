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
from src.auth import require_auth, render_user_info

st.set_page_config(
    page_title="Zone Inspection — EO Dashboard",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth()

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    _t_pre = LIGHT if st.session_state.get("_theme", "Light") == "Light" else DARK
    render_user_info(_t_pre)
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

# ── Status summary row for a zone list ──────────────────────
def _status_summary(zones, latest_lookup, index_key):
    counts = {"normal": 0, "warning": 0, "critical": 0}
    for z in zones:
        alert = latest_lookup.get(z["zone_name"], {}).get("alert_level", "normal")
        counts[alert] = counts.get(alert, 0) + 1
    parts = []
    if counts["critical"]: parts.append(f'<span style="color:{t["red"]};font-weight:600;">{counts["critical"]} critical</span>')
    if counts["warning"]:  parts.append(f'<span style="color:{t["amber"]};font-weight:600;">{counts["warning"]} warning</span>')
    if counts["normal"]:   parts.append(f'<span style="color:{t["green"]};">{counts["normal"]} normal</span>')
    return " · ".join(parts) if parts else ""


# ── Zone Selectors ───────────────────────────────────────────
hydro_col, agri_col = st.columns(2)

with hydro_col:
    _h_summary = _status_summary(hydro_zones, hydro_latest, "ndti_mean")
    st.markdown(f"""<div style="margin-bottom:8px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
            <span class="panel-label" style="margin:0;">HYDRO ZONES</span>
            <span class="meta-tag">{len(hydro_zones)} monitored</span>
        </div>
        <div style="font-size:11px;margin-bottom:10px;">{_h_summary}</div>
    </div>""", unsafe_allow_html=True)

    _hydro_names = ["— select a zone —"] + [z["zone_name"] for z in hydro_zones]
    _hydro_sel   = st.selectbox("Hydro zone", _hydro_names,
                                label_visibility="collapsed", key="zi_hydro")

with agri_col:
    _a_summary = _status_summary(agri_zones, agri_latest, "ndvi_mean")
    st.markdown(f"""<div style="margin-bottom:8px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
            <span class="panel-label" style="margin:0;">AGRI ZONES</span>
            <span class="meta-tag">{len(agri_zones)} monitored</span>
        </div>
        <div style="font-size:11px;margin-bottom:10px;">{_a_summary}</div>
    </div>""", unsafe_allow_html=True)

    _agri_names = ["— select a zone —"] + [z["zone_name"] for z in agri_zones]
    _agri_sel   = st.selectbox("Agri zone", _agri_names,
                               label_visibility="collapsed", key="zi_agri")

# If both are selected, whichever changed last wins — track via session state
if _hydro_sel != "— select a zone —":
    if st.session_state.get("_zi_last") != _hydro_sel:
        st.session_state["_zi_last"]    = _hydro_sel
        st.session_state["zi_selected"] = _hydro_sel

if _agri_sel != "— select a zone —":
    if st.session_state.get("_zi_last") != _agri_sel:
        st.session_state["_zi_last"]    = _agri_sel
        st.session_state["zi_selected"] = _agri_sel


# ── Zone Detail ──────────────────────────────────────────────
_selected = st.session_state.get("zi_selected")
if _selected and _selected not in ("— select a zone —",):
    all_zones  = hydro_zones + agri_zones
    _zone_dict = next((z for z in all_zones if z["zone_name"] == _selected), None)
    if _zone_dict:
        st.markdown("---")
        st.markdown(f'<span class="panel-label">ZONE DETAIL — {_selected}</span>',
                    unsafe_allow_html=True)
        st.markdown("")
        with st.expander(_selected, expanded=True):
            render_zone_dashboard(_zone_dict, t)

# ── Footer ────────────────────────────────────────────────────
st.markdown("")
st.markdown(f"""<div style="text-align:center;padding:24px 0 16px;border-top:1px solid {t['border']};margin-top:24px;">
    <span style="font-size:11px;color:{t['text4']};">NextGen Spark Sdn Bhd · EO Monitoring Prototype v1.0 · Powered by Sentinel-2 & Google Earth Engine</span>
</div>""", unsafe_allow_html=True)
