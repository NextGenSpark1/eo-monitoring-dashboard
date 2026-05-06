

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from database import (
    read_hydro_data,
    read_agri_data,
    remove_saved_zone
)
from gee_logic import initialize_gee


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_zone_dashboard(zone: dict, t: dict = None):
    """
    Render a complete dashboard for a saved zone.
    t: theme dict from app.py (LIGHT or DARK). Falls back to neutral defaults if not passed.
    """
    _t = t or {
        "border": "#e2e8f0", "text1": "#0f172a", "text2": "#1e293b",
        "text3": "#475569", "text4": "#94a3b8", "green": "#16a34a",
        "amber": "#d97706", "red": "#dc2626", "bg_card": "#ffffff",
    }

    zone_name = zone["zone_name"]
    lat       = zone["lat"]
    lon       = zone["lon"]
    zone_type = zone["zone_type"]
    added_at  = zone.get("added_at", "")

    # ── Header ───────────────────────────────────────────
    col_title, col_remove = st.columns([5, 1])

    with col_title:
        type_label = "Hydro" if zone_type == "hydro" else "Agriculture" if zone_type == "agri" else "Hydro + Agri"
        st.markdown(
            f"""<div style="margin-bottom:4px;">
                <span style="font-size:17px;font-weight:700;color:{_t['text1']};">{zone_name}</span>
                <span style="font-size:11px;color:{_t['text4']};margin-left:10px;">{type_label}</span>
            </div>
            <div style="font-size:11px;color:{_t['text3']};">
                {lat:.4f}, {lon:.4f} · Added: {added_at[:10] if added_at else 'N/A'}
            </div>""",
            unsafe_allow_html=True
        )

    with col_remove:
        if st.button("Remove", key=f"remove_{zone_name}", help=f"Remove {zone_name} from watchlist"):
            _handle_remove(zone_name)
            return

    st.markdown(f'<hr style="border:none;border-top:1px solid {_t["border"]};margin:12px 0 16px;">', unsafe_allow_html=True)

    # ── Load data from Supabase ───────────────────────────
    hydro_df = pd.DataFrame()
    agri_df  = pd.DataFrame()

    if zone_type in ["hydro", "both"]:
        hydro_df = read_hydro_data(zone=zone_name, months=24)

    if zone_type in ["agri", "both"]:
        agri_df = read_agri_data(zone=zone_name, months=24)

    has_hydro = not hydro_df.empty
    has_agri  = not agri_df.empty

    if not has_hydro and not has_agri:
        st.markdown(
            f'<div style="padding:16px;background:{_t["amber"]}18;border-left:3px solid {_t["amber"]};'
            f'font-size:13px;color:{_t["text2"]};border-radius:4px;">No data found for <b>{zone_name}</b> yet. '
            f'Go to Live Lookup, search this zone and save it first.</div>',
            unsafe_allow_html=True
        )
        return

    # ── KPI Row ───────────────────────────────────────────
    st.markdown(f'<p class="sb-label" style="margin-bottom:8px;">Current Status</p>', unsafe_allow_html=True)
    _render_kpis(hydro_df, agri_df, zone_type, _t)

    st.markdown(f'<hr style="border:none;border-top:1px solid {_t["border"]};margin:16px 0;">', unsafe_allow_html=True)

    # ── Charts + Map side by side ─────────────────────────
    col_charts, col_map = st.columns([1, 1])

    with col_charts:
        st.markdown(f'<p class="sb-label" style="margin-bottom:8px;">Trends</p>', unsafe_allow_html=True)
        _render_trend_charts(hydro_df, agri_df, zone_type, zone_name, _t)

    with col_map:
        st.markdown(f'<p class="sb-label" style="margin-bottom:8px;">Live Satellite Map</p>', unsafe_allow_html=True)
        _render_map(lat, lon, zone_type, zone_name)

    st.markdown(f'<hr style="border:none;border-top:1px solid {_t["border"]};margin:16px 0;">', unsafe_allow_html=True)

    # ── Alert History ─────────────────────────────────────
    st.markdown(f'<p class="sb-label" style="margin-bottom:8px;">Alert History</p>', unsafe_allow_html=True)
    _render_alert_history(hydro_df, agri_df, zone_type, _t)

    # ── Raw Data ──────────────────────────────────────────
    with st.expander("View raw data"):
        if has_hydro:
            st.dataframe(hydro_df, use_container_width=True)
        if has_agri:
            st.dataframe(agri_df, use_container_width=True)


# ============================================================
# KPI PANELS
# ============================================================

