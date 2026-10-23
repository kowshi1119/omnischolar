"""
ui_components.py — OmniScholar UI primitives

Design System v2: Warm Teal + Scholarly Gold + Neon Live Indicator
Fonts: Fraunces (display) · DM Sans (body) · JetBrains Mono (code/metrics)
"""

import streamlit as st

# ── Colour palette ─────────────────────────────────────────────────────────────
COLORS = {
    # Core palette
    "bg":             "#060A14",
    "surface":        "#0D1B2A",
    "surface2":       "#0A1628",
    "primary":        "#00B4A6",
    "primary_glow":   "#00D4C8",
    "neon":           "#39FF14",
    "gold":           "#D4A24C",
    "amber":          "#FFB830",
    "danger":         "#FF4757",
    "text_primary":   "#F0F4F8",
    "text_secondary": "#8899AA",
    "text_dim":       "#3A5060",
    "border":         "rgba(0,180,166,0.15)",
    "border_gold":    "rgba(212,162,76,0.3)",
    # Backward-compat aliases — do not remove
    "card":           "#0D1B2A",
    "section":        "#0A1628",
    "muted":          "#8899AA",
    "text":           "#8899AA",
    "primary_old":    "#00D4FF",
    "green":          "#39FF14",
    "red":            "#FF4757",
    # Font keys
    "mono":           "JetBrains Mono",
    "sans":           "DM Sans",
    "display":        "Fraunces",
    "sinhala":        "Noto Sans Sinhala",
    "tamil":          "Noto Sans Tamil",
}

# ── Premium CSS injection ──────────────────────────────────────────────────────

