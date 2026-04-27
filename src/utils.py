"""
================================================================================
src/utils.py
================================================================================
Developer  : Mohamed Nawran (AI Platform Engineering)
Description: Helper functions — coordinate parsing, date utilities,
             formatting helpers used across the project.
================================================================================
"""

from datetime import datetime, timedelta


# ============================================================
# COORDINATE UTILITIES
# ============================================================

def parse_coordinate_string(coord_str):
    """
    Parse a coordinate string into lat, lon floats.

    Supports formats:
    - "4.420818973863855, 101.39234334882522"
    - "4.420818973863855 101.39234334882522"
    - "lat=4.42, lon=101.39"

    Returns:
        tuple: (lat, lon) as floats
    """
    coord_str = coord_str.strip()

    # Remove lat=/lon= prefixes if present
    coord_str = coord_str.replace("lat=", "").replace("lon=", "")

    # Split by comma or space
    if "," in coord_str:
        parts = coord_str.split(",")
    else:
        parts = coord_str.split()

    if len(parts) != 2:
        raise ValueError(f"Cannot parse coordinate string: '{coord_str}'")

    lat = float(parts[0].strip())
    lon = float(parts[1].strip())

    # Validate ranges
    if not (-90 <= lat <= 90):
        raise ValueError(f"Invalid latitude: {lat}. Must be between -90 and 90.")
    if not (-180 <= lon <= 180):
        raise ValueError(f"Invalid longitude: {lon}. Must be between -180 and 180.")

    return lat, lon


def build_bounding_box(lat, lon, buffer_km=2):
    """
    Build a simple bounding box around a center point.

    Parameters:
        lat       : float — center latitude
        lon       : float — center longitude
        buffer_km : float — buffer distance in km (default 2km)

    Returns:
        dict with min_lat, max_lat, min_lon, max_lon
    """
    # Approximate degrees per km
    lat_offset = buffer_km / 111.0         # 1 degree lat ≈ 111km
    lon_offset = buffer_km / (111.0 * abs(lat) + 0.001)  # varies by latitude

    return {
        "min_lat": lat - lat_offset,
        "max_lat": lat + lat_offset,
        "min_lon": lon - lon_offset,
        "max_lon": lon + lon_offset,
        "center_lat": lat,
        "center_lon": lon
    }


# ============================================================
# DATE UTILITIES
# ============================================================

def get_date_windows(months_back=12, window_days=30):
    """
    Generate a list of (start_date, end_date) windows going back N months.

    Parameters:
        months_back  : int — how many months back to generate
        window_days  : int — size of each window in days

    Returns:
        list of (start_str, end_str) tuples in 'YYYY-MM-DD' format
    """
    end_date   = datetime.now()
    start_date = end_date - timedelta(days=30 * months_back)

    windows = []
    current = start_date

    while current < end_date:
        window_end = current + timedelta(days=window_days)
        windows.append((
            current.strftime("%Y-%m-%d"),
            min(window_end, end_date).strftime("%Y-%m-%d")
        ))
        current = window_end

    return windows


def get_last_n_months(n=3):
    """
    Get start and end date for the last N months.

    Returns:
        tuple: (start_str, end_str) in 'YYYY-MM-DD' format
    """
    end   = datetime.now()
    start = end - timedelta(days=30 * n)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def format_date_for_display(date_str):
    """
    Format a date string for dashboard display.
    '2024-01-15' → 'Jan 15, 2024'
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return date_str


# ============================================================
# ALERT FORMATTING
# ============================================================

def get_alert_color(alert_level):
    """
    Return hex color for an alert level.
    Used by dashboard for consistent coloring.
    """
    colors = {
        "normal":   "#38B000",  # green
        "warning":  "#FFB703",  # yellow
        "critical": "#D62828",  # red
        "unknown":  "#888888"   # gray
    }
    return colors.get(alert_level, colors["unknown"])


def get_alert_emoji(alert_level):
    """Return emoji for alert level display."""
    emojis = {
        "normal":   "🟢",
        "warning":  "🟡",
        "critical": "🔴",
        "unknown":  "⚪"
    }
    return emojis.get(alert_level, "⚪")


def format_ndti_for_display(ndti_value):
    """
    Format NDTI value with interpretation label.
    0.08 → "0.0800 (Critical — High Turbidity)"
    """
    if ndti_value is None:
        return "No data"

    if ndti_value > 0.05:
        label = "Critical — High Turbidity"
    elif ndti_value > 0.0:
        label = "Warning — Moderate Turbidity"
    else:
        label = "Normal — Clear Water"

    return f"{ndti_value:.4f} ({label})"


def format_ndvi_for_display(ndvi_value):
    """
    Format NDVI value with interpretation label.
    0.35 → "0.3500 (Warning — Vegetation Stress)"
    """
    if ndvi_value is None:
        return "No data"

    if ndvi_value < 0.2:
        label = "Critical — Severe Stress"
    elif ndvi_value < 0.4:
        label = "Warning — Moderate Stress"
    else:
        label = "Normal — Healthy Vegetation"

    return f"{ndvi_value:.4f} ({label})"


# ============================================================
# QUICK TEST
# ============================================================

if __name__ == "__main__":
    # Test coordinate parsing
    lat, lon = parse_coordinate_string("4.420818973863855, 101.39234334882522")
    print(f"✅ Coordinates parsed: lat={lat}, lon={lon}")

    # Test bounding box
    bbox = build_bounding_box(lat, lon, buffer_km=2)
    print(f"✅ Bounding box: {bbox}")

    # Test date windows
    windows = get_date_windows(months_back=3)
    print(f"✅ Generated {len(windows)} date windows")
    print(f"   First: {windows[0]}")
    print(f"   Last:  {windows[-1]}")

    # Test formatters
    print(f"✅ NDTI format: {format_ndti_for_display(0.08)}")
    print(f"✅ NDVI format: {format_ndvi_for_display(0.35)}")
    print(f"✅ Alert color: {get_alert_color('critical')}")
