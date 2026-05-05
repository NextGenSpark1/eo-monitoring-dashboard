

import os
import sys
import pandas as pd
from supabase import create_client, Client




# CONNECTION


def get_supabase_client() -> Client:
    """
    Get Supabase client using credentials from secrets or env vars.
    Works on local machine and Streamlit Cloud.
    """
    try:
        # Streamlit Cloud / local with secrets.toml
        import streamlit as st
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["service_key"]
        return create_client(url, key)

    except Exception:
        pass

    # GitHub Actions / environment variables
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if url and key:
        return create_client(url, key)

    raise Exception(
        "Supabase credentials not found.\n"
    )


# INITIALIZE 

def init_database():
    """
    Verify Supabase connection is working.
    Tables must be created manually in Supabase SQL Editor.
    (See CREATE TABLE SQL in project README)
    """
    try:
        client = get_supabase_client()
        # Quick test query
        client.table("hydro_data").select("id").limit(1).execute()
        print("✅ Supabase connection verified")
        print(f"   Tables: hydro_data, agri_data, alerts_log")
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        raise


# GREATEST HITS SEEDERS

def seed_hydro_greatest_hits():
    """Pre-load dramatic turbidity events for reservoir demo."""
    print("💧 Seeding Hydro Greatest Hits to Supabase...")

    events = [
        # CRITICAL
        {
            "date": "2025-01-15", "zone": "Empangan Sultan Abu Bakar",
            "location": "Pahang, Malaysia",
            "ndti_mean": 0.142, "ndti_min": 0.098, "ndti_max": 0.201,
            "ndwi_mean": 0.312, "alert_level": "critical",
            "cloud_pct": 8.2,  "last_clear_view": "2025-01-15",
            "is_greatest_hit": 1,
            "event_label": "Post-storm runoff — Jan 2025 flood event"
        },
        {
            "date": "2025-03-20", "zone": "Empangan Sultan Abu Bakar",
            "location": "Pahang, Malaysia",
            "ndti_mean": 0.118, "ndti_min": 0.087, "ndti_max": 0.165,
            "ndwi_mean": 0.298, "alert_level": "critical",
            "cloud_pct": 12.5, "last_clear_view": "2025-03-20",
            "is_greatest_hit": 1,
            "event_label": "Land clearing upstream detected"
        },
        {
            "date": "2025-07-08", "zone": "Empangan Sultan Abu Bakar",
            "location": "Pahang, Malaysia",
            "ndti_mean": 0.096, "ndti_min": 0.071, "ndti_max": 0.143,
            "ndwi_mean": 0.401, "alert_level": "critical",
            "cloud_pct": 5.1,  "last_clear_view": "2025-07-08",
            "is_greatest_hit": 1,
            "event_label": "Monsoon siltation peak — dredging recommended"
        },
        {
            "date": "2025-11-02", "zone": "Empangan Sultan Abu Bakar",
            "location": "Pahang, Malaysia",
            "ndti_mean": 0.134, "ndti_min": 0.102, "ndti_max": 0.189,
            "ndwi_mean": 0.356, "alert_level": "critical",
            "cloud_pct": 3.8,  "last_clear_view": "2025-11-02",
            "is_greatest_hit": 1,
            "event_label": "Northeast monsoon onset — highest silt of year"
        },
        {
            "date": "2026-02-14", "zone": "Empangan Sultan Abu Bakar",
            "location": "Pahang, Malaysia",
            "ndti_mean": 0.109, "ndti_min": 0.081, "ndti_max": 0.157,
            "ndwi_mean": 0.388, "alert_level": "critical",
            "cloud_pct": 7.3,  "last_clear_view": "2026-02-14",
            "is_greatest_hit": 1,
            "event_label": "Recent critical — Feb 2026 storm surge"
        },
        # WARNING
        {
            "date": "2025-02-10", "zone": "Empangan Sultan Abu Bakar",
            "location": "Pahang, Malaysia",
            "ndti_mean": 0.038, "ndti_min": 0.021, "ndti_max": 0.062,
            "ndwi_mean": 0.285, "alert_level": "warning",
            "cloud_pct": 15.3, "last_clear_view": "2025-02-10",
            "is_greatest_hit": 1,
            "event_label": "Moderate siltation — monitor closely"
        },
        {
            "date": "2025-09-15", "zone": "Empangan Sultan Abu Bakar",
            "location": "Pahang, Malaysia",
            "ndti_mean": 0.042, "ndti_min": 0.028, "ndti_max": 0.071,
            "ndwi_mean": 0.271, "alert_level": "warning",
            "cloud_pct": 18.9, "last_clear_view": "2025-09-15",
            "is_greatest_hit": 1,
            "event_label": "Inter-monsoon turbidity increase"
        },
        {
            "date": "2026-01-20", "zone": "Empangan Sultan Abu Bakar",
            "location": "Pahang, Malaysia",
            "ndti_mean": 0.033, "ndti_min": 0.018, "ndti_max": 0.055,
            "ndwi_mean": 0.261, "alert_level": "warning",
            "cloud_pct": 11.4, "last_clear_view": "2026-01-20",
            "is_greatest_hit": 1,
            "event_label": "Early 2026 — siltation building up"
        },
        # NORMAL
        {
            "date": "2025-05-20", "zone": "Empangan Sultan Abu Bakar",
            "location": "Pahang, Malaysia",
            "ndti_mean": -0.023, "ndti_min": -0.041, "ndti_max": -0.008,
            "ndwi_mean": 0.198, "alert_level": "normal",
            "cloud_pct": 6.4,  "last_clear_view": "2025-05-20",
            "is_greatest_hit": 1,
            "event_label": "Baseline — clear water, no dredging needed"
        },
        {
            "date": "2025-08-05", "zone": "Empangan Sultan Abu Bakar",
            "location": "Pahang, Malaysia",
            "ndti_mean": -0.018, "ndti_min": -0.035, "ndti_max": -0.004,
            "ndwi_mean": 0.187, "alert_level": "normal",
            "cloud_pct": 9.2,  "last_clear_view": "2025-08-05",
            "is_greatest_hit": 1,
            "event_label": "Post-dry season — minimal siltation"
        },
        {
            "date": "2026-03-10", "zone": "Empangan Sultan Abu Bakar",
            "location": "Pahang, Malaysia",
            "ndti_mean": -0.012, "ndti_min": -0.028, "ndti_max": 0.003,
            "ndwi_mean": 0.201, "alert_level": "normal",
            "cloud_pct": 4.1,  "last_clear_view": "2026-03-10",
            "is_greatest_hit": 1,
            "event_label": "Recent normal — March 2026 baseline"
        },
    ]

    _upsert_records("hydro_data", events)
    print(f"✅ Hydro Greatest Hits: {len(events)} events seeded")


