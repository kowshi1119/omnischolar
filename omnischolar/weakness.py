"""
weakness.py — Misconception & Weak Area Dashboard for OmniScholar

Analyses quiz history to identify persistent misconceptions and renders
a visual breakdown ranked by severity.
"""

import streamlit as st


def render_weakness_mode(student: dict, ollama_client, db) -> None:
    """
    Render the Weakness Analysis / Misconception Dashboard mode.

    Parameters
    ----------
    student       : student profile dict
    ollama_client : OllamaClient instance
    db            : Database instance
    """
    st.markdown("## 🔍 Weak Area Analysis")
    st.caption(
        "Identifies persistent misconceptions from your quiz history "
        "and generates targeted remediation."
    )

    subject    = student.get("subject",   "Computer Science")
    name       = student.get("name",      "Student")
    language   = student.get("language",  student.get("preferred_language", "english"))
    student_id = student.get("student_id", "")

    # Fetch quiz history
    try:
        if db and hasattr(db, "get_quiz_history"):
            history = db.get_quiz_history(student_id)
        else:
            from database import get_quiz_history
            history = get_quiz_history(student_id)
    except Exception:
        history = []

    weak_areas = student.get("weak_areas", [])
    if isinstance(weak_areas, str):
        weak_areas = [w.strip() for w in weak_areas.split(",") if w.strip()]

    if not history and not weak_areas:
        st.info("No quiz history yet. Complete some quizzes first, then return here.")
        return

    # ── Summary metrics ────────────────────────────────────────────────────────
    if history:
        scores = [row[1] / max(row[2], 1) * 100 for row in history if row[2] > 0]
        avg    = sum(scores) / len(scores) if scores else 0
        misconceptions = [row[3] for row in history if row[3] and row[3] != "null"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Quiz Sessions",     len(history))
        col2.metric("Average Score",     f"{avg:.0f}%")
        col3.metric("Misconceptions",    len(misconceptions))

        # Topic breakdown
        topic_scores: dict[str, list] = {}
        for row in history:
            topic = row[0]
            pct   = row[1] / max(row[2], 1) * 100
            topic_scores.setdefault(topic, []).append(pct)

        topic_avgs = {t: sum(v) / len(v) for t, v in topic_scores.items()}
        sorted_topics = sorted(topic_avgs.items(), key=lambda x: x[1])

        if sorted_topics:
            st.markdown("### Topic Scores (weakest first)")
            for topic, score in sorted_topics:
                bar_color = "#00C850" if score >= 75 else "#FFB800" if score >= 50 else "#EF4444"
                st.markdown(
                    f"""
                    <div style="margin:4px 0;">
                      <div style="display:flex;justify-content:space-between;
                                  margin-bottom:3px;">
                        <span style="color:#A0B4D6;font-size:0.82rem;">{topic}</span>
                        <span style="color:{bar_color};font-size:0.72rem;
                                     font-family:Orbitron,monospace;">{score:.0f}%</span>
                      </div>
                      <div style="background:#1A2540;border-radius:4px;
                                  height:6px;overflow:hidden;">
                        <div style="width:{score:.0f}%;height:100%;border-radius:4px;
                                    background:{bar_color};"></div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Misconception list
        if misconceptions:
            st.markdown("### Persistent Misconceptions")
            for m in set(misconceptions):
                st.error(f"⚠ {m}")

    # ── AI remediation ─────────────────────────────────────────────────────────
    if weak_areas:
        st.markdown("### AI Remediation Plan")
        remed_key = f"remed_{subject}"
        if st.button("🤖 Generate Remediation Plan", type="primary"):
            weak_str = ", ".join(weak_areas)
            prompt   = (
                f"Student: {name} | Subject: {subject} | Language: {language}\n"
                f"Weak areas: {weak_str}\n\n"
                f"For EACH weak area produce a ZPD diagnostic block:\n"
                f"DIAGNOSIS: What is the exact misconception?\n"
                f"PREREQUISITE: What concept must be solid before fixing this?\n"
                f"SCAFFOLD STEP 1: Simplest example that makes the gap visible\n"
                f"SCAFFOLD STEP 2: Intermediate worked example closing the gap\n"
                f"SCAFFOLD STEP 3: Full-complexity problem at the student's target level\n"
                f"CHECK QUESTION: One short exam-style question to confirm mastery\n\n"
                f"Rules:\n"
                f"- Respond entirely in {language}\n"
                f"- Keep technical terms in English even in Sinhala/Tamil\n"
                f"- Each block under 120 words\n"
                f"- Do NOT give the answer to the CHECK QUESTION"
            )
            with st.spinner("Analysing misconceptions..."):
                try:
                    if hasattr(ollama_client, "fast_chat"):
                        plan = ollama_client.fast_chat(
                            message=prompt,
                            system="You are an expert tutor identifying common misconceptions.",
                            max_tokens=1024,
                        )
                    else:
                        plan = ollama_client.chat(
                            messages=[{"role": "user", "content": prompt}]
                        )
                    st.session_state[remed_key] = plan
                except Exception as exc:
                    st.error(f"Could not generate plan: {exc}")

        plan = st.session_state.get(remed_key, "")
        if plan:
            st.markdown(plan)
# weakness.py — Weakness detection and error pattern analysis
# OmniScholar | stub — full implementation coming

import streamlit as st


# weakness.py — Misconception Pattern Analysis Dashboard
# OmniScholar | Gemma 4 Good Hackathon

import datetime

import streamlit as st

from rag import retrieve_context


_ERROR_TYPE_LABELS = {
    "conceptual_confusion": "Conceptual Confusion",
    "factual_error":        "Factual Error",
    "process_confusion":    "Process Confusion",
    "direction_error":      "Direction Error",
    "terminology_error":    "Terminology Error",
    "calculation_error":    "Calculation Error",
}

_ERROR_COLORS = {
    "conceptual_confusion": "#7C3AED",
    "factual_error":        "#DC2626",
    "process_confusion":    "#D97706",
    "direction_error":      "#0EA5E9",
    "terminology_error":    "#CA8A04",
    "calculation_error":    "#16A34A",
}

# Pattern descriptions for the Examiner Warning Panel
_EXAMINER_WARNINGS = [
    "Confusing active transport with facilitated diffusion — costs 2–4 marks per paper.",
    "Reversing the direction of osmosis under hypertonic conditions — common 1-mark error.",
    "Missing the role of ATP in active transport explanations — marks withheld.",
]


def _render_heat_map(chapters: list, weak_concepts: list):
    """Render a chapter × error-frequency heat map using st.dataframe."""
    if not weak_concepts:
        return

    # Build topic → error_type → count mapping
    topic_errors: dict = {}
    for wc in weak_concepts:
        topic = wc.get("topic", "Unknown")
        etype = wc.get("error_type", "factual_error")
        freq = wc.get("frequency", 1)
        if topic not in topic_errors:
            topic_errors[topic] = {}
        topic_errors[topic][etype] = topic_errors[topic].get(etype, 0) + freq

    if not topic_errors:
        return

    # Build a simple display table
    rows = []
    for topic, errors in topic_errors.items():
        total_errors = sum(errors.values())
        dominant = max(errors, key=errors.get)
        rows.append({
            "Topic / Section": topic,
            "Total Errors": total_errors,
            "Dominant Error Type": _ERROR_TYPE_LABELS.get(dominant, dominant),
            "Frequency": "●" * min(total_errors, 5),
        })

    rows.sort(key=lambda r: r["Total Errors"], reverse=True)

    st.markdown("#### 🗺️ Error Frequency Map")
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Total Errors": st.column_config.NumberColumn(format="%d"),
            "Frequency": st.column_config.TextColumn(),
        },
    )


def _render_weakness_cards(weak_concepts: list, student: dict = None):
    """Render top 3 critical weakness cards, with NIE unit mapping for A/L students."""
    if not weak_concepts:
        st.info("No weakness data yet. Complete quizzes and past papers to build your profile.")
        return

    # Load syllabus for NIE unit matching (A/L students only)
    nie_chapters: list = []
    if student and student.get("student_type") == "A/L Student":
        try:
            import os
            import json as _json
            from al_config import STREAM_FOLDER_NAMES, SUBJECT_FILE_SLUGS
            al_stream = student.get("al_stream", "")
            al_subjects = student.get("al_subjects") or []
            _data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
            for subj in al_subjects[:1]:  # use first subject as primary
                stream_folder = STREAM_FOLDER_NAMES.get(al_stream, "")
                subject_slug = SUBJECT_FILE_SLUGS.get(subj, subj.lower().replace(" ", "_"))
                path = os.path.join(_data_dir, "al_syllabus", stream_folder, f"{subject_slug}.json")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        nie_chapters = _json.load(f).get("chapters", [])
                    break
        except Exception:
            nie_chapters = []

    def _find_nie_unit(concept: str, topic: str) -> str:
        if not nie_chapters:
            return ""
        query = f"{concept} {topic}".lower()
        best_match = None
        best_score = 0
        for ch in nie_chapters:
            ch_text = f"{ch['name']} {' '.join(ch.get('subtopics', []))}".lower()
            # Simple word overlap score
            query_words = set(query.split())
            ch_words = set(ch_text.split())
            score = len(query_words & ch_words)
            if score > best_score:
                best_score = score
                best_match = ch
        if best_match and best_score > 0:
            freq = best_match.get("past_paper_frequency_10yr", 0)
            return (f"NIE {best_match['unit_id']} — {best_match['name'].split('—')[-1].strip()} "
                    f"(appeared in {freq}/10 A/L papers)")
        return ""

    top_3 = sorted(weak_concepts, key=lambda w: w.get("frequency", 0), reverse=True)[:3]

    st.markdown("#### ⚠️ Top 3 Critical Weaknesses")
    for i, wc in enumerate(top_3, start=1):
        concept = wc.get("concept", "Unknown concept")
        topic = wc.get("topic", "Unknown topic")
        error_type = wc.get("error_type", "factual_error")
        frequency = wc.get("frequency", 1)
        last_seen = wc.get("last_seen", "Unknown")
        color = _ERROR_COLORS.get(error_type, "#DC2626")
        label = _ERROR_TYPE_LABELS.get(error_type, error_type)
        nie_unit = _find_nie_unit(concept, topic)

        nie_html = ""
        if nie_unit:
            nie_html = (
                f'<div style="font-size:11px;color:#00D4FF;margin-top:4px;'
                f'font-family:JetBrains Mono,monospace">'
                f'📋 {nie_unit}</div>'
            )

        st.markdown(
            f"""
            <div style="border-left:5px solid {color};padding:14px 16px;
                        margin:8px 0;border-radius:0 10px 10px 0;background:#FEF2F2;">
              <div style="font-size:11px;color:#64748B">
                #{i} CRITICAL WEAKNESS · {label}
              </div>
              <div style="font-weight:700;color:#0F172A;font-size:15px;margin:4px 0">
                {concept[:80]}
              </div>
              <div style="font-size:13px;color:#64748B">
                Topic: {topic} · Seen {frequency}x · Last: {last_seen}
              </div>
              {nie_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"📖 Revise '{concept[:30]}...' Now", key=f"revise_btn_{wc.get('id', i)}"):
            st.session_state["revise_concept"] = concept
            st.info(f"Go to REVISE mode and ask about: '{concept}'")


def _render_resolution_tracker(student_id: str, db):
    """Show concepts where student has since answered correctly 3+ times."""
    resolved = db.get_weak_concepts(student_id, resolved=True)
    if not resolved:
        return

    st.markdown("#### ✅ Resolved Weaknesses")
    for wc in resolved[:5]:
        concept = wc.get("concept", "")
        topic = wc.get("topic", "")
        st.markdown(
            f"""
            <div style="border-left:4px solid #16A34A;padding:10px 14px;
                        margin:4px 0;border-radius:0 8px 8px 0;background:#F0FDF4;">
              <span style="color:#16A34A;font-weight:600">✓ {concept[:60]}</span>
              <span style="color:#64748B;font-size:12px"> — {topic}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ── Main entry point ──────────────────────────────────────────────────────────

def render_weakness_mode(student: dict, db, llm):
    """Weakness Analysis Dashboard — misconception patterns and remediation."""
    language = student.get("language", student.get("preferred_language", "English"))
    subject = student.get("subject", "Biology")
    sid = student.get("id", student.get("student_id", ""))

    st.markdown(
        """
        <div style="background:#1E3A5F;color:white;border-radius:12px;
                    padding:20px;margin-bottom:20px;">
          <h3 style="margin:0">🔍 Weakness Analysis</h3>
          <p style="margin:4px 0 0;opacity:.85">
            Misconception patterns detected across all your quizzes and past papers.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Load data
    weak_concepts = db.get_weak_concepts(sid, resolved=False)
    chapters = db.get_chapter_scores_by_subject(sid, subject)

    if not weak_concepts and not chapters:
        st.info(
            "No weakness data yet for this student. "
            "Complete quizzes in TEST_ME mode and Past Paper Battle Mode to build your weakness profile."
        )
        return

    # Summary stats
    col1, col2, col3 = st.columns(3)
    col1.metric("Active Weaknesses", len(weak_concepts))
    col2.metric("Topics Affected", len({w.get("topic") for w in weak_concepts}))
    resolved_count = len(db.get_weak_concepts(sid, resolved=True))
    col3.metric("Resolved ✓", resolved_count)

    # Heat map
    if weak_concepts or chapters:
        _render_heat_map(chapters, weak_concepts)

    # Top 3 weakness cards
    _render_weakness_cards(weak_concepts, student=student)

    # Examiner Warning Panel
    if weak_concepts:
        st.markdown("---")
        st.markdown("#### 🎯 Examiner Warning Panel")
        st.markdown("*These patterns cost students marks most in A/L examinations:*")

        # Try to get subject-specific warnings from LLM
        with st.spinner("Fetching examiner insights..."):
            top_concepts = [w.get("concept", "") for w in weak_concepts[:3]]
            context, _ = retrieve_context(
                f"{subject} common exam mistakes misconceptions",
                subject=subject, n_results=3,
            )
            try:
                warnings_raw = llm.fast_chat(
                    message=f"List exactly 3 patterns that cost {subject} students marks. "
                            f"Focus on: {', '.join(top_concepts[:2])}. "
                            f"One sentence each. Numbered 1-3.",
                    system="Be concise.",
                    max_tokens=150,
                )
                warning_lines = [
                    line.strip() for line in warnings_raw.split("\n")
                    if line.strip() and line.strip()[0].isdigit()
                ]
                if not warning_lines:
                    warning_lines = _EXAMINER_WARNINGS
            except Exception:
                warning_lines = _EXAMINER_WARNINGS

        for warn in warning_lines[:3]:
            st.warning(f"⚠️ {warn}")

        if context:
            st.caption("📎 Based on your uploaded study materials")
        else:
            st.caption("📎 From model general knowledge — upload course materials for grounded analysis")

    # Resolution tracker
    st.markdown("---")
    _render_resolution_tracker(sid, db)

    # Mark as resolved button
    if weak_concepts:
        st.markdown("---")
        st.markdown("#### Mark as Resolved")
        concept_options = {
            f"{w.get('concept', '')[:50]} (#{w.get('id')})": w.get("id")
            for w in weak_concepts
        }
        selected = st.selectbox(
            "Select a concept you've mastered:",
            options=list(concept_options.keys()),
        )
        if st.button("✅ Mark as Resolved", type="secondary"):
            concept_id = concept_options[selected]
            db.resolve_concept(concept_id)
            st.success(f"Marked as resolved! Great progress.")
            st.rerun()