def inject_premium_css():
    # Permissions-Policy meta to reduce browser console noise
    st.markdown("""
    <meta http-equiv="Permissions-Policy"
      content="ambient-light-sensor=(), battery=(), camera=(),
               microphone=(), geolocation=()">
    """, unsafe_allow_html=True)
    st.markdown("""
    <style>
    /* ══════════════════════════════════════
       FONTS
    ══════════════════════════════════════ */
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,700;1,9..144,400&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&family=JetBrains+Mono:wght@400;600&family=Noto+Sans+Sinhala:wght@400;600&family=Noto+Sans+Tamil:wght@400;600&display=swap');

    /* ══════════════════════════════════════
       DESIGN TOKENS
    ══════════════════════════════════════ */
    :root {
      --color-bg:             #060A14;
      --color-surface:        #0D1B2A;
      --color-surface2:       #0A1628;
      --color-primary:        #00B4A6;
      --color-primary-glow:   #00D4C8;
      --color-neon:           #39FF14;
      --color-gold:           #D4A24C;
      --color-amber:          #FFB830;
      --color-danger:         #FF4757;
      --color-text-primary:   #F0F4F8;
      --color-text-secondary: #8899AA;
      --color-text-dim:       #3A5060;
      --color-border:         rgba(0,180,166,0.15);
      --color-border-gold:    rgba(212,162,76,0.3);
      --font-display:         'Fraunces', serif;
      --font-sans:            'DM Sans', sans-serif;
      --font-mono:            'JetBrains Mono', monospace;
      --font-sinhala:         'Noto Sans Sinhala', sans-serif;
      --font-tamil:           'Noto Sans Tamil', sans-serif;
      --radius-card:          12px;
      --radius-chip:          20px;
      --radius-btn:           8px;
      --transition-fast:      0.15s ease;
      --transition-normal:    0.3s ease;
    }

    /* ══════════════════════════════════════
       BASE
    ══════════════════════════════════════ */
    html, body, [data-testid="stAppViewContainer"] {
        background: var(--color-bg) !important;
        color: var(--color-text-secondary) !important;
        font-family: var(--font-sans) !important;
    }
    [data-testid="stMain"] { background: transparent !important; }

    /* ══════════════════════════════════════
       ANIMATED GRADIENT MESH BACKGROUND
    ══════════════════════════════════════ */
    [data-testid="stAppViewContainer"]::before {
      content: "";
      position: fixed;
      inset: 0;
      z-index: 0;
      pointer-events: none;
      background:
        radial-gradient(ellipse 80% 50% at 20% 30%,
          rgba(0,180,166,0.06) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 70%,
          rgba(212,162,76,0.03) 0%, transparent 60%),
        radial-gradient(ellipse 50% 60% at 50% 10%,
          rgba(0,180,166,0.04) 0%, transparent 60%);
      animation: mesh-drift 25s ease-in-out infinite alternate;
    }

    /* ══════════════════════════════════════
       SIDEBAR
    ══════════════════════════════════════ */
    [data-testid="stSidebar"] {
        background: var(--color-surface2) !important;
        border-right: 1px solid var(--color-border) !important;
    }

    /* ══════════════════════════════════════
       TYPOGRAPHY
    ══════════════════════════════════════ */
    h1                    { font-family: var(--font-display) !important; }
    h2, h3                { font-family: var(--font-sans) !important; }
    body, p, label        { font-family: var(--font-sans) !important; }
    code, .metric, .badge { font-family: var(--font-mono) !important; }
    .sinhala-text         { font-family: var(--font-sinhala) !important; }
    .tamil-text           { font-family: var(--font-tamil) !important; }

    h1 { color: var(--color-text-primary) !important; font-weight: 700 !important; font-size: 1.6rem !important; letter-spacing: -0.01em !important; }
    h2 { color: var(--color-text-primary) !important; font-weight: 600 !important; font-size: 1.2rem !important; }
    h3 { color: var(--color-text-secondary) !important; font-weight: 500 !important; font-size: 1rem !important; }
    p, li, div { color: var(--color-text-secondary) !important; font-size: 0.875rem !important; }
    strong, b  { color: var(--color-text-primary) !important; font-weight: 600 !important; }
    code, pre  { font-family: var(--font-mono) !important; }

    /* ══════════════════════════════════════
       BUTTONS
    ══════════════════════════════════════ */
    .stButton > button {
        background: transparent !important;
        border: 1px solid rgba(0,180,166,0.35) !important;
        border-radius: var(--radius-btn) !important;
        color: #00B4A6 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        padding: 8px 18px !important;
        transition: all var(--transition-fast) !important;
    }
    .stButton > button:hover {
        background: rgba(0,180,166,0.1) !important;
        border-color: #00D4FF !important;
        border-color: #00B4A6 !important;
        color: #FFFFFF !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(0,180,166,0.2) !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00B4A6, #008A80) !important;
        border: none !important;
        color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #00C8B8, #00A090) !important;
        box-shadow: 0 6px 24px rgba(0,180,166,0.35) !important;
        transform: translateY(-2px) !important;
    }

    /* ══════════════════════════════════════
       INPUTS
    ══════════════════════════════════════ */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(8, 16, 32, 0.95) !important;
        border: 1px solid rgba(0,180,166,0.2) !important;
        border-radius: 6px !important;
        color: #D0E4F8 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.88rem !important;
        padding: 9px 12px !important;
        caret-color: #00B4A6 !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: rgba(0,180,166,0.5) !important;
        box-shadow: 0 0 0 3px rgba(0,180,166,0.08) !important;
        background: rgba(0,20,40,0.98) !important;
    }
    .stTextInput > label, .stTextArea > label {
        color: #3A6080 !important;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: rgba(60,90,120,0.7) !important;
    }

    /* ══════════════════════════════════════
       SELECTBOX / DROPDOWN
    ══════════════════════════════════════ */
    .stSelectbox > div > div {
        background: rgba(8,16,32,0.95) !important;
        border: 1px solid rgba(0,180,166,0.2) !important;
        border-radius: 6px !important;
        color: #D0E4F8 !important;
    }
    .stSelectbox > label {
        color: #3A6080 !important;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
    }
    [data-baseweb="select"] ul {
        background: #0C1828 !important;
        border: 1px solid rgba(0,180,166,0.15) !important;
    }
    [data-baseweb="select"] li {
        color: #A0B8D0 !important;
        font-size: 0.85rem !important;
    }
    [data-baseweb="select"] li:hover {
        background: rgba(0,180,166,0.08) !important;
        color: #E8F4FF !important;
    }

    /* ══════════════════════════════════════
       RADIO BUTTONS
    ══════════════════════════════════════ */
    .stRadio label {
        color: #6A8098 !important;
        font-size: 0.85rem !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        font-size: 0.82rem !important;
        padding: 3px 0 !important;
        color: #4A6080 !important;
    }
    [data-testid="stSidebar"] .stRadio label:hover { color: #90B8D8 !important; }

    /* ══════════════════════════════════════
       METRICS
    ══════════════════════════════════════ */
    [data-testid="metric-container"] {
        background: rgba(8,16,32,0.9) !important;
        border: 1px solid rgba(0,180,166,0.1) !important;
        border-radius: 8px !important;
        padding: 14px 16px !important;
    }
    [data-testid="stMetricLabel"] {
        color: #2A4060 !important;
        font-size: 0.65rem !important;
        letter-spacing: 0.15em !important;
        text-transform: uppercase !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    [data-testid="stMetricValue"] {
        color: #00B4A6 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.8rem !important;
        font-weight: 600 !important;
    }

    /* ══════════════════════════════════════
       ALERTS
    ══════════════════════════════════════ */
    .stSuccess {
        background: rgba(0,200,80,0.06) !important;
        border: 1px solid rgba(0,200,80,0.2) !important;
        border-left: 3px solid #00C850 !important;
        border-radius: 0 6px 6px 0 !important;
    }
    .stSuccess p { color: #60C890 !important; }
    .stWarning {
        background: rgba(255,184,0,0.06) !important;
        border: 1px solid rgba(255,184,0,0.2) !important;
        border-left: 3px solid #FFB800 !important;
        border-radius: 0 6px 6px 0 !important;
    }
    .stWarning p { color: #C89040 !important; }
    .stError {
        background: rgba(239,68,68,0.06) !important;
        border: 1px solid rgba(239,68,68,0.2) !important;
        border-left: 3px solid #EF4444 !important;
        border-radius: 0 6px 6px 0 !important;
    }
    .stError p { color: #D07070 !important; }
    .stInfo {
        background: rgba(0,180,166,0.05) !important;
        border: 1px solid rgba(0,180,166,0.15) !important;
        border-left: 3px solid #00B4A6 !important;
        border-radius: 0 6px 6px 0 !important;
    }
    .stInfo p { color: #509090 !important; }

    /* ══════════════════════════════════════
       EXPANDERS
    ══════════════════════════════════════ */
    .streamlit-expanderHeader {
        background: rgba(8,16,32,0.8) !important;
        border: 1px solid rgba(0,180,166,0.12) !important;
        border-radius: 6px !important;
        color: #5090A0 !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        font-family: 'DM Sans', sans-serif !important;
        letter-spacing: 0.04em !important;
        padding: 10px 14px !important;
    }
    .streamlit-expanderHeader:hover {
        border-color: rgba(0,180,166,0.25) !important;
        color: #80B8C8 !important;
    }
    .streamlit-expanderContent {
        background: rgba(6,10,20,0.6) !important;
        border: 1px solid rgba(0,180,166,0.08) !important;
        border-top: none !important;
        border-radius: 0 0 6px 6px !important;
        padding: 14px !important;
    }

    /* ══════════════════════════════════════
       PROGRESS
    ══════════════════════════════════════ */
    .stProgress > div > div {
        background: rgba(0,180,166,0.06) !important;
        border-radius: 3px !important;
    }
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #004840, #00B4A6) !important;
        border-radius: 3px !important;
        transition: width 0.5s ease !important;
    }

    /* ══════════════════════════════════════
       TABS
    ══════════════════════════════════════ */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(8,16,32,0.8) !important;
        border-bottom: 1px solid rgba(0,180,166,0.1) !important;
        border-radius: 6px 6px 0 0 !important;
        gap: 2px !important;
        padding: 4px 4px 0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #3A5070 !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.06em !important;
        font-family: 'DM Sans', sans-serif !important;
        text-transform: uppercase !important;
    }
    .stTabs [aria-selected="true"] {
        color: #00B4A6 !important;
        border-bottom: 2px solid #00B4A6 !important;
    }

    /* ══════════════════════════════════════
       SCROLLBAR
    ══════════════════════════════════════ */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: #060A14; }
    ::-webkit-scrollbar-thumb {
        background: rgba(0,180,166,0.2);
        border-radius: 2px;
    }

    /* ══════════════════════════════════════
       DIVIDER
    ══════════════════════════════════════ */
    hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg,transparent,rgba(0,180,166,0.15),transparent) !important;
        margin: 16px 0 !important;
    }

    /* ══════════════════════════════════════
       DATE INPUT
    ══════════════════════════════════════ */
    .stDateInput > div > div > input {
        background: rgba(8,16,32,0.95) !important;
        border: 1px solid rgba(0,180,166,0.2) !important;
        color: #D0E4F8 !important;
        border-radius: 6px !important;
    }

    /* ══════════════════════════════════════
       BRAND CLASSES
    ══════════════════════════════════════ */
    .omni-header {
        font-family: 'DM Sans', sans-serif;
        font-size: 1rem;
        font-weight: 700;
        color: #00B4A6;
        letter-spacing: 0.2em;
        text-align: center;
        padding: 14px 0 16px;
        border-bottom: 1px solid rgba(0,180,166,0.1);
        margin-bottom: 10px;
    }
    .omni-subtitle {
        font-size: 0.55rem;
        color: #1A3050;
        letter-spacing: 0.25em;
        text-align: center;
        margin-top: -8px;
        margin-bottom: 12px;
        text-transform: uppercase;
        font-family: 'JetBrains Mono', monospace;
    }

    /* ══════════════════════════════════════
       HIDE STREAMLIT UI
    ══════════════════════════════════════ */
    #MainMenu, footer, header { visibility: hidden !important; }
    .stDeployButton { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }

    /* ══════════════════════════════════════
       MODE CARDS
    ══════════════════════════════════════ */
    .omni-mode-card {
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-card);
        padding: 14px 18px;
        margin: 6px 0;
        position: relative;
        overflow: hidden;
        transition: border-color var(--transition-fast), background var(--transition-fast);
        cursor: pointer;
    }
    .omni-mode-card:hover {
        border-color: rgba(0,180,166,0.3);
        background: rgba(0,28,50,0.95);
    }
    .omni-mode-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg,transparent,rgba(0,180,166,0.3),transparent);
    }
    .omni-section-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 8px;
        color: #1E3A5A;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        margin: 16px 0 8px;
    }
    .omni-tag {
        display: inline-block;
        font-family: 'JetBrains Mono', monospace;
        font-size: 9px;
        padding: 2px 8px;
        border-radius: 10px;
        letter-spacing: 0.08em;
        margin: 2px;
    }
    .omni-tag-cyan {
        background: rgba(0,212,255,0.08);
        border: 1px solid rgba(0,212,255,0.15);
        color: #3A7090;
    }
    .omni-tag-amber {
        background: rgba(255,184,0,0.08);
        border: 1px solid rgba(255,184,0,0.15);
        color: #806040;
    }
    .omni-tag-green {
        background: rgba(0,200,80,0.08);
        border: 1px solid rgba(0,200,80,0.15);
        color: #306050;
    }
    .omni-stat-row {
        display: flex;
        gap: 8px;
        margin: 10px 0;
    }
    .omni-stat {
        flex: 1;
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-card);
        padding: 10px 12px;
        text-align: center;
    }
    .omni-stat-num {
        font-family: var(--font-mono);
        font-size: 2.5rem;
        font-weight: 700;
        line-height: 1;
    }
    .omni-stat-label {
        font-family: var(--font-mono);
        font-size: 0.6rem;
        color: var(--color-text-dim);
        letter-spacing: 0.2em;
        text-transform: uppercase;
        margin-top: 6px;
    }

    /* ══════════════════════════════════════
       MULTISELECT TAGS
    ══════════════════════════════════════ */
    .stMultiSelect > div > div {
        background: rgba(8,16,32,0.9) !important;
        border: 1px solid rgba(0,180,166,0.2) !important;
        border-radius: 6px !important;
    }
    .stMultiSelect [data-baseweb="tag"] {
        background: rgba(0,180,166,0.1) !important;
        color: #00B4A6 !important;
        border-radius: 4px !important;
    }

    /* ══════════════════════════════════════
       SLIDER
    ══════════════════════════════════════ */
    .stSlider > div > div > div {
        background: rgba(0,180,166,0.1) !important;
    }
    .stSlider > div > div > div > div {
        background: linear-gradient(90deg, #003A38, #00B4A6) !important;
    }

    /* ══════════════════════════════════════
       FILE UPLOADER
    ══════════════════════════════════════ */
    [data-testid="stFileUploader"] {
        background: rgba(8,16,32,0.9) !important;
        border: 1px dashed rgba(0,180,166,0.25) !important;
        border-radius: 6px !important;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: rgba(0,180,166,0.5) !important;
        background: rgba(0,18,38,0.95) !important;
    }

    /* ══════════════════════════════════════
       SPINNER
    ══════════════════════════════════════ */
    .stSpinner > div {
        border-top-color: #00B4A6 !important;
    }

    /* ══════════════════════════════════════
       CODE BLOCKS
    ══════════════════════════════════════ */
    .stCodeBlock {
        background: rgba(6,10,20,0.95) !important;
        border: 1px solid rgba(0,180,166,0.12) !important;
        border-radius: 6px !important;
    }
    code {
        color: #00B4A6 !important;
        background: rgba(0,180,166,0.06) !important;
        padding: 1px 5px !important;
        border-radius: 3px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.82rem !important;
    }

    /* ══════════════════════════════════════
       DATAFRAMES
    ══════════════════════════════════════ */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(0,180,166,0.1) !important;
        border-radius: 6px !important;
        overflow: hidden !important;
    }

    /* ══════════════════════════════════════
       ACTIVE MODE HIGHLIGHT
    ══════════════════════════════════════ */
    [data-testid="stSidebar"] .stRadio [aria-checked="true"] + div {
        color: #00B4A6 !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] .stRadio div[data-testid] {
        padding: 2px 0 !important;
    }

    /* ══════════════════════════════════════
       EXPANDER CONTENT TEXT
    ══════════════════════════════════════ */
    .streamlit-expanderContent p,
    .streamlit-expanderContent li,
    .streamlit-expanderContent span {
        color: #8AAAC0 !important;
    }
    .streamlit-expanderContent strong {
        color: #C0D8F0 !important;
    }
    .streamlit-expanderContent code {
        color: #00B4A6 !important;
    }

    /* ══════════════════════════════════════
       OMNI-CARD SYSTEM
    ══════════════════════════════════════ */
    .omni-card {
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-card);
      padding: 20px 24px;
      position: relative;
      overflow: hidden;
      transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
    }
    .omni-card::before {
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 1px;
      background: linear-gradient(90deg,
        transparent 0%, rgba(0,180,166,0.5) 50%, transparent 100%);
    }
    .omni-card:hover {
      border-color: rgba(0,180,166,0.3);
      box-shadow: 0 8px 32px rgba(0,180,166,0.08), 0 2px 8px rgba(0,0,0,0.4);
      transform: translateY(-1px);
    }
    .omni-card-gold {
      border-color: var(--color-border-gold);
    }
    .omni-card-gold::before {
      background: linear-gradient(90deg, transparent, rgba(212,162,76,0.5), transparent);
    }
    .omni-card-gold:hover {
      border-color: rgba(212,162,76,0.5);
      box-shadow: 0 8px 32px rgba(212,162,76,0.1);
    }

    /* ══════════════════════════════════════
       CHIP / TAG SYSTEM
    ══════════════════════════════════════ */
    .omni-chip {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 3px 10px;
      border-radius: var(--radius-chip);
      font-family: var(--font-mono);
      font-size: 0.65rem;
      font-weight: 600;
      letter-spacing: 0.05em;
      white-space: nowrap;
    }
    .omni-chip:hover { transform: scale(1.05); transition: transform var(--transition-fast); }
    .omni-chip-teal  { background: rgba(0,180,166,0.12);  color: #00B4A6; border: 1px solid rgba(0,180,166,0.3); }
    .omni-chip-gold  { background: rgba(212,162,76,0.12); color: #D4A24C; border: 1px solid rgba(212,162,76,0.3); }
    .omni-chip-neon  { background: rgba(57,255,20,0.08);  color: #39FF14; border: 1px solid rgba(57,255,20,0.25); }
    .omni-chip-red   { background: rgba(255,71,87,0.10);  color: #FF4757; border: 1px solid rgba(255,71,87,0.3); }
    .omni-chip-amber { background: rgba(255,184,48,0.10); color: #FFB830; border: 1px solid rgba(255,184,48,0.3); }
    .omni-chip-blue  { background: rgba(59,130,246,0.10); color: #60A5FA; border: 1px solid rgba(59,130,246,0.25); }

    /* ══════════════════════════════════════
       KEYFRAMES & UTILITIES
    ══════════════════════════════════════ */
    @keyframes fade-in       { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
    @keyframes slide-right   { from { opacity:0; transform:translateX(-12px); } to { opacity:1; transform:translateX(0); } }
    @keyframes scale-in      { from { opacity:0; transform:scale(0.95); } to { opacity:1; transform:scale(1); } }
    @keyframes pulse-neon    { 0%,100% { box-shadow:0 0 4px rgba(57,255,20,0.3); } 50% { box-shadow:0 0 18px rgba(57,255,20,0.7), 0 0 36px rgba(57,255,20,0.3); } }
    @keyframes pulse-teal    { 0%,100% { box-shadow:0 0 4px rgba(0,180,166,0.3); } 50% { box-shadow:0 0 16px rgba(0,180,166,0.6); } }
    @keyframes seal-breathe  { 0%,100% { box-shadow:0 0 8px rgba(212,162,76,0.3),0 0 0 0 rgba(212,162,76,0); } 50% { box-shadow:0 0 20px rgba(212,162,76,0.6),0 0 0 4px rgba(212,162,76,0.1); } }
    @keyframes thinking-dots { 0%,80%,100% { opacity:0.2; transform:scale(0.8); } 40% { opacity:1; transform:scale(1.2); } }
    @keyframes omni-breathe  { 0%,100% { transform:scale(1); } 50% { transform:scale(1.04); } }
    @keyframes bar-fill      { from { width:0% !important; } }
    @keyframes mesh-drift    { 0% { opacity:1; transform:scale(1) translateY(0); } 100% { opacity:0.7; transform:scale(1.05) translateY(-10px); } }
    @keyframes omni-fadein   { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }

    .fade-in   { animation: fade-in     0.35s ease forwards; }
    .slide-in  { animation: slide-right 0.25s ease forwards; }
    .scale-in  { animation: scale-in    0.3s  ease forwards; }
    .stagger-1 { animation-delay: 0ms; }
    .stagger-2 { animation-delay: 100ms; }
    .stagger-3 { animation-delay: 200ms; }
    .stagger-4 { animation-delay: 300ms; }
    .stagger-5 { animation-delay: 400ms; }

    [data-testid="stMain"] > div { animation: omni-fadein 0.25s ease; }

    /* ══════════════════════════════════════
       OMNISCHOLAR-CARD (backward compat)
    ══════════════════════════════════════ */
    .omnischolar-card {
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-card);
        padding: 20px 24px;
        position: relative;
        overflow: hidden;
    }

    </style>
    """, unsafe_allow_html=True)


