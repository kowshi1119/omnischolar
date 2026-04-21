"""
virtual_teacher.py — World-Class Virtual Teacher for OmniScholar

Dr. Omni delivers lessons with:
  - Progressive section-by-section delivery
  - Mid-lesson Socratic questions (active recall, not passive reading)
  - Auto-generated Mermaid diagrams
  - Enhanced expressive avatar with emotion states
  - Web Speech API with speed/pause control
  - Hint system (3 levels)
  - Lesson memory across topics
  - Full lesson recap card
  - Related topic suggestions
"""

import json
import re
import time
import uuid

import streamlit as st
import streamlit.components.v1 as components

from prompt import (
    VIRTUAL_TEACHER_PROMPT,
    VIRTUAL_TEACHER_EVAL_PROMPT,
    VIRTUAL_TEACHER_DIAGRAM_PROMPT,
    VIRTUAL_TEACHER_MID_QUESTION_PROMPT,
    VIRTUAL_TEACHER_SOCRATIC_FOLLOWUP,
    VIRTUAL_TEACHER_RECAP_PROMPT,
)
from rag import retrieve_context


# ── Lesson memory across topics in session ────────────────────────────────────

def _get_lesson_memory() -> list:
    if "vt_lesson_memory" not in st.session_state:
        st.session_state["vt_lesson_memory"] = []
    return st.session_state["vt_lesson_memory"]


def _add_to_memory(topic: str, key_points: list):
    memory = _get_lesson_memory()
    memory.append({"topic": topic, "points": key_points})
    if len(memory) > 10:
        memory.pop(0)


# ── VirtualTeacher class ──────────────────────────────────────────────────────

class VirtualTeacher:
    def __init__(self, ollama_client, db, rag=None):
        self.client = ollama_client
        self.db = db

    # ── Core lesson generation ────────────────────────────────────────────────

    def teach(self, topic: str, subject: str, student_id: str,
              language: str) -> dict:
        """Generate full lesson dict. RAG-grounded. Returns rich lesson object."""
        try:
            rag_context, sources = retrieve_context(topic, subject, n_results=3)
        except Exception:
            rag_context, sources = "", []

        prompt = VIRTUAL_TEACHER_PROMPT.format(
            subject=subject, name="the student",
            language=language, topic=topic,
            rag_context=rag_context or "No uploaded materials for this topic.",
        )

        try:
            raw = self.client.chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="",
                temperature=0.9,
                num_ctx=4096,
            )
        except Exception as exc:
            raw = json.dumps({
                "hook": f"Let's explore {topic} together.",
                "explanation": f"Could not reach model: {exc}",
                "worked_example": "Not available.",
                "exam_hook": [
                    f"Define {topic}",
                    f"Explain the key principles of {topic}",
                    f"Give an example of {topic}",
                ],
                "check_questions": [
                    {"question": f"What is {topic}?",
                     "expected_key_points": "basic understanding"},
                ],
            })

        lesson = self._parse_lesson(raw, topic)
        lesson["_sources"] = sources
        lesson["_topic"] = topic
        lesson["_subject"] = subject
        lesson["_language"] = language

        lesson["_diagram"] = self.generate_diagram(topic, subject)

        lesson["_mid_question"] = self.generate_mid_question(
            topic, subject,
            just_explained=lesson.get("explanation", "")[:300],
            name="the student",
            language=language,
        )

        return lesson

    # ── Diagram generation ────────────────────────────────────────────────────

    def generate_diagram(self, topic: str, subject: str) -> str:
        """Generate Mermaid diagram code for the topic. Returns raw mermaid string."""
        prompt = VIRTUAL_TEACHER_DIAGRAM_PROMPT.format(
            topic=topic, subject=subject
        )
        try:
            raw = self.client.fast_chat(
                message=prompt,
                system="Return ONLY Mermaid diagram code. No markdown fences. No explanation.",
                max_tokens=500,
            )
            raw = raw.strip()
            for fence in ["```mermaid", "```", "~~~"]:
                raw = raw.replace(fence, "").strip()
            return raw
        except Exception:
            return f"""flowchart TD
    A[{topic}] --> B[Key Concept 1]
    A --> C[Key Concept 2]
    A --> D[Key Concept 3]
    B --> E[Application]
    C --> E
    style A fill:#1A2540,stroke:#00D4FF,color:#E8F0FF
    style E fill:#0D1B35,stroke:#00C850,color:#E8F0FF"""

    # ── Mid-lesson question generation ───────────────────────────────────────

    def generate_mid_question(self, topic: str, subject: str,
                              just_explained: str, name: str,
                              language: str = "english") -> dict:
        """Generate a single sharp mid-lesson check question."""
        prompt = VIRTUAL_TEACHER_MID_QUESTION_PROMPT.format(
            topic=topic, subject=subject,
            just_explained=just_explained, language=language,
        )
        try:
            raw = self.client.fast_chat(
                message=prompt,
                system="Return ONLY valid JSON. No markdown. Be conversational.",
                max_tokens=250,
            )
            raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            return json.loads(raw)
        except Exception:
            return {
                "question": f"Quick check — can you explain {topic} in one sentence?",
                "expected": "basic definition in own words",
                "hint": f"Think about what {topic} does and why it matters.",
            }

    # ── Socratic follow-up ────────────────────────────────────────────────────

    def get_socratic_followup(self, topic: str, question: str,
                              student_answer: str, expected: str) -> dict:
        """After wrong answer: don't correct, ask probing question."""
        prompt = VIRTUAL_TEACHER_SOCRATIC_FOLLOWUP.format(
            topic=topic, question=question,
            student_answer=student_answer, expected=expected,
        )
        try:
            raw = self.client.fast_chat(
                message=prompt,
                system="Return only valid JSON. No markdown.",
                max_tokens=200,
            )
            raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            return json.loads(raw)
        except Exception:
            return {
                "acknowledgement": "Not quite.",
                "probing_question": f"Think about what {topic} means fundamentally.",
                "nudge": "Focus on the core definition first.",
            }

    # ── Lesson recap ──────────────────────────────────────────────────────────

    def generate_recap(self, topic: str, subject: str) -> dict:
        """Generate a 5-point recap card at end of lesson."""
        prompt = VIRTUAL_TEACHER_RECAP_PROMPT.format(
            topic=topic, subject=subject
        )
        try:
            raw = self.client.fast_chat(
                message=prompt,
                system="Return only valid JSON. No markdown.",
                max_tokens=600,
            )
            raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            return json.loads(raw)
        except Exception:
            return {
                "title": f"Lesson Recap: {topic}",
                "points": [f"Key concept {i+1} of {topic}" for i in range(5)],
                "exam_one_liner": f"{topic} is a fundamental concept in {subject}.",
                "related_topics": [],
                "memory_trick": f"Remember {topic} as a core building block.",
            }

    # ── Answer evaluation ─────────────────────────────────────────────────────

    def evaluate_check_answer(self, question: str, student_answer: str,
                              topic: str, student_id: str, language: str,
                              expected_key_points: str = "",
                              subject: str = "") -> dict:
        """Evaluate answer. Writes weakness to DB if detected."""
        eval_prompt = VIRTUAL_TEACHER_EVAL_PROMPT.format(
            question=question,
            expected_key_points=expected_key_points or "basic understanding",
            student_answer=student_answer,
            language=language,
            subject=subject or "the subject",
            topic=topic,
        )
        try:
            raw = self.client.fast_chat(
                message=eval_prompt,
                system="Return only valid JSON. No markdown.",
                max_tokens=150,
            )
        except Exception as exc:
            return {"correct": False,
                    "feedback": f"Evaluation unavailable ({exc})",
                    "weakness": None}

        try:
            result = json.loads(raw)
        except Exception:
            m = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
            result = json.loads(m.group()) if m else {}

        correct = bool(result.get("correct", False))
        feedback = str(result.get("feedback", raw[:200]))
        weakness = result.get("weakness") or None

        if weakness and student_id and self.db:
            try:
                self.db.upsert_weak_concept(
                    student_id=student_id, concept=weakness,
                    topic=topic, error_type="comprehension_error",
                )
            except Exception:
                pass

        return {"correct": correct, "feedback": feedback, "weakness": weakness}

    def detect_zpd_level(self, topic: str, student_id: str,
                          correct_streak: int, wrong_streak: int) -> str:
        """
        Detect Vygotsky ZPD floor and ceiling.
        Returns: 'too_easy' | 'in_zpd' | 'too_hard' | 'mastered'
        Based on last 5 answers pattern.
        """
        if correct_streak >= 3:
            return "mastered"
        elif correct_streak >= 2 and wrong_streak == 0:
            return "in_zpd"
        elif wrong_streak >= 2:
            return "too_hard"
        elif wrong_streak == 0 and correct_streak == 1:
            return "in_zpd"
        else:
            return "too_hard"

    def get_next_topic_recommendation(self, topic: str, subject: str,
                                       zpd_status: str) -> str:
        """Based on ZPD status, recommend what to study next."""
        if zpd_status == "mastered":
            return f"Ready to advance beyond {topic}"
        elif zpd_status == "too_hard":
            return f"Review prerequisites of {topic} first"
        else:
            return f"Continue practicing {topic} — you're in the learning zone"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _parse_lesson(self, raw: str, topic: str) -> dict:
        try:
            return json.loads(raw)
        except Exception:
            pass
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
        return {
            "hook": f"Let's explore {topic}.",
            "explanation": raw,
            "worked_example": "See explanation above.",
            "exam_hook": [f"Define {topic}",
                          f"Explain {topic} with example",
                          f"Common mistakes about {topic}"],
            "check_questions": [
                {"question": f"In your own words, what is {topic}?",
                 "expected_key_points": "basic understanding"},
                {"question": f"Give one real-world example of {topic}.",
                 "expected_key_points": "concrete accurate example"},
            ],
        }


