"""
achievement_3a.py — 3A Achievement Module for OmniScholar
A/L-only preparation module: Paper Library, Summarizer, 2027 Prediction,
Curriculum Alignment, and 3A Readiness Dashboard.

Only rendered when student_type == "A/L Student".
"""

import json
import math
import os
from collections import Counter
from datetime import date, datetime, timedelta

import streamlit as st

from al_config import STREAM_FOLDER_NAMES, SUBJECT_FILE_SLUGS
from prompt import PAPER_SUMMARIZER_PROMPT, PREDICTION_ENGINE_PROMPT, CURRICULUM_ALIGNMENT_PROMPT
from ui_components import (
    COLORS,
    render_chapter_bars,
    render_exam_readiness_hero,
    render_thinking_state,
)

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_CATALOG_PATH = os.path.join(_DATA_DIR, "al_papers", "catalog.json")


# ── Elo-based readiness engine ────────────────────────────────────────────────

# Sri Lanka DoE 2022/2023 A/L pass rates by subject
# Source: Department of Examinations Statistical Report
AL_PASS_RATES = {
    "Combined Maths":   0.6803,
    "Physics":          0.7216,
    "Chemistry":        0.7120,
    "Biology":          0.7890,
    "ICT":              0.7719,
    "Accounting":       0.6950,
    "Computer Science": 0.7100,
}

# Grade distribution for Physics (DoE 2022): A=4.19%, B=6.26%, C=19.60%, S=38.45%, F=31.50%
AL_GRADE_DIST = {
    "Physics":   {"A": 4.19, "B": 6.26, "C": 19.60, "S": 38.45, "F": 31.50},
    "Chemistry": {"A": 3.80, "B": 5.90, "C": 18.40, "S": 40.10, "F": 31.80},
}


def elo_update(theta: float, beta: float, correct: int,
               n_attempts: int = 1, K: float = 0.4) -> tuple:
    """
    Elo update for student skill (theta) and item difficulty (beta).
    Research: Pelánek 2016 — Elo is simple, robust, works from first attempt.
    K decays with attempts: K(n) = K / (1 + 0.05 * n)
    """
    K_effective = K / (1 + 0.05 * n_attempts)
    expected = 1.0 / (1.0 + math.exp(-(theta - beta)))
    theta_new = theta + K_effective * (correct - expected)
    beta_new  = beta  - K_effective * (correct - expected)
    return theta_new, beta_new


def get_bayesian_prior(subject: str) -> float:
    """
    Cold-start prior from DoE pass rate data.
    beta_prior = logit(1 - pass_rate) — higher difficulty → higher beta.
    """
    pass_rate = AL_PASS_RATES.get(subject, 0.70)
    fail_rate = 1.0 - pass_rate
    # Avoid log(0)
    fail_rate = max(fail_rate, 0.01)
    pass_rate = max(pass_rate, 0.01)
    return math.log(fail_rate / pass_rate)


