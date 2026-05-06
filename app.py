# ================================================================================
# app.py — EO Monitoring Dashboard
# ================================================================================
# Developer  : Habiba Hassan (AI Analytics & Visualization)
# Description: Streamlit frontend — KPI panels, satellite maps, trend charts,
#              alert system, Telegram subscription, and Live Lookup feature.
# ================================================================================

import streamlit as st
import pandas as pd
import pydeck as pdk
import altair as alt
import datetime
import time

from utils.theme import DARK, LIGHT
from utils.styles import get_css
from src.database import (
    read_hydro_data,
    read_agri_data,
    add_subscriber,
    get_all_subscribers,
    read_saved_zones,
)
from src.zone_dashboard import render_zone_dashboard
from src.telegram_helper import (
    send_telegram_message,
    send_test_alert,
    send_subscription_welcome,
    build_alert_message,
)
from src.gee_logic import (
    initialize_gee,
    get_map_layers,
    RESERVOIR_CONFIG,
    FARM_CONFIG,
)


# ──────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EO Monitoring Dashboard",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────
# SAVED ZONES — load once per session, cleared on auto-refresh
# ──────────────────────────────────────────────────────────────
if "saved_zones" not in st.session_state:
    try:
        st.session_state["saved_zones"] = read_saved_zones()
    except Exception:
        st.session_state["saved_zones"] = []

saved_zones = st.session_state["saved_zones"]

# AUTO-REFRESH
REFRESH_INTERVAL = 300
if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = time.time()

time_since = time.time() - st.session_state["last_refresh"]
time_left  = max(0, int(REFRESH_INTERVAL - time_since))

# ──────────────────────────────────────────────────────────────
# THEME SYSTEM
# ──────────────────────────────────────────────────────────────
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

    theme_choice = st.radio("Theme", ["Light", "Dark"], horizontal=True,
                            label_visibility="collapsed", key="theme_choice")

t = LIGHT if theme_choice == "Light" else DARK

# ──────────────────────────────────────────────────────────────
# DYNAMIC CSS
# ──────────────────────────────────────────────────────────────
st.markdown(get_css(t, theme_choice), unsafe_allow_html=True)

st.caption(f"Auto-refreshing in {time_left // 60}m {time_left % 60}s")
if time_since >= REFRESH_INTERVAL:
    st.session_state["last_refresh"] = time.time()
    if "saved_zones" in st.session_state:
        del st.session_state["saved_zones"]
    time.sleep(0.5)
    st.rerun()


# ──────────────────────────────────────────────────────────────
# DATA LOADING — CSV + GeoJSON
# ──────────────────────────────────────────────────────────────

ZONE_COORDS = {
    RESERVOIR_CONFIG["name"]: {
        "lat":     RESERVOIR_CONFIG["lat"],
        "lon":     RESERVOIR_CONFIG["lon"],
        "zone_id": "RES-001",
    },
    FARM_CONFIG["name"]: {
        "lat":     FARM_CONFIG["lat"],
        "lon":     FARM_CONFIG["lon"],
        "zone_id": "FARM-001",
    },
}


def compute_trend(sorted_values):
    if len(sorted_values) < 2:
        return "stable"
    previous, current = sorted_values.iloc[-2], sorted_values.iloc[-1]
    if current > previous + 0.01:
        return "rising"
    elif current < previous - 0.01:
        return "falling"
    return "stable"


@st.cache_data(ttl=300)
def load_hydro_data(extra_zones=()):
    """Latest hydro reading per zone. extra_zones extends ZONE_COORDS with saved zones."""
    df = read_hydro_data()
    if df.empty:
        return pd.DataFrame()

    all_coords = dict(ZONE_COORDS)
    for z_name, z_lat, z_lon, z_id in extra_zones:
        if z_name not in all_coords:
            all_coords[z_name] = {"lat": z_lat, "lon": z_lon, "zone_id": z_id}

    df = df.sort_values("date")
    result = []
    for zone_name, group in df.groupby("zone"):
        if zone_name not in all_coords:
            continue
        latest_row = group.iloc[-1]
        coords = all_coords[zone_name]
        result.append({
            "zone_id":   coords["zone_id"],
            "name":      zone_name,
            "lat":       coords["lat"],
            "lon":       coords["lon"],
            "turbidity": round(latest_row["ndti_mean"], 4) if pd.notna(latest_row["ndti_mean"]) else 0.0,
            "status":    latest_row.get("alert_level", "normal"),
            "trend":     compute_trend(group["ndti_mean"]),
            "ndwi":      round(latest_row["ndwi_mean"], 4) if pd.notna(latest_row.get("ndwi_mean")) else 0.0,
            "ndti_min":  round(latest_row["ndti_min"], 4) if pd.notna(latest_row.get("ndti_min")) else 0.0,
            "ndti_max":  round(latest_row["ndti_max"], 4) if pd.notna(latest_row.get("ndti_max")) else 0.0,
        })
    return pd.DataFrame(result)


