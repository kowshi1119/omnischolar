"""
ui_components.py — OmniScholar UI primitives

Dark Academic Arcade theme: #060A14 navy, #00D4FF cyan, #FFB800 amber,
Space Grotesk / JetBrains Mono fonts.
"""

import streamlit as st

# ── Colour palette ─────────────────────────────────────────────────────────────
COLORS = {
    "primary":    "#00D4FF",   # cyan — main brand
    "amber":      "#FFB800",   # amber — accent / exam countdown
    "green":      "#00C850",   # green — success / strong chapters
    "red":        "#EF4444",   # red   — critical / weak areas
    "muted":      "#2A4060",   # slate — muted text
    "text":       "#6A8098",   # body text
    "card":       "#080D1A",   # card backgrounds
    "bg":         "#060A14",   # page background
    "section":    "#0A1020",   # section background
    "border":     "rgba(0,212,255,0.12)",  # subtle border
    "mono":       "JetBrains Mono",        # monospace font
    "sans":       "Space Grotesk",         # sans font
}

# ── Premium CSS injection ──────────────────────────────────────────────────────

def inject_premium_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

    /* ══════════════════════════════════════
       BASE
    ══════════════════════════════════════ */
    html, body, [data-testid="stAppViewContainer"] {
        background: #060A14 !important;
        color: #C8DCF0 !important;
        font-family: 'Space Grotesk', sans-serif !important;
    }
    [data-testid="stMain"] { background: transparent !important; }

    /* Grid background */
    [data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed; inset: 0; z-index: 0;
        background-image:
            linear-gradient(rgba(0,212,255,0.02) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,212,255,0.02) 1px, transparent 1px);
        background-size: 44px 44px;
        pointer-events: none;
    }

    /* ══════════════════════════════════════
       SIDEBAR
    ══════════════════════════════════════ */
    [data-testid="stSidebar"] {
        background: #080D1A !important;
        border-right: 1px solid rgba(0,212,255,0.08) !important;
    }

    /* ══════════════════════════════════════
       TYPOGRAPHY
    ══════════════════════════════════════ */
    h1, h2, h3 {
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.01em !important;
    }
    h1 { color: #E8F4FF !important; font-weight: 700 !important; font-size: 1.6rem !important; }
    h2 { color: #C8DCF0 !important; font-weight: 600 !important; font-size: 1.2rem !important; }
    h3 { color: #A0B8D0 !important; font-weight: 500 !important; font-size: 1rem !important; }
    p, li, div { color: #90A8C0 !important; font-size: 0.875rem !important; }
    strong, b  { color: #C8DCF0 !important; font-weight: 600 !important; }
    code, pre  { font-family: 'JetBrains Mono', monospace !important; }

    /* ══════════════════════════════════════
       BUTTONS
    ══════════════════════════════════════ */
    .stButton > button {
        background: rgba(10, 25, 50, 0.9) !important;
        color: #00D4FF !important;
        border: 1px solid rgba(0,212,255,0.3) !important;
        border-radius: 6px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        padding: 7px 16px !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button:hover {
        background: rgba(0,212,255,0.1) !important;
        border-color: #00D4FF !important;
        color: #FFFFFF !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(0,212,255,0.15) !important;
    }
    .stButton > button[kind="primary"] {
        background: rgba(0,80,120,0.8) !important;
        border-color: rgba(0,212,255,0.5) !important;
        color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: rgba(0,100,150,0.9) !important;
        box-shadow: 0 4px 20px rgba(0,212,255,0.25) !important;
    }

    /* ══════════════════════════════════════
       INPUTS
    ══════════════════════════════════════ */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(8, 16, 32, 0.95) !important;
        border: 1px solid rgba(0,212,255,0.2) !important;
        border-radius: 6px !important;
        color: #D0E4F8 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 0.88rem !important;
        padding: 9px 12px !important;
        caret-color: #00D4FF !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: rgba(0,212,255,0.5) !important;
        box-shadow: 0 0 0 3px rgba(0,212,255,0.08) !important;
        background: rgba(0,20,45,0.98) !important;
    }
    .stTextInput > label, .stTextArea > label {
        color: #3A6080 !important;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        font-family: 'Space Grotesk', sans-serif !important;
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
        border: 1px solid rgba(0,212,255,0.2) !important;
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
        border: 1px solid rgba(0,212,255,0.15) !important;
    }
    [data-baseweb="select"] li {
        color: #A0B8D0 !important;
        font-size: 0.85rem !important;
    }
    [data-baseweb="select"] li:hover {
        background: rgba(0,212,255,0.08) !important;
        color: #E8F4FF !important;
    }

    /* ══════════════════════════════════════
       RADIO BUTTONS
    ══════════════════════════════════════ */
    .stRadio label {
        color: #6A8098 !important;
        font-size: 0.85rem !important;
        font-family: 'Space Grotesk', sans-serif !important;
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
        border: 1px solid rgba(0,212,255,0.1) !important;
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
        color: #00D4FF !important;
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
        background: rgba(0,212,255,0.05) !important;
        border: 1px solid rgba(0,212,255,0.15) !important;
        border-left: 3px solid #00D4FF !important;
        border-radius: 0 6px 6px 0 !important;
    }
    .stInfo p { color: #6090B0 !important; }

    /* ══════════════════════════════════════
       EXPANDERS
    ══════════════════════════════════════ */
    .streamlit-expanderHeader {
        background: rgba(8,16,32,0.8) !important;
        border: 1px solid rgba(0,212,255,0.12) !important;
        border-radius: 6px !important;
        color: #6090B0 !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: 0.04em !important;
        padding: 10px 14px !important;
    }
    .streamlit-expanderHeader:hover {
        border-color: rgba(0,212,255,0.25) !important;
        color: #A0C0D8 !important;
    }
    .streamlit-expanderContent {
        background: rgba(6,10,20,0.6) !important;
        border: 1px solid rgba(0,212,255,0.08) !important;
        border-top: none !important;
        border-radius: 0 0 6px 6px !important;
        padding: 14px !important;
    }

    /* ══════════════════════════════════════
       PROGRESS
    ══════════════════════════════════════ */
    .stProgress > div > div {
        background: rgba(0,212,255,0.06) !important;
        border-radius: 3px !important;
    }
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #004A70, #00D4FF) !important;
        border-radius: 3px !important;
        transition: width 0.5s ease !important;
    }

    /* ══════════════════════════════════════
       TABS
    ══════════════════════════════════════ */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(8,16,32,0.8) !important;
        border-bottom: 1px solid rgba(0,212,255,0.1) !important;
        border-radius: 6px 6px 0 0 !important;
        gap: 2px !important;
        padding: 4px 4px 0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #3A5070 !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.06em !important;
        font-family: 'Space Grotesk', sans-serif !important;
        text-transform: uppercase !important;
    }
    .stTabs [aria-selected="true"] {
        color: #00D4FF !important;
        border-bottom: 2px solid #00D4FF !important;
    }

    /* ══════════════════════════════════════
       SCROLLBAR
    ══════════════════════════════════════ */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: #060A14; }
    ::-webkit-scrollbar-thumb {
        background: rgba(0,212,255,0.2);
        border-radius: 2px;
    }

    /* ══════════════════════════════════════
       DIVIDER
    ══════════════════════════════════════ */
    hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg,transparent,rgba(0,212,255,0.15),transparent) !important;
        margin: 16px 0 !important;
    }

    /* ══════════════════════════════════════
       DATE INPUT
    ══════════════════════════════════════ */
    .stDateInput > div > div > input {
        background: rgba(8,16,32,0.95) !important;
        border: 1px solid rgba(0,212,255,0.2) !important;
        color: #D0E4F8 !important;
        border-radius: 6px !important;
    }

    /* ══════════════════════════════════════
       BRAND CLASSES
    ══════════════════════════════════════ */
    .omni-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1rem;
        font-weight: 700;
        color: #00D4FF;
        letter-spacing: 0.2em;
        text-align: center;
        padding: 14px 0 16px;
        border-bottom: 1px solid rgba(0,212,255,0.1);
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
        background: rgba(8,16,32,0.9);
        border: 1px solid rgba(0,212,255,0.12);
        border-radius: 8px;
        padding: 14px 18px;
        margin: 6px 0;
        position: relative;
        overflow: hidden;
        transition: border-color 0.15s, background 0.15s;
        cursor: pointer;
    }
    .omni-mode-card:hover {
        border-color: rgba(0,212,255,0.3);
        background: rgba(0,30,60,0.95);
    }
    .omni-mode-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg,transparent,rgba(0,212,255,0.3),transparent);
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
        background: rgba(8,16,32,0.9);
        border: 1px solid rgba(0,212,255,0.08);
        border-radius: 6px;
        padding: 10px 12px;
        text-align: center;
    }
    .omni-stat-num {
        font-family: 'JetBrains Mono', monospace;
        font-size: 20px;
        font-weight: 600;
        line-height: 1;
    }
    .omni-stat-label {
        font-size: 8px;
        color: #1E3A5A;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-top: 4px;
        font-family: 'JetBrains Mono', monospace;
    }

    /* ══════════════════════════════════════
       MULTISELECT TAGS
    ══════════════════════════════════════ */
    .stMultiSelect > div > div {
        background: rgba(8,16,32,0.9) !important;
        border: 1px solid rgba(0,212,255,0.2) !important;
        border-radius: 6px !important;
    }
    .stMultiSelect [data-baseweb="tag"] {
        background: rgba(0,212,255,0.1) !important;
        color: #00D4FF !important;
        border-radius: 4px !important;
    }

    /* ══════════════════════════════════════
       SLIDER
    ══════════════════════════════════════ */
    .stSlider > div > div > div {
        background: rgba(0,212,255,0.1) !important;
    }
    .stSlider > div > div > div > div {
        background: linear-gradient(90deg, #003A58, #00D4FF) !important;
    }

    /* ══════════════════════════════════════
       FILE UPLOADER
    ══════════════════════════════════════ */
    [data-testid="stFileUploader"] {
        background: rgba(8,16,32,0.9) !important;
        border: 1px dashed rgba(0,212,255,0.25) !important;
        border-radius: 6px !important;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: rgba(0,212,255,0.5) !important;
        background: rgba(0,20,45,0.95) !important;
    }

    /* ══════════════════════════════════════
       SPINNER
    ══════════════════════════════════════ */
    .stSpinner > div {
        border-top-color: #00D4FF !important;
    }

    /* ══════════════════════════════════════
       CODE BLOCKS
    ══════════════════════════════════════ */
    .stCodeBlock {
        background: rgba(6,10,20,0.95) !important;
        border: 1px solid rgba(0,212,255,0.12) !important;
        border-radius: 6px !important;
    }
    code {
        color: #00D4FF !important;
        background: rgba(0,212,255,0.06) !important;
        padding: 1px 5px !important;
        border-radius: 3px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.82rem !important;
    }

    /* ══════════════════════════════════════
       DATAFRAMES
    ══════════════════════════════════════ */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(0,212,255,0.1) !important;
        border-radius: 6px !important;
        overflow: hidden !important;
    }

    /* ══════════════════════════════════════
       ACTIVE MODE HIGHLIGHT
    ══════════════════════════════════════ */
    [data-testid="stSidebar"] .stRadio [aria-checked="true"] + div {
        color: #00D4FF !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] .stRadio div[data-testid] {
        padding: 2px 0 !important;
    }

    /* ══════════════════════════════════════
       PAGE FADE-IN
    ══════════════════════════════════════ */
    [data-testid="stMain"] > div {
        animation: omni-fadein 0.25s ease;
    }
    @keyframes omni-fadein {
        from { opacity: 0; transform: translateY(6px); }
        to   { opacity: 1; transform: translateY(0); }
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
        color: #00D4FF !important;
    }

    </style>
    """, unsafe_allow_html=True)


# ── RAG grounding indicator ────────────────────────────────────────────────────

def render_grounding_indicator(sources: list | None = None,
                                coverage: float | None = None,
                                level: str | None = None) -> None:
    """
    3-band confidence indicator.
    level: 'grounded' | 'curriculum' | 'uncertain'  (overrides coverage calculation)
    """
    if sources is None:
        sources = []
    n = len(sources)

    if level == "grounded":
        color, icon, label, sub = "#00C850", "🟢", "From your notes", "Grounded in your uploaded materials"
    elif level == "uncertain":
        color, icon, label, sub = "#EF4444", "🔴", "Uncertain", "Check textbook — not confirmed in your notes"
    elif level == "curriculum":
        color, icon, label, sub = "#FFB800", "🟡", "Curriculum knowledge", "Verify key facts with your textbook"
    else:
        # Legacy path: infer from coverage / source count
        if coverage is not None:
            pct = coverage * 100
        else:
            pct = min(100, n * 25)

        if pct >= 60 or n >= 3:
            color, icon, label, sub = "#00C850", "🟢", "From your notes", "Grounded in your uploaded materials"
        elif pct >= 20 or n >= 1:
            color, icon, label, sub = "#FFB800", "🟡", "Curriculum knowledge", "Verify key facts with your textbook"
        else:
            color, icon, label, sub = "#4A6080", "○", "General knowledge", "Upload your textbook to improve accuracy"

    source_text = ""
    if sources:
        names = ", ".join(str(s)[:35] for s in sources[:2])
        if n > 2:
            names += f" +{n-2} more"
        source_text = (
            f'<span style="color:#1E3A5A;font-size:0.62rem;margin-left:6px;">'
            f'· {names}</span>'
        )

    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:5px;'
        f'padding:3px 10px;background:{color}0D;'
        f'border:1px solid {color}22;border-radius:20px;margin:4px 0;">'
        f'<span style="color:{color};font-size:0.7rem;">{icon}</span>'
        f'<span style="color:{color};font-size:0.68rem;'
        f'font-family:\'Space Grotesk\',sans-serif;font-weight:600;">{label}</span>'
        f'<span style="color:#2A4060;font-size:0.62rem;">{sub}</span>'
        f'{source_text}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Thinking state indicator ───────────────────────────────────────────────────

def render_thinking_state(message: str = "Gemma 4 is thinking...") -> None:
    """Animated thinking indicator while model generates response."""
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;
                padding:10px 14px;
                background:rgba(6,10,20,0.8);
                border:1px solid rgba(0,212,255,0.12);
                border-radius:6px;margin:6px 0;">
      <div style="display:flex;gap:3px;align-items:center;">
        <span style="width:5px;height:5px;background:#00D4FF;border-radius:50%;
                     display:inline-block;animation:omni-pulse 1.2s ease-in-out infinite;
                     animation-delay:0s;"></span>
        <span style="width:5px;height:5px;background:#00D4FF;border-radius:50%;
                     display:inline-block;animation:omni-pulse 1.2s ease-in-out infinite;
                     animation-delay:0.2s;"></span>
        <span style="width:5px;height:5px;background:#00D4FF;border-radius:50%;
                     display:inline-block;animation:omni-pulse 1.2s ease-in-out infinite;
                     animation-delay:0.4s;"></span>
      </div>
      <span style="color:#4A7090;font-size:0.8rem;
                   font-family:'Space Grotesk',sans-serif;">{message}</span>
      <span style="color:#1A3050;font-size:0.6rem;
                   font-family:'JetBrains Mono',monospace;
                   letter-spacing:0.1em;margin-left:auto;">⬡ GEMMA 4</span>
    </div>
    <style>
      @keyframes omni-pulse {{
        0%,80%,100% {{ opacity:0.2;transform:scale(0.8); }}
        40%          {{ opacity:1.0;transform:scale(1.1); }}
      }}
    </style>
    """, unsafe_allow_html=True)


