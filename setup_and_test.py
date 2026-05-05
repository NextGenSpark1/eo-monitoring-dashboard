import os
import sys
 
# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
 
print("=" * 55)
print("  TNB Siltation Monitor — Setup Verification")
print("=" * 55)
 
 
# ─────────────────────────────────────────────────────
# TEST 1: Folder Structure
# ─────────────────────────────────────────────────────
print("\n📁 Checking folder structure...")
 
required = [
    "src/__init__.py",
    "src/gee_logic.py",
    "src/database.py",
    "src/utilities.py",

    "src/telegram_helper.py",
    "src/geo_service.py",          # NEW
    "src/dynamic_zone.py",      # NEW
    "app.py",
    "alert_system.py",
    "run_pipeline.py",
    "requirements.txt",
    ".gitignore",
    ".streamlit/config.toml",
    ".streamlit/secrets.toml",
    ".github/workflows/daily_check.yml",
]
 
all_good = True
for path in required:
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"   {status} {path}")
    if not exists:
        all_good = False
 
if all_good:
    print("   ✅ All required files present")
else:
    print("   ❌ Some files missing — check above")
 
 
# ─────────────────────────────────────────────────────
# TEST 2: Library Imports
# ─────────────────────────────────────────────────────
print("\n📦 Checking libraries...")
 
libraries = [
    ("streamlit",        "streamlit"),
    ("pandas",           "pandas"),
    ("earthengine-api",  "ee"),
    ("diskcache",        "diskcache"),
    ("supabase",         "supabase"),
    ("geopy",            "geopy"),
    ("plotly",           "plotly"),
    ("geemap",           "geemap"),
    ("folium",           "folium"),
]
 
for name, module in libraries:
    try:
        __import__(module)
        print(f"   ✅ {name}")
    except ImportError:
        print(f"   ❌ {name} — run: pip install {name}")
        all_good = False
 
 
# ─────────────────────────────────────────────────────
# TEST 3: src/ Module Imports
# ─────────────────────────────────────────────────────
print("\n🔧 Checking src/ module imports...")
 
# database.py
try:
    from database import (
        get_supabase_client,
        init_database,
        seed_hydro_greatest_hits,
        seed_agri_greatest_hits,
        write_hydro_data,
        write_agri_data,
        read_hydro_data,
        read_agri_data,
        read_greatest_hits,
        read_latest_status,
        read_alerts_log,
        log_alert,
        check_database_health
    )
    print("   ✅ database.py — all functions imported")
except Exception as e:
    print(f"   ❌ database.py import failed: {e}")
 
# gee_logic.py
try:
    from gee_logic import (
        initialize_gee,
        get_geometry,
        load_sentinel2,
        compute_ndti,
        compute_ndwi,
        compute_ndvi,
        compute_ndre,
        extract_stats,
        compute_alert_level,
        run_full_pipeline,
        RESERVOIR_CONFIG,
        FARM_CONFIG
    )
    print("   ✅ gee_logic.py — all functions imported")
except Exception as e:
    print(f"   ❌ gee_logic.py import failed: {e}")
 
# utilities.py
try:
    from utilities import (
        parse_coordinate_string,
        get_date_windows,
        get_alert_color,
        get_alert_emoji,
        format_ndti_for_display,
        format_ndvi_for_display
    )
    print("   ✅ utilities.py — all functions imported")
except Exception as e:
    print(f"   ❌ utilities.py import failed: {e}")

 
# telegram_helper.py
try:
    from telegram_helper import (
        send_telegram_message,
        send_test_alert,
        send_critical_alert,
        send_warning_alert
    )
    print("   ✅ telegram_helper.py — all functions imported")
except Exception as e:
    print(f"   ❌ telegram_helper.py import failed: {e}")
 
# geo_service.py
try:
    from geo_service import (
        search_place,
        parse_coordinates,
        detect_and_resolve,
        get_suggestions,
        MALAYSIA_SUGGESTIONS
    )
    print("   ✅ geo_service.py — all functions imported")
except Exception as e:
    print(f"   ❌ geo_service.py import failed: {e}")

 
# dynamic_zone.py
try:
    from dynamic_zone import (
        analyse_location,
        save_custom_zone,
        get_live_map,
        render_search_ui
    )
    print("   ✅ dynamic_zone.py — all functions imported")
except Exception as e:
    print(f"   ❌ dynamic_zone.py import failed: {e}")
 
 
# ─────────────────────────────────────────────────────
# TEST 4: Supabase Connection
# ─────────────────────────────────────────────────────
print("\n🗄️  Checking Supabase connection...")
 
try:
    client = get_supabase_client()
    # Quick test query
    client.table("hydro_data").select("id").limit(1).execute()
    print("   ✅ Supabase connected successfully")
except Exception as e:
    print(f"   ❌ Supabase connection failed: {e}")
    print("   → Check .streamlit/secrets.toml has [supabase] section")
    print("   → url and service_key must be correct")
 
 
