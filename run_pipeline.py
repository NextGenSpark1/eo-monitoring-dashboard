"""
================================================================================
run_pipeline.py
================================================================================
Developer  : Mohamed Nawran
Description: Run this to populate the database with REAL satellite data
             for both zones — Reservoir and Palm Oil Farm.

Run from repo root:
    python run_pipeline.py

What it does:
1. Connects to GEE using service_account.json
2. Pulls 12 months of Sentinel-2 data for BOTH zones
3. Computes NDTI + NDWI for reservoir
4. Computes NDVI + NDRE for palm oil farm
5. Writes everything to SQLite database
6. Prints health check so you can confirm data is there
================================================================================
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from gee_logic  import run_full_pipeline
from database   import (
    init_database,
    seed_hydro_greatest_hits,
    seed_agri_greatest_hits,
    write_hydro_data,
    write_agri_data,
    check_database_health
)


def main():
    print("="*55)
    print("  TNB Siltation Monitor — Real Data Pipeline")
    print("  Running for BOTH zones — 12 months")
    print("="*55)

    # Step 1: Initialize database
    print("\n📦 Step 1: Initializing database...")
    init_database()

    # Step 2: Seed Greatest Hits (demo backup data)
    print("\n🎯 Step 2: Seeding Greatest Hits events...")
    seed_hydro_greatest_hits()
    seed_agri_greatest_hits()

    # Step 3: Run real GEE pipeline
    print("\n🛰️  Step 3: Running GEE pipeline (12 months)...")
    print("   This will take 10-20 minutes depending on GEE speed.")
    print("   Both zones will be processed.\n")

    try:
        hydro_df, agri_df = run_full_pipeline(months_back=12)

        # Step 4: Write real data to database
        print("\n💾 Step 4: Writing real data to database...")
        write_hydro_data(hydro_df)
        write_agri_data(agri_df)

        print("\n✅ Real data successfully written!")
        print(f"   Hydro records : {len(hydro_df)}")
        print(f"   Agri records  : {len(agri_df)}")

    except Exception as e:
        print(f"\n⚠️  GEE pipeline error: {e}")
        print("   Greatest Hits data is still available for demo.")
        print("   Fix the GEE error and re-run.")

    # Step 5: Health check
    print("\n📊 Step 5: Database health check...")
    check_database_health()

    print("\n✅ Pipeline complete!")
    print("   Run: streamlit run app.py")
    print("   Dashboard should now show real data for both zones.")


if __name__ == "__main__":
    main()
