"""
================================================================================
src/database.py — UPDATED with agri Greatest Hits + real data focus
================================================================================
"""

import sqlite3
import pandas as pd
import os

SRC_DIR  = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SRC_DIR)
DB_PATH  = os.path.join(ROOT_DIR, "data", "tnb_monitoring.db")


# ============================================================
# INITIALIZE
# ============================================================

def init_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hydro_data (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            date             TEXT NOT NULL,
            zone             TEXT NOT NULL,
            location         TEXT,
            ndti_mean        REAL,
            ndti_min         REAL,
            ndti_max         REAL,
            ndwi_mean        REAL,
            alert_level      TEXT,
            cloud_pct        REAL,
            last_clear_view  TEXT,
            is_greatest_hit  INTEGER DEFAULT 0,
            event_label      TEXT,
            created_at       TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, zone)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agri_data (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT NOT NULL,
            zone            TEXT NOT NULL,
            location        TEXT,
            ndvi_mean       REAL,
            ndvi_min        REAL,
            ndvi_max        REAL,
            ndre_mean       REAL,
            alert_level     TEXT,
            cloud_pct       REAL,
            is_greatest_hit INTEGER DEFAULT 0,
            event_label     TEXT,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, zone)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         TEXT NOT NULL,
            zone         TEXT NOT NULL,
            alert_level  TEXT NOT NULL,
            ndti_mean    REAL,
            ndvi_mean    REAL,
            message      TEXT,
            notified     INTEGER DEFAULT 0,
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {DB_PATH}")


# ============================================================
# HYDRO GREATEST HITS
# ============================================================

def seed_hydro_greatest_hits():
    """Pre-load dramatic turbidity events for reservoir demo."""
    print("💧 Seeding Hydro Greatest Hits...")

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
            "event_label": "Recent critical event — Feb 2026 storm surge"
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

    conn = sqlite3.connect(DB_PATH)
    for r in events:
        conn.execute("""
            INSERT OR REPLACE INTO hydro_data
            (date, zone, location, ndti_mean, ndti_min, ndti_max,
             ndwi_mean, alert_level, cloud_pct, last_clear_view,
             is_greatest_hit, event_label)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            r["date"], r["zone"], r["location"],
            r["ndti_mean"], r["ndti_min"], r["ndti_max"],
            r["ndwi_mean"], r["alert_level"], r["cloud_pct"],
            r["last_clear_view"], r["is_greatest_hit"], r["event_label"]
        ))
    conn.commit()
    conn.close()
    print(f"✅ Hydro Greatest Hits: {len(events)} events seeded")


# ============================================================
# AGRI GREATEST HITS — NEW
# ============================================================

def seed_agri_greatest_hits():
    """
    Pre-load dramatic vegetation stress events for palm oil farm demo.

    NDVI thresholds for Malaysian palm oil:
    > 0.6   = healthy mature palm
    0.4-0.6 = moderate — monitor
    0.2-0.4 = stressed — intervention needed ⚠️
    < 0.2   = severe stress / disease / bare soil ❌

    NDRE thresholds:
    > 0.4   = high chlorophyll, healthy
    0.25-0.4= moderate
    0.15-0.25= warning — nutrient deficiency
    < 0.15  = critical — severe deficiency
    """
    print("🌴 Seeding Agri Greatest Hits...")

    # NOTE: Update zone name and location once manager
    # provides actual palm oil plantation coordinates
    ZONE     = "Felda Jengka"
    LOCATION = "Pahang, Malaysia"

    events = [
        # ── CRITICAL EVENTS (severe stress) ─────────────────
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
            "event_label": "Nutrient deficiency detected — urgent fertilisation needed"
        },
        {
            "date": "2026-01-10", "zone": ZONE, "location": LOCATION,
            "ndvi_mean": 0.17, "ndvi_min": 0.08, "ndvi_max": 0.25,
            "ndre_mean": 0.10, "alert_level": "critical",
            "cloud_pct": 6.2, "is_greatest_hit": 1,
            "event_label": "Recent critical — Jan 2026 vegetation collapse"
        },

        # ── WARNING EVENTS (moderate stress) ────────────────
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
            "event_label": "Below average chlorophyll — fertiliser review needed"
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

        # ── NORMAL EVENTS (for contrast) ─────────────────────
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

    conn = sqlite3.connect(DB_PATH)
    for r in events:
        conn.execute("""
            INSERT OR REPLACE INTO agri_data
            (date, zone, location, ndvi_mean, ndvi_min, ndvi_max,
             ndre_mean, alert_level, cloud_pct, is_greatest_hit, event_label)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            r["date"], r["zone"], r["location"],
            r["ndvi_mean"], r["ndvi_min"], r["ndvi_max"],
            r["ndre_mean"], r["alert_level"], r["cloud_pct"],
            r["is_greatest_hit"], r["event_label"]
        ))
    conn.commit()
    conn.close()

    c = sum(1 for r in events if r["alert_level"] == "critical")
    w = sum(1 for r in events if r["alert_level"] == "warning")
    n = sum(1 for r in events if r["alert_level"] == "normal")
    print(f"✅ Agri Greatest Hits: {len(events)} events seeded")
    print(f"   🔴 Critical : {c}")
    print(f"   🟡 Warning  : {w}")
    print(f"   🟢 Normal   : {n}")