# ── Enhanced Avatar ───────────────────────────────────────────────────────────

def render_avatar_teacher(text: str = "", phase: str = "greeting",
                          emotion: str = "neutral",
                          show_speech_controls: bool = True,
                          student_name: str = "") -> None:
    """
    V3 Dr. Omni avatar — 3D-style emotional face with:
    - Emotions: neutral / happy / angry / thinking / excited / encouraging
    - Eyebrow paths, cheek blush, hair highlight, forehead shine
    - float + glow + blink CSS animations (UID-scoped)
    - Web Speech API with speed slider, pause/resume/stop
    - Phase-based color themes, DR. OMNI badge
    - Auto-emotion mapping from phase when emotion='neutral'
    """
    # Auto-map emotion from phase when not explicitly set
    phase_emotion_map = {
        "correct":     "happy",
        "wrong":       "angry",
        "questioning": "thinking",
        "recap":       "excited",
        "teaching":    "encouraging",
        "greeting":    "neutral",
    }
    if emotion == "neutral" and phase in phase_emotion_map:
        emotion = phase_emotion_map[phase]

    phase_config = {
        "greeting":    {"color": "#00D4FF", "label": "Ready to Teach",    "bg": "#001D35"},
        "teaching":    {"color": "#FFB800", "label": "Teaching",           "bg": "#1D1400"},
        "questioning": {"color": "#00C850", "label": "Question Time",      "bg": "#001D0D"},
        "waiting":     {"color": "#A0B4D6", "label": "Waiting",            "bg": "#0D1426"},
        "correct":     {"color": "#00C850", "label": "Excellent!",         "bg": "#001D0D"},
        "wrong":       {"color": "#EF4444", "label": "Let me guide you",   "bg": "#1D0000"},
        "recap":       {"color": "#9B59B6", "label": "Lesson Complete",    "bg": "#0D0020"},
    }
    cfg = phase_config.get(phase, phase_config["greeting"])
    color = cfg["color"]
    raw_label = cfg["label"]
    label = f"Hi {student_name}! · {raw_label}" if student_name else raw_label
    bg = cfg["bg"]

    # V3 emotion config: brow paths, mouth, eye height, cheek color, extra SVG
    emotions = {
        "neutral": {
            "brow_l": "M 26 24 Q 33 21 38 23",
            "brow_r": "M 52 23 Q 57 21 64 24",
            "mouth":  "M 27 38 Q 35 44 43 38",
            "eye_ry": "3.5",
            "cheek":  "transparent",
            "extra":  "",
        },
        "happy": {
            "brow_l": "M 26 22 Q 33 19 38 21",
            "brow_r": "M 52 21 Q 57 19 64 22",
            "mouth":  "M 24 37 Q 35 50 46 37",
            "eye_ry": "2.8",
            "cheek":  "#FF8888",
            "extra":  (
                '<text x="60" y="15" font-size="10" opacity="0.8">✨</text>'
                '<text x="6"  y="18" font-size="8"  opacity="0.7">⭐</text>'
            ),
        },
        "angry": {
            "brow_l": "M 26 26 Q 33 22 38 25",
            "brow_r": "M 52 25 Q 57 22 64 26",
            "mouth":  "M 27 42 Q 35 37 43 42",
            "eye_ry": "2.2",
            "cheek":  "#FF4444",
            "extra":  (
                '<line x1="28" y1="19" x2="32" y2="22" stroke="#EF4444" stroke-width="1.5"/>'
                '<line x1="52" y1="22" x2="56" y2="19" stroke="#EF4444" stroke-width="1.5"/>'
            ),
        },
        "thinking": {
            "brow_l": "M 26 24 Q 33 22 38 24",
            "brow_r": "M 52 22 Q 57 24 64 23",
            "mouth":  "M 30 40 Q 35 40 40 40",
            "eye_ry": "4.0",
            "cheek":  "transparent",
            "extra":  (
                '<circle cx="64" cy="18" r="3" fill="' + color + '" opacity="0.6">'
                '<animate attributeName="r" values="3;5;3" dur="1s" repeatCount="indefinite"/>'
                '</circle>'
                '<circle cx="70" cy="11" r="4" fill="' + color + '" opacity="0.4">'
                '<animate attributeName="r" values="4;6;4" dur="1s" begin="0.3s" repeatCount="indefinite"/>'
                '</circle>'
                '<circle cx="75" cy="5"  r="5" fill="' + color + '22" stroke="' + color + '" stroke-width="1">'
                '<animate attributeName="r" values="5;7;5" dur="1s" begin="0.6s" repeatCount="indefinite"/>'
                '</circle>'
            ),
        },
        "excited": {
            "brow_l": "M 26 21 Q 33 17 38 20",
            "brow_r": "M 52 20 Q 57 17 64 21",
            "mouth":  "M 23 36 Q 35 52 47 36",
            "eye_ry": "2.5",
            "cheek":  "#FFB800",
            "extra":  (
                '<text x="58" y="14" font-size="11" opacity="0.9">🎉</text>'
                '<text x="5"  y="20" font-size="9"  opacity="0.8">⭐</text>'
                '<text x="60" y="70" font-size="8"  opacity="0.6">✨</text>'
            ),
        },
        "encouraging": {
            "brow_l": "M 26 22 Q 33 20 38 22",
            "brow_r": "M 52 22 Q 57 20 64 22",
            "mouth":  "M 25 37 Q 35 47 45 37",
            "eye_ry": "3.8",
            "cheek":  "#88DDFF",
            "extra":  (
                '<text x="60" y="16" font-size="10" opacity="0.8">💡</text>'
            ),
        },
    }
    em = emotions.get(emotion, emotions["neutral"])
    mouth_d  = em["mouth"]
    eye_ry   = em["eye_ry"]
    brow_l   = em["brow_l"]
    brow_r   = em["brow_r"]
    cheek_c  = em["cheek"]
    extra_svg = em["extra"]

    safe = (text.replace("'", "\\'")
               .replace("\n", " ")
               .replace('"', '\\"')
               .replace("`", "'"))[:500]
    display = (text[:160] + "..." if len(text) > 160
               else text or "Enter a topic to begin your lesson.")
    uid = f"omni_{phase}_{hash(text) % 10000}"
    auto_speak = f"setTimeout(()=>speak_{uid}(),600);" if (phase in ("teaching", "questioning", "correct", "wrong") and text) else ""

    controls_html = ""
    if show_speech_controls and text:
        controls_html = f"""
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <button onclick="speak_{uid}()" id="btn_speak_{uid}"
                  style="padding:5px 14px;background:{color}22;color:{color};
                         border:1px solid {color}55;border-radius:8px;
                         cursor:pointer;font-size:0.75rem;font-weight:600;">
            🔊 Listen
          </button>
          <button onclick="pause_{uid}()" id="btn_pause_{uid}"
                  style="padding:5px 10px;background:rgba(255,184,0,0.12);
                         color:#FFB800;border:1px solid rgba(255,184,0,0.3);
                         border-radius:8px;cursor:pointer;font-size:0.75rem;">
            ⏸
          </button>
          <button onclick="stopSpeech_{uid}()"
                  style="padding:5px 10px;background:rgba(239,68,68,0.1);
                         color:#EF4444;border:1px solid rgba(239,68,68,0.3);
                         border-radius:8px;cursor:pointer;font-size:0.75rem;">
            ⏹
          </button>
          <div style="display:flex;align-items:center;gap:6px;">
            <span style="font-size:0.65rem;color:#4A6080;">Speed:</span>
            <input type="range" id="speed_{uid}" min="0.5" max="1.8"
                   step="0.1" value="0.95"
                   style="width:70px;accent-color:{color};"
                   oninput="document.getElementById('spd_lbl_{uid}').innerText=this.value+'x'"/>
            <span id="spd_lbl_{uid}" style="font-size:0.65rem;color:{color};
                                             min-width:28px;">0.95x</span>
          </div>
        </div>
        """

    cheek_html = (
        f'<ellipse cx="28" cy="38" rx="6" ry="4" fill="{cheek_c}" opacity="0.35"/>'
        f'<ellipse cx="62" cy="38" rx="6" ry="4" fill="{cheek_c}" opacity="0.35"/>'
    ) if cheek_c not in ("transparent", "") else ""

    components.html(f"""
    <style>
      @keyframes float_{uid} {{
        0%,100% {{ transform: translateY(0px); }}
        50%      {{ transform: translateY(-5px); }}
      }}
      @keyframes glow_{uid} {{
        0%,100% {{ filter: drop-shadow(0 0 4px {color}55); }}
        50%      {{ filter: drop-shadow(0 0 12px {color}CC); }}
      }}
    </style>

    <div id="av_{uid}" style="display:flex;align-items:flex-start;gap:20px;
                padding:20px 24px;
                background:linear-gradient(135deg,{bg},{bg}dd);
                border:1px solid {color}55;border-radius:16px;margin:10px 0;
                font-family:'Segoe UI',sans-serif;
                box-shadow:0 0 24px {color}22;">

      <div style="flex-shrink:0;position:relative;
                  animation:float_{uid} 4s ease-in-out infinite,
                             glow_{uid} 3s ease-in-out infinite;">
        <svg id="svg_{uid}" width="90" height="115" viewBox="0 0 90 115">
          <defs>
            <radialGradient id="faceGrad_{uid}" cx="45%" cy="40%" r="55%">
              <stop offset="0%"   stop-color="#2A3F6A"/>
              <stop offset="100%" stop-color="#111929"/>
            </radialGradient>
            <radialGradient id="bodyGrad_{uid}" cx="50%" cy="30%" r="60%">
              <stop offset="0%"   stop-color="{color}44"/>
              <stop offset="100%" stop-color="{color}11"/>
            </radialGradient>
          </defs>

          <!-- glow ring -->
          <circle cx="45" cy="36" r="30" fill="none"
                  stroke="{color}" stroke-width="0.5" opacity="0.2">
            <animate attributeName="r"       values="30;35;30" dur="3s" repeatCount="indefinite"/>
            <animate attributeName="opacity" values="0.2;0.05;0.2" dur="3s" repeatCount="indefinite"/>
          </circle>

          <!-- body -->
          <ellipse cx="45" cy="86" rx="24" ry="20"
                   fill="url(#bodyGrad_{uid})" stroke="{color}" stroke-width="1.2">
            <animate attributeName="ry" values="20;22;20" dur="4s" repeatCount="indefinite"/>
          </ellipse>
          <path d="M 32 68 Q 45 75 58 68" fill="none"
                stroke="{color}" stroke-width="1.5" opacity="0.6"/>

          <!-- 3D face -->
          <circle cx="45" cy="36" r="26"
                  fill="url(#faceGrad_{uid})"
                  stroke="{color}" stroke-width="2"/>
          <!-- forehead shine -->
          <ellipse cx="40" cy="22" rx="8" ry="4"
                   fill="white" opacity="0.06"/>

          <!-- hair -->
          <path d="M 22 30 Q 20 12 45 10 Q 70 12 68 30"
                fill="{color}33" stroke="{color}" stroke-width="1.2"/>
          <path d="M 28 18 Q 35 12 45 11"
                fill="none" stroke="{color}99" stroke-width="2"
                stroke-linecap="round"/>

          <!-- cheeks -->
          {cheek_html}

          <!-- eyebrows -->
          <path d="{brow_l}" fill="none" stroke="{color}" stroke-width="2"
                stroke-linecap="round"/>
          <path d="{brow_r}" fill="none" stroke="{color}" stroke-width="2"
                stroke-linecap="round"/>

          <!-- eyes with blink -->
          <ellipse id="eye_L_{uid}" cx="34" cy="32"
                   rx="3.5" ry="{eye_ry}" fill="{color}">
            <animate attributeName="ry" values="{eye_ry};0.2;{eye_ry}"
                     dur="4s" begin="0s" repeatCount="indefinite"/>
          </ellipse>
          <ellipse id="eye_R_{uid}" cx="56" cy="32"
                   rx="3.5" ry="{eye_ry}" fill="{color}">
            <animate attributeName="ry" values="{eye_ry};0.2;{eye_ry}"
                     dur="4s" begin="0.05s" repeatCount="indefinite"/>
          </ellipse>
          <circle cx="35.5" cy="33" r="1.8" fill="#0A0F1E"/>
          <circle cx="57.5" cy="33" r="1.8" fill="#0A0F1E"/>
          <circle cx="36.5" cy="31.5" r="0.8" fill="white" opacity="0.85"/>
          <circle cx="58.5" cy="31.5" r="0.8" fill="white" opacity="0.85"/>

          <!-- nose bridge -->
          <path d="M 43 38 Q 45 42 47 38"
                fill="none" stroke="{color}55" stroke-width="1"
                stroke-linecap="round"/>

          <!-- mouth -->
          <path id="mouth_{uid}" d="{mouth_d}"
                stroke="{color}" stroke-width="2.5" fill="none"
                stroke-linecap="round"/>

          <!-- emotion extras (sparkles, bubbles, anger lines, etc.) -->
          {extra_svg}

          <!-- speaking dots -->
          <g id="dots_{uid}" opacity="0">
            <circle cx="62" cy="20" r="3" fill="{color}">
              <animate attributeName="opacity" values="0;1;0" dur="0.6s"
                       begin="0s" repeatCount="indefinite"/>
            </circle>
            <circle cx="68" cy="14" r="3" fill="{color}">
              <animate attributeName="opacity" values="0;1;0" dur="0.6s"
                       begin="0.2s" repeatCount="indefinite"/>
            </circle>
            <circle cx="74" cy="8" r="3" fill="{color}">
              <animate attributeName="opacity" values="0;1;0" dur="0.6s"
                       begin="0.4s" repeatCount="indefinite"/>
            </circle>
          </g>

          <!-- DR. OMNI badge -->
          <rect x="18" y="103" width="54" height="10" rx="5"
                fill="{color}22" stroke="{color}66" stroke-width="0.8"/>
          <text x="45" y="111" text-anchor="middle"
                font-family="monospace" font-size="5.5"
                fill="{color}" font-weight="bold">DR. OMNI</text>
        </svg>
      </div>

      <div style="flex:1;min-width:0;">
        <div style="font-size:0.6rem;color:{color};letter-spacing:0.2em;
                    text-transform:uppercase;margin-bottom:6px;font-weight:700;">
          ⬡ {label.upper()}
        </div>

        <div style="font-size:0.92rem;color:#C8D8F0;line-height:1.65;
                    background:{color}0A;border-left:3px solid {color}44;
                    padding:10px 14px;border-radius:0 8px 8px 0;
                    margin-bottom:10px;">
          {display}
        </div>

        {controls_html}
      </div>
    </div>

    <script>
    (function() {{
      const TXT = '{safe}';
      const synth = window.speechSynthesis;
      let going = false;
      let paused = false;

      const dots  = document.getElementById('dots_{uid}');
      const mouth = document.getElementById('mouth_{uid}');
      const defaultMouth = '{mouth_d}';
      let mouthIv = null;

      function startMouth() {{
        if (mouthIv) clearInterval(mouthIv);
        let t = true;
        mouthIv = setInterval(() => {{
          if (!going || !mouth) {{ clearInterval(mouthIv); return; }}
          mouth.setAttribute('d', t
            ? 'M 27 38 Q 35 48 43 38'
            : 'M 27 38 Q 35 43 43 38');
          t = !t;
        }}, 150);
      }}

      function stopMouth() {{
        if (mouthIv) {{ clearInterval(mouthIv); mouthIv = null; }}
        if (mouth) mouth.setAttribute('d', defaultMouth);
      }}

      window['speak_{uid}'] = function() {{
        if (synth.speaking) synth.cancel();
        if (!TXT) return;
        const speedEl = document.getElementById('speed_{uid}');
        const speed = speedEl ? parseFloat(speedEl.value) : 0.95;
        const u = new SpeechSynthesisUtterance(TXT);
        u.rate  = speed;
        u.pitch = 1.05;
        u.lang  = 'en-US';
        const voices = synth.getVoices();
        const preferred = voices.find(v =>
          v.name.includes('Google') || v.name.includes('Natural') ||
          v.name.includes('Daniel') || v.name.includes('Samantha')
        );
        if (preferred) u.voice = preferred;
        u.onstart = () => {{
          going = true; paused = false;
          if (dots) dots.setAttribute('opacity','1');
          startMouth();
        }};
        u.onend = () => {{
          going = false; paused = false;
          if (dots) dots.setAttribute('opacity','0');
          stopMouth();
        }};
        u.onerror = () => {{
          going = false;
          if (dots) dots.setAttribute('opacity','0');
          stopMouth();
        }};
        synth.speak(u);
      }};

      window['pause_{uid}'] = function() {{
        if (synth.speaking && !paused) {{
          synth.pause(); paused = true; going = false;
          stopMouth();
          if (dots) dots.setAttribute('opacity','0.3');
        }} else if (paused) {{
          synth.resume(); paused = false; going = true;
          if (dots) dots.setAttribute('opacity','1');
          startMouth();
        }}
      }};

      window['stopSpeech_{uid}'] = function() {{
        synth.cancel();
        going = false; paused = false;
        if (dots) dots.setAttribute('opacity','0');
        stopMouth();
      }};

      {auto_speak}
    }})();
    </script>
    """, height=210)


