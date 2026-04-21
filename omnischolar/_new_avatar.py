# ── Enhanced Avatar (3D-style emotional Dr. Omni) ────────────────────────────

def render_avatar_teacher(text: str = "", phase: str = "greeting",
                          emotion: str = "neutral",
                          show_speech_controls: bool = True,
                          student_name: str = "") -> None:
    """
    3D-style emotional avatar — Dr. Omni.
    Emotions: neutral / happy / angry / thinking / excited / encouraging
    Phases:   greeting / teaching / questioning / correct / wrong / recap / waiting
    """
    emotions = {
        "neutral": {
            "brow_l": "M 28 22 Q 33 20 38 22",
            "brow_r": "M 42 22 Q 47 20 52 22",
            "mouth":  "M 33 44 Q 40 48 47 44",
            "eye_ry": "3.5",
            "cheek":  "transparent",
            "extra":  "",
        },
        "happy": {
            "brow_l": "M 28 21 Q 33 18 38 21",
            "brow_r": "M 42 21 Q 47 18 52 21",
            "mouth":  "M 30 43 Q 40 54 50 43",
            "eye_ry": "2.8",
            "cheek":  "rgba(255,100,100,0.25)",
            "extra":  """
                <text x="54" y="22" font-size="12" opacity="0.9">✨</text>
                <text x="14" y="22" font-size="12" opacity="0.9">✨</text>
            """,
        },
        "angry": {
            "brow_l": "M 28 24 Q 33 20 38 22",
            "brow_r": "M 42 22 Q 47 20 52 24",
            "mouth":  "M 32 48 Q 40 43 48 48",
            "eye_ry": "2.5",
            "cheek":  "rgba(255,60,60,0.15)",
            "extra":  """
                <text x="56" y="18" font-size="14" opacity="0.8">😤</text>
                <path d="M 34 14 Q 36 10 38 14" fill="none"
                      stroke="#EF4444" stroke-width="1.5" opacity="0.7"/>
                <path d="M 42 14 Q 44 10 46 14" fill="none"
                      stroke="#EF4444" stroke-width="1.5" opacity="0.7"/>
            """,
        },
        "thinking": {
            "brow_l": "M 28 22 Q 33 22 38 20",
            "brow_r": "M 42 20 Q 47 22 52 22",
            "mouth":  "M 35 46 Q 40 44 45 46",
            "eye_ry": "4",
            "cheek":  "transparent",
            "extra":  """
                <text x="54" y="18" font-size="14">💭</text>
                <circle cx="61" cy="10" r="6" fill="#1A2540"
                        stroke="#A0B4D6" stroke-width="1">
                  <animate attributeName="r" values="6;8;6"
                           dur="1.5s" repeatCount="indefinite"/>
                </circle>
                <text x="57" y="14" font-size="7" fill="#A0B4D6">?</text>
            """,
        },
        "excited": {
            "brow_l": "M 26 20 Q 32 17 38 20",
            "brow_r": "M 42 20 Q 48 17 54 20",
            "mouth":  "M 29 42 Q 40 56 51 42",
            "eye_ry": "4.5",
            "cheek":  "rgba(255,184,0,0.2)",
            "extra":  """
                <text x="54" y="15" font-size="12" opacity="0.9">⭐</text>
                <text x="12" y="15" font-size="12" opacity="0.9">⭐</text>
                <text x="33" y="8"  font-size="10" opacity="0.8">🎉</text>
            """,
        },
        "encouraging": {
            "brow_l": "M 28 21 Q 33 19 38 21",
            "brow_r": "M 42 21 Q 47 19 52 21",
            "mouth":  "M 31 43 Q 40 51 49 43",
            "eye_ry": "3.8",
            "cheek":  "rgba(0,200,80,0.15)",
            "extra":  "<text x='52' y='18' font-size='12'>👍</text>",
        },
    }

    phase_cfg = {
        "greeting":    ("#00D4FF", "Ready to Teach",  "#001D35"),
        "teaching":    ("#FFB800", "Teaching",         "#1D1400"),
        "questioning": ("#00C850", "Question Time",    "#001D0D"),
        "correct":     ("#00C850", "Correct!",         "#001D0D"),
        "wrong":       ("#EF4444", "Let me guide you", "#1D0000"),
        "recap":       ("#9B59B6", "Lesson Complete",  "#0D0020"),
        "waiting":     ("#A0B4D6", "Waiting",          "#0D1426"),
    }
    color, label, bg = phase_cfg.get(phase, ("#00D4FF", "Active", "#0D1B35"))

    if emotion == "neutral" and phase == "correct":
        emotion = "happy"
    elif emotion == "neutral" and phase == "wrong":
        emotion = "angry"
    elif emotion == "neutral" and phase == "questioning":
        emotion = "thinking"
    elif emotion == "neutral" and phase == "teaching":
        emotion = "encouraging"

    em = emotions.get(emotion, emotions["neutral"])

    safe = (text.replace("'", "\\'")
               .replace("\n", " ")
               .replace('"', '\\"')
               .replace("`", "'"))[:500]
    display = (text[:200] + "..." if len(text) > 200
               else text or "Enter a topic to begin your lesson.")
    uid = f"omni_{abs(hash(text + phase + emotion)) % 99999}"
    auto_speak = f"setTimeout(speak_{uid}, 700);" if (
        phase in ("teaching", "questioning", "correct", "wrong") and text
    ) else ""

    name_suffix = f"· Hi {student_name}!" if student_name else ""
    italic_style = "italic" if emotion == "thinking" else "normal"

    if show_speech_controls and text:
        controls_html = f"""
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <button onclick="speak_{uid}()" style="padding:5px 14px;background:{color}22;color:{color};border:1px solid {color}55;border-radius:8px;cursor:pointer;font-size:0.75rem;font-weight:600;transition:all 0.2s;">🔊 Listen</button>
          <button onclick="pause_{uid}()" style="padding:5px 12px;background:rgba(255,184,0,0.12);color:#FFB800;border:1px solid rgba(255,184,0,0.3);border-radius:8px;cursor:pointer;font-size:0.8rem;">⏸</button>
          <button onclick="stop_{uid}()"  style="padding:5px 12px;background:rgba(239,68,68,0.1);color:#EF4444;border:1px solid rgba(239,68,68,0.3);border-radius:8px;cursor:pointer;font-size:0.8rem;">⏹</button>
          <input type="range" id="spd_{uid}" min="0.6" max="1.6" step="0.1" value="0.95"
                 style="width:65px;accent-color:{color};"
                 oninput="document.getElementById('lbl_{uid}').innerText=parseFloat(this.value).toFixed(1)+'x'"/>
          <span id="lbl_{uid}" style="font-size:0.65rem;color:{color};min-width:30px;">0.9x</span>
        </div>
        """
    else:
        controls_html = "<div></div>"

    components.html(f"""
    <style>
    @keyframes breathe_{uid} {{
      0%,100% {{ transform: scaleY(1); }}
      50%      {{ transform: scaleY(1.04); }}
    }}
    @keyframes blink_{uid} {{
      0%,90%,100% {{ transform: scaleY(1); }}
      95%         {{ transform: scaleY(0.05); }}
    }}
    @keyframes float_{uid} {{
      0%,100% {{ transform: translateY(0px); }}
      50%     {{ transform: translateY(-4px); }}
    }}
    @keyframes glow_{uid} {{
      0%,100% {{ box-shadow: 0 0 12px {color}44; }}
      50%     {{ box-shadow: 0 0 28px {color}88; }}
    }}
    </style>

    <div style="display:flex;align-items:flex-start;gap:20px;
                padding:20px 24px;
                background:linear-gradient(160deg,{bg}ee,#0A0F1EDD);
                border:1.5px solid {color}66;border-radius:18px;
                margin:10px 0;font-family:'Segoe UI',sans-serif;
                animation:glow_{uid} 3s ease-in-out infinite;">

      <div style="flex-shrink:0;animation:float_{uid} 4s ease-in-out infinite;">
        <svg width="100" height="130" viewBox="0 0 80 120">

          <ellipse cx="40" cy="115" rx="20" ry="5"
                   fill="black" opacity="0.3"/>

          <defs>
            <radialGradient id="bodyGrad_{uid}" cx="35%" cy="30%">
              <stop offset="0%"   stop-color="{color}44"/>
              <stop offset="100%" stop-color="{color}11"/>
            </radialGradient>
            <radialGradient id="faceGrad_{uid}" cx="35%" cy="30%">
              <stop offset="0%"   stop-color="#2A3A5A"/>
              <stop offset="100%" stop-color="#111929"/>
            </radialGradient>
          </defs>

          <ellipse cx="40" cy="95" rx="22" ry="18"
                   fill="url(#bodyGrad_{uid})"
                   stroke="{color}" stroke-width="1.2">
            <animate attributeName="ry" values="18;20;18"
                     dur="4s" repeatCount="indefinite"/>
          </ellipse>

          <path d="M 30 78 Q 40 84 50 78"
                fill="none" stroke="{color}88" stroke-width="2"
                stroke-linecap="round"/>

          <circle cx="40" cy="40" r="28"
                  fill="url(#faceGrad_{uid})"
                  stroke="{color}" stroke-width="2"/>

          <ellipse cx="33" cy="28" rx="8" ry="6"
                   fill="white" opacity="0.06"/>

          <path d="M 16 36 Q 14 12 40 9 Q 66 12 64 36"
                fill="{color}44" stroke="{color}" stroke-width="1.5"/>
          <path d="M 22 22 Q 30 14 42 12"
                fill="none" stroke="{color}88" stroke-width="2"
                stroke-linecap="round"/>

          <ellipse cx="22" cy="46" rx="7" ry="5"
                   fill="{em['cheek']}" opacity="0.8"/>
          <ellipse cx="58" cy="46" rx="7" ry="5"
                   fill="{em['cheek']}" opacity="0.8"/>

          <path d="{em['brow_l']}" fill="none"
                stroke="{color}" stroke-width="2.5"
                stroke-linecap="round"/>
          <path d="{em['brow_r']}" fill="none"
                stroke="{color}" stroke-width="2.5"
                stroke-linecap="round"/>

          <g style="animation:blink_{uid} 5s ease-in-out infinite;">
            <ellipse cx="33" cy="35" rx="5" ry="{em['eye_ry']}"
                     fill="{color}"/>
            <ellipse cx="47" cy="35" rx="5" ry="{em['eye_ry']}"
                     fill="{color}"/>
          </g>
          <circle cx="34" cy="36" r="2.5" fill="#0A0F1E"/>
          <circle cx="48" cy="36" r="2.5" fill="#0A0F1E"/>
          <circle cx="35.5" cy="34" r="1.2" fill="white" opacity="0.9"/>
          <circle cx="49.5" cy="34" r="1.2" fill="white" opacity="0.9"/>

          <path d="M 38 40 Q 40 45 42 40"
                fill="none" stroke="{color}55" stroke-width="1.2"
                stroke-linecap="round"/>

          <path id="mouth_{uid}" d="{em['mouth']}"
                stroke="{color}" stroke-width="2.8" fill="none"
                stroke-linecap="round"/>

          {em['extra']}

          <g id="dots_{uid}" opacity="0">
            <circle cx="60" cy="24" r="3.5" fill="{color}">
              <animate attributeName="r" values="3.5;5;3.5"
                       dur="0.5s" begin="0s" repeatCount="indefinite"/>
            </circle>
            <circle cx="67" cy="17" r="3.5" fill="{color}">
              <animate attributeName="r" values="3.5;5;3.5"
                       dur="0.5s" begin="0.17s" repeatCount="indefinite"/>
            </circle>
            <circle cx="74" cy="10" r="3.5" fill="{color}">
              <animate attributeName="r" values="3.5;5;3.5"
                       dur="0.5s" begin="0.34s" repeatCount="indefinite"/>
            </circle>
          </g>

          <rect x="8" y="105" width="64" height="14"
                rx="7" fill="{color}22"
                stroke="{color}55" stroke-width="0.8"/>
          <text x="40" y="115" text-anchor="middle"
                font-size="7" fill="{color}"
                font-family="monospace" font-weight="bold"
                letter-spacing="1">DR. OMNI</text>

        </svg>
      </div>

      <div style="flex:1;min-width:0;">
        <div style="font-size:0.58rem;color:{color};letter-spacing:0.2em;
                    text-transform:uppercase;margin-bottom:6px;font-weight:700;
                    display:flex;align-items:center;gap:6px;">
          <span style="display:inline-block;width:6px;height:6px;
                       border-radius:50%;background:{color};
                       animation:blink_{uid} 2s infinite;"></span>
          ⬡ DR. OMNI · {label.upper()} {name_suffix}
        </div>

        <div style="position:relative;background:{color}0D;
                    border:1px solid {color}33;border-radius:12px;
                    padding:12px 16px;margin-bottom:10px;">
          <div style="font-size:0.9rem;color:#D0E4F8;line-height:1.7;
                      font-style:{italic_style};">
            {display}
          </div>
        </div>

        {controls_html}
      </div>
    </div>

    <script>
    (function() {{
      const TXT = '{safe}';
      const sy = window.speechSynthesis;
      let going = false, paused = false;
      const dots  = document.getElementById('dots_{uid}');
      const mouth = document.getElementById('mouth_{uid}');
      const defM  = '{em["mouth"]}';
      let mIv = null;

      function startM() {{
        if (mIv) clearInterval(mIv);
        let t = true;
        mIv = setInterval(() => {{
          if (!going) {{ clearInterval(mIv); return; }}
          mouth && mouth.setAttribute('d',
            t ? 'M 30 44 Q 40 56 50 44' : 'M 32 44 Q 40 50 48 44');
          t = !t;
        }}, 140);
      }}

      function stopM() {{
        if (mIv) {{ clearInterval(mIv); mIv = null; }}
        mouth && mouth.setAttribute('d', defM);
      }}

      window['speak_{uid}'] = function() {{
        if (sy.speaking) sy.cancel();
        if (!TXT) return;
        const spd = document.getElementById('spd_{uid}');
        const u = new SpeechSynthesisUtterance(TXT);
        u.rate  = spd ? parseFloat(spd.value) : 0.95;
        u.pitch = 1.05;
        u.lang  = 'en-US';
        const vs = sy.getVoices();
        const pv = vs.find(v =>
          v.name.includes('Google') || v.name.includes('Natural') ||
          v.name.includes('Daniel') || v.name.includes('Samantha') ||
          v.name.includes('Karen')
        );
        if (pv) u.voice = pv;
        u.onstart = () => {{
          going = true; paused = false;
          dots && dots.setAttribute('opacity','1');
          startM();
        }};
        u.onend = u.onerror = () => {{
          going = false; paused = false;
          dots && dots.setAttribute('opacity','0');
          stopM();
        }};
        sy.speak(u);
      }};

      window['pause_{uid}'] = function() {{
        if (sy.speaking && !paused) {{
          sy.pause(); paused = true; going = false;
          stopM();
        }} else if (paused) {{
          sy.resume(); paused = false; going = true;
          startM();
        }}
      }};

      window['stop_{uid}'] = function() {{
        sy.cancel(); going = false; paused = false;
        dots && dots.setAttribute('opacity','0');
        stopM();
      }};

      {auto_speak}
    }})();
    </script>
    """, height=210)


