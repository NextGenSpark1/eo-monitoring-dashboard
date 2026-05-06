

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

def render_zone_dashboard(zone: dict):
    """
    Render a complete dashboard for a saved zone.
    Called by app.py for each tab in the watchlist.

    Parameters:
        zone : dict from saved_zones table containing:
               zone_name, lat, lon, zone_type, added_at
    """

    zone_name = zone["zone_name"]
    lat       = zone["lat"]
    lon       = zone["lon"]
    zone_type = zone["zone_type"]
    added_at  = zone.get("added_at", "")

    # ── Header ───────────────────────────────────────────
    col_title, col_remove = st.columns([5, 1])

    with col_title:
        emoji = "💧" if zone_type == "hydro" else "🌴" if zone_type == "agri" else "🌍"
        st.subheader(f"{emoji} {zone_name}")
        st.caption(
            f"📍 `{lat}, {lon}` · "
            f"Monitoring: **{zone_type.upper()}** · "
            f"Added: {added_at[:10] if added_at else 'N/A'}"
        )

    with col_remove:
        st.write("")  # spacing
        if st.button(
            "🗑️ Remove",
            key  = f"remove_{zone_name}",
            help = f"Remove {zone_name} from watchlist"
        ):
            _handle_remove(zone_name)
            return   # Stop rendering this zone

    st.divider()

    # ── Load data from Supabase ───────────────────────────
    hydro_df = pd.DataFrame()
    agri_df  = pd.DataFrame()

    if zone_type in ["hydro", "both"]:
        hydro_df = read_hydro_data(zone=zone_name, months=24)

    if zone_type in ["agri", "both"]:
        agri_df = read_agri_data(zone=zone_name, months=24)

    # Check if any data exists
    has_hydro = not hydro_df.empty
    has_agri  = not agri_df.empty

    if not has_hydro and not has_agri:
        st.warning(
            f"⚠️ No data found for **{zone_name}** in the database yet.  \n"
            f"Go to **🔍 Search Any Location** tab, search for this zone, "
            f"analyse it and save the data first."
        )
        return

    # ── KPI Row ───────────────────────────────────────────
    st.markdown("### 📊 Current Status")
    _render_kpis(hydro_df, agri_df, zone_type)

    st.divider()

    # ── Charts + Map side by side ─────────────────────────
    col_charts, col_map = st.columns([1, 1])

    with col_charts:
        st.markdown("### 📈 Trends")
        _render_trend_charts(hydro_df, agri_df, zone_type, zone_name)

    with col_map:
        st.markdown("### 🗺️ Live Satellite Map")
        _render_map(lat, lon, zone_type, zone_name)

    st.divider()

    # ── Alert History ─────────────────────────────────────
    st.markdown("### 🚨 Alert History")
    _render_alert_history(hydro_df, agri_df, zone_type)

    # ── Raw Data ──────────────────────────────────────────
    with st.expander("📋 View raw data"):
        if has_hydro:
            st.write("**Hydro Data:**")
            st.dataframe(hydro_df, use_container_width=True)
        if has_agri:
            st.write("**Agri Data:**")
            st.dataframe(agri_df, use_container_width=True)


# ============================================================
# KPI PANELS
# ============================================================