# ── Welcome banner ─────────────────────────────────────────────────────────────

def render_welcome_banner(name: str = "Kowshi") -> None:
    """First-launch story banner."""
    st.markdown(f"""
    <div style="text-align:center;padding:28px 16px;">
      <div style="font-family:'Space Grotesk',sans-serif;font-size:2rem;
                  font-weight:700;color:#00D4FF;letter-spacing:0.15em;
                  margin-bottom:6px;">⬡ OMNISCHOLAR</div>
      <div style="color:#1A3050;font-size:0.6rem;letter-spacing:0.25em;
                  text-transform:uppercase;margin-bottom:24px;
                  font-family:'JetBrains Mono',monospace;">
        OFFLINE · MULTILINGUAL · BUILT BY A STUDENT
      </div>
      <div style="background:rgba(6,10,20,0.8);
                  border:1px solid rgba(0,212,255,0.15);border-radius:10px;
                  padding:22px 26px;max-width:560px;margin:0 auto 24px;
                  text-align:left;position:relative;overflow:hidden;">
        <div style="position:absolute;top:0;left:0;right:0;height:1px;
                    background:linear-gradient(90deg,transparent,rgba(0,212,255,0.3),transparent);">
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:8px;
                    color:#1E3A5A;letter-spacing:0.18em;margin-bottom:10px;">
          WHY THIS EXISTS
        </div>
        <div style="font-size:0.9rem;line-height:1.7;color:#6A8098;">
          I'm {name} — a Computer Science undergraduate in Sri Lanka.
          During exam season I had no tutor, unreliable internet, and
          textbooks in three languages. I built OmniScholar so no
          student has to study alone again.
        </div>
        <div style="margin-top:12px;font-size:0.75rem;color:#1E3A5A;
                    border-top:1px solid rgba(0,212,255,0.08);padding-top:10px;
                    font-family:'JetBrains Mono',monospace;letter-spacing:0.06em;">
          ✓ 100% offline &nbsp;·&nbsp; ✓ Gemma 4 &nbsp;·&nbsp;
          ✓ Zero cloud &nbsp;·&nbsp; ✓ Free forever
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Exam readiness hero card ───────────────────────────────────────────────────

def render_exam_readiness_hero(overall: float = 0.0, days_left: int = 0,
                                streak: int = 0, weak_count: int = 0,
                                subject: str = "CS") -> None:
    pct = int(overall)
    color = "#00C850" if pct >= 75 else "#00D4FF" if pct >= 50 else "#EF4444"
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(0,212,255,0.06),rgba(0,50,90,0.04));
                border:1px solid rgba(0,212,255,0.18);border-radius:10px;
                padding:18px 22px;margin-bottom:14px;position:relative;overflow:hidden;">
      <div style="position:absolute;top:0;left:0;right:0;height:2px;
                  background:linear-gradient(90deg,transparent,{color},transparent);"></div>
      <div style="display:flex;align-items:center;justify-content:space-between;">
        <div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:9px;
                      color:#1E3A5A;letter-spacing:0.2em;margin-bottom:4px;">
            EXAM READINESS · {subject.upper()}
          </div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:40px;
                      font-weight:600;color:{color};line-height:1;">{pct}%</div>
          <div style="font-size:9px;color:#1E3A5A;letter-spacing:0.12em;margin-top:4px;">
            {streak} DAY STREAK {'🔥' if streak >= 3 else ''} &nbsp;·&nbsp;
            {weak_count} WEAK AREAS
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-family:'JetBrains Mono',monospace;font-size:32px;
                      font-weight:600;color:#FFB800;line-height:1;">{days_left}</div>
          <div style="font-size:9px;color:#3A3010;letter-spacing:0.12em;margin-top:4px;">
            DAYS TO EXAM
          </div>
        </div>
      </div>
      <div style="margin-top:12px;height:3px;background:rgba(0,212,255,0.08);
                  border-radius:2px;">
        <div style="height:100%;width:{min(pct,100)}%;
                    background:linear-gradient(90deg,#004060,{color});
                    border-radius:2px;transition:width 0.5s ease;"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Chapter mastery bars ───────────────────────────────────────────────────────

def render_chapter_bars(chapter_scores: list) -> None:
    if not chapter_scores:
        return
    st.markdown("""
    <div style="font-family:'JetBrains Mono',monospace;font-size:9px;
                color:#1E3A5A;letter-spacing:0.18em;margin-bottom:10px;">
        CHAPTER MASTERY
    </div>
    """, unsafe_allow_html=True)
    for ch in chapter_scores[:6]:
        name  = ch.get("chapter_name", ch.get("name", "Unknown"))[:22]
        score = float(ch.get("score", 0))
        color = "#00C850" if score >= 70 else "#00D4FF" if score >= 40 else "#EF4444"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:7px;">
          <div style="width:130px;font-size:10px;color:#4A6080;flex-shrink:0;
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
            {name}
          </div>
          <div style="flex:1;height:3px;background:rgba(0,212,255,0.07);
                      border-radius:2px;">
            <div style="height:100%;width:{min(score,100):.0f}%;
                        background:{color};border-radius:2px;
                        transition:width 0.5s ease;"></div>
          </div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:9px;
                      color:{color};width:28px;text-align:right;flex-shrink:0;">
            {score:.0f}%
          </div>
        </div>
        """, unsafe_allow_html=True)