# ── Session summary card ─────────────────────────────────────────────────────

def render_session_summary(student_name: str, db, student_id: str,
                           subject: str) -> None:
    """
    Render a full session performance summary.
    Shows strong areas, weak areas, and overall readiness change.
    """
    try:
        weak = db.get_weak_concepts(student_id, resolved=False) or []
        strong_chapters = (
            db.get_chapter_scores_by_subject(student_id, subject) or []
        )
        strong   = [c for c in strong_chapters if c.get("score", 0) >= 70]
        critical = [c for c in strong_chapters if c.get("score", 0) < 40]
    except Exception:
        weak, strong, critical = [], [], []

    memory = _get_lesson_memory()

    strong_html = ""
    if strong:
        strong_chips = "".join([
            f'<span style="display:inline-block;background:rgba(0,200,80,0.1);'
            f'color:#00C850;border:1px solid rgba(0,200,80,0.2);'
            f'border-radius:6px;padding:3px 10px;font-size:0.78rem;margin:3px;">'
            f'{c.get("chapter_name", c.get("name", "?"))} '
            f'{c.get("score", 0):.0f}%</span>'
            for c in strong[:5]
        ])
        strong_html = (
            '<div style="margin-bottom:10px;">'
            '<div style="font-size:0.65rem;color:#00C850;letter-spacing:0.1em;'
            'text-transform:uppercase;margin-bottom:6px;">'
            '✅ Strong Chapters</div>' + strong_chips + '</div>'
        )

    weak_html = ""
    if weak:
        weak_chips = "".join([
            f'<span style="display:inline-block;background:rgba(239,68,68,0.08);'
            f'color:#EF4444;border:1px solid rgba(239,68,68,0.2);'
            f'border-radius:6px;padding:3px 10px;font-size:0.78rem;margin:3px;">'
            f'{w.get("concept", "?")[:30]}</span>'
            for w in weak[:4]
        ])
        weak_html = (
            '<div style="margin-bottom:10px;">'
            '<div style="font-size:0.65rem;color:#EF4444;letter-spacing:0.1em;'
            'text-transform:uppercase;margin-bottom:6px;">'
            '⚠️ Focus Next</div>' + weak_chips + '</div>'
        )

    memory_html = ""
    if memory:
        mem_chips = "".join([
            f'<span style="display:inline-block;background:rgba(0,212,255,0.06);'
            f'color:#00D4FF;border:1px solid rgba(0,212,255,0.15);'
            f'border-radius:6px;padding:3px 10px;font-size:0.78rem;margin:3px;">'
            f'📖 {m["topic"]}</span>'
            for m in memory
        ])
        memory_html = (
            '<div><div style="font-size:0.65rem;color:#00D4FF;'
            'letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">'
            '📚 Covered Today</div>' + mem_chips + '</div>'
        )

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0D0020,#111929);
                border:1.5px solid #9B59B666;border-radius:18px;
                padding:28px;margin:16px 0;position:relative;overflow:hidden;">
      <div style="position:absolute;top:0;left:0;right:0;height:3px;
                  background:linear-gradient(90deg,transparent,#9B59B6,transparent);">
      </div>
      <div style="font-family:Orbitron,monospace;font-size:0.65rem;
                  color:#9B59B6;letter-spacing:0.2em;text-transform:uppercase;
                  margin-bottom:16px;">📊 SESSION SUMMARY — {student_name.upper()}</div>

      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;
                  margin-bottom:16px;">
        <div style="background:rgba(0,200,80,0.08);border:1px solid rgba(0,200,80,0.2);
                    border-radius:10px;padding:12px;text-align:center;">
          <div style="font-size:0.6rem;color:#00C850;letter-spacing:0.1em;
                      text-transform:uppercase;">Strong Areas</div>
          <div style="font-family:Orbitron,monospace;font-size:1.5rem;
                      color:#00C850;font-weight:900;">{len(strong)}</div>
          <div style="font-size:0.72rem;color:#A0B4D6;">chapters ≥70%</div>
        </div>
        <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);
                    border-radius:10px;padding:12px;text-align:center;">
          <div style="font-size:0.6rem;color:#EF4444;letter-spacing:0.1em;
                      text-transform:uppercase;">Weak Areas</div>
          <div style="font-family:Orbitron,monospace;font-size:1.5rem;
                      color:#EF4444;font-weight:900;">{len(weak)}</div>
          <div style="font-size:0.72rem;color:#A0B4D6;">active concepts</div>
        </div>
        <div style="background:rgba(0,212,255,0.08);border:1px solid rgba(0,212,255,0.2);
                    border-radius:10px;padding:12px;text-align:center;">
          <div style="font-size:0.6rem;color:#00D4FF;letter-spacing:0.1em;
                      text-transform:uppercase;">Topics Today</div>
          <div style="font-family:Orbitron,monospace;font-size:1.5rem;
                      color:#00D4FF;font-weight:900;">{len(memory)}</div>
          <div style="font-size:0.72rem;color:#A0B4D6;">lessons complete</div>
        </div>
      </div>

      {strong_html}
      {weak_html}
      {memory_html}
    </div>
    """, unsafe_allow_html=True)