# ============================================================
# EVENT LABEL GENERATOR (for real incoming GEE data)
# ============================================================

def generate_hydro_event_label(ndti_mean, alert_level, cloud_pct=None):
    """
    Auto-generate a human-readable event_label for real hydro GEE data.
    This ensures the dashboard always has meaningful context, even for
    unknown/future situations — not just seeded demo records.

    Priority logic:
      1. Cloud-obscured (high cloud_pct → unreliable reading)
      2. Alert level (critical / warning / normal)
      3. NDTI value range for finer detail
    """
    # Cloud check first — reading may not be reliable
    if cloud_pct is not None and cloud_pct > 50:
        return f"⛅ High cloud cover ({cloud_pct:.0f}%) — reading may be unreliable"

    if alert_level == "critical":
        if ndti_mean is not None and ndti_mean > 0.12:
            return "🔴 Extreme turbidity detected — urgent inspection required"
        elif ndti_mean is not None and ndti_mean > 0.08:
            return "🔴 Critical siltation — dredging/intervention recommended"
        else:
            return "🔴 Critical alert — elevated turbidity, investigate cause"

    elif alert_level == "warning":
        if ndti_mean is not None and ndti_mean > 0.04:
            return "🟡 Elevated turbidity — monitor trend closely"
        else:
            return "🟡 Moderate siltation — review upstream activity"

    else:  # normal
        if ndti_mean is not None and ndti_mean < -0.01:
            return "🟢 Clear water — baseline conditions, no action needed"
        else:
            return "🟢 Normal turbidity — within acceptable range"


def generate_agri_event_label(ndvi_mean, alert_level, ndre_mean=None, cloud_pct=None):
    """
    Auto-generate a human-readable event_label for real agri GEE data.
    This ensures the dashboard always has meaningful context, even for
    unknown/future situations — not just seeded demo records.

    Priority logic:
      1. Cloud-obscured (high cloud_pct → unreliable reading)
      2. Alert level (critical / warning / normal)
      3. NDVI + NDRE values for finer agronomic detail
    """
    # Cloud check first — reading may not be reliable
    if cloud_pct is not None and cloud_pct > 50:
        return f"⛅ High cloud cover ({cloud_pct:.0f}%) — reading may be unreliable"

    if alert_level == "critical":
        if ndvi_mean is not None and ndvi_mean < 0.15:
            return "🔴 Severe vegetation stress — possible disease or bare soil"
        elif ndre_mean is not None and ndre_mean < 0.10:
            return "🔴 Critical chlorophyll deficiency — urgent fertilisation needed"
        else:
            return "🔴 Critical canopy decline — field inspection required"

    elif alert_level == "warning":
        if ndre_mean is not None and ndre_mean < 0.22:
            return "🟡 Below-average chlorophyll — fertiliser review recommended"
        elif ndvi_mean is not None and ndvi_mean < 0.38:
            return "🟡 Moderate vegetation stress — monitor water and nutrients"
        else:
            return "🟡 Canopy stress detected — inspect affected blocks"

    else:  # normal
        if ndvi_mean is not None and ndvi_mean > 0.65:
            return "🟢 Healthy mature canopy — good yield conditions"
        else:
            return "🟢 Vegetation within normal range — continue routine monitoring"