def seed_agri_greatest_hits():
    """Pre-load vegetation stress events for Felda Jengka demo."""
    print("🌴 Seeding Agri Greatest Hits to Supabase...")

    ZONE     = "Felda Jengka"
    LOCATION = "Pahang, Malaysia"

    events = [
        # CRITICAL
        {
            "date": "2025-02-01", "zone": ZONE, "location": LOCATION,
            "ndvi_mean": 0.18, "ndvi_min": 0.09, "ndvi_max": 0.27,
            "ndre_mean": 0.11, "alert_level": "critical",
            "cloud_pct": 7.3, "is_greatest_hit": 1,
            "event_label": "Severe drought stress — NDVI critically low"
        },
        {
            "date": "2025-04-15", "zone": ZONE, "location": LOCATION,
            "ndvi_mean": 0.15, "ndvi_min": 0.08, "ndvi_max": 0.22,
            "ndre_mean": 0.09, "alert_level": "critical",
            "cloud_pct": 5.1, "is_greatest_hit": 1,
            "event_label": "Ganoderma disease suspected — abnormal NDVI drop"
        },
        {
            "date": "2025-08-20", "zone": ZONE, "location": LOCATION,
            "ndvi_mean": 0.19, "ndvi_min": 0.11, "ndvi_max": 0.28,
            "ndre_mean": 0.12, "alert_level": "critical",
            "cloud_pct": 9.8, "is_greatest_hit": 1,
            "event_label": "Nutrient deficiency — urgent fertilisation needed"
        },
        {
            "date": "2026-01-10", "zone": ZONE, "location": LOCATION,
            "ndvi_mean": 0.17, "ndvi_min": 0.08, "ndvi_max": 0.25,
            "ndre_mean": 0.10, "alert_level": "critical",
            "cloud_pct": 6.2, "is_greatest_hit": 1,
            "event_label": "Recent critical — Jan 2026 vegetation collapse"
        },
        # WARNING
        {
            "date": "2025-03-10", "zone": ZONE, "location": LOCATION,
            "ndvi_mean": 0.35, "ndvi_min": 0.22, "ndvi_max": 0.48,
            "ndre_mean": 0.21, "alert_level": "warning",
            "cloud_pct": 14.1, "is_greatest_hit": 1,
            "event_label": "Moderate water stress — dry season impact"
        },
        {
            "date": "2025-06-25", "zone": ZONE, "location": LOCATION,
            "ndvi_mean": 0.32, "ndvi_min": 0.19, "ndvi_max": 0.44,
            "ndre_mean": 0.20, "alert_level": "warning",
            "cloud_pct": 18.3, "is_greatest_hit": 1,
            "event_label": "Below average chlorophyll — fertiliser review"
        },
        {
            "date": "2025-10-05", "zone": ZONE, "location": LOCATION,
            "ndvi_mean": 0.38, "ndvi_min": 0.25, "ndvi_max": 0.51,
            "ndre_mean": 0.23, "alert_level": "warning",
            "cloud_pct": 11.7, "is_greatest_hit": 1,
            "event_label": "Partial canopy stress — inspect block 3 and 7"
        },
        {
            "date": "2026-02-20", "zone": ZONE, "location": LOCATION,
            "ndvi_mean": 0.33, "ndvi_min": 0.21, "ndvi_max": 0.45,
            "ndre_mean": 0.22, "alert_level": "warning",
            "cloud_pct": 8.9, "is_greatest_hit": 1,
            "event_label": "Recent warning — Feb 2026 vegetation decline"
        },
        # NORMAL
        {
            "date": "2025-05-01", "zone": ZONE, "location": LOCATION,
            "ndvi_mean": 0.72, "ndvi_min": 0.61, "ndvi_max": 0.84,
            "ndre_mean": 0.51, "alert_level": "normal",
            "cloud_pct": 4.2, "is_greatest_hit": 1,
            "event_label": "Peak health — post-rain canopy flush"
        },
        {
            "date": "2025-07-15", "zone": ZONE, "location": LOCATION,
            "ndvi_mean": 0.68, "ndvi_min": 0.57, "ndvi_max": 0.79,
            "ndre_mean": 0.47, "alert_level": "normal",
            "cloud_pct": 6.8, "is_greatest_hit": 1,
            "event_label": "Healthy mature canopy — good yield expected"
        },
        {
            "date": "2025-12-01", "zone": ZONE, "location": LOCATION,
            "ndvi_mean": 0.65, "ndvi_min": 0.54, "ndvi_max": 0.76,
            "ndre_mean": 0.44, "alert_level": "normal",
            "cloud_pct": 9.1, "is_greatest_hit": 1,
            "event_label": "Year-end baseline — vegetation stable"
        },
        {
            "date": "2026-03-15", "zone": ZONE, "location": LOCATION,
            "ndvi_mean": 0.63, "ndvi_min": 0.52, "ndvi_max": 0.74,
            "ndre_mean": 0.43, "alert_level": "normal",
            "cloud_pct": 5.5, "is_greatest_hit": 1,
            "event_label": "Recent normal — March 2026 baseline"
        },
    ]

    _upsert_records("agri_data", events)
    print(f"✅ Agri Greatest Hits: {len(events)} events seeded")


