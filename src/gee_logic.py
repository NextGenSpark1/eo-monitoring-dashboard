"""
================================================================================
src/gee_logic.py
================================================================================
Developer  : Mohamed Nawran (AI Platform Engineering)
             Habiba Hassan (AI Analytics & Visualization)
Description: Google Earth Engine processing — Sentinel-2 image loading,
             index computation (NDTI, NDVI, NDWI, NDRE), statistics
             extraction, alert classification, and live map tile generation.
================================================================================
"""

import ee
import json
import os
import diskcache as dc

# DISK CACHE SETUP

CACHE_DIR  = ".cache"
CACHE_TTL  = 60 * 60 * 24 * 7   # 7 days cache expiry
cache      = dc.Cache(CACHE_DIR)


def clear_cache():
    """Clear all cached GEE results. Use when you want fresh data."""
    cache.clear()
    print("Cache cleared")


def warm_up_cache():
    """
    Pre-load all zones into cache before the demo.
    Run this 30 minutes before your presentation.
    After this, all zone switches will be instant.
    """
    print("🔥 Warming up cache for demo...")
    print("   This may take 5-10 minutes — run before presentation\n")

    from datetime import datetime, timedelta
    end   = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    for config in [RESERVOIR_CONFIG, FARM_CONFIG]:
        geometry = get_geometry(config)
        print(f"   Loading {config['name']}...", end=" ")
        load_sentinel2(geometry, start, end)
        print("✅ cached")

    print("\n✅ Cache warm-up complete — demo is ready!")


# AUTHENTICATION

def initialize_gee():
    """
    Headless GEE authentication.
    """
    try:
        import streamlit as st
        key_data    = json.loads(st.secrets["EARTHENGINE_TOKEN"])
        credentials = ee.ServiceAccountCredentials(
            email    = key_data["client_email"],
            key_data = json.dumps(key_data)
        )
        ee.Initialize(credentials)
        return
    except Exception:
        pass

    try:
        if os.path.exists("service_account.json"):
            with open("service_account.json") as f:
                key_data = json.load(f)
            credentials = ee.ServiceAccountCredentials(
                email    = key_data["client_email"],
                key_data = json.dumps(key_data)
            )
            ee.Initialize(credentials)
            return
    except Exception:
        pass

    try:
        token = os.environ.get("EARTHENGINE_TOKEN")
        if token:
            key_data    = json.loads(token)
            credentials = ee.ServiceAccountCredentials(
                email    = key_data["client_email"],
                key_data = json.dumps(key_data)
            )
            ee.Initialize(credentials)
            return
    except Exception:
        pass

    raise Exception("❌ GEE authentication failed.")


# REGION DEFINITIONS

FARM_CONFIG = {
    "name":        "Felda Jengka",
    "location":    "Pahang, Malaysia",
    "use_case":    "Agriculture Monitoring",
    "lat":         3.6800,
    "lon":         102.5100,
    "buffer_m":    3000,    # 3km radius — covers a representative plantation block
    "description": "Felda Jengka — one of Malaysia's largest palm oil schemes. "
                   "Monitoring vegetation health to correlate with upstream "
                   "siltation patterns at Empangan Sultan Abu Bakar."
}
 
RESERVOIR_CONFIG = {
    "name":        "Empangan Sultan Abu Bakar",
    "location":    "Pahang, Malaysia",
    "use_case":    "Hydro Monitoring",
    "lat":         4.420818973863855,
    "lon":         101.39234334882522,
    "buffer_m":    2000,
    "description": "Empangan Sultan Abu Bakar — TNB GENCO reservoir. "
                   "Monitoring turbidity and siltation for dredging optimisation."
}
 

def get_geometry(config):
    """Build ee.Geometry from config dict using Point + buffer."""
    return (
        ee.Geometry.Point([config["lon"], config["lat"]])
        .buffer(config["buffer_m"])
        .bounds()
    )


# IMAGE LOADING — WITH CACHE

def load_sentinel2(geometry, start_date, end_date, cloud_threshold=20):
    """
    Load cloud-free Sentinel-2 median composite.
    Results cached to disk — subsequent calls are instant.

    Returns:
        tuple: (ee.Image or None, cloud_pct, last_clear_date)
    """
    # Build cache key from parameters
    geo_info  = geometry.getInfo()
    cache_key = f"s2_{hash(str(geo_info))}_{start_date}_{end_date}_{cloud_threshold}"

    # Check cache first
    cached = cache.get(cache_key)
    if cached is not None:
        print(f"Cache hit — instant load")
        # Return cached stats (we cache stats, not the ee.Image object)
        return cached["image_proxy"], cached["cloud_pct"], cached["last_clear"]

    # Not in cache — fetch from GEE
    print(f"Fetching from GEE (will cache for next time)...")

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_threshold))
    )

    count = collection.size().getInfo()
    if count == 0:
        return None, 0, None

    cloud_pct = round(
        collection.aggregate_mean("CLOUDY_PIXEL_PERCENTAGE").getInfo(), 1
    )
    last_clear = (
        collection
        .sort("system:time_start", False)
        .first()
        .date()
        .format("YYYY-MM-dd")
        .getInfo()
    )

    image = collection.median().clip(geometry)

    # Cache the result
    cache.set(
        cache_key,
        {"image_proxy": image, "cloud_pct": cloud_pct, "last_clear": last_clear},
        expire=CACHE_TTL
    )

    return image, cloud_pct, last_clear