def _render_kpis(hydro_df, agri_df, zone_type):
    """Render KPI metric cards with delta from previous month."""

    if zone_type in ["hydro", "both"] and not hydro_df.empty:
        latest = hydro_df.iloc[-1]
        prev   = hydro_df.iloc[-2] if len(hydro_df) > 1 else latest

        alert_emoji = {
            "critical": "🔴 CRITICAL",
            "warning":  "🟡 WARNING",
            "normal":   "🟢 NORMAL"
        }.get(latest.get("alert_level", ""), "⚪ UNKNOWN")

        c1, c2, c3, c4 = st.columns(4)

        ndti_now  = latest.get("ndti_mean")
        ndti_prev = prev.get("ndti_mean")
        ndti_delta = round(ndti_now - ndti_prev, 4) if ndti_now and ndti_prev else None

        c1.metric(
            "💧 NDTI (Turbidity)",
            f"{ndti_now:.4f}" if ndti_now else "N/A",
            delta        = f"{ndti_delta:+.4f}" if ndti_delta else None,
            delta_color  = "inverse"   # higher NDTI = worse = red
        )
        c2.metric(
            "🌊 NDWI (Water)",
            f"{latest.get('ndwi_mean'):.4f}" if latest.get("ndwi_mean") else "N/A"
        )
        c3.metric(
            "☁️ Cloud Cover",
            f"{latest.get('cloud_pct')}%" if latest.get("cloud_pct") else "N/A"
        )
        c4.metric("⚠️ Alert Status", alert_emoji)

        if latest.get("last_clear_view"):
            st.caption(f"Last clear satellite view: **{latest['last_clear_view']}**")

    if zone_type in ["agri", "both"] and not agri_df.empty:
        latest = agri_df.iloc[-1]
        prev   = agri_df.iloc[-2] if len(agri_df) > 1 else latest

        alert_emoji = {
            "critical": "🔴 CRITICAL",
            "warning":  "🟡 WARNING",
            "normal":   "🟢 NORMAL"
        }.get(latest.get("alert_level", ""), "⚪ UNKNOWN")

        c1, c2, c3, c4 = st.columns(4)

        ndvi_now   = latest.get("ndvi_mean")
        ndvi_prev  = prev.get("ndvi_mean")
        ndvi_delta = round(ndvi_now - ndvi_prev, 4) if ndvi_now and ndvi_prev else None

        c1.metric(
            "🌿 NDVI (Vegetation)",
            f"{ndvi_now:.4f}" if ndvi_now else "N/A",
            delta       = f"{ndvi_delta:+.4f}" if ndvi_delta else None,
            delta_color = "normal"   # higher NDVI = better = green
        )
        c2.metric(
            "🍃 NDRE (Chlorophyll)",
            f"{latest.get('ndre_mean'):.4f}" if latest.get("ndre_mean") else "N/A"
        )
        c3.metric(
            "☁️ Cloud Cover",
            f"{latest.get('cloud_pct')}%" if latest.get("cloud_pct") else "N/A"
        )
        c4.metric("⚠️ Alert Status", alert_emoji)


# ============================================================
# TREND CHARTS
# ============================================================

def _render_trend_charts(hydro_df, agri_df, zone_type, zone_name):
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

def _render_alert_history(hydro_df, agri_df, zone_type):
    """Show alert history timeline for this zone."""

    all_alerts = []

    if zone_type in ["hydro", "both"] and not hydro_df.empty:
        for _, row in hydro_df.iterrows():
            if row.get("alert_level") in ["warning", "critical"]:
                all_alerts.append({
                    "date":        row["date"],
                    "type":        "💧 Hydro",
                    "alert_level": row["alert_level"],
                    "value":       f"NDTI: {row.get('ndti_mean', 'N/A')}"
                })

    if zone_type in ["agri", "both"] and not agri_df.empty:
        for _, row in agri_df.iterrows():
            if row.get("alert_level") in ["warning", "critical"]:
                all_alerts.append({
                    "date":        row["date"],
                    "type":        "🌴 Agri",
                    "alert_level": row["alert_level"],
                    "value":       f"NDVI: {row.get('ndvi_mean', 'N/A')}"
                })

    if not all_alerts:
        st.success("✅ No alerts in the monitoring history — all readings normal")
        return

    # Sort by date descending
    alerts_df = pd.DataFrame(all_alerts)
    alerts_df = alerts_df.sort_values("date", ascending=False)

    # Color code
    for _, alert in alerts_df.iterrows():
        emoji = "🔴" if alert["alert_level"] == "critical" else "🟡"
        st.markdown(
            f"{emoji} **{alert['date']}** — {alert['type']} "
            f"**{alert['alert_level'].upper()}** — {alert['value']}"
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
