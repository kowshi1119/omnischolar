"""
seed_demo_data.py — Reset OmniScholar to a clean, populated demo state.
Run: python seed_demo_data.py

Creates two demo students:
  1. Kowshi (demo_kowshi_001) — Undergraduate, Computer Science
  2. Kavindi (demo_kavindi_001) — A/L Student, Biological Science Stream, targeting 3A
"""
import json
import sqlite3
import os
import sys
from datetime import date, datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "omnischolar.db")

DEMO_STUDENT_ID = "demo_kowshi_001"
DEMO_NAME = "Kowshi"
DEMO_SUBJECT = "Computer Science"
DEMO_EXAM_DATE = str(date.today() + timedelta(days=45))


def seed():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ── Student profile ────────────────────────────────────────────────────
    c.execute("""
        INSERT OR REPLACE INTO students
          (student_id, name, subject, exam_date, preferred_language, weak_areas, pdf_files)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        DEMO_STUDENT_ID, DEMO_NAME, DEMO_SUBJECT, DEMO_EXAM_DATE,
        "English", "Recursion, Sorting Algorithms, Deadlock",
        ""
    ))

    # ── Chapter scores ─────────────────────────────────────────────────────
    chapters = [
        ("Data Structures", 78),
        ("Sorting Algorithms", 52),
        ("Recursion", 45),
        ("OS Concepts", 63),
        ("Deadlock", 38),
        ("Networking Basics", 70),
        ("Databases", 85),
        ("Graph Theory", 58),
    ]
    for chapter, score in chapters:
        c.execute("""
            INSERT OR REPLACE INTO chapter_scores
              (student_id, subject, chapter_name, score, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (DEMO_STUDENT_ID, DEMO_SUBJECT, chapter, score,
              datetime.now().isoformat()))

    # ── Quiz history (last 7 days) ─────────────────────────────────────────
    quiz_topics = [
        ("Data Structures", 7, 10, "Confused list vs linked list"),
        ("Recursion", 3, 10, "Stack overflow concept unclear"),
        ("Sorting Algorithms", 5, 10, "QuickSort worst-case not understood"),
        ("OS Concepts", 8, 10, None),
        ("Graph Theory", 6, 10, "DFS vs BFS application"),
        ("Networking Basics", 9, 10, None),
        ("Deadlock", 4, 10, "Banker's algorithm steps unclear"),
    ]
    for i, (topic, score, total, misconception) in enumerate(quiz_topics):
        session_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        c.execute("""
            INSERT INTO quiz_history
              (student_id, topic, score, total, misconception, session_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (DEMO_STUDENT_ID, topic, score, total, misconception, session_date))

    # ── Weak concepts ──────────────────────────────────────────────────────
    weak_concepts = [
        ("Stack overflow in recursion", False),
        ("Banker's algorithm", False),
        ("QuickSort worst-case O(n^2)", True),
        ("DFS implementation", False),
    ]
    for concept, resolved in weak_concepts:
        c.execute("""
            INSERT OR IGNORE INTO weak_concepts
              (student_id, concept, subject, resolved, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (DEMO_STUDENT_ID, concept, DEMO_SUBJECT, 1 if resolved else 0,
              datetime.now().isoformat()))

    # ── Study streak (last 7 days of activity) ─────────────────────────────
    for i in range(7):
        session_date = (date.today() - timedelta(days=i)).isoformat()
        c.execute("""
            INSERT OR IGNORE INTO study_sessions
              (student_id, session_date)
            VALUES (?, ?)
        """, (DEMO_STUDENT_ID, session_date))

    conn.commit()
    conn.close()
    print(f"Demo data seeded for '{DEMO_NAME}' (student_id={DEMO_STUDENT_ID})")
    print(f"  Subject: {DEMO_SUBJECT}")
    print(f"  Exam date: {DEMO_EXAM_DATE}")
    print(f"  {len(chapters)} chapters, {len(quiz_topics)} quiz sessions, {len(weak_concepts)} weak concepts")


# ── Kavindi — A/L Student (Biological Science, targeting 3A) ──────────────────

KAVINDI_ID = "demo_kavindi_001"
KAVINDI_NAME = "Kavindi"
KAVINDI_AL_SUBJECTS = ["Biology", "Physics", "Chemistry"]
KAVINDI_AL_SUBJECTS_JSON = json.dumps(KAVINDI_AL_SUBJECTS)
KAVINDI_EXAM_DATE = "2026-08-15"


def seed_kavindi():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ── Student profile ────────────────────────────────────────────────────
    c.execute("""
        INSERT OR REPLACE INTO students
          (student_id, name, subject, exam_date, preferred_language, weak_areas,
           student_type, al_stream, al_subjects)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        KAVINDI_ID, KAVINDI_NAME, "Biological Science A/L", KAVINDI_EXAM_DATE,
        "English", "Osmosis, Newton's Laws, Organic Chemistry",
        "A/L Student", "Biological Science Stream", KAVINDI_AL_SUBJECTS_JSON,
    ))

    # ── Chapter scores (3 per subject) ────────────────────────────────────
    bio_chapters = [
        ("Cell Biology",     72),
        ("Genetics",         55),
        ("Plant Biology",    48),
        ("Animal Physiology",67),
        ("Ecology",          80),
    ]
    phy_chapters = [
        ("Mechanics",        60),
        ("Electricity",      53),
        ("Waves and Optics", 70),
    ]
    chem_chapters = [
        ("Organic Chemistry",  45),
        ("Equilibrium",        58),
        ("Electrochemistry",   63),
    ]
    all_chapters = (
        [(subj, ch, sc) for ch, sc in bio_chapters for subj in ["Biology"][:1]]
        + [(subj, ch, sc) for ch, sc in phy_chapters for subj in ["Physics"][:1]]
        + [(subj, ch, sc) for ch, sc in chem_chapters for subj in ["Chemistry"][:1]]
    )
    # Rebuild list properly
    all_chapters_flat = (
        [("Biology", ch, sc) for ch, sc in bio_chapters]
        + [("Physics", ch, sc) for ch, sc in phy_chapters]
        + [("Chemistry", ch, sc) for ch, sc in chem_chapters]
    )
    for subj, chapter, score in all_chapters_flat:
        c.execute("""
            INSERT OR REPLACE INTO chapter_scores
              (student_id, subject, chapter_name, score, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (KAVINDI_ID, subj, chapter, score, datetime.now().isoformat()))

    # ── Quiz history ──────────────────────────────────────────────────────
    kavindi_quiz = [
        ("Biology — Cell Biology",         7, 10, None),
        ("Biology — Genetics",             5, 10, "Confused dominant vs codominance"),
        ("Biology — Plant Biology",        4, 10, "Osmosis direction in hypertonic solution"),
        ("Physics — Mechanics",            6, 10, "Newton's third law application unclear"),
        ("Physics — Electricity",          5, 10, "Ohm's law in parallel circuits"),
        ("Chemistry — Organic Chemistry",  4, 10, "Confused esterification with saponification"),
        ("Chemistry — Equilibrium",        6, 10, None),
    ]
    for i, (topic, score, total, misconception) in enumerate(kavindi_quiz):
        session_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        c.execute("""
            INSERT INTO quiz_history
              (student_id, topic, score, total, misconception, session_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (KAVINDI_ID, topic, score, total, misconception, session_date))

    # ── Weak concepts (with topic fields for NIE mapping) ─────────────────
    kavindi_weak = [
        ("Osmosis",                    "Plant Biology — Unit 6.3 Transport in Plants", "conceptual_confusion"),
        ("Newton's 3rd Law",           "Mechanics",                                     "direction_error"),
        ("Esterification mechanism",   "Organic Chemistry",                             "process_confusion"),
        ("Hardy-Weinberg equilibrium", "Genetics",                                      "factual_error"),
    ]
    for concept, topic, error_type in kavindi_weak:
        c.execute("""
            INSERT OR IGNORE INTO weak_concepts
              (student_id, concept, topic, error_type, frequency, resolved, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (KAVINDI_ID, concept, topic, error_type, 2, 0, datetime.now().isoformat()))

    # ── Study streak (last 7 days) ────────────────────────────────────────
    for i in range(7):
        session_date = (date.today() - timedelta(days=i)).isoformat()
        c.execute("""
            INSERT OR IGNORE INTO study_sessions
              (student_id, session_date)
            VALUES (?, ?)
        """, (KAVINDI_ID, session_date))

    conn.commit()
    conn.close()
    print(f"Demo data seeded for '{KAVINDI_NAME}' (student_id={KAVINDI_ID})")
    print(f"  Student type: A/L Student | Stream: Biological Science Stream")
    print(f"  Subjects: {', '.join(KAVINDI_AL_SUBJECTS)}")
    print(f"  Exam date: {KAVINDI_EXAM_DATE}")
    print(f"  {len(all_chapters_flat)} chapter scores, {len(kavindi_quiz)} quiz sessions, {len(kavindi_weak)} weak concepts")


if __name__ == "__main__":
    seed()
    seed_kavindi()
