# past_paper.py — Past Paper Battle Mode
# OmniScholar | Gemma 4 Good Hackathon

import json
import re
import time

import fitz  # PyMuPDF
import streamlit as st

from prompt import EXAMINER_PROMPT, SOCRATIC_PROMPT, THREE_A_SOCRATIC_PROMPT
from rag import retrieve_context


# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_questions_from_pdf(pdf_bytes: bytes) -> tuple:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    questions = []
    marks_pattern = re.compile(r"\[(\d+)\]|\((\d+)\s*marks?\)", re.IGNORECASE)

    # Pattern A: "Question 1 (25 marks)" style — SLIIT/Colombo format
    main_q_pattern = re.compile(
        r"Question\s+(\d+)\s*\((\d+)\s*marks?\)", re.IGNORECASE
    )
    sub_q_pattern = re.compile(
        r"(?:^|\n)\s*([a-e])\)\s+(.+?)(?=\n\s*[a-f]\)\s|\n\s*Question\s|\Z)",
        re.DOTALL
    )
    # Pattern B: numbered "1." "2." style
    num_q_pattern = re.compile(
        r"(?:^|\n)\s*(\d{1,2})[.)]\s+(.+?)(?=\n\s*\d{1,2}[.)]\s|\Z)",
        re.DOTALL
    )

    main_matches = list(main_q_pattern.finditer(full_text))

    if main_matches:
        # SLIIT-style paper
        for i, mm in enumerate(main_matches):
            q_num = int(mm.group(1))
            q_marks = int(mm.group(2))
            section = f"Question {q_num}"
            start = mm.end()
            end = main_matches[i+1].start() if i+1 < len(main_matches) else len(full_text)
            section_text = full_text[start:end]
            sub_matches = list(sub_q_pattern.finditer(section_text))
            if sub_matches:
                for sub in sub_matches:
                    letter = sub.group(1)
                    body = sub.group(2).strip()[:500]
                    m = marks_pattern.search(body)
                    sub_marks = int(m.group(1) or m.group(2)) if m else 2
                    body = marks_pattern.sub("", body).strip()
                    questions.append({
                        "number": f"{q_num}{letter}",
                        "text": body,
                        "marks": sub_marks,
                        "section": section,
                    })
            else:
                questions.append({
                    "number": q_num,
                    "text": section_text.strip()[:400],
                    "marks": q_marks,
                    "section": section,
                })
    else:
        # Numbered style fallback
        for match in num_q_pattern.finditer(full_text):
            body = match.group(2).strip()[:500]
            m = marks_pattern.search(body)
            marks = int(m.group(1) or m.group(2)) if m else 2
            body = marks_pattern.sub("", body).strip()
            questions.append({
                "number": int(match.group(1)),
                "text": body,
                "marks": marks,
                "section": "General",
            })

    # Last resort: extract readable lines
    if not questions:
        lines = [l.strip() for l in full_text.split("\n") if len(l.strip()) > 25]
        for i, line in enumerate(lines[:15]):
            questions.append({
                "number": i + 1,
                "text": line[:300],
                "marks": 2,
                "section": "General",
            })

    first_500 = full_text[:600]
    year_m = re.search(r"\b(20\d{2})\b", first_500)
    year = int(year_m.group(1)) if year_m else 2024
    cs_subjects = ["Computer Security", "Computer Science", "Information Technology",
                   "Biology", "Chemistry", "Physics", "Mathematics"]
    detected = next((s for s in cs_subjects if s.lower() in full_text[:800].lower()),
                    "Computer Science")
    total_marks = sum(q["marks"] for q in questions if isinstance(q["marks"], int))

    return questions, {
        "subject": detected, "year": year,
        "total_marks": total_marks or 100,
        "total_questions": len(questions),
        "estimated_minutes": max(60, total_marks),
    }