# ─────────────────────────────────────────────────────
# TEST 5: Database Seed & Health Check
# ─────────────────────────────────────────────────────
print("\n🌱 Seeding database...")
 
try:
    init_database()
    print("   ✅ init_database() passed")
 
    seed_hydro_greatest_hits()
    print("   ✅ seed_hydro_greatest_hits() passed")
 
    seed_agri_greatest_hits()
    print("   ✅ seed_agri_greatest_hits() passed")
 
except Exception as e:
    print(f"   ❌ Database seed failed: {e}")
 
 
# ─────────────────────────────────────────────────────
# TEST 6: Data Retrieval
# ─────────────────────────────────────────────────────
print("\n📊 Verifying data retrieval...")
 
try:
    hydro_df = read_hydro_data()
    print(f"   ✅ read_hydro_data()        → {len(hydro_df)} records")
 
    agri_df  = read_agri_data()
    print(f"   ✅ read_agri_data()         → {len(agri_df)} records")
 
    hits_h   = read_greatest_hits("hydro")
    print(f"   ✅ read_greatest_hits(hydro)→ {len(hits_h)} events")
 
    hits_a   = read_greatest_hits("agri")
    print(f"   ✅ read_greatest_hits(agri) → {len(hits_a)} events")
 
    status   = read_latest_status()
    print(f"   ✅ read_latest_status()     → hydro: {len(status['hydro'])} row, agri: {len(status['agri'])} row")
 
    # Warnings if empty
    if len(hydro_df) == 0:
        print("   ⚠️  hydro_data empty — run: python run_pipeline.py")
    if len(agri_df) == 0:
        print("   ⚠️  agri_data empty — run: python run_pipeline.py")
 
except Exception as e:
    print(f"   ❌ Data retrieval failed: {e}")
 
 
# ─────────────────────────────────────────────────────
# TEST 7: GEE Authentication
# ─────────────────────────────────────────────────────
print("\n🔐 Checking GEE authentication...")
 
if os.path.exists("service_account.json"):
    print("   ✅ service_account.json found")
    try:
        import ee
        initialize_gee()
        test = ee.Image("USGS/SRTMGL1_003").getInfo()
        print(f"   ✅ GEE working — test band: {test['bands'][0]['id']}")
    except Exception as e:
        print(f"   ❌ GEE init failed: {e}")
else:
    print("   ⚠️  service_account.json not found")
    print("   → Download from Google Cloud Console")
    print("   → Place in repo root (NEVER push to GitHub)")
 
 
# ─────────────────────────────────────────────────────
# TEST 8: Geocoder
# ─────────────────────────────────────────────────────
print("\n🗺️  Testing geo_service...")
 
try:
    tests = [
        "Tasik Kenyir",
        "4.4208, 101.3923",
        "Empangan Semenyih"
    ]
    for t in tests:
        result = detect_and_resolve(t)
        if result["valid"]:
            print(f"   ✅ '{t}' → {result['lat']}, {result['lon']}")
        else:
            print(f"   ❌ '{t}' → {result['error']}")
except Exception as e:
    print(f"   ❌ Geocoder test failed: {e}")
 
 
# ─────────────────────────────────────────────────────
# TEST 9: Telegram
# ─────────────────────────────────────────────────────
print("\n📱 Testing Telegram alert...")
 
try:
    success, msg = send_test_alert()
    if success:
        print(f"   ✅ {msg}")
        print("   → Check your phone for the test message")
    else:
        print(f"   ⚠️  {msg}")
        print("   → Check [telegram] section in .streamlit/secrets.toml")
except Exception as e:
    print(f"   ❌ Telegram test failed: {e}")
 
 
# ─────────────────────────────────────────────────────
# TEST 10: Zone configs check
# ─────────────────────────────────────────────────────
print("\n📍 Checking zone configurations...")
 
try:
    print(f"   ✅ Reservoir : {RESERVOIR_CONFIG['name']}")
    print(f"      Coords   : {RESERVOIR_CONFIG['lat']}, {RESERVOIR_CONFIG['lon']}")
    print(f"   ✅ Farm      : {FARM_CONFIG['name']}")
    print(f"      Coords   : {FARM_CONFIG['lat']}, {FARM_CONFIG['lon']}")
except Exception as e:
    print(f"   ❌ Zone config check failed: {e}")
 
 
# ─────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────
print("\n" + "=" * 55)
print("  SETUP VERIFICATION COMPLETE")
print("=" * 55)
print("""
Next steps:
1. Fix any ❌ errors shown above
2. Run pipeline for real data:
      python run_pipeline.py
3. Launch dashboard:
      streamlit run app.py
4. Test all 3 tabs:
      💧 Hydro — check records load
      🌴 Agri  — check records load
      🔍 Search — type 'Tasik Kenyir' and analyse
 
Before client demo:
   python -c "from src.gee_logic import warm_up_cache; warm_up_cache()"
   (Run 30 mins before — makes zone switching instant)
""")