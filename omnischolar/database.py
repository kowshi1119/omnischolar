import sqlite3
import os

DB_PATH = os.getenv("SQLITE_DB_PATH", "omnischolar.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT,
            subject TEXT,
            exam_date TEXT,
            preferred_language TEXT,
            weak_areas TEXT,
            pdf_files TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS quiz_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            topic TEXT,
            score INTEGER,
            total INTEGER,
            misconception TEXT,
            session_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS weak_concepts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            concept TEXT,
            subject TEXT,
            resolved INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS saved_lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            subject TEXT,
            topic TEXT,
            content TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            session_date TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS past_paper_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            subject TEXT,
            year TEXT,
            score INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS past_paper_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            question TEXT,
            answer TEXT,
            correct INTEGER
        )
        """
    )
    # Auto-migrate: add any missing columns to existing students table
    _migrations = [
        ("subject",            "TEXT"),
        ("exam_date",          "TEXT"),
        ("preferred_language", "TEXT DEFAULT 'english'"),
        ("weak_areas",         "TEXT"),
        ("pdf_files",          "TEXT"),
        ("current_pdf",        "TEXT"),
        ("student_type",       "TEXT DEFAULT 'Undergraduate'"),
        ("al_stream",          "TEXT"),
        ("al_subjects",        "TEXT"),
    ]
    for _col, _type in _migrations:
        try:
            c.execute(f"ALTER TABLE students ADD COLUMN {_col} {_type}")
            conn.commit()
        except Exception:
            pass  # column already exists
    conn.commit()
    conn.close()


def save_student(profile_or_id, name=None, subject=None, exam_date=None,
                 preferred_language=None, weak_areas=None):
    """Accept either a profile dict or 6 positional args (backwards compat)."""
    if isinstance(profile_or_id, dict):
        profile = profile_or_id
    else:
        wa = weak_areas or ""
        if isinstance(wa, (list, tuple)):
            wa = ",".join(wa)
        profile = {
            "student_id":         profile_or_id,
            "name":               name or "",
            "subject":            subject or "",
            "exam_date":          exam_date or "",
            "preferred_language": preferred_language or "english",
            "weak_areas":         wa,
        }
    wa = profile.get("weak_areas", "")
    if isinstance(wa, (list, tuple)):
        wa = ",".join(wa)
    al_subjects = profile.get("al_subjects", "")
    if isinstance(al_subjects, (list, tuple)):
        import json as _json
        al_subjects = _json.dumps(al_subjects)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT OR REPLACE INTO students
        (student_id, name, subject, exam_date, preferred_language, weak_areas,
         student_type, al_stream, al_subjects)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            profile["student_id"],
            profile.get("name", ""),
            profile.get("subject", ""),
            profile.get("exam_date", ""),
            profile.get("preferred_language", "english"),
            wa,
            profile.get("student_type", "Undergraduate"),
            profile.get("al_stream", "") or "",
            al_subjects or "",
        ),
    )
    conn.commit()
    conn.close()


def save_quiz_result(student_id, topic, score, total, misconception=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO quiz_history (student_id, topic, score, total, misconception)
        VALUES (?, ?, ?, ?, ?)
        """,
        (student_id, topic, score, total, misconception),
    )
    conn.commit()
    conn.close()