# ── Mermaid diagram renderer ─────────────────────────────────────────────────

def render_mermaid_diagram(mermaid_code: str, title: str = "") -> None:
    """Render a Mermaid diagram inline using CDN (works offline after first load)."""
    if not mermaid_code or not mermaid_code.strip():
        return
    title_html = ('<div style="font-size:0.65rem;color:#00D4FF;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:10px;">📊 ' + title + '</div>') if title else ''
    components.html(f"""
    <div style="background:#0A0F1E;border:1px solid rgba(0,212,255,0.2);
                border-radius:12px;padding:16px;margin:8px 0;">
      {title_html}
      <div class="mermaid" style="background:transparent;">
{mermaid_code}
      </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
      mermaid.initialize({{
        startOnLoad: true,
        theme: 'dark',
        themeVariables: {{
          primaryColor: '#1A2540',
          primaryTextColor: '#E8F0FF',
          primaryBorderColor: '#00D4FF',
          lineColor: '#00D4FF',
          secondaryColor: '#0D1B35',
          tertiaryColor: '#111929',
          background: '#0A0F1E',
        }}
      }});
    </script>
    """, height=320)


def render_confidence_badge(source_type: str = "model", has_rag: bool = False) -> None:
    """
    3-band confidence badge:
      grounded  → green  ✅  "Based on your notes"
      model     → amber  ⚠   "Model knowledge (verify in textbook)"
      uncertain → red    📘  "Not in your notes — treat as a guide only"
    """
    if source_type == "grounded" or has_rag:
        color, icon, label = "#2ECC71", "✅", "Based on your uploaded notes"
    elif source_type == "uncertain":
        color, icon, label = "#E74C3C", "📘", "Not in your notes — verify in textbook"
    else:
        color, icon, label = "#F39C12", "⚠", "Model knowledge — verify key facts"

    st.markdown(
        f'<div style="display:inline-block;background:rgba(255,255,255,0.05);'
        f'border:1px solid {color};border-radius:8px;padding:4px 12px;'
        f'font-size:0.75rem;color:{color};margin:4px 0;">'
        f'{icon} {label}</div>',
        unsafe_allow_html=True,
    )


