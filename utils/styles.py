# ================================================================================
# utils/styles.py — Dashboard CSS & Styling
# ================================================================================
# Developer  : Habiba Hassan (AI Analytics & Visualization)
# Description: Dynamic CSS generation for the full dashboard — KPI cards, panels,
#              charts, maps, alerts, sidebar, and native widget theming.
#              Responds to Light/Dark mode toggle in real time.
# ================================================================================

# Dashboard CSS


def get_css(t, theme_choice):
    zcard_bg = t['bg'] if theme_choice == 'Dark' else '#f8fafc'
    return f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ── Global ── */
    .stApp {{
        background-color: {t['bg']};
        color: {t['text1']};
        font-family: 'Inter', -apple-system, sans-serif;
    }}
    hr {{ border-color: {t['border']} !important; margin: 14px 0 !important; }}

    /* ── Header ── */
    header[data-testid="stHeader"] {{
        background: {t['header_bg']} !important;
        backdrop-filter: blur(10px);
    }}
    button[data-testid="stBaseButton-headerNoPadding"],
    button[data-testid="stBaseButton-header"],
    header button {{
        color: {t['text1']} !important;
    }}
    header button svg {{
        stroke: {t['text2']} !important;
        fill: {t['text2']} !important;
    }}
    [data-testid="stStatusWidget"],
    [data-testid="stStatusWidget"] button,
    [data-testid="stStatusWidget"] label,
    [data-testid="stStatusWidget"] span {{
        color: {t['text2']} !important;
    }}
    [data-testid="stStatusWidget"] button {{
        background: {t['bg_card']} !important;
        border: 1px solid {t['border']} !important;
    }}
    [data-testid="stAppDeployButton"] button,
    .stDeployButton button {{
        color: {t['text1']} !important;
    }}

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {{
        background-color: {t['bg_sidebar']} !important;
        border-right: 1px solid {t['border']};
    }}
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li,
    section[data-testid="stSidebar"] .stMarkdown span {{
        color: {t['sb_text']} !important;
        font-size: 13px;
    }}
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3,
    section[data-testid="stSidebar"] .stMarkdown h4 {{
        color: {t['text1']} !important;
    }}
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] label p,
    section[data-testid="stSidebar"] label span,
    section[data-testid="stSidebar"] label div,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stRadio label span,
    section[data-testid="stSidebar"] .stRadio label p,
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label,
    section[data-testid="stSidebar"] .stCheckbox label,
    section[data-testid="stSidebar"] .stCheckbox label span,
    section[data-testid="stSidebar"] .stCheckbox label p {{
        color: {t['checkbox_text']} !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }}
    button[data-testid="stSidebarCollapseButton"] {{
        color: {t['collapse_icon']} !important;
        background: {t['collapse_bg']} !important;
        border: 1px solid {t['collapse_bdr']} !important;
        border-radius: 8px !important;
    }}
    button[data-testid="stSidebarCollapseButton"]:hover {{
        background: {t['border_hover']} !important;
    }}
    button[data-testid="stSidebarCollapseButton"] svg,
    [data-testid="collapsedControl"] svg {{
        stroke: {t['collapse_icon']} !important;
    }}
    [data-testid="collapsedControl"] {{
        background: {t['collapse_bg']} !important;
        border: 1px solid {t['collapse_bdr']} !important;
        border-radius: 8px !important;
    }}

    /* ── Dashboard header ── */
    .dash-header {{ display:flex; align-items:center; gap:16px; padding:6px 0 18px; }}
    .dash-logo {{
        width:44px; height:44px; border-radius:12px;
        background:linear-gradient(135deg,#4f8df5,#34d399);
        display:flex; align-items:center; justify-content:center;
        font-size:17px; font-weight:700; color:#fff;
        box-shadow:0 4px 14px rgba(79,141,245,0.3);
    }}
    .dash-title {{ font-size:22px; font-weight:700; color:{t['text1']}; letter-spacing:-0.03em; margin:0; line-height:1.15; }}
    .dash-sub   {{ font-size:12.5px; color:{t['text4']}; margin:0; }}
    .live-pill {{
        display:inline-flex; align-items:center; gap:6px;
        padding:5px 14px; border-radius:20px;
        background:{t['green_bg']}; border:1px solid {t['green_bdr']};
        font-size:11px; color:{t['green']}; font-weight:600; letter-spacing:0.04em;
    }}
    .live-dot-anim {{
        width:6px; height:6px; border-radius:50%;
        background:{t['green']}; animation:lp 2s infinite;
    }}
    @keyframes lp {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.3; }} }}
    .meta-tag {{ font-size:10px; color:{t['text4']}; font-family:'JetBrains Mono',monospace; }}
    .sb-label {{
        font-size:10.5px; color:{t['sb_label']}; font-weight:600;
        text-transform:uppercase; letter-spacing:0.08em; margin-bottom:8px;
    }}
    .sb-header-title {{ color:{t['text1']}; }}

    /* ── KPI cards ── */
    .kpi-row {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:12px; }}
    .kpi {{
        background:{t['bg_card']}; border:1px solid {t['border']};
        border-radius:14px; padding:20px 22px 16px;
        transition:transform 0.2s,box-shadow 0.2s; position:relative; overflow:hidden;
    }}
    .kpi:hover  {{ transform:translateY(-2px); box-shadow:0 8px 24px rgba(0,0,0,0.12); }}
    .kpi-label  {{ font-size:10.5px; font-weight:600; color:{t['text3']}; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:10px; }}
    .kpi-val    {{ font-size:34px; font-weight:800; color:{t['text1']}; font-family:'JetBrains Mono',monospace; line-height:1; margin-bottom:12px; letter-spacing:-0.02em; }}
    .kpi-tag    {{ display:inline-flex; align-items:center; gap:5px; padding:4px 11px; border-radius:6px; font-size:11px; font-weight:500; }}
    .kpi-glow   {{ border-color:{t['red_bdr']}; box-shadow:0 0 20px {t['red_bg']}; }}
    .kpi-accent {{ position:absolute; top:0; left:0; right:0; height:3px; border-radius:14px 14px 0 0; }}
    .tag-blue  {{ background:{t['blue_bg']};  color:{t['blue']};  border:1px solid {t['blue_bdr']};  }}
    .tag-red   {{ background:{t['red_bg']};   color:{t['red']};   border:1px solid {t['red_bdr']};   }}
    .tag-amber {{ background:{t['amber_bg']}; color:{t['amber']}; border:1px solid {t['amber_bdr']}; }}
    .tag-green {{ background:{t['green_bg']}; color:{t['green']}; border:1px solid {t['green_bdr']}; }}

    /* ── Panels ── */
    .panel       {{ background:{t['bg_card']}; border:1px solid {t['border']}; border-radius:14px; }}
    .panel-head  {{ padding:14px 18px; border-bottom:1px solid {t['border']}; display:flex; justify-content:space-between; align-items:center; }}
    .panel-label {{ font-size:12.5px; font-weight:600; color:{t['text3']}; display:flex; align-items:center; gap:8px; }}
    .panel-body  {{ padding:18px; }}

    /* ── Zone cards ── */
    .zcard {{
        background:{zcard_bg}; border:1px solid {t['border']}; border-radius:10px;
        padding:13px 15px; margin-bottom:7px; transition:background 0.15s;
    }}
    .zcard:hover  {{ background:{t['border_hover']}; }}
    .zcard-crit   {{ border-color:{t['red_bdr']}; }}
    .zcard-warn   {{ border-color:{t['amber_bdr']}; }}
    .zname {{ font-size:13px; font-weight:500; color:{t['text1']}; }}
    .zmeta {{ font-size:11px; color:{t['text4']}; margin-top:3px; }}
    .zval  {{ font-family:'JetBrains Mono',monospace; font-weight:600; font-size:14px; }}
    .dot   {{ width:8px; height:8px; border-radius:50%; display:inline-block; margin-right:8px; }}
    .dot-g {{ background:{t['green']}; }}
    .dot-y {{ background:{t['amber']}; }}
    .dot-r {{ background:{t['red']}; }}
    .c-g   {{ color:{t['green']}; }}
    .c-y   {{ color:{t['amber']}; }}
    .c-r   {{ color:{t['red']}; }}
    .dbar-track {{ height:7px; border-radius:4px; background:{t['border']}; margin-top:5px; margin-bottom:14px; }}
    .dbar-fill  {{ height:100%; border-radius:4px; }}

    /* ── Alerts ── */
    .alrt      {{ padding:12px 18px; border-bottom:1px solid {t['border']}; }}
    .alrt-crit {{ border-left:3px solid {t['red']};   background:{t['red_bg']};   }}
    .alrt-warn {{ border-left:3px solid {t['amber']}; background:{t['amber_bg']}; }}
    .alrt-zone {{ font-size:13px; font-weight:500; color:{t['text1']}; }}
    .alrt-msg  {{ font-size:12px; color:{t['text3']}; line-height:1.45; margin-top:3px; }}
    .alrt-time {{ font-size:10px; color:{t['text4']}; font-family:'JetBrains Mono',monospace; }}

    /* ── Radio buttons ── */
    section[data-testid="stSidebar"] div[role="radiogroup"] {{
        color: {t['text3']} !important;
    }}
    section[data-testid="stSidebar"] .stRadio label > div:first-child {{
        border-color: {t['text3']} !important;
        color: {t['text3']} !important;
    }}

    /* ── Sliders ── */
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stSlider label p {{
        color: {t['sb_text']} !important;
        font-size: 12px !important;
        font-family: 'Inter', sans-serif !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSliderTickBar"],
    section[data-testid="stSidebar"] [data-testid="stSliderTickBar"] div,
    section[data-testid="stSidebar"] [data-testid="stTickBarMin"],
    section[data-testid="stSidebar"] [data-testid="stTickBarMax"] {{
        color: {t['text2']} !important;
        background: transparent !important;
        font-size: 10px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600 !important;
        opacity: 1 !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] {{
        background-color: {t['blue']} !important;
        border-color: {t['blue']} !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"]:focus {{
        box-shadow: 0 0 0 4px {t['blue_bg']} !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="slider"] > div > div:first-child {{
        background-color: {t['border']} !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="slider"] > div > div:nth-child(2) {{
        background-color: {t['blue']} !important;
    }}

    /* ── Subscription text input ── */
    section[data-testid="stSidebar"] .stTextInput input {{
        background-color: {t['bg_card']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 8px !important;
        color: {t['text1']} !important;
        font-size: 13px !important;
        font-family: 'JetBrains Mono', monospace !important;
        padding: 8px 12px !important;
    }}
    section[data-testid="stSidebar"] .stTextInput input:focus {{
        border-color: {t['blue']} !important;
        box-shadow: 0 0 0 3px {t['blue_bg']} !important;
        outline: none !important;
    }}
    section[data-testid="stSidebar"] .stTextInput input::placeholder {{
        color: {t['text4']} !important;
        font-size: 11px !important;
    }}

    /* ── Sidebar buttons ── */
    section[data-testid="stSidebar"] .stButton > button {{
        border-radius: 8px !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        padding: 6px 10px !important;
        transition: all 0.2s !important;
        border: 1px solid {t['border']} !important;
        background-color: {t['bg_card']} !important;
        color: {t['text2']} !important;
    }}
    section[data-testid="stSidebar"] .stButton > button:hover {{
        border-color: {t['blue']} !important;
        color: {t['blue']} !important;
        background-color: {t['blue_bg']} !important;
    }}
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
        background-color: {t['blue']} !important;
        border-color: {t['blue']} !important;
        color: #ffffff !important;
    }}
    section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
        background-color: {t['blue']} !important;
        opacity: 0.88;
        color: #ffffff !important;
    }}

    /* ── Subscription feedback pills ── */
    .sb-feedback {{
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 11.5px;
        font-weight: 500;
        margin-top: 6px;
        font-family: 'Inter', sans-serif;
        line-height: 1.4;
    }}
    .sb-ok  {{ background:{t['green_bg']}; color:{t['green']}; border:1px solid {t['green_bdr']}; }}
    .sb-err {{ background:{t['red_bg']};   color:{t['red']};   border:1px solid {t['red_bdr']};   }}
    .sb-warn {{ background:{t['amber_bg']}; color:{t['amber']}; border:1px solid {t['amber_bdr']}; }}

    /* ── Misc ── */
    .note-box {{
        font-size:10px; color:{t['text4']}; font-family:'JetBrains Mono',monospace;
        background:{t['border']}; padding:4px 10px; border-radius:6px;
    }}

    /* ── Native widgets — main content (Live Lookup + any st.* calls) ── */

    /* Page background & text */
    .stMainBlockContainer, .block-container {{
        background-color: {t['bg']} !important;
    }}
    .stMarkdown p, .stMarkdown span, .stMarkdown li {{
        color: {t['text2']} !important;
    }}
    h1, h2, h3, h4, .stSubheader {{
        color: {t['text1']} !important;
    }}
    [data-testid="stCaptionContainer"] p {{
        color: {t['text4']} !important;
        font-size: 12px !important;
    }}

    /* Text inputs */
    .stTextInput input {{
        background-color: {t['bg_card']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 8px !important;
        color: {t['text1']} !important;
        font-size: 14px !important;
        font-family: 'Inter', sans-serif !important;
    }}
    .stTextInput input:focus {{
        border-color: {t['blue']} !important;
        box-shadow: 0 0 0 3px {t['blue_bg']} !important;
        outline: none !important;
    }}
    .stTextInput input::placeholder {{ color: {t['text4']} !important; }}
    .stTextInput label p {{ color: {t['text3']} !important; font-size: 13px !important; }}

    /* Selectbox */
    [data-baseweb="select"] > div {{
        background-color: {t['bg_card']} !important;
        border-color: {t['border']} !important;
        border-radius: 8px !important;
        color: {t['text1']} !important;
    }}
    [data-baseweb="select"] span {{ color: {t['text1']} !important; }}
    [data-baseweb="popover"] ul, [data-baseweb="menu"] {{
        background-color: {t['bg_card']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 8px !important;
    }}
    [role="option"] {{
        background-color: {t['bg_card']} !important;
        color: {t['text1']} !important;
    }}
    [role="option"]:hover {{ background-color: {t['blue_bg']} !important; }}
    .stSelectbox label p {{ color: {t['text3']} !important; font-size: 13px !important; }}

    /* Buttons — main content */
    .stMainBlockContainer .stButton > button {{
        background-color: {t['bg_card']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 8px !important;
        color: {t['text2']} !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.2s !important;
    }}
    .stMainBlockContainer .stButton > button:hover {{
        border-color: {t['blue']} !important;
        color: {t['blue']} !important;
        background-color: {t['blue_bg']} !important;
    }}
    .stMainBlockContainer .stButton > button[kind="primary"] {{
        background-color: {t['blue']} !important;
        border-color: {t['blue']} !important;
        color: #ffffff !important;
    }}
    .stMainBlockContainer .stButton > button[kind="primary"]:hover {{
        opacity: 0.88 !important;
    }}

    /* Expanders */
    .stExpander {{
        background-color: {t['bg_card']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 10px !important;
    }}
    .stExpander summary {{
        color: {t['text2']} !important;
        background-color: {t['bg_card']} !important;
        border-radius: 10px !important;
    }}
    .stExpander summary:hover {{ background-color: {t['border']} !important; }}
    .stExpander summary p {{ color: {t['text2']} !important; font-weight: 500 !important; }}
    [data-testid="stExpanderToggleIcon"] svg {{ stroke: {t['text3']} !important; }}
    .stExpander [data-testid="stExpanderDetails"] {{
        background-color: {t['bg_card']} !important;
    }}

    /* Sliders — main content */
    .stMainBlockContainer .stSlider label p {{ color: {t['text3']} !important; }}
    .stMainBlockContainer [data-baseweb="slider"] div[role="slider"] {{
        background-color: {t['blue']} !important;
        border-color: {t['blue']} !important;
    }}
    .stMainBlockContainer [data-baseweb="slider"] > div > div:nth-child(2) {{
        background-color: {t['blue']} !important;
    }}

    /* Metrics */
    div[data-testid="stMetric"] {{
        background-color: {t['bg_card']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 10px !important;
        padding: 14px 18px !important;
    }}
    [data-testid="stMetricValue"] {{
        color: {t['text1']} !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
    }}
    [data-testid="stMetricLabel"] p {{
        color: {t['text3']} !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }}

    /* Info / warning / error / success boxes */
    [data-testid="stNotificationContentInfo"] {{
        background-color: {t['blue_bg']} !important;
        border-color: {t['blue_bdr']} !important;
        color: {t['text1']} !important;
        border-radius: 8px !important;
    }}
    [data-testid="stNotificationContentWarning"] {{
        background-color: {t['amber_bg']} !important;
        border-color: {t['amber_bdr']} !important;
        color: {t['text1']} !important;
        border-radius: 8px !important;
    }}
    [data-testid="stNotificationContentError"] {{
        background-color: {t['red_bg']} !important;
        border-color: {t['red_bdr']} !important;
        color: {t['text1']} !important;
        border-radius: 8px !important;
    }}
    [data-testid="stNotificationContentSuccess"] {{
        background-color: {t['green_bg']} !important;
        border-color: {t['green_bdr']} !important;
        color: {t['text1']} !important;
        border-radius: 8px !important;
    }}

    /* Spinner */
    [data-testid="stSpinner"] p {{ color: {t['text3']} !important; }}

    /* Dataframes */
    [data-testid="stDataFrame"] {{
        border: 1px solid {t['border']} !important;
        border-radius: 8px !important;
    }}
</style>
"""