# ============================================================
# WRITE OPERATIONS (real GEE data goes here)
# ============================================================

def write_hydro_data(df):
    """Write real GEE hydro data. Skips duplicates. Auto-generates event_label."""
    if df.empty:
        print("⚠️  No hydro data to write")
        return

    # Auto-generate event_label for any row that doesn't already have one
    if "event_label" not in df.columns:
        df = df.copy()
        df["event_label"] = df.apply(
            lambda row: generate_hydro_event_label(
                ndti_mean   = row.get("ndti_mean"),
                alert_level = row.get("alert_level", "normal"),
                cloud_pct   = row.get("cloud_pct")
            ), axis=1
        )
    else:
        # Fill only missing labels (don't overwrite manual ones)
        mask = df["event_label"].isna() | (df["event_label"] == "")
        df.loc[mask, "event_label"] = df[mask].apply(
            lambda row: generate_hydro_event_label(
                ndti_mean   = row.get("ndti_mean"),
                alert_level = row.get("alert_level", "normal"),
                cloud_pct   = row.get("cloud_pct")
            ), axis=1
        )

    conn = sqlite3.connect(DB_PATH)
    df.to_sql("hydro_data_temp", conn, if_exists="replace", index=False)
    conn.execute("""
        INSERT OR IGNORE INTO hydro_data
        (date, zone, location, ndti_mean, ndti_min, ndti_max,
         ndwi_mean, alert_level, cloud_pct, last_clear_view, event_label)
        SELECT date, zone, location, ndti_mean, ndti_min, ndti_max,
               ndwi_mean, alert_level, cloud_pct, last_clear_view, event_label
        FROM hydro_data_temp
    """)
    conn.execute("DROP TABLE hydro_data_temp")
    conn.commit()
    conn.close()
    print(f"✅ Written {len(df)} real hydro records")


def write_agri_data(df):
    """Write real GEE agri data. Skips duplicates. Auto-generates event_label."""
    if df.empty:
        print("⚠️  No agri data to write")
        return

    # Auto-generate event_label for any row that doesn't already have one
    if "event_label" not in df.columns:
        df = df.copy()
        df["event_label"] = df.apply(
            lambda row: generate_agri_event_label(
                ndvi_mean   = row.get("ndvi_mean"),
                alert_level = row.get("alert_level", "normal"),
                ndre_mean   = row.get("ndre_mean"),
                cloud_pct   = row.get("cloud_pct")
            ), axis=1
        )
    else:
        # Fill only missing labels (don't overwrite manual ones)
        mask = df["event_label"].isna() | (df["event_label"] == "")
        df.loc[mask, "event_label"] = df[mask].apply(
            lambda row: generate_agri_event_label(
                ndvi_mean   = row.get("ndvi_mean"),
                alert_level = row.get("alert_level", "normal"),
                ndre_mean   = row.get("ndre_mean"),
                cloud_pct   = row.get("cloud_pct")
            ), axis=1
        )

    conn = sqlite3.connect(DB_PATH)
    df.to_sql("agri_data_temp", conn, if_exists="replace", index=False)
    conn.execute("""
        INSERT OR IGNORE INTO agri_data
        (date, zone, location, ndvi_mean, ndvi_min, ndvi_max,
         ndre_mean, alert_level, cloud_pct, event_label)
        SELECT date, zone, location, ndvi_mean, ndvi_min, ndvi_max,
               ndre_mean, alert_level, cloud_pct, event_label
        FROM agri_data_temp
    """)
    conn.execute("DROP TABLE agri_data_temp")
    conn.commit()
    conn.close()
    print(f"✅ Written {len(df)} real agri records")