# INTERNAL HELPER

def _upsert_records(table, records):
    """
    Upsert records into Supabase table.
    Uses ON CONFLICT(date, zone) DO UPDATE — no duplicates.
    """
    client = get_supabase_client()
    client.table(table).upsert(
        records,
        on_conflict="date,zone"
    ).execute()



# WRITE OPERATIONS 


def write_hydro_data(df):
    """Write real GEE hydro DataFrame to Supabase."""
    if df.empty:
        print("⚠️  No hydro data to write")
        return
    records = df.to_dict(orient="records")
    _upsert_records("hydro_data", records)
    print(f"✅ Written {len(records)} hydro records to Supabase")


def write_agri_data(df):
    """Write real GEE agri DataFrame to Supabase."""
    if df.empty:
        print("⚠️  No agri data to write")
        return
    records = df.to_dict(orient="records")
    _upsert_records("agri_data", records)
    print(f"✅ Written {len(records)} agri records to Supabase")


def log_alert(zone, alert_level, date,
              ndti_mean=None, ndvi_mean=None, message=None):
    """Log alert to Supabase alerts_log table."""
    client = get_supabase_client()
    client.table("alerts_log").insert({
        "date":        date,
        "zone":        zone,
        "alert_level": alert_level,
        "ndti_mean":   ndti_mean,
        "ndvi_mean":   ndvi_mean,
        "message":     message
    }).execute()