# ── Impact counter ─────────────────────────────────────────────────────────────

def render_impact_counter(streak: int = 0,
                           questions: int = 0,
                           fixed: int = 0) -> None:
    """3-stat impact counter row — streak / questions / weaknesses fixed."""
    stats = [
        {"num": streak,     "label": "DAY STREAK",      "color": "#00D4FF"},
        {"num": questions,  "label": "QUESTIONS DONE",  "color": "#FFB800"},
        {"num": fixed,      "label": "WEAKNESSES FIXED","color": "#00C850"},
    ]
    cols = st.columns(3)
    for col, s in zip(cols, stats):
        with col:
            st.markdown(f"""
            <div class="omni-stat">
              <div class="omni-stat-num" style="color:{s['color']};">{s['num']}</div>
              <div class="omni-stat-label">{s['label']}</div>
            </div>
            """, unsafe_allow_html=True)


# ── Gemma badges ───────────────────────────────────────────────────────────────

def render_gemma_badges() -> None:
    """Gemma 4 feature pill badges shown on home dashboard."""
    st.markdown("""
    <div style="display:flex;gap:5px;flex-wrap:wrap;margin:10px 0 14px;">
      <span class="omni-tag omni-tag-cyan">⬡ Function Calling</span>
      <span class="omni-tag omni-tag-cyan">⬡ Vision Input</span>
      <span class="omni-tag omni-tag-cyan">⬡ Thinking Mode</span>
      <span class="omni-tag omni-tag-cyan">⬡ 140+ Languages</span>
      <span class="omni-tag omni-tag-cyan">⬡ Apache 2.0</span>
      <span class="omni-tag omni-tag-amber">🔥 Unsloth Fine-Tuned</span>
      <span class="omni-tag omni-tag-amber">🔥 Ollama Offline</span>
    </div>
    """, unsafe_allow_html=True)


