import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import re
import threading
import uuid
from datetime import date, datetime, timedelta

import streamlit as st

st.set_page_config(
    page_title="OmniScholar",
    page_icon=":material/school:",
    layout="wide",
    initial_sidebar_state="auto",  # collapsed on phones, open on desktop
)

import nav
from config import APP_DEBUG, OLLAMA_HOST, OLLAMA_MODEL
from database import Database, init_db, save_student, save_quiz_result, get_quiz_history
from ollama_client import OllamaClient
from rag import ingest_pdf, retrieve_context_hybrid, get_confidence_score, get_retrieval_coverage
from prompt import SYSTEM_PROMPT
from ui_components import (
    inject_premium_css,
    render_grounding_indicator,
    render_welcome_banner,
    render_exam_readiness_hero,
    render_chapter_bars,
    render_urgency_countdown,
    render_today_focus,
    render_offline_seal,
)
from achievement_3a import render_3a_achievement_mode, calculate_readiness
from past_paper import render_past_paper_mode
from study_plan import render_study_plan_mode, get_todays_topic
from teacher import render_teacher_mode
from weakness import render_weakness_mode
from virtual_teacher import render_virtual_teacher_mode
from battle_game import render_battle_game_mode
from al_config import STREAM_SUBJECTS, STREAM_DEFAULT_SUBJECTS, STUDENT_TYPES

inject_premium_css()
st.logo(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "logo.svg"), size="large")


def _safe_format(template: str, **kwargs) -> str:
    """Format a prompt template safely — only replaces known placeholders.

    Avoids Python str.format() interpreting raw `{ }` JSON examples in the
    template as format placeholders (which causes KeyError crashes).
    """
    result = template
    for key, val in kwargs.items():
        result = result.replace("{" + key + "}", str(val))
    return result


@st.cache_resource
def _get_db() -> Database:
    # Schema migrations run once per server process, not on every rerun
    init_db()
    return Database()


@st.cache_resource
def _get_llm() -> OllamaClient:
    llm = OllamaClient()
    # Load the model into RAM in the background so the first answer isn't a cold start
    threading.Thread(target=llm.warmup, daemon=True).start()
    return llm


db = _get_db()
_llm = _get_llm()

# Navigation registry: (title, mode key). Keys are what modules pass to nav.go().
_PRIMARY_MODES = [
    ("Home",            "HOME"),
    ("Learn",           "LEARN"),
    ("Revise",          "REVISE"),
    ("Test Me",         "TEST_ME"),
    ("Virtual Teacher", "VIRTUAL_TEACHER"),
]

_SECONDARY_MODES = [
    ("Past Papers",  "PAST_PAPER"),
    ("CS Battle",    "BATTLE_GAME"),
    ("Weak Areas",   "WEAKNESS"),
    ("Study Plan",   "STUDY_PLAN"),
    ("Teacher Mode", "TEACHER"),
]

_ICONS = {
    "HOME": "home", "LEARN": "school", "REVISE": "autorenew", "TEST_ME": "quiz",
    "VIRTUAL_TEACHER": "smart_toy", "PAST_PAPER": "description", "BATTLE_GAME": "bolt",
    "WEAKNESS": "troubleshoot", "STUDY_PLAN": "calendar_month", "TEACHER": "co_present",
    "THREE_A": "emoji_events", "NOTES": "folder_open", "SETTINGS": "settings",
}

_LANGUAGES = ["English", "Sinhala", "Tamil"]


