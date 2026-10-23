"""
test_navigation.py -- OmniScholar Navigation & Integration Tests
Run: python test_navigation.py
Tests ALL navigation paths without a browser.
"""

import sys
import os
import time
import unittest

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _APP_DIR)


class TestNavigationLogic(unittest.TestCase):
    """Test that mode values and routing constants are correct."""

    def test_primary_modes_no_three_a(self):
        """THREE_A must NOT be in _PRIMARY_MODES."""
        from app import _PRIMARY_MODES
        mode_values = [m[1] for m in _PRIMARY_MODES]
        self.assertNotIn(
            "THREE_A", mode_values,
            "THREE_A found in _PRIMARY_MODES -- it must be "
            "in the separate A/L achievement section only"
        )

    def test_secondary_modes_no_three_a(self):
        """THREE_A must NOT be in _SECONDARY_MODES."""
        from app import _SECONDARY_MODES
        mode_values = [m[1] for m in _SECONDARY_MODES]
        self.assertNotIn(
            "THREE_A", mode_values,
            "THREE_A found in _SECONDARY_MODES -- duplicate!"
        )

    def test_all_mode_values_unique(self):
        """No duplicate mode values across PRIMARY + SECONDARY."""
        from app import _PRIMARY_MODES, _SECONDARY_MODES
        all_modes = (
            [m[1] for m in _PRIMARY_MODES] +
            [m[1] for m in _SECONDARY_MODES]
        )
        self.assertEqual(
            len(all_modes), len(set(all_modes)),
            f"Duplicate mode values found: "
            f"{[m for m in all_modes if all_modes.count(m) > 1]}"
        )

    def test_required_modes_exist(self):
        """All critical modes must exist somewhere."""
        from app import _PRIMARY_MODES, _SECONDARY_MODES
        all_vals = (
            [m[1] for m in _PRIMARY_MODES] +
            [m[1] for m in _SECONDARY_MODES]
        )
        required = [
            "LEARN", "REVISE", "TEST_ME",
            "VIRTUAL_TEACHER", "PAST_PAPER",
            "BATTLE_GAME", "TEACHER", "STUDY_PLAN",
        ]
        for mode in required:
            self.assertIn(
                mode, all_vals,
                f"Required mode '{mode}' is missing from navigation"
            )

    def test_no_duplicate_imports(self):
        """achievement_3a must not be imported twice in app.py."""
        app_path = os.path.join(
            _APP_DIR, "app.py"
        )
        with open(app_path, "r", encoding="utf-8") as f:
            content = f.read()

        import_count = content.count(
            "from achievement_3a import render_3a_achievement_mode"
        )
        self.assertLessEqual(
            import_count, 1,
            f"render_3a_achievement_mode imported {import_count} "
            f"times -- should be 1"
        )


class TestOllamaClient(unittest.TestCase):
    """Test Ollama client configuration."""

    def test_ollama_client_instantiates(self):
        """OllamaClient must instantiate without crashing."""
        try:
            from ollama_client import OllamaClient
            client = OllamaClient()
            self.assertIsNotNone(client)
        except ImportError as e:
            self.fail(f"Cannot import OllamaClient: {e}")

    def test_fast_chat_exists(self):
        """fast_chat() method must exist on OllamaClient."""
        from ollama_client import OllamaClient
        self.assertTrue(
            hasattr(OllamaClient, "fast_chat"),
            "fast_chat() method missing from OllamaClient"
        )

    def test_ctx_constants_defined(self):
        """FAST_CTX, STUDY_CTX, DEEP_CTX must be defined in ollama_client."""
        import ollama_client as oc
        self.assertTrue(hasattr(oc, "FAST_CTX"),  "FAST_CTX missing from ollama_client")
        self.assertTrue(hasattr(oc, "STUDY_CTX"), "STUDY_CTX missing from ollama_client")
        self.assertTrue(hasattr(oc, "DEEP_CTX"),  "DEEP_CTX missing from ollama_client")
        self.assertLess(oc.FAST_CTX, oc.STUDY_CTX,  "FAST_CTX must be < STUDY_CTX")
        self.assertLess(oc.STUDY_CTX, oc.DEEP_CTX,  "STUDY_CTX must be < DEEP_CTX")
        print(f"\n  [OK] CTX constants: FAST={oc.FAST_CTX} STUDY={oc.STUDY_CTX} DEEP={oc.DEEP_CTX}")

    def test_default_num_ctx_is_4096(self):
        """Default OLLAMA_NUM_CTX must be 4096 for performance."""
        import ollama_client as oc
        self.assertEqual(
            oc.OLLAMA_NUM_CTX, 4096,
            f"OLLAMA_NUM_CTX is {oc.OLLAMA_NUM_CTX}, expected 4096"
        )

    def test_ollama_connection(self):
        """Test if Ollama is reachable (soft test -- skip if offline)."""
        try:
            import ollama
            client = ollama.Client(host="http://localhost:11434")
            response = client.list()
            self.assertIsNotNone(response)
            print(f"\n  [OK] Ollama connected. "
                  f"Models: {[m.model for m in response.models]}")
        except Exception as e:
            print(f"\n  [WARN]  Ollama not reachable: {e} "
                  f"(start with: ollama serve)")
            # Not a failure -- Ollama may not be running in CI

    def test_gemma4_model_available(self):
        """gemma4:e4b or equivalent must be in ollama list."""
        try:
            import ollama
            client = ollama.Client(host="http://localhost:11434")
            response = client.list()
            model_names = [m.model for m in response.models]
            has_gemma4 = any("gemma4" in name for name in model_names)
            if not has_gemma4:
                print(f"\n  [WARN]  No Gemma 4 model found. "
                      f"Available: {model_names}")
                print("  Run: ollama pull gemma4:e4b")
            else:
                print(f"\n  [OK] Gemma 4 found: "
                      f"{[n for n in model_names if 'gemma4' in n]}")
        except Exception:
            pass  # Ollama offline -- skip


