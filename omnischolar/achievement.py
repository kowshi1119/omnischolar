"""
achievement.py — OmniScholar 3A Probability Engine

Estimates Sri Lanka A/L 3A probability and renders the exam readiness
dashboard.  All calculations are offline, heuristic-based.
"""

import datetime
import streamlit as st

# ── A-grade thresholds by subject (Sri Lanka A/L typical cutoffs) ─────────────
_A_THRESHOLDS: dict[str, int] = {
    "Biology":           78,
    "Chemistry":         75,
    "Physics":           72,
    "Combined Maths":    70,
    "Mathematics":       70,
    "Computer Science":  78,
    "Information Technology": 75,
    "Business Studies":  72,
    "Economics":         72,
    "Accounting":        70,
    "default":           78,
}


def get_a_grade_threshold(subject: str) -> int:
    """Return the minimum % needed for an A in the given subject."""
    return _A_THRESHOLDS.get(subject, _A_THRESHOLDS["default"])


# ── Milestone badges (3 items — one per A grade needed for 3A) ───────────────
MILESTONE_BADGES: list[dict] = [
    {
        "id":    "first_a",
        "label": "First A",
        "icon":  "⭐",
        "desc":  "First subject reaches A-grade threshold",
        "color": "#00D4FF",
    },
    {
        "id":    "double_a",
        "label": "Double A",
        "icon":  "🌟",
        "desc":  "Two subjects at A-grade threshold",
        "color": "#FFB800",
    },
    {
        "id":    "triple_a",
        "label": "3A Achieved",
        "icon":  "🏆",
        "desc":  "All three subjects at A-grade threshold — 3A!",
        "color": "#00C850",
    },
]


def compute_3a_probability(subject_scores: dict[str, float],
                            days_left: int,
                            streak: int = 0) -> dict:
    """
    Estimate probability of achieving 3A (A grade in all subjects).

    Parameters
    ----------
    subject_scores : {subject_name: current_readiness_pct}
    days_left      : calendar days until exam
    streak         : consecutive daily study days

    Returns
    -------
    dict with keys: probability, subjects_on_track, recommendation
    """
    if not subject_scores:
        return {"probability": 0, "subjects_on_track": 0, "recommendation": "Set up your subjects."}

    on_track = 0
    gaps = []
    for subject, score in subject_scores.items():
        threshold = get_a_grade_threshold(subject)
        if score >= threshold:
            on_track += 1
        else:
            gaps.append(threshold - score)

    base_prob = (on_track / max(len(subject_scores), 1)) * 100

    # Boost for days remaining (more time = higher probability of catching up)
    time_factor = min(1.0, days_left / 30) * 15
    streak_bonus = min(streak * 0.5, 10)
    gap_penalty = sum(g * 0.3 for g in gaps)

    probability = max(0, min(100, base_prob + time_factor + streak_bonus - gap_penalty))

    if probability >= 80:
        rec = "You're on track for 3A. Maintain consistency and focus on weak sub-topics."
    elif probability >= 50:
        rec = f"Focus intensively on your {len(gaps)} weaker subject(s) — daily practice required."
    else:
        rec = "Critical: Start intensive revision now. Prioritise past papers over notes."

    return {
        "probability":      round(probability, 1),
        "subjects_on_track": on_track,
        "recommendation":    rec,
    }