def _init_session():
    defaults = {
        "student_id": str(uuid.uuid4()),
        "name": "Student",
        "subject": "Computer Science",
        "exam_date": str(date.today() + timedelta(days=30)),
        "weak_areas": "",
        "preferred_language": "English",
        "student_type": "Undergraduate",
        "al_stream": "",
        "al_subjects": [],
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
            st.session_state["profile_saved"] = True
            st.session_state["student_id"] = loaded.get("student_id") or st.session_state["student_id"]
            st.session_state["name"] = loaded.get("name") or st.session_state["name"]
            st.session_state["subject"] = loaded.get("subject") or st.session_state["subject"]
            st.session_state["exam_date"] = loaded.get("exam_date") or st.session_state["exam_date"]
            st.session_state["weak_areas"] = loaded.get("weak_areas") or st.session_state["weak_areas"]
            # DB rows may hold lowercase defaults like "english"
            _lang = (loaded.get("preferred_language") or "English").title()
            st.session_state["preferred_language"] = _lang if _lang in _LANGUAGES else "English"
            st.session_state["student_type"] = loaded.get("student_type") or st.session_state["student_type"]
            st.session_state["al_stream"] = loaded.get("al_stream") or st.session_state["al_stream"]
            _loaded_subjects = loaded.get("al_subjects") or []
            st.session_state["al_subjects"] = _loaded_subjects if isinstance(_loaded_subjects, list) else []
            # Restore indexed-PDF list so RAG keeps working after a restart
            _pdfs = db.get_student_pdf(st.session_state["student_id"])
            st.session_state["rag_docs"] = [p for p in _pdfs.split(",") if p] if _pdfs else []

        st.session_state["_profile_hydrated"] = True


_init_session()


def _exam_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return date.today() + timedelta(days=30)


def _student():
    exam_date_str = st.session_state.get("exam_date", str(date.today() + timedelta(days=30)))
    days_remaining = max((_exam_date(exam_date_str) - date.today()).days, 1)
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


def _save_profile() -> None:
    s = _student()
    save_student({**s, "al_subjects": json.dumps(s.get("al_subjects") or [])})
    st.session_state["profile_saved"] = True


@st.cache_data(ttl=60, show_spinner=False)
def _progress(student_id: str, subject: str) -> dict:
    """All dashboard numbers in one place (was ~10 DB round-trips per rerun).

    Cleared via _progress.clear() whenever a quiz is saved.
    """
    def _safe(fn, default):
        try:
            return fn()
        except Exception:
            return default

    return {
        "history": _safe(lambda: get_quiz_history(student_id) or [], []),
        "streak": _safe(lambda: db.get_study_streak(student_id) or 0, 0),
        "weak": _safe(lambda: db.get_weak_concepts(student_id) or [], []),
        "resolved": _safe(lambda: db.get_weak_concepts(student_id, resolved=True) or [], []),
        "chapters": _safe(lambda: db.get_chapter_scores_by_subject(student_id, subject) or [], []),
    }


# ── Profile dialog ────────────────────────────────────────────────────────────

@st.dialog("Your profile")
def _profile_dialog():
    st.caption("Used to personalise explanations, quizzes and your study plan.")
    name = st.text_input("Your name", value=st.session_state["name"])
    subject = st.text_input("Main subject", value=st.session_state["subject"])
    exam_date = st.date_input("Exam date", value=_exam_date(st.session_state["exam_date"]),
                              min_value=date.today())
    weak = st.text_area("Topics you find hard (comma-separated)",
                        value=st.session_state.get("weak_areas", ""), height=80)
    _cur_type = st.session_state.get("student_type", "Undergraduate")
    student_type = st.radio("I am a", STUDENT_TYPES, horizontal=True,
                            index=STUDENT_TYPES.index(_cur_type) if _cur_type in STUDENT_TYPES else 1)

    al_stream, al_subjects = "", []
    if student_type == "A/L Student":
        streams = list(STREAM_SUBJECTS.keys())
        cur = st.session_state.get("al_stream") or streams[0]
        al_stream = st.selectbox("A/L stream", streams, index=streams.index(cur) if cur in streams else 0)
        options = STREAM_SUBJECTS.get(al_stream, [])
        current = [s for s in (st.session_state.get("al_subjects") or []) if s in options]
        al_subjects = st.multiselect("Your three subjects", options,
                                     default=current or STREAM_DEFAULT_SUBJECTS.get(al_stream, []),
                                     max_selections=3)

    if st.button("Save profile", type="primary", width="stretch"):
        if not name.strip() or not subject.strip():
            st.error("Name and subject are required.")
            return
        st.session_state.update({
            "name": name.strip(), "subject": subject.strip(),
            "exam_date": exam_date.strftime("%Y-%m-%d"), "weak_areas": weak.strip(),
            "student_type": student_type, "al_stream": al_stream, "al_subjects": al_subjects,
        })
        _save_profile()
        _progress.clear()
        st.toast("Profile saved", icon=":material/check_circle:")
        st.rerun()


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _render_sidebar(ollama_ok: bool):
    s = _student()
    with st.sidebar:
        with st.container(border=True):
            st.markdown(f"**{s['name']}**  \n{s['subject']}")
            exam = _exam_date(s["exam_date"])
            if exam < date.today():
                st.caption(":orange[Exam date has passed — update it in your profile]")
            else:
                st.caption(f"{(exam - date.today()).days} days to exam · {exam:%d %b %Y}")
            if st.button("Edit profile", icon=":material/edit:", width="stretch", key="btn_edit_profile"):
                _profile_dialog()

        # Language is a widget bound to session state; saving on change keeps it across restarts
        st.segmented_control(
            "Answer language", _LANGUAGES, key="preferred_language", required=True,
            on_change=_save_profile, width="stretch",
        )

        streak = _progress(s["student_id"], s["subject"])["streak"]
        if streak:
            st.caption(f":material/local_fire_department: {streak}-day study streak")

        model = st.session_state.get("ollama_model", OLLAMA_MODEL)
        if ollama_ok:
            st.caption(f":green[●] {model} · running locally")
        else:
            st.caption(":red[●] AI model offline · start `ollama serve`")

    # First visit: ask for a profile once instead of showing the defaults
    if not st.session_state.get("profile_saved") and not st.session_state.get("_onboarded"):
        st.session_state["_onboarded"] = True
        _profile_dialog()


# ── LLM prompt building ───────────────────────────────────────────────────────

def _build_system_prompt(student, context="", mode=""):
    base = _safe_format(
        SYSTEM_PROMPT,
        name=student["name"],
        subject=student["subject"],
        language=student["preferred_language"],
        weak_areas=student["weak_areas"] or "none specified",
        days_remaining=student["days_remaining"],
    )
    # SYSTEM_PROMPT expects the profile as JSON and a [MODE:] tag per turn
    profile = {k: student.get(k) for k in (
        "name", "subject", "preferred_language", "weak_areas", "days_remaining",
        "student_type", "al_stream", "al_subjects",
    )}
    base += f"\n\nSTUDENT PROFILE:\n{json.dumps(profile, ensure_ascii=False)}"
    if mode:
        base += f"\n\n[MODE: {mode}]"
    if context:
        base += (
            "\n\n[RETRIEVED CONTEXT]\nEach passage starts with its [file page N] label. "
            "Cite facts from it with that label. If the passages don't answer the "
            f"question, say it is not in the student's notes.\n\n{context}"
        )
    return base


# Older turns beyond this are dropped: they overflow the 4K context and slow every answer
_CHAT_HISTORY_TURNS = 8


def _handle_chat_mode(mode, student):
    cfg = {
        "LEARN": {
            "title": "Learn",
            "subtitle": "Structured explanations with examples, memory tips and citations from your notes.",
            "placeholder": f"What topic in {student['subject']} would you like to learn?",
        },
        "REVISE": {
            "title": "Revise",
            "subtitle": "Examiner-ready summaries and the mistakes students usually make.",
            "placeholder": f"Which {student['subject']} topic should we revise?",
        },
    }[mode]
    history_key = f"chat_{mode}"
    history = st.session_state.setdefault(history_key, [])

    head, action = st.columns([5, 1], vertical_alignment="bottom")
    head.title(cfg["title"])
    head.caption(cfg["subtitle"])
    if history and action.button("New chat", icon=":material/add_comment:", key=f"clear_{mode}"):
        history.clear()
        st.rerun()

    if not history:
        if st.session_state.get("rag_docs"):
            st.info(f"Answers will cite your {len(st.session_state['rag_docs'])} uploaded document(s).",
                    icon=":material/menu_book:")
        else:
            st.info("Tip: upload your lecture notes in **My Notes** so answers cite your own material.",
                    icon=":material/lightbulb:")

    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(cfg["placeholder"]):
        history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        rag_context, rag_sources = "", []
        if st.session_state.get("rag_docs"):
            with st.spinner("Searching your notes..."):
                try:
                    # For A/L students, filter RAG by the active subject in their stream
                    _al_subjects = student.get("al_subjects") or []
                    if _al_subjects:
                        rag_context, rag_sources = retrieve_context_hybrid(prompt, al_subject=_al_subjects[0])
                    else:
                        rag_context, rag_sources = retrieve_context_hybrid(prompt, subject=student["subject"])
                except Exception:
                    rag_context, rag_sources = "", []

        messages = [{"role": "system", "content": _build_system_prompt(student, rag_context, mode=mode)}]
        messages.extend(history[-_CHAT_HISTORY_TURNS - 1:-1])
        messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            full_response = st.write_stream(_llm.stream(messages))
            if rag_context:
                _conf = get_confidence_score(prompt, full_response, rag_sources, context=rag_context)
                render_grounding_indicator(sources=rag_sources, level=_conf)

        history.append({"role": "assistant", "content": full_response})


# ── Test Me ───────────────────────────────────────────────────────────────────

_LLM_ERROR_PREFIX = "[OmniScholar]"

# Matches the fine-tuned model's TEST_ME schema, plus an explanation for instant feedback
_QUIZ_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_text": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4},
                    "correct_answer": {"type": "string", "enum": ["A", "B", "C", "D"]},
                    "explanation": {"type": "string"},
                },
                "required": ["question_text", "options", "correct_answer", "explanation"],
            },
        }
    },
    "required": ["questions"],
}


