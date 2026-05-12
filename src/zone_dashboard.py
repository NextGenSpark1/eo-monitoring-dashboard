

import streamlit as st
import pandas as pd
import altair as alt
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
                {lat:.4f}, {lon:.4f}
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
    """Render KPI cards matching dashboard style."""

    def _kpi_card(label, value, accent_color, tag_text=None, tag_class="tag-blue", delta=None, delta_inverse=False):
        if delta is not None:
            worse = delta > 0 if delta_inverse else delta < 0
            delta_color = t["red"] if worse else t["green"]
            arrow = "↑" if delta > 0 else "↓"
            delta_html = f'<div style="font-size:11px;color:{delta_color};margin-top:2px;">{arrow} {abs(delta):.4f}</div>'
        else:
            delta_html = ""
        tag_html = f'<span class="kpi-tag {tag_class}">{tag_text}</span>' if tag_text else ""
        return (
            f'<div class="kpi">'
            f'<div class="kpi-accent" style="background:{accent_color};"></div>'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-val">{value}</div>'
            f'{delta_html}{tag_html}'
            f'</div>'
        )

    if zone_type in ["hydro", "both"] and not hydro_df.empty:
        latest = hydro_df.iloc[-1]
        prev   = hydro_df.iloc[-2] if len(hydro_df) > 1 else latest

        alert  = latest.get("alert_level", "normal")
        ndti   = latest.get("ndti_mean")
        ndwi   = latest.get("ndwi_mean")
        cloud  = latest.get("cloud_pct")
        ndti_p = prev.get("ndti_mean")
        ndti_ok  = ndti is not None and not pd.isna(ndti)
        ndti_delta = round(ndti - ndti_p, 4) if (ndti_ok and ndti_p is not None and not pd.isna(ndti_p)) else None

        alert_color = {"critical": t["red"], "warning": t["amber"], "normal": t["green"]}.get(alert, t["text4"])
        alert_tag   = {"critical": "tag-red", "warning": "tag-amber", "normal": "tag-green"}.get(alert, "tag-blue")

        _cloud_html = _kpi_card("Cloud Cover", f"{cloud}%", t["text4"]) if cloud else ""
        st.markdown(f"""<div class="kpi-row">
            {_kpi_card("NDTI (Turbidity)", _fmt(ndti), t["blue"], delta=ndti_delta, delta_inverse=True)}
            {_kpi_card("NDWI (Water)", _fmt(ndwi) if (ndwi is not None and not pd.isna(ndwi) and ndwi != 0.0) else "—", t["blue"])}
            {_cloud_html}
            {_kpi_card("Alert Status", alert.upper(), alert_color, alert.capitalize(), alert_tag)}
        </div>""", unsafe_allow_html=True)

        if latest.get("last_clear_view"):
            st.markdown(f'<div style="font-size:11px;color:{t["text4"]};margin-top:4px;">Last clear view: {latest["last_clear_view"]}</div>',
                        unsafe_allow_html=True)

    if zone_type in ["agri", "both"] and not agri_df.empty:
        latest = agri_df.iloc[-1]
        prev   = agri_df.iloc[-2] if len(agri_df) > 1 else latest

        alert  = latest.get("alert_level", "normal")
        ndvi   = latest.get("ndvi_mean")
        ndre   = latest.get("ndre_mean")
        cloud  = latest.get("cloud_pct")
        ndvi_p = prev.get("ndvi_mean")
        ndvi_ok  = ndvi is not None and not pd.isna(ndvi)
        ndvi_delta = round(ndvi - ndvi_p, 4) if (ndvi_ok and ndvi_p is not None and not pd.isna(ndvi_p)) else None

        alert_color = {"critical": t["red"], "warning": t["amber"], "normal": t["green"]}.get(alert, t["text4"])
        alert_tag   = {"critical": "tag-red", "warning": "tag-amber", "normal": "tag-green"}.get(alert, "tag-blue")

        st.markdown(f"""<div class="kpi-row">
            {_kpi_card("NDVI (Vegetation)", _fmt(ndvi), t["green"], delta=ndvi_delta, delta_inverse=False)}
            {_kpi_card("NDRE (Chlorophyll)", _fmt(ndre), t["green"])}
            {_kpi_card("Cloud Cover",        f"{cloud}%" if cloud else "N/A", t["text4"])}
            {_kpi_card("Alert Status",       alert.upper(), alert_color, alert.capitalize(), alert_tag)}
        </div>""", unsafe_allow_html=True)


# ============================================================
# TREND CHARTS
# ============================================================

