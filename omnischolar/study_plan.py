"""
study_plan.py — Spaced Repetition Study Planner for OmniScholar

Generates a day-by-day study schedule from today to exam date,
prioritising weak areas in the first 60% of days and locking the
final 3 days to revision only.
"""

import datetime

import streamlit as st


def render_study_plan_mode(student: dict, ollama_client, db) -> None:
    """
    Render the Study Plan mode.

    Parameters
    ----------
    student       : student profile dict from session_state
    ollama_client : OllamaClient instance
    db            : Database instance (can be None for legacy function-based db)
    """
    st.markdown("## 📅 Study Plan")
    st.caption(
        "AI-generated spaced repetition schedule tailored to your exam date "
        "and weak areas."
    )

    subject   = student.get("subject", "Computer Science")
    name      = student.get("name",    "Student")
    language  = student.get("language", student.get("preferred_language", "english"))
    exam_date = student.get("exam_date", "")
    weak_areas = student.get("weak_areas", [])
    if isinstance(weak_areas, str):
        weak_areas = [w.strip() for w in weak_areas.split(",") if w.strip()]

    # Parse days remaining
    try:
        exam_dt   = datetime.date.fromisoformat(exam_date)
        today     = datetime.date.today()
        days_left = (exam_dt - today).days
    except Exception:
        days_left = student.get("days_remaining", 30)
        try:
            days_left = int(days_left)
        except Exception:
            days_left = 30

    st.info(f"📅 **{days_left}** days until {subject} exam · "
            f"Weak areas: {', '.join(weak_areas) or 'none set'}")

    if st.button("🗓 Generate My Study Plan", type="primary"):
        with st.spinner("Building your personalised schedule..."):
            plan_text = _generate_plan(
                name, subject, days_left, weak_areas, language, ollama_client
            )
        st.session_state["study_plan_text"] = plan_text

    plan_text = st.session_state.get("study_plan_text", "")
    if plan_text:
        st.markdown("---")
        st.markdown(plan_text)
    else:
        _render_static_preview(days_left, weak_areas, subject)


def _generate_plan(name, subject, days_left, weak_areas, language, llm) -> str:
    """Call LLM to generate a study plan; fall back to static template."""
    weak_str = ", ".join(weak_areas) if weak_areas else "general revision"
    prompt = (
        f"Create a {days_left}-day study plan for {name} preparing for {subject}.\n"
        f"Weak areas (prioritise in first 60% of days): {weak_str}\n"
        f"Final 3 days: revision only, no new topics.\n"
        f"Language: {language}\n"
        f"Format as a day-by-day table: Day | Focus Topic | Activity | Duration\n"
        f"Keep it concise — max 30 rows."
    )
    try:
        if hasattr(llm, "fast_chat"):
            return llm.fast_chat(
                message=prompt,
                system="You are an expert study planner. Return a clean markdown table.",
                max_tokens=1024,
            )
        else:
            resp = llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
            )
            return resp
    except Exception as exc:
        return _static_plan(days_left, weak_areas, subject)


def _static_plan(days_left: int, weak_areas: list, subject: str) -> str:
    """Generate a minimal static plan when LLM is unavailable."""
    lines = [f"### {subject} Study Plan — {days_left} Days\n"]
    lines.append("| Day | Focus | Activity | Duration |")
    lines.append("|-----|-------|----------|----------|")

    cutoff  = int(days_left * 0.6)
    final_3 = days_left - 3

    for d in range(1, days_left + 1):
        if d > final_3:
            focus    = "Full Revision"
            activity = "Past papers + mark scheme review"
        elif d <= cutoff and weak_areas:
            focus    = weak_areas[(d - 1) % len(weak_areas)]
            activity = "Deep study + practice questions"
        else:
            focus    = f"{subject} core topics"
            activity = "Notes review + flashcards"
        lines.append(f"| {d} | {focus} | {activity} | 2 hours |")

    return "\n".join(lines)