# ── RAG grounding indicator ────────────────────────────────────────────────────

def render_grounding_indicator(sources: list | None = None,
                                coverage: float | None = None,
                                level: str | float | None = None) -> None:
    """
    Compact metadata chip shown below AI responses.
    level: float 0.0-1.0, or str 'grounded'|'curriculum'|'uncertain'
    """
    if sources is None:
        sources = []
    n = len(sources)

    if isinstance(level, (int, float)):
        lv = float(level)
        if lv > 0.7:
            chip_cls = "omni-chip-teal"
            icon = "🟢"
            label = f"From your notes · {sources[0][:35]}" if sources else "From your notes"
        elif lv > 0.3:
            chip_cls = "omni-chip-amber"
            icon = "🟡"
            label = f"Partly from your notes ({int(lv * 100)}%)"
        else:
            chip_cls = "omni-chip-blue"
            icon = "🔵"
            label = "Model knowledge — verify key facts"
    elif level == "grounded":
        chip_cls = "omni-chip-teal"
        icon = "🟢"
        label = f"From your notes · {sources[0][:35]}" if sources else "From your notes"
    elif level == "uncertain":
        chip_cls = "omni-chip-red"
        icon = "🔴"
        label = "Uncertain — check your textbook"
    elif level == "curriculum":
        chip_cls = "omni-chip-amber"
        icon = "🟡"
        label = "Curriculum knowledge — verify key facts"
    else:
        pct = (coverage or 0.0) * 100
        if pct >= 60 or n >= 3:
            chip_cls, icon, label = "omni-chip-teal", "🟢", "From your notes"
        elif pct >= 20 or n >= 1:
            chip_cls, icon, label = "omni-chip-amber", "🟡", "Curriculum knowledge"
        else:
            chip_cls, icon, label = "omni-chip-blue", "🔵", "Model knowledge — verify key facts"

    st.markdown(
        f'<div class="fade-in" style="margin-top:8px;">'
        f'<span class="omni-chip {chip_cls}" style="font-size:0.6rem;padding:2px 8px;">'
        f'{icon} {label}'
        f'</span></div>',
        unsafe_allow_html=True,
    )


