# teacher.py — Model paper generator
# OmniScholar | stub — full implementation coming

import streamlit as st


# teacher.py — Model Paper Generator (Teacher Mode)
# OmniScholar | Gemma 4 Good Hackathon

import json
import math

import streamlit as st

from prompt import PAPER_GEN_PROMPT
from rag import retrieve_context


_UNIVERSITIES = ["General", "Colombo", "Peradeniya", "Kelaniya", "Ruhuna", "SLIIT"]
_QUESTION_TYPES = ["MCQ", "Short Answer", "Essay", "Structured"]
_LANGUAGES = ["English", "Tamil", "Sinhala"]
_MARKS_OPTIONS = [25, 50, 75, 100]


def _time_for_marks(total_marks: int) -> int:
    """Estimate exam duration in minutes based on total marks."""
    return max(30, math.ceil(total_marks * 1.2))


def _render_paper(paper_data: dict):
    """Render the generated exam paper in university format."""
    paper_info = paper_data.get("paper", {})
    questions = paper_data.get("questions", [])
    marking_scheme = paper_data.get("marking_scheme", [])

    university = paper_info.get("university", "General")
    subject = paper_info.get("subject", "Subject")
    total_marks = paper_info.get("total_marks", 0)
    time_allowed = paper_info.get("time_allowed_minutes", 60)
    instructions = paper_info.get(
        "instructions",
        "Answer ALL questions in Section A. Answer THREE from Section B.",
    )

    # Paper header
    st.markdown(
        f"""
        <div style="border:2px solid #1E3A5F;border-radius:10px;padding:24px;
                    margin-bottom:16px;background:#F8FAFC;">
          <div style="text-align:center;">
            <h3 style="margin:0;color:#1E3A5F">
              {"GENERAL CERTIFICATE OF EDUCATION" if university == "General"
               else f"UNIVERSITY OF {university.upper()}"}
            </h3>
            <h4 style="margin:4px 0;color:#0F172A">{subject}</h4>
            <div style="display:flex;justify-content:center;gap:32px;margin-top:10px;
                        font-size:13px;color:#64748B;">
              <span>⏱ Time Allowed: {time_allowed} minutes</span>
              <span>📊 Total Marks: {total_marks}</span>
            </div>
            <div style="margin-top:10px;font-size:13px;font-style:italic;color:#64748B;">
              {instructions}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not questions:
        st.warning("No questions were generated. Try adjusting the parameters and regenerating.")
        return

    # Group by section
    sections: dict = {}
    for q in questions:
        sec = q.get("section", "A")
        if sec not in sections:
            sections[sec] = []
        sections[sec].append(q)

    for sec, sec_questions in sorted(sections.items()):
        sec_marks = sum(q.get("marks", 0) for q in sec_questions)
        st.markdown(f"#### Section {sec} ({sec_marks} marks)")

        for q in sec_questions:
            q_num = q.get("number", "?")
            q_type = q.get("type", "")
            q_marks = q.get("marks", 1)
            q_text = q.get("question_text", "")
            q_options = q.get("options", [])
            difficulty = q.get("difficulty", "")

            with st.container():
                st.markdown(
                    f"**{q_num}.** {q_text} *[{q_marks} mark{'s' if q_marks > 1 else ''}]*"
                )
                if q_options and q_type == "MCQ":
                    cols = st.columns(2)
                    for idx, opt in enumerate(q_options):
                        cols[idx % 2].markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{opt}")
                st.caption(f"Type: {q_type} | Difficulty: {difficulty}")
                st.markdown("")

    # Marking scheme in expander
    if marking_scheme:
        st.markdown("---")
        with st.expander("📋 Marking Scheme (Separate Page)", expanded=False):
            st.markdown(
                """
                <div style="background:#1E3A5F;color:white;padding:12px 16px;
                            border-radius:8px;margin-bottom:12px;text-align:center;">
                  <strong>MARKING SCHEME — EXAMINER'S COPY ONLY</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )
            for ms in marking_scheme:
                q_num = ms.get("question_number", "?")
                answer = ms.get("answer", "")
                explanation = ms.get("explanation", "")
                marks = ms.get("marks", 0)
                st.markdown(
                    f"**Q{q_num}:** Answer: **{answer}**  [{marks} mark{'s' if marks > 1 else ''}]"
                )
                st.caption(f"→ {explanation}")
                st.markdown("")


# ── Streaming question generator ────────────────────────────────────────────

def _generate_questions_streaming(
    llm,
    subject,
    num_questions,
    difficulty_dist,
    language,
    exam_format,
    student_type,
    progress_container,
    result_container,
):
    """Generate questions ONE AT A TIME with live progress."""
    all_questions = []
    progress_bar = progress_container.progress(0)
    status_text = progress_container.empty()

    if student_type == "A/L Student":
        format_instruction = (
            f"Generate this as a Sri Lanka A/L examination question "
            f"in {exam_format} format. Follow DoE marking conventions."
        )
    else:
        format_instruction = (
            f"Generate this as a {exam_format} format university exam question."
        )

    easy_pct = difficulty_dist.get("easy", 30)
    medium_pct = difficulty_dist.get("medium", 40)

    for i in range(num_questions):
        rand_val = (i / max(num_questions, 1)) * 100
        if rand_val < easy_pct:
            diff = "easy"
        elif rand_val < easy_pct + medium_pct:
            diff = "medium"
        else:
            diff = "hard"

        status_text.markdown(
            f"Generating question {i + 1} of {num_questions} ({diff})..."
        )

        prompt = (
            f"Generate exactly ONE {diff} {subject} exam question in {language}. "
            f"{format_instruction} "
            f"Format:\nQ: [question text]\n"
            f"A) [option]\nB) [option]\nC) [option]\nD) [option]\n"
            f"Answer: [correct letter]\nMarks: [1-5]\n"
            f"Explanation: [brief]\n\n"
            f"Generate ONLY this one question. Nothing else."
        )

        try:
            result = llm.fast_chat(
                message=prompt,
                system=(
                    f"You are a {subject} examiner. "
                    f"Generate one question only. Be concise."
                ),
                max_tokens=300,
            )
            all_questions.append(result.strip())
        except Exception as exc:
            all_questions.append(f"Q{i + 1}: [Generation failed: {exc}]")

        progress_bar.progress((i + 1) / num_questions)
        result_container.markdown("\n\n---\n\n".join(all_questions))

    status_text.success(f"[OK] Generated {num_questions} questions!")
    return "\n\n---\n\n".join(all_questions)


# ── Main entry point ──────────────────────────────────────────────────────────

def render_class_analytics(db) -> None:
    """Render anonymous class performance analytics."""
    st.subheader("📊 Anonymous Class Performance")
    st.caption(
        "Aggregated chapter scores from all students on this device. "
        "No names shared — percentages and counts only."
    )

    subject_filter = st.selectbox(
        "Filter by subject",
        ["All", "Computer Science", "Mathematics", "Physics", "Chemistry", "Biology"],
        key="analytics_subject_filter",
    )
    subject = None if subject_filter == "All" else subject_filter
    analytics = db.get_class_analytics(subject)

    if not analytics["topics"]:
        st.info("No chapter score data yet. Students must complete quizzes first.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Students", analytics["total_students"])
    col2.metric("Class Average", f"{analytics['class_avg']:.0f}%")
    col3.metric("Weakest Topic", analytics["most_struggling_topic"] or "—")

    st.markdown("**Topic Performance**")
    for row in analytics["topics"]:
        color = "🔴" if row["avg_score"] < 50 else "🟡" if row["avg_score"] < 70 else "🟢"
        st.markdown(
            f"{color} **{row['topic']}** — "
            f"Avg: {row['avg_score']:.0f}% | "
            f"Attempts: {row.get('attempt_count', row.get('attempts', 0))}"
        )

    if analytics["most_struggling_topic"]:
        st.warning(
            f"⚠️ **Action needed:** {analytics['most_struggling_topic']} "
            f"has the lowest class average. Consider generating a "
            f"focused revision paper on this topic."
        )
        if st.button("Generate Revision Paper for Weakest Topic", key="gen_weak_paper"):
            st.session_state["teacher_topic_prefill"] = analytics["most_struggling_topic"]
            st.rerun()


def render_teacher_mode(student: dict, db, llm):
    """Teacher Mode — generate print-ready exam papers with marking schemes."""
    language = student.get("language", student.get("preferred_language", "English"))
    subject = student.get("subject", "Biology")

    st.markdown("## 👩‍🏫 Teacher Mode")

    tab1, tab2 = st.tabs(["📝 Generate Paper", "📊 Class Analytics"])

    with tab1:
        st.markdown(
            """
            <div style="background:#1E3A5F;color:white;border-radius:12px;
                        padding:20px;margin-bottom:20px;">
              <h3 style="margin:0">📄 Model Paper Generator</h3>
              <p style="margin:4px 0 0;opacity:.85">
                Generate print-ready exam papers with marking schemes in any language.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Parameter input ───────────────────────────────────────────────────
        st.markdown("### Paper Parameters")

        col_a, col_b = st.columns(2)
        with col_a:
            paper_subject = st.text_input("Subject", value=subject)
            total_marks = st.selectbox("Total Marks", _MARKS_OPTIONS, index=1)
            question_count = st.slider("Number of Questions", min_value=3, max_value=15, value=5)
            paper_language = st.radio("Language", _LANGUAGES, horizontal=True,
                                      index=_LANGUAGES.index(language) if language in _LANGUAGES else 0)
        with col_b:
            question_types = st.multiselect(
                "Question Types",
                _QUESTION_TYPES,
                default=["MCQ", "Short Answer"],
            )
            if not question_types:
                question_types = ["MCQ"]

            st.markdown("**Difficulty Distribution**")
            easy_pct = st.slider("Easy %", min_value=0, max_value=100, value=30, step=5)
            medium_pct = st.slider("Medium %", min_value=0, max_value=100, value=40, step=5)
            hard_pct = 100 - easy_pct - medium_pct
            if hard_pct < 0:
                st.warning("Easy + Medium exceeds 100%. Adjusting Hard to 0%.")
                hard_pct = 0
            st.caption(f"Hard: {hard_pct}% (auto-calculated)")

            student_type = student.get("student_type", "Undergraduate")
            if student_type == "A/L Student":
                _al_formats = [
                    "Sri Lanka A/L (General)",
                    "Sri Lanka A/L (2023 Style)",
                    "Sri Lanka A/L (2022 Style)",
                    "NIE Curriculum Format",
                ]
                university = st.selectbox(
                    "A/L Exam Format", _al_formats, key="teacher_al_format"
                )
                _al_subs = student.get("al_subjects") or []
                if isinstance(_al_subs, str):
                    try:
                        _al_subs = json.loads(_al_subs)
                    except Exception:
                        _al_subs = []
                if _al_subs:
                    paper_subject = st.text_input(
                        "Subject",
                        value=_al_subs[0],
                        key="teacher_subject_al",
                    )
                st.caption(
                    "A/L papers follow DoE format: "
                    "Part A (MCQ) + Part B (Structured Essays)"
                )
            else:
                university = st.selectbox(
                    "University Format", _UNIVERSITIES, key="teacher_uni_format"
                )

        time_allowed = _time_for_marks(total_marks)
        difficulty_distribution = f"Easy {easy_pct}% / Medium {medium_pct}% / Hard {hard_pct}%"

        # Pre-fill topic from class analytics "weakest topic" button
        topic_prefill = st.session_state.pop("teacher_topic_prefill", None)
        if topic_prefill:
            st.info(f"📌 Generating revision paper for: **{topic_prefill}**")

        st.markdown("---")

        # Cap questions at 5 for demo speed
        num_q = question_count
        if num_q > 5:
            st.warning(
                f"Capped at 5 questions for speed. "
                f"Full {num_q}-question paper would take "
                f"{num_q * 2}\u2013{num_q * 3} minutes."
            )
            num_q = 5

        generate_btn = st.button(
            f"Generate {num_q}-Question {paper_subject} Paper",
            type="primary",
            use_container_width=True,
        )

        if "generated_paper" not in st.session_state:
            st.session_state.generated_paper = None
        if "teacher_paper" not in st.session_state:
            st.session_state.teacher_paper = None

        if generate_btn:
            _prog_container = st.container()
            _result_container = st.container()
            paper_text = _generate_questions_streaming(
                llm=llm,
                subject=paper_subject,
                num_questions=num_q,
                difficulty_dist={"easy": easy_pct, "medium": medium_pct},
                language=paper_language,
                exam_format=university,
                student_type=student.get("student_type", "Undergraduate"),
                progress_container=_prog_container,
                result_container=_result_container,
            )
            st.session_state.teacher_paper = paper_text
            st.session_state.generated_paper = None  # clear legacy JSON paper

        # ── Show streamed paper ───────────────────────────────────────────────
        if st.session_state.get("teacher_paper"):
            st.markdown("---")
            st.markdown("## Generated Exam Paper")
            col_dl, col_new = st.columns([3, 1])
            with col_dl:
                st.download_button(
                    label="Download Paper (TXT)",
                    data=st.session_state.teacher_paper,
                    file_name=f"{paper_subject}_paper.txt",
                    mime="text/plain",
                    key="btn_txt_download",
                )
            with col_new:
                if st.button("Generate New Paper", key="btn_new_stream"):
                    st.session_state.teacher_paper = None
                    st.rerun()
            st.markdown(st.session_state.teacher_paper)

        # Render generated paper
        if st.session_state.generated_paper:
            st.markdown("---")
            st.markdown("## 📄 Generated Exam Paper")

            col_dl, col_new = st.columns([3, 1])
            with col_dl:
                json_str = json.dumps(st.session_state.generated_paper, indent=2, ensure_ascii=False)
                st.download_button(
                    label="⬇️ Download Paper (JSON)",
                    data=json_str,
                    file_name=f"{paper_subject}_paper.json",
                    mime="application/json",
                )
                # ── PDF export ──────────────────────────────────────────────
                try:
                    from reportlab.lib.pagesizes import A4
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                    from reportlab.lib.styles import getSampleStyleSheet
                    import io as _io

                    _buf = _io.BytesIO()
                    _doc = SimpleDocTemplate(_buf, pagesize=A4,
                                            topMargin=40, bottomMargin=40,
                                            leftMargin=50, rightMargin=50)
                    _styles = getSampleStyleSheet()
                    _story = []
                    _paper = st.session_state.generated_paper
                    _pi = _paper.get("paper", {})

                    _story.append(Paragraph(
                        _pi.get("university", "General University").upper(),
                        _styles["Heading1"]
                    ))
                    _story.append(Paragraph(
                        _pi.get("subject", paper_subject), _styles["Heading2"]
                    ))
                    _story.append(Paragraph(
                        f"Duration: {_pi.get('time_allowed_minutes', 60)} min  |  "
                        f"Total Marks: {_pi.get('total_marks', 100)}",
                        _styles["Normal"]
                    ))
                    _story.append(Spacer(1, 20))

                    for _q in _paper.get("questions", []):
                        _story.append(Paragraph(
                            f"<b>Q{_q.get('number', '?')}.</b> {_q.get('question_text', '')} "
                            f"[{_q.get('marks', 1)} mark{'s' if _q.get('marks', 1) > 1 else ''}]",
                            _styles["Normal"]
                        ))
                        for _opt in _q.get("options", []):
                            _story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{_opt}", _styles["Normal"]))
                        _story.append(Spacer(1, 10))

                    _doc.build(_story)
                    _buf.seek(0)
                    st.download_button(
                        label="📄 Download as PDF",
                        data=_buf.getvalue(),
                        file_name=f"{_pi.get('subject', paper_subject)}_paper.pdf",
                        mime="application/pdf",
                        key="btn_pdf_download",
                    )
                except ImportError:
                    st.caption("Install reportlab for PDF export: `pip install reportlab`")
            with col_new:
                if st.button("Generate New Paper"):
                    st.session_state.generated_paper = None
                    st.rerun()

            _render_paper(st.session_state.generated_paper)

            paper_sources = getattr(st.session_state, "paper_sources", [])
            if paper_sources:
                st.caption(f"📎 Questions grounded in: {', '.join(paper_sources[:3])}")
            else:
                st.caption("📎 From model general knowledge — upload course materials for curriculum-grounded questions")

    with tab2:
        render_class_analytics(db)