@st.cache_data(ttl=300)
def load_agri_data(extra_zones=()):
    """Latest agri reading per zone. extra_zones extends ZONE_COORDS with saved zones."""
    df = read_agri_data()
    if df.empty:
        return pd.DataFrame()

    all_coords = dict(ZONE_COORDS)
    for z_name, z_lat, z_lon, z_id in extra_zones:
        if z_name not in all_coords:
            all_coords[z_name] = {"lat": z_lat, "lon": z_lon, "zone_id": z_id}

    df = df.sort_values("date")
    result = []
    for zone_name, group in df.groupby("zone"):
        if zone_name not in all_coords:
            continue
        latest_row = group.iloc[-1]
        coords = all_coords[zone_name]
        result.append({
            "zone_id":  coords["zone_id"],
            "name":     zone_name,
            "lat":      coords["lat"],
            "lon":      coords["lon"],
            "ndvi":     round(latest_row["ndvi_mean"], 4) if pd.notna(latest_row["ndvi_mean"]) else 0.0,
            "status":   latest_row.get("alert_level", "normal"),
            "trend":    compute_trend(group["ndvi_mean"]),
            "ndre":     round(latest_row["ndre_mean"], 4) if pd.notna(latest_row.get("ndre_mean")) else 0.0,
            "ndvi_min": round(latest_row["ndvi_min"], 4) if pd.notna(latest_row.get("ndvi_min")) else 0.0,
            "ndvi_max": round(latest_row["ndvi_max"], 4) if pd.notna(latest_row.get("ndvi_max")) else 0.0,
        })
    return pd.DataFrame(result)