def _score_quiz(quiz_text: str, user_answers: str) -> tuple:
    """Score answers like "1:A 2:C" against the quiz's answer key.

    Returns (correct, total); total is 0 when no answer key could be parsed.
    """
    key = [q["answer"] for q in _parse_quiz(quiz_text) or []] or re.findall(
        r"Answer\s*[:\-]\s*\**\s*\(?([A-D])\b", quiz_text, re.IGNORECASE
    )
    given = {
        int(n): letter.upper()
        for n, letter in re.findall(r"(\d+)\s*[:.)\-=]?\s*\(?([A-Da-d])\b", user_answers)
    }
    correct = sum(1 for i, ans in enumerate(key, start=1) if given.get(i) == ans.upper())
    return correct, len(key)


def _parse_quiz(quiz_text: str):
    """Parse the model's TEST_ME JSON into questions, or None if it isn't JSON."""
    match = re.search(r"\{.*\}", quiz_text, re.DOTALL)
    if not match:
        return None
    try:
        questions = json.loads(match.group(0)).get("questions") or []
    except (ValueError, AttributeError):
        return None
    return [
        {
            # The model often numbers questions itself ("Q1: ..."); the UI adds its own numbers
            "text": re.sub(r"^\s*Q?\d+\s*[:.)]\s*", "", q.get("question_text", "")),
            "options": q.get("options") or [],
            "answer": str(q.get("correct_answer", "")).strip()[:1].upper(),
            "explanation": q.get("explanation", ""),
        }
        for q in questions if isinstance(q, dict)
    ] or None


