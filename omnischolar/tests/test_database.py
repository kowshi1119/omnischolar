import sqlite3

import database
from database import Database, get_quiz_history, save_quiz_result, save_student


def test_weak_concepts_round_trip():
    db = Database()
    db.upsert_weak_concept("s1", "recursion", topic="Algorithms")
    db.upsert_weak_concept("s1", "recursion", topic="Algorithms")
    rows = db.get_weak_concepts("s1")
    assert len(rows) == 1
    assert rows[0]["frequency"] == 2  # second call bumped, didn't duplicate
    assert rows[0]["last_seen"]

    db.resolve_concept(rows[0]["id"])
    assert db.get_weak_concepts("s1") == []
    assert len(db.get_weak_concepts("s1", resolved=True)) == 1


def test_quiz_result_saved_and_counts_streak():
    db = Database()
    save_quiz_result("s2", "Sorting", 3, 5, subject="Discrete Maths")
    assert db.get_quiz_history("s2") == get_quiz_history("s2")
    assert get_quiz_history("s2")[0][:3] == ("Sorting", 3, 5)
    assert db.get_study_streak("s2") == 1
    # A second quiz the same day must not double-count the study day
    save_quiz_result("s2", "Graphs", 4, 5)
    assert db.get_study_streak("s2") == 1
    assert db.get_class_analytics("Discrete Maths")["class_avg"] == 60.0


def test_save_student_keeps_pdf_list():
    db = Database()
    profile = {"student_id": "s3", "name": "A", "subject": "Physics"}
    save_student(profile)
    db.update_student_pdf("s3", "notes.pdf")
    save_student({**profile, "name": "B"})  # e.g. a language toggle re-save
    assert db.get_student_pdf("s3") == "notes.pdf"
    assert db.get_student_profile("s3")["name"] == "B"


def test_legacy_weak_concepts_table_gets_last_seen(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE weak_concepts (id INTEGER PRIMARY KEY, student_id TEXT, "
        "concept TEXT, subject TEXT, resolved INTEGER DEFAULT 0, "
        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.execute("INSERT INTO weak_concepts (student_id, concept) VALUES ('s4', 'loops')")
    conn.commit()
    conn.close()

    db = Database(db_path=str(path))
    assert [r["concept"] for r in db.get_weak_concepts("s4")] == ["loops"]
    assert database.DB_PATH != str(path)  # module default untouched