def _call_examiner(llm, student, question, answer, subject, year, language):
    """Call LLM in examiner mode; return parsed verdict dict."""
    sys_prompt = EXAMINER_PROMPT.format(
        year=year, subject=subject,
        name=student.get("name", "Student"), language=language,
    )
    context, _ = retrieve_context(question["text"], subject=subject, n_results=3)
    ctx_block = f"\n\nRelevant context:\n{context}" if context else ""

    user_msg = (
        f"Question {question['number']} ({question['marks']} marks):\n"
        f"{question['text']}{ctx_block}\n\nStudent's answer: {answer}"
    )
    try:
        raw = llm.chat(
            messages=[{"role": "user", "content": user_msg}],
            system_prompt=sys_prompt,
            temperature=0.2,
        )
    except Exception as exc:
        raw = f"VERDICT: WRONG\nMARKS: 0 out of {question['marks']}\nFEEDBACK: Evaluation unavailable ({exc})"

    verdict_match = re.search(r"VERDICT:\s*(CORRECT|PARTIAL|WRONG)", raw, re.IGNORECASE)
    marks_match = re.search(r"MARKS:\s*(\d+)\s*out of\s*(\d+)", raw, re.IGNORECASE)
    feedback_match = re.search(r"FEEDBACK:\s*(.+?)(?:\n|$)", raw, re.IGNORECASE | re.DOTALL)

    verdict = verdict_match.group(1).upper() if verdict_match else "WRONG"
    marks_awarded = int(marks_match.group(1)) if marks_match else 0
    feedback = feedback_match.group(1).strip() if feedback_match else raw[:200]

    return {
        "verdict": verdict,
        "marks_awarded": min(marks_awarded, question["marks"]),
        "marks_available": question["marks"],
        "feedback": feedback,
        "raw": raw,
    }


def _call_socratic(llm, student, question, wrong_answer, turn, subject, language, history):
    """Run one Socratic turn; return the assistant's response string."""
    sys_prompt = SOCRATIC_PROMPT.format(
        name=student.get("name", "Student"),
        subject=subject,
        topic=question.get("text", "")[:100],
        language=language,
        turn=turn,
    )
    context, _ = retrieve_context(question["text"], subject=subject, n_results=3)
    ctx_note = f"\n\n[Context from study materials: {context}]" if context else ""

    messages = history + [{
        "role": "user",
        "content": (
            f"My answer was: {wrong_answer}\n"
            f"Question: {question['text']}{ctx_note}"
        ),
    }]
    try:
        response = llm.chat(messages=messages, system_prompt=sys_prompt, temperature=0.5)
    except Exception as exc:
        response = f"Could not reach OmniScholar right now ({exc}). Please ensure Ollama is running."
    return response