def _fmt(val, decimals=4):
    """Format a numeric value safely — returns 'N/A' for None or NaN."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    return f"{val:.{decimals}f}"


def _render_kpis(hydro_df, agri_df, zone_type, t):
    """Render KPI metric cards with delta from previous month."""

    if zone_type in ["hydro", "both"] and not hydro_df.empty:
        latest = hydro_df.iloc[-1]
        prev   = hydro_df.iloc[-2] if len(hydro_df) > 1 else latest

        alert_level = latest.get("alert_level", "normal")
        alert_label = {"critical": "CRITICAL", "warning": "WARNING", "normal": "NORMAL"}.get(alert_level, "UNKNOWN")
        alert_color = {"critical": t["red"], "warning": t["amber"], "normal": t["green"]}.get(alert_level, t["text4"])

        c1, c2, c3, c4 = st.columns(4)

        ndti_now   = latest.get("ndti_mean")
        ndti_prev  = prev.get("ndti_mean")
        ndti_ok    = ndti_now is not None and not pd.isna(ndti_now)
        ndti_delta = round(ndti_now - ndti_prev, 4) if (ndti_ok and ndti_prev is not None and not pd.isna(ndti_prev)) else None

        c1.metric("NDTI (Turbidity)", _fmt(ndti_now),
                  delta=f"{ndti_delta:+.4f}" if ndti_delta is not None else None,
                  delta_color="inverse")
        c2.metric("NDWI (Water)",     _fmt(latest.get("ndwi_mean")))
        c3.metric("Cloud Cover",      f"{latest.get('cloud_pct')}%" if latest.get("cloud_pct") else "N/A")
        c4.metric("Alert Status",     alert_label)

        if latest.get("last_clear_view"):
            st.markdown(f'<div style="font-size:11px;color:{t["text4"]};margin-top:4px;">Last clear view: {latest["last_clear_view"]}</div>',
                        unsafe_allow_html=True)

    if zone_type in ["agri", "both"] and not agri_df.empty:
        latest = agri_df.iloc[-1]
        prev   = agri_df.iloc[-2] if len(agri_df) > 1 else latest

        alert_level = latest.get("alert_level", "normal")
        alert_label = {"critical": "CRITICAL", "warning": "WARNING", "normal": "NORMAL"}.get(alert_level, "UNKNOWN")

        c1, c2, c3, c4 = st.columns(4)

        ndvi_now   = latest.get("ndvi_mean")
        ndvi_prev  = prev.get("ndvi_mean")
        ndvi_ok    = ndvi_now is not None and not pd.isna(ndvi_now)
        ndvi_delta = round(ndvi_now - ndvi_prev, 4) if (ndvi_ok and ndvi_prev is not None and not pd.isna(ndvi_prev)) else None

        c1.metric("NDVI (Vegetation)", _fmt(ndvi_now),
                  delta=f"{ndvi_delta:+.4f}" if ndvi_delta is not None else None,
                  delta_color="normal")
        c2.metric("NDRE (Chlorophyll)", _fmt(latest.get("ndre_mean")))
        c3.metric("Cloud Cover",        f"{latest.get('cloud_pct')}%" if latest.get("cloud_pct") else "N/A")
        c4.metric("Alert Status",       alert_label)


# ============================================================
# TREND CHARTS
# ============================================================

def _render_trend_charts(hydro_df, agri_df, zone_type, zone_name, t):
    """Render Plotly time series charts for NDTI and/or NDVI."""

    if zone_type in ["hydro", "both"] and not hydro_df.empty:
        df = hydro_df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        fig = go.Figure()

        # NDTI line
        fig.add_trace(go.Scatter(
            x    = df["date"],
            y    = df["ndti_mean"],
            mode = "lines+markers",
            name = "NDTI",
            line = dict(color="#00B4D8", width=2),
            marker = dict(size=6)
        ))

        # Threshold lines
        fig.add_hline(
            y=0.05, line_dash="dash", line_color="red",
            annotation_text="🔴 Critical (0.05)",
            annotation_position="bottom right"
        )
        fig.add_hline(
            y=0.0, line_dash="dash", line_color="orange",
            annotation_text="🟡 Warning (0.0)",
            annotation_position="bottom right"
        )

        # Shade critical zone
        fig.add_hrect(
            y0=0.05, y1=df["ndti_mean"].max() + 0.02 if not df.empty else 0.2,
            fillcolor="red", opacity=0.05, line_width=0
        )

        fig.update_layout(
            title      = f"💧 Turbidity Trend — {zone_name}",
            xaxis_title= "Date",
            yaxis_title= "NDTI Value",
            height     = 280,
            margin     = dict(t=40, b=20, l=20, r=20),
            showlegend = False
        )
        st.plotly_chart(fig, use_container_width=True)

        # Trend direction
        if len(df) >= 3:
            first3 = df.head(3)["ndti_mean"].mean()
            last3  = df.tail(3)["ndti_mean"].mean()
            change = last3 - first3
            if change > 0.02:
                st.error(f"📈 Turbidity increasing (+{change:.4f}) — dredging may be needed")
            elif change < -0.02:
                st.success(f"📉 Turbidity decreasing ({change:.4f}) — conditions improving")
            else:
                st.info(f"➡️ Turbidity stable (change: {change:.4f})")

    if zone_type in ["agri", "both"] and not agri_df.empty:
        df = agri_df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x    = df["date"],
            y    = df["ndvi_mean"],
            mode = "lines+markers",
            name = "NDVI",
            line = dict(color="#38B000", width=2),
            marker = dict(size=6)
        ))

        if "ndre_mean" in df.columns and df["ndre_mean"].notna().any():
            fig.add_trace(go.Scatter(
                x    = df["date"],
                y    = df["ndre_mean"],
                mode = "lines+markers",
                name = "NDRE",
                line = dict(color="#70E000", width=2, dash="dot"),
                marker = dict(size=6)
            ))

        fig.add_hline(
            y=0.4, line_dash="dash", line_color="orange",
            annotation_text="🟡 Warning (0.4)"
        )
        fig.add_hline(
            y=0.2, line_dash="dash", line_color="red",
            annotation_text="🔴 Critical (0.2)"
        )

        fig.update_layout(
            title      = f"🌴 Vegetation Trend — {zone_name}",
            xaxis_title= "Date",
            yaxis_title= "Index Value",
            height     = 280,
            margin     = dict(t=40, b=20, l=20, r=20),
            showlegend = True
        )
        st.plotly_chart(fig, use_container_width=True)

        if len(df) >= 3:
            first3 = df.head(3)["ndvi_mean"].mean()
            last3  = df.tail(3)["ndvi_mean"].mean()
            change = last3 - first3
            if change < -0.05:
                st.error(f"📉 Vegetation declining ({change:.4f}) — investigate crop stress")
            elif change > 0.05:
                st.success(f"📈 Vegetation improving (+{change:.4f}) — healthy growth")
            else:
                st.info(f"➡️ Vegetation stable (change: {change:.4f})")


# ============================================================
# LIVE MAP
# ============================================================

def _render_map(lat, lon, zone_type, zone_name):
    """Render live satellite map tile for the zone."""
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from dynamic_zone import get_live_map
    from streamlit_folium import st_folium

    with st.spinner("Loading satellite map..."):
        map_result = get_live_map(lat, lon, zone_type, zone_name=zone_name)

    if map_result["success"]:
        st_folium(map_result["map"], height=380, use_container_width=True)
        if map_result.get("last_clear"):
            st.caption(
                f"Last clear view: **{map_result['last_clear']}**  "
                f"Cloud: **{map_result['cloud_pct']}%**"
            )
    else:
        st.warning(
            f"Live map unavailable: {map_result['error']}  \n"
            f"Coordinates: `{lat}, {lon}`"
        )


# ============================================================
# ALERT HISTORY
# ============================================================

def _render_alert_history(hydro_df, agri_df, zone_type, t):
    """Show alert history timeline for this zone."""

    all_alerts = []

    if zone_type in ["hydro", "both"] and not hydro_df.empty:
        for _, row in hydro_df.iterrows():
            if row.get("alert_level") in ["warning", "critical"]:
                all_alerts.append({
                    "date":        row["date"],
                    "type":        "Hydro",
                    "alert_level": row["alert_level"],
                    "value":       f"NDTI: {_fmt(row.get('ndti_mean'))}"
                })

    if zone_type in ["agri", "both"] and not agri_df.empty:
        for _, row in agri_df.iterrows():
            if row.get("alert_level") in ["warning", "critical"]:
                all_alerts.append({
                    "date":        row["date"],
                    "type":        "Agri",
                    "alert_level": row["alert_level"],
                    "value":       f"NDVI: {_fmt(row.get('ndvi_mean'))}"
                })

    if not all_alerts:
        st.markdown(
            f'<div style="padding:12px 16px;background:{t["green"]}18;border-left:3px solid {t["green"]};'
            f'font-size:12px;color:{t["text3"]};border-radius:4px;">No alerts in monitoring history — all readings normal</div>',
            unsafe_allow_html=True
        )
        return

    alerts_df = pd.DataFrame(all_alerts)
    alerts_df = alerts_df.sort_values("date", ascending=False)

    for _, alert in alerts_df.iterrows():
        color = t["red"] if alert["alert_level"] == "critical" else t["amber"]
        st.markdown(
            f'<div style="font-size:12px;padding:4px 0;color:{t["text2"]};">'
            f'<span style="color:{color};font-weight:600;">{alert["alert_level"].upper()}</span>'
            f' · {alert["date"]} · {alert["type"]} · {alert["value"]}</div>',
            unsafe_allow_html=True
        )


# ============================================================
# REMOVE ZONE HANDLER
# ============================================================

def _handle_remove(zone_name: str):
    """Handle zone removal from watchlist."""
    try:
        remove_saved_zone(zone_name)
        st.success(f"✅ **{zone_name}** removed from watchlist")
        # Clear session state so tabs rebuild
        if "saved_zones" in st.session_state:
            del st.session_state["saved_zones"]
        st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to remove zone: {e}")