def _quiz_markdown(quiz_text: str) -> str:
    """Quiz as the student should see it: readable, with the answer key hidden."""
    questions = _parse_quiz(quiz_text)
    if questions:
        return "\n\n".join(
            f"**{i}. {q['text']}**\n\n" + "\n".join(f"- {o}" for o in q["options"])
            for i, q in enumerate(questions, start=1)
        )
    return re.sub(r"(?im)^\s*\**\s*Answer\s*[:\-].*$", "", quiz_text)


def _option_letter(option: str, index: int) -> str:
    """'B. Stack' -> 'B'; falls back to position when the model omits the letter."""
    m = re.match(r"\s*\(?([A-Da-d])[.):]\s", option)
    return m.group(1).upper() if m else "ABCD"[index]


def _handle_test_me(student):
    st.title("Test Me")
    st.caption("Retrieval practice: answer from memory, then see why each answer is right.")

    with st.form("tm_setup", border=True):
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        topic = c1.text_input("Topic", placeholder=f"e.g. {student['subject']} — recursion")
        num_q = c2.number_input("Questions", min_value=3, max_value=10, value=5)
        generate = st.form_submit_button("Generate quiz", type="primary", icon=":material/bolt:")

    if generate:
        topic = topic.strip() or student["subject"]
        with st.spinner(f"Writing {num_q} questions on {topic}..."):
            raw = _llm.chat(
                [{"role": "user", "content": (
                    f"Write {num_q} multiple-choice questions about '{topic}' for a "
                    f"{student['subject']} student preparing for an exam. Options start with "
                    "'A. ', 'B. ', 'C. ', 'D. '. Give a one-sentence explanation of the correct answer."
                )}],
                system_prompt=_build_system_prompt(student),
                temperature=0.4,
                format=_QUIZ_SCHEMA,
            )
        questions = None if raw.startswith(_LLM_ERROR_PREFIX) else _parse_quiz(raw)
        if not questions:
            st.error("Couldn't generate a quiz — the local model didn't respond. "
                     "Check that Ollama is running, then try again.")
            if APP_DEBUG:
                st.code(raw)
        else:
            st.session_state["tm_quiz"] = {"topic": topic, "questions": questions[:num_q], "saved": False}
            for k in [k for k in st.session_state if k.startswith("tm_q_")]:
                del st.session_state[k]

    quiz = st.session_state.get("tm_quiz")
    if not quiz:
        st.info("Pick a topic and generate a quiz. Results feed your streak, readiness and weak areas.",
                icon=":material/quiz:")
        return

    st.subheader(quiz["topic"])
    with st.form("tm_answers"):
        for i, q in enumerate(quiz["questions"]):
            st.radio(f"**{i + 1}.** {q['text']}", q["options"], index=None, key=f"tm_q_{i}")
        submitted = st.form_submit_button("Check answers", type="primary", icon=":material/fact_check:")

    if not submitted and not quiz["saved"]:
        return
    picks = [st.session_state.get(f"tm_q_{i}") for i in range(len(quiz["questions"]))]
    if submitted and None in picks:
        st.warning(f"Answer all {len(picks)} questions first.")
        return

    correct = 0
    for i, (q, pick) in enumerate(zip(quiz["questions"], picks)):
        chosen = _option_letter(pick, q["options"].index(pick)) if pick in q["options"] else None
        ok = chosen == q["answer"]
        correct += ok
        with st.container(border=True):
            st.markdown(f"{':green[:material/check_circle:]' if ok else ':red[:material/cancel:]'} "
                        f"**{i + 1}. {q['text']}**")
            if not ok:
                right = next((o for j, o in enumerate(q["options"]) if _option_letter(o, j) == q["answer"]),
                             q["answer"])
                st.markdown(f"Correct answer: **{right}**")
            if q.get("explanation"):
                st.caption(q["explanation"])

    total = len(quiz["questions"])
    st.metric("Score", f"{correct}/{total}", f"{round(100 * correct / total)}%")
    # Guard against double-saving on reruns
    if not quiz["saved"]:
        save_quiz_result(student["student_id"], quiz["topic"], correct, total, subject=student["subject"])
        if correct < total:
            db.upsert_weak_concept(student["student_id"], quiz["topic"], topic=quiz["topic"],
                                   subject=student["subject"])
        quiz["saved"] = True
        _progress.clear()
        st.toast("Result saved to your progress", icon=":material/check_circle:")


