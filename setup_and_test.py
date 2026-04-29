
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

print("="*55)
print("  TNB Siltation Monitor — Setup Verification")
print("="*55)

# ─────────────────────────────────────────
# TEST 1: Check folder structure
# ─────────────────────────────────────────
print("\n📁 Checking folder structure...")

required = [
    "src/__init__.py",
    "src/gee_logic.py",
    "src/database.py",
    "src/utils.py",
    "src/telegram_helper.py",
    "app.py",
    "alert_system.py",
    "requirements.txt",
    ".gitignore",
    ".streamlit/config.toml",
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

# ─────────────────────────────────────────
# TEST 2: Check imports
# ─────────────────────────────────────────
print("\n📦 Checking imports...")

try:
    from database import init_database, seed_greatest_hits, check_database_health
    print("   ✅ database.py imports OK")
except Exception as e:
    print(f"   ❌ database.py import failed: {e}")

try:
    from utils import parse_coordinate_string, get_date_windows
    print("   ✅ utils.py imports OK")
except Exception as e:
    print(f"   ❌ utils.py import failed: {e}")

try:
    import streamlit
    print("   ✅ streamlit installed")
except Exception:
    print("   ❌ streamlit not installed — run: pip install streamlit")

try:
    import pandas
    print("   ✅ pandas installed")
except Exception:
    print("   ❌ pandas not installed")

try:
    import ee
    print("   ✅ earthengine-api installed")
except Exception:
    print("   ❌ earthengine-api not installed")

try:
    import diskcache
    print("   ✅ diskcache installed")
except Exception:
    print("   ❌ diskcache not installed — run: pip install diskcache")

# ─────────────────────────────────────────
# TEST 3: Initialize and seed database
# ─────────────────────────────────────────
print("\n🗄️  Setting up database...")

try:
    init_database()
    seed_greatest_hits()
    print("   ✅ Database ready")
except Exception as e:
    print(f"   ❌ Database setup failed: {e}")

# ─────────────────────────────────────────
# TEST 4: Verify data is readable
# ─────────────────────────────────────────
print("\n📊 Verifying data retrieval...")

try:
    from database import read_hydro_data, read_greatest_hits, read_latest_status

    hydro_df = read_hydro_data()
    print(f"   ✅ read_hydro_data()    → {len(hydro_df)} records")

    hits_df  = read_greatest_hits()
    print(f"   ✅ read_greatest_hits() → {len(hits_df)} events")

    status   = read_latest_status()
    print(f"   ✅ read_latest_status() → hydro: {len(status['hydro'])} row")

    if len(hydro_df) == 0:
        print("\n   ⚠️  hydro_data is empty!")
        print("   → Run the GEE pipeline to populate with real data")
        print("   → Or Greatest Hits should show at least 8 records")

except Exception as e:
    print(f"   ❌ Data retrieval failed: {e}")

# ─────────────────────────────────────────
# TEST 5: Check service account
# ─────────────────────────────────────────
print("\n🔐 Checking GEE authentication...")

if os.path.exists("service_account.json"):
    print("   ✅ service_account.json found")
    print("   ✅ Ready for headless GEE auth")
else:
    print("   ⚠️  service_account.json not found")
    print("   → Download from Google Cloud Console")
    print("   → Place in repo root (never push to GitHub)")

# ─────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────
print("\n" + "="*55)
print("  SETUP COMPLETE")
print("="*55)
print("""
Next steps:
1. Fix any ❌ issues above
2. Run: streamlit run app.py
3. Dashboard should show Greatest Hits data

If charts still empty in Streamlit:
→ Check that Habiba's app.py imports from src.database
→ Import should be: from src.database import read_hydro_data
→ NOT: from database import read_hydro_data
""")