def log_alert(zone, alert_level, date,
              ndti_mean=None, ndvi_mean=None, message=None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO alerts_log
        (date, zone, alert_level, ndti_mean, ndvi_mean, message)
        VALUES (?,?,?,?,?,?)
    """, (date, zone, alert_level, ndti_mean, ndvi_mean, message))
    conn.commit()
    conn.close()


# ============================================================
# READ OPERATIONS — 24 MONTHS DEFAULT
# ============================================================

def read_hydro_data(zone=None, months=24):
    conn = sqlite3.connect(DB_PATH)
    if zone:
        query  = """SELECT * FROM hydro_data
                    WHERE zone = ? AND date >= date('now', ?)
                    ORDER BY date ASC"""
        params = [zone, f"-{months} months"]
    else:
        query  = """SELECT * FROM hydro_data
                    WHERE date >= date('now', ?)
                    ORDER BY date ASC"""
        params = [f"-{months} months"]
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df


def read_agri_data(zone=None, months=24):
    conn = sqlite3.connect(DB_PATH)
    if zone:
        query  = """SELECT * FROM agri_data
                    WHERE zone = ? AND date >= date('now', ?)
                    ORDER BY date ASC"""
        params = [zone, f"-{months} months"]
    else:
        query  = """SELECT * FROM agri_data
                    WHERE date >= date('now', ?)
                    ORDER BY date ASC"""
        params = [f"-{months} months"]
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df


def read_greatest_hits(zone_type="hydro"):
    """
    Return Greatest Hits events for demo panel.
    zone_type: 'hydro' or 'agri'
    """
    conn  = sqlite3.connect(DB_PATH)
    table = "hydro_data" if zone_type == "hydro" else "agri_data"
    df    = pd.read_sql(f"""
        SELECT * FROM {table}
        WHERE is_greatest_hit = 1
        ORDER BY
            CASE alert_level
                WHEN 'critical' THEN 1
                WHEN 'warning'  THEN 2
                ELSE 3
            END, date DESC
    """, conn)
    conn.close()
    return df


def read_latest_status():
    conn  = sqlite3.connect(DB_PATH)
    hydro = pd.read_sql(
        "SELECT * FROM hydro_data ORDER BY date DESC LIMIT 1", conn
    )
    agri  = pd.read_sql(
        "SELECT * FROM agri_data  ORDER BY date DESC LIMIT 1", conn
    )
    conn.close()
    return {"hydro": hydro, "agri": agri}


def read_alerts_log(limit=50):
    conn = sqlite3.connect(DB_PATH)
    df   = pd.read_sql("""
        SELECT * FROM alerts_log
        ORDER BY created_at DESC LIMIT ?
    """, conn, params=[limit])
    conn.close()
    return df


# ============================================================
# HEALTH CHECK
# ============================================================

def check_database_health():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    print(f"\n{'='*55}")
    print(f"  DATABASE HEALTH CHECK")
    print(f"{'='*55}")

    for table in ["hydro_data", "agri_data", "alerts_log"]:
        r = conn.execute(
            f"SELECT COUNT(*), MIN(date), MAX(date) FROM {table}"
        ).fetchone()
        print(f"\n  {table}:")
        print(f"    Total records : {r[0]}")
        print(f"    Earliest date : {r[1]}")
        print(f"    Latest date   : {r[2]}")

    # Alert breakdown per table
    for table, label in [("hydro_data","💧 Hydro"), ("agri_data","🌴 Agri")]:
        alerts = conn.execute(f"""
            SELECT alert_level, COUNT(*) FROM {table}
            GROUP BY alert_level
        """).fetchall()
        print(f"\n  {label} alert breakdown:")
        for level, count in alerts:
            e = "🔴" if level=="critical" else "🟡" if level=="warning" else "🟢"
            print(f"    {e} {level}: {count}")

    # What read functions return
    for label, query in [
        ("read_hydro_data()", "SELECT COUNT(*) FROM hydro_data WHERE date >= date('now','-24 months')"),
        ("read_agri_data()",  "SELECT COUNT(*) FROM agri_data  WHERE date >= date('now','-24 months')")
    ]:
        count = conn.execute(query).fetchone()[0]
        print(f"\n  {label} returns: {count} records")

    conn.close()
    print(f"\n{'='*55}\n")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    init_database()
    seed_hydro_greatest_hits()
    seed_agri_greatest_hits()
    check_database_health()