# ── System status ──────────────────────────────────────────────────────────────

def render_system_status(ollama_ok: bool = True) -> None:
    """Sidebar system status panel showing all services."""
    rows = [
        ("Gemma 4 E4B",    ollama_ok, "Local inference"),
        ("Ollama :11434",  ollama_ok, "Model server"),
        ("ChromaDB",       True,      "Vector store"),
        ("SQLite",         True,      "Local database"),
        ("Internet",       False,     "Not required"),
    ]
    html = """
    <div style="margin:10px 8px;background:rgba(0,200,80,0.04);
                border:1px solid rgba(0,200,80,0.12);border-radius:6px;
                padding:10px 12px;">
      <div style="font-family:'JetBrains Mono',monospace;font-size:8px;
                  color:#1A4030;letter-spacing:0.2em;margin-bottom:8px;">
        ⬡ SYSTEM STATUS
      </div>
    """
    for name, ok, note in rows:
        dot_color = "#00C850" if ok else "#EF4444"
        text_color = "#2A5040" if ok else "#5A2020"
        html += f"""
      <div style="display:flex;align-items:center;gap:6px;
                  margin:3px 0;font-size:10px;">
        <span style="width:5px;height:5px;border-radius:50%;
                     background:{dot_color};flex-shrink:0;display:inline-block;">
        </span>
        <span style="color:{text_color};flex:1;">{name}</span>
        <span style="color:#1A3028;font-size:8px;">{note}</span>
      </div>"""
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


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
    """Daily launch prompt showing today's study focus."""
    if not topic:
        return
    urgency = "🔥" if days_left <= 7 else "📌"
    st.markdown(f"""
    <div style="background:rgba(0,212,255,0.04);
                border:1px solid rgba(0,212,255,0.12);
                border-left:3px solid #00D4FF;
                border-radius:0 6px 6px 0;
                padding:10px 14px;margin:8px 0;">
      <span style="font-family:'JetBrains Mono',monospace;font-size:8px;
                   color:#1E3A5A;letter-spacing:0.15em;">{urgency} TODAY'S FOCUS · </span>
      <span style="font-size:0.85rem;color:#4A7090;font-family:'Space Grotesk',sans-serif;">
        {topic}
      </span>
      <span style="font-size:0.75rem;color:#1A3050;margin-left:8px;">
        · {days_left} days to exam
      </span>
    </div>
    """, unsafe_allow_html=True)


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