def render_exam_readiness_dashboard(student: dict, quiz_history: list) -> None:
    """
    Render the full 3A exam readiness dashboard using Streamlit.

    Parameters
    ----------
    student     : student profile dict from session_state
    quiz_history: list of (topic, score, total, misconception, date) tuples
    """
    subject      = student.get("subject", "Computer Science")
    name         = student.get("name", "Student")
    days_left    = student.get("days_remaining", 30)
    if isinstance(days_left, str):
        try:
            days_left = int(days_left)
        except ValueError:
            days_left = 30

    # Compute overall readiness from quiz history
    if quiz_history:
        scores = [row[1] / max(row[2], 1) * 100 for row in quiz_history if row[2] > 0]
        overall = sum(scores) / len(scores) if scores else 0
    else:
        overall = 0

    threshold = get_a_grade_threshold(subject)
    gap       = max(0, threshold - overall)

    col1, col2, col3 = st.columns(3)
    color = "#00C850" if overall >= threshold else "#FFB800" if overall >= threshold * 0.8 else "#EF4444"

    col1.metric("Readiness", f"{overall:.0f}%", delta=f"Need {threshold}% for A")
    col2.metric("Days Left",  days_left)
    col3.metric("Gap to A",   f"{gap:.0f}%")

    st.progress(min(overall / 100, 1.0))

    if overall >= threshold:
        st.success(f"✓ {name} is on track for an A in {subject}!")
    elif gap <= 10:
        st.warning(f"⚠ {name} — {gap:.0f}% gap to A grade. Keep going!")
    else:
        st.error(f"🔴 {name} — {gap:.0f}% gap to A grade. Intensive revision needed.")

    # Show milestone badges
    st.markdown("**Milestones**")
    bcols = st.columns(len(MILESTONE_BADGES))
    for i, badge in enumerate(MILESTONE_BADGES):
        achieved = overall >= threshold * (0.7 + i * 0.15)
        bcols[i].markdown(
            f"{'✅' if achieved else '⬜'} {badge['icon']} **{badge['label']}**  \n"
            f"<span style='font-size:0.7rem;color:#4A6080;'>{badge['desc']}</span>",
            unsafe_allow_html=True,
        )
# achievement.py — 3A Achievement Engine
# OmniScholar | Sri Lanka A/L 3A Achievement Engine Edition

import json
import math
from datetime import date, datetime

import streamlit as st

from database import Database
from ollama_client import OllamaClient

# ── A-grade thresholds per subject type ──────────────────────────────────────
A_GRADE_THRESHOLD = {
    "default":        75,
    "Biology":        78,
    "Chemistry":      76,
    "Physics":        74,
    "Mathematics":    80,
    "Combined_Maths": 82,
    "Economics":      74,
    "Accounting":     76,
    "History":        72,
}

MILESTONE_BADGES = {
    75: {"label": "A-Grade Territory",  "emoji": "🎯", "color": "#16A34A"},
    85: {"label": "A-Grade Secured",    "emoji": "⭐", "color": "#0EA5E9"},
    95: {"label": "A-Grade Excellence", "emoji": "🏆", "color": "#D97706"},
}


def get_a_grade_threshold(subject: str) -> int:
    """Return A-grade threshold % for a given subject."""
    for key in A_GRADE_THRESHOLD:
        if key.lower() in subject.lower():
            return A_GRADE_THRESHOLD[key]
    return A_GRADE_THRESHOLD["default"]


def calculate_3a_probability(db: Database, student: dict) -> dict:
    """
    Calculate probability of achieving an A in each subject.
    Weighted combination:
      - Current chapter readiness scores (40 %)
      - Recent quiz performance trend     (30 %)
      - Past paper performance            (20 %)
      - Study consistency / streak        (10 %)
    """
    student_id = student.get("id") or student.get("student_id") or "demo_001"
    subjects   = student.get("subjects") or [student.get("subject", "Biology")]
    results    = {}

    for subject in subjects:
        threshold      = get_a_grade_threshold(subject)
        chapter_scores = db.get_chapter_scores_by_subject(student_id, subject)
        quiz_trend     = db.get_quiz_trend(student_id, subject, last_n=10)
        past_paper_avg = db.get_past_paper_average(student_id, subject)
        streak         = db.get_study_streak(student_id)

        chapter_avg = (
            sum(c["score"] for c in chapter_scores) / max(len(chapter_scores), 1)
            if chapter_scores else 50.0
        )
        quiz_avg  = sum(quiz_trend) / max(len(quiz_trend), 1) if quiz_trend else chapter_avg
        paper_avg = past_paper_avg if past_paper_avg is not None else chapter_avg

        streak_bonus  = min(streak * 0.5, 5)
        weighted_score = (
            chapter_avg  * 0.40
            + quiz_avg   * 0.30
            + paper_avg  * 0.20
            + streak_bonus * 0.10
        )

        gap         = weighted_score - threshold
        probability = round(50 + 50 * math.tanh(gap / 20), 1)
        probability = max(5, min(95, probability))

        weak_chapters   = [c for c in chapter_scores if c["score"] < threshold]
        strong_chapters = [c for c in chapter_scores if c["score"] >= threshold]

        if len(quiz_trend) >= 2:
            trend = "improving" if quiz_trend[-1] > quiz_trend[0] else "declining"
        else:
            trend = "insufficient data"

        results[subject] = {
            "weighted_score":    round(weighted_score, 1),
            "a_grade_threshold": threshold,
            "probability":       probability,
            "gap_to_a_grade":    max(0, round(threshold - weighted_score, 1)),
            "weak_chapters":     weak_chapters,
            "strong_chapters":   strong_chapters,
            "trend":             trend,
        }

    probs           = [results[s]["probability"] for s in results]
    overall_3a_prob = round(
        math.prod(p / 100 for p in probs) ** (1 / max(len(probs), 1)) * 100, 1
    )

    return {
        "subjects":               results,
        "overall_3a_probability": overall_3a_prob,
        "subjects_on_track":      sum(1 for s in results if results[s]["probability"] >= 60),
        "subjects_at_risk":       [s for s in results if results[s]["probability"] < 50],
    }