def _handle_find_weak_areas(student):
    st.subheader("AI weak-area analysis")
    st.caption("Reads your recent quiz results and suggests what to revise first.")
    if st.button("Analyse my weak areas", icon=":material/psychology:"):
        quiz_history = _progress(student["student_id"], student["subject"])["history"]
        history_summary = "\n".join(f"- {r[0]}: {r[1]}/{r[2]}" for r in quiz_history[:10]) or "No quiz history yet."
        prompt_text = (
            f"Based on this quiz history for {student['subject']}:\n{history_summary}\n\n"
            f"Known weak areas from profile: {student['weak_areas'] or 'none'}\n\n"
            "Identify the top 5 weak areas and give specific revision advice for each."
        )
        with st.chat_message("assistant"):
            st.write_stream(_llm.stream([
                {"role": "system", "content": _build_system_prompt(student, mode="FIND_WEAK_AREAS")},
                {"role": "user", "content": prompt_text},
            ]))


# ── Dashboard ─────────────────────────────────────────────────────────────────

def _render_dashboard(student):
    render_welcome_banner(student["name"])
    stats = _progress(student["student_id"], student["subject"])
    chapter_data = stats["chapters"]
    scores = [c["score"] for c in chapter_data]
    overall = round(sum(scores) / len(scores), 1) if scores else 0.0
    # Upgrade to Elo-based readiness for A/L students
    if student.get("student_type") == "A/L Student" and len(stats["history"]) >= 3:
        try:
            _subj = (student.get("al_subjects") or ["General"])[0]
            overall = float(calculate_readiness(stats["history"], _subj).get("readiness_pct", overall))
        except Exception:
            pass  # fall back to chapter-score average
    render_exam_readiness_hero(overall, student["days_remaining"], stats["streak"],
                               len(stats["weak"]), student["subject"])
    render_urgency_countdown(student["days_remaining"], student["subject"])
    if chapter_data:
        render_chapter_bars(chapter_data)
    todays_topic = get_todays_topic(student)
    if todays_topic:
        render_today_focus(topic=todays_topic, days_left=student["days_remaining"])
    c1, c2 = st.columns(2)
    c1.metric("Quizzes completed", len(stats["history"]))
    c2.metric("Weak areas resolved", len(stats["resolved"]))


