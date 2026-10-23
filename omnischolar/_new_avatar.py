import html as _html

import streamlit as st

# ── Enhanced Avatar (3D-style emotional Dr. Omni) ────────────────────────────

def render_dr_omni_svg(emotion: str = "idle", size: int = 80) -> str:
    """Return an inline SVG string of Dr. Omni the owl mascot.
    Embed via st.markdown(..., unsafe_allow_html=True).
    """
    glasses_colors = {
        "idle":       "#00B4A6",
        "thinking":   "#39FF14",
        "happy":      "#D4A24C",
        "explaining": "#00B4A6",
        "warning":    "#FFB830",
        "excited":    "#39FF14",
        "recap":      "#D4A24C",
    }
    gc = glasses_colors.get(emotion, "#00B4A6")

    pulse = (
        '<animate attributeName="opacity" '
        'values="1;0.4;1" dur="1.2s" '
        'repeatCount="indefinite"/>'
        if emotion == "thinking" else ""
    )

    wing_l_y = "60" if emotion == "excited" else "65"
    wing_r_y = "60" if emotion == "excited" else "65"

    return f"""<svg width="{size}" height="{size}" viewBox="0 0 100 100"
     xmlns="http://www.w3.org/2000/svg"
     style="animation: omni-breathe 3s ease-in-out infinite;">
  <!-- Body -->
  <ellipse cx="50" cy="58" rx="28" ry="32"
    fill="#0D1B2A" stroke="#00B4A6" stroke-width="2"/>
  <!-- Left wing -->
  <ellipse cx="22" cy="{wing_l_y}" rx="10" ry="16"
    fill="#0A1628" stroke="#00B4A6" stroke-width="1.5"
    transform="rotate(-15 22 {wing_l_y})"/>
  <!-- Right wing -->
  <ellipse cx="78" cy="{wing_r_y}" rx="10" ry="16"
    fill="#0A1628" stroke="#00B4A6" stroke-width="1.5"
    transform="rotate(15 78 {wing_r_y})"/>
  <!-- Head -->
  <circle cx="50" cy="30" r="22"
    fill="#0D1B2A" stroke="#00B4A6" stroke-width="2"/>
  <!-- Left glasses -->
  <circle cx="40" cy="30" r="9"
    fill="rgba(0,180,166,0.08)"
    stroke="{gc}" stroke-width="2">{pulse}</circle>
  <!-- Right glasses -->
  <circle cx="60" cy="30" r="9"
    fill="rgba(0,180,166,0.08)"
    stroke="{gc}" stroke-width="2">{pulse}</circle>
  <!-- Bridge -->
  <line x1="49" y1="30" x2="51" y2="30"
    stroke="{gc}" stroke-width="1.5"/>
  <!-- Left pupil -->
  <circle cx="40" cy="30" r="4" fill="{gc}" opacity="0.8"/>
  <!-- Right pupil -->
  <circle cx="60" cy="30" r="4" fill="{gc}" opacity="0.8"/>
  <!-- Beak -->
  <polygon points="46,36 54,36 50,42"
    fill="#FFB830" opacity="0.9"/>
  <!-- Grad cap base -->
  <rect x="32" y="10" width="36" height="5" rx="2"
    fill="#D4A24C"/>
  <!-- Grad cap board -->
  <rect x="30" y="6" width="40" height="6" rx="1"
    fill="#D4A24C" transform="rotate(-5 50 9)"/>
  <!-- Tassel -->
  <line x1="68" y1="9" x2="72" y2="18"
    stroke="#D4A24C" stroke-width="1.5"/>
  <circle cx="72" cy="19" r="2" fill="#D4A24C"/>
  <!-- Feet -->
  <ellipse cx="42" cy="89" rx="6" ry="3"
    fill="#FFB830" opacity="0.7"/>
  <ellipse cx="58" cy="89" rx="6" ry="3"
    fill="#FFB830" opacity="0.7"/>
</svg>"""


def render_dr_omni_greeting_card(
    name: str,
    topic: str = "",
    days_left: int = 0,
    emotion: str = "idle",
) -> None:
    """Sticky greeting card in the sidebar with Dr. Omni SVG + audio controls."""
    owl_svg = render_dr_omni_svg(emotion=emotion, size=48)
    focus_text = topic if topic else "Set your study topic"
    days_text = (
        f"🔥 {days_left} days — final push!"
        if days_left <= 7 else
        f"📅 {days_left} days to exam"
    )

    html_parts = [
        '<div style="background:linear-gradient(135deg,#0A1420,#0D1B2A);'
        'border:1px solid rgba(0,180,166,0.2);border-radius:12px;'
        'padding:14px;margin-top:8px;">',
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">',
        owl_svg,
        '<div>',
        '<div style="font-family:\'DM Sans\',sans-serif;font-size:0.9rem;'
        'font-weight:600;color:#F0F4F8;">Hi ',
        _html.escape(str(name)),
        '! \U0001f44b</div>',
        '<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.6rem;'
        'color:#7A8FA3;margin-top:2px;">',
        days_text,
        '</div></div></div>',
        # Today's focus box
        '<div style="background:rgba(0,180,166,0.06);'
        'border-left:2px solid #00B4A6;border-radius:0 6px 6px 0;'
        'padding:7px 10px;margin-bottom:10px;">',
        '<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.55rem;'
        'color:#7A8FA3;letter-spacing:0.15em;text-transform:uppercase;'
        'margin-bottom:3px;">TODAY\'S FOCUS</div>',
        '<div style="font-family:\'DM Sans\',sans-serif;font-size:0.8rem;'
        'color:#F0F4F8;font-weight:500;">',
        _html.escape(str(focus_text)),
        '</div></div>',
        # Audio controls
        '<div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap;">',
        '<button onclick="return false;" style="background:rgba(0,180,166,0.1);'
        'border:1px solid rgba(0,180,166,0.3);border-radius:12px;padding:3px 10px;'
        'color:#00B4A6;font-size:0.7rem;cursor:pointer;">'
        '&#9654; Listen</button>',
        '<button onclick="return false;" style="background:transparent;'
        'border:1px solid rgba(0,180,166,0.2);border-radius:12px;padding:3px 10px;'
        'color:#8899AA;font-size:0.7rem;cursor:pointer;">'
        '&#9646;&#9646; Pause</button>',
        '<button onclick="return false;" style="background:transparent;'
        'border:1px solid rgba(0,180,166,0.1);border-radius:10px;padding:3px 7px;'
        'color:#7A8FA3;font-size:0.65rem;cursor:pointer;">'
        '0.75&#215;</button>',
        '<button onclick="return false;" style="background:rgba(0,180,166,0.1);'
        'border:1px solid rgba(0,180,166,0.3);border-radius:10px;padding:3px 7px;'
        'color:#00B4A6;font-size:0.65rem;cursor:pointer;">'
        '1&#215;</button>',
        '<button onclick="return false;" style="background:transparent;'
        'border:1px solid rgba(0,180,166,0.1);border-radius:10px;padding:3px 7px;'
        'color:#7A8FA3;font-size:0.65rem;cursor:pointer;">'
        '1.5&#215;</button>',
        '</div></div>',
    ]
    st.sidebar.markdown("".join(html_parts), unsafe_allow_html=True)