def generate_3a_battle_plan(db: Database, student: dict, llm: OllamaClient) -> str:
    """Use Gemma to generate a personalised, day-by-day 3A battle plan."""
    exam_date = student["exam_date"]
    if isinstance(exam_date, str):
        exam_date = date.fromisoformat(exam_date)
    days_remaining = (exam_date - date.today()).days
    analysis       = calculate_3a_probability(db, student)

    context = {
        "student_name":    student["name"],
        "subjects":        list(analysis["subjects"].keys()),
        "days_remaining":  days_remaining,
        "overall_3a_prob": analysis["overall_3a_probability"],
        "per_subject": {
            s: {
                "probability":    analysis["subjects"][s]["probability"],
                "weak_chapters":  [c["name"] for c in analysis["subjects"][s]["weak_chapters"][:5]],
                "gap_to_a_grade": analysis["subjects"][s]["gap_to_a_grade"],
                "trend":          analysis["subjects"][s]["trend"],
            }
            for s in analysis["subjects"]
        },
    }

    prompt = f"""You are Sri Lanka's most experienced A/L examiner and study coach.
{student['name']} needs to achieve 3 A's in {days_remaining} days.

Their current data:
{json.dumps(context, indent=2)}

Generate a SPECIFIC, actionable day-by-day study battle plan.
Rules:
1. Allocate more days to subjects with lower probability
2. Prioritise weak chapters that appear most often in past papers
3. Include a final 2-day revision sprint before the exam
4. Be direct, specific, and motivating — Sri Lankan A/L stakes are real
5. Output in the student's language: {student.get('language', 'English')}
6. Format: Day 1 → [subject] → [specific chapter] → [specific activity]

This plan determines whether {student['name']} gets into university. Make it count."""

    return llm.chat(
        system_prompt="You are an expert Sri Lankan A/L study strategist.",
        messages=[{"role": "user", "content": prompt}],
    )