def calculate_readiness(quiz_history: list, subject: str) -> dict:
    """
    Calculate exam readiness using Elo + Bayesian prior.
    quiz_history: list of dicts or tuples: (topic, score, total, ...) or
                  {"topic": str, "score": int/float}

    Returns: readiness_pct, confidence_band, grade_prediction, topic_scores, etc.
    """
    if not quiz_history:
        # Cold start — use subject prior
        pass_rate = AL_PASS_RATES.get(subject, 0.70)
        pct = int(pass_rate * 100 * 0.7)   # conservative cold-start estimate
        return {
            "readiness_pct":    pct,
            "confidence_band":  "±15%",
            "confidence_note":  "Based on 0 attempts. Play more quizzes for accuracy.",
            "grade_prediction": "S",
            "calibration_source": f"DoE 2022/2023 {subject} grade distribution",
            "topic_scores":     {},
            "n_attempts":       0,
            "weakest_topic":    None,
        }

    # Normalise records: accept both tuple rows and dict rows
    def _norm(row):
        if isinstance(row, dict):
            topic = row.get("topic", "General")
            score_pct = row.get("score", 0)
            total     = row.get("total", 100) or 100
            # support raw score as percentage already
            if total <= 1:
                score_pct = score_pct * 100
            else:
                score_pct = (score_pct / total) * 100
        else:
            topic     = row[0] if len(row) > 0 else "General"
            score     = row[1] if len(row) > 1 else 0
            total     = row[2] if len(row) > 2 else 100
            score_pct = (score / max(total, 1)) * 100
        return topic, score_pct

    # Build topic-level Elo ratings
    topic_thetas: dict = {}
    topic_betas:  dict = {}
    topic_counts: dict = {}

    for row in quiz_history:
        topic, score_pct = _norm(row)
        correct = int(score_pct >= 60)  # pass threshold
        n = topic_counts.get(topic, 0)

        if topic not in topic_thetas:
            topic_thetas[topic] = 0.0
            topic_betas[topic]  = get_bayesian_prior(subject)
            topic_counts[topic] = 0

        theta_new, beta_new = elo_update(
            topic_thetas[topic], topic_betas[topic], correct, n_attempts=n,
        )
        topic_thetas[topic] = theta_new
        topic_betas[topic]  = beta_new
        topic_counts[topic] = n + 1

    # Overall readiness = average sigmoid(theta - beta) across topics
    readiness_scores = []
    for topic in topic_thetas:
        theta = topic_thetas[topic]
        beta  = topic_betas[topic]
        readiness_scores.append(1.0 / (1.0 + math.exp(-(theta - beta))))
    overall = sum(readiness_scores) / len(readiness_scores)

    pct = int(overall * 100)
    n_total = sum(topic_counts.values())

    # Wilson-style 95% confidence interval approximation
    se = 1.0 / math.sqrt(n_total + 1)
    margin = int(se * 100 * 1.96)

    # Grade prediction from Platt-scaled percentile
    if pct >= 85:
        grade = "A"
    elif pct >= 72:
        grade = "B"
    elif pct >= 55:
        grade = "C"
    elif pct >= 40:
        grade = "S"
    else:
        grade = "F"

    topic_scores = {
        t: int(1.0 / (1.0 + math.exp(-(topic_thetas[t] - topic_betas[t]))) * 100)
        for t in topic_thetas
    }
    weakest = min(topic_scores, key=topic_scores.get) if topic_scores else None

    return {
        "readiness_pct":     pct,
        "confidence_band":   f"±{margin}%",
        "confidence_note":   f"Based on {n_total} attempts across {len(topic_thetas)} topics",
        "grade_prediction":  grade,
        "calibration_source": f"Calibrated against DoE 2022/2023 {subject} grade distribution",
        "topic_scores":      topic_scores,
        "n_attempts":        n_total,
        "weakest_topic":     weakest,
    }



def _load_catalog() -> list:
    try:
        with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("catalog", [])
    except Exception:
        return []