@st.cache_data(ttl=15, show_spinner=False)
def _check_ollama_connection() -> bool:
    """Return True if Ollama API is reachable (cached briefly to keep reruns fast)."""
    try:
        import httpx
        return httpx.get(f"{OLLAMA_HOST.rstrip('/')}/api/version", timeout=3).status_code == 200
    except Exception:
        return False


# ── Pages ─────────────────────────────────────────────────────────────────────

def _page_home():
    student = _student()
    _render_dashboard(student)
    st.subheader("Jump back in")
    cols = st.columns(3)
    for col, key, blurb in zip(cols, ("LEARN", "TEST_ME", "VIRTUAL_TEACHER"), (
        "Ask anything about your subject",
        "A quick quiz to lock it in",
        "A guided lesson with Dr. Omni",
    )):
        with col.container(border=True):
            st.page_link(nav.PAGES[key], icon=f":material/{_ICONS[key]}:")
            st.caption(blurb)


def _page_learn():
    _handle_chat_mode("LEARN", _student())


def _page_revise():
    _handle_chat_mode("REVISE", _student())


def _page_test_me():
    _handle_test_me(_student())


def _page_virtual_teacher():
    render_virtual_teacher_mode(_student(), _llm, db)


def _page_past_paper():
    render_past_paper_mode(_student(), db, _llm)


def _page_battle():
    render_battle_game_mode(_student(), _llm, db)


def _page_weakness():
    student = _student()
    render_weakness_mode(student, db, _llm)
    st.divider()
    _handle_find_weak_areas(student)


def _page_study_plan():
    render_study_plan_mode(_student(), db, _llm)


def _page_teacher():
    render_teacher_mode(_student(), db, _llm)


def _page_progress():
    student = _student()
    if student.get("student_type") != "A/L Student":
        st.title("My Progress")
        _render_dashboard(student)
        st.info("Switch your profile to **A/L Student** to unlock the 3A Achievement Engine: "
                "Elo readiness scoring calibrated against Sri Lanka DoE 2022/2023 grade distributions.",
                icon=":material/emoji_events:")
        return

    quizzes = len(_progress(student["student_id"], student["subject"])["history"])
    if quizzes < 3:
        st.title("3A Achievement Engine")
        st.progress(quizzes / 3, text=f"{quizzes}/3 quizzes completed")
        st.write("Complete at least 3 quizzes in Test Me to unlock your personalised Elo readiness score.")
        if st.button("Start a quiz", type="primary", icon=":material/quiz:"):
            nav.go("TEST_ME")
        return
    render_3a_achievement_mode(student, db, _llm)


def _page_notes():
    st.title("My Notes")
    st.caption("Upload lecture notes or textbooks (PDF). Learn, Revise and the Virtual Teacher "
               "answer from them and cite the page.")
    pdfs = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True, key="_notes_pdfs")
    for pdf in pdfs or []:
        if pdf.name in st.session_state["rag_docs"]:
            continue
        with st.status(f"Indexing {pdf.name}...", expanded=False) as status:
            try:
                _al_subj = (st.session_state.get("al_subjects") or [None])[0] or None
                chunks = ingest_pdf(
                    pdf, st.session_state.get("subject", "General"),
                    st.session_state.get("preferred_language", "English"),
                    al_stream=st.session_state.get("al_stream") or None, al_subject=_al_subj,
                )
                if not chunks:
                    status.update(label=f"{pdf.name}: no selectable text (scanned PDF?)", state="error")
                    continue
                st.session_state["rag_docs"].append(pdf.name)
                db.update_student_pdf(st.session_state["student_id"], ",".join(st.session_state["rag_docs"]))
                status.update(label=f"{pdf.name}: {chunks} passage{'s' if chunks != 1 else ''} indexed", state="complete")
            except Exception as e:
                status.update(label=f"Could not index {pdf.name}", state="error")
                st.write(str(e) if APP_DEBUG else "Check that Ollama is running (it creates the embeddings).")

    docs = st.session_state["rag_docs"]
    st.subheader(f"Indexed documents ({len(docs)})")
    if docs:
        for d in docs:
            st.markdown(f":material/picture_as_pdf: {d}")
        st.caption(f"{get_retrieval_coverage().get('total_chunks', 0)} passages searchable")
    else:
        st.caption("Nothing uploaded yet.")