# INDEX COMPUTATIONS

def compute_ndti(image):
    """NDTI = (B4-B3)/(B4+B3) — Turbidity. Higher = dirtier water."""
    return image.normalizedDifference(["B4", "B3"]).rename("NDTI")


def compute_ndwi(image):
    """NDWI = (B3-B8)/(B3+B8) — Water presence."""
    return image.normalizedDifference(["B3", "B8"]).rename("NDWI")


def compute_ndvi(image):
    """NDVI = (B8-B4)/(B8+B4) — Vegetation health."""
    return image.normalizedDifference(["B8", "B4"]).rename("NDVI")


def compute_ndre(image):
    """NDRE = (B8A-B5)/(B8A+B5) — Chlorophyll depth for dense canopy."""
    return image.normalizedDifference(["B8A", "B5"]).rename("NDRE")


# STATISTICS EXTRACTION

def extract_stats(index_image, geometry, index_name, scale=10):
    """Extract mean, min, max for an index over a zone."""
    stats = index_image.reduceRegion(
        reducer  = ee.Reducer.mean()
            .combine(ee.Reducer.min(), sharedInputs=True)
            .combine(ee.Reducer.max(), sharedInputs=True),
        geometry = geometry,
        scale    = scale,
        maxPixels= 1e9
    ).getInfo()

    def safe_round(val):
        return round(val, 4) if val is not None else None

    return {
        f"{index_name}_mean": safe_round(stats.get(f"{index_name}_mean")),
        f"{index_name}_min":  safe_round(stats.get(f"{index_name}_min")),
        f"{index_name}_max":  safe_round(stats.get(f"{index_name}_max")),
    }



# ALERT LOGIC

def compute_alert_level(ndti_mean=None, ndvi_mean=None, ndre_mean=None):
    """Returns 'normal' | 'warning' | 'critical'"""
    alerts = []

    if ndti_mean is not None:
        if   ndti_mean > 0.05:  alerts.append("critical")
        elif ndti_mean > 0.0:   alerts.append("warning")
        else:                   alerts.append("normal")

    if ndvi_mean is not None:
        if   ndvi_mean < 0.2:   alerts.append("critical")
        elif ndvi_mean < 0.4:   alerts.append("warning")
        else:                   alerts.append("normal")

    if ndre_mean is not None:
        if   ndre_mean < 0.15:  alerts.append("critical")
        elif ndre_mean < 0.25:  alerts.append("warning")
        else:                   alerts.append("normal")

    if "critical" in alerts: return "critical"
    if "warning"  in alerts: return "warning"
    return "normal"


# LIVE MAP LAYERS — combined water (NDTI) + land (NDVI) for dashboard maps

def get_map_layers(lat, lon, date_str, buffer_m=2000):
    """
    Returns both NDTI (water-masked) and NDVI (land-masked) ee.Image objects
    for displaying a complete environmental map. Single GEE call for both layers.
    Uses 120-day lookback and 70% cloud threshold for maximum coverage.
    """
    from datetime import datetime, timedelta

    stats_area   = ee.Geometry.Point([lon, lat]).buffer(buffer_m).bounds()
    # Full Malaysia bounding box — Peninsular + Sabah + Sarawak
    display_area = ee.Geometry.Rectangle([99.6, 0.8, 119.5, 7.5])

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    start    = (date_obj - timedelta(days=365)).strftime("%Y-%m-%d")
    end      = date_str

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(display_area)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 90))
    )

    image      = collection.median()
    water_mask = compute_ndwi(image).gt(0)
    land_mask  = compute_ndwi(image).lt(0.1)

    ndti = compute_ndti(image).updateMask(water_mask)
    ndvi = compute_ndvi(image).updateMask(land_mask)

    return ndti, ndvi, stats_area


# LIVE MAP TILE (for geemap in dashboard)