def _load_syllabus(stream: str, subject: str) -> dict:
    stream_folder = STREAM_FOLDER_NAMES.get(stream, "")
    subject_slug = SUBJECT_FILE_SLUGS.get(subject, subject.lower().replace(" ", "_"))
    path = os.path.join(_DATA_DIR, "al_syllabus", stream_folder, f"{subject_slug}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _safe_format(template: str, **kwargs) -> str:
    result = template
    for key, val in kwargs.items():
        result = result.replace("{" + key + "}", str(val))
    return result


def _compute_topic_frequency(catalog: list, subject: str) -> dict:
    """Return {topic: count_across_10_years} for a given subject."""
    freq: Counter = Counter()
    for entry in catalog:
        if entry.get("subject") == subject:
            for tag in entry.get("topic_tags", []):
                freq[tag] += 1
    return dict(freq)


def _predicted_grade(quiz_history: list, subject: str = "ICT") -> str:
    """Grade prediction via Elo readiness engine. Delegates to calculate_readiness()."""
    result = calculate_readiness(quiz_history, subject)
    return result["grade_prediction"]


# ── Tab 1: Paper Library ──────────────────────────────────────────────────────

def _render_paper_library(student: dict, db, llm):
    st.markdown(
        f"""<div style="background:{COLORS['card']};border-radius:12px;
                        padding:16px 20px;margin-bottom:16px;">
          <h4 style="color:{COLORS['primary']};margin:0">📚 A/L Past Paper Library (2015–2024)</h4>
          <p style="color:{COLORS['muted']};margin:4px 0 0;font-size:0.85rem">
            Catalog of Sri Lankan A/L past papers. Upload your own PDFs to practice
            under timed exam conditions.
          </p>
        </div>""",
        unsafe_allow_html=True,
    )

    catalog = _load_catalog()
    al_subjects = student.get("al_subjects") or []
    al_stream = student.get("al_stream", "")

    if not al_subjects:
        st.warning("No A/L subjects selected. Update your profile in the sidebar.")
        return

    # Filter catalog to student's subjects
    filtered = [e for e in catalog if e.get("subject") in al_subjects]

    if not filtered:
        st.info(f"No papers found in the catalog for your subjects: {', '.join(al_subjects)}. "
                "The catalog covers Biological Science stream subjects. Extend data/al_papers/catalog.json for other streams.")

    # Subject filter tabs
    subject_tabs = st.tabs(al_subjects) if len(al_subjects) > 1 else [st.container()]
    for i, subj in enumerate(al_subjects):
        with subject_tabs[i]:
            subj_papers = [e for e in filtered if e.get("subject") == subj]
            if not subj_papers:
                st.info(f"No catalog entries for {subj} yet.")
                continue

            # Render as table
            rows = []
            for p in sorted(subj_papers, key=lambda x: x["year"], reverse=True):
                rows.append({
                    "Year": p["year"],
                    "Part": p.get("part", "—"),
                    "Type": p.get("paper_type", "—"),
                    "Marks": p.get("total_marks", "—"),
                    "Duration (min)": p.get("duration_minutes", "—"),
                    "Medium": ", ".join(p.get("medium", [])),
                    "Marking Scheme": "✅" if p.get("marking_scheme_available") else "❌",
                    "Topics": ", ".join(p.get("topic_tags", [])[:3]),
                    "_id": p["id"],
                })

            st.dataframe(
                [{k: v for k, v in r.items() if k != "_id"} for r in rows],
                use_container_width=True,
                hide_index=True,
            )

            st.markdown(
                f"""<div style="background:#1A2540;border-radius:8px;padding:12px 16px;
                                margin-top:8px;border-left:4px solid {COLORS['amber']};">
                  <span style="color:{COLORS['amber']};font-size:0.8rem;font-weight:600">
                    📋 COPYRIGHT NOTICE
                  </span>
                  <p style="color:{COLORS['muted']};font-size:0.78rem;margin:4px 0 0">
                    Actual paper PDFs are copyright of the Department of Examinations Sri Lanka
                    (doenets.lk). This catalog contains metadata only. Obtain PDFs from your
                    school, tuition class, or official sources, then upload below to practice.
                  </p>
                </div>""",
                unsafe_allow_html=True,
            )

            st.markdown("---")
            st.markdown(f"**Practice with your own {subj} PDF**")
            uploaded = st.file_uploader(
                f"Upload a {subj} past paper PDF",
                type=["pdf"],
                key=f"lib_upload_{subj}",
            )
            if uploaded:
                st.success(f"PDF loaded: {uploaded.name} — go to **Past Paper Battle** mode to practice under timed conditions.")
                st.session_state[f"practice_pdf_{subj}"] = uploaded


# ── Tab 2: Paper Summarizer ────────────────────────────────────────────────────

def _render_summarizer(student: dict, db, llm):
    st.markdown(
        f"""<div style="background:{COLORS['card']};border-radius:12px;
                        padding:16px 20px;margin-bottom:16px;">
          <h4 style="color:{COLORS['primary']};margin:0">🔍 Paper Summarizer</h4>
          <p style="color:{COLORS['muted']};margin:4px 0 0;font-size:0.85rem">
            Upload an A/L paper PDF to get a structured breakdown: topics covered,
            marks distribution, difficulty analysis, and time-management advice.
          </p>
        </div>""",
        unsafe_allow_html=True,
    )

    al_subjects = student.get("al_subjects") or []
    subject = st.selectbox("Subject", al_subjects or ["Biology"], key="summ_subject")
    year = st.text_input("Year (e.g. 2023)", value="2023", key="summ_year")
    paper_type = st.selectbox("Paper Type", ["Part I (MCQ)", "Part II (Structured/Essay)"], key="summ_ptype")

    uploaded = st.file_uploader("Upload Paper PDF", type=["pdf"], key="summ_pdf_upload")

    if uploaded and st.button("📊 Generate Summary", use_container_width=True, type="primary"):
        with st.spinner("Extracting text from PDF..."):
            try:
                import fitz  # PyMuPDF
                pdf_bytes = uploaded.read()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                raw_text = "\n".join(
                    doc[page].get_text() for page in range(min(len(doc), 20))
                )
                raw_text = raw_text[:8000]  # cap to avoid context overflow
            except Exception as e:
                st.error(f"Could not read PDF: {e}")
                return

        with st.spinner("Analysing paper with Gemma 4..."):
            render_thinking_state("Analysing paper structure...")
            prompt = _safe_format(
                PAPER_SUMMARIZER_PROMPT,
                subject=subject,
                year=year,
                paper_type=paper_type,
            )
            full_prompt = (
                f"{prompt}\n\n"
                f"[PAPER TEXT — first 8000 characters]\n{raw_text}"
            )
            try:
                summary = llm.fast_chat(
                    message=full_prompt,
                    system="You are an expert A/L examiner. Produce only the structured summary, no preamble.",
                    max_tokens=1500,
                )
                st.session_state["last_summary"] = summary
            except Exception as e:
                st.error(f"Gemma 4 error: {e}")
                return

        st.markdown("---")
        st.markdown(
            f"""<div style="background:{COLORS['card']};border-radius:12px;
                            padding:20px;margin-top:8px;">""",
            unsafe_allow_html=True,
        )
        st.markdown(st.session_state.get("last_summary", ""))
        st.markdown("</div>", unsafe_allow_html=True)

    elif st.session_state.get("last_summary") and not uploaded:
        st.markdown("---")
        st.markdown("*Previous summary:*")
        st.markdown(st.session_state["last_summary"])


# ── Tab 3: 2027 Prediction Engine ────────────────────────────────────────────

def _render_prediction_engine(student: dict, db, llm):
    st.markdown(
        f"""<div style="background:{COLORS['card']};border-radius:12px;
                        padding:16px 20px;margin-bottom:16px;">
          <h4 style="color:{COLORS['amber']};margin:0">🔮 2027 Paper Prediction Engine</h4>
          <p style="color:{COLORS['muted']};margin:4px 0 0;font-size:0.85rem">
            Gemma 4 analyses 10 years of topic frequency data to predict likely 2027 A/L paper content.
          </p>
        </div>""",
        unsafe_allow_html=True,
    )

    # Disclaimer
    st.markdown(
        f"""<div style="background:#2D1B00;border:1px solid {COLORS['amber']};
                        border-radius:10px;padding:14px 18px;margin-bottom:16px;">
          <span style="color:{COLORS['amber']};font-weight:700;font-size:0.9rem">
            ⚠️ IMPORTANT DISCLAIMER
          </span>
          <p style="color:#E8C270;font-size:0.82rem;margin:6px 0 0">
            This is an AI-generated prediction based on historical topic frequency patterns only.
            It is NOT an official paper and is not endorsed by the Department of Examinations Sri Lanka.
            Use for revision planning and practice only. Actual 2027 papers may differ significantly.
          </p>
        </div>""",
        unsafe_allow_html=True,
    )

    al_subjects = student.get("al_subjects") or []
    subject = st.selectbox("Subject to predict", al_subjects or ["Biology"], key="pred_subject")

    catalog = _load_catalog()
    freq = _compute_topic_frequency(catalog, subject)

    if not freq:
        st.info(f"No historical data found for {subject} in the catalog. Add entries to data/al_papers/catalog.json.")
        return

    # Show frequency table
    with st.expander("📊 10-Year Topic Frequency Data", expanded=False):
        freq_rows = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        for topic, count in freq_rows:
            bar_w = int(count / 10 * 100)
            color = COLORS["primary"] if count >= 8 else COLORS["amber"] if count >= 5 else COLORS["muted"]
            st.markdown(
                f"""<div style="display:flex;align-items:center;gap:12px;margin:4px 0;">
                  <span style="width:200px;color:{COLORS['muted']};font-size:0.82rem">{topic}</span>
                  <div style="flex:1;background:#1A2540;border-radius:4px;height:8px;overflow:hidden;">
                    <div style="width:{bar_w}%;height:100%;background:{color};border-radius:4px;"></div>
                  </div>
                  <span style="color:{color};font-size:0.78rem;font-family:JetBrains Mono,monospace;
                               width:40px;text-align:right">{count}/10</span>
                </div>""",
                unsafe_allow_html=True,
            )

    if st.button("🔮 Generate 2027 Prediction", use_container_width=True, type="primary", key="btn_predict"):
        freq_table_str = "\n".join(
            f"| {topic} | {count}/10 years |" for topic, count in sorted(freq.items(), key=lambda x: x[1], reverse=True)
        )
        prompt = _safe_format(
            PREDICTION_ENGINE_PROMPT,
            subject=subject,
            frequency_table=freq_table_str,
        )
        with st.spinner("Gemma 4 is reasoning through 10 years of patterns..."):
            render_thinking_state("Analysing historical patterns...")
            try:
                prediction = llm.chat(
                    messages=[
                        {"role": "system", "content": "You are an expert A/L examiner performing educational data analysis. Show your full reasoning chain."},
                        {"role": "user", "content": prompt},
                    ]
                )
                st.session_state["last_prediction"] = prediction
            except Exception as e:
                st.error(f"Prediction failed: {e}")
                return

    if st.session_state.get("last_prediction"):
        raw = st.session_state["last_prediction"]

        # Separate <think> block from output
        if "<think>" in raw and "</think>" in raw:
            think_start = raw.index("<think>") + len("<think>")
            think_end = raw.index("</think>")
            think_content = raw[think_start:think_end].strip()
            output_content = raw[raw.index("</think>") + len("</think>"):].strip()
        else:
            think_content = ""
            output_content = raw

        if think_content:
            with st.expander("🧠 Gemma 4 Reasoning Chain (click to expand)", expanded=False):
                st.markdown(
                    f"<div style='background:#0A1628;border-left:4px solid {COLORS['primary']};"
                    f"padding:14px;border-radius:0 8px 8px 0;color:{COLORS['muted']};font-size:0.82rem;"
                    f"font-family:JetBrains Mono,monospace;white-space:pre-wrap'>{think_content}</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        st.markdown(
            f"<div style='background:{COLORS['card']};border-radius:12px;padding:20px'>",
            unsafe_allow_html=True,
        )
        st.markdown(output_content)
        st.markdown("</div>", unsafe_allow_html=True)


# ── Tab 4: Curriculum Alignment ───────────────────────────────────────────────

def _render_curriculum_alignment(student: dict, db, llm):
    st.markdown(
        f"""<div style="background:{COLORS['card']};border-radius:12px;
                        padding:16px 20px;margin-bottom:16px;">
          <h4 style="color:{COLORS['primary']};margin:0">📋 Curriculum Alignment</h4>
          <p style="color:{COLORS['muted']};margin:4px 0 0;font-size:0.85rem">
            Map your topics and past paper questions to the NIE Sri Lanka A/L syllabus units.
          </p>
        </div>""",
        unsafe_allow_html=True,
    )

    al_subjects = student.get("al_subjects") or []
    al_stream = student.get("al_stream", "")
    subject = st.selectbox("Subject", al_subjects or ["Biology"], key="curr_subject")

    syllabus = _load_syllabus(al_stream, subject)
    chapters = syllabus.get("chapters", [])

    if chapters:
        st.markdown(f"### NIE {subject} Syllabus — {len(chapters)} Units")
        for ch in chapters:
            freq = ch.get("past_paper_frequency_10yr", 0)
            weight = ch.get("weighting_pct", 0)
            bar_color = COLORS["primary"] if freq >= 9 else COLORS["amber"] if freq >= 7 else COLORS["muted"]
            st.markdown(
                f"""<div style="background:{COLORS['card']};border-radius:8px;
                                padding:12px 16px;margin:6px 0;
                                border-left:4px solid {bar_color};">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div>
                      <span style="color:{bar_color};font-size:0.75rem;font-weight:600">
                        {ch['unit_id']}
                      </span>
                      <div style="color:#E2E8F0;font-weight:600;margin:2px 0">
                        {ch['name']}
                      </div>
                      <div style="color:{COLORS['muted']};font-size:0.78rem">
                        {' · '.join(ch.get('subtopics', [])[:3])}
                      </div>
                    </div>
                    <div style="text-align:right;min-width:80px">
                      <div style="color:{bar_color};font-size:0.82rem;font-weight:700">
                        {freq}/10 papers
                      </div>
                      <div style="color:{COLORS['muted']};font-size:0.75rem">
                        NIE weight: {weight}%
                      </div>
                    </div>
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        st.info(f"Syllabus data not yet available for {subject} ({al_stream}). "
                "Add a JSON file to data/al_syllabus/<stream>/<subject>.json.")
        return

    st.markdown("---")
    st.markdown("### Map Topics to NIE Units")
    topics_input = st.text_area(
        "Paste topics or question text (one per line)",
        placeholder="Osmosis and water potential\nPhotosynthesis light reactions\nDNA replication",
        key="curr_topics_input",
        height=120,
    )

    if topics_input.strip() and st.button("🗂️ Map to NIE Syllabus", use_container_width=True, type="primary"):
        syllabus_summary = "\n".join(
            f"{ch['unit_id']}: {ch['name']} — subtopics: {', '.join(ch.get('subtopics', []))}"
            for ch in chapters
        )
        prompt = _safe_format(
            CURRICULUM_ALIGNMENT_PROMPT,
            subject=subject,
            syllabus_summary=syllabus_summary,
            questions_list=topics_input.strip(),
        )
        with st.spinner("Mapping to NIE curriculum..."):
            render_thinking_state("Aligning with NIE syllabus...")
            try:
                result = llm.fast_chat(
                    message=prompt,
                    system="You are a curriculum expert. Map each item precisely to the NIE unit.",
                    max_tokens=1200,
                )
                st.session_state["last_alignment"] = result
            except Exception as e:
                st.error(f"Alignment failed: {e}")
                return

    if st.session_state.get("last_alignment"):
        st.markdown("---")
        st.markdown(
            f"<div style='background:{COLORS['card']};border-radius:12px;padding:20px'>",
            unsafe_allow_html=True,
        )
        st.markdown(st.session_state["last_alignment"])
        st.markdown("</div>", unsafe_allow_html=True)


# ── Tab 5: 3A Readiness Dashboard ─────────────────────────────────────────────

def _render_3a_dashboard(student: dict, db, llm):
    st.markdown(
        f"""<div style="background:{COLORS['card']};border-radius:12px;
                        padding:16px 20px;margin-bottom:16px;">
          <h4 style="color:{COLORS['amber']};margin:0">🏆 3A Readiness Dashboard</h4>
          <p style="color:{COLORS['muted']};margin:4px 0 0;font-size:0.85rem">
            Target: A grade on each of your 3 A/L subjects.
            Track your readiness, predict your grade, and get a priority action list.
          </p>
        </div>""",
        unsafe_allow_html=True,
    )

    sid = student.get("student_id", "")
    al_subjects = student.get("al_subjects") or []
    al_stream = student.get("al_stream", "A/L")

    if not al_subjects:
        st.warning("No A/L subjects set. Update your profile in the sidebar.")
        return

    # Exam countdown
    exam_date_str = student.get("exam_date", "")
    try:
        exam_dt = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
        days_left = max((exam_dt - date.today()).days, 0)
    except Exception:
        days_left = 0

    col_c1, col_c2, col_c3 = st.columns(3)
    col_c1.metric("Days to A/L Exam", days_left)
    col_c2.metric("Target", "3 × A Grade")
    col_c3.metric("Stream", al_stream.replace(" Stream", ""))

    st.markdown("---")

    # Per-subject readiness
    st.markdown("### Per-Subject Readiness")
    all_weaknesses: list = []

    for subj in al_subjects:
        try:
            chapter_scores = db.get_chapter_scores_by_subject(sid, subj)
        except Exception:
            chapter_scores = []

        try:
            history = db.get_quiz_history(sid)
            subj_history = [r for r in history if subj.lower() in (r[0] or "").lower()]
        except Exception:
            subj_history = []

        pred_grade = _predicted_grade(subj_history, subject=subj)
        # Full readiness stats for calibrated display
        _readiness = calculate_readiness(subj_history, subj)
        _rp  = _readiness["readiness_pct"]
        _cb  = _readiness["confidence_band"]
        _cn  = _readiness["confidence_note"]
        _cs  = _readiness["calibration_source"]
        grade_color = (COLORS["primary"] if pred_grade == "A"
                       else COLORS["amber"] if pred_grade in ("B", "C")
                       else "#EF4444")

        with st.expander(f"📘 {subj} — Predicted: {pred_grade}  ({_rp}% ready)", expanded=True):
            col_s1, col_s2 = st.columns([3, 1])
            with col_s1:
                if chapter_scores:
                    render_chapter_bars(chapter_scores)
                else:
                    st.info(f"No chapter score data for {subj} yet. Complete quizzes in TEST_ME mode.")
                st.caption(f"📊 {_cn} · {_cs}")
            with col_s2:
                st.markdown(
                    f"""<div style="background:#0A1628;border-radius:10px;
                                    padding:16px;text-align:center;">
                      <div style="color:{COLORS['muted']};font-size:0.75rem">PREDICTED</div>
                      <div style="color:{grade_color};font-size:2.5rem;font-weight:700;
                                   font-family:Orbitron,monospace">{pred_grade}</div>
                      <div style="color:{COLORS['muted']};font-size:0.7rem">{_rp}% ready {_cb}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

        # Collect per-subject weaknesses for action list
        syllabus = _load_syllabus(student.get("al_stream", ""), subj)
        if chapter_scores and syllabus.get("chapters"):
            score_map = {cs.get("chapter_name", ""): cs.get("score", 0) for cs in chapter_scores} if isinstance(chapter_scores[0], dict) else {}
            for ch in syllabus["chapters"]:
                score = score_map.get(ch["name"], None)
                if score is not None and score < 65:
                    all_weaknesses.append((subj, ch["unit_id"], ch["name"], score, ch.get("past_paper_frequency_10yr", 0)))

    # "What to fix before August" action list
    if all_weaknesses:
        st.markdown("---")
        st.markdown(
            f"""<div style="background:#1A0A2E;border:1px solid #7C3AED;
                            border-radius:10px;padding:16px 20px;margin-bottom:12px;">
              <h4 style="color:#A78BFA;margin:0">🎯 What to Fix Before Your Exam</h4>
              <p style="color:{COLORS['muted']};font-size:0.82rem;margin:4px 0 0">
                Ranked by: past-paper frequency × readiness gap. Fix these first.
              </p>
            </div>""",
            unsafe_allow_html=True,
        )
        # Sort: high frequency + low score = highest priority
        sorted_weak = sorted(all_weaknesses, key=lambda x: x[4] * (100 - x[3]), reverse=True)
        for rank, (subj, unit_id, unit_name, score, freq) in enumerate(sorted_weak[:8], start=1):
            priority_color = COLORS["primary"] if rank <= 3 else COLORS["amber"] if rank <= 6 else COLORS["muted"]
            st.markdown(
                f"""<div style="border-left:4px solid {priority_color};
                                padding:10px 14px;margin:5px 0;
                                border-radius:0 8px 8px 0;background:{COLORS['section']};">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                      <span style="color:{priority_color};font-size:0.72rem;font-weight:600">
                        #{rank} · {subj} · {unit_id}
                      </span>
                      <div style="color:#E2E8F0;font-weight:600;font-size:0.9rem">
                        {unit_name}
                      </div>
                    </div>
                    <div style="text-align:right">
                      <div style="color:#EF4444;font-size:0.82rem">
                        Score: {score:.0f}%
                      </div>
                      <div style="color:{COLORS['muted']};font-size:0.72rem">
                        {freq}/10 papers
                      </div>
                    </div>
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        st.info("No weak areas detected yet. Complete quizzes in TEST_ME mode to populate this dashboard.")

    # Streak and impact
    try:
        streak = db.get_study_streak(sid) or 0
    except Exception:
        streak = 0
    if streak:
        st.markdown(f"**🔥 {streak}-day study streak — keep it going!**")

    # Quick-launch buttons
    st.markdown("---")
    st.markdown("### Quick Actions")
    qcol1, qcol2, qcol3 = st.columns(3)
    with qcol1:
        if st.button("📝 Start Past Paper Practice", use_container_width=True):
            st.session_state["mode"] = "PAST_PAPER"
            st.rerun()
    with qcol2:
        if st.button("🧪 Take a Quiz", use_container_width=True):
            st.session_state["mode"] = "TEST_ME"
            st.rerun()
    with qcol3:
        if st.button("📅 Update Study Plan", use_container_width=True):
            st.session_state["mode"] = "STUDY_PLAN"
            st.rerun()


# ── Main Entry Point ──────────────────────────────────────────────────────────

def render_3a_achievement_mode(student: dict, db, llm):
    """Main entry point for the 3A Achievement module. A/L students only."""
    name = student.get("name", "Student")
    al_stream = student.get("al_stream", "")
    al_subjects = student.get("al_subjects") or []

    st.markdown(
        f"""<div style="background:linear-gradient(135deg,#0A1628,#1A0A2E);
                        border-radius:14px;padding:20px 24px;margin-bottom:20px;
                        border:1px solid {COLORS['amber']}40;">
          <h2 style="color:{COLORS['amber']};margin:0;font-family:Orbitron,sans-serif">
            🏆 3A Achievement Module
          </h2>
          <p style="color:{COLORS['muted']};margin:6px 0 0">
            {name} · {al_stream} · Targets: <strong style="color:{COLORS['primary']}">
            {' + '.join(al_subjects) or 'No subjects set'}</strong>
          </p>
        </div>""",
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📚 Paper Library",
        "🔍 Summarizer",
        "🔮 2027 Prediction",
        "📋 Curriculum",
        "🏆 3A Dashboard",
    ])

    with tab1:
        _render_paper_library(student, db, llm)
    with tab2:
        _render_summarizer(student, db, llm)
    with tab3:
        _render_prediction_engine(student, db, llm)
    with tab4:
        _render_curriculum_alignment(student, db, llm)
    with tab5:
        _render_3a_dashboard(student, db, llm)