# READ OPERATIONS 

def read_hydro_data(zone=None, months=24):
    """
    Read hydro data from Supabase.
    Same signature as SQLite version — app.py needs zero changes.
    """
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=30 * months)).strftime("%Y-%m-%d")

    client = get_supabase_client()
    query  = client.table("hydro_data").select("*").gte("date", cutoff).order("date")

    if zone:
        query = query.eq("zone", zone)

    result = query.execute()
    return pd.DataFrame(result.data)


def read_agri_data(zone=None, months=24):
    """
    Read agri data from Supabase.
    Same signature as SQLite version — app.py needs zero changes.
    """
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=30 * months)).strftime("%Y-%m-%d")

    client = get_supabase_client()
    query  = client.table("agri_data").select("*").gte("date", cutoff).order("date")

    if zone:
        query = query.eq("zone", zone)

    result = query.execute()
    return pd.DataFrame(result.data)


def read_greatest_hits(zone_type="hydro"):
    """
    Read Greatest Hits events for demo panel.
    zone_type: 'hydro' or 'agri'
    """
    table  = "hydro_data" if zone_type == "hydro" else "agri_data"
    client = get_supabase_client()
    result = (
        client.table(table)
        .select("date,zone,ndti_mean,ndvi_mean,alert_level,event_label")
        .eq("is_greatest_hit", 1)
        .order("alert_level")
        .execute()
    )
    return pd.DataFrame(result.data)


def read_latest_status():
    """Get most recent record per zone for KPI panels."""
    client = get_supabase_client()

    hydro  = client.table("hydro_data").select("*").order(
        "date", desc=True
    ).limit(1).execute()

    agri   = client.table("agri_data").select("*").order(
        "date", desc=True
    ).limit(1).execute()

    return {
        "hydro": pd.DataFrame(hydro.data),
        "agri":  pd.DataFrame(agri.data)
    }