def _render_static_preview(days_left: int, weak_areas: list, subject: str) -> None:
    """Show a preview card before the plan is generated."""
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#0D1B35,#111929);
                    border:1px solid rgba(0,212,255,0.2);border-radius:12px;
                    padding:20px;text-align:center;margin:16px 0;">
          <div style="font-family:Orbitron,monospace;font-size:0.65rem;
                      color:#00D4FF;letter-spacing:0.15em;text-transform:uppercase;
                      margin-bottom:8px;">YOUR PLAN PREVIEW</div>
          <div style="color:#A0B4D6;font-size:0.9rem;line-height:1.7;">
            📚 First {int(days_left * 0.6)} days — weak areas<br>
            📝 Middle {days_left - int(days_left * 0.6) - 3} days — standard topics<br>
            🔁 Final 3 days — past papers &amp; revision only
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
# study_plan.py — Spaced repetition engine
# OmniScholar | stub — full implementation coming

import streamlit as st


# study_plan.py — Spaced Repetition Study Planner
# OmniScholar | Gemma 4 Good Hackathon

import datetime
import json

import streamlit as st

from rag import retrieve_context


# ── Scheduling algorithm ──────────────────────────────────────────────────────

_MASTERY_CONFIG = {
    "Critical":      {"range": (0, 40),   "interval": 2, "label": "🔴 URGENT",   "color": "#DC2626"},
    "Developing":    {"range": (40, 70),  "interval": 3, "label": "🟠 HIGH",     "color": "#D97706"},
    "Consolidating": {"range": (70, 85),  "interval": 5, "label": "🟡 MEDIUM",   "color": "#CA8A04"},
    "Strong":        {"range": (85, 101), "interval": 0, "label": "🟢 LOW",      "color": "#16A34A"},
}


def _classify_mastery(score: float) -> str:
    for label, cfg in _MASTERY_CONFIG.items():
        lo, hi = cfg["range"]
        if lo <= score < hi:
            return label
    return "Strong"


def build_schedule(chapter_scores: list, days_remaining: int) -> list:
    """
    Build a day-by-day schedule from today.
    Returns list of day dicts: {date, day_num, slots: [{topic, mastery, mastery_pct, mode, reason}]}
    """
    if not chapter_scores:
        return []

    # Classify all chapters
    classified = []
    for ch in chapter_scores:
        name = ch.get("name", "Unknown Chapter")
        score = ch.get("score", 0)
        mastery = _classify_mastery(score)
        cfg = _MASTERY_CONFIG[mastery]
        if mastery == "Strong":
            continue  # skip strong topics
        classified.append({
            "name": name,
            "score": score,
            "mastery": mastery,
            "interval": cfg["interval"],
            "next_day": 1,  # when to next schedule this topic
        })

    # Sort by score ascending (weakest first)
    classified.sort(key=lambda x: x["score"])

    schedule = []
    today = datetime.date.today()

    for day_num in range(1, days_remaining + 1):
        day_date = today + datetime.timedelta(days=day_num - 1)
        slots = []

        # Final 2 days: mock + weak review only
        if day_num >= days_remaining - 1:
            if day_num == days_remaining - 1:
                slots.append({
                    "topic": "Full Mock Paper",
                    "mastery": "Critical",
                    "mastery_pct": 0,
                    "mode": "TEST_ME",
                    "reason": "Second-to-last day — full mock exam practice",
                    "estimated_minutes": 90,
                })
            else:
                weak_names = [c["name"] for c in classified[:3] if c["score"] < 70]
                for w in weak_names[:2]:
                    slots.append({
                        "topic": w,
                        "mastery": _classify_mastery(next((c["score"] for c in classified if c["name"] == w), 0)),
                        "mastery_pct": next((c["score"] for c in classified if c["name"] == w), 0),
                        "mode": "REVISE",
                        "reason": "Final day — weak topic rapid review only",
                        "estimated_minutes": 30,
                    })
        else:
            # Normal scheduling: pick topics due on this day
            due_today = [c for c in classified if c["next_day"] <= day_num]
            due_today = due_today[:3]  # max 3 topics per day
            for topic in due_today:
                score = topic["score"]
                if score < 40:
                    mode = "LEARN"
                elif score < 70:
                    mode = "REVISE"
                else:
                    mode = "TEST_ME"
                reason = f"{topic['mastery']} mastery ({score:.0f}%) — scheduled every {topic['interval']} days"
                slots.append({
                    "topic": topic["name"],
                    "mastery": topic["mastery"],
                    "mastery_pct": score,
                    "mode": mode,
                    "reason": reason,
                    "estimated_minutes": {"LEARN": 45, "REVISE": 30, "TEST_ME": 20}.get(mode, 30),
                })
                # Advance next scheduling day
                topic["next_day"] = day_num + topic["interval"]

        if slots:
            schedule.append({
                "day_num": day_num,
                "date": day_date,
                "slots": slots,
            })

    return schedule


