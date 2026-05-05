import sys
import os
import pandas as pd
from datetime import datetime, timedelta
 
# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
 
from gee_logic import (
    initialize_gee,
    get_geometry,
    load_sentinel2,
    compute_ndti,
    compute_ndwi,      # ← FIXED: was missing, alert_system was using compute_ndvi
    compute_ndvi,
    compute_ndre,      # ← NEW: now properly computing NDRE for farm
    extract_stats,
    compute_alert_level,
    RESERVOIR_CONFIG,
    FARM_CONFIG
)
from database import (
    init_database,
    write_hydro_data,
    write_agri_data,
    log_alert
)
from telegram_helper import (   # ← NEW: real Telegram integration
    send_critical_alert,
    send_warning_alert
)
 
 
# ============================================================
# CONFIGURATION
# ============================================================
 
TODAY     = datetime.now().strftime("%Y-%m-%d")
MONTH_AGO = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
 
 
# ============================================================
# MAIN DAILY CHECK
# ============================================================
 
def run_daily_check():
    """
    Run by GitHub Actions every day at 2AM Malaysia Time.
 
    Steps:
    1. Initialize GEE (headless auth via service account)
    2. Initialize Supabase connection
    3. Process reservoir — NDTI + NDWI
    4. Process farm — NDVI + NDRE
    5. Send Telegram alerts if critical/warning
    6. Write new data to Supabase
    7. Print summary report
    """
 
    print("=" * 55)
    print(f"  TNB Siltation Monitor — Daily Check")
    print(f"  Date : {TODAY}")
    print("=" * 55)
 
    # Initialize
    initialize_gee()
    init_database()
 
    alerts_triggered = []
    hydro_records    = []
    agri_records     = []
 
    # ── RESERVOIR: Empangan Sultan Abu Bakar ──────────────
    print(f"\n💧 Checking: {RESERVOIR_CONFIG['name']}")
 
    reservoir_geom = get_geometry(RESERVOIR_CONFIG)
    image, cloud_pct, last_clear = load_sentinel2(
        reservoir_geom, MONTH_AGO, TODAY, cloud_threshold=30
    )
 
    if image is None:
        print("   ⚠️  No clear images — skipping reservoir")
    else:
        # FIXED: compute_ndwi (was using compute_ndvi before — bug)
        ndti_stats = extract_stats(compute_ndti(image), reservoir_geom, "NDTI")
        ndwi_stats = extract_stats(compute_ndwi(image), reservoir_geom, "NDWI")
        alert      = compute_alert_level(ndti_mean=ndti_stats["NDTI_mean"])
 
        print(f"   NDTI mean    : {ndti_stats['NDTI_mean']}")
        print(f"   NDWI mean    : {ndwi_stats['NDWI_mean']}")
        print(f"   Alert level  : {alert.upper()}")
        print(f"   Cloud cover  : {cloud_pct}%")
        print(f"   Last clear   : {last_clear}")
 
        # Send real Telegram alert
        if alert == "critical":
            send_critical_alert(
                zone       = RESERVOIR_CONFIG["name"],
                ndti_value = ndti_stats["NDTI_mean"],
                date       = TODAY
            )
            alerts_triggered.append("critical")
 
        elif alert == "warning":
            send_warning_alert(
                zone       = RESERVOIR_CONFIG["name"],
                ndti_value = ndti_stats["NDTI_mean"],
                date       = TODAY
            )
            alerts_triggered.append("warning")
 
        # Log to Supabase alerts_log table
        if alert in ["warning", "critical"]:
            log_alert(
                zone        = RESERVOIR_CONFIG["name"],
                alert_level = alert,
                date        = TODAY,
                ndti_mean   = ndti_stats["NDTI_mean"],
                message     = f"Daily check: {alert} turbidity detected. NDTI={ndti_stats['NDTI_mean']}"
            )
 
        hydro_records.append({
            "date":            TODAY,
            "zone":            RESERVOIR_CONFIG["name"],
            "location":        RESERVOIR_CONFIG["location"],
            "ndti_mean":       ndti_stats["NDTI_mean"],
            "ndti_min":        ndti_stats["NDTI_min"],
            "ndti_max":        ndti_stats["NDTI_max"],
            "ndwi_mean":       ndwi_stats["NDWI_mean"],  # ← FIXED: correct value now
            "alert_level":     alert,
            "cloud_pct":       cloud_pct,
            "last_clear_view": last_clear
        })
 
    # ── FARM: Felda Jengka ────────────────────────────────
    print(f"\n🌴 Checking: {FARM_CONFIG['name']}")
 
    farm_geom = get_geometry(FARM_CONFIG)
    image, cloud_pct, last_clear = load_sentinel2(
        farm_geom, MONTH_AGO, TODAY, cloud_threshold=30
    )
 
    if image is None:
        print("   ⚠️  No clear images — skipping farm")
    else:
        ndvi_stats = extract_stats(compute_ndvi(image), farm_geom, "NDVI")
        ndre_stats = extract_stats(compute_ndre(image), farm_geom, "NDRE")  # ← FIXED: now computed
        alert      = compute_alert_level(
            ndvi_mean = ndvi_stats["NDVI_mean"],
            ndre_mean = ndre_stats["NDRE_mean"]
        )
 
        print(f"   NDVI mean    : {ndvi_stats['NDVI_mean']}")
        print(f"   NDRE mean    : {ndre_stats['NDRE_mean']}")
        print(f"   Alert level  : {alert.upper()}")
        print(f"   Cloud cover  : {cloud_pct}%")
 
        # Send Telegram alert for vegetation stress
        if alert == "critical":
            from telegram_helper import send_telegram_message
            send_telegram_message(
                f"🔴 <b>CRITICAL VEGETATION ALERT</b>\n\n"
                f"📍 <b>Zone:</b> {FARM_CONFIG['name']}\n"
                f"📅 <b>Date:</b> {TODAY}\n"
                f"🌿 <b>NDVI:</b> {ndvi_stats['NDVI_mean']:.4f}\n"
                f"🍃 <b>NDRE:</b> {ndre_stats['NDRE_mean']:.4f}\n"
                f"⚠️ <b>Status:</b> CRITICAL — Severe vegetation stress\n\n"
                f"🌴 <b>Action:</b> Inspect plantation for disease or nutrient deficiency\n"
                f"🤖 <i>TNB Siltation Monitor — Automated Alert</i>"
            )
            alerts_triggered.append("critical")
 
        elif alert == "warning":
            alerts_triggered.append("warning")
 
        if alert in ["warning", "critical"]:
            log_alert(
                zone        = FARM_CONFIG["name"],
                alert_level = alert,
                date        = TODAY,
                ndvi_mean   = ndvi_stats["NDVI_mean"],
                message     = f"Daily check: {alert} vegetation stress. NDVI={ndvi_stats['NDVI_mean']}"
            )
 
        agri_records.append({
            "date":        TODAY,
            "zone":        FARM_CONFIG["name"],
            "location":    FARM_CONFIG["location"],
            "ndvi_mean":   ndvi_stats["NDVI_mean"],
            "ndvi_min":    ndvi_stats["NDVI_min"],
            "ndvi_max":    ndvi_stats["NDVI_max"],
            "ndre_mean":   ndre_stats["NDRE_mean"],  # ← FIXED: real value
            "alert_level": alert,
            "cloud_pct":   cloud_pct
        })
 
    # ── Write to Supabase ─────────────────────────────────
    if hydro_records:
        write_hydro_data(pd.DataFrame(hydro_records))
        print(f"\n✅ Hydro data written to Supabase")
 
    if agri_records:
        write_agri_data(pd.DataFrame(agri_records))
        print(f"✅ Agri data written to Supabase")
 
    # ── Summary ───────────────────────────────────────────
    print("\n" + "=" * 55)
    print("  DAILY CHECK COMPLETE")
    print(f"  Alerts triggered : {len(alerts_triggered)}")
 
    if alerts_triggered:
        highest = "critical" if "critical" in alerts_triggered else "warning"
        print(f"  Highest severity : {highest.upper()}")
        print(f"  Telegram alert   : ✅ Sent")
    else:
        print("  Status           : ALL ZONES NORMAL ✅")
        print("  Telegram alert   : Not needed")
 
    print("=" * 55)
 
    # GitHub Actions catches exit code 1 as failure
    if "critical" in alerts_triggered:
        sys.exit(1)
 
 
if __name__ == "__main__":
    run_daily_check()
 