def _render_report(student, db, llm, session_id, questions, answers,
                   evaluations, subject, year, language, meta):
    """Render the Post-Battle Report and persist to DB."""
    st.subheader("📊 Post-Battle Report")

    total_scored = sum(e["marks_awarded"] for e in evaluations)
    total_available = sum(e["marks_available"] for e in evaluations)
    pct = round(total_scored / total_available * 100, 1) if total_available > 0 else 0
    pass_threshold = 50

    section_scores = {}
    for q, ev in zip(questions, evaluations):
        sec = q["section"]
        if sec not in section_scores:
            section_scores[sec] = {"scored": 0, "available": 0}
        section_scores[sec]["scored"] += ev["marks_awarded"]
        section_scores[sec]["available"] += ev["marks_available"]

    scored_with_idx = sorted(
        enumerate(evaluations),
        key=lambda x: x[1]["marks_awarded"] / max(x[1]["marks_available"], 1),
    )
    weakest_3 = scored_with_idx[:3]
    weak_topics = [questions[i]["section"] for i, _ in weakest_3]

    # Persist weak concepts
    for i, ev in enumerate(evaluations):
        if ev["verdict"] in ("WRONG", "PARTIAL"):
            db.upsert_weak_concept(
                student_id=student.get("id", student.get("student_id", "")),
                concept=questions[i]["text"][:80],
                topic=questions[i]["section"],
                error_type="factual_error" if ev["verdict"] == "WRONG" else "process_confusion",
            )

    # Hero score card
    color = "#16A34A" if pct >= pass_threshold else "#DC2626"
    st.markdown(
        f"""
        <div style="background:{color};color:white;border-radius:12px;
                    padding:24px;text-align:center;margin-bottom:16px;">
          <h2 style="margin:0">{total_scored} / {total_available} marks</h2>
          <h3 style="margin:4px 0">{pct}% — {'PASS ✓' if pct >= pass_threshold else 'BELOW PASS MARK ✗'}</h3>
          <p style="margin:0;opacity:.85">{subject} {year} Past Paper</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Section Breakdown")
    for sec, data in section_scores.items():
        sec_pct = round(data["scored"] / max(data["available"], 1) * 100, 1)
        st.progress(sec_pct / 100, text=f"{sec}: {data['scored']}/{data['available']} ({sec_pct}%)")

    st.markdown("#### ⚠️ Weakest Questions")
    for i, ev in weakest_3:
        with st.expander(
            f"Q{questions[i]['number']} — {ev['marks_awarded']}/{ev['marks_available']} marks — {ev['verdict']}"
        ):
            st.markdown(f"**Question:** {questions[i]['text']}")
            st.markdown(f"**Your answer:** {answers[i]}")
            st.markdown(f"**Feedback:** {ev['feedback']}")

    st.markdown("#### 📝 Examiner Comment")
    with st.spinner("Generating examiner comment..."):
        weak_summary = ", ".join([questions[i]["text"][:60] for i, _ in weakest_3])
        try:
            examiner_comment = llm.chat(
                messages=[{
                    "role": "user",
                    "content": (
                        f"Write one paragraph of examiner feedback for a student who scored "
                        f"{pct}% on the {year} {subject} paper. Weakest areas: {weak_summary}. "
                        f"Respond in {language}. Examiner voice only."
                    ),
                }],
                system_prompt=EXAMINER_PROMPT.format(
                    year=year, subject=subject,
                    name=student.get("name", "Student"), language=language,
                ),
                temperature=0.4,
            )
        except Exception:
            examiner_comment = "Examiner comment unavailable — please ensure Ollama is running."
    st.info(examiner_comment)

    st.markdown("#### 🎯 Next Steps")
    for i, ev in weakest_3:
        st.markdown(
            f"- **{questions[i]['section']}** — Revise this section. "
            f"Scored {ev['marks_awarded']}/{ev['marks_available']}."
        )
    if pct < pass_threshold:
        st.error("Priority: Reach 50% before your exam. Focus on weakest sections above.")
    else:
        st.success("Good foundation. Focus on pushing from pass to distinction level.")

    if weak_topics:
        st.caption(f"📎 Weak topics recorded: {', '.join(set(weak_topics))}")


# ── Main entry point ──────────────────────────────────────────────────────────

def render_past_paper_mode(student: dict, db, llm):
    """Past Paper Battle Mode — upload, simulate, debate, report."""
    language = student.get("language", student.get("preferred_language", "English"))
    subject = student.get("subject", "Biology")

    defaults = {
        "pp_phase": "upload",
        "pp_current_q": 0,
        "pp_answers": [],
        "pp_evaluations": [],
        "pp_questions": [],
        "pp_meta": {},
        "pp_session_id": None,
        "pp_timer_start": None,
        "pp_elapsed": 0,
        "pp_debate_queue": [],
        "pp_debate_current": 0,
        "pp_debate_turn": 1,
        "pp_debate_history": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # ── PHASE: UPLOAD ─────────────────────────────────────────────────────────
    if st.session_state.pp_phase == "upload":
        st.markdown(
            """
            <div style="background:#1E3A5F;color:white;border-radius:12px;
                        padding:20px;margin-bottom:20px;">
              <h3 style="margin:0">⚔️ Past Paper Battle Mode</h3>
              <p style="margin:4px 0 0;opacity:.85">
                Upload a past exam paper. OmniScholar becomes your examiner.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            "Upload Past Paper PDF",
            type=["pdf"],
            help="Upload an A/L or university past paper in PDF format",
        )

        if uploaded:
            pdf_bytes = uploaded.read()
            with st.spinner("Extracting questions from PDF..."):
                try:
                    questions, meta = extract_questions_from_pdf(pdf_bytes)
                except Exception as exc:
                    st.error(f"Could not parse PDF: {exc}")
                    questions, meta = [], {}

            if not questions:
                st.warning(
                    "Could not automatically extract questions. Enter questions manually below."
                )
                n_questions = st.number_input("Number of questions", min_value=1, max_value=50, value=5)
                manual_questions = []
                for i in range(int(n_questions)):
                    with st.expander(f"Question {i + 1}"):
                        q_text = st.text_area(f"Question text", key=f"manual_q_{i}")
                        q_marks = st.number_input("Marks", min_value=1, max_value=20, value=2, key=f"manual_m_{i}")
                        manual_questions.append({
                            "number": i + 1,
                            "text": q_text,
                            "marks": q_marks,
                            "section": "Section A",
                        })
                if st.button("Start Battle with Manual Questions", type="primary"):
                    total_marks = sum(q["marks"] for q in manual_questions)
                    meta = {
                        "subject": subject,
                        "year": 2023,
                        "total_marks": total_marks,
                        "total_questions": len(manual_questions),
                        "estimated_minutes": len(manual_questions) * 2,
                    }
                    st.session_state.pp_questions = manual_questions
                    st.session_state.pp_meta = meta
                    st.session_state.pp_timer_start = time.time()
                    st.session_state.pp_phase = "exam"
                    st.rerun()
            else:
                st.success(f"✅ Extracted {meta['total_questions']} questions from PDF")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Questions", meta["total_questions"])
                col2.metric("Total Marks", meta["total_marks"])
                col3.metric("Est. Time", f"{meta['estimated_minutes']} min")
                col4.metric("Subject", meta["subject"])

                with st.expander("Preview extracted questions", expanded=False):
                    for q in questions[:5]:
                        st.markdown(f"**Q{q['number']}** ({q['marks']} marks) — *{q['section']}*")
                        st.markdown(f"> {q['text'][:200]}{'...' if len(q['text']) > 200 else ''}")
                    if len(questions) > 5:
                        st.caption(f"... and {len(questions) - 5} more questions")

                if st.button("⚔️ Start Battle Mode", type="primary"):
                    st.session_state.pp_questions = questions
                    st.session_state.pp_meta = meta
                    st.session_state.pp_timer_start = time.time()
                    st.session_state.pp_phase = "exam"
                    st.rerun()

    # ── PHASE: EXAM ───────────────────────────────────────────────────────────
    elif st.session_state.pp_phase == "exam":
        questions = st.session_state.pp_questions
        meta = st.session_state.pp_meta
        current_idx = st.session_state.pp_current_q
        total_q = len(questions)
        year = meta.get("year", 2023)

        if current_idx >= total_q:
            wrong_idxs = [
                i for i, ev in enumerate(st.session_state.pp_evaluations)
                if ev["verdict"] in ("WRONG", "PARTIAL")
            ]
            st.session_state.pp_elapsed = int(
                time.time() - (st.session_state.pp_timer_start or time.time())
            )
            st.session_state.pp_debate_queue = wrong_idxs
            st.session_state.pp_debate_current = 0
            st.session_state.pp_phase = "debate" if wrong_idxs else "report"
            st.rerun()
            return

        q = questions[current_idx]

        elapsed = int(time.time() - (st.session_state.pp_timer_start or time.time()))
        total_secs = meta.get("estimated_minutes", 90) * 60
        remaining_secs = max(0, total_secs - elapsed)
        remaining_mins = remaining_secs // 60
        remaining_s = remaining_secs % 60

        col_timer, col_progress = st.columns([1, 3])
        with col_timer:
            st.metric("⏱ Time Left", f"{remaining_mins:02d}:{remaining_s:02d}")
        with col_progress:
            progress_val = min(1.0, elapsed / max(total_secs, 1))
            color_note = "🟢" if progress_val < 0.6 else ("🟡" if progress_val < 0.85 else "🔴")
            st.progress(
                progress_val,
                text=f"{color_note} Question {current_idx + 1} of {total_q} — {meta['subject']} {year}",
            )

        st.markdown(
            f"""
            <div style="background:#1E3A5F;color:white;border-radius:10px;padding:20px;margin:12px 0;">
              <div style="font-size:12px;opacity:.7">
                QUESTION {q['number']} | {q['section']} | {q['marks']} marks
              </div>
              <div style="font-size:16px;margin-top:8px;line-height:1.6">{q['text']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        q_start_key = f"q_start_{current_idx}"
        if q_start_key not in st.session_state:
            st.session_state[q_start_key] = time.time()

        answer = st.text_area(
            f"Your answer (Q{q['number']}, {q['marks']} marks):",
            key=f"pp_ans_{current_idx}",
            height=120,
            placeholder="Write your answer here...",
        )

        col_submit, col_skip = st.columns([2, 1])
        with col_submit:
            submit = st.button("Submit Answer →", type="primary", use_container_width=True)
        with col_skip:
            skip = st.button("Skip (0 marks)", use_container_width=True)

        if submit or skip:
            final_answer = answer.strip() if (submit and answer.strip()) else "[No answer provided]"
            time_spent = int(time.time() - st.session_state.get(q_start_key, time.time()))

            with st.spinner("Examiner is marking..."):
                if skip or not answer.strip():
                    evaluation = {
                        "verdict": "WRONG",
                        "marks_awarded": 0,
                        "marks_available": q["marks"],
                        "feedback": "No answer provided.",
                        "raw": "",
                    }
                else:
                    evaluation = _call_examiner(llm, student, q, final_answer, subject, year, language)

            if st.session_state.pp_session_id is None:
                sid = db.save_past_paper_session(
                    student_id=student.get("id", student.get("student_id", "")),
                    paper_name=f"{year} {subject} Past Paper",
                    year=year,
                    subject=subject,
                    total_marks=meta.get("total_marks", 0),
                    score_achieved=0,
                    time_taken_seconds=0,
                    weak_sections=[],
                )
                st.session_state.pp_session_id = sid

            db.save_past_paper_question(
                session_id=st.session_state.pp_session_id,
                question_number=q["number"],
                question_text=q["text"],
                student_answer=final_answer,
                marks_awarded=evaluation["marks_awarded"],
                marks_available=q["marks"],
                time_spent_seconds=time_spent,
                verdict=evaluation["verdict"],
            )

            st.session_state.pp_answers.append(final_answer)
            st.session_state.pp_evaluations.append(evaluation)

            v = evaluation["verdict"]
            if v == "CORRECT":
                st.success(f"✅ {evaluation['feedback']} ({evaluation['marks_awarded']}/{q['marks']} marks)")
            elif v == "PARTIAL":
                st.warning(f"⚠️ {evaluation['feedback']} ({evaluation['marks_awarded']}/{q['marks']} marks)")
            else:
                st.error(f"✗ {evaluation['feedback']} (0/{q['marks']} marks)")

            st.session_state.pp_current_q = current_idx + 1
            time.sleep(1)
            st.rerun()

    # ── PHASE: DEBATE ─────────────────────────────────────────────────────────
    elif st.session_state.pp_phase == "debate":
        questions = st.session_state.pp_questions
        answers = st.session_state.pp_answers
        evaluations = st.session_state.pp_evaluations
        debate_queue = st.session_state.pp_debate_queue
        debate_idx = st.session_state.pp_debate_current

        if debate_idx >= len(debate_queue):
            st.session_state.pp_phase = "report"
            st.rerun()
            return

        q_idx = debate_queue[debate_idx]
        q = questions[q_idx]
        ev = evaluations[q_idx]
        turn = st.session_state.pp_debate_turn

        st.markdown(
            """
            <div style="background:#92400E;color:white;border-radius:10px;
                        padding:16px;margin-bottom:12px;">
              <h4 style="margin:0">🧠 Socratic Debate — OmniScholar argues back</h4>
              <p style="margin:4px 0 0;opacity:.85">Reason your way to the correct answer.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.progress(
            debate_idx / max(len(debate_queue), 1),
            text=f"Debate {debate_idx + 1} of {len(debate_queue)} | Turn {turn}/3",
        )

        st.markdown(
            f"""
            <div style="background:#1E3A5F;color:white;border-radius:8px;padding:16px;margin:8px 0;">
              <div style="font-size:11px;opacity:.7">Q{q['number']} — {q['section']} — {q['marks']} marks</div>
              <div style="margin-top:6px">{q['text']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info(f"**Your answer:** {answers[q_idx]}")
        st.warning(f"**Examiner verdict:** {ev['verdict']} — {ev['feedback']}")

        for msg in st.session_state.pp_debate_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if not st.session_state.pp_debate_history:
            with st.spinner("OmniScholar is preparing the Socratic challenge..."):
                response = _call_socratic(
                    llm, student, q, answers[q_idx], turn,
                    student.get("subject", "Biology"), language, [],
                )
            st.session_state.pp_debate_history.append({"role": "assistant", "content": response})
            st.rerun()
        elif turn < 3:
            user_reply = st.chat_input("Your reasoning...")
            if user_reply:
                st.session_state.pp_debate_history.append({"role": "user", "content": user_reply})
                new_turn = turn + 1
                st.session_state.pp_debate_turn = new_turn
                with st.spinner("OmniScholar is thinking..."):
                    response = _call_socratic(
                        llm, student, q, user_reply, new_turn,
                        student.get("subject", "Biology"), language,
                        st.session_state.pp_debate_history,
                    )
                st.session_state.pp_debate_history.append({"role": "assistant", "content": response})
                st.rerun()
        else:
            st.error("Turn limit reached. Here is the full explanation:")
            with st.spinner("Generating full explanation..."):
                try:
                    explanation = llm.chat(
                        messages=[{
                            "role": "user",
                            "content": (
                                f"Give the complete correct answer with examiner-level explanation "
                                f"for: {q['text']}\nRespond in {language}. Keep scientific terms in English."
                            ),
                        }],
                        system_prompt=THREE_A_SOCRATIC_PROMPT.format(
                            subject=student.get("subject", "Biology"),
                            language=language,
                            name=student.get("name", "Student"),
                            days_remaining=student.get("days_remaining", "N/A"),
                            weak_chapters="N/A",
                            probability="N/A",
                        ),
                        temperature=0.3,
                    )
                except Exception as exc:
                    explanation = f"Explanation unavailable: {exc}"
            st.success(explanation)

            if st.button("Next Question →", type="primary"):
                st.session_state.pp_debate_current = debate_idx + 1
                st.session_state.pp_debate_turn = 1
                st.session_state.pp_debate_history = []
                st.rerun()

    # ── PHASE: REPORT ─────────────────────────────────────────────────────────
    elif st.session_state.pp_phase == "report":
        meta = st.session_state.pp_meta
        year = meta.get("year", 2023)
        _render_report(
            student=student, db=db, llm=llm,
            session_id=st.session_state.pp_session_id,
            questions=st.session_state.pp_questions,
            answers=st.session_state.pp_answers,
            evaluations=st.session_state.pp_evaluations,
            subject=student.get("subject", meta.get("subject", "Biology")),
            year=year, language=language, meta=meta,
        )

        if st.button("🔄 Start New Battle", type="primary"):
            for key in list(st.session_state.keys()):
                if key.startswith("pp_"):
                    del st.session_state[key]
            st.rerun()