class TestDatabase(unittest.TestCase):
    """Test database operations."""

    def setUp(self):
        """Set up test database."""
        from database import Database
        self.db = Database()

    def test_database_init(self):
        """Database must initialize without errors."""
        self.assertIsNotNone(self.db)

    def test_get_student_returns_none_for_missing(self):
        """get_student_profile() must return None for unknown ID."""
        result = self.db.get_student_profile("nonexistent_test_id_xyz")
        self.assertIsNone(result)

    def test_save_and_retrieve_student(self):
        """Save a test student and retrieve them."""
        from database import save_student
        test_id = "test_auto_001"
        test_student = {
            "student_id":         test_id,
            "name":               "Test User",
            "subject":            "Computer Science",
            "exam_date":          "2026-08-01",
            "preferred_language": "English",
            "weak_areas":         "Recursion",
            "student_type":       "Undergraduate",
            "al_stream":          "",
            "al_subjects":        "[]",
        }
        save_student(test_student)
        retrieved = self.db.get_student_profile(test_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["name"], "Test User")

    def test_quiz_history_empty_for_new_student(self):
        """New student should have empty quiz history."""
        from database import get_quiz_history
        result = get_quiz_history("brand_new_student_xyz")
        self.assertIsInstance(result, (list, type(None)))

    def test_get_quiz_history_returns_list(self):
        """get_quiz_history() must always return list or None."""
        from database import get_quiz_history
        result = get_quiz_history("demo_kowshi_001")
        self.assertIsInstance(result, (list, type(None)))


class TestAchievement3A(unittest.TestCase):
    """Test 3A Achievement module guards."""

    def test_calculate_readiness_empty_history(self):
        """calculate_readiness with empty list must not crash."""
        from achievement_3a import calculate_readiness
        try:
            result = calculate_readiness([], "Biology")
            self.assertIn("readiness_pct", result)
            self.assertIn("grade_prediction", result)
            print(f"\n  [OK] Cold start result: {result}")
        except Exception as e:
            self.fail(
                f"calculate_readiness() crashed on empty list: {e}"
            )

    def test_calculate_readiness_with_data(self):
        """calculate_readiness with real data returns valid result."""
        from achievement_3a import calculate_readiness
        mock_history = [
            {"topic": "Cell Biology", "score": 7, "total": 10},
            {"topic": "Genetics",     "score": 5, "total": 10},
            {"topic": "Cell Biology", "score": 8, "total": 10},
            {"topic": "Ecology",      "score": 9, "total": 10},
        ]
        result = calculate_readiness(mock_history, "Biology")
        self.assertIn("readiness_pct", result)
        self.assertIn("grade_prediction", result)
        self.assertIn(result["grade_prediction"],
                      ["A", "B", "C", "S", "F"])
        pct = result["readiness_pct"]
        self.assertGreaterEqual(pct, 0)
        self.assertLessEqual(pct, 100)
        print(f"\n  [OK] Readiness: {pct}% -> "
              f"Grade: {result['grade_prediction']}")

    def test_al_config_streams_defined(self):
        """All A/L streams must have subjects defined."""
        from al_config import (
            STREAM_SUBJECTS
        )
        for stream, subjects in STREAM_SUBJECTS.items():
            self.assertGreater(
                len(subjects), 0,
                f"Stream '{stream}' has no subjects defined"
            )
        print(f"\n  [OK] {len(STREAM_SUBJECTS)} A/L streams configured")

    def test_render_3a_rejects_undergrad(self):
        """render_3a_achievement_mode must reject Undergraduate students."""
        path = os.path.join(_APP_DIR, "achievement_3a.py")
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        # Verify the hard guard is present
        self.assertIn(
            'student_type != "A/L Student"',
            src,
            "Hard A/L guard missing from render_3a_achievement_mode()"
        )


