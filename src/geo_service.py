"""
================================================================================
src/geo_service.py

================================================================================
Developer  : Mohamed Nawran (AI Platform Engineering)
Description: Converts place names to coordinates and validates coordinate input.
             Uses Nominatim (OpenStreetMap) — free, no API key needed.
             Focused on Malaysian locations.
================================================================================
"""

import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


# ============================================================
# GEOCODER SETUP
# ============================================================

# User agent must be unique — identifies your app to Nominatim
geolocator = Nominatim(user_agent="tnb_siltation_monitor_nextgenspark")


# ============================================================
# PLACE NAME → COORDINATES
# ============================================================

def search_place(place_name: str) -> dict:
    """
    Convert a place name to coordinates using Nominatim.
    Biased toward Malaysia for better results.

    Parameters:
        place_name : str — e.g. "Tasik Kenyir", "Empangan Semenyih"

    Returns:
        dict with keys: name, lat, lon, display_name, found
        found=False if location not found
    """

    # Add Malaysia context if not already mentioned
    search_query = place_name
    if "malaysia" not in place_name.lower():
        search_query = f"{place_name}, Malaysia"

    try:
        # Small delay to respect Nominatim rate limit (1 req/sec)
        time.sleep(1)

        location = geolocator.geocode(
            search_query,
            timeout        = 10,
            country_codes  = ["MY"],   # Bias to Malaysia
            exactly_one    = True
        )

        if location is None:
            # Try without country restriction
            location = geolocator.geocode(search_query, timeout=10)

        if location is None:
            return {
                "found":        False,
                "error":        f"Location '{place_name}' not found. Try adding more detail.",
                "name":         place_name,
                "lat":          None,
                "lon":          None,
                "display_name": None
            }

        return {
            "found":        True,
            "name":         place_name,
            "lat":          round(location.latitude,  6),
            "lon":          round(location.longitude, 6),
            "display_name": location.address,
            "error":        None
        }

    except GeocoderTimedOut:
        return {
            "found": False,
            "error": "Search timed out. Please try again.",
            "name":  place_name, "lat": None, "lon": None, "display_name": None
        }
    except GeocoderServiceError as e:
        return {
            "found": False,
            "error": f"Geocoding service error: {e}",
            "name":  place_name, "lat": None, "lon": None, "display_name": None
        }
    except Exception as e:
        return {
            "found": False,
            "error": f"Unexpected error: {e}",
            "name":  place_name, "lat": None, "lon": None, "display_name": None
        }


# ============================================================
# COORDINATE STRING → LAT/LON
# ============================================================

def parse_coordinates(coord_input: str) -> dict:
    """
    Parse a coordinate string into lat/lon.

    Accepts multiple formats:
    - "4.420818, 101.392343"
    - "4.420818 101.392343"
    - "4°25'14.9\"N 101°23'32.8\"E"  ← DMS format

    Returns:
        dict with keys: lat, lon, valid, error
    """
    coord_input = coord_input.strip()

    # Try decimal format first (most common)
    try:
        # Remove common separators
        cleaned = coord_input.replace(",", " ").replace(";", " ")
        parts   = cleaned.split()

        # Filter to numeric parts only
        numeric = []
        for p in parts:
            try:
                numeric.append(float(p))
            except ValueError:
                continue

        if len(numeric) >= 2:
            lat, lon = numeric[0], numeric[1]

            # Validate ranges
            if not (-90 <= lat <= 90):
                return {
                    "valid": False,
                    "error": f"Invalid latitude {lat}. Must be between -90 and 90.",
                    "lat": None, "lon": None
                }
            if not (-180 <= lon <= 180):
                return {
                    "valid": False,
                    "error": f"Invalid longitude {lon}. Must be between -180 and 180.",
                    "lat": None, "lon": None
                }

            # Quick sanity check for Malaysia
            if not (0.8 <= lat <= 7.5 and 99.5 <= lon <= 119.5):
                return {
                    "valid":   True,   # Valid coordinates but outside Malaysia
                    "warning": f"⚠️ These coordinates ({lat}, {lon}) appear to be outside Malaysia. Continuing anyway.",
                    "lat":     round(lat, 6),
                    "lon":     round(lon, 6),
                    "error":   None
                }

            return {
                "valid":   True,
                "lat":     round(lat, 6),
                "lon":     round(lon, 6),
                "error":   None,
                "warning": None
            }

        return {
            "valid": False,
            "error": "Could not parse coordinates. Use format: 4.4208, 101.3923",
            "lat":   None, "lon": None
        }

    except Exception as e:
        return {
            "valid": False,
            "error": f"Could not parse: {e}. Use format: 4.4208, 101.3923",
            "lat":   None, "lon": None
        }


