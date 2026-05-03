"""
================================================================================
src/dynamic_zone.py
================================================================================
Developer  : Mohamed Nawran (AI Platform Engineering)
             Habiba Hassan (AI Analytics & Visualization)
Description: Live GEE processing for ANY coordinates the client enters.
             Works with geocoder.py to form the complete dynamic zone feature.

Flow:
    Client enters location
          ↓
    geocoder.py resolves to lat/lon
          ↓
    dynamic_zone.py processes via GEE (this file)
          ↓
    Returns NDTI/NDVI results + map tile
          ↓
    dashboard displays live results
          ↓
    client saves to Supabase if they want

Key design decisions:
    - diskcache used so same location never processed twice
    - works for hydro (NDTI/NDWI) and agri (NDVI/NDRE)
    - returns everything dashboard needs in one call
    - gracefully handles cloud cover and missing data
================================================================================
"""

import ee
import diskcache as dc
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import streamlit as st


sys.path.insert(0, os.path.dirname(__file__))
from gee_logic import (
    initialize_gee,
    load_sentinel2,
    compute_ndti,
    compute_ndwi,
    compute_ndvi,
    compute_ndre,
    extract_stats,
    compute_alert_level
)
from geo_service import detect_and_resolve, get_suggestions

# ============================================================
# CACHE SETUP
# ============================================================

CACHE_DIR = ".cache/dynamic_zones"
CACHE_TTL = 60 * 60 * 24 * 3   # 3 days — fresh enough for demo
cache     = dc.Cache(CACHE_DIR)


# ============================================================
# CORE FUNCTION — ANALYSE ANY LOCATION
# ============================================================

