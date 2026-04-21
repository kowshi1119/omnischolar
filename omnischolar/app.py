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
from rag import ingest_pdf, retrieve_context, get_retrieval_coverage
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
    COLORS,
)
from achievement import render_achievement_mode
from past_paper import render_past_paper_mode
from study_plan import render_study_plan_mode, get_todays_topic, build_schedule
from teacher import render_teacher_mode
from weakness import render_weakness_mode
from virtual_teacher import render_virtual_teacher_mode
from battle_game import render_battle_game_mode
from al_config import STREAM_SUBJECTS, STREAM_DEFAULT_SUBJECTS, STUDENT_TYPES
from achievement_3a import render_3a_achievement_mode

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

# All modes — THREE_A is filtered out for non-A/L students in the sidebar
MODES = [
    ("📚 Learn", "LEARN"),
    ("🔄 Revise", "REVISE"),
    ("🧪 Test Me", "TEST_ME"),
    ("🔍 Find Weak Areas", "FIND_WEAK_AREAS"),
    ("📅 Study Plan", "STUDY_PLAN"),
    ("🏆 3A Achievement", "THREE_A"),          # A/L only — filtered in sidebar
    ("📝 Past Paper Battle", "PAST_PAPER"),
    ("🗓️ Advanced Study Plan", "ADVANCED_STUDY_PLAN"),
    ("👩‍🏫 Teacher Mode", "TEACHER"),
    ("⚠️ Weakness Analysis", "WEAKNESS"),
    ("🤖 Virtual Teacher", "VIRTUAL_TEACHER"),
    ("⚔️ CS Battle", "BATTLE_GAME"),
]

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
        st.markdown("**Learning Mode**")
        _is_al = st.session_state.get("student_type", "Undergraduate") == "A/L Student"
        _visible_modes = [m for m in MODES if m[1] != "THREE_A" or _is_al]
        mode_labels = [m[0] for m in _visible_modes]
        mode_values = [m[1] for m in _visible_modes]
        _cur_mode = st.session_state["mode"]
        # If THREE_A was active but student switched to Undergraduate, fall back to LEARN
        if _cur_mode == "THREE_A" and not _is_al:
            _cur_mode = "LEARN"
            st.session_state["mode"] = _cur_mode
        _cur_idx = mode_values.index(_cur_mode) if _cur_mode in mode_values else 0
        _sel = st.radio("Select Mode", mode_labels, index=_cur_idx, key="_sb_mode", label_visibility="collapsed")
        _new_mode = mode_values[mode_labels.index(_sel)]
        if _new_mode != st.session_state["mode"]:
            st.session_state["mode"] = _new_mode
            st.session_state["chat_history"] = []
            st.rerun()
        st.divider()
        st.caption(f"Model: {OLLAMA_MODEL}")
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
        if st.session_state.get("rag_docs"):
            with st.spinner("Searching study materials..."):
                try:
                    # For A/L students, filter RAG by the active subject in their stream
                    _al_subjects = student.get("al_subjects") or []
                    _rag_subject = _al_subjects[0] if _al_subjects else student["subject"]
                    rag_context, _ = retrieve_context(prompt, subject=_rag_subject)
                except Exception:
                    rag_context = ""

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
                render_grounding_indicator()

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
        st.info(f"Today's focus: {todays_topic}")

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
    if not _check_ollama_connection():
        st.sidebar.error("⚠️ Ollama not responding on :11434")
        st.error("**Gemma 4 is not running.**\n\nOpen PowerShell and run:\n```\nollama serve\n```\nThen refresh this page.")
        return
    else:
        st.sidebar.success("✅ Ollama connected")
    student = _student()
    mode = st.session_state["mode"]

    # ── Language quick-toggle (visible in all modes) ──────────────────────
    lang_col1, lang_col2 = st.columns([8, 2])
    with lang_col2:
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
        elif mode == "STUDY_PLAN":
            render_study_plan_mode(student, db, _llm)
        elif mode == "THREE_A":
            if student.get("student_type") == "A/L Student":
                render_3a_achievement_mode(student, db, _llm)
            else:
                st.warning("The 3A Achievement module is available for A/L students only. Update your profile to A/L Student in the sidebar.")
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