# ============================================================
# SMART INPUT DETECTOR
# ============================================================

def detect_and_resolve(user_input: str) -> dict:
    """
    Automatically detects whether the input is:
    - A place name ("Tasik Kenyir")
    - Coordinates ("4.420818, 101.392343")

    Then resolves to lat/lon either way.

    This is the MAIN function Streamlit calls.

    Returns:
        dict with: lat, lon, name, display_name, input_type, valid, error
    """
    user_input = user_input.strip()

    if not user_input:
        return {"valid": False, "error": "Please enter a location or coordinates."}

    # Check if it looks like coordinates
    # Heuristic: if first character is digit, minus, or dot → coordinates
    first_char = user_input[0]
    looks_like_coords = (
        first_char.isdigit() or
        first_char in ["-", "+", "."] or
        user_input.count(",") == 1 and any(c.isdigit() for c in user_input)
    )

    if looks_like_coords:
        result = parse_coordinates(user_input)
        if result["valid"]:
            return {
                "valid":        True,
                "lat":          result["lat"],
                "lon":          result["lon"],
                "name":         f"Custom Location ({result['lat']}, {result['lon']})",
                "display_name": f"Coordinates: {result['lat']}, {result['lon']}",
                "input_type":   "coordinates",
                "warning":      result.get("warning"),
                "error":        None
            }
        # If coordinate parsing fails, try as place name
        # (e.g., "5.0, 102.0" failed but "5.0 102.0" might work)

    # Try as place name
    result = search_place(user_input)
    if result["found"]:
        return {
            "valid":        True,
            "lat":          result["lat"],
            "lon":          result["lon"],
            "name":         result["name"],
            "display_name": result["display_name"],
            "input_type":   "place_name",
            "warning":      None,
            "error":        None
        }

    # Both failed
    return {
        "valid":      False,
        "error":      result["error"] or "Could not find location. Try a different name or paste coordinates.",
        "input_type": "unknown",
        "lat":        None,
        "lon":        None
    }


# ============================================================
# POPULAR MALAYSIAN WATER BODIES (quick suggestions)
# ============================================================

MALAYSIA_SUGGESTIONS = [
    {"name": "Empangan Sultan Abu Bakar",  "lat": 4.4208,  "lon": 101.3923, "type": "hydro"},
    {"name": "Tasik Kenyir",               "lat": 5.0500,  "lon": 102.6000, "type": "hydro"},
    {"name": "Empangan Semenyih",          "lat": 2.9833,  "lon": 101.8500, "type": "hydro"},
    {"name": "Empangan Langat",            "lat": 3.0333,  "lon": 101.7833, "type": "hydro"},
    {"name": "Empangan Klang Gates",       "lat": 3.2167,  "lon": 101.7667, "type": "hydro"},
    {"name": "Empangan Beris",             "lat": 5.9000,  "lon": 100.7167, "type": "hydro"},
    {"name": "Tasik Bera",                 "lat": 3.2500,  "lon": 102.5667, "type": "hydro"},
    {"name": "Felda Jengka",               "lat": 3.6800,  "lon": 102.5100, "type": "agri"},
    {"name": "Felda Sahom",                "lat": 4.1500,  "lon": 101.2000, "type": "agri"},
    {"name": "Felda Gunung Besout",        "lat": 4.0333,  "lon": 101.3167, "type": "agri"},
]


def get_suggestions(query: str = "") -> list:
    """
    Return location suggestions matching the query.
    Used for autocomplete in the search box.
    """
    if not query:
        return MALAYSIA_SUGGESTIONS

    query_lower = query.lower()
    return [
        s for s in MALAYSIA_SUGGESTIONS
        if query_lower in s["name"].lower()
    ]


# ============================================================
# QUICK TEST
# ============================================================

if __name__ == "__main__":
    print("Testing geocoder...\n")

    tests = [
        "Tasik Kenyir",
        "4.420818, 101.392343",
        "Empangan Semenyih",
        "5.123 102.456",
        "nonexistent place xyz"
    ]

    for test in tests:
        print(f"Input: '{test}'")
        result = detect_and_resolve(test)
        if result["valid"]:
            print(f"  ✅ {result['lat']}, {result['lon']} ({result['input_type']})")
            if result.get("warning"):
                print(f"  ⚠️  {result['warning']}")
        else:
            print(f"  ❌ {result['error']}")
        print()