@st.cache_data(ttl=300)
def load_hydro_trends():
    """Pivot hydro NDTI history into a date×zone table for the trend chart."""
    df = read_hydro_data()
    if df.empty:
        return pd.DataFrame(columns=["date"])
    df = df[["date", "zone", "ndti_mean"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    pivot = df.pivot(index="date", columns="zone", values="ndti_mean")
    pivot = pivot.sort_index().reset_index()
    pivot.columns.name = None
    pivot["date"] = pivot["date"].dt.strftime("%Y-%m-%d")
    return pivot


@st.cache_data(ttl=300)
def load_agri_trends():
    """Pivot agri NDVI history into a date×zone table for the trend chart."""
    df = read_agri_data()
    if df.empty:
        return pd.DataFrame(columns=["date"])
    df = df[["date", "zone", "ndvi_mean"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    pivot = df.pivot(index="date", columns="zone", values="ndvi_mean")
    pivot = pivot.sort_index().reset_index()
    pivot.columns.name = None
    pivot["date"] = pivot["date"].dt.strftime("%Y-%m-%d")
    return pivot

NDTI_VIS = {"min": -0.1, "max": 0.35,
            "palette": ["1a237e", "0288d1", "4dd0e1", "fff176", "ff8f00", "b71c1c"]}
NDVI_VIS = {"min": 0.1,  "max": 0.85,
            "palette": ["a50026", "f46d43", "fee08b", "d9ef8b", "66bd63", "1a9850", "006837"]}


@st.cache_resource(show_spinner=False)
def load_map_tile_urls(lat, lon):
    """Load both NDTI (water) and NDVI (land) tile URLs in one GEE call."""
    from datetime import datetime
    try:
        initialize_gee()
        ndti_img, ndvi_img, _, last_date = get_map_layers(lat, lon, datetime.now().strftime("%Y-%m-%d"))
        ndti_url = ndti_img.getMapId(NDTI_VIS)["tile_fetcher"].url_format if ndti_img else None
        ndvi_url = ndvi_img.getMapId(NDVI_VIS)["tile_fetcher"].url_format if ndvi_img else None
        error    = None if (ndti_url or ndvi_url) else "No clear Sentinel-2 image in the last 365 days"
        return ndti_url, ndvi_url, error, last_date
    except Exception as e:
        return None, None, str(e), None


def get_all_alerts(zones_df, value_col):
    alerts = []
    time_str = datetime.datetime.now().strftime("%H:%M")
    non_normal_zones = zones_df[zones_df["status"] != "normal"].copy()
    severity_order = {"critical": 0, "warning": 1}
    non_normal_zones = non_normal_zones.assign(
        _sort=non_normal_zones["status"].map(severity_order)
    ).sort_values("_sort")
    for _, zone_row in non_normal_zones.iterrows():
        index_value = zone_row[value_col]
        if value_col == "turbidity":
            message = (
                f"NDTI at {index_value} — turbidity critical. Immediate inspection recommended."
                if zone_row["status"] == "critical"
                else f"NDTI at {index_value} — turbidity elevated. Monitor closely for next satellite pass."
            )
        else:
            message = (
                f"NDVI at {index_value} — severe vegetation stress detected. Ground inspection recommended."
                if zone_row["status"] == "critical"
                else f"NDVI at {index_value} — vegetation health below optimal. Monitor closely."
            )
        alerts.append({
            "severity": zone_row["status"],
            "status":   zone_row["status"],
            "zone":     zone_row["name"],
            "time":     time_str,
            "message":  message,
        })
    return alerts

def classify_hydro_status(zones_df, warning_threshold, critical_threshold):
    zones_df = zones_df.copy()
    def get_status(turbidity_value):
        if turbidity_value >= critical_threshold: return "critical"
        if turbidity_value >= warning_threshold:  return "warning"
        return "normal"
    zones_df["status"] = zones_df["turbidity"].apply(get_status)
    return zones_df

def classify_agri_status(zones_df, warning_threshold, critical_threshold):
    zones_df = zones_df.copy()
    def get_status(ndvi_value):
        if ndvi_value < critical_threshold: return "critical"
        if ndvi_value < warning_threshold:  return "warning"
        return "normal"
    zones_df["status"] = zones_df["ndvi"].apply(get_status)
    return zones_df


# ──────────────────────────────────────────────────────────────
# MAP
# ──────────────────────────────────────────────────────────────

def build_map(zones_df, value_col):
    map_df = zones_df.copy()

    # pydeck needs colors as (R, G, B, Alpha) tuples, not hex
    color_map = {
        "critical": (int(t['red'][1:3],16),   int(t['red'][3:5],16),   int(t['red'][5:7],16),   210),
        "warning":  (int(t['amber'][1:3],16),  int(t['amber'][3:5],16), int(t['amber'][5:7],16), 190),
        "normal":   (int(t['green'][1:3],16),  int(t['green'][3:5],16), int(t['green'][5:7],16), 180),
    }
    radius_map = {"critical": 6000, "warning": 4500, "normal": 3000}

    map_df["r"]      = map_df["status"].map(lambda s: color_map[s][0])
    map_df["g"]      = map_df["status"].map(lambda s: color_map[s][1])
    map_df["b"]      = map_df["status"].map(lambda s: color_map[s][2])
    map_df["a"]      = map_df["status"].map(lambda s: color_map[s][3])
    map_df["radius"] = map_df["status"].map(radius_map)

    if value_col == "turbidity":
        tooltip_html = f"""
            <div style='font-family:Inter,sans-serif;padding:12px 16px;max-width:260px;'>
                <div style='font-size:15px;font-weight:600;color:{t['text1']};margin-bottom:8px;'>{{name}}</div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>
                    NDTI: <b style="color:{t['text1']}">{{turbidity}}</b>
                </div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>
                    Range: {{ndti_min}} to {{ndti_max}}
                </div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>NDWI: {{ndwi}}</div>
                <div style='font-size:11px;color:{t['text4']};border-top:1px solid {t['border']};padding-top:6px;margin-top:4px;'>
                    Status: <b>{{status}}</b> · Trend: {{trend}}
                </div>
            </div>"""
    else:
        tooltip_html = f"""
            <div style='font-family:Inter,sans-serif;padding:12px 16px;max-width:260px;'>
                <div style='font-size:15px;font-weight:600;color:{t['text1']};margin-bottom:8px;'>{{name}}</div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>
                    NDVI: <b style="color:{t['text1']}">{{ndvi}}</b>
                </div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>
                    Range: {{ndvi_min}} to {{ndvi_max}}
                </div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>NDRE: {{ndre}}</div>
                <div style='font-size:11px;color:{t['text4']};border-top:1px solid {t['border']};padding-top:6px;margin-top:4px;'>
                    Status: <b>{{status}}</b> · Trend: {{trend}}
                </div>
            </div>"""

    layers = []
    critical_zones = map_df[map_df["status"] == "critical"].copy()
    if not critical_zones.empty:
        critical_zones["glow_radius"] = critical_zones["radius"] * 2.5
        layers.append(pdk.Layer(
            "ScatterplotLayer", data=critical_zones,
            get_position=["lon", "lat"],
            get_color=[color_map["critical"][0], color_map["critical"][1], color_map["critical"][2], 30],
            get_radius="glow_radius", pickable=False,
        ))
    layers.append(pdk.Layer(
        "ScatterplotLayer", data=map_df,
        get_position=["lon", "lat"],
        get_color=["r", "g", "b", "a"],
        get_radius="radius", pickable=True,
        auto_highlight=True, highlight_color=[255, 255, 255, 50],
    ))

    view_state = pdk.ViewState(
        latitude=float(map_df["lat"].mean()),
        longitude=float(map_df["lon"].mean()),
        zoom=7.2 if value_col == "turbidity" else 7.5,
        pitch=0,
    )
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip={
            "html": tooltip_html,
            "style": {
                "backgroundColor": t['tooltip_bg'],
                "border": f"1px solid {t['tooltip_bdr']}",
                "borderRadius": "12px",
                "color": t['text1'],
                "boxShadow": "0 8px 24px rgba(0,0,0,0.15)",
            },
        },
        map_style=t['map_style'],
    )


# ──────────────────────────────────────────────────────────────
# ALTAIR CHART
# ──────────────────────────────────────────────────────────────

def build_trend_chart(trends_df, value_col):
    long_df = trends_df.melt(id_vars="date", var_name="Zone", value_name=value_col.upper())
    long_df = long_df.dropna(subset=[value_col.upper()])
    color_scale = alt.Scale(range=[t['green'], t['amber'], t['red'], t['blue'], "#a78bfa", "#f472b6"])
    y_min    = long_df[value_col.upper()].min()
    y_max    = long_df[value_col.upper()].max()
    y_pad    = max(0.05, (y_max - y_min) * 0.15)
    y_domain = [round(y_min - y_pad, 2), round(y_max + y_pad, 2)]

    base = alt.Chart(long_df).encode(
        x=alt.X("date:T", title=None,
            axis=alt.Axis(format="%b '%y", tickCount="month",
                          labelColor=t['text4'], labelFontSize=11, labelFont="Inter",
                          tickColor="transparent", domainColor=t['border'],
                          labelAngle=0, labelPadding=10)),
        y=alt.Y(f"{value_col.upper()}:Q", scale=alt.Scale(domain=y_domain), title=None,
            axis=alt.Axis(labelColor=t['text4'], labelFontSize=10, labelFont="JetBrains Mono",
                          gridColor=t['chart_grid'], tickColor="transparent", domainColor="transparent")),
        color=alt.Color("Zone:N", scale=color_scale, title="Zone",
            legend=alt.Legend(orient="bottom", columns=3, labelColor=t['text3'],
                              labelFontSize=11, labelFont="Inter", titleColor=t['text4'],
                              titleFontSize=10, symbolSize=60)),
    )
    lines  = base.mark_line(strokeWidth=2.5, opacity=0.9)
    points = base.mark_circle(size=50, opacity=1).encode(
        tooltip=[
            alt.Tooltip("date:T",                title="Date", format="%d %b %Y"),
            alt.Tooltip("Zone:N",                title="Zone"),
            alt.Tooltip(f"{value_col.upper()}:Q", title=value_col.upper(), format=".4f"),
        ]
    )
    return (lines + points).properties(height=300, background="transparent") \
                           .configure(font="Inter") \
                           .configure_view(strokeWidth=0)


# ══════════════════════════════════════════════════════════════
# SIDEBAR — MODULE, FILTERS, THRESHOLDS, SUBSCRIPTION
# ══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("---")
    st.markdown(f'<p class="sb-label">Monitoring Module</p>', unsafe_allow_html=True)
    view_choice = st.radio("Module", ["Hydro Reservoir", "Agriculture"], label_visibility="collapsed")

    st.markdown("---")
    st.markdown(f'<p class="sb-label">Status Filter</p>', unsafe_allow_html=True)
    show_normal   = st.checkbox("Normal",   value=True)
    show_warning  = st.checkbox("Warning",  value=True)
    show_critical = st.checkbox("Critical", value=True)
    active_statuses = []
    if show_normal:   active_statuses.append("normal")
    if show_warning:  active_statuses.append("warning")
    if show_critical: active_statuses.append("critical")

    st.markdown("---")
    st.markdown(f'<p class="sb-label">Thresholds</p>', unsafe_allow_html=True)
    if view_choice == "Hydro Reservoir":
        warning_threshold  = st.slider("Warning level (NDTI >=)", 0.0, 1.0, 0.40, 0.05, key="hydro_warn")
        critical_threshold = st.slider("Critical level (NDTI >=)", 0.0, 1.0, 0.60, 0.05, key="hydro_crit")
        st.markdown(f"""<div style="font-size:10.5px;line-height:2.2;color:{t['sb_text']};">
            <span style="color:{t['green']};">●</span> Normal: &lt; {warning_threshold:.2f}<br>
            <span style="color:{t['amber']};">●</span> Warning: {warning_threshold:.2f} – {critical_threshold:.2f}<br>
            <span style="color:{t['red']};">●</span> Critical: ≥ {critical_threshold:.2f}</div>""", unsafe_allow_html=True)
    else:
        warning_threshold  = st.slider("Warning level (NDVI <)", 0.0, 1.0, 0.55, 0.05, key="agri_warn")
        critical_threshold = st.slider("Critical level (NDVI <)", 0.0, 1.0, 0.40, 0.05, key="agri_crit")
        st.markdown(f"""<div style="font-size:10.5px;line-height:2.2;color:{t['sb_text']};">
            <span style="color:{t['green']};">●</span> Normal: &gt; {warning_threshold:.2f}<br>
            <span style="color:{t['amber']};">●</span> Warning: {critical_threshold:.2f} – {warning_threshold:.2f}<br>
            <span style="color:{t['red']};">●</span> Critical: &lt; {critical_threshold:.2f}</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f'<p class="sb-label">Alert Subscription</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-size:11px;color:{t["text4"]};margin:0 0 10px;">Paste your Telegram chat ID to receive alerts.</p>', unsafe_allow_html=True)
    chat_id_input = st.text_input(
        "Telegram Chat ID",
        placeholder="e.g. 1761625405",
        label_visibility="collapsed",
        key="chat_id_input"
    )
    subscribe_col, test_col = st.columns(2)
    with subscribe_col:
        subscribe_clicked = st.button("Subscribe", use_container_width=True, key="btn_subscribe", type="primary")
    with test_col:
        test_clicked = st.button("Test Alert", use_container_width=True, key="btn_test")

    if subscribe_clicked:
        if chat_id_input.strip():
            chat_id = chat_id_input.strip()
            saved = add_subscriber(chat_id)
            if saved:
                ok, error_msg = send_subscription_welcome(chat_id)
                st.markdown(
                    f'<div class="sb-feedback {"sb-ok" if ok else "sb-err"}">'
                    f'{"Subscribed successfully." if ok else f"Failed: {error_msg}"}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown('<div class="sb-feedback sb-err">Could not save subscriber. Check Supabase connection.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="sb-feedback sb-warn">Enter a chat ID first.</div>', unsafe_allow_html=True)

    if test_clicked:
        if chat_id_input.strip():
            ok, error_msg = send_test_alert(chat_id_input.strip())
            st.markdown(
                f'<div class="sb-feedback {"sb-ok" if ok else "sb-err"}">'
                f'{"Test alert sent to Telegram." if ok else f"Failed: {error_msg}"}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="sb-feedback sb-warn">Enter a chat ID first.</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:10px;color:{t["text4"]};margin-top:8px;line-height:1.6;">Get your ID via <b style="color:{t["text3"]};">@userinfobot</b> on Telegram.</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"""<div style="font-size:10px;color:{t['text4']};line-height:1.7;padding-top:6px;">
        <strong style="color:{t['text3']};">Data Source:</strong> Sentinel-2 L2A<br>
        <strong style="color:{t['text3']};">Revisit:</strong> 5-day cycle<br>
        <strong style="color:{t['text3']};">Processing:</strong> Google Earth Engine<br>
        <strong style="color:{t['text3']};">Version:</strong> Prototype v1.0</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# LOAD & FILTER DATA
# ══════════════════════════════════════════════════════════════

# Build extra_zones tuple from saved_zones for cache-safe passing
_hydro_extra = tuple(
    (z["zone_name"], z["lat"], z["lon"], f"SAVED-{i}")
    for i, z in enumerate(saved_zones)
    if z.get("zone_type") in ("hydro", "both")
)
_agri_extra = tuple(
    (z["zone_name"], z["lat"], z["lon"], f"SAVED-{i}")
    for i, z in enumerate(saved_zones)
    if z.get("zone_type") in ("agri", "both")
)

if view_choice == "Hydro Reservoir":
    all_zones  = classify_hydro_status(load_hydro_data(_hydro_extra), warning_threshold, critical_threshold)
    trends_df  = load_hydro_trends()
    value_col  = "turbidity"
    module_name = "Turbidity"
    threshold_note = "Higher = worse water quality"
else:
    all_zones  = classify_agri_status(load_agri_data(_agri_extra), warning_threshold, critical_threshold)
    trends_df  = load_agri_trends()
    value_col  = "ndvi"
    module_name = "NDVI"
    threshold_note = "Lower = vegetation stress"

filtered_zones = all_zones[all_zones["status"].isin(active_statuses)].copy()
total_zones    = len(all_zones)
filtered_count = len(filtered_zones)
num_critical   = len(filtered_zones[filtered_zones["status"] == "critical"])
num_warning    = len(filtered_zones[filtered_zones["status"] == "warning"])
num_normal     = len(filtered_zones[filtered_zones["status"] == "normal"])
avg_value      = round(filtered_zones[value_col].mean(), 2) if not filtered_zones.empty else 0
filtered_alerts = [a for a in get_all_alerts(all_zones, value_col) if a["status"] in active_statuses]

# Auto-send alerts to subscribers when threshold is breached
if filtered_alerts:
    subscribers = get_all_subscribers()
    if subscribers:
        sent_state_key = f"sent_keys_{value_col}"
        if sent_state_key not in st.session_state:
            st.session_state[sent_state_key] = set()
        current_alert_keys = {f"{alert['zone']}_{alert['severity']}" for alert in filtered_alerts}
        new_alerts = [
            alert for alert in filtered_alerts
            if f"{alert['zone']}_{alert['severity']}" not in st.session_state[sent_state_key]
        ]
        for alert in new_alerts:
            zone_row = all_zones[all_zones["name"] == alert["zone"]]
            index_value = round(zone_row[value_col].iloc[0], 4) if not zone_row.empty else "N/A"
            alert_message = build_alert_message(
                alert["zone"], str(index_value), alert["severity"], value_col, module_name
            )
            for subscriber_chat_id in subscribers:
                send_telegram_message(subscriber_chat_id, alert_message)
        st.session_state[sent_state_key] = current_alert_keys
else:
    st.session_state[f"sent_keys_{value_col}"] = set()


# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════

header_col, live_col = st.columns([3, 1])
with header_col:
    st.markdown(f"""<div class="dash-header"><div class="dash-logo">NS</div><div>
        <p class="dash-title">EO Monitoring Dashboard</p>
        <p class="dash-sub">NextGen Spark — Sentinel-2 Analytics Platform</p></div></div>""", unsafe_allow_html=True)
with live_col:
    st.markdown(f"""<div style="display:flex;justify-content:flex-end;align-items:center;gap:14px;padding-top:16px;">
        <span class="meta-tag">Last update: {datetime.datetime.now().strftime("%d %b %Y, %H:%M")}</span>
        <span class="live-pill"><span class="live-dot-anim"></span>LIVE</span></div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# KPI CARDS
# ══════════════════════════════════════════════════════════════

kpi_index_label = "NDTI Index" if value_col == "turbidity" else "Vegetation Index"
critical_badge  = '<span class="kpi-tag tag-red">Immediate attention</span>'  if num_critical > 0 else '<span class="kpi-tag tag-green">All clear</span>'
warning_badge   = '<span class="kpi-tag tag-amber">Under observation</span>' if num_warning  > 0 else '<span class="kpi-tag tag-green">All clear</span>'

st.markdown(f"""
<div class="kpi-row">
    <div class="kpi"><div class="kpi-accent" style="background:linear-gradient(90deg,{t['blue']},{t['green']});"></div>
        <div class="kpi-label">Avg {module_name}</div><div class="kpi-val">{avg_value}</div><span class="kpi-tag tag-blue">{kpi_index_label}</span></div>
    <div class="kpi {'kpi-glow' if num_critical>0 else ''}"><div class="kpi-accent" style="background:{t['red']};"></div>
        <div class="kpi-label">Critical Zones</div><div class="kpi-val">{num_critical}</div>{critical_badge}</div>
    <div class="kpi"><div class="kpi-accent" style="background:{t['amber']};"></div>
        <div class="kpi-label">Warning Zones</div><div class="kpi-val">{num_warning}</div>{warning_badge}</div>
    <div class="kpi"><div class="kpi-accent" style="background:{t['green']};"></div>
        <div class="kpi-label">Normal Zones</div><div class="kpi-val">{num_normal}</div><span class="kpi-tag tag-green">Within safe range</span></div>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TREND CHART
# ══════════════════════════════════════════════════════════════

st.markdown("")
st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <span class="panel-label" style="margin:0;">TREND: {module_name} — Historical Readings</span>
    <span class="note-box">{threshold_note}</span></div>""", unsafe_allow_html=True)
st.altair_chart(build_trend_chart(trends_df, value_col), use_container_width=True)


# ══════════════════════════════════════════════════════════════
# MAP + ZONE DETAILS
# ══════════════════════════════════════════════════════════════

map_col, details_col = st.columns([2, 1])
with map_col:
    import folium
    import branca.colormap as cm
    from streamlit_folium import st_folium

    center_cfg = RESERVOIR_CONFIG if value_col == "turbidity" else FARM_CONFIG
    map_title  = "Empangan Sultan Abu Bakar" if value_col == "turbidity" else "Felda Jengka"

    ndti_url, ndvi_url, gee_error, last_image_date = load_map_tile_urls(center_cfg["lat"], center_cfg["lon"])

    date_tag = f"Last image: {last_image_date}" if last_image_date else "Sentinel-2 L2A · Live GEE"
    st.markdown(f"""<div class="panel" style="margin-bottom:0;overflow:hidden;"><div class="panel-head">
        <span class="panel-label">MAP: {map_title} — Water Turbidity & Vegetation</span>
        <span class="meta-tag">Sentinel-2 L2A · {date_tag}</span></div></div>""", unsafe_allow_html=True)

    geo_map = folium.Map(
        location=[4.2, 101.8],
        zoom_start=8, control_scale=True,
        tiles="https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png",
        attr="© OpenStreetMap contributors © CARTO",
    )

    if gee_error and not ndti_url and not ndvi_url:
        st.markdown(f"""<div style="padding:8px 16px;background:{t['amber']}22;border-left:3px solid {t['amber']};
            font-size:12px;color:{t['text3']};margin-bottom:4px;">
            Live imagery unavailable — {gee_error}</div>""", unsafe_allow_html=True)
    else:
        if ndvi_url:
            folium.TileLayer(tiles=ndvi_url, attr="GEE", name="Vegetation (NDVI)",
                             overlay=True, opacity=0.85).add_to(geo_map)
        if ndti_url:
            folium.TileLayer(tiles=ndti_url, attr="GEE", name="Turbidity (NDTI)",
                             overlay=True, opacity=0.9).add_to(geo_map)

    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png",
        attr="© CARTO", overlay=True, control=False,
    ).add_to(geo_map)

    # Zone markers — one dot per zone in all_zones
    for _, row in all_zones.iterrows():
        dot_color = {"critical": "#dc2626", "warning": "#d97706", "normal": "#16a34a"}.get(row["status"], "#2563eb")
        val_label = f"NDTI {row['turbidity']}" if value_col == "turbidity" else f"NDVI {row['ndvi']}"
        sec_val   = row['ndwi'] if value_col == "turbidity" else row['ndre']
        sec_label = f"{'NDWI' if value_col == 'turbidity' else 'NDRE'}: {sec_val if pd.notna(sec_val) else 'N/A'}"
        popup_html = (
            f"<div style='font-family:sans-serif;padding:8px 10px;min-width:180px;'>"
            f"<b style='font-size:13px;color:#0f172a;'>{row['name']}</b><br>"
            f"<span style='color:#555;font-size:11px;'>{val_label}</span><br>"
            f"<span style='color:#555;font-size:11px;'>{sec_label}</span><br>"
            f"<span style='color:#555;font-size:11px;'>Trend: {row['trend']}</span><br>"
            f"<span style='font-size:12px;font-weight:700;color:{dot_color};'>{row['status'].upper()}</span>"
            f"</div>"
        )
        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=folium.Tooltip(popup_html, sticky=False),
            icon=folium.DivIcon(
                html=f"""<div style="
                    width:18px;height:18px;border-radius:50%;
                    background:{dot_color};border:3px solid #fff;
                    box-shadow:0 2px 8px rgba(0,0,0,0.4),0 0 0 4px {dot_color}44;
                "></div>""",
                icon_size=(18, 18), icon_anchor=(9, 9),
            ),
        ).add_to(geo_map)

    st_folium(geo_map, height=520, use_container_width=True)
    st.markdown(f"""
    <div style="display:flex;gap:20px;margin-top:12px;">
        <div style="flex:1;">
            <div style="background:linear-gradient(to right,#1a237e,#0288d1,#4dd0e1,#fff176,#ff8f00,#b71c1c);
                height:10px;border-radius:6px;"></div>
            <div style="display:flex;justify-content:space-between;margin-top:4px;">
                <span style="font-size:10px;color:{t['text4']};">Clean water (NDTI −0.10)</span>
                <span style="font-size:10px;color:{t['text4']};font-weight:600;">Turbidity Index</span>
                <span style="font-size:10px;color:{t['text4']};">Turbid (0.35)</span>
            </div>
        </div>
        <div style="flex:1;">
            <div style="background:linear-gradient(to right,#a50026,#f46d43,#fee08b,#d9ef8b,#66bd63,#1a9850,#006837);
                height:10px;border-radius:6px;"></div>
            <div style="display:flex;justify-content:space-between;margin-top:4px;">
                <span style="font-size:10px;color:{t['text4']};">Stressed (NDVI 0.10)</span>
                <span style="font-size:10px;color:{t['text4']};font-weight:600;">Vegetation Index</span>
                <span style="font-size:10px;color:{t['text4']};">Healthy (0.85)</span>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

with details_col:
    st.markdown(f"""<div class="panel"><div class="panel-body"><div class="panel-label" style="margin-bottom:16px;">DISTRIBUTION: Zone Health</div>""", unsafe_allow_html=True)
    for label, count, color in [("Normal", num_normal, t['green']), ("Warning", num_warning, t['amber']), ("Critical", num_critical, t['red'])]:
        percentage = round((count / total_zones) * 100) if total_zones > 0 else 0
        st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:12.5px;color:{t['text2']};">{label}</span>
            <span style="font-size:12.5px;color:{color};font-weight:600;font-family:'JetBrains Mono',monospace;">{count} <span style="color:{t['text4']};font-weight:400;">({percentage}%)</span></span></div>
        <div class="dbar-track"><div class="dbar-fill" style="width:{percentage}%;background:{color};"></div></div>""", unsafe_allow_html=True)
    st.markdown(f"""<div style="border-top:1px solid {t['border']};padding-top:14px;margin-top:4px;display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:11px;color:{t['text4']};">Showing / Total</span>
            <span style="font-size:24px;font-weight:800;color:{t['text1']};font-family:'JetBrains Mono',monospace;">{filtered_count}<span style="font-size:14px;color:{t['text4']};font-weight:400;">/{total_zones}</span></span>
        </div></div></div>""", unsafe_allow_html=True)

    st.markdown("")
    st.markdown(f'<p class="sb-label" style="margin-top:8px;">Zone Details</p>', unsafe_allow_html=True)
    if filtered_zones.empty:
        st.markdown(f'<div style="color:{t["text4"]};font-size:12px;padding:12px 0;">No zones to display</div>', unsafe_allow_html=True)
    else:
        STATUS_STYLES = {
            "critical": {"card": "zcard-crit", "color": "c-r", "dot": "dot-r"},
            "warning":  {"card": "zcard-warn", "color": "c-y", "dot": "dot-y"},
            "normal":   {"card": "",            "color": "c-g", "dot": "dot-g"},
        }
        for _, zone_row in filtered_zones.iterrows():
            zone_style   = STATUS_STYLES[zone_row["status"]]
            zone_value   = zone_row[value_col]
            trend_arrow  = {"rising": "↑", "falling": "↓"}.get(zone_row["trend"], "→")
            detail_label = f"NDWI: {zone_row['ndwi']}" if value_col == "turbidity" else f"NDRE: {zone_row['ndre']}"
            st.markdown(f"""<div class="zcard {zone_style['card']}"><div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div><div class="zname"><span class="dot {zone_style['dot']}"></span>{zone_row['name']}</div><div class="zmeta">{detail_label}</div></div>
                <div style="text-align:right;"><div class="zval {zone_style['color']}">{zone_value}</div><div style="font-size:10px;color:{t['text4']};">{trend_arrow} {zone_row['trend']}</div></div></div></div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# ZONE INSPECTION — dropdown drill-down per zone
# ══════════════════════════════════════════════════════════════

st.markdown("")

# Build zone list for current module only
_module_type = "hydro" if view_choice == "Hydro Reservoir" else "agri"
_all_monitored = [
    {"zone_name": RESERVOIR_CONFIG["name"], "lat": RESERVOIR_CONFIG["lat"],
     "lon": RESERVOIR_CONFIG["lon"], "zone_type": "hydro", "added_at": ""},
    {"zone_name": FARM_CONFIG["name"], "lat": FARM_CONFIG["lat"],
     "lon": FARM_CONFIG["lon"], "zone_type": "agri", "added_at": ""},
] + [z for z in saved_zones if z["zone_name"] not in
     (RESERVOIR_CONFIG["name"], FARM_CONFIG["name"])]

_module_zones = [z for z in _all_monitored
                 if z["zone_type"] in (_module_type, "both")]
_zone_names   = ["— select a zone to inspect —"] + [z["zone_name"] for z in _module_zones]
_selected     = st.selectbox("Inspect a zone", _zone_names,
                             label_visibility="collapsed", key="zone_inspect_select")

if _selected and _selected != "— select a zone to inspect —":
    _zone_dict = next((z for z in _module_zones if z["zone_name"] == _selected), None)
    if _zone_dict:
        with st.expander(f"Zone Detail — {_selected}", expanded=True):
            render_zone_dashboard(_zone_dict, t)

# ══════════════════════════════════════════════════════════════
# ALERTS PANEL
# ══════════════════════════════════════════════════════════════

st.markdown("")
critical_alerts  = [alert for alert in filtered_alerts if alert["severity"] == "critical"]
alerts_header    = f"ALERTS: Active ({len(filtered_alerts)})"
if critical_alerts:
    alerts_header += f" · {len(critical_alerts)} critical"
st.markdown(f"""<div class="panel" style="overflow:hidden;"><div class="panel-head">
    <span class="panel-label">{alerts_header}</span><span class="meta-tag">Today, {datetime.datetime.now().strftime("%d %b %Y")}</span></div>""", unsafe_allow_html=True)
if filtered_alerts:
    for alert in filtered_alerts:
        alert_css_class = "alrt-crit" if alert["severity"] == "critical" else "alrt-warn"
        st.markdown(f"""<div class="alrt {alert_css_class}"><div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="alrt-zone">{alert['zone']}</span><span class="alrt-time">{alert['time']}</span></div>
            <div class="alrt-msg">{alert['message']}</div></div>""", unsafe_allow_html=True)
else:
    st.markdown(f"""<div style="padding:28px;text-align:center;color:{t['text4']};font-size:12px;">No alerts for the current filter</div>""", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════

st.markdown("")
st.markdown(f"""<div style="text-align:center;padding:24px 0 16px;border-top:1px solid {t['border']};margin-top:24px;">
    <span style="font-size:11px;color:{t['text4']};">NextGen Spark Sdn Bhd · EO Monitoring Prototype v1.0 · Powered by Sentinel-2 & Google Earth Engine</span></div>""", unsafe_allow_html=True)
