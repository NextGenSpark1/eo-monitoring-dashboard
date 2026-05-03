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
            location=[lat, lon], zoom_start=13, control_scale=True,
            tiles="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png",
            attr="© OpenStreetMap contributors © CARTO",
        )

        if zone_type in ["hydro", "both"]:
            ndti    = compute_ndti(image)
            vis     = {"min": -0.1, "max": 0.35, "palette": ["1a237e", "0288d1", "4dd0e1", "fff176", "ff8f00", "b71c1c"]}
            tile_url = ndti.getMapId(vis)["tile_fetcher"].url_format
            folium.TileLayer(tiles=tile_url, attr="Google Earth Engine", name="Turbidity (NDTI)", overlay=True).add_to(geo_map)
            cm.LinearColormap(colors=["#1a237e","#0288d1","#4dd0e1","#fff176","#ff8f00","#b71c1c"],
                              vmin=-0.1, vmax=0.35, caption="Turbidity Index (NDTI)").add_to(geo_map)

        if zone_type in ["agri", "both"]:
            ndvi    = compute_ndvi(image)
            vis     = {"min": 0.1, "max": 0.85, "palette": ["a50026", "f46d43", "fee08b", "d9ef8b", "66bd63", "1a9850", "006837"]}
            tile_url = ndvi.getMapId(vis)["tile_fetcher"].url_format
            folium.TileLayer(tiles=tile_url, attr="Google Earth Engine", name="Vegetation (NDVI)", overlay=True).add_to(geo_map)
            cm.LinearColormap(colors=["#a50026","#f46d43","#fee08b","#d9ef8b","#66bd63","#1a9850","#006837"],
                              vmin=0.1, vmax=0.85, caption="Vegetation Index (NDVI)").add_to(geo_map)

        folium.TileLayer(
            tiles="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png",
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

    st.subheader("Analyse Any Location")
    st.caption(
        "Search by place name or paste coordinates. "
        "Recent data loads in ~30 seconds. "
        "Full 12-month history loads in ~2 minutes."
    )

    # Quick suggestions
    with st.expander("Quick suggestions — Malaysian locations"):
        suggestions = get_suggestions()
        cols = st.columns(3)
        for i, s in enumerate(suggestions):
            label = "Hydro" if s["type"] == "hydro" else "Agri"
            if cols[i % 3].button(f"{s['name']} ({label})", key=f"sug_{i}"):
                st.session_state["search_input"] = s["name"]
                st.rerun()

    col1, col2 = st.columns([3, 1])
    with col1:
        search_input = st.text_input(
            "Enter location name or coordinates",
            value       = st.session_state.get("search_input", ""),
            placeholder = "e.g. Tasik Kenyir  or  5.0500, 102.6000",
            key         = "location_search"
        )
    with col2:
        zone_type = st.selectbox(
            "Monitor for",
            options     = ["hydro", "agri", "both"],
            format_func = lambda x: {"hydro": "Hydro", "agri": "Agri", "both": "Both"}[x]
        )

    with st.expander("Advanced options"):
        buffer_m = st.slider("Zone radius (metres)", 500, 5000, 2000, step=500)

    analyse_clicked = st.button("Analyse Location", type="primary", use_container_width=True)

    # Run analysis and store results in session_state
    if analyse_clicked and search_input:
        with st.spinner("Finding location..."):
            location = detect_and_resolve(search_input)

        if not location["valid"]:
            st.error(location["error"])
            return

        if location.get("warning"):
            st.warning(location["warning"])

        with st.spinner("Loading recent satellite data... (~30 seconds for new locations)"):
            quick_result = analyse_location(
                lat=location["lat"], lon=location["lon"],
                zone_name=location["name"], zone_type=zone_type,
                months=3, buffer_m=buffer_m
            )

        if not quick_result["success"]:
            st.error(f"Analysis failed: {quick_result['error']}")
            return

        # Persist results so reruns (theme change, buttons) don't wipe them
        st.session_state["lookup_location"]    = location
        st.session_state["lookup_quick"]       = quick_result
        st.session_state["lookup_zone_type"]   = zone_type
        st.session_state["lookup_buffer_m"]    = buffer_m
        st.session_state.pop("lookup_full", None)

    # Display stored results (survives any rerun)
    if "lookup_quick" not in st.session_state:
        return

    location     = st.session_state["lookup_location"]
    quick_result = st.session_state["lookup_quick"]
    zone_type    = st.session_state["lookup_zone_type"]
    buffer_m     = st.session_state["lookup_buffer_m"]
    lat, lon     = location["lat"], location["lon"]

    cache_note = "  (from cache)" if quick_result.get("from_cache") else ""
    st.info(f"**{location['name']}**  |  {lat:.4f}, {lon:.4f}{cache_note}")

    st.markdown("#### Recent Data — Last 3 Months")
    _render_kpis(quick_result)
    _render_trend_chart(quick_result, label="Recent 3-Month Trend")
    _render_live_map(lat, lon, zone_type)

    st.divider()
    st.markdown("#### Full 12-Month History")

    if "lookup_full" not in st.session_state:
        if st.button("Load Full 12-Month History", help="Takes ~2 minutes for new locations. Instant if cached."):
            with st.spinner("Loading full 12-month history... This takes 1-2 minutes for new locations."):
                full_result = analyse_location(
                    lat=lat, lon=lon, zone_name=location["name"],
                    zone_type=zone_type, months=12, buffer_m=buffer_m
                )
            if full_result["success"]:
                st.session_state["lookup_full"] = full_result
                st.rerun()
            else:
                st.error(f"Full history failed: {full_result['error']}")
        st.caption("You can save the 3-month preview now, or load full history first for better trends.")
        _render_save_button(quick_result)
    else:
        full_result = st.session_state["lookup_full"]
        _render_trend_chart(full_result, label="Full 12-Month Trend")
        _render_data_table(full_result)
        _render_trend_summary(full_result)
        st.divider()
        _render_save_button(full_result)
 
 
# ============================================================
# UI SUBCOMPONENTS
# ============================================================
 
def _render_kpis(result: dict):
    """Render KPI metric cards."""
 
    if result["zone_type"] in ["hydro", "both"] and result["latest_hydro"]:
        h = result["latest_hydro"]
        c1, c2, c3, c4 = st.columns(4)
 
        c1.metric("Latest NDTI",   f"{h['ndti_mean']:.4f}"  if h.get('ndti_mean')  else "N/A")
        c2.metric("Latest NDWI",   f"{h['ndwi_mean']:.4f}"  if h.get('ndwi_mean')  else "N/A")
        c3.metric("Cloud Cover",   f"{h['cloud_pct']}%"     if h.get('cloud_pct')  else "N/A")
        c4.metric("Alert Status",  h.get('alert_level', '').upper() or "N/A")

    if result["zone_type"] in ["agri", "both"] and result["latest_agri"]:
        a = result["latest_agri"]
        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Latest NDVI",   f"{a['ndvi_mean']:.4f}"  if a.get('ndvi_mean')  else "N/A")
        c2.metric("Latest NDRE",   f"{a['ndre_mean']:.4f}"  if a.get('ndre_mean')  else "N/A")
        c3.metric("Cloud Cover",   f"{a['cloud_pct']}%"     if a.get('cloud_pct')  else "N/A")
        c4.metric("Alert Status",  a.get('alert_level', '').upper() or "N/A")
 
 
def _render_trend_chart(result: dict, label: str = "Trend"):
    """Render time series trend charts."""
    import plotly.graph_objects as go
 
    if result["hydro_data"]:
        df = pd.DataFrame(result["hydro_data"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
 
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x    = df["date"],
            y    = df["ndti_mean"],
            mode = "lines+markers",
            name = "NDTI (Turbidity)",
            line = dict(color="#00B4D8", width=2)
        ))
 
        # Add threshold lines
        fig.add_hline(y=0.05, line_dash="dash", line_color="red",
                      annotation_text="Critical threshold")
        fig.add_hline(y=0.0,  line_dash="dash", line_color="orange",
                      annotation_text="Warning threshold")
 
        fig.update_layout(
            title      = f"{label} — Turbidity (NDTI)",
            xaxis_title= "Date",
            yaxis_title= "NDTI Value",
            height     = 300,
            showlegend = True
        )
        st.plotly_chart(fig, use_container_width=True)
 
    if result["agri_data"]:
        df = pd.DataFrame(result["agri_data"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
 
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x    = df["date"],
            y    = df["ndvi_mean"],
            mode = "lines+markers",
            name = "NDVI (Vegetation)",
            line = dict(color="#38B000", width=2)
        ))
 
        # Add threshold lines
        fig.add_hline(y=0.4, line_dash="dash", line_color="orange",
                      annotation_text="Warning threshold")
        fig.add_hline(y=0.2, line_dash="dash", line_color="red",
                      annotation_text="Critical threshold")
 
        fig.update_layout(
            title      = f"{label} — Vegetation Health (NDVI)",
            xaxis_title= "Date",
            yaxis_title= "NDVI Value",
            height     = 300,
            showlegend = True
        )
        st.plotly_chart(fig, use_container_width=True)
 
 
def _render_live_map(lat: float, lon: float, zone_type: str):
    """Render live satellite map using folium."""
    from streamlit_folium import st_folium
    st.markdown("#### Live Satellite Map")
    with st.spinner("Loading satellite map..."):
        map_result = get_live_map(lat, lon, zone_type)

    if map_result["success"]:
        st_folium(map_result["map"], height=400, use_container_width=True)
    else:
        st.warning(f"Map unavailable: {map_result['error']}")
 
 
def _render_trend_summary(result: dict):
    """Render trend summary — is it getting better or worse?"""
    st.markdown("#### Trend Summary")

    if result["hydro_data"] and len(result["hydro_data"]) >= 3:
        df     = pd.DataFrame(result["hydro_data"])
        first3 = df.head(3)["ndti_mean"].mean()
        last3  = df.tail(3)["ndti_mean"].mean()
        change = last3 - first3

        if change > 0.02:
            st.error(f"Turbidity is **INCREASING** — up {change:.4f} over the period. Dredging may be needed.")
        elif change < -0.02:
            st.success(f"Turbidity is **DECREASING** — down {abs(change):.4f}. Conditions improving.")
        else:
            st.info(f"Turbidity is **STABLE** — change of {change:.4f} over the period.")

    if result["agri_data"] and len(result["agri_data"]) >= 3:
        df     = pd.DataFrame(result["agri_data"])
        first3 = df.head(3)["ndvi_mean"].mean()
        last3  = df.tail(3)["ndvi_mean"].mean()
        change = last3 - first3

        if change < -0.05:
            st.error(f"Vegetation is **DECLINING** — down {abs(change):.4f}. Investigate crop stress.")
        elif change > 0.05:
            st.success(f"Vegetation is **IMPROVING** — up {change:.4f}. Healthy growth trend.")
        else:
            st.info(f"Vegetation is **STABLE** — change of {change:.4f} over the period.")
 
 
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
    """Render save to dashboard button."""
    col1, col2 = st.columns([1, 2])
 
    with col1:
        if st.button("Save to Dashboard", use_container_width=True, type="primary"):
            with st.spinner("Saving to database..."):
                save_result = save_custom_zone(result)
 
            if save_result["saved"]:
                st.success(save_result["message"])
                st.balloons()
            else:
                st.error(save_result["message"])
 
    with col2:
        st.caption(
            f"Saving **{result['zone_name']}** adds it permanently "
            f"to your dashboard alongside the existing monitoring zones."
        )
 


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