# ── Lesson recap card ─────────────────────────────────────────────────────────

def render_lesson_recap(recap: dict, color: str = "#00D4FF") -> None:
    """Render the 5-point lesson recap card."""
    points_html = "".join([
        f'<div style="display:flex;gap:10px;margin:6px 0;align-items:flex-start;">'
        f'<span style="color:{color};font-weight:700;flex-shrink:0;">{i+1}.</span>'
        f'<span style="color:#C8D8F0;font-size:0.88rem;line-height:1.5;">{p}</span>'
        f'</div>'
        for i, p in enumerate(recap.get("points", []))
    ])
    related = recap.get("related_topics", [])
    related_html = " &nbsp;·&nbsp; ".join(
        f'<span style="color:{color};cursor:pointer;">📌 {t}</span>'
        for t in related
    )
    memory_trick = recap.get("memory_trick", "")
    memory_html = ('<div style="margin-top:12px;padding:8px 12px;background:rgba(255,184,0,0.08);border-radius:8px;"><span style="font-size:0.7rem;color:#FFB800;letter-spacing:0.1em;text-transform:uppercase;">MEMORY TRICK · </span><span style="font-size:0.85rem;color:#C8D8F0;">' + memory_trick + '</span></div>') if memory_trick else ''
    related_block = ('<div style="margin-top:12px;font-size:0.72rem;color:#4A6080;">Study next: ' + related_html + '</div>') if related else ''
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0D1B35,#111929);
                border:1px solid {color}44;border-radius:16px;
                padding:24px 28px;margin:12px 0;position:relative;overflow:hidden;">
      <div style="position:absolute;top:0;left:0;right:0;height:3px;
                  background:linear-gradient(90deg,transparent,{color},transparent);">
      </div>
      <div style="font-family:Orbitron,monospace;font-size:0.65rem;color:{color};
                  letter-spacing:0.2em;text-transform:uppercase;margin-bottom:14px;">
        📋 {recap.get("title","Lesson Recap")}
      </div>
      {points_html}
      <div style="margin-top:14px;background:{color}11;border-radius:8px;
                  padding:10px 14px;border-left:3px solid {color};">
        <div style="font-size:0.65rem;color:{color};letter-spacing:0.1em;
                    text-transform:uppercase;margin-bottom:4px;">EXAM ANSWER</div>
        <div style="font-size:0.88rem;color:#E8F0FF;font-style:italic;">
          "{recap.get("exam_one_liner","")}"
        </div>
      </div>
      {memory_html}
      {related_block}
    </div>
    """, unsafe_allow_html=True)


# ── Session Summary ──────────────────────────────────────────────────────────

def render_session_summary(student_name: str, db, student_id: str,
                           subject: str) -> None:
    """Render a post-session performance summary card."""
    color = "#9B59B6"
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0D0020,#111929);
                border:1px solid {color}55;border-radius:16px;
                padding:24px 28px;margin:16px 0;position:relative;overflow:hidden;">
      <div style="position:absolute;top:0;left:0;right:0;height:3px;
                  background:linear-gradient(90deg,transparent,{color},transparent);"></div>
      <div style="font-family:Orbitron,monospace;font-size:0.65rem;color:{color};
                  letter-spacing:0.2em;text-transform:uppercase;margin-bottom:16px;">
        📊 SESSION SUMMARY · {student_name.upper() if student_name else "YOUR PROGRESS"}
      </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    # Topics covered this session
    memory = _get_lesson_memory()
    topics_today = [m["topic"] for m in memory] if memory else []

    # Weak concepts
    weak_items: list = []
    if db:
        try:
            weak_items = db.get_weak_concepts(student_id, resolved=False) or []
        except Exception:
            weak_items = []

    # Chapter scores
    scores: dict = {}
    if db:
        try:
            raw = db.get_chapter_scores_by_subject(student_id, subject) or {}
            scores = raw if isinstance(raw, dict) else {}
        except Exception:
            scores = {}

    strong_chapters = [ch for ch, sc in scores.items() if sc >= 70]
    weak_chapters   = [ch for ch, sc in scores.items() if sc < 50]

    with col1:
        st.markdown(f"""
        <div style="background:rgba(0,200,80,0.08);border:1px solid rgba(0,200,80,0.3);
                    border-radius:10px;padding:14px;min-height:120px;">
          <div style="font-size:0.6rem;color:#00C850;letter-spacing:0.15em;
                      text-transform:uppercase;margin-bottom:8px;">💪 Strong Areas</div>
        """, unsafe_allow_html=True)
        if strong_chapters:
            for ch in strong_chapters[:4]:
                st.markdown(f'<span style="display:inline-block;background:rgba(0,200,80,0.15);'
                            f'color:#00C850;border-radius:6px;padding:2px 8px;'
                            f'font-size:0.75rem;margin:2px;">{ch}</span>',
                            unsafe_allow_html=True)
        else:
            st.markdown('<span style="color:#4A6080;font-size:0.78rem;">Keep studying!</span>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.3);
                    border-radius:10px;padding:14px;min-height:120px;">
          <div style="font-size:0.6rem;color:#EF4444;letter-spacing:0.15em;
                      text-transform:uppercase;margin-bottom:8px;">⚠️ Needs Work</div>
        """, unsafe_allow_html=True)
        items_shown = 0
        for wc in weak_items[:4]:
            concept = wc.get("concept", "") if isinstance(wc, dict) else str(wc)
            if concept:
                st.markdown(f'<span style="display:inline-block;background:rgba(239,68,68,0.12);'
                            f'color:#EF4444;border-radius:6px;padding:2px 8px;'
                            f'font-size:0.75rem;margin:2px;">{concept}</span>',
                            unsafe_allow_html=True)
                items_shown += 1
        for ch in weak_chapters[:max(0, 4 - items_shown)]:
            st.markdown(f'<span style="display:inline-block;background:rgba(239,68,68,0.1);'
                        f'color:#FF8888;border-radius:6px;padding:2px 8px;'
                        f'font-size:0.75rem;margin:2px;">{ch}</span>',
                        unsafe_allow_html=True)
        if not weak_items and not weak_chapters:
            st.markdown('<span style="color:#4A6080;font-size:0.78rem;">No weak areas found!</span>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background:rgba(155,89,182,0.08);border:1px solid rgba(155,89,182,0.3);
                    border-radius:10px;padding:14px;min-height:120px;">
          <div style="font-size:0.6rem;color:{color};letter-spacing:0.15em;
                      text-transform:uppercase;margin-bottom:8px;">📚 Topics Today</div>
        """, unsafe_allow_html=True)
        if topics_today:
            for t in topics_today[-4:]:
                st.markdown(f'<span style="display:inline-block;background:rgba(155,89,182,0.15);'
                            f'color:#C39BD3;border-radius:6px;padding:2px 8px;'
                            f'font-size:0.75rem;margin:2px;">{t}</span>',
                            unsafe_allow_html=True)
        else:
            st.markdown('<span style="color:#4A6080;font-size:0.78rem;">No topics yet.</span>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ── Image Explainer (Gemma 4 Vision) ─────────────────────────────────────────

def render_image_explainer(student: dict, ollama_client) -> None:
    """Upload image of diagram/textbook page → explanation + exam questions via Gemma 4 vision."""
    st.markdown("### 📸 Explain This Diagram")
    st.caption("Point your camera at any diagram, textbook page, or handwritten notes")

    uploaded_img = st.file_uploader(
        "Upload image",
        type=["jpg", "jpeg", "png", "webp"],
        key="vt_image_upload",
        label_visibility="collapsed",
    )

    if uploaded_img:
        import base64
        import io

        try:
            from PIL import Image
        except ImportError:
            st.error("Install Pillow: pip install Pillow")
            return

        col1, col2 = st.columns([1, 2])
        with col1:
            img = Image.open(uploaded_img)
            max_size = 1024
            ratio = min(max_size / img.width, max_size / img.height)
            if ratio < 1:
                img = img.resize(
                    (int(img.width * ratio), int(img.height * ratio)),
                    Image.LANCZOS,
                )
            st.image(img, use_container_width=True)

        with col2:
            if st.button("🔍 Explain This", type="primary", key="btn_explain_image"):
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                img_b64 = base64.b64encode(buf.getvalue()).decode()

                with st.spinner("Dr. Omni is analysing the image..."):
                    import ollama as _ollama_lib
                    try:
                        resp = _ollama_lib.chat(
                            model="gemma4:e4b",
                            messages=[{
                                "role": "user",
                                "content": (
                                    f"You are a {student.get('subject', 'Computer Science')} lecturer. "
                                    f"Explain this diagram/image to a student. "
                                    f"Structure your response as:\n"
                                    f"WHAT THIS SHOWS: [one sentence]\n"
                                    f"KEY PARTS:\n1. [part]: [what it does]\n"
                                    f"2. [part]: [what it does]\n"
                                    f"3. [part]: [what it does]\n"
                                    f"THE PROCESS: [step by step]\n"
                                    f"EXAMINER WILL ASK:\n"
                                    f"1. [likely exam question]\n"
                                    f"2. [likely exam question]\n"
                                    f"MEMORY TIP: [one mnemonic]"
                                ),
                                "images": [img_b64],
                            }],
                            options={"num_ctx": 4096},
                        )
                        explanation = (
                            resp["message"]["content"]
                            if isinstance(resp, dict)
                            else resp.message.content
                        )
                        st.session_state["vt_img_explanation"] = explanation
                    except Exception as e:
                        st.error(f"Image analysis failed: {e}")

            if "vt_img_explanation" in st.session_state:
                st.markdown(st.session_state["vt_img_explanation"])
    else:
        st.markdown("""
        <div style="text-align:center;padding:40px 20px;
                    background:rgba(0,212,255,0.04);border:1px dashed rgba(0,212,255,0.2);
                    border-radius:12px;margin:16px 0;">
          <div style="font-size:2rem;margin-bottom:8px;">📸</div>
          <div style="color:#4A6080;font-size:0.85rem;">
            Upload a photo of any diagram, textbook page, or handwritten notes<br>
            Gemma 4's vision will explain it and generate exam questions
          </div>
        </div>
        """, unsafe_allow_html=True)


# ── Main render function ──────────────────────────────────────────────────────

def render_virtual_teacher_mode(student: dict, ollama_client, db, rag=None):
    """
    World-class Virtual Teacher mode.
    Progressive delivery + mid-lesson questions + diagrams + memory + recap.
    """
    subject    = student.get("subject", "Computer Science")
    student_id = student.get("student_id", "demo_001")
    language   = student.get("language",
                             student.get("preferred_language", "english"))
    name       = student.get("name", "Student")

    teacher = VirtualTeacher(ollama_client, db, rag)


    tab_teach, tab_image = st.tabs(["📖 Full Lesson", "📸 Explain Image"])
    with tab_image:
        render_image_explainer(student, ollama_client)
    with tab_teach:
        st.markdown("## 👩‍🏫 Virtual Teacher — Dr. Omni")
        st.caption(
            "World-class AI lecturer · Progressive lessons · Diagrams · "
            "Mid-lesson questions · Voice narration · Lesson memory"
        )

        memory = _get_lesson_memory()
        if memory:
            with st.expander(f"📚 Topics covered this session ({len(memory)})",
                             expanded=False):
                for m in reversed(memory):
                    st.markdown(f"**{m['topic']}**")
                    for pt in m.get("points", [])[:2]:
                        st.caption(f"• {pt}")

        render_avatar_teacher("", phase="greeting", emotion="neutral",
                              show_speech_controls=False)

        col1, col2 = st.columns([4, 1])
        with col1:
            topic = st.text_input(
                "What topic shall we cover today?",
                placeholder="e.g. Deadlock in Operating Systems",
                key="vt_topic_input",
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            start = st.button("🎓 Teach Me", type="primary",
                              disabled=not bool(topic.strip()),
                              use_container_width=True)

        if start:
            prog = st.progress(0)
            stat = st.empty()
            stat.markdown(
                '<div style="color:#00D4FF;font-family:Exo 2,sans-serif;'
                'font-size:0.9rem;padding:12px;">⬡ Dr. Omni is reading your materials...</div>',
                unsafe_allow_html=True
            )
            prog.progress(15)
            import time as _t
            _t.sleep(0.3)
            stat.markdown(
                '<div style="color:#FFB800;font-family:Exo 2,sans-serif;'
                'font-size:0.9rem;padding:12px;">⬡ Preparing your lesson on '
                + topic + '...</div>',
                unsafe_allow_html=True
            )
            prog.progress(40)
            lesson = teacher.teach(topic.strip(), subject, student_id, language)
            prog.progress(90)
            stat.markdown(
                '<div style="color:#00C850;font-family:Exo 2,sans-serif;'
                'font-size:0.9rem;padding:12px;">✓ Lesson ready!</div>',
                unsafe_allow_html=True
            )
            _t.sleep(0.4)
            prog.progress(100)
            prog.empty()
            stat.empty()
            st.session_state["vt_lesson"]       = lesson
            st.session_state["vt_topic"]        = topic.strip()
            st.session_state["vt_phase"]        = "hook"
            st.session_state["vt_mid_answered"] = False
            st.session_state["vt_mid_result"]   = None
            st.session_state["vt_answers"]      = {}
            st.session_state["vt_recap"]        = None
            st.session_state["vt_socratic"]     = None
            st.session_state.pop("vt_hint_level", None)
            st.rerun()

        lesson = st.session_state.get("vt_lesson")
        if not lesson:
            st.info("Enter a topic above and click **Teach Me** to begin.")
            return

        saved_topic = st.session_state.get("vt_topic", "")
        phase       = st.session_state.get("vt_phase", "hook")
        color       = "#00D4FF"

        st.markdown(f"### 📖 Lesson: **{saved_topic}**")
        st.markdown("---")

        # ── PHASE 1 — HOOK ──────────────────────────────────────────────────────
        hook = lesson.get("hook", "")
        render_avatar_teacher(hook, phase="teaching", emotion="encouraging")

        with st.expander("📖 Hook — Real-World Analogy", expanded=True):
            st.markdown(hook)

        if phase == "hook":
            if st.button("➡️ I understand — continue to explanation",
                         key="btn_hook_next"):
                st.session_state["vt_phase"] = "explanation"
                st.rerun()
            return

        # ── PHASE 2 — CORE EXPLANATION + DIAGRAM ────────────────────────────────
        explanation = lesson.get("explanation", "")

        with st.expander("🧠 Core Explanation", expanded=True):
            st.markdown(explanation)
            sources = lesson.get("_sources", [])
            if sources:
                st.caption("📎 From your notes: " + " | ".join(sources))

        has_rag = bool(lesson.get("_sources"))
        render_confidence_badge(
            source_type="grounded" if has_rag else "model",
            has_rag=has_rag,
        )

        diagram_code = lesson.get("_diagram", "")
        if diagram_code:
            render_mermaid_diagram(diagram_code,
                                   title=f"Visual Diagram: {saved_topic}")

        # ── MID-LESSON QUESTION ──────────────────────────────────────────────────
        mid_q = lesson.get("_mid_question", {})

        if mid_q and not st.session_state.get("vt_mid_answered"):
            st.markdown("---")
            mid_text = mid_q.get("question", "")
            render_avatar_teacher(mid_text, phase="questioning",
                                  emotion="thinking")

            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#001D0D,#0D1B35);
                        border:2px solid #00C85044;border-radius:12px;
                        padding:18px 22px;margin:8px 0;">
              <div style="font-size:0.6rem;color:#00C850;letter-spacing:0.15em;
                          text-transform:uppercase;margin-bottom:8px;">
                🛑 MID-LESSON CHECK — Answer before continuing
              </div>
              <div style="font-size:1rem;color:#E8F0FF;font-weight:600;">
                {mid_text}
              </div>
            </div>
            """, unsafe_allow_html=True)

            mid_answer = st.text_area(
                "Your answer",
                key="vt_mid_input",
                placeholder="Type your answer...",
                label_visibility="collapsed",
                height=80,
            )

            hint_level = st.session_state.get("vt_hint_level", 0)

            col_a, col_b, col_c = st.columns([2, 1, 1])
            with col_a:
                if st.button("✅ Submit Answer", key="btn_mid_submit",
                             type="primary"):
                    if mid_answer.strip():
                        with st.spinner("Dr. Omni is evaluating..."):
                            result = teacher.evaluate_check_answer(
                                question=mid_text,
                                student_answer=mid_answer,
                                topic=saved_topic,
                                student_id=student_id,
                                language=language,
                                expected_key_points=mid_q.get("expected", ""),
                                subject=subject,
                            )
                            if not result["correct"]:
                                socratic = teacher.get_socratic_followup(
                                    topic=saved_topic,
                                    question=mid_text,
                                    student_answer=mid_answer,
                                    expected=mid_q.get("expected", ""),
                                )
                            else:
                                socratic = None
                        st.session_state["vt_mid_result"]  = result
                        st.session_state["vt_socratic"]    = socratic
                        if result["correct"]:
                            st.session_state["vt_mid_answered"] = True
                        st.rerun()
                    else:
                        st.warning("Please write an answer first.")

            with col_b:
                if st.button("💡 Hint", key="btn_mid_hint"):
                    st.session_state["vt_hint_level"] = min(hint_level + 1, 3)
                    st.rerun()

            with col_c:
                if st.button("⏭ Skip", key="btn_mid_skip"):
                    st.session_state["vt_mid_answered"] = True
                    st.rerun()

            if hint_level >= 1:
                st.info(f"💡 Hint: {mid_q.get('hint','Think about the core concept.')}")
            if hint_level >= 2:
                st.info(f"💡 Bigger hint: Focus on: {mid_q.get('expected','the key points')}")

            mid_result = st.session_state.get("vt_mid_result")
            if mid_result:
                if mid_result["correct"]:
                    render_avatar_teacher(
                        f"Excellent! {mid_result['feedback']}",
                        phase="correct", emotion="happy",
                        student_name=name
                    )
                else:
                    socratic = st.session_state.get("vt_socratic", {}) or {}
                    render_avatar_teacher(
                        socratic.get("probing_question",
                                     mid_result["feedback"]),
                        phase="wrong", emotion="angry",
                        student_name=name
                    )
                    st.warning(
                        f"**{socratic.get('acknowledgement','')}**  \n"
                        f"🔍 {socratic.get('probing_question','')}  \n"
                        f"💭 *{socratic.get('nudge','')}*"
                    )

                    if st.button("✅ I understand now — continue",
                                 key="btn_mid_override"):
                        st.session_state["vt_mid_answered"] = True
                        st.rerun()
            return

        if mid_q and st.session_state.get("vt_mid_answered"):
            mid_result = st.session_state.get("vt_mid_result")
            if mid_result and mid_result.get("correct"):
                st.success(f"✅ Mid-lesson check passed! {mid_result.get('feedback','')}")
            elif mid_result:
                st.info("✅ Continuing lesson...")

        if phase in ("hook", "explanation"):
            st.session_state["vt_phase"] = "worked_example"

        # ── PHASE 3 — WORKED EXAMPLE ────────────────────────────────────────────
        with st.expander("⚙️ Worked Example — Step by Step", expanded=True):
            st.markdown(lesson.get("worked_example",
                                   "_No worked example generated._"))

        # ── PHASE 4 — EXAM HOOK ──────────────────────────────────────────────────
        with st.expander("🎯 What the Examiner Will Ask", expanded=False):
            render_avatar_teacher(
                "These are the most likely exam questions on this topic.",
                phase="teaching", emotion="encouraging",
                student_name=name
            )
            exam_hooks = lesson.get("exam_hook", [])
            if isinstance(exam_hooks, list):
                for i, item in enumerate(exam_hooks, 1):
                    st.markdown(f"""
                    <div style="display:flex;gap:12px;padding:8px 0;
                                border-bottom:1px solid rgba(0,212,255,0.1);">
                      <span style="color:#00D4FF;font-family:Orbitron,monospace;
                                   font-weight:700;flex-shrink:0;">Q{i}</span>
                      <span style="color:#C8D8F0;font-size:0.9rem;">{item}</span>
                    </div>
                    """, unsafe_allow_html=True)

        # ── PHASE 5 — COMPREHENSION CHECK ────────────────────────────────────────
        st.markdown("---")
        render_avatar_teacher(
            "Final check — answer these questions to complete the lesson.",
            phase="questioning", emotion="thinking",
            student_name=name
        )
        st.markdown("### ✅ Final Comprehension Check")

        check_qs = lesson.get("check_questions", [])
        if "vt_answers" not in st.session_state:
            st.session_state["vt_answers"] = {}
        if "vt_correct_streak" not in st.session_state:
            st.session_state["vt_correct_streak"] = 0
        if "vt_wrong_streak" not in st.session_state:
            st.session_state["vt_wrong_streak"] = 0

        all_done = True
        for i, cq in enumerate(check_qs):
            q_text   = cq.get("question", f"Question {i+1}")
            expected = cq.get("expected_key_points", "")
            key      = f"vt_final_{i}"

            # Late reply detector — mark when question was first shown
            ts_key = f"vt_q{i}_start"
            if ts_key not in st.session_state:
                st.session_state[ts_key] = time.time()

            st.markdown(f"""
            <div style="background:rgba(0,212,255,0.04);border-left:3px solid #00D4FF44;
                        padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;">
              <span style="color:#00D4FF;font-weight:700;">Q{i+1}. </span>
              <span style="color:#E8F0FF;">{q_text}</span>
            </div>
            """, unsafe_allow_html=True)

            if key not in st.session_state["vt_answers"]:
                all_done = False
                # Show nudge if student has been idle >120 s on this question
                elapsed = time.time() - st.session_state.get(ts_key, time.time())
                if elapsed > 120:
                    render_avatar_teacher(
                        "Still there? Take your time, but give it a try — even a rough answer helps!",
                        phase="wrong", emotion="angry",
                        student_name=name,
                    )
                answer = st.text_area(
                    "Answer", key=f"{key}_input",
                    label_visibility="collapsed",
                    placeholder="Type your answer here...",
                    height=80,
                )
                if st.button(f"Submit", key=f"{key}_btn", type="primary"):
                    if answer.strip():
                        with st.spinner("Marking..."):
                            result = teacher.evaluate_check_answer(
                                question=q_text,
                                student_answer=answer,
                                topic=saved_topic,
                                student_id=student_id,
                                language=language,
                                expected_key_points=expected,
                                subject=subject,
                            )
                        # Update streaks
                        if result.get("correct"):
                            st.session_state["vt_correct_streak"] += 1
                            st.session_state["vt_wrong_streak"] = 0
                        else:
                            st.session_state["vt_wrong_streak"] += 1
                            st.session_state["vt_correct_streak"] = 0
                        st.session_state["vt_answers"][key] = result
                        st.rerun()
                    else:
                        st.warning("Write your answer before submitting.")
            else:
                result = st.session_state["vt_answers"][key]
                if result.get("correct"):
                    render_avatar_teacher(
                        f"Correct! {result['feedback']}",
                        phase="correct", emotion="happy",
                        student_name=name
                    )
                    st.success(f"✅ {result['feedback']}")
                else:
                    render_avatar_teacher(
                        result["feedback"],
                        phase="wrong", emotion="angry",
                        student_name=name
                    )
                    st.error(f"❌ {result['feedback']}")
                    if result.get("weakness"):
                        st.warning(
                            f"⚠️ Added to weak areas: **{result['weakness']}**"
                        )

        # ── LESSON COMPLETE — RECAP + MEMORY ─────────────────────────────────────
        if all_done and check_qs:
            st.markdown("---")

            if not st.session_state.get("vt_recap"):
                if st.button("📋 Generate Lesson Recap", type="primary",
                             key="btn_recap"):
                    with st.spinner("Generating lesson recap..."):
                        recap = teacher.generate_recap(saved_topic, subject)
                    st.session_state["vt_recap"] = recap
                    _add_to_memory(saved_topic,
                                   recap.get("points", [])[:3])
                    st.rerun()
            else:
                recap = st.session_state["vt_recap"]
                render_avatar_teacher(
                    f"Excellent work! You've completed the lesson on {saved_topic}. "
                    f"Here's your recap card.",
                    phase="recap", emotion="excited",
                    student_name=name
                )
                render_lesson_recap(recap, color="#9B59B6")

                if db and st.button("💾 Save Lesson", key="btn_save"):
                    try:
                        lesson_data = {**lesson, "_recap": recap}
                        lid = db.save_lesson(
                            student_id=student_id,
                            topic=saved_topic,
                            subject=subject,
                            lesson_json=json.dumps(lesson_data,
                                                   ensure_ascii=False),
                        )
                        st.success(f"✅ Lesson saved! (ID: {lid[:8]})")
                    except Exception as e:
                        st.error(f"Could not save: {e}")

                if st.button("📖 Teach Me Another Topic", key="btn_new"):
                    for k in ["vt_lesson", "vt_topic", "vt_phase", "vt_mid_answered",
                              "vt_mid_result", "vt_answers", "vt_recap", "vt_socratic"]:
                        st.session_state.pop(k, None)
                    st.rerun()

                if st.button("📊 View Session Summary", key="btn_session_summary"):
                    render_session_summary(name, db, student_id, subject)
