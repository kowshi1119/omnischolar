# study_plan.py — Spaced Repetition Study Planner
# OmniScholar | Gemma 4 Good Hackathon

import datetime

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