def get_quiz_history(student_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT topic, score, total, misconception, session_date
        FROM quiz_history WHERE student_id = ?
        ORDER BY session_date DESC LIMIT 20
        """,
        (student_id,),
    )
    rows = c.fetchall()
    conn.close()
    return rows


class Database:
    """OOP interface on top of the omnischolar.db SQLite database."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        init_db()
        self._init_extended_tables()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # ── Extended tables (idempotent — safe to run multiple times) ─────────────
    def _init_extended_tables(self):
        """Create ALL extended tables. Safe to run multiple times (IF NOT EXISTS)."""
        conn = self._conn()
        # Add missing columns to students table safely
        for _col, _type in [
            ("subject",            "TEXT"),
            ("exam_date",          "TEXT"),
            ("preferred_language", "TEXT DEFAULT 'english'"),
            ("weak_areas",         "TEXT"),
            ("current_pdf",        "TEXT"),
            ("student_type",       "TEXT DEFAULT 'Undergraduate'"),
            ("al_stream",          "TEXT"),
            ("al_subjects",        "TEXT"),
        ]:
            try:
                conn.execute(
                    f"ALTER TABLE students ADD COLUMN {_col} {_type}"
                )
                conn.commit()
            except Exception:
                pass  # column already exists

        # Add missing columns to weak_concepts (legacy schema may lack these)
        for _col, _type in [
            ("topic",      "TEXT DEFAULT ''"),
            ("error_type", "TEXT DEFAULT 'factual_error'"),
            ("frequency",  "INTEGER DEFAULT 1"),
            ("last_seen",  "DATETIME DEFAULT CURRENT_TIMESTAMP"),
        ]:
            try:
                conn.execute(
                    f"ALTER TABLE weak_concepts ADD COLUMN {_col} {_type}"
                )
                conn.commit()
            except Exception:
                pass

        # Add missing columns to past_paper_sessions
        for _col, _type in [
            ("paper_name",         "TEXT"),
            ("total_marks",        "INTEGER DEFAULT 0"),
            ("score_achieved",     "INTEGER DEFAULT 0"),
            ("time_taken_seconds", "INTEGER DEFAULT 0"),
            ("weak_sections",      "TEXT"),
        ]:
            try:
                conn.execute(
                    f"ALTER TABLE past_paper_sessions ADD COLUMN {_col} {_type}"
                )
                conn.commit()
            except Exception:
                pass

        # Add missing columns to past_paper_questions
        for _col, _type in [
            ("student_id",      "TEXT"),
            ("question_number", "TEXT"),
            ("question_text",   "TEXT"),
            ("student_answer",  "TEXT"),
            ("verdict",         "TEXT"),
            ("marks_awarded",   "INTEGER DEFAULT 0"),
            ("marks_available", "INTEGER DEFAULT 1"),
            ("time_spent",      "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(
                    f"ALTER TABLE past_paper_questions ADD COLUMN {_col} {_type}"
                )
                conn.commit()
            except Exception:
                pass

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS chapter_scores (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id   TEXT NOT NULL,
                subject      TEXT NOT NULL,
                chapter_name TEXT NOT NULL,
                score        REAL NOT NULL DEFAULT 0,
                updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, subject, chapter_name)
            );

            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                subject    TEXT NOT NULL,
                score      REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS past_paper_attempts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                subject    TEXT NOT NULL,
                score_pct  REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS battle_plans (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                plan_json  TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS past_paper_sessions (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id           TEXT NOT NULL,
                paper_name           TEXT NOT NULL,
                year                 INTEGER,
                subject              TEXT,
                total_marks          INTEGER,
                score_achieved       INTEGER,
                time_taken_seconds   INTEGER,
                weak_sections        TEXT,
                created_at           DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS past_paper_questions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id       INTEGER,
                student_id       TEXT NOT NULL,
                question_number  TEXT,
                question_text    TEXT,
                student_answer   TEXT,
                verdict          TEXT,
                marks_awarded    INTEGER DEFAULT 0,
                marks_available  INTEGER DEFAULT 1,
                time_spent       INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS weak_concepts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id  TEXT NOT NULL,
                concept     TEXT NOT NULL,
                topic       TEXT NOT NULL DEFAULT '',
                error_type  TEXT NOT NULL DEFAULT 'factual_error',
                frequency   INTEGER NOT NULL DEFAULT 1,
                resolved    INTEGER NOT NULL DEFAULT 0,
                last_seen   DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS saved_lessons (
                lesson_id   TEXT PRIMARY KEY,
                student_id  TEXT NOT NULL,
                topic       TEXT NOT NULL,
                subject     TEXT NOT NULL,
                lesson_json TEXT NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()

    # ── Past paper persistence ────────────────────────────────────────────────
    def save_past_paper_session(self, student_id: str, paper_name: str,
                                 year: int, subject: str,
                                 total_marks: int, score_achieved: int,
                                 time_taken_seconds: int,
                                 weak_sections=None) -> int:
        """Insert a new past paper session row; return its id."""
        import json as _json
        ws = _json.dumps(weak_sections or [])
        conn = self._conn()
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO past_paper_sessions
              (student_id, paper_name, year, subject, total_marks,
               score_achieved, time_taken_seconds, weak_sections)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (student_id, paper_name, year, subject, total_marks,
             score_achieved, time_taken_seconds, ws),
        )
        conn.commit()
        sid = c.lastrowid
        conn.close()
        return sid

    def save_past_paper_question(self, session_id: int, question_number,
                                  question_text: str, student_answer: str,
                                  marks_awarded: int, marks_available: int,
                                  time_spent_seconds: int = 0,
                                  verdict: str = "WRONG",
                                  student_id: str = "") -> None:
        conn = self._conn()
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO past_paper_questions
              (session_id, student_id, question_number, question_text,
               student_answer, verdict, marks_awarded, marks_available,
               time_spent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, student_id, str(question_number), question_text,
             student_answer, verdict, marks_awarded, marks_available,
             time_spent_seconds),
        )
        conn.commit()
        conn.close()

    def get_past_paper_average(self, student_id: str, subject: str = None):
        """Return the average score % across past paper sessions, or None."""
        conn = self._conn()
        c = conn.cursor()
        try:
            if subject:
                c.execute(
                    """SELECT AVG(100.0 * score_achieved / MAX(total_marks,1))
                       FROM past_paper_sessions
                       WHERE student_id = ? AND subject = ?""",
                    (student_id, subject),
                )
            else:
                c.execute(
                    """SELECT AVG(100.0 * score_achieved / MAX(total_marks,1))
                       FROM past_paper_sessions WHERE student_id = ?""",
                    (student_id,),
                )
            row = c.fetchone()
            return round(row[0], 1) if row and row[0] is not None else None
        except Exception:
            return None
        finally:
            conn.close()

    # ── Weak concepts (extended) ──────────────────────────────────────────────
    def upsert_weak_concept(self, student_id: str, concept: str,
                             topic: str = "", error_type: str = "factual_error",
                             subject: str = "") -> None:
        """Insert or bump frequency of an existing weak concept."""
        conn = self._conn()
        c = conn.cursor()
        try:
            c.execute(
                """SELECT id, frequency FROM weak_concepts
                   WHERE student_id = ? AND concept = ? AND resolved = 0""",
                (student_id, concept),
            )
            row = c.fetchone()
            if row:
                new_freq = (row[1] or 1) + 1
                c.execute(
                    """UPDATE weak_concepts
                       SET frequency = ?, last_seen = CURRENT_TIMESTAMP,
                           topic = COALESCE(NULLIF(?, ''), topic),
                           error_type = COALESCE(NULLIF(?, ''), error_type)
                       WHERE id = ?""",
                    (new_freq, topic, error_type, row[0]),
                )
            else:
                c.execute(
                    """INSERT INTO weak_concepts
                       (student_id, concept, subject, topic, error_type,
                        frequency, resolved)
                       VALUES (?, ?, ?, ?, ?, 1, 0)""",
                    (student_id, concept, subject or topic, topic, error_type),
                )
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    # ── Quiz trend ────────────────────────────────────────────────────────────
    def get_quiz_trend(self, student_id: str, subject: str = None,
                        last_n: int = 10) -> list:
        """Return list of recent quiz % scores (oldest first)."""
        conn = self._conn()
        c = conn.cursor()
        try:
            c.execute(
                """SELECT score, total FROM quiz_history
                   WHERE student_id = ?
                   ORDER BY session_date DESC LIMIT ?""",
                (student_id, last_n),
            )
            rows = c.fetchall()
            scores = []
            for s, t in reversed(rows):
                if t and t > 0:
                    scores.append(round(100.0 * s / t, 1))
            return scores
        except Exception:
            return []
        finally:
            conn.close()

    # ── Battle plan persistence ───────────────────────────────────────────────
    def save_battle_plan(self, student_id: str, plan) -> int:
        """Persist a battle plan (string or dict)."""
        import json as _json
        if not isinstance(plan, str):
            plan = _json.dumps(plan, ensure_ascii=False)
        conn = self._conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO battle_plans (student_id, plan_json) VALUES (?, ?)",
            (student_id, plan),
        )
        conn.commit()
        pid = c.lastrowid
        conn.close()
        return pid

    # ── Chapter scores ────────────────────────────────────────────────────────
    def get_chapter_scores_by_subject(self, student_id: str, subject: str) -> list:
        """Return [{"chapter": topic, "score": avg_pct}, ...] from quiz_history."""
        conn = self._conn()
        c = conn.cursor()
        c.execute(
            """
            SELECT topic,
                   ROUND(100.0 * SUM(score) / MAX(SUM(total), 1), 1) AS avg_pct
            FROM quiz_history
            WHERE student_id = ?
            GROUP BY topic
            ORDER BY avg_pct ASC
            LIMIT 10
            """,
            (student_id,),
        )
        rows = c.fetchall()
        conn.close()
        return [
            {"chapter": r[0], "name": r[0], "chapter_name": r[0],
             "score": r[1] or 0}
            for r in rows
        ]

    # ── Study streak ──────────────────────────────────────────────────────────
    def get_study_streak(self, student_id: str) -> int:
        """Count consecutive study days ending today."""
        import datetime
        conn = self._conn()
        c = conn.cursor()
        c.execute(
            "SELECT DISTINCT session_date FROM study_sessions WHERE student_id = ? ORDER BY session_date DESC",
            (student_id,),
        )
        rows = [r[0] for r in c.fetchall()]
        conn.close()
        if not rows:
            return 0
        streak = 0
        today = datetime.date.today()
        for i, d_str in enumerate(rows):
            try:
                d = datetime.date.fromisoformat(d_str)
            except Exception:
                break
            if d == today - datetime.timedelta(days=i):
                streak += 1
            else:
                break
        return streak

    # ── Weak concepts ─────────────────────────────────────────────────────────
    def get_weak_concepts(self, student_id: str, resolved: bool = False) -> list:
        conn = self._conn()
        c = conn.cursor()
        # Defensive: only request columns that exist
        cols = {row[1] for row in c.execute("PRAGMA table_info(weak_concepts)")}
        sel = ["id", "concept", "subject", "created_at"]
        if "topic" in cols:      sel.append("topic")
        if "frequency" in cols:  sel.append("frequency")
        if "last_seen" in cols:  sel.append("last_seen")
        c.execute(
            f"SELECT {', '.join(sel)} FROM weak_concepts "
            f"WHERE student_id = ? AND resolved = ?",
            (student_id, 1 if resolved else 0),
        )
        rows = c.fetchall()
        conn.close()
        out = []
        for r in rows:
            d = {"id": r[0], "concept": r[1], "subject": r[2],
                 "created_at": r[3]}
            idx = 4
            if "topic" in cols:
                d["topic"] = r[idx] or ""; idx += 1
            else:
                d["topic"] = ""
            if "frequency" in cols:
                d["frequency"] = r[idx] or 1; idx += 1
            else:
                d["frequency"] = 1
            if "last_seen" in cols:
                d["last_seen"] = r[idx]; idx += 1
            out.append(d)
        return out

    def record_weak_concept(self, student_id: str, concept: str, subject: str = "") -> None:
        conn = self._conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO weak_concepts (student_id, concept, subject) VALUES (?, ?, ?)",
            (student_id, concept, subject),
        )
        conn.commit()
        conn.close()

    # ── PDF files ─────────────────────────────────────────────────────────────
    def update_student_pdf(self, student_id: str, pdf_names: str) -> None:
        conn = self._conn()
        c = conn.cursor()
        c.execute(
            "UPDATE students SET pdf_files = ? WHERE student_id = ?",
            (pdf_names, student_id),
        )
        conn.commit()
        conn.close()

    def get_student_pdf(self, student_id: str) -> str:
        conn = self._conn()
        c = conn.cursor()
        c.execute("SELECT pdf_files FROM students WHERE student_id = ?", (student_id,))
        row = c.fetchone()
        conn.close()
        return row[0] if row and row[0] else ""

    # ── Lessons ───────────────────────────────────────────────────────────────
    def save_lesson(self, student_id: str = "", subject: str = "",
                    topic: str = "", content: str = "",
                    lesson_json: str = "") -> str:
        """Save a lesson; accepts either `content=` or `lesson_json=`. Returns id."""
        body = lesson_json or content
        conn = self._conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO saved_lessons (student_id, subject, topic, content) VALUES (?, ?, ?, ?)",
            (student_id, subject, topic, body),
        )
        conn.commit()
        new_id = str(c.lastrowid)
        conn.close()
        return new_id

    def get_lessons(self, student_id: str, subject: str = None) -> list:
        conn = self._conn()
        c = conn.cursor()
        if subject:
            c.execute(
                "SELECT id, subject, topic, content, created_at FROM saved_lessons WHERE student_id = ? AND subject = ? ORDER BY created_at DESC",
                (student_id, subject),
            )
        else:
            c.execute(
                "SELECT id, subject, topic, content, created_at FROM saved_lessons WHERE student_id = ? ORDER BY created_at DESC",
                (student_id,),
            )
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "subject": r[1], "topic": r[2], "content": r[3], "created_at": r[4]} for r in rows]

    # ── Analytics ─────────────────────────────────────────────────────────────
    def get_class_analytics(self, subject: str | None = None) -> dict:
        """Return aggregate stats across all students, optionally filtered by subject."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute("SELECT COUNT(*) FROM students")
            total_students = c.fetchone()[0]

            if subject:
                c.execute(
                    "SELECT AVG(100.0 * score / MAX(total, 1)) FROM quiz_history WHERE subject = ?",
                    (subject,),
                )
            else:
                c.execute("SELECT AVG(100.0 * score / MAX(total, 1)) FROM quiz_history")
            class_avg = round(c.fetchone()[0] or 0, 1)

            if subject:
                c.execute(
                    """SELECT topic, AVG(100.0 * score / MAX(total, 1)) as avg_score, COUNT(*) as attempts
                       FROM quiz_history WHERE subject = ?
                       GROUP BY topic ORDER BY avg_score ASC""",
                    (subject,),
                )
            else:
                c.execute(
                    """SELECT topic, AVG(100.0 * score / MAX(total, 1)) as avg_score, COUNT(*) as attempts
                       FROM quiz_history
                       GROUP BY topic ORDER BY avg_score ASC"""
                )
            topic_rows = c.fetchall()
            topics = [{"topic": r[0], "avg_score": round(r[1] or 0, 1), "attempts": r[2]} for r in topic_rows]
            most_struggling_topic = topics[0]["topic"] if topics else None
        except Exception:
            total_students, class_avg, topics, most_struggling_topic = 0, 0.0, [], None
        finally:
            conn.close()
        return {
            "total_students": total_students,
            "class_avg": class_avg,
            "topics": topics,
            "most_struggling_topic": most_struggling_topic,
        }

