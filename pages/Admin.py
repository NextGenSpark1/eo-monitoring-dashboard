# ================================================================================
# pages/Admin.py — Admin Panel
# ================================================================================
# Developer  : Habiba Hassan (AI Analytics & Visualization)
# Description: User role management and global threshold configuration.
#              Only accessible to users with the 'admin' role.
# ================================================================================

import streamlit as st
import datetime

from utils.theme import DARK, LIGHT
from utils.styles import get_css
from src.auth import require_auth, get_role, get_current_email, render_user_info
from src.database import get_all_user_roles, set_user_role, get_system_config, set_system_config

st.set_page_config(
    page_title="Admin Panel — EO Dashboard",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth()

# Restrict to admin only
if get_role() != "admin":
    st.error("Access denied. This page is for administrators only.")
    st.stop()

current_email = get_current_email()

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    _t_pre = LIGHT if st.session_state.get("_theme", "Light") == "Light" else DARK
    render_user_info(_t_pre)
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px;">
        <div style="width:34px;height:34px;border-radius:10px;
            background:linear-gradient(135deg,#4f8df5,#34d399);
            display:flex;align-items:center;justify-content:center;
            font-size:13px;font-weight:700;color:#fff;
            box-shadow:0 3px 10px rgba(79,141,245,0.25);">NS</div>
        <div>
            <div style="font-size:14px;font-weight:600;" class="sb-header-title">Admin Panel</div>
            <div style="font-size:10px;color:#94a3b8;">NextGen Spark EO</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if "_theme" not in st.session_state:
        st.session_state["_theme"] = "Light"
    theme_choice = st.radio("Theme", ["Light", "Dark"], horizontal=True,
                            label_visibility="collapsed",
                            index=0 if st.session_state["_theme"] == "Light" else 1)
    st.session_state["_theme"] = theme_choice

t = LIGHT if theme_choice == "Light" else DARK
st.markdown(get_css(t, theme_choice), unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────
header_col, live_col = st.columns([3, 1])
with header_col:
    st.markdown(f"""<div class="dash-header"><div class="dash-logo">NS</div><div>
        <p class="dash-title">Admin Panel</p>
        <p class="dash-sub">Manage users, roles, and global dashboard settings</p>
    </div></div>""", unsafe_allow_html=True)
with live_col:
    st.markdown(f"""<div style="display:flex;justify-content:flex-end;align-items:center;
        gap:14px;padding-top:16px;">
        <span class="meta-tag">{datetime.datetime.now().strftime("%d %b %Y, %H:%M")}</span>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════
# USER MANAGEMENT
# ══════════════════════════════════════════════════════════════

st.markdown(f'<div class="panel-label" style="margin-bottom:16px;">USER MANAGEMENT</div>',
            unsafe_allow_html=True)

ROLE_OPTIONS  = ["viewer", "hydro_viewer", "agri_viewer", "admin"]
ROLE_LABELS   = {
    "viewer":       "Full Viewer",
    "hydro_viewer": "Hydro Viewer",
    "agri_viewer":  "Agri Viewer",
    "admin":        "Admin",
}
ROLE_COLORS   = {
    "admin":        t["red"],
    "viewer":       t["green"],
    "hydro_viewer": t["blue"],
    "agri_viewer":  t["green"],
}

try:
    users = get_all_user_roles()
except Exception as e:
    st.error(f"Could not load users: {e}")
    users = []

if not users:
    st.markdown(f'<div style="color:{t["text4"]};font-size:13px;padding:16px 0;">No users registered yet.</div>',
                unsafe_allow_html=True)
else:
    for user in users:
        uid        = user["user_id"]
        email      = user["email"]
        role       = user["role"]
        joined     = user.get("created_at", "")[:10] if user.get("created_at") else "—"
        role_color = ROLE_COLORS.get(role, t["text4"])
        role_label = ROLE_LABELS.get(role, role)

        row_col, select_col, btn_col = st.columns([3, 2, 1])
        with row_col:
            st.markdown(f"""<div class="zcard" style="margin-bottom:0;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div style="font-size:13px;font-weight:600;color:{t['text1']};">{email}</div>
                        <div style="font-size:10px;color:{t['text4']};margin-top:2px;">Joined: {joined}</div>
                    </div>
                    <span style="font-size:10px;font-weight:700;color:{role_color};
                        background:{role_color}18;padding:2px 10px;border-radius:10px;">
                        {role_label}
                    </span>
                </div>
            </div>""", unsafe_allow_html=True)
        with select_col:
            new_role = st.selectbox(
                "Role", ROLE_OPTIONS,
                index=ROLE_OPTIONS.index(role),
                format_func=lambda r: ROLE_LABELS.get(r, r),
                label_visibility="collapsed",
                key=f"role_sel_{uid}"
            )
        with btn_col:
            if st.button("Update", key=f"role_btn_{uid}", use_container_width=True):
                if new_role != role:
                    try:
                        set_user_role(uid, new_role)
                        st.success(f"Updated to {ROLE_LABELS[new_role]}.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

# ══════════════════════════════════════════════════════════════
# GLOBAL THRESHOLD DEFAULTS
# ══════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown(f'<div class="panel-label" style="margin-bottom:16px;">GLOBAL THRESHOLD DEFAULTS</div>',
            unsafe_allow_html=True)
st.markdown(f'<div style="font-size:12px;color:{t["text4"]};margin-bottom:20px;">These values are shown to all non-admin users and used as the default classification thresholds.</div>',
            unsafe_allow_html=True)

try:
    cfg = get_system_config()
except Exception as e:
    st.error(f"Could not load config: {e}")
    cfg = {}

hydro_col, agri_col = st.columns(2)

with hydro_col:
    st.markdown(f'<p class="sb-label" style="margin-bottom:12px;">Hydro (NDTI)</p>', unsafe_allow_html=True)
    h_warn = st.slider("Warning (NDTI >=)", 0.0, 1.0, cfg.get("hydro_warning_threshold", 0.03), 0.01, key="adm_h_warn")
    h_crit = st.slider("Critical (NDTI >=)", 0.0, 1.0, cfg.get("hydro_critical_threshold", 0.09), 0.01, key="adm_h_crit")
    st.markdown(f"""<div style="font-size:10.5px;line-height:2.2;color:{t['sb_text']};margin-bottom:12px;">
        <span style="color:{t['green']};">●</span> Normal: &lt; {h_warn:.2f}<br>
        <span style="color:{t['amber']};">●</span> Warning: {h_warn:.2f} – {h_crit:.2f}<br>
        <span style="color:{t['red']};">●</span> Critical: ≥ {h_crit:.2f}
    </div>""", unsafe_allow_html=True)
    if st.button("Save Hydro Defaults", type="primary", use_container_width=True, key="save_h"):
        set_system_config("hydro_warning_threshold",  h_warn, current_email)
        set_system_config("hydro_critical_threshold", h_crit, current_email)
        st.success("Hydro thresholds saved.")

with agri_col:
    st.markdown(f'<p class="sb-label" style="margin-bottom:12px;">Agriculture (NDVI)</p>', unsafe_allow_html=True)
    a_warn = st.slider("Warning (NDVI <)", 0.0, 1.0, cfg.get("agri_warning_threshold", 0.40), 0.05, key="adm_a_warn")
    a_crit = st.slider("Critical (NDVI <)", 0.0, 1.0, cfg.get("agri_critical_threshold", 0.20), 0.05, key="adm_a_crit")
    st.markdown(f"""<div style="font-size:10.5px;line-height:2.2;color:{t['sb_text']};margin-bottom:12px;">
        <span style="color:{t['green']};">●</span> Normal: &gt; {a_warn:.2f}<br>
        <span style="color:{t['amber']};">●</span> Warning: {a_crit:.2f} – {a_warn:.2f}<br>
        <span style="color:{t['red']};">●</span> Critical: &lt; {a_crit:.2f}
    </div>""", unsafe_allow_html=True)
    if st.button("Save Agri Defaults", type="primary", use_container_width=True, key="save_a"):
        set_system_config("agri_warning_threshold",  a_warn, current_email)
        set_system_config("agri_critical_threshold", a_crit, current_email)
        st.success("Agri thresholds saved.")

# ── Footer ────────────────────────────────────────────────────
st.markdown("")
st.markdown(f"""<div style="text-align:center;padding:24px 0 16px;border-top:1px solid {t['border']};margin-top:24px;">
    <span style="font-size:11px;color:{t['text4']};">NextGen Spark Sdn Bhd · EO Monitoring Prototype v1.0</span>
</div>""", unsafe_allow_html=True)