def analyse_location(
    lat:        float,
    lon:        float,
    zone_name:  str,
    zone_type:  str,   # "hydro" | "agri" | "both"
    months:     int  = 12,
    buffer_m:   int  = 2000
) -> dict:
    """
    Full GEE analysis for any coordinates the client provides.
    Results cached — same location is instant on second call.

    Parameters:
        lat       : float — latitude
        lon       : float — longitude
        zone_name : str   — name client gave this location
        zone_type : str   — "hydro", "agri", or "both"
        months    : int   — how many months of history to process
        buffer_m  : int   — buffer radius in metres around the point

    Returns:
        dict containing:
            success      : bool
            zone_name    : str
            lat, lon     : float
            zone_type    : str
            hydro_data   : list of dicts (if hydro or both)
            agri_data    : list of dicts (if agri or both)
            latest_hydro : dict — most recent hydro reading
            latest_agri  : dict — most recent agri reading
            map_info     : dict — info for geemap rendering
            summary      : dict — KPI values for dashboard
            error        : str or None
    """

    # Build cache key from all parameters
    cache_key = f"zone_{lat}_{lon}_{zone_type}_{months}_{buffer_m}"

    # Check cache first
    cached = cache.get(cache_key)
    if cached is not None:
        print(f"⚡ Cache hit for ({lat}, {lon}) — instant load")
        cached["from_cache"] = True
        return cached

    print(f"🛰️  Processing new location: {zone_name} ({lat}, {lon})")
    print(f"   Zone type : {zone_type}")
    print(f"   History   : {months} months")
    print(f"   Buffer    : {buffer_m}m")

    try:
        initialize_gee()

        # Build geometry — point + buffer + bounding box
        geometry = (
            ee.Geometry.Point([lon, lat])
            .buffer(buffer_m)
            .bounds()
        )

        # Build monthly date windows
        end_date   = datetime.now()
        start_date = end_date - timedelta(days=30 * months)
        date_windows = _build_date_windows(start_date, end_date)

        hydro_records = []
        agri_records  = []

        print(f"   Processing {len(date_windows)} monthly windows...")

        for start, end in date_windows:
            image, cloud_pct, last_clear = load_sentinel2(
                geometry, start, end, cloud_threshold=25
            )

            if image is None:
                continue

            # Process hydro indices
            if zone_type in ["hydro", "both"]:
                ndti_s = extract_stats(compute_ndti(image), geometry, "NDTI")
                ndwi_s = extract_stats(compute_ndwi(image), geometry, "NDWI")
                alert  = compute_alert_level(ndti_mean=ndti_s["NDTI_mean"])

                hydro_records.append({
                    "date":            start,
                    "zone":            zone_name,
                    "lat":             lat,
                    "lon":             lon,
                    "ndti_mean":       ndti_s["NDTI_mean"],
                    "ndti_min":        ndti_s["NDTI_min"],
                    "ndti_max":        ndti_s["NDTI_max"],
                    "ndwi_mean":       ndwi_s["NDWI_mean"],
                    "alert_level":     alert,
                    "cloud_pct":       cloud_pct,
                    "last_clear_view": last_clear
                })

            # Process agri indices
            if zone_type in ["agri", "both"]:
                ndvi_s = extract_stats(compute_ndvi(image), geometry, "NDVI")
                ndre_s = extract_stats(compute_ndre(image), geometry, "NDRE")
                alert  = compute_alert_level(
                    ndvi_mean=ndvi_s["NDVI_mean"],
                    ndre_mean=ndre_s["NDRE_mean"]
                )

                agri_records.append({
                    "date":        start,
                    "zone":        zone_name,
                    "lat":         lat,
                    "lon":         lon,
                    "ndvi_mean":   ndvi_s["NDVI_mean"],
                    "ndvi_min":    ndvi_s["NDVI_min"],
                    "ndvi_max":    ndvi_s["NDVI_max"],
                    "ndre_mean":   ndre_s["NDRE_mean"],
                    "alert_level": alert,
                    "cloud_pct":   cloud_pct
                })

        # Build summary for KPI panels
        summary    = _build_summary(hydro_records, agri_records, zone_type)

        # Build map info for geemap rendering
        map_info   = _build_map_info(lat, lon, geometry, zone_type, buffer_m)

        result = {
            "success":     True,
            "zone_name":   zone_name,
            "lat":         lat,
            "lon":         lon,
            "zone_type":   zone_type,
            "hydro_data":  hydro_records,
            "agri_data":   agri_records,
            "latest_hydro": hydro_records[-1] if hydro_records else None,
            "latest_agri":  agri_records[-1]  if agri_records  else None,
            "map_info":    map_info,
            "summary":     summary,
            "from_cache":  False,
            "error":       None,
            "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        # Cache the result
        cache.set(cache_key, result, expire=CACHE_TTL)

        print(f"✅ Analysis complete!")
        print(f"   Hydro records : {len(hydro_records)}")
        print(f"   Agri records  : {len(agri_records)}")

        return result

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Analysis failed: {error_msg}")
        return {
            "success":   False,
            "zone_name": zone_name,
            "lat":       lat,
            "lon":       lon,
            "zone_type": zone_type,
            "error":     error_msg,
            "hydro_data": [],
            "agri_data":  [],
            "latest_hydro": None,
            "latest_agri":  None,
            "map_info":   None,
            "summary":    None
        }


# ============================================================
# SAVE CUSTOM ZONE TO SUPABASE
# ============================================================

def save_custom_zone(analysis_result: dict) -> dict:
    """
    Save a successfully analysed custom zone to Supabase.
    Called when client clicks "Save to Dashboard" button.

    Parameters:
        analysis_result : dict — returned by analyse_location()

    Returns:
        dict with success status and message
    """
    if not analysis_result.get("success"):
        return {
            "saved":   False,
            "message": "Cannot save — analysis was not successful"
        }

    try:
        from database import write_hydro_data, write_agri_data

        saved_count = 0

        if analysis_result["hydro_data"]:
            df = pd.DataFrame(analysis_result["hydro_data"])
            write_hydro_data(df)
            saved_count += len(df)

        if analysis_result["agri_data"]:
            df = pd.DataFrame(analysis_result["agri_data"])
            write_agri_data(df)
            saved_count += len(df)

        return {
            "saved":   True,
            "message": f"✅ {analysis_result['zone_name']} saved to dashboard ({saved_count} records)",
            "zone":    analysis_result["zone_name"]
        }

    except Exception as e:
        return {
            "saved":   False,
            "message": f"❌ Failed to save: {e}"
        }


# ============================================================
# GET LIVE MAP TILE
# ============================================================

def get_live_map(lat: float, lon: float, zone_type: str,
                 buffer_m: int = 2000) -> dict:
    """
    Generate live satellite map using folium + GEE tile URLs.
    Returns a folium Map object ready for st_folium rendering.
    """
    try:
        import folium
        import branca.colormap as cm

        initialize_gee()

        display_area = ee.Geometry.Point([lon, lat]).buffer(20000).bounds()
        end          = datetime.now()
        start        = end - timedelta(days=60)

        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(display_area)
            .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))
        )

        if collection.size().getInfo() == 0:
            return {"success": False, "map": None, "error": "No clear Sentinel-2 image in the last 60 days"}

        image = collection.median()

        geo_map = folium.Map(
            location=[lat, lon], zoom_start=10, control_scale=True,
            tiles="https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png",
            attr="© OpenStreetMap contributors © CARTO",
        )

        if zone_type in ["hydro", "both"]:
            ndti     = compute_ndti(image)
            vis      = {"min": -0.1, "max": 0.35, "palette": ["1a237e", "0288d1", "4dd0e1", "fff176", "ff8f00", "b71c1c"]}
            tile_url = ndti.getMapId(vis)["tile_fetcher"].url_format
            folium.TileLayer(tiles=tile_url, attr="Google Earth Engine", name="Turbidity (NDTI)", overlay=True, opacity=0.8).add_to(geo_map)
            cm.LinearColormap(colors=["#1a237e","#0288d1","#4dd0e1","#fff176","#ff8f00","#b71c1c"],
                              vmin=-0.1, vmax=0.35, caption="Turbidity Index (NDTI)").add_to(geo_map)

        if zone_type in ["agri", "both"]:
            ndvi     = compute_ndvi(image)
            vis      = {"min": 0.1, "max": 0.85, "palette": ["a50026", "f46d43", "fee08b", "d9ef8b", "66bd63", "1a9850", "006837"]}
            tile_url = ndvi.getMapId(vis)["tile_fetcher"].url_format
            folium.TileLayer(tiles=tile_url, attr="Google Earth Engine", name="Vegetation (NDVI)", overlay=True, opacity=0.8).add_to(geo_map)
            cm.LinearColormap(colors=["#a50026","#f46d43","#fee08b","#d9ef8b","#66bd63","#1a9850","#006837"],
                              vmin=0.1, vmax=0.85, caption="Vegetation Index (NDVI)").add_to(geo_map)

        folium.TileLayer(
            tiles="https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png",
            attr="© CARTO", overlay=True, control=False,
        ).add_to(geo_map)
        folium.Marker(location=[lat, lon], tooltip=f"{lat:.4f}, {lon:.4f}",
                      icon=folium.Icon(color="white", icon="map-marker")).add_to(geo_map)

        return {"success": True, "map": geo_map, "error": None}

    except Exception as e:
        return {"success": False, "map": None, "error": str(e)}


