
import sys
import os
from datetime import datetime, timedelta

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from gee_logic import (
    initialize_gee,
    get_geometry,
    load_sentinel2,
    compute_ndti,
    compute_ndvi,
    extract_stats,
    compute_alert_level,
    RESERVOIR_CONFIG,
    FARM_CONFIG
)
from database import (
    init_database,
    write_hydro_data,
    write_agri_data,
    log_alert,
    get_all_subscribers,
)
from telegram_helper import (
    build_alert_message,
    send_telegram_message,
)

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

# Alert thresholds
CRITICAL_NDTI = 0.05   # Above this = critical turbidity
WARNING_NDTI  = 0.0    # Above this = warning turbidity

# Date range for daily check — last 30 days
TODAY      = datetime.now().strftime("%Y-%m-%d")
MONTH_AGO  = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")


# ============================================================
# NOTIFICATION
# ============================================================

def broadcast_alert(zone, alert_level, value, value_col, module_name, date, event_label=None):
    """
    Send the formatted alert to every subscriber in Supabase.
    Returns the message text so it can also be logged in the alerts_log table.
    """
    message = build_alert_message(
        zone_name=zone,
        index_value=value,
        status=alert_level,
        value_col=value_col,
        module_name=module_name,
        event_label=event_label,
    )

    subscribers = get_all_subscribers()
    if not subscribers:
        print("   ⚠️  No subscribers found — alert not broadcast")
    else:
        sent = 0
        for chat_id in subscribers:
            ok, _ = send_telegram_message(chat_id, message)
            if ok:
                sent += 1
        print(f"   📨 Telegram broadcast sent to {sent}/{len(subscribers)} subscribers")

    print(message)
    print("-" * 40)
    return message


# ============================================================
# MAIN DAILY CHECK
# ============================================================

def run_daily_check():
    """
    Main function — run by GitHub Actions every day at 2AM.

    Steps:
    1. Initialize GEE with headless auth
    2. Initialize database
    3. Process latest satellite data for reservoir
    4. Process latest satellite data for farm
    5. Log any alerts
    6. Write new data to database
    7. Print summary report
    """

    print("=" * 55)
    print(f"  TNB Siltation Monitor — Daily Check")
    print(f"  Date: {TODAY}")
    print("=" * 55)

    # Step 1: Initialize
    initialize_gee()
    init_database()

    alerts_triggered = []
    hydro_records    = []
    agri_records     = []

    # -------------------------------------------------------
    # Step 2: Process Reservoir (Empangan Sultan Abu Bakar)
    # -------------------------------------------------------
    print(f"\n Checking: {RESERVOIR_CONFIG['name']}")

    reservoir_geometry = get_geometry(RESERVOIR_CONFIG)
    image, cloud_pct, last_clear = load_sentinel2(
        reservoir_geometry, MONTH_AGO, TODAY, cloud_threshold=30
    )

    if image is None:
        print("   ⚠️  No clear images available — skipping")
    else:
        ndti_stats = extract_stats(compute_ndti(image), reservoir_geometry, "NDTI")
        ndwi_stats = extract_stats(compute_ndvi(image), reservoir_geometry, "NDWI")
        alert      = compute_alert_level(ndti_mean=ndti_stats["NDTI_mean"])

        print(f"   NDTI mean    : {ndti_stats['NDTI_mean']}")
        print(f"   Alert level  : {alert.upper()}")
        print(f"   Cloud cover  : {cloud_pct}%")
        print(f"   Last clear   : {last_clear}")

        # Log alert if not normal
        if alert in ["warning", "critical"]:
            message = broadcast_alert(
                zone        = RESERVOIR_CONFIG["name"],
                alert_level = alert,
                value       = ndti_stats["NDTI_mean"],
                value_col   = "turbidity",
                module_name = "Hydro",
                date        = TODAY,
            )
            log_alert(
                zone        = RESERVOIR_CONFIG["name"],
                alert_level = alert,
                date        = TODAY,
                ndti_mean   = ndti_stats["NDTI_mean"],
                message     = message
            )
            alerts_triggered.append(alert)

        hydro_records.append({
            "date":            TODAY,
            "zone":            RESERVOIR_CONFIG["name"],
            "location":        RESERVOIR_CONFIG["location"],
            "ndti_mean":       ndti_stats["NDTI_mean"],
            "ndti_min":        ndti_stats["NDTI_min"],
            "ndti_max":        ndti_stats["NDTI_max"],
            "ndwi_mean":       ndwi_stats.get("NDWI_mean"),
            "alert_level":     alert,
            "cloud_pct":       cloud_pct,
            "last_clear_view": last_clear
        })

    # -------------------------------------------------------
    # Step 3: Process Farm
    # -------------------------------------------------------
    print(f"\n🌴 Checking: {FARM_CONFIG['name']}")

    farm_geometry = get_geometry(FARM_CONFIG)
    image, cloud_pct, last_clear = load_sentinel2(
        farm_geometry, MONTH_AGO, TODAY, cloud_threshold=30
    )

    if image is None:
        print("   ⚠️  No clear images available — skipping")
    else:
        ndvi_stats = extract_stats(compute_ndvi(image), farm_geometry, "NDVI")
        alert      = compute_alert_level(ndvi_mean=ndvi_stats["NDVI_mean"])

        print(f"   NDVI mean    : {ndvi_stats['NDVI_mean']}")
        print(f"   Alert level  : {alert.upper()}")
        print(f"   Cloud cover  : {cloud_pct}%")

        if alert in ["warning", "critical"]:
            message = broadcast_alert(
                zone        = FARM_CONFIG["name"],
                alert_level = alert,
                value       = ndvi_stats["NDVI_mean"],
                value_col   = "ndvi",
                module_name = "Agriculture",
                date        = TODAY,
            )
            log_alert(
                zone        = FARM_CONFIG["name"],
                alert_level = alert,
                date        = TODAY,
                ndvi_mean   = ndvi_stats["NDVI_mean"],
                message     = message,
            )
            alerts_triggered.append(alert)

        agri_records.append({
            "date":        TODAY,
            "zone":        FARM_CONFIG["name"],
            "location":    FARM_CONFIG["location"],
            "ndvi_mean":   ndvi_stats["NDVI_mean"],
            "ndvi_min":    ndvi_stats["NDVI_min"],
            "ndvi_max":    ndvi_stats["NDVI_max"],
            "ndre_mean":   None,
            "alert_level": alert,
            "cloud_pct":   cloud_pct
        })

    # -------------------------------------------------------
    # Step 4: Write to database
    # -------------------------------------------------------
    if hydro_records:
        write_hydro_data(pd.DataFrame(hydro_records))
    if agri_records:
        write_agri_data(pd.DataFrame(agri_records))

    # -------------------------------------------------------
    # Step 5: Summary report
    # -------------------------------------------------------
    print("\n" + "=" * 55)
    print("  DAILY CHECK COMPLETE")
    print(f"  Alerts triggered : {len(alerts_triggered)}")
    if alerts_triggered:
        highest = "critical" if "critical" in alerts_triggered else "warning"
        print(f"  Highest severity : {highest.upper()}")
    else:
        print("  Status           : ALL ZONES NORMAL ✅")
    print("=" * 55)

    # Exit with code 1 if critical alert (GitHub Actions can catch this)
    if "critical" in alerts_triggered:
        sys.exit(1)


if __name__ == "__main__":
    run_daily_check()
