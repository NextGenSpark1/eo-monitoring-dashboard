"""
Run from repo root:
    python run_pipeline.py                    ← full 12 months both zones
    python run_pipeline.py --months 3         ← quick test, 3 months only
    python run_pipeline.py --seed-only        ← only seed Greatest Hits, skip GEE
    python run_pipeline.py --warmup           ← warm up cache before demo
================================================================================
"""
 
import sys
import os
import argparse
 
# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
 
from gee_logic import run_full_pipeline, warm_up_cache
from database  import (
    init_database,
    seed_hydro_greatest_hits,
    seed_agri_greatest_hits,
    write_hydro_data,
    write_agri_data,
    check_database_health
)
 
 
# ============================================================
# ARGUMENT PARSER
# ============================================================
 
def parse_args():
    parser = argparse.ArgumentParser(
        description="TNB Siltation Monitor — Pipeline Runner"
    )
    parser.add_argument(
        "--months",
        type    = int,
        default = 12,
        help    = "Number of months of historical data to fetch (default: 12)"
    )
    parser.add_argument(
        "--seed-only",
        action  = "store_true",
        help    = "Only seed Greatest Hits — skip GEE pipeline"
    )
    parser.add_argument(
        "--warmup",
        action  = "store_true",
        help    = "Warm up diskcache for both zones before demo"
    )
    parser.add_argument(
        "--skip-seed",
        action  = "store_true",
        help    = "Skip Greatest Hits seeding — only run GEE pipeline"
    )
    return parser.parse_args()
 
 
# ============================================================
# MAIN PIPELINE
# ============================================================
 
def main():
    args = parse_args()
 
    print("=" * 55)
    print("  TNB Siltation Monitor — Pipeline Runner")
    print("=" * 55)
 
    # ── Handle --warmup flag ──────────────────────────────
    if args.warmup:
        print("\n🔥 Running cache warm-up for demo...")
        print("   Run this 30 minutes before client presentation.")
        print("   After this, all zone switches will be instant.\n")
        try:
            warm_up_cache()
        except Exception as e:
            print(f"   ❌ Cache warm-up failed: {e}")
            print("   → Check GEE authentication and try again")
        return
 
    # ── Step 1: Initialize database ───────────────────────
    print("\n📦 Step 1: Initializing Supabase database...")
    try:
        init_database()
    except Exception as e:
        print(f"   ❌ Database init failed: {e}")
        print("   → Check .streamlit/secrets.toml [supabase] section")
        sys.exit(1)
 
    # ── Step 2: Seed Greatest Hits ────────────────────────
    if not args.skip_seed:
        print("\n🎯 Step 2: Seeding Greatest Hits events...")
        try:
            seed_hydro_greatest_hits()
            seed_agri_greatest_hits()
        except Exception as e:
            print(f"   ❌ Seeding failed: {e}")
            print("   → Continuing to GEE pipeline anyway...")
    else:
        print("\n⏭️  Step 2: Skipping Greatest Hits seed (--skip-seed flag)")
 
    # ── Handle --seed-only flag ───────────────────────────
    if args.seed_only:
        print("\n✅ Seed-only mode complete!")
        print("   Greatest Hits data is now in Supabase.")
        print("   Run: streamlit run app.py to view dashboard.")
        check_database_health()
        return
 
    # ── Step 3: Run GEE Pipeline ──────────────────────────
    print(f"\n🛰️  Step 3: Running GEE pipeline ({args.months} months)...")
    print("   Processing zones:")
    print("   💧 Empangan Sultan Abu Bakar — NDTI + NDWI")
    print("   🌴 Felda Jengka              — NDVI + NDRE")
 
    if args.months == 12:
        print("   ⏱️  Estimated time: 10-20 minutes")
    elif args.months <= 3:
        print("   ⏱️  Estimated time: 2-5 minutes (quick mode)")
    else:
        print(f"   ⏱️  Estimated time: ~{args.months * 1.5:.0f} minutes")
 
    print()
 
    try:
        hydro_df, agri_df = run_full_pipeline(months_back=args.months)
 
        # ── Step 4: Write to Supabase ─────────────────────
        print("\n💾 Step 4: Writing real data to Supabase...")
 
        if not hydro_df.empty:
            write_hydro_data(hydro_df)
        else:
            print("   ⚠️  No hydro records — all months may have been cloud-covered")
            print("   → Try increasing cloud_threshold in gee_logic.py")
 
        if not agri_df.empty:
            write_agri_data(agri_df)
        else:
            print("   ⚠️  No agri records — all months may have been cloud-covered")
 
        print("\n✅ Real data successfully written to Supabase!")
        print(f"   💧 Hydro records : {len(hydro_df)}")
        print(f"   🌴 Agri records  : {len(agri_df)}")
 
    except Exception as e:
        print(f"\n⚠️  GEE pipeline error: {e}")
        print("   Greatest Hits data is still available for demo.")
        print("   Common fixes:")
        print("   → Check service_account.json is in repo root")
        print("   → Check GEE project has Sentinel-2 access")
        print("   → Try: python run_pipeline.py --seed-only")
 
    # ── Step 5: Health check ──────────────────────────────
    print("\n📊 Step 5: Supabase health check...")
    try:
        check_database_health()
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
 
    # ── Final instructions ────────────────────────────────
    print("\n" + "=" * 55)
    print("  PIPELINE COMPLETE")
    print("=" * 55)
    print("""
Next steps:
  1. Launch dashboard:
        streamlit run app.py
 
  2. Verify all 3 tabs load correctly:
        💧 Hydro — Empangan Sultan Abu Bakar
        🌴 Agri  — Felda Jengka
        🔍 Search — type any location
 
  3. Before client demo:
        python run_pipeline.py --warmup
        (run 30 mins before — makes zone switching instant)
""")
 
 
if __name__ == "__main__":
    main()