def read_alerts_log(limit=50):
    """Read recent alerts for dashboard alert panel."""
    client = get_supabase_client()
    result = (
        client.table("alerts_log")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return pd.DataFrame(result.data)


# SUBSCRIBERS

def add_subscriber(chat_id):
    """Add a Telegram chat ID to subscribers table. Idempotent — won't duplicate."""
    client = get_supabase_client()
    try:
        client.table("subscribers").upsert(
            {"chat_id": str(chat_id)},
            on_conflict="chat_id"
        ).execute()
        return True
    except Exception as e:
        print(f"Failed to add subscriber: {e}")
        return False


def get_all_subscribers():
    """Return list of all subscriber chat IDs."""
    client = get_supabase_client()
    try:
        result = client.table("subscribers").select("chat_id").execute()
        return [row["chat_id"] for row in result.data]
    except Exception as e:
        print(f"Failed to fetch subscribers: {e}")
        return []


def remove_subscriber(chat_id):
    """Remove a subscriber by chat ID."""
    client = get_supabase_client()
    try:
        client.table("subscribers").delete().eq("chat_id", str(chat_id)).execute()
        return True
    except Exception:
        return False


# HEALTH CHECK

def check_database_health():
    """Verify Supabase connection and print record counts."""
    print(f"\n{'='*55}")
    print(f"  SUPABASE HEALTH CHECK")
    print(f"{'='*55}")

    client = get_supabase_client()

    for table in ["hydro_data", "agri_data", "alerts_log"]:
        try:
            result = client.table(table).select(
                "id", count="exact"
            ).execute()
            count = result.count
            print(f"\n  {table}: {count} records")
        except Exception as e:
            print(f"\n  {table}: ❌ Error — {e}")

    # Alert breakdown
    for table, label in [("hydro_data","💧 Hydro"), ("agri_data","🌴 Agri")]:
        for level in ["critical", "warning", "normal"]:
            r = client.table(table).select(
                "id", count="exact"
            ).eq("alert_level", level).execute()
            e = "🔴" if level=="critical" else "🟡" if level=="warning" else "🟢"
            print(f"    {e} {label} {level}: {r.count}")

    print(f"\n{'='*55}\n")

def save_zone_to_watchlist(zone_name: str, lat: float,
                           lon: float, zone_type: str) -> dict:
    """
    Save a zone to the watchlist (saved_zones table).
    Creates a persistent tab for this zone in the dashboard.
 
    Returns:
        dict: {saved: bool, message: str}
    """
    client = get_supabase_client()
 
    try:
        client.table("saved_zones").upsert(
            {
                "zone_name": zone_name,
                "lat":       lat,
                "lon":       lon,
                "zone_type": zone_type
            },
            on_conflict="zone_name"
        ).execute()
 
        return {
            "saved":   True,
            "message": f"✅ {zone_name} added to watchlist"
        }
 
    except Exception as e:
        return {
            "saved":   False,
            "message": f"❌ Failed to save zone: {e}"
        }
 
 
def read_saved_zones() -> list:
    """
    Read all zones in the watchlist.
    Used by app.py to build dynamic tabs.

    Returns:
        list of dicts with zone_name, lat, lon, zone_type, added_at
    """
    client = get_supabase_client()
 
    try:
        result = (
            client.table("saved_zones")
            .select("*")
            .order("added_at")
            .execute()
            )
        return result.data
 
    except Exception as e:
        print(f"❌ Failed to read saved zones: {e}")
        return []
 
 
def remove_saved_zone(zone_name: str) -> dict:
    """
    Remove a zone from the watchlist.
    Called when client clicks 'Remove' button on a tab.
 
    Returns:
        dict: {removed: bool, message: str}
    """
    client = get_supabase_client()
 
    try:
        client.table("saved_zones").delete().eq(
            "zone_name", zone_name
        ).execute()
 
        return {
            "removed": True,
            "message": f"✅ {zone_name} removed from watchlist"
        }
 
    except Exception as e:
        return {
            "removed": False,
            "message": f"❌ Failed to remove zone: {e}"
        }
 
 
def zone_in_watchlist(zone_name: str) -> bool:
    """
    Check if a zone is already in the watchlist.
    Used in Search tab to show correct button state.
 
    Returns:
        bool
    """
    client = get_supabase_client()
 
    try:
        result = (
            client.table("saved_zones")
            .select("id")
            .eq("zone_name", zone_name)
            .execute()
        )
        return len(result.data) > 0
 
    except Exception:
        return False
 

# MAIN

if __name__ == "__main__":
    print("Setting up Supabase database...\n")
    init_database()
    seed_hydro_greatest_hits()
    seed_agri_greatest_hits()
    check_database_health()