# ── Ollama status chip ────────────────────────────────────────────────────────

def render_ollama_status_chip(connected: bool, model: str = "gemma4:e4b") -> None:
    """Inline teal/neon chip when connected, red chip when offline. Shows on every screen."""
    if connected:
        anim_style = "animation: pulse-neon 2s ease-in-out infinite;"
        bg = "rgba(57,255,20,0.08)"
        border = "rgba(57,255,20,0.25)"
        color = "#39FF14"
        label = f"● {model} — ONLINE"
        hint = ""
    else:
        anim_style = ""
        bg = "rgba(255,71,87,0.10)"
        border = "rgba(255,71,87,0.3)"
        color = "#FF4757"
        label = "● Gemma 4 — OFFLINE"
        hint = '<div style="font-size:0.58rem;color:#FF4757;opacity:0.7;margin-top:2px;letter-spacing:0.04em;">run: ollama serve</div>'
    st.markdown(
        f'<div style="display:inline-flex;flex-direction:column;gap:1px;'
        f'background:{bg};border:1px solid {border};'
        f'border-radius:20px;padding:4px 12px;'
        f'font-family:\'JetBrains Mono\',monospace;{anim_style}'
        f'margin-bottom:4px;">'
        f'<span style="font-size:0.72rem;font-weight:600;color:{color};">{label}</span>'
        f'<span style="font-size:0.58rem;color:#3A5060;letter-spacing:0.04em;">9.6GB · 128K ctx · 100% offline</span>'
        f'{hint}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Thinking state indicator ───────────────────────────────────────────────────

def render_thinking_state(message: str = "Gemma 4 is thinking...") -> None:
    """Rich animated .omni-card thinking indicator while model generates response."""
    try:
        from _new_avatar import render_dr_omni_svg
        owl_html = render_dr_omni_svg(emotion="thinking", size=48)
    except Exception:
        owl_html = '<span style="font-size:1.6rem;animation:omni-breathe 2s ease-in-out infinite;filter:drop-shadow(0 0 6px rgba(57,255,20,0.5));">🦉</span>'
    st.markdown(f"""
    <div class="omni-card fade-in" style="display:flex;align-items:center;gap:14px;padding:14px 20px;">
      <div style="flex-shrink:0;filter:drop-shadow(0 0 6px rgba(57,255,20,0.5));">
        {owl_html}
      </div>
      <div style="flex:1;">
        <span class="omni-chip omni-chip-teal"
              style="animation:pulse-teal 1.8s ease-in-out infinite;">
          &#10227; Gemma 4 E4B reasoning...
          <span style="animation:thinking-dots 1.4s ease-in-out infinite;
                       animation-delay:0s;display:inline-block;">&#183;</span>
          <span style="animation:thinking-dots 1.4s ease-in-out infinite;
                       animation-delay:0.2s;display:inline-block;">&#183;</span>
          <span style="animation:thinking-dots 1.4s ease-in-out infinite;
                       animation-delay:0.4s;display:inline-block;">&#183;</span>
        </span>
      </div>
      <div style="font-family:var(--font-mono);font-size:0.6rem;color:#2A4A3A;
                  text-align:right;flex-shrink:0;line-height:1.6;">
        Searching your notes<br>&#8594; Generating response
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Welcome banner ─────────────────────────────────────────────────────────────

def render_welcome_banner(name: str = "Kowshi") -> None:
    """2-column card banner — name + Ollama/privacy status chips."""
    connected = st.session_state.get("ollama_connected", False)
    if connected:
        ollama_chip = (
            '<span class="omni-chip omni-chip-neon" '
            'style="animation:pulse-neon 2s ease-in-out infinite;">'
            '&#9679; gemma4:e4b &mdash; ONLINE</span>'
        )
    else:
        ollama_chip = '<span class="omni-chip omni-chip-red">&#9679; Gemma 4 &mdash; OFFLINE</span>'
    st.markdown(
        f'<div class="omni-card fade-in" style="'
        f'background:linear-gradient(135deg,rgba(0,180,166,0.07) 0%,rgba(13,27,42,0.9) 100%);'
        f'margin-bottom:16px;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;gap:16px;">'
        f'<div>'
        f'<div style="font-family:var(--font-mono);font-size:0.58rem;color:#3A5060;'
        f'letter-spacing:0.22em;text-transform:uppercase;margin-bottom:6px;">WELCOME BACK</div>'
        f'<div style="font-family:var(--font-display);font-size:2rem;font-weight:700;'
        f'color:#F0F4F8;letter-spacing:-0.02em;line-height:1.1;margin-bottom:6px;">{name}</div>'
        f'<div style="font-family:var(--font-sans);font-size:0.88rem;color:#8899AA;">'
        f'Your offline AI study companion</div>'
        f'</div>'
        f'<div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end;flex-shrink:0;">'
        f'{ollama_chip}'
        f'<span class="omni-chip omni-chip-gold">&#128274; Offline &middot; Fully Private</span>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Exam readiness hero card ───────────────────────────────────────────────────

def render_exam_readiness_hero(overall: float = 0.0, days_left: int = 0,
                                streak: int = 0, weak_count: int = 0,
                                subject: str = "CS") -> None:
    pct = int(overall)
    r_color = "#39FF14" if pct >= 75 else "#D4A24C" if pct >= 50 else "#FF4757"
    d_color = "#FF4757" if days_left <= 7 else "#FFB830" if days_left <= 14 else "#F0F4F8"
    days_pct = max(0, min(100, 100 - (days_left / 90 * 100)))
    arc_len = overall * 2.2
    streak_glow = (
        "box-shadow:0 0 0 1px rgba(212,162,76,0.4),0 0 16px rgba(212,162,76,0.2);"
        if streak >= 7 else ""
    )
    cols = st.columns(3)
    with cols[0]:
        st.markdown(
            f'<div class="omni-stat fade-in stagger-1" '
            f'style="position:relative;overflow:hidden;animation-delay:0ms;">'
            f'<svg style="position:absolute;top:8px;right:8px;opacity:0.08;" '
            f'width="80" height="80" viewBox="0 0 80 80">'
            f'<circle cx="40" cy="40" r="35" fill="none" stroke="{r_color}" '
            f'stroke-width="8" stroke-dasharray="{arc_len:.0f} 220" '
            f'transform="rotate(-90 40 40)"/></svg>'
            f'<div class="omni-stat-num" style="color:{r_color};">{pct:.0f}%</div>'
            f'<div class="omni-stat-label">OVERALL READINESS</div>'
            f'<div style="font-family:var(--font-mono);font-size:0.58rem;'
            f'color:var(--color-text-dim);margin-top:4px;">Target: 75%+ for A grade</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            f'<div class="omni-stat fade-in stagger-2" style="animation-delay:100ms;">'
            f'<div class="omni-stat-num" style="color:{d_color};">{days_left}</div>'
            f'<div class="omni-stat-label">DAYS TO EXAM</div>'
            f'<div style="font-family:var(--font-sans);font-size:0.72rem;'
            f'color:var(--color-text-secondary);margin-top:4px;">{subject}</div>'
            f'<div style="margin-top:8px;height:3px;background:rgba(0,180,166,0.08);border-radius:2px;">'
            f'<div style="height:100%;width:{days_pct:.0f}%;background:{d_color};'
            f'border-radius:2px;opacity:0.6;"></div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            f'<div class="omni-stat fade-in stagger-3" '
            f'style="animation-delay:200ms;{streak_glow}">'
            f'<div class="omni-stat-num" style="color:#D4A24C;">🔥 {streak}</div>'
            f'<div class="omni-stat-label">DAY STREAK</div>'
            f'<div style="font-family:var(--font-sans);font-size:0.72rem;'
            f'color:var(--color-text-secondary);margin-top:4px;">'
            f'{weak_count} weak areas flagged</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Chapter mastery bars ───────────────────────────────────────────────────────

def render_chapter_bars(chapter_scores: list) -> None:
    if not chapter_scores:
        return
    st.markdown(
        '<div style="font-family:var(--font-mono);font-size:9px;color:var(--color-text-dim);'
        'letter-spacing:0.18em;text-transform:uppercase;margin-bottom:10px;">'
        'Chapter Mastery</div>',
        unsafe_allow_html=True,
    )
    for i, ch in enumerate(chapter_scores[:8]):
        name  = ch.get("chapter_name", ch.get("name", "Unknown"))
        score = float(ch.get("score", 0))
        if score >= 75:
            color = "#39FF14"
            glow  = "rgba(57,255,20,0.4)"
            chip  = '<span class="omni-chip omni-chip-neon" style="font-size:0.6rem;padding:2px 7px;">&#10003; Strong</span>'
        elif score >= 40:
            color = "#FFB830"
            glow  = "rgba(255,184,48,0.4)"
            chip  = '<span class="omni-chip omni-chip-amber" style="font-size:0.6rem;padding:2px 7px;">&#9888; Needs Work</span>'
        else:
            color = "#FF4757"
            glow  = "rgba(255,71,87,0.4)"
            chip  = '<span class="omni-chip omni-chip-red" style="font-size:0.6rem;padding:2px 7px;">&#10007; CRITICAL</span>'
        st.markdown(
            f'<div class="slide-in" style="animation-delay:{i * 80}ms;'
            f'opacity:0;animation-fill-mode:both;margin-bottom:10px;">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
            f'<div style="font-family:var(--font-sans);font-size:0.83rem;'
            f'color:var(--color-text-secondary);max-width:240px;white-space:nowrap;'
            f'overflow:hidden;text-overflow:ellipsis;flex:1;">{name}</div>'
            f'{chip}'
            f'<div style="font-family:var(--font-mono);font-size:0.75rem;color:{color};'
            f'flex-shrink:0;min-width:32px;text-align:right;">{score:.0f}%</div>'
            f'</div>'
            f'<div style="height:4px;background:rgba(0,180,166,0.08);border-radius:3px;overflow:hidden;">'
            f'<div style="height:100%;width:{min(score, 100):.0f}%;background:{color};'
            f'border-radius:3px;box-shadow:0 0 6px {glow};'
            f'animation:bar-fill 0.8s ease forwards;animation-delay:{i * 80}ms;"></div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Impact counter ─────────────────────────────────────────────────────────────

def render_impact_counter(streak: int = 0,
                           questions: int = 0,
                           fixed: int = 0) -> None:
    """3-stat impact counter row — streak / questions / weaknesses fixed."""
    stats = [
        {"num": f"🔥 {streak}" if streak else "0", "color": "#D4A24C",
         "label": "DAY STREAK",       "sub": "consecutive days",  "delay": "0ms"},
        {"num": str(questions),                        "color": "#00B4A6",
         "label": "QUESTIONS DONE",   "sub": "across all topics", "delay": "100ms"},
        {"num": str(fixed),                            "color": "#39FF14",
         "label": "WEAKNESSES FIXED", "sub": "concepts mastered", "delay": "200ms"},
    ]
    cols = st.columns(3)
    for col, s in zip(cols, stats):
        with col:
            st.markdown(
                f'<div class="omni-stat fade-in" '
                f'style="animation-delay:{s["delay"]};opacity:0;animation-fill-mode:both;">'
                f'<div class="omni-stat-num" style="color:{s["color"]};">{s["num"]}</div>'
                f'<div class="omni-stat-label">{s["label"]}</div>'
                f'<div style="font-family:var(--font-sans);font-size:0.7rem;'
                f'color:var(--color-text-dim);margin-top:3px;">{s["sub"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Gemma badges ───────────────────────────────────────────────────────────────

def render_gemma_badges() -> None:
    """Two-row chip layout: teal model features + gold prize qualifications."""
    st.markdown("""
    <div style="margin:10px 0 14px;">
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;">
        <span class="omni-chip omni-chip-teal">⬡ Gemma 4 E4B · 4.5B params</span>
        <span class="omni-chip omni-chip-teal">⬡ 128K Context</span>
        <span class="omni-chip omni-chip-teal">⬡ Native Function Calling</span>
        <span class="omni-chip omni-chip-teal">⬡ Vision Input</span>
        <span class="omni-chip omni-chip-teal">⬡ Thinking Mode</span>
        <span class="omni-chip omni-chip-teal">⬡ 140+ Languages</span>
      </div>
      <div style="height:1px;background:rgba(0,180,166,0.08);margin:6px 0;"></div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;">
        <span class="omni-chip omni-chip-gold">🏅 Unsloth QLoRA Fine-Tuned</span>
        <span class="omni-chip omni-chip-gold">🏅 Ollama Offline Inference</span>
        <span class="omni-chip omni-chip-gold">🏅 Apache 2.0 License</span>
        <span class="omni-chip omni-chip-gold">🏅 Sri Lanka A/L Curriculum</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── System status ──────────────────────────────────────────────────────────────

def render_system_status(ollama_ok: bool = True) -> None:
    """Compact system status panel — 5 service rows with coloured dots."""
    _dot_neon = "background:#39FF14;box-shadow:0 0 6px #39FF14;"
    _dot_red  = "background:#FF4757;"
    _dot_teal = "background:#00B4A6;"
    _dot_gold = "background:#D4A24C;"
    rows = [
        ("Gemma 4 E4B",   _dot_neon if ollama_ok else _dot_red,  "Local inference"),
        ("Ollama :11434",  _dot_neon if ollama_ok else _dot_red,  "Model server"),
        ("ChromaDB",       _dot_teal,                             "Vector store"),
        ("SQLite",         _dot_teal,                             "Local database"),
        ("Internet",       _dot_gold,                             "&#128274; Not required"),
    ]
    rows_html = "".join(
        f'<div style="display:flex;align-items:center;gap:7px;margin:4px 0;">'
        f'<span style="width:6px;height:6px;border-radius:50%;flex-shrink:0;display:inline-block;{dot}"></span>'
        f'<span style="font-family:var(--font-sans);font-size:0.78rem;color:var(--color-text-secondary);flex:1;">{name}</span>'
        f'<span style="font-family:var(--font-mono);font-size:0.6rem;color:var(--color-text-dim);">{note}</span>'
        f'</div>'
        for name, dot, note in rows
    )
    st.markdown(
        f'<div style="background:rgba(0,180,166,0.04);border:1px solid rgba(0,180,166,0.1);'
        f'border-radius:10px;padding:12px 14px;margin:6px 0;">'
        f'<div style="font-family:var(--font-mono);font-size:0.58rem;color:var(--color-text-dim);'
        f'letter-spacing:0.2em;text-transform:uppercase;margin-bottom:8px;">⬡ SYSTEM</div>'
        f'{rows_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Urgency countdown ──────────────────────────────────────────────────────────

def render_urgency_countdown(days_left: int, subject: str) -> None:
    """Urgency-aware exam countdown banner for sidebar."""
    if days_left <= 0:
        st.sidebar.error("🚨 Exam date has passed!")
        return
    if days_left <= 3:
        st.sidebar.markdown(
            f'<div style="background:#EF4444;color:white;padding:8px 12px;'
            f'border-radius:8px;font-weight:bold;text-align:center;'
            f'font-family:\'Space Grotesk\',sans-serif;font-size:0.8rem;">'
            f'🚨 CRITICAL — {days_left} DAYS LEFT</div>',
            unsafe_allow_html=True
        )
    elif days_left <= 7:
        st.sidebar.warning(f"⚠️ {days_left} days to {subject} exam")
    elif days_left <= 14:
        st.sidebar.info(f"📅 {days_left} days to exam")
    else:
        st.sidebar.success(f"📅 {days_left} days to exam")


# ── Daily focus prompt ────────────────────────────────────────────────────────

def render_today_focus(topic: str = "", days_left: int = 0) -> None:
    """Urgency-aware daily focus card."""
    if not topic:
        return
    if days_left <= 7:
        urgency_color = "#FF4757"
        icon = "🔥"
        urgency_text = f"{days_left} days left — this must be done today"
    elif days_left <= 14:
        urgency_color = "#FFB830"
        icon = "📌"
        urgency_text = f"{days_left} days to exam"
    else:
        urgency_color = "#00B4A6"
        icon = "📌"
        urgency_text = f"{days_left} days to exam"
    st.markdown(
        f'<div class="omni-card slide-in" style="border-color:{urgency_color}33;margin:8px 0;">'
        f'<div style="font-family:var(--font-mono);font-size:0.58rem;color:var(--color-text-dim);'
        f'letter-spacing:0.18em;text-transform:uppercase;margin-bottom:6px;">'
        f'{icon} TODAY\'S FOCUS</div>'
        f'<div style="font-family:var(--font-sans);font-size:1.05rem;font-weight:600;'
        f'color:#F0F4F8;margin-bottom:8px;">{topic}</div>'
        f'<div style="font-family:var(--font-mono);font-size:0.6rem;color:{urgency_color};'
        f'letter-spacing:0.06em;">{urgency_text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Metric card ────────────────────────────────────────────────────────────────

def render_metric_card(title: str, value: str, subtitle: str = "", color: str = "#0F172A"):
    """Render a single metric card."""
    st.markdown(f"""
    <div class="omnischolar-card" style="text-align: center;">
        <div style="font-size: 0.75rem; color: {COLORS['muted']}; font-weight: 500;
                    text-transform: uppercase; letter-spacing: 0.05em;">
            {title}
        </div>
        <div style="font-size: 2.5rem; font-weight: 700; color: {color}; margin: 8px 0;">
            {value}
        </div>
        <div style="font-size: 0.8rem; color: {COLORS['muted']};">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Offline seal ───────────────────────────────────────────────────────────────

def render_offline_seal() -> None:
    """
    Fixed-position gold lock seal — always visible in top-right corner across all screens.
    Conic-gradient gold ring around a black circle containing 🔒.
    Uses seal-breathe animation. Tooltip: "Running 100% offline · Zero cloud · Fully private"
    """
    st.markdown("""
    <div title="Running 100% offline · Zero cloud · Fully private"
         style="position:fixed;top:16px;right:20px;z-index:9999;
                width:52px;height:52px;border-radius:50%;
                background:conic-gradient(
                  #D4A24C 0deg, #FFD080 60deg, #D4A24C 120deg,
                  #A07830 180deg, #D4A24C 240deg, #FFD080 300deg, #D4A24C 360deg
                );
                display:flex;align-items:center;justify-content:center;
                cursor:default;
                animation:seal-breathe 3s ease-in-out infinite;">
      <div style="width:40px;height:40px;border-radius:50%;
                  background:#060A14;
                  display:flex;align-items:center;justify-content:center;
                  font-size:1.1rem;line-height:1;">
        🔒
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Offline confirmed banner ──────────────────────────────────────────────────

def render_offline_confirmed_toast() -> None:
    """
    Dramatic offline confirmation banner for demo video moment (timestamp 2:22).
    Shown when st.session_state['wifi_demo_off'] is True.
    """
    st.markdown("""
    <div class="fade-in" style="
      background:linear-gradient(135deg,
        rgba(57,255,20,0.08),
        rgba(0,180,166,0.06));
      border:1px solid rgba(57,255,20,0.35);
      border-radius:12px;
      padding:14px 20px;
      margin:12px 0;">
      <div style="display:flex;align-items:center;gap:12px;">
        <span style="font-size:1.4rem;">&#128274;</span>
        <div style="flex:1;">
          <div class="omni-chip omni-chip-neon"
               style="animation:pulse-neon 1s ease-in-out infinite;
                      margin-bottom:6px;">
            &#9679; STILL RUNNING &middot; ZERO INTERNET
          </div>
          <div style="
            font-family:'DM Sans',sans-serif;
            font-size:0.82rem; color:#8899AA;
            line-height:1.5;">
            OmniScholar is 100% offline. No WiFi required.
            Gemma 4 E4B runs entirely on this laptop.
            Your data never leaves this device.
          </div>
        </div>
        <div style="
          font-family:'JetBrains Mono',monospace;
          font-size:0.6rem; color:#2A4A2A;
          text-align:right; flex-shrink:0;
          line-height:1.8;">
          Local inference<br>
          Zero cloud<br>
          Apache 2.0
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