# ============================================================
# STREAMLIT UI COMPONENT
# ============================================================
def render_search_ui():
    """Complete Streamlit UI for custom zone search."""

    # Quick suggestions
    with st.expander("Quick suggestions — Malaysian locations"):
        suggestions = get_suggestions()
        cols = st.columns(3)
        for i, s in enumerate(suggestions):
            label = "Hydro" if s["type"] == "hydro" else "Agri"
            if cols[i % 3].button(f"{s['name']} ({label})", key=f"sug_{i}"):
                st.session_state["location_search"] = s["name"]
                st.rerun()

    col1, col2 = st.columns([3, 1])
    with col1:
        search_input = st.text_input(
            "Enter location name or coordinates",
            placeholder = "e.g. Tasik Kenyir  or  5.0500, 102.6000",
            key         = "location_search"
        )
    with col2:
        zone_type = st.selectbox(
            "Monitor for",
            options     = ["hydro", "agri", "both"],
            format_func = lambda x: {"hydro": "Hydro", "agri": "Agri", "both": "Both"}[x]
        )

    analyse_clicked = st.button("Analyse Location", type="primary", use_container_width=True)

    if analyse_clicked and search_input:
        with st.spinner("Finding location..."):
            location = detect_and_resolve(search_input)

        if not location["valid"]:
            st.markdown(f'<div class="alrt alrt-crit"><div class="alrt-zone">Location not found</div><div class="alrt-msg">{location["error"]}</div></div>', unsafe_allow_html=True)
            return

        with st.spinner("Loading recent satellite data... (~30 seconds for new locations)"):
            quick_result = analyse_location(
                lat=location["lat"], lon=location["lon"],
                zone_name=location["name"], zone_type=zone_type,
                months=3, buffer_m=2000
            )

        if not quick_result["success"]:
            st.markdown(f'<div class="alrt alrt-crit"><div class="alrt-zone">Analysis failed</div><div class="alrt-msg">{quick_result["error"]}</div></div>', unsafe_allow_html=True)
            return

        st.session_state["lookup_location"]  = location
        st.session_state["lookup_quick"]     = quick_result
        st.session_state["lookup_zone_type"] = zone_type
        st.session_state.pop("lookup_full", None)

    if "lookup_quick" not in st.session_state:
        return

    location     = st.session_state["lookup_location"]
    quick_result = st.session_state["lookup_quick"]
    zone_type    = st.session_state["lookup_zone_type"]
    lat, lon     = location["lat"], location["lon"]
    cache_note   = " · from cache" if quick_result.get("from_cache") else ""

    st.markdown(f"""<div style="margin:16px 0 20px;padding:12px 18px;border-radius:10px;
        border-left:3px solid #2563eb;background:rgba(37,99,235,0.06);">
        <span style="font-size:14px;font-weight:600;">{location['name']}</span>
        <span class="meta-tag" style="margin-left:12px;">{lat:.4f}, {lon:.4f}{cache_note}</span>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="panel-label" style="margin-bottom:14px;">RECENT DATA — LAST 3 MONTHS</div>', unsafe_allow_html=True)
    _render_kpis(quick_result)
    _render_trend_chart(quick_result, label="Recent 3-Month Trend")
    _render_live_map(lat, lon, zone_type)

    st.markdown('<hr style="margin:24px 0;border-color:rgba(0,0,0,0.07);">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label" style="margin-bottom:14px;">FULL 12-MONTH HISTORY</div>', unsafe_allow_html=True)

    if "lookup_full" not in st.session_state:
        if st.button("Load Full 12-Month History", help="Takes ~2 minutes for new locations. Instant if cached."):
            with st.spinner("Loading full 12-month history..."):
                full_result = analyse_location(
                    lat=lat, lon=lon, zone_name=location["name"],
                    zone_type=zone_type, months=12, buffer_m=2000
                )
            if full_result["success"]:
                st.session_state["lookup_full"] = full_result
                st.rerun()
            else:
                st.markdown(f'<div class="alrt alrt-crit"><div class="alrt-zone">Failed</div><div class="alrt-msg">{full_result["error"]}</div></div>', unsafe_allow_html=True)
        _render_save_button(quick_result)
    else:
        full_result = st.session_state["lookup_full"]
        _render_trend_chart(full_result, label="Full 12-Month Trend")
        _render_data_table(full_result)
        _render_trend_summary(full_result)
        st.markdown('<hr style="margin:16px 0;border-color:rgba(0,0,0,0.07);">', unsafe_allow_html=True)
        _render_save_button(full_result)
 
 
# ============================================================
# UI SUBCOMPONENTS
# ============================================================
 
def _render_kpis(result: dict):
    """Render KPI cards matching the main dashboard style."""

    if result["zone_type"] in ["hydro", "both"] and result["latest_hydro"]:
        h      = result["latest_hydro"]
        alert  = h.get("alert_level", "normal")
        accent = {"critical": "#dc2626", "warning": "#d97706", "normal": "#16a34a"}.get(alert, "#2563eb")
        tag    = {"critical": "tag-red",  "warning": "tag-amber", "normal": "tag-green"}.get(alert, "tag-green")
        ndti   = f"{h['ndti_mean']:.4f}" if h.get("ndti_mean") is not None else "N/A"
        ndwi   = f"{h['ndwi_mean']:.4f}" if h.get("ndwi_mean") is not None else "N/A"
        cloud  = f"{h['cloud_pct']}%"    if h.get("cloud_pct") is not None else "N/A"
        glow   = "kpi-glow" if alert == "critical" else ""
        st.markdown(f"""<div class="kpi-row">
            <div class="kpi"><div class="kpi-accent" style="background:#2563eb;"></div>
                <div class="kpi-label">Latest NDTI</div><div class="kpi-val">{ndti}</div>
                <span class="kpi-tag tag-blue">Turbidity Index</span></div>
            <div class="kpi"><div class="kpi-accent" style="background:#0288d1;"></div>
                <div class="kpi-label">Latest NDWI</div><div class="kpi-val">{ndwi}</div>
                <span class="kpi-tag tag-blue">Water Index</span></div>
            <div class="kpi"><div class="kpi-accent" style="background:#94a3b8;"></div>
                <div class="kpi-label">Cloud Cover</div><div class="kpi-val">{cloud}</div>
                <span class="kpi-tag tag-blue">Last image</span></div>
            <div class="kpi {glow}"><div class="kpi-accent" style="background:{accent};"></div>
                <div class="kpi-label">Alert Status</div>
                <div class="kpi-val" style="font-size:22px;">{alert.upper()}</div>
                <span class="kpi-tag {tag}">{alert.capitalize()}</span></div>
        </div>""", unsafe_allow_html=True)

    if result["zone_type"] in ["agri", "both"] and result["latest_agri"]:
        a      = result["latest_agri"]
        alert  = a.get("alert_level", "normal")
        accent = {"critical": "#dc2626", "warning": "#d97706", "normal": "#16a34a"}.get(alert, "#16a34a")
        tag    = {"critical": "tag-red",  "warning": "tag-amber", "normal": "tag-green"}.get(alert, "tag-green")
        ndvi   = f"{a['ndvi_mean']:.4f}" if a.get("ndvi_mean") is not None else "N/A"
        ndre   = f"{a['ndre_mean']:.4f}" if a.get("ndre_mean") is not None else "N/A"
        cloud  = f"{a['cloud_pct']}%"    if a.get("cloud_pct") is not None else "N/A"
        glow   = "kpi-glow" if alert == "critical" else ""
        st.markdown(f"""<div class="kpi-row">
            <div class="kpi"><div class="kpi-accent" style="background:#16a34a;"></div>
                <div class="kpi-label">Latest NDVI</div><div class="kpi-val">{ndvi}</div>
                <span class="kpi-tag tag-green">Vegetation Index</span></div>
            <div class="kpi"><div class="kpi-accent" style="background:#15803d;"></div>
                <div class="kpi-label">Latest NDRE</div><div class="kpi-val">{ndre}</div>
                <span class="kpi-tag tag-green">Chlorophyll</span></div>
            <div class="kpi"><div class="kpi-accent" style="background:#94a3b8;"></div>
                <div class="kpi-label">Cloud Cover</div><div class="kpi-val">{cloud}</div>
                <span class="kpi-tag tag-blue">Last image</span></div>
            <div class="kpi {glow}"><div class="kpi-accent" style="background:{accent};"></div>
                <div class="kpi-label">Alert Status</div>
                <div class="kpi-val" style="font-size:22px;">{alert.upper()}</div>
                <span class="kpi-tag {tag}">{alert.capitalize()}</span></div>
        </div>""", unsafe_allow_html=True)
 
 
def _render_trend_chart(result: dict, label: str = "Trend"):
    """Render trend chart using Altair matching the main dashboard style."""
    import altair as alt

    def _make_chart(df, y_col, color, title):
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        df["date_str"] = df["date"].dt.strftime("%d %b %Y")
        date_order = df["date_str"].tolist()

        base   = alt.Chart(df).encode(
            x=alt.X("date_str:N", sort=date_order, title=None,
                axis=alt.Axis(labelFontSize=11, labelAngle=0, labelFont="Inter",
                              tickColor="transparent", domainColor="rgba(0,0,0,0.1)",
                              labelColor="#94a3b8", labelPadding=8)),
            y=alt.Y(f"{y_col}:Q", title=None, scale=alt.Scale(zero=False),
                axis=alt.Axis(labelFontSize=10, labelFont="JetBrains Mono",
                              gridColor="rgba(0,0,0,0.06)", tickColor="transparent",
                              domainColor="transparent", labelColor="#94a3b8")),
        )
        lines  = base.mark_line(strokeWidth=2.5, color=color, opacity=0.9)
        points = base.mark_circle(size=55, color=color, opacity=1).encode(
            tooltip=[alt.Tooltip("date_str:N", title="Date"),
                     alt.Tooltip(f"{y_col}:Q", title=y_col.upper(), format=".4f")]
        )
        return (lines + points).properties(
            title=alt.TitleParams(title, fontSize=13, font="Inter",
                                  color="#64748b", fontWeight=600),
            height=270, background="transparent"
        ).configure_view(strokeWidth=0)

    if result["hydro_data"]:
        df = pd.DataFrame(result["hydro_data"])
        st.altair_chart(
            _make_chart(df, "ndti_mean", "#2563eb", f"{label} — Turbidity (NDTI)"),
            use_container_width=True
        )

    if result["agri_data"]:
        df = pd.DataFrame(result["agri_data"])
        st.altair_chart(
            _make_chart(df, "ndvi_mean", "#16a34a", f"{label} — Vegetation (NDVI)"),
            use_container_width=True
        )
 
 
def _render_live_map(lat: float, lon: float, zone_type: str):
    """Render live satellite map using folium."""
    from streamlit_folium import st_folium
    st.markdown('<div class="panel-label" style="margin:20px 0 10px;">LIVE SATELLITE MAP</div>', unsafe_allow_html=True)
    with st.spinner("Loading satellite map..."):
        map_result = get_live_map(lat, lon, zone_type)

    if map_result["success"]:
        st_folium(map_result["map"], height=420, use_container_width=True)
    else:
        st.markdown(f'<div class="alrt alrt-warn"><div class="alrt-zone">Map unavailable</div><div class="alrt-msg">{map_result["error"]}</div></div>', unsafe_allow_html=True)
 
 
def _render_trend_summary(result: dict):
    """Render trend summary using dashboard alert style."""
    st.markdown('<div class="panel-label" style="margin:16px 0 12px;">TREND SUMMARY</div>', unsafe_allow_html=True)

    if result["hydro_data"] and len(result["hydro_data"]) >= 3:
        df     = pd.DataFrame(result["hydro_data"])
        first3 = df.head(3)["ndti_mean"].mean()
        last3  = df.tail(3)["ndti_mean"].mean()
        change = last3 - first3

        if change > 0.02:
            st.markdown(f'<div class="alrt alrt-crit"><div class="alrt-zone">Turbidity INCREASING</div><div class="alrt-msg">Up {change:.4f} over the period — dredging may be needed.</div></div>', unsafe_allow_html=True)
        elif change < -0.02:
            st.markdown(f'<div style="padding:12px 18px;border-left:3px solid #16a34a;background:rgba(22,163,74,0.08);border-radius:0 6px 6px 0;margin-bottom:8px;"><div class="alrt-zone">Turbidity DECREASING</div><div class="alrt-msg">Down {abs(change):.4f} — conditions improving.</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="padding:12px 18px;border-left:3px solid #94a3b8;background:rgba(148,163,184,0.08);border-radius:0 6px 6px 0;margin-bottom:8px;"><div class="alrt-zone">Turbidity STABLE</div><div class="alrt-msg">Change of {change:.4f} over the period.</div></div>', unsafe_allow_html=True)

    if result["agri_data"] and len(result["agri_data"]) >= 3:
        df     = pd.DataFrame(result["agri_data"])
        first3 = df.head(3)["ndvi_mean"].mean()
        last3  = df.tail(3)["ndvi_mean"].mean()
        change = last3 - first3

        if change < -0.05:
            st.markdown(f'<div class="alrt alrt-crit"><div class="alrt-zone">Vegetation DECLINING</div><div class="alrt-msg">Down {abs(change):.4f} — investigate crop stress.</div></div>', unsafe_allow_html=True)
        elif change > 0.05:
            st.markdown(f'<div style="padding:12px 18px;border-left:3px solid #16a34a;background:rgba(22,163,74,0.08);border-radius:0 6px 6px 0;margin-bottom:8px;"><div class="alrt-zone">Vegetation IMPROVING</div><div class="alrt-msg">Up {change:.4f} — healthy growth trend.</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="padding:12px 18px;border-left:3px solid #94a3b8;background:rgba(148,163,184,0.08);border-radius:0 6px 6px 0;margin-bottom:8px;"><div class="alrt-zone">Vegetation STABLE</div><div class="alrt-msg">Change of {change:.4f} over the period.</div></div>', unsafe_allow_html=True)
 
 
def _render_data_table(result: dict):
    """Render raw data in an expandable table."""
    with st.expander("View full data table"):
        if result["hydro_data"]:
            st.write("**Hydro Data:**")
            st.dataframe(
                pd.DataFrame(result["hydro_data"]),
                use_container_width=True
            )
        if result["agri_data"]:
            st.write("**Agri Data:**")
            st.dataframe(
                pd.DataFrame(result["agri_data"]),
                use_container_width=True
            )
 
 
def _render_save_button(result: dict):
    """Render save button using dashboard styling."""
    col1, col2 = st.columns([1, 2])

    with col1:
        if st.button("Save to Dashboard", use_container_width=True, type="primary"):
            with st.spinner("Saving..."):
                save_result = save_custom_zone(result)
            if save_result["saved"]:
                st.markdown(f'<div class="sb-feedback sb-ok">{save_result["message"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="sb-feedback sb-err">{save_result["message"]}</div>', unsafe_allow_html=True)

    with col2:
        st.markdown(f'<div style="padding:10px 0;"><span class="zmeta">Saving <b style="font-weight:600;">{result["zone_name"]}</b> adds it to your monitored zones list.</span></div>', unsafe_allow_html=True)
 


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _build_date_windows(start_date, end_date):
    """Build list of monthly (start, end) date window tuples."""
    windows = []
    current = start_date
    while current < end_date:
        window_end = current + timedelta(days=30)
        windows.append((
            current.strftime("%Y-%m-%d"),
            min(window_end, end_date).strftime("%Y-%m-%d")
        ))
        current = window_end
    return windows


def _build_summary(hydro_records, agri_records, zone_type):
    """Build summary dict for KPI panels."""
    summary = {"zone_type": zone_type}

    if hydro_records:
        latest = hydro_records[-1]
        summary["latest_ndti"]        = latest.get("ndti_mean")
        summary["hydro_alert"]        = latest.get("alert_level")
        summary["hydro_record_count"] = len(hydro_records)
        summary["critical_hydro"]     = sum(
            1 for r in hydro_records if r.get("alert_level") == "critical"
        )

    if agri_records:
        latest = agri_records[-1]
        summary["latest_ndvi"]       = latest.get("ndvi_mean")
        summary["latest_ndre"]       = latest.get("ndre_mean")
        summary["agri_alert"]        = latest.get("alert_level")
        summary["agri_record_count"] = len(agri_records)
        summary["critical_agri"]     = sum(
            1 for r in agri_records if r.get("alert_level") == "critical"
        )

    return summary


def _build_map_info(lat, lon, geometry, zone_type, buffer_m):
    """Build map configuration info."""
    return {
        "center":    [lat, lon],
        "zoom":      13,
        "geometry":  geometry.getInfo(),
        "zone_type": zone_type,
        "buffer_m":  buffer_m
    }