def get_turbidity_map(lat, lon, date_str, buffer_m=2000):
    """
    Generate live turbidity map tile — water pixels only.
    """
    from datetime import datetime, timedelta

    stats_area   = ee.Geometry.Point([lon, lat]).buffer(buffer_m).bounds()
    display_area = ee.Geometry.Point([lon, lat]).buffer(500000).bounds()

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    start    = (date_obj - timedelta(days=60)).strftime("%Y-%m-%d")
    end      = date_str

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(display_area)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))
    )
    if collection.size().getInfo() == 0:
        return None, stats_area

    image      = collection.median()
    water_mask = compute_ndwi(image).gt(0)
    return compute_ndti(image).updateMask(water_mask), stats_area



# LIVE MAP TILE — NDVI (for agriculture module in dashboard)

def get_ndvi_map(lat, lon, date_str, buffer_m=3000):
    """
    Generate live NDVI map tile — land/vegetation pixels only.
    """
    from datetime import datetime, timedelta

    stats_area   = ee.Geometry.Point([lon, lat]).buffer(buffer_m).bounds()
    display_area = ee.Geometry.Point([lon, lat]).buffer(500000).bounds()

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    start    = (date_obj - timedelta(days=60)).strftime("%Y-%m-%d")
    end      = date_str

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(display_area)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))
    )
    if collection.size().getInfo() == 0:
        return None, stats_area

    image     = collection.median()
    land_mask = compute_ndwi(image).lt(0.1)
    return compute_ndvi(image).updateMask(land_mask), stats_area


# FULL PIPELINE RUNNER — 12 MONTHS

def run_full_pipeline(months_back=12):
    """
    Full pipeline — processes both zones for all monthly windows.
    12 months by default as per manager's requirement.
    Returns (hydro_df, agri_df).
    """
    import pandas as pd
    from datetime import datetime, timedelta

    initialize_gee()

    end_date   = datetime.now()
    start_date = end_date - timedelta(days=30 * months_back)

    # Build monthly windows
    date_windows = []
    current = start_date
    while current < end_date:
        window_end = current + timedelta(days=30)
        date_windows.append((
            current.strftime("%Y-%m-%d"),
            min(window_end, end_date).strftime("%Y-%m-%d")
        ))
        current = window_end

    print(f"\n Processing {months_back} months ({len(date_windows)} windows)")
    print(f"   From : {start_date.strftime('%Y-%m-%d')}")
    print(f"   To   : {end_date.strftime('%Y-%m-%d')}\n")

    hydro_records = []
    agri_records  = []

    for zone_type, config in [("reservoir", RESERVOIR_CONFIG), ("farm", FARM_CONFIG)]:
        geometry = get_geometry(config)
        print(f" {config['name']}")

        for start, end in date_windows:
            print(f" {start} → {end}", end=" ")
            image, cloud_pct, last_clear = load_sentinel2(geometry, start, end)

            if image is None:
                print(" skipped")
                continue

            if zone_type == "reservoir":
                ndti_s = extract_stats(compute_ndti(image), geometry, "NDTI")
                ndwi_s = extract_stats(compute_ndwi(image), geometry, "NDWI")
                alert  = compute_alert_level(ndti_mean=ndti_s["NDTI_mean"])
                hydro_records.append({
                    "date":            start,
                    "zone":            config["name"],
                    "location":        config["location"],
                    "ndti_mean":       ndti_s["NDTI_mean"],
                    "ndti_min":        ndti_s["NDTI_min"],
                    "ndti_max":        ndti_s["NDTI_max"],
                    "ndwi_mean":       ndwi_s["NDWI_mean"],
                    "alert_level":     alert,
                    "cloud_pct":       cloud_pct,
                    "last_clear_view": last_clear
                })
            else:
                ndvi_s = extract_stats(compute_ndvi(image), geometry, "NDVI")
                ndre_s = extract_stats(compute_ndre(image), geometry, "NDRE")
                alert  = compute_alert_level(
                    ndvi_mean=ndvi_s["NDVI_mean"],
                    ndre_mean=ndre_s["NDRE_mean"]
                )
                agri_records.append({
                    "date":        start,
                    "zone":        config["name"],
                    "location":    config["location"],
                    "ndvi_mean":   ndvi_s["NDVI_mean"],
                    "ndvi_min":    ndvi_s["NDVI_min"],
                    "ndvi_max":    ndvi_s["NDVI_max"],
                    "ndre_mean":   ndre_s["NDRE_mean"],
                    "alert_level": alert,
                    "cloud_pct":   cloud_pct
                })
            print("processed")

    hydro_df = pd.DataFrame(hydro_records)
    agri_df  = pd.DataFrame(agri_records)

    print(f"\n Pipeline complete!")
    print(f"   Hydro : {len(hydro_df)} records")
    print(f"   Agri  : {len(agri_df)} records")

    return hydro_df, agri_df