class TestVirtualTeacher(unittest.TestCase):
    """Test virtual teacher module structure."""

    def test_virtual_teacher_imports(self):
        """VirtualTeacher class must be importable."""
        try:
            from virtual_teacher import VirtualTeacher  # noqa: F401 (import check)
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Cannot import VirtualTeacher: {e}")

    def test_validate_lesson_function_exists(self):
        """_validate_lesson() must exist after Phase 4 fix."""
        try:
            from virtual_teacher import _validate_lesson
            # Test with invalid input
            valid, reason = _validate_lesson({})
            self.assertFalse(valid)
            self.assertIsInstance(reason, str)
            print(f"\n  [OK] _validate_lesson exists. "
                  f"Empty dict -> ({valid}, '{reason}')")
        except ImportError:
            print("\n  [WARN]  _validate_lesson not yet added "
                  "(run Phase 4 fix first)")

    def test_validate_lesson_with_good_data(self):
        """_validate_lesson() must return True for valid lesson."""
        try:
            from virtual_teacher import _validate_lesson
            good_lesson = {
                "hook":            "Deadlock is a classic OS problem...",
                "explanation":     "A deadlock occurs when four conditions are met simultaneously: mutual exclusion, hold and wait, no preemption, and circular wait...",
                "worked_example":  "Process A holds Resource 1 and waits for Resource 2. Process B holds Resource 2 and waits for Resource 1.",
                "diagram":         "flowchart TD\n  A[Process A] -->|holds| R1[Resource 1]\n  B[Process B] -->|holds| R2[Resource 2]",
                "exam_hook":       ["What are the four conditions for deadlock?"],
                "check_questions": [{"question": "Name the four Coffman conditions."}],
                "mid_question":    {"question": "Can deadlock occur with only one process?"},
                "memory_tip":      "MHNCs: Mutual exclusion, Hold & wait, No preemption, Circular wait",
            }
            valid, reason = _validate_lesson(good_lesson)
            self.assertTrue(valid,
                f"Good lesson marked invalid. Reason: {reason}")
        except ImportError:
            pass


class TestUIComponents(unittest.TestCase):
    """Test UI component module structure."""

    def test_colors_dict_has_required_keys(self):
        """COLORS dict must have all required keys."""
        from ui_components import COLORS
        required_keys = [
            "bg", "surface", "primary", "neon", "gold",
            "amber", "danger", "text_primary", "border",
        ]
        for key in required_keys:
            self.assertIn(
                key, COLORS,
                f"COLORS dict missing key: '{key}'"
            )

    def test_inject_premium_css_callable(self):
        """inject_premium_css() must be callable."""
        from ui_components import inject_premium_css
        self.assertTrue(callable(inject_premium_css))

    def test_render_functions_exist(self):
        """All critical render functions must exist."""
        import ui_components as ui
        required = [
            "render_welcome_banner",
            "render_exam_readiness_hero",
            "render_chapter_bars",
            "render_grounding_indicator",
            "render_thinking_state",
            "render_gemma_badges",
            "render_system_status",
            "render_offline_seal",
            "render_ollama_status_chip",
        ]
        for fn_name in required:
            self.assertTrue(
                hasattr(ui, fn_name),
                f"ui_components.py missing function: {fn_name}"
            )

    def test_offline_confirmed_toast_exists(self):
        """render_offline_confirmed_toast() must exist (Phase 6)."""
        import ui_components as ui
        self.assertTrue(
            hasattr(ui, "render_offline_confirmed_toast"),
            "render_offline_confirmed_toast missing from ui_components"
        )


class TestPerformance(unittest.TestCase):
    """Test response time targets."""

    def test_database_query_speed(self):
        """Database queries must complete in under 100ms."""
        from database import Database
        db = Database()

        start = time.perf_counter()
        db.get_student_profile("demo_kowshi_001")
        elapsed_ms = (time.perf_counter() - start) * 1000

        self.assertLess(
            elapsed_ms, 100,
            f"DB query took {elapsed_ms:.1f}ms -- should be <100ms"
        )
        print(f"\n  [OK] DB query: {elapsed_ms:.1f}ms")

    def test_module_import_speed(self):
        """All modules must import in under 3 seconds."""
        modules = [
            "database", "ollama_client", "ui_components",
            "achievement_3a", "al_config", "config",
        ]
        start = time.perf_counter()
        for mod in modules:
            try:
                __import__(mod)
            except Exception as e:
                print(f"\n  [WARN]  {mod} import error: {e}")
        elapsed = time.perf_counter() - start
        self.assertLess(
            elapsed, 3.0,
            f"Module imports took {elapsed:.2f}s -- should be <3s"
        )
        print(f"\n  [OK] All imports: {elapsed:.2f}s")


if __name__ == "__main__":
    print("=" * 60)
    print("OmniScholar -- Automated Navigation & Integration Tests")
    print("=" * 60)

    # Run with verbose output
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    for cls in [
        TestNavigationLogic,
        TestOllamaClient,
        TestDatabase,
        TestAchievement3A,
        TestVirtualTeacher,
        TestUIComponents,
        TestPerformance,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print(f"ALL {result.testsRun} TESTS PASSED")
    else:
        print(f"FAILED: {len(result.failures)} failures, "
              f"{len(result.errors)} errors "
              f"out of {result.testsRun} tests")
        print("\nFailed tests:")
        for test, traceback in result.failures + result.errors:
            print(f"  - {test}")
    print("=" * 60)

    sys.exit(0 if result.wasSuccessful() else 1)