def render_achievement_mode(student: dict, db: Database, llm: OllamaClient):
    """Render the 3A Achievement Engine dashboard."""

    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <h1 style="font-size: 1.8rem; font-weight: 700; color: #0F172A; margin: 0;">
            🏆 3A Achievement Engine
        </h1>
        <p style="color: #64748B; font-size: 0.95rem; margin: 4px 0 0;">
            Your personalised probability engine for Sri Lanka A/L success.
            Updated in real-time as you study.
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Calculating your 3A probability..."):
        analysis = calculate_3a_probability(db, student)

    overall_prob = analysis["overall_3a_probability"]

    # ── Hero card: Overall 3A Probability ────────────────────────────────────
    prob_color = (
        "#16A34A" if overall_prob >= 70 else
        "#D97706" if overall_prob >= 45 else
        "#DC2626"
    )
    prob_label = (
        "ON TRACK"  if overall_prob >= 70 else
        "AT RISK"   if overall_prob >= 45 else
        "CRITICAL"
    )

    st.markdown(f"""
    <div style="text-align: center; padding: 2.5rem 2rem;
         background: linear-gradient(135deg, #1E3A5F 0%, #0F2640 100%);
         border-radius: 12px; margin-bottom: 1rem;">
        <div style="font-size: 0.8rem; color: #94A3B8; font-weight: 600;
                    text-transform: uppercase; letter-spacing: 0.1em;">
            Overall 3A Probability
        </div>
        <div style="font-size: 5rem; font-weight: 800; color: {prob_color};
                    line-height: 1; margin: 0.5rem 0; letter-spacing: -0.04em;">
            {overall_prob}%
        </div>
        <div style="display: inline-block; padding: 4px 16px; border-radius: 20px;
                    background: {prob_color}22; border: 1px solid {prob_color};
                    color: {prob_color}; font-size: 0.85rem; font-weight: 700;
                    letter-spacing: 0.08em;">
            {prob_label}
        </div>
        <div style="color: #64748B; font-size: 0.8rem; margin-top: 1rem;">
            Based on your quiz scores, past papers, chapter readiness, and study streak
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Per-subject probability cards ────────────────────────────────────────
    subjects = list(analysis["subjects"].keys())
    if subjects:
        cols = st.columns(max(len(subjects), 1))
        for i, subject in enumerate(subjects):
            data       = analysis["subjects"][subject]
            prob       = data["probability"]
            color      = "#16A34A" if prob >= 70 else "#D97706" if prob >= 45 else "#DC2626"
            trend_icon = "↑" if data["trend"] == "improving" else "↓" if data["trend"] == "declining" else "→"
            gap_html   = (
                f"<div style='font-size: 0.75rem; color: #DC2626; margin-top: 4px;'>"
                f"Gap to close: {data['gap_to_a_grade']}%</div>"
                if data["gap_to_a_grade"] > 0 else
                "<div style='font-size: 0.75rem; color: #16A34A; margin-top: 4px;'>✓ A-grade zone reached</div>"
            )
            with cols[i]:
                st.markdown(f"""
                <div style="border: 1px solid #E2E8F0; border-radius: 10px; padding: 1.2rem; text-align: center; margin-bottom: 0.5rem;">
                    <div style="font-size: 0.75rem; color: #64748B; font-weight: 600;
                                text-transform: uppercase; letter-spacing: 0.05em;">
                        {subject}
                    </div>
                    <div style="font-size: 2.8rem; font-weight: 800; color: {color};
                                margin: 8px 0; line-height: 1;">
                        {prob}%
                    </div>
                    <div style="font-size: 0.8rem; color: {color}; margin-bottom: 8px;">
                        {trend_icon} {data['trend'].title()}
                    </div>
                    <div style="background: #F1F5F9; border-radius: 4px; height: 6px; overflow: hidden;">
                        <div style="width: {prob}%; height: 100%; background: {color};
                                    border-radius: 4px;"></div>
                    </div>
                    <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 8px;">
                        A-grade threshold: {data['a_grade_threshold']}%
                    </div>
                    {gap_html}
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Weak chapter priority list ────────────────────────────────────────────
    st.markdown("#### ⚠️ Priority Chapters to Rescue Your A's")
    all_weak = []
    for subject, data in analysis["subjects"].items():
        for ch in data["weak_chapters"]:
            all_weak.append({"subject": subject, **ch})

    if all_weak:
        all_weak.sort(key=lambda x: x["score"])
        for ch in all_weak[:6]:
            gap_pct = get_a_grade_threshold(ch["subject"]) - ch["score"]
            st.markdown(f"""
            <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 8px;
                        padding: 0.8rem 1rem; margin-bottom: 0.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 0.85rem; font-weight: 700; color: #92400E;">
                            {ch['name']}
                        </div>
                        <div style="font-size: 0.78rem; color: #B45309; margin-top: 2px;">
                            {ch['subject']} · Current: {ch['score']}% · Need: +{gap_pct}% more
                        </div>
                    </div>
                    <div style="background: #FEF3C7; color: #92400E; padding: 4px 10px;
                                border-radius: 20px; font-size: 0.75rem; font-weight: 700;">
                        PRIORITY
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 1rem;">
            <div style="font-size: 0.9rem; font-weight: 600; color: #14532D;">
                🎉 All chapters are in A-grade territory! Keep it up.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── 3A Battle Plan generator ──────────────────────────────────────────────
    st.markdown("#### 📅 Generate Your 3A Battle Plan")
    st.markdown(
        "*Powered by Gemma 4 — personalised to your exact weak areas and days remaining.*"
    )

    if st.button("🚀 Generate My 3A Battle Plan", type="primary", use_container_width=True):
        exam_date = student["exam_date"]
        if isinstance(exam_date, str):
            exam_date = date.fromisoformat(exam_date)
        days = (exam_date - date.today()).days
        if days <= 0:
            st.error("Your exam date has passed. Update your profile to continue.")
        else:
            with st.spinner(f"Gemma 4 is crafting your personalised {days}-day battle plan..."):
                plan = generate_3a_battle_plan(db, student, llm)

            st.markdown(f"""
            <div style="border: 1px solid #E2E8F0; border-left: 4px solid #0EA5E9;
                        border-radius: 8px; padding: 1.5rem; background: #F8FAFC;">
                <div style="font-size: 0.85rem; font-weight: 700; color: #1D4ED8;
                            margin-bottom: 1rem;">
                    Your {days}-Day 3A Battle Plan
                </div>
                <div style="font-size: 0.9rem; line-height: 1.8; color: #0F172A;
                            white-space: pre-wrap;">{plan}</div>
            </div>
            """, unsafe_allow_html=True)

            db.save_battle_plan(student.get("id", student.get("student_id", "demo_001")), plan)

    st.markdown("---")

    # ── Milestone badges ──────────────────────────────────────────────────────
    st.markdown("#### 🏅 Your Achievement Milestones")

    all_scores = []
    for subject, data in analysis["subjects"].items():
        all_scores.extend([c["score"] for c in data["strong_chapters"]])

    badge_cols = st.columns(3)
    for i, (threshold, badge) in enumerate(MILESTONE_BADGES.items()):
        earned  = any(s >= threshold for s in all_scores)
        opacity = "1" if earned else "0.3"
        with badge_cols[i]:
            st.markdown(f"""
            <div style="border: 1px solid #E2E8F0; border-radius: 10px; padding: 1.2rem;
                        text-align: center; opacity: {opacity};">
                <div style="font-size: 2.5rem;">{badge['emoji']}</div>
                <div style="font-size: 0.8rem; font-weight: 700; color: {badge['color']};
                            margin-top: 6px;">
                    {badge['label']}
                </div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 4px;">
                    Reach {threshold}% on any chapter
                </div>
            </div>
            """, unsafe_allow_html=True)


# ── Exam Readiness Dashboard ──────────────────────────────────────────────────

def render_exam_readiness_dashboard(student: dict, db: Database) -> None:
    """
    Full-screen exam readiness dashboard — the demo centrepiece.
    Shows overall readiness %, chapter mastery bars, and today's priority.
    Designed to be shown as the home screen before the mode selector.
    """
    student_id = student.get("student_id", student.get("id", ""))
    subject    = student.get("subject", "Computer Science")
    name       = student.get("name", "Student")

    # ── days left ─────────────────────────────────────────────────────────────
    try:
        exam_date_str = student.get("exam_date", "")
        exam_dt = datetime.strptime(str(exam_date_str), "%Y-%m-%d").date()
        days_left = max(0, (exam_dt - date.today()).days)
    except Exception:
        days_left = 0

    # ── data ──────────────────────────────────────────────────────────────────
    try:
        chapter_scores = db.get_chapter_scores_by_subject(student_id, subject)
    except Exception:
        chapter_scores = []
    try:
        weak_concepts = db.get_weak_concepts(student_id, resolved=False)
    except Exception:
        weak_concepts = []
    try:
        streak = db.get_study_streak(student_id)
    except Exception:
        streak = 0

    # ── overall readiness ─────────────────────────────────────────────────────
    if chapter_scores:
        overall = sum(c.get("score", 0) for c in chapter_scores) / len(chapter_scores)
    else:
        overall = 0.0

    if overall >= 75:
        overall_color = "#00C850"
        status_text   = "ON TRACK"
    elif overall >= 50:
        overall_color = "#FFB800"
        status_text   = "NEEDS WORK"
    else:
        overall_color = "#EF4444"
        status_text   = "CRITICAL"

    # ── Hero card ─────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0D1B35,#111929);
                border:1px solid rgba(0,212,255,0.25);border-radius:20px;
                padding:32px;text-align:center;margin-bottom:24px;
                position:relative;overflow:hidden;">
      <div style="position:absolute;top:0;left:0;right:0;height:3px;
                  background:linear-gradient(90deg,transparent,{overall_color},transparent);">
      </div>
      <div style="font-family:Orbitron,monospace;font-size:0.65rem;
                  color:#4A6080;letter-spacing:0.2em;text-transform:uppercase;
                  margin-bottom:8px;">EXAM READINESS — {subject.upper()}</div>
      <div style="font-family:Orbitron,monospace;font-size:4rem;font-weight:900;
                  color:{overall_color};text-shadow:0 0 30px {overall_color}66;
                  line-height:1;">{overall:.0f}%</div>
      <div style="font-family:Orbitron,monospace;font-size:0.8rem;
                  color:{overall_color};letter-spacing:0.15em;
                  margin:8px 0 16px;">{status_text}</div>
      <div style="color:#4A6080;font-size:0.85rem;">
        {days_left} days until exam &nbsp;·&nbsp; {streak} day streak &nbsp;·&nbsp;
        {len(weak_concepts)} active weak area{"s" if len(weak_concepts) != 1 else ""}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Chapter mastery bars ──────────────────────────────────────────────────
    if chapter_scores:
        st.markdown("#### Chapter Mastery")
        for chapter in sorted(chapter_scores, key=lambda c: c.get("score", 0)):
            score    = chapter.get("score", 0)
            ch_name  = chapter.get("chapter_name", "Unknown")
            if score >= 85:
                bar_color = "#00C850";  tag = "✓ Strong"
            elif score >= 70:
                bar_color = "#00D4FF";  tag = "→ Consolidating"
            elif score >= 40:
                bar_color = "#FFB800";  tag = "⚠ Developing"
            else:
                bar_color = "#EF4444";  tag = "🔴 Critical"

            st.markdown(f"""
            <div style="margin:8px 0;">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="color:#A0B4D6;font-size:0.85rem;
                             font-family:'Exo 2',sans-serif;">{ch_name}</span>
                <span style="color:{bar_color};font-size:0.75rem;
                             font-family:Orbitron,monospace;">{score:.0f}% {tag}</span>
              </div>
              <div style="background:#1A2540;border-radius:4px;height:8px;overflow:hidden;">
                <div style="width:{score:.0f}%;height:100%;border-radius:4px;
                            background:linear-gradient(90deg,{bar_color}88,{bar_color});
                            box-shadow:0 0 8px {bar_color}44;">
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Today's Priority ──────────────────────────────────────────────────────
    if weak_concepts:
        worst = sorted(weak_concepts, key=lambda w: w.get("frequency", 0), reverse=True)[0]
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1a0a00,#220f00);
                    border:1px solid rgba(255,184,0,0.3);border-radius:12px;
                    padding:20px;margin-top:16px;">
          <div style="font-size:0.65rem;color:#FFB800;letter-spacing:0.15em;
                      text-transform:uppercase;margin-bottom:8px;">
            TODAY'S PRIORITY
          </div>
          <div style="font-size:1rem;color:#E8F0FF;font-weight:600;">
            {worst.get("concept", "Review your weakest topic")}
          </div>
          <div style="font-size:0.8rem;color:#4A6080;margin-top:4px;">
            Appeared {worst.get("frequency", 1)}x &nbsp;·&nbsp; {worst.get("topic", "")}
          </div>
        </div>
        """, unsafe_allow_html=True)
