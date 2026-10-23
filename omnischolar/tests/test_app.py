"""Render every mode with Ollama unreachable: the app must degrade, not crash."""

import os

import pytest
from streamlit.testing.v1 import AppTest

from conftest import APP_DIR

APP = os.path.join(APP_DIR, "app.py")
MODES = [
    "LEARN", "REVISE", "TEST_ME", "FIND_WEAK_AREAS", "STUDY_PLAN", "THREE_A",
    "PAST_PAPER", "ADVANCED_STUDY_PLAN", "TEACHER", "WEAKNESS",
    "VIRTUAL_TEACHER", "BATTLE_GAME",
]


@pytest.mark.parametrize("mode", MODES)
def test_mode_renders_without_exception(mode):
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["mode"] = mode
    at.run()
    assert not at.exception, at.exception
    assert not [e for e in at.error if "Something went wrong" in e.value]
    assert any("isn't running" in w.value for w in at.warning)


def test_score_quiz():
    # app.py runs the UI on import, so load just this pure function
    import json
    import re
    src = open(APP, encoding="utf-8").read()
    ns = {"re": re, "json": json}
    exec(src[src.index("def _score_quiz"):src.index("def _handle_test_me")], ns)
    quiz = "Q: a\nA) x\nAnswer: B\nQ: b\nAnswer: **C**\nQ: c\nAnswer - (d)"
    assert ns["_score_quiz"](quiz, "1:B 2:a 3.D") == (2, 3)
    assert "Answer" not in ns["_quiz_markdown"](quiz)
    assert ns["_score_quiz"]("no key here", "1:A") == (0, 0)

    # The fine-tuned model replies in its TEST_ME JSON schema
    quiz_json = 'Sure:\n{"questions": [{"question_text": "Base case?", "options": ["A. x", "B. y"], "correct_answer": "B"},' \
                ' {"question_text": "Stack?", "options": ["A. z"], "correct_answer": "a"}]}'
    assert ns["_score_quiz"](quiz_json, "1:B 2:B") == (1, 2)
    shown = ns["_quiz_markdown"](quiz_json)
    assert "**1. Base case?**" in shown and "correct_answer" not in shown