def _render_trend_charts(hydro_df, agri_df, zone_type, zone_name, t):
    """Render Altair trend charts matching main dashboard style."""

    def _axis_x():
        return alt.X("date:T", title=None,
            axis=alt.Axis(format="%b '%y", tickCount="month",
                          labelColor=t["text4"], labelFontSize=11, labelFont="Inter",
                          tickColor="transparent", domainColor=t["border"],
                          labelAngle=0, labelPadding=10))

    def _axis_y():
        return alt.Y("Value:Q", title=None,
            axis=alt.Axis(labelColor=t["text4"], labelFontSize=10, labelFont="JetBrains Mono",
                          gridColor=t["chart_grid"], tickColor="transparent", domainColor="transparent"))

    def _threshold_rule(y_val, color):
        return alt.Chart(pd.DataFrame({"y": [y_val]})).mark_rule(
            strokeDash=[4, 4], color=color, opacity=0.55
        ).encode(y=alt.Y("y:Q"))

    def _trend_note(df, col, t):
        valid = df[col].dropna()
        if len(valid) < 3:
            return
        change = valid.tail(3).mean() - valid.head(3).mean()
        if abs(change) < 0.02:
            msg, bg, bdr = f"Stable (change: {change:+.4f})", t["blue_bg"], t["blue_bdr"]
        elif (col == "ndti_mean" and change > 0) or (col != "ndti_mean" and change < 0):
            msg, bg, bdr = f"Worsening ({change:+.4f})", t["red_bg"], t["red_bdr"]
        else:
            msg, bg, bdr = f"Improving ({change:+.4f})", t["green_bg"], t["green_bdr"]
        st.markdown(f'<div style="font-size:11px;padding:6px 12px;background:{bg};border-left:3px solid {bdr};'
                    f'border-radius:4px;color:{t["text3"]};margin-top:6px;">{msg}</div>',
                    unsafe_allow_html=True)

    if zone_type in ["hydro", "both"] and not hydro_df.empty:
        df = hydro_df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").dropna(subset=["ndti_mean"])
        df = df.rename(columns={"ndti_mean": "Value"})

        base   = alt.Chart(df).encode(x=_axis_x(), y=_axis_y(),
                     tooltip=[alt.Tooltip("date:T", title="Date", format="%d %b %Y"),
                              alt.Tooltip("Value:Q", title="NDTI", format=".4f")])
        line   = base.mark_line(strokeWidth=2.5, color=t["blue"], opacity=0.9)
        points = base.mark_circle(size=50, color=t["blue"], opacity=1)

        chart = (line + points + _threshold_rule(0.05, t["red"]) + _threshold_rule(0.0, t["amber"])) \
            .properties(height=260, background="transparent") \
            .configure(font="Inter").configure_view(strokeWidth=0)
        st.altair_chart(chart, use_container_width=True)
        _trend_note(hydro_df, "ndti_mean", t)

    if zone_type in ["agri", "both"] and not agri_df.empty:
        df = agri_df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        frames = []
        if "ndvi_mean" in df.columns and df["ndvi_mean"].notna().any():
            tmp = df[["date", "ndvi_mean"]].dropna().rename(columns={"ndvi_mean": "Value"})
            tmp["Index"] = "NDVI"
            frames.append(tmp)
        if "ndre_mean" in df.columns and df["ndre_mean"].notna().any():
            tmp = df[["date", "ndre_mean"]].dropna().rename(columns={"ndre_mean": "Value"})
            tmp["Index"] = "NDRE"
            frames.append(tmp)

        if frames:
            long_df = pd.concat(frames)
            color_scale = alt.Scale(domain=["NDVI", "NDRE"], range=[t["green"], "#70E000"])
            base = alt.Chart(long_df).encode(
                x=_axis_x(), y=_axis_y(),
                color=alt.Color("Index:N", scale=color_scale,
                    legend=alt.Legend(orient="bottom", labelColor=t["text3"],
                                      labelFontSize=11, titleColor=t["text4"], symbolSize=60)),
                tooltip=[alt.Tooltip("date:T", title="Date", format="%d %b %Y"),
                         alt.Tooltip("Index:N", title="Index"),
                         alt.Tooltip("Value:Q", title="Value", format=".4f")]
            )
            line   = base.mark_line(strokeWidth=2.5, opacity=0.9)
            points = base.mark_circle(size=50, opacity=1)

            chart = (line + points + _threshold_rule(0.4, t["amber"]) + _threshold_rule(0.2, t["red"])) \
                .properties(height=260, background="transparent") \
                .configure(font="Inter").configure_view(strokeWidth=0)
            st.altair_chart(chart, use_container_width=True)
        _trend_note(agri_df, "ndvi_mean", t)


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
