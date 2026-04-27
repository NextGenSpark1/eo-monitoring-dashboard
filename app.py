"""
================================================================================
app.py — Main Entry Point
================================================================================
Developer  : Habiba Hassan (AI Analytics & Visualization)
Description: Streamlit dashboard UI for TNB Siltation Monitor.
             Reads from SQLite database via src/database.py
             Renders live GEE maps via src/gee_logic.py
================================================================================
"""

import streamlit as st
import sys
import os
import time


from src.database import (
    read_hydro_data,
    read_agri_data,
    read_latest_status,
    init_database,
    seed_hydro_greatest_hits,
    seed_agri_greatest_hits
)
from src.gee_logic import initialize_gee

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title  = "TNB Siltation Monitor",
    page_icon   = "💧",
    layout      = "wide",
    initial_sidebar_state = "expanded"
)

# ============================================================
# DASHBOARD — Habiba builds this section
# ============================================================



if "db_initialized" not in st.session_state:
    init_database()
    seed_hydro_greatest_hits()
    seed_agri_greatest_hits()
    st.session_state["db_initialized"] = True

# ============================================================
# AUTO-REFRESH — reruns the full dashboard every 5 minutes
# No user interaction needed; works on Supabase (no cache.db)
# ============================================================
REFRESH_INTERVAL = 300  # seconds (5 minutes)

if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = time.time()

time_since = time.time() - st.session_state["last_refresh"]
time_left  = max(0, REFRESH_INTERVAL - int(time_since))

# Load data directly from Supabase (no local cache needed)
hydro_df = read_hydro_data()
agri_df  = read_agri_data()

# Show countdown and auto-trigger rerun when timer hits 0
st.caption(f"🔄 Auto-refreshing in {time_left // 60}m {time_left % 60}s")
if time_since >= REFRESH_INTERVAL:
    st.session_state["last_refresh"] = time.time()
    time.sleep(0.5)   # brief pause so the user sees the update
    st.rerun()

# Page header
st.title("💧 TNB Siltation Monitor")
st.caption("Empangan Sultan Abu Bakar · Felda Jengka — Real-Time Monitoring  |  🔄 Auto-refreshes every 5 minutes")

# Verify both zones loading correctly
tab1, tab2 = st.tabs([
    "💧 Hydro — Empangan Sultan Abu Bakar",
    "🌴 Agri — Felda Jengka"
])

with tab1:
    st.subheader("Hydro Monitoring Data")
    if hydro_df.empty:
        st.warning("No hydro data found")
    else:
        st.success(f"{len(hydro_df)} records loaded")
        st.dataframe(hydro_df)

with tab2:
    st.subheader("Agriculture Monitoring Data")
    if agri_df.empty:
        st.warning("No agri data found")
    else:
        st.success(f"{len(agri_df)} records loaded")
        st.dataframe(agri_df)