def get_todays_topic(student: dict, db) -> str | None:
    """Return today's primary topic for the daily launch prompt in app.py."""
    try:
        subject = student.get("subject", "")
        sid = student.get("id", student.get("student_id", ""))
        days_remaining = student.get("days_remaining", 14)
        chapters = db.get_chapter_scores_by_subject(sid, subject)
        schedule = build_schedule(chapters, days_remaining)
        today = datetime.date.today()
        for day in schedule:
            if day["date"] == today and day["slots"]:
                return day["slots"][0]["topic"]
    except Exception:
        pass
    return None


# ── Main entry point ──────────────────────────────────────────────────────────

def render_study_plan_mode(student: dict, db, llm):
    """Spaced Repetition Study Planner — day-by-day adaptive schedule."""
    language = student.get("language", student.get("preferred_language", "English"))
    subject = student.get("subject", "Biology")
    sid = student.get("id", student.get("student_id", ""))
    exam_date_str = student.get("exam_date", str(datetime.date.today() + datetime.timedelta(days=14)))

    try:
        exam_date = datetime.date.fromisoformat(exam_date_str)
    except ValueError:
        exam_date = datetime.date.today() + datetime.timedelta(days=14)

    today = datetime.date.today()
    days_remaining = max(1, (exam_date - today).days)

    st.markdown(
        """
        <div style="background:#1E3A5F;color:white;border-radius:12px;
                    padding:20px;margin-bottom:20px;">
          <h3 style="margin:0">📅 Adaptive Study Plan</h3>
          <p style="margin:4px 0 0;opacity:.85">
            Spaced repetition schedule built from your quiz performance.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Load chapter scores
    chapters = db.get_chapter_scores_by_subject(sid, subject)

    if not chapters:
        st.info(
            f"No quiz data yet for {subject}. Complete some quizzes in TEST_ME mode first, "
            "then return here for a personalised schedule."
        )
        st.markdown("**Quick start:** Go to 📝 Test Me mode and answer a few questions to seed your schedule.")
        return

    # Mastery overview
    st.markdown("### Current Mastery Overview")
    col1, col2, col3, col4 = st.columns(4)
    critical_count = sum(1 for c in chapters if c["score"] < 40)
    developing_count = sum(1 for c in chapters if 40 <= c["score"] < 70)
    consolidating_count = sum(1 for c in chapters if 70 <= c["score"] < 85)
    strong_count = sum(1 for c in chapters if c["score"] >= 85)
    col1.metric("🔴 Critical", critical_count)
    col2.metric("🟠 Developing", developing_count)
    col3.metric("🟡 Consolidating", consolidating_count)
    col4.metric("🟢 Strong", strong_count)

    # Chapter mastery bars
    with st.expander("Chapter Mastery Details", expanded=False):
        for ch in chapters:
            score = ch["score"]
            mastery = _classify_mastery(score)
            cfg = _MASTERY_CONFIG[mastery]
            st.progress(
                score / 100,
                text=f"{ch['name']}: {score:.0f}% — {cfg['label']}",
            )

    # Build schedule
    schedule = build_schedule(chapters, days_remaining)

    if not schedule:
        st.success("All topics are at Strong level! Focus on full mock papers in final days.")
        return

    st.markdown(f"### Your {days_remaining}-Day Study Plan")
    st.caption(f"Exam: {exam_date.strftime('%B %d, %Y')} | {days_remaining} days remaining")

    today_shown = False
    for day in schedule:
        is_today = day["date"] == today
        is_final = day["day_num"] >= days_remaining - 1

        if is_today and not today_shown:
            st.markdown("---")
            st.markdown("**⬇ TODAY ⬇**")
            today_shown = True

        label = day["date"].strftime("%A, %B %d")
        if is_today:
            label = f"📍 {label} — TODAY"
        elif is_final:
            label = f"🏁 {label} — FINAL SPRINT"

        total_minutes = sum(s["estimated_minutes"] for s in day["slots"])

        with st.expander(
            f"Day {day['day_num']} — {label} ({total_minutes} min)",
            expanded=is_today,
        ):
            for slot_idx, slot in enumerate(day["slots"]):
                cfg = _MASTERY_CONFIG.get(slot["mastery"], _MASTERY_CONFIG["Developing"])
                priority_label = "PRIMARY" if slot_idx == 0 else "SECONDARY"

                st.markdown(
                    f"""
                    <div style="border-left:4px solid {cfg['color']};
                                padding:10px 14px;margin:6px 0;border-radius:0 8px 8px 0;
                                background:#F8FAFC;">
                      <div style="font-size:11px;color:#64748B">{priority_label} · {slot['mode']} · {slot['estimated_minutes']} min</div>
                      <div style="font-weight:600;color:#0F172A;font-size:15px">{slot['topic']}</div>
                      <div style="font-size:12px;color:#64748B;margin-top:2px">{slot['reason']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if is_today:
                primary_topic = day["slots"][0]["topic"]
                primary_mode = day["slots"][0]["mode"]
                st.info(
                    f"📌 Today's focus: **{primary_topic}** — Use {primary_mode} mode to study this topic."
                )

    # AI-enhanced plan summary
    st.markdown("---")
    st.markdown("### 🤖 Personalised Study Advice")
    with st.spinner("Generating personalised advice..."):
        weak_chapters = [c["name"] for c in chapters if c["score"] < 60][:5]
        context, _ = retrieve_context(
            f"{subject} study plan revision strategy",
            subject=subject, n_results=3,
        )
        ctx_block = f"\nContext from materials:\n{context}" if context else ""

        try:
            advice = llm.fast_chat(
                message=f"Give 3-sentence study advice for {student.get('name','Student')} "
                        f"studying {subject} with {days_remaining} days left. "
                        f"Weakest chapters: {', '.join(weak_chapters[:3]) or 'none yet'}. "
                        f"Be specific. Respond in {language}.",
                system="You are a study coach. Be direct and concise.",
                max_tokens=200,
            )
        except Exception:
            advice = "Could not generate advice — please ensure Ollama is running."

    st.info(advice)
    if context:
        st.caption("📎 Based on your uploaded study materials")
    else:
        st.caption("📎 From model general knowledge — upload course materials for grounded advice")


def get_todays_topic(student: dict, db=None) -> str:
    """Return today's focus topic from the student's weak_areas, rotating by day-of-year."""
    import datetime
    weak = student.get("weak_areas", [])
    if isinstance(weak, str):
        weak = [w.strip() for w in weak.split(",") if w.strip()]
    if not weak:
        return ""
    day_idx = datetime.date.today().timetuple().tm_yday
    return weak[day_idx % len(weak)]


def build_schedule(student: dict, db=None) -> list:
    """Return a list of {"date": str, "topic": str} dicts for each remaining study day."""
    import datetime
    weak = student.get("weak_areas", [])
    if isinstance(weak, str):
        weak = [w.strip() for w in weak.split(",") if w.strip()]
    today = datetime.date.today()
    days = int(student.get("days_remaining", 30))
    return [
        {
            "date": str(today + datetime.timedelta(days=i)),
            "topic": weak[i % len(weak)] if weak else student.get("subject", "Revision"),
        }
        for i in range(days)
    ]
