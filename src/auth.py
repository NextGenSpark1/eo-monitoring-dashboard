# ================================================================================
# src/auth.py — Authentication & Role Management
# ================================================================================
# Developer  : Habiba Hassan (AI Analytics & Visualization)
# Description: Supabase Auth integration — login, signup, logout, role checks,
#              and the styled landing/auth page rendered when not authenticated.
# ================================================================================

import streamlit as st
from utils.theme import LIGHT
from utils.styles import get_css


# ── Supabase Client ───────────────────────────────────────────

def _client():
    from src.database import get_supabase_client
    return get_supabase_client()


# ── Core Auth Functions ───────────────────────────────────────

def login(email: str, password: str):
    try:
        res  = _client().auth.sign_in_with_password({"email": email, "password": password})
        user = res.user
        st.session_state["user"]  = {"id": str(user.id), "email": user.email}
        st.session_state["token"] = res.session.access_token
        r = _client().table("user_roles").select("role").eq("user_id", str(user.id)).execute()
        st.session_state["role"] = r.data[0]["role"] if r.data else "viewer"
        return True, None
    except Exception as e:
        return False, str(e)


def signup(email: str, password: str):
    try:
        res  = _client().auth.sign_up({"email": email, "password": password})
        user = res.user
        if user:
            _client().table("user_roles").upsert(
                {"user_id": str(user.id), "email": email, "role": "viewer"},
                on_conflict="user_id"
            ).execute()
            return True, "Account created. Check your email to verify, then sign in."
        return False, "Sign-up failed — please try again."
    except Exception as e:
        return False, str(e)


def logout():
    try:
        _client().auth.sign_out()
    except Exception:
        pass
    for k in ["user", "role", "token"]:
        st.session_state.pop(k, None)


def is_authenticated() -> bool:
    return "user" in st.session_state


def get_role() -> str:
    return st.session_state.get("role", "viewer")


def get_current_email() -> str:
    return st.session_state.get("user", {}).get("email", "")


def require_auth():
    """Call at the top of every page. Shows auth page and stops if not logged in."""
    if not is_authenticated():
        _render_auth_page()
        st.stop()


# ── Sidebar User Info ─────────────────────────────────────────

def render_user_info(t: dict):
    """Renders signed-in user info + logout button at the top of any sidebar."""
    email = get_current_email()
    role  = get_role()
    role_labels = {
        "admin":       ("Admin",       t["blue"]),
        "viewer":      ("Full Viewer", t["green"]),
        "hydro_viewer":("Hydro Viewer",t["blue"]),
        "agri_viewer": ("Agri Viewer", t["green"]),
    }
    role_label, role_color = role_labels.get(role, ("Viewer", t["text4"]))

    st.markdown(f"""
    <div style="padding:10px 4px 12px;border-bottom:1px solid {t['border']};margin-bottom:12px;">
        <div style="font-size:11px;color:{t['text4']};margin-bottom:2px;">Signed in as</div>
        <div style="font-size:12px;font-weight:600;color:{t['text1']};
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{email}</div>
        <span style="font-size:10px;font-weight:600;color:{role_color};
            background:{role_color}18;padding:2px 8px;border-radius:8px;
            margin-top:4px;display:inline-block;">{role_label}</span>
    </div>""", unsafe_allow_html=True)

    if st.button("Sign Out", use_container_width=True, key="btn_signout"):
        logout()
        st.rerun()


# ── Auth / Landing Page ───────────────────────────────────────

def _render_auth_page():
    t = LIGHT
    st.markdown(get_css(t, "Light"), unsafe_allow_html=True)
    st.markdown("""
    <style>
        section[data-testid="stSidebar"] { display:none !important; }
        header[data-testid="stHeader"]   { display:none !important; }
        .block-container {
            max-width: 480px !important;
            margin: 0 auto !important;
            padding-top: 56px !important;
            padding-bottom: 48px !important;
        }
    </style>""", unsafe_allow_html=True)

    # ── Branding ──────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;margin-bottom:40px;">
        <div style="width:64px;height:64px;border-radius:20px;
            background:linear-gradient(135deg,#4f8df5,#34d399);
            display:flex;align-items:center;justify-content:center;
            font-size:24px;font-weight:800;color:#fff;
            margin:0 auto 20px;
            box-shadow:0 8px 32px rgba(79,141,245,0.35),
                       0 2px 8px rgba(52,211,153,0.2);">NS</div>
        <div style="font-size:23px;font-weight:800;color:#0f172a;
            font-family:Inter,sans-serif;letter-spacing:-0.02em;margin-bottom:8px;">
            EO Monitoring Dashboard
        </div>
        <div style="font-size:12px;color:#64748b;font-family:Inter,sans-serif;
            line-height:1.8;">
            NextGen Spark Sdn Bhd
            <br>Real-time satellite monitoring · Sentinel-2 &amp; Google Earth Engine
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Form card ─────────────────────────────────────────────
    st.markdown("""
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:16px;
        padding:28px 28px 20px;box-shadow:0 4px 24px rgba(0,0,0,0.07);
        margin-bottom:4px;">
    """, unsafe_allow_html=True)

    login_tab, signup_tab = st.tabs(["Sign In", "Create Account"])

    with login_tab:
        _login_form()
    with signup_tab:
        _signup_form()

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;margin-top:28px;">
        <span style="font-size:10.5px;color:#94a3b8;font-family:Inter,sans-serif;">
            Powered by Sentinel-2 · Google Earth Engine · Supabase
        </span>
    </div>""", unsafe_allow_html=True)


def _login_form():
    email    = st.text_input("Email address", placeholder="you@example.com", key="li_email")
    password = st.text_input("Password", type="password", placeholder="••••••••", key="li_pw")
    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
    if st.button("Sign In", type="primary", use_container_width=True, key="btn_li"):
        if not email or not password:
            st.warning("Please enter your email and password.")
        else:
            with st.spinner("Signing in..."):
                ok, err = login(email.strip(), password)
            if ok:
                st.rerun()
            else:
                st.error("Incorrect email or password.")


def _signup_form():
    email    = st.text_input("Email address", placeholder="you@example.com", key="su_email")
    password = st.text_input("Password", type="password",
                             placeholder="Minimum 6 characters", key="su_pw")
    confirm  = st.text_input("Confirm password", type="password",
                             placeholder="••••••••", key="su_confirm")
    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
    if st.button("Create Account", type="primary", use_container_width=True, key="btn_su"):
        if not email or not password or not confirm:
            st.warning("Please fill in all fields.")
        elif password != confirm:
            st.error("Passwords do not match.")
        elif len(password) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            with st.spinner("Creating account..."):
                ok, msg = signup(email.strip(), password)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
