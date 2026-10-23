import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import uuid
from datetime import date, datetime, timedelta

import streamlit as st

st.set_page_config(
    page_title="OmniScholar",
    page_icon="&#x2B21;",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config import OLLAMA_MODEL
from database import Database, init_db, save_student, get_quiz_history
from ollama_client import OllamaClient
from rag import ingest_pdf, retrieve_context, retrieve_context_hybrid, get_confidence_score, get_retrieval_coverage
from prompt import SYSTEM_PROMPT
from ui_components import (
    inject_premium_css,
    render_grounding_indicator,
    render_thinking_state,
    render_welcome_banner,
    render_exam_readiness_hero,
    render_chapter_bars,
    render_urgency_countdown,
    render_gemma_badges,
    render_impact_counter,
    render_system_status,
    render_today_focus,
    render_ollama_status_chip,
    render_offline_seal,
    render_offline_confirmed_toast,
    COLORS,
)
from achievement import render_achievement_mode
from achievement_3a import render_3a_achievement_mode, calculate_readiness
from past_paper import render_past_paper_mode
from study_plan import render_study_plan_mode, get_todays_topic, build_schedule
from teacher import render_teacher_mode
from weakness import render_weakness_mode
from virtual_teacher import render_virtual_teacher_mode
from battle_game import render_battle_game_mode
from al_config import STREAM_SUBJECTS, STREAM_DEFAULT_SUBJECTS, STUDENT_TYPES

inject_premium_css()


def _safe_format(template: str, **kwargs) -> str:
    """Format a prompt template safely — only replaces known placeholders.

    Avoids Python str.format() interpreting raw `{ }` JSON examples in the
    template as format placeholders (which causes KeyError crashes).
    """
    result = template
    for key, val in kwargs.items():
        result = result.replace("{" + key + "}", str(val))
    return result


init_db()
db = Database()

if "_llm" not in st.session_state:
    st.session_state["_llm"] = OllamaClient()
_llm = st.session_state["_llm"]

# Primary modes — always visible in sidebar (THREE_A is a dedicated button)
_PRIMARY_MODES = [
    ("📖 Learn",           "LEARN"),
    ("🔄 Revise",          "REVISE"),
    ("📝 Test Me",         "TEST_ME"),
    ("🤖 Virtual Teacher", "VIRTUAL_TEACHER"),
]

# Secondary modes — under "⋯ Tools" expander
_SECONDARY_MODES = [
    ("🔍 Find Weak Areas",     "FIND_WEAK_AREAS"),
    ("📅 Study Plan",          "STUDY_PLAN"),
    ("📄 Past Paper Battle",   "PAST_PAPER"),
    ("⚔️  CS Battle",          "BATTLE_GAME"),
    ("👩‍🏫 Teacher Mode",      "TEACHER"),
    ("⚠️ Weakness Analysis",   "WEAKNESS"),
    ("🗓️ Advanced Study Plan", "ADVANCED_STUDY_PLAN"),
]

# Combined for internal dispatch (THREE_A handled via dedicated button)
MODES = _PRIMARY_MODES + _SECONDARY_MODES

_DELEGATED = {
    "THREE_A", "PAST_PAPER", "ADVANCED_STUDY_PLAN", "TEACHER",
    "WEAKNESS", "VIRTUAL_TEACHER", "BATTLE_GAME", "STUDY_PLAN",
}


def _init_session():
    defaults = {
        "student_id": str(uuid.uuid4()),
        "name": "Kowshi",
        "subject": "Computer Science",
        "exam_date": str(date.today() + timedelta(days=30)),
        "weak_areas": "",
        "preferred_language": "English",
        "student_type": "Undergraduate",
        "al_stream": "",
        "al_subjects": [],
        "mode": "LEARN",
        "chat_history": [],
        "rag_docs": [],
        "profile_saved": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # One-time hydration: restore saved profile so A/L settings survive restarts.
    if not st.session_state.get("_profile_hydrated", False):
        loaded = None
        _sid = st.session_state.get("student_id")
        if _sid:
            loaded = db.get_student_profile(_sid)
        if not loaded:
            loaded = db.get_latest_student_profile()

        if loaded:
            st.session_state["student_id"] = loaded.get("student_id") or st.session_state["student_id"]
            st.session_state["name"] = loaded.get("name") or st.session_state["name"]
            st.session_state["subject"] = loaded.get("subject") or st.session_state["subject"]
            st.session_state["exam_date"] = loaded.get("exam_date") or st.session_state["exam_date"]
            st.session_state["weak_areas"] = loaded.get("weak_areas") or st.session_state["weak_areas"]
            st.session_state["preferred_language"] = loaded.get("preferred_language") or st.session_state["preferred_language"]
            st.session_state["student_type"] = loaded.get("student_type") or st.session_state["student_type"]
            st.session_state["al_stream"] = loaded.get("al_stream") or st.session_state["al_stream"]
            _loaded_subjects = loaded.get("al_subjects") or []
            st.session_state["al_subjects"] = _loaded_subjects if isinstance(_loaded_subjects, list) else []

        st.session_state["_profile_hydrated"] = True


_init_session()


def _student():
    exam_date_str = st.session_state.get("exam_date", str(date.today() + timedelta(days=30)))
    try:
        exam_dt = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
    except Exception:
        exam_dt = date.today() + timedelta(days=30)
    days_remaining = max((exam_dt - date.today()).days, 1)
    return {
        "student_id": st.session_state["student_id"],
        "name": st.session_state["name"],
        "subject": st.session_state["subject"],
        "exam_date": exam_date_str,
        "days_remaining": days_remaining,
        "weak_areas": st.session_state.get("weak_areas", ""),
        "preferred_language": st.session_state.get("preferred_language", "English"),
        "student_type": st.session_state.get("student_type", "Undergraduate"),
        "al_stream": st.session_state.get("al_stream", ""),
        "al_subjects": st.session_state.get("al_subjects", []),
    }


def _render_system_status():
    render_system_status(ollama_ok=True)


def _render_sidebar():
    with st.sidebar:
        st.sidebar.markdown(
            '<div class="omni-header">⬡ OMNISCHOLAR</div>',
            unsafe_allow_html=True
        )
        st.sidebar.markdown(
            '<div class="omni-subtitle">OFFLINE · MULTILINGUAL · AI</div>',
            unsafe_allow_html=True
        )
        st.divider()
        st.markdown("**Profile**")
        st.session_state["name"] = st.text_input("Your Name", value=st.session_state["name"], key="_sb_name")
        st.session_state["subject"] = st.text_input("Subject", value=st.session_state["subject"], key="_sb_subject")
        try:
            _exam_val = datetime.strptime(st.session_state["exam_date"], "%Y-%m-%d").date()
        except Exception:
            _exam_val = date.today() + timedelta(days=30)
        st.session_state["exam_date"] = st.date_input("Exam Date", value=_exam_val, key="_sb_exam_date").strftime("%Y-%m-%d")
        st.session_state["weak_areas"] = st.text_area("Weak Areas (comma-separated)", value=st.session_state.get("weak_areas", ""), height=80, key="_sb_weak")
        st.session_state["preferred_language"] = st.selectbox(
            "Language", ["English", "Sinhala", "Tamil"],
            index=["English", "Sinhala", "Tamil"].index(st.session_state.get("preferred_language", "English")),
            key="_sb_lang",
        )

        # ── A/L Profile Fields ─────────────────────────────────────────────
        st.markdown("**Student Type**")
        _cur_stype = st.session_state.get("student_type", "Undergraduate")
        _stype_idx = STUDENT_TYPES.index(_cur_stype) if _cur_stype in STUDENT_TYPES else 1
        _new_stype = st.radio(
            "student_type_radio",
            STUDENT_TYPES,
            index=_stype_idx,
            key="_sb_student_type",
            label_visibility="collapsed",
            horizontal=True,
        )
        st.session_state["student_type"] = _new_stype

        if _new_stype == "A/L Student":
            _stream_options = list(STREAM_SUBJECTS.keys())
            _cur_stream = st.session_state.get("al_stream", "") or _stream_options[0]
            if _cur_stream not in _stream_options:
                _cur_stream = _stream_options[0]
            _new_stream = st.selectbox(
                "A/L Stream",
                _stream_options,
                index=_stream_options.index(_cur_stream),
                key="_sb_al_stream",
            )
            if _new_stream != st.session_state.get("al_stream", ""):
                st.session_state["al_stream"] = _new_stream
                st.session_state["al_subjects"] = list(
                    STREAM_DEFAULT_SUBJECTS.get(_new_stream, [])
                )
            else:
                st.session_state["al_stream"] = _new_stream

            _all_subjects = STREAM_SUBJECTS.get(_new_stream, [])
            _cur_subjects = st.session_state.get("al_subjects", [])
            if not isinstance(_cur_subjects, list):
                _cur_subjects = []
            _valid_defaults = [s for s in _cur_subjects if s in _all_subjects]
            _new_subjects = st.multiselect(
                "Subjects (select your 3)",
                _all_subjects,
                default=_valid_defaults,
                key="_sb_al_subjects",
            )
            st.session_state["al_subjects"] = _new_subjects
        else:
            # Undergraduate — clear A/L fields
            st.session_state["al_stream"] = ""
            st.session_state["al_subjects"] = []

        if st.button("Save Profile", use_container_width=True):
            s = _student()
            _al_subjects_json = json.dumps(s.get("al_subjects") or [])
            save_student({
                "student_id":         s["student_id"],
                "name":               s["name"],
                "subject":            s["subject"],
                "exam_date":          s["exam_date"],
                "preferred_language": s["preferred_language"],
                "weak_areas":         s.get("weak_areas", ""),
                "student_type":       s.get("student_type", "Undergraduate"),
                "al_stream":          s.get("al_stream", ""),
                "al_subjects":        _al_subjects_json,
            })
            st.session_state["profile_saved"] = True
            st.success("Profile saved!")
        st.divider()
        st.markdown("**Upload Study Materials**")
        pdfs = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True, key="_sb_pdfs")
        if pdfs:
            for pdf in pdfs:
                if pdf.name not in st.session_state.get("rag_docs", []):
                    with st.spinner(f"Ingesting {pdf.name}..."):
                        try:
                            _subj = st.session_state.get("subject", "General")
                            _lang = st.session_state.get("preferred_language", "English")
                            _al_stream = st.session_state.get("al_stream") or None
                            _al_subj = (st.session_state.get("al_subjects") or [None])[0] or None
                            ingest_pdf(pdf, _subj, _lang, al_stream=_al_stream, al_subject=_al_subj)
                            st.session_state["rag_docs"].append(pdf.name)
                        except Exception as e:
                            st.warning(f"Could not ingest {pdf.name}: {e}")
            db.update_student_pdf(st.session_state["student_id"], ",".join(st.session_state["rag_docs"]))
            if st.session_state["rag_docs"]:
                st.success(f"{len(st.session_state['rag_docs'])} PDF(s) loaded")
        st.divider()
        _render_system_status()
        _cur_mode = st.session_state["mode"]
        _PRIMARY_MODE_KEYS = [m[1] for m in _PRIMARY_MODES]

        # ── Section 1: STUDY ─────────────────────────────────────────────
        st.sidebar.markdown(
            '<div class="omni-section-label">── STUDY ──</div>',
            unsafe_allow_html=True,
        )

        for _label, _mode_val in _PRIMARY_MODES:
            _is_active = (st.session_state["mode"] == _mode_val)
            if st.sidebar.button(
                _label,
                key=f"nav_btn_{_mode_val}",
                use_container_width=True,
                type="primary" if _is_active else "secondary",
            ):
                if st.session_state["mode"] != _mode_val:
                    st.session_state["mode"] = _mode_val
                    st.session_state["chat_history"] = []
                    for _k in [
                        "vt_lesson", "vt_topic", "vt_phase",
                        "vt_mid_answered", "vt_answers",
                        "test_questions", "test_idx",
                        "battle_state", "pp_questions",
                    ]:
                        st.session_state.pop(_k, None)
                    st.rerun()

        # ── Section 2: MORE ──────────────────────────────────────────────
        st.sidebar.markdown(
            '<div class="omni-section-label">── MORE ──</div>',
            unsafe_allow_html=True,
        )

        _sec_modes = [m for m in _SECONDARY_MODES]
        _sec_mode_vals = [m[1] for m in _sec_modes]
        with st.sidebar.expander(
            "⋯ Tools",
            expanded=(st.session_state["mode"] in _sec_mode_vals),
        ):
            for _label, _mode_val in _sec_modes:
                _is_active = (st.session_state["mode"] == _mode_val)
                if st.button(
                    _label,
                    key=f"nav_btn_{_mode_val}",
                    use_container_width=True,
                    type="primary" if _is_active else "secondary",
                ):
                    if st.session_state["mode"] != _mode_val:
                        st.session_state["mode"] = _mode_val
                        st.session_state["chat_history"] = []
                        for _k in [
                            "vt_lesson", "vt_topic", "vt_phase",
                            "vt_mid_answered", "vt_answers",
                            "test_questions", "test_idx",
                            "battle_state", "pp_questions",
                        ]:
                            st.session_state.pop(_k, None)
                        st.rerun()

        # Active mode teal highlight via CSS
        _active_mode = st.session_state["mode"]
        st.sidebar.markdown(f"""
        <style>
        [data-testid="stSidebar"]
        [data-testid="stButton"][key="nav_btn_{_active_mode}"] > button {{
          border-color: #00B4A6 !important;
          color: #00B4A6 !important;
          background: rgba(0,180,166,0.1) !important;
        }}
        </style>
        """, unsafe_allow_html=True)

        # ── Section 3: A/L ACHIEVEMENT (conditional) ─────────────────────────
        _student_type_sb = st.session_state.get("student_type", "Undergraduate")

        if _student_type_sb == "A/L Student":
            # Gold gradient separator + section label
            st.sidebar.markdown("""
            <div style="
              height: 1px;
              background: linear-gradient(90deg,
                transparent, rgba(212,162,76,0.4), transparent);
              margin: 14px 0 10px;">
            </div>
            <div style="
              font-family: 'JetBrains Mono', monospace;
              font-size: 0.58rem;
              color: #3A5060;
              letter-spacing: 0.22em;
              text-transform: uppercase;
              padding: 0 4px 8px;
              display: flex;
              align-items: center;
              gap: 6px;">
              <span style="color:#D4A24C;">🏆</span>
              A/L ACHIEVEMENT
            </div>
            """, unsafe_allow_html=True)

            # Get quiz count for lock/unlock state
            _quiz_count = 0
            try:
                _qh_sb = db.get_quiz_history(
                    st.session_state.get("student_id", "")) or []
                _quiz_count = len(_qh_sb)
            except Exception:
                pass

            _is_unlocked = _quiz_count >= 3

            if _is_unlocked:
                if st.sidebar.button(
                    "🏆 3A Achievement Engine",
                    use_container_width=True,
                    help="Elo IRT readiness · DoE grade calibration",
                    key="btn_3a_achievement",
                ):
                    st.session_state["mode"] = "THREE_A"
                    st.session_state["chat_history"] = []
                    st.rerun()
                # Gold highlight when active
                if st.session_state.get("mode") == "THREE_A":
                    st.sidebar.markdown("""
                    <style>
                    [data-testid="stSidebar"]
                    [data-testid="stButton"]:last-of-type > button {
                      background: rgba(212,162,76,0.12) !important;
                      border-color: rgba(212,162,76,0.5) !important;
                      color: #D4A24C !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)
            else:
                # Locked — show progress toward unlock
                _needed = max(0, 3 - _quiz_count)
                st.sidebar.markdown(f"""
                <div style="
                  background: rgba(212,162,76,0.04);
                  border: 1px solid rgba(212,162,76,0.15);
                  border-radius: 10px;
                  padding: 10px 12px;
                  margin: 2px 0;">
                  <div style="
                    font-family: 'DM Sans', sans-serif;
                    font-size: 0.8rem;
                    color: #3A5060;
                    margin-bottom: 6px;">
                    🔒 3A Achievement Engine
                  </div>
                  <div style="
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.62rem;
                    color: #D4A24C;
                    opacity: 0.7;">
                    Complete {_needed} more quiz{"" if _needed == 1 else "zes"} to unlock
                  </div>
                  <div style="
                    height: 3px;
                    background: rgba(212,162,76,0.1);
                    border-radius: 2px;
                    margin-top: 8px;
                    overflow: hidden;">
                    <div style="
                      height: 100%;
                      width: {(_quiz_count / 3) * 100:.0f}%;
                      background: #D4A24C;
                      border-radius: 2px;">
                    </div>
                  </div>
                  <div style="
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.55rem;
                    color: #2A3A4A;
                    margin-top: 4px;
                    text-align: right;">
                    {_quiz_count}/3 quizzes
                  </div>
                </div>
                """, unsafe_allow_html=True)

        elif _student_type_sb == "Undergraduate":
            # Subtle separator + simple progress button (no 3A engine for UG)
            st.sidebar.markdown("""
            <div style="
              height: 1px;
              background: rgba(0,180,166,0.08);
              margin: 14px 0 10px;">
            </div>
            """, unsafe_allow_html=True)
            if st.sidebar.button(
                "📊 My Progress",
                use_container_width=True,
                help="View your study progress and readiness",
                key="btn_progress_ug",
            ):
                st.session_state["mode"] = "THREE_A"
                st.session_state["chat_history"] = []
                st.rerun()

        st.divider()
        st.sidebar.markdown(
            f'<div style="text-align:center;padding:6px;">'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:8px;'
            f'color:#1A3050;letter-spacing:0.12em;">'
            f'Model: {os.getenv("OLLAMA_MODEL", OLLAMA_MODEL)}</span></div>',
            unsafe_allow_html=True,
        )
        try:
            streak = db.get_study_streak(st.session_state["student_id"])
        except Exception:
            streak = 0
        if streak:
            st.markdown(f"**{streak}-day streak**")
        st.divider()
        with st.expander("⚙️ Demo Controls", expanded=False):
            if st.button("🔄 Reset Demo Data", key="btn_reset_demo"):
                import subprocess
                result = subprocess.run(
                    [sys.executable, "seed_demo_data.py"],
                    capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))
                )
                if result.returncode == 0:
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.success("Demo data reset! Reloading...")
                    st.rerun()
                else:
                    st.error(f"Reset failed: {result.stderr[:200]}")

            st.markdown("---")

            # Demo mode toggle
            demo_mode = st.checkbox(
                "🎬 Demo Mode",
                value=st.session_state.get("demo_mode", False),
                help="Optimize UI for video recording",
            )
            st.session_state["demo_mode"] = demo_mode

            if demo_mode:
                _subj = st.session_state.get("subject", "")
                _demo_topic = (
                    "Deadlock" if "computer" in _subj.lower() or "cs" in _subj.lower() else
                    "Cellular Respiration" if "biology" in _subj.lower() else
                    "Newton's Laws" if "physics" in _subj.lower() else
                    "Recursion"
                )
                st.info(f"🎬 Demo topic: **{_demo_topic}**")
                st.session_state["demo_topic"] = _demo_topic

            # WiFi Off simulation
            wifi_off = st.checkbox(
                "📵 Simulate WiFi Off",
                value=st.session_state.get("wifi_demo_off", False),
                help="Shows offline confirmation banner for demo",
            )
            st.session_state["wifi_demo_off"] = wifi_off

    # Dr. Omni greeting card — bottom of sidebar
    try:
        from _new_avatar import render_dr_omni_greeting_card
        _s = _student()
        _today_topic = (
            st.session_state.get("vt_topic")
            or st.session_state.get("demo_topic")
            or ""
        )
        _days = max(int(_s.get("days_remaining", 1)), 1)
        render_dr_omni_greeting_card(
            name=_s.get("name", "Student"),
            topic=_today_topic,
            days_left=_days,
            emotion="idle",
        )
    except Exception:
        pass  # Avatar never crashes the sidebar


def _build_system_prompt(student, context=""):
    base = _safe_format(
        SYSTEM_PROMPT,
        name=student["name"],
        subject=student["subject"],
        language=student["preferred_language"],
        weak_areas=student["weak_areas"] or "none specified",
        days_remaining=student["days_remaining"],
    )
    if context:
        base += f"\n\n[RETRIEVED CONTEXT]\n{context}"
    return base


def _handle_chat_mode(mode, student):
    cfg = {
        "LEARN": {
            "title": "Learn Mode",
            "subtitle": "Deep, structured explanations with examples",
            "placeholder": f"What topic in {student['subject']} would you like to learn?",
            "color": "#00D4FF",
        },
        "REVISE": {
            "title": "Revise Mode",
            "subtitle": "Quick summaries and key-point reinforcement",
            "placeholder": f"Which {student['subject']} topic should we revise?",
            "color": "#FFB800",
        },
    }[mode]

    st.markdown(f"<h2 style='color:{cfg['color']};'>{cfg['title']}</h2><p style='color:#A0B4D6;'>{cfg['subtitle']}</p>", unsafe_allow_html=True)

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(cfg["placeholder"]):
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        rag_context = ""
        rag_sources = []
        if st.session_state.get("rag_docs"):
            with st.spinner("Searching study materials..."):
                try:
                    # For A/L students, filter RAG by the active subject in their stream
                    _al_subjects = student.get("al_subjects") or []
                    _rag_subject = _al_subjects[0] if _al_subjects else student["subject"]
                    rag_context, rag_sources = retrieve_context_hybrid(prompt, subject=_rag_subject)
                except Exception:
                    rag_context = ""
                    rag_sources = []

        sys_prompt = _build_system_prompt(student, rag_context)
        messages = [{"role": "system", "content": sys_prompt}]
        for m in st.session_state["chat_history"][:-1]:
            messages.append(m)
        messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            render_thinking_state()
            placeholder = st.empty()
            full_response = ""
            try:
                for chunk in _llm.stream(messages):
                    full_response += chunk
                    placeholder.markdown(full_response + "...")
                placeholder.markdown(full_response)
            except Exception as e:
                full_response = f"Could not reach Ollama: {e}\n\nMake sure `ollama serve` is running with model `{OLLAMA_MODEL}`."
                placeholder.markdown(full_response)

            if rag_context:
                _conf = get_confidence_score(prompt, full_response, rag_sources)
                render_grounding_indicator(sources=rag_sources, level=_conf)

        st.session_state["chat_history"].append({"role": "assistant", "content": full_response})


def _handle_test_me(student):
    st.markdown("<h2 style='color:#A855F7;'>Test Me</h2><p style='color:#A0B4D6;'>Challenge yourself with AI-generated questions.</p>", unsafe_allow_html=True)
    topic = st.text_input("Topic to be tested on", placeholder=f"e.g. {student['subject']} Chapter 3", key="_tm_topic")
    num_q = st.slider("Number of questions", 3, 10, 5, key="_tm_num")
    if st.button("Generate Quiz", use_container_width=True):
        with st.spinner("Generating questions..."):
            prompt_text = (
                f"Create {num_q} multiple-choice quiz questions about '{topic}' "
                f"for a {student['subject']} student. "
                "Format each as:\nQ: ...\nA) ...\nB) ...\nC) ...\nD) ...\nAnswer: X"
            )
            try:
                quiz_text = _llm.chat([{"role": "system", "content": _build_system_prompt(student)}, {"role": "user", "content": prompt_text}])
            except Exception as e:
                quiz_text = f"Error: {e}"
        st.markdown(quiz_text)
        st.session_state["last_quiz"] = quiz_text
        st.session_state["last_quiz_topic"] = topic
    if "last_quiz" in st.session_state:
        st.divider()
        user_answers = st.text_area("Paste your answers (e.g. 1:A 2:C 3:B)", key="_tm_answers", height=80)
        if st.button("Check Answers", key="_tm_check"):
            with st.spinner("Evaluating..."):
                try:
                    feedback = _llm.chat([
                        {"role": "system", "content": _build_system_prompt(student)},
                        {"role": "user", "content": f"Quiz:\n{st.session_state['last_quiz']}\n\nStudent answers: {user_answers}\n\nScore and explain."},
                    ])
                except Exception as e:
                    feedback = f"Error: {e}"
            st.markdown(feedback)


def _handle_find_weak_areas(student):
    st.markdown("<h2 style='color:#F97316;'>Find Weak Areas</h2><p style='color:#A0B4D6;'>Diagnose your knowledge gaps.</p>", unsafe_allow_html=True)
    quiz_history = get_quiz_history(student["student_id"])
    weak_from_db = db.get_weak_concepts(student["student_id"])
    if weak_from_db:
        st.subheader("Known Weak Concepts")
        for w in weak_from_db:
            st.markdown(f"- **{w['concept']}** *(recorded {w['created_at'][:10]})*")
        st.divider()
    if st.button("Analyse My Weak Areas", use_container_width=True):
        history_summary = "\n".join([f"- {r[0]}: {r[1]}/{r[2]}" for r in quiz_history[:10]]) if quiz_history else "No quiz history yet."
        prompt_text = (
            f"Based on this quiz history for {student['subject']}:\n{history_summary}\n\n"
            f"Known weak areas from profile: {student['weak_areas'] or 'none'}\n\n"
            "Identify the top 5 weak areas and give specific revision advice for each."
        )
        with st.spinner("Analysing..."):
            try:
                analysis = _llm.chat([{"role": "system", "content": _build_system_prompt(student)}, {"role": "user", "content": prompt_text}])
            except Exception as e:
                analysis = f"Error: {e}"
        st.markdown(analysis)


def render_exam_countdown(days_remaining: int, subject: str = "") -> None:
    """Render a compact exam countdown banner."""
    render_urgency_countdown(days_remaining, subject)


def _render_dashboard(student):
    render_welcome_banner(student["name"])
    try:
        chapter_data = db.get_chapter_scores_by_subject(student["student_id"], student["subject"])
    except Exception:
        chapter_data = []
    scores = [c["score"] for c in chapter_data] if chapter_data else []
    overall = round(sum(scores) / len(scores), 1) if scores else 50.0
    # Upgrade to Elo-based readiness for A/L students
    _is_al_student = st.session_state.get("student_type", "Undergraduate") == "A/L Student"
    if _is_al_student:
        try:
            _qh = db.get_quiz_history(student["student_id"]) or []
            if len(_qh) < 3:
                raise ValueError("insufficient_data")
            _subj = (student.get("al_subjects") or ["General"])[0]
            _elo = calculate_readiness(_qh, _subj)
            overall = float(_elo.get("readiness_pct", overall))
        except Exception:
            pass  # fall back to chapter-score average
    try:
        streak = db.get_study_streak(student["student_id"])
    except Exception:
        streak = 0
    try:
        weak_concepts = db.get_weak_concepts(student["student_id"])
    except Exception:
        weak_concepts = []
    render_exam_readiness_hero(
        overall,
        student["days_remaining"],
        streak,
        len(weak_concepts),
        student["subject"],
    )
    render_exam_countdown(student["days_remaining"], student["subject"])
    if chapter_data:
        render_chapter_bars(chapter_data)
    todays_topic = get_todays_topic(student)
    if todays_topic:
        render_today_focus(topic=todays_topic, days_left=student["days_remaining"])

    # ── Gemma 4 Feature Badges ────────────────────────────────────────────
    render_gemma_badges()

    # ── Student Impact Counter ────────────────────────────────────────────
    try:
        streak = db.get_study_streak(student["student_id"]) or 0
        questions = len(get_quiz_history(student["student_id"]) or [])
        fixed = len(db.get_weak_concepts(student["student_id"], resolved=True) or [])
    except Exception:
        streak = questions = fixed = 0
    render_impact_counter(streak=streak, questions=questions, fixed=fixed)


def _check_ollama_connection() -> bool:
    """Return True if Ollama API is reachable."""
    try:
        import httpx
        return httpx.get("http://localhost:11434/api/tags", timeout=3).status_code == 200
    except Exception:
        try:
            import requests
            return requests.get("http://localhost:11434/api/tags", timeout=3).status_code == 200
        except Exception:
            return False


def main():
    _render_sidebar()
    _ollama_ok = _check_ollama_connection()
    if not _ollama_ok:
        st.sidebar.error("⚠️ Ollama not responding on :11434")
        st.error("**Gemma 4 is not running.**\n\nOpen PowerShell and run:\n```\nollama serve\n```\nThen refresh this page.")
        return
    else:
        st.sidebar.success("✅ Ollama connected")
    student = _student()
    mode = st.session_state["mode"]

    # ── Header: Ollama chip · reserved · language toggle ─────────────────
    render_offline_seal()
    header_col1, header_col2, header_col3 = st.columns([5, 3, 2])
    with header_col1:
        render_ollama_status_chip(
            connected=_ollama_ok,
            model=os.getenv("OLLAMA_MODEL", OLLAMA_MODEL)
        )
    with header_col2:
        pass  # Reserved
    with header_col3:
        _lang_options = {"English": "English", "Sinhala": "Sinhala", "Tamil": "Tamil"}
        _current_lang = student.get("preferred_language", "English")
        if _current_lang not in _lang_options:
            _current_lang = "English"
        _new_lang = st.selectbox(
            "🌐",
            options=list(_lang_options.keys()),
            index=list(_lang_options.keys()).index(_current_lang),
            key="lang_quick_toggle",
            label_visibility="visible",
        )
        if _new_lang != _current_lang:
            st.session_state["preferred_language"] = _new_lang
            save_student({**student, "preferred_language": _new_lang})
            st.rerun()

    # WiFi-off demo banner
    if st.session_state.get("wifi_demo_off", False):
        render_offline_confirmed_toast()

    try:
        if mode == "LEARN":
            _render_dashboard(student)
            st.divider()
            _handle_chat_mode("LEARN", student)
        elif mode == "REVISE":
            _render_dashboard(student)
            st.divider()
            _handle_chat_mode("REVISE", student)
        elif mode == "TEST_ME":
            _render_dashboard(student)
            st.divider()
            _handle_test_me(student)
        elif mode == "FIND_WEAK_AREAS":
            _render_dashboard(student)
            st.divider()
            _handle_find_weak_areas(student)
            # Improvement 3: always show model-knowledge grounding badge for Find Weak Areas
            render_grounding_indicator(sources=[], level="curriculum")
        elif mode == "STUDY_PLAN":
            render_study_plan_mode(student, db, _llm)
        elif mode == "THREE_A":
            student_type = st.session_state.get("student_type", "Undergraduate")

            if student_type != "A/L Student":
                # Undergraduate: simple progress dashboard + upgrade CTA
                _render_dashboard(student)
                st.markdown("""
                <div style="
                  background: rgba(212,162,76,0.05);
                  border: 1px solid rgba(212,162,76,0.15);
                  border-radius: 10px;
                  padding: 14px 18px;
                  margin-top: 16px;">
                  <div style="
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.62rem;
                    color: #D4A24C;
                    letter-spacing: 0.12em;
                    margin-bottom: 6px;">
                    💡 UPGRADE AVAILABLE
                  </div>
                  <div style="
                    font-family: 'DM Sans', sans-serif;
                    font-size: 0.88rem;
                    color: #8899AA;">
                    Switch to <strong style="color:#D4A24C;">A/L Student</strong>
                    profile to unlock the 3A Achievement Engine with Elo IRT
                    readiness scoring calibrated against Sri Lanka DoE 2022/2023
                    grade distributions.
                  </div>
                </div>
                """, unsafe_allow_html=True)
                return  # never render 3A content for undergraduates

            # A/L Student: check quiz minimum
            _qh = []
            try:
                _qh = db.get_quiz_history(student["student_id"]) or []
            except Exception:
                pass

            if len(_qh) < 3:
                st.markdown(f"""
                <div style="
                  text-align: center;
                  padding: 56px 32px;
                  max-width: 520px;
                  margin: 40px auto;">
                  <div style="font-size:4rem; margin-bottom:16px;">🏆</div>
                  <h2 style="
                    font-family: 'Fraunces', serif;
                    color: #D4A24C;
                    margin: 0 0 12px;">
                    3A Achievement Engine
                  </h2>
                  <p style="
                    color: #8899AA;
                    font-family: 'DM Sans', sans-serif;
                    font-size: 0.92rem;
                    max-width: 380px;
                    margin: 0 auto 20px;
                    line-height: 1.6;">
                    Complete at least 3 quizzes in Test Me mode to unlock your
                    personalised Elo IRT readiness score — calibrated against
                    Sri Lanka DoE 2022/2023 grade distributions.
                  </p>
                  <div style="
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 0.75rem;
                    color: #D4A24C;
                    margin-bottom: 24px;">
                    {len(_qh)}/3 quizzes completed
                  </div>
                </div>
                """, unsafe_allow_html=True)
                col_l, col_btn, col_r = st.columns([1, 2, 1])
                with col_btn:
                    if st.button(
                        "📝 Start Quiz in Test Me →",
                        type="primary",
                        use_container_width=True,
                        key="_three_a_goto_test",
                    ):
                        st.session_state["mode"] = "TEST_ME"
                        st.rerun()
            else:
                render_3a_achievement_mode(student, db, _llm)
        elif mode == "PAST_PAPER":
            render_past_paper_mode(student, db, _llm)
        elif mode == "ADVANCED_STUDY_PLAN":
            render_study_plan_mode(student, db, _llm)
        elif mode == "TEACHER":
            render_teacher_mode(student, db, _llm)
        elif mode == "WEAKNESS":
            render_weakness_mode(student, db, _llm)
        elif mode == "VIRTUAL_TEACHER":
            render_virtual_teacher_mode(student, _llm, db)
        elif mode == "BATTLE_GAME":
            render_battle_game_mode(student, _llm, db)
        else:
            st.error(f"Unknown mode: {mode}")
    except Exception as _mode_err:
        st.error(f"⚠️ Mode error: {_mode_err}")
        st.code(str(_mode_err))
        import traceback
        st.text(traceback.format_exc())


main()