def _page_settings():
    st.title("Settings")
    ok = st.session_state.get("ollama_connected", False)
    with st.container(border=True):
        st.subheader("System")
        st.markdown(f"**AI model:** {st.session_state.get('ollama_model', OLLAMA_MODEL)} "
                    f"({':green[running]' if ok else ':red[not reachable]'} at `{OLLAMA_HOST}`)")
        st.markdown(f"**Notes index:** {get_retrieval_coverage().get('total_chunks', 0)} passages")
        st.markdown("**Internet:** not required — fonts, diagrams and the model run on this machine")

    with st.expander("Demo controls"):
        st.warning("Resetting replaces the demo students' data with fresh sample data.")
        if st.button("Reset demo data", icon=":material/restart_alt:", key="btn_reset_demo"):
            import subprocess
            result = subprocess.run(
                [sys.executable, "seed_demo_data.py"],
                capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)),
            )
            if result.returncode == 0:
                st.session_state.clear()
                _progress.clear()
                st.rerun()
            else:
                st.error(f"Reset failed: {result.stderr[:200]}")


def _build_navigation():
    builders = {
        "HOME": _page_home, "LEARN": _page_learn, "REVISE": _page_revise, "TEST_ME": _page_test_me,
        "VIRTUAL_TEACHER": _page_virtual_teacher, "PAST_PAPER": _page_past_paper,
        "BATTLE_GAME": _page_battle, "WEAKNESS": _page_weakness, "STUDY_PLAN": _page_study_plan,
        "TEACHER": _page_teacher, "THREE_A": _page_progress, "NOTES": _page_notes,
        "SETTINGS": _page_settings,
    }
    # The landing page is fixed per session (tests and deep links set "mode" before the first run)
    start = st.session_state.setdefault("_start_page", st.session_state.get("mode", "HOME"))
    progress_title = "3A Achievement" if st.session_state.get("student_type") == "A/L Student" else "My Progress"
    titles = {key: title for title, key in _PRIMARY_MODES + _SECONDARY_MODES}
    titles.update(THREE_A=progress_title, NOTES="My Notes", SETTINGS="Settings")

    def page(key):
        p = st.Page(builders[key], title=titles[key], icon=f":material/{_ICONS[key]}:",
                    url_path=key.lower().replace("_", "-"), default=(key == start))
        nav.PAGES[key] = p
        return p

    sections = {
        "Study": [page(k) for _, k in _PRIMARY_MODES],
        "Practice": [page(k) for _, k in _SECONDARY_MODES],
        "You": [page("THREE_A"), page("NOTES"), page("SETTINGS")],
    }
    return st.navigation(sections, expanded=True)


def main():
    _ollama_ok = _check_ollama_connection()
    st.session_state["ollama_connected"] = _ollama_ok
    if _ollama_ok:
        st.session_state["ollama_model"] = _llm._resolve_model()

    pg = _build_navigation()
    _render_sidebar(_ollama_ok)
    render_offline_seal()
    if not _ollama_ok:
        st.warning(
            "**The local AI model isn't running.** Your progress, study plan and "
            "history still work, but AI answers won't. Start it with `ollama serve`, "
            "then refresh this page.",
            icon=":material/cloud_off:",
        )

    try:
        pg.run()
    except Exception as _mode_err:
        st.error("Something went wrong on this page. Try again, or pick another page from the sidebar.")
        if APP_DEBUG:
            st.exception(_mode_err)


main()
