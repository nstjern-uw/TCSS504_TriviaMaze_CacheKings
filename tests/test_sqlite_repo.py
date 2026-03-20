"""SQLiteRepository integration tests — real SQLite, in-memory database.

Unlike test_repo_contract.py (which tests MockRepository), these tests
exercise the actual SQLiteRepository implementation against a live SQLite
":memory:" database to verify the concrete persistence layer behaves
correctly end-to-end.

Run with:  pytest tests/test_sqlite_repo.py -v
"""

import pytest

from db import SQLiteRepository, SEED_QUESTIONS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo() -> SQLiteRepository:
    """A fresh in-memory SQLiteRepository for each test."""
    return SQLiteRepository(":memory:")


def _make_questions(n: int) -> list[dict]:
    """Generate n distinct question dicts for testing."""
    return [
        {
            "prompt": f"Test question {i}?",
            "choices": ["A", "B", "C", "D"],
            "correct_answer": "A",
        }
        for i in range(n)
    ]


# ===========================================================================
# Game State Persistence (6 tests)
# ===========================================================================

class TestSQLiteGameStatePersistence:

    def test_save_returns_true(self, repo: SQLiteRepository) -> None:
        assert repo.save_game({"score": 42}) is True

    def test_save_then_load_matches(self, repo: SQLiteRepository) -> None:
        data = {"player": {"row": 1, "col": 2}, "pressure": 80, "items": [1, 2, None]}
        assert repo.save_game(data) is True
        loaded = repo.load_game()
        assert loaded == data

    def test_load_missing_slot_returns_none(self, repo: SQLiteRepository) -> None:
        assert repo.load_game("nonexistent") is None

    def test_delete_and_exists(self, repo: SQLiteRepository) -> None:
        assert repo.save_exists() is False
        repo.save_game({"x": 1})
        assert repo.save_exists() is True
        assert repo.delete_save() is True
        assert repo.save_exists() is False
        assert repo.delete_save() is False

    def test_multiple_slots_are_independent(self, repo: SQLiteRepository) -> None:
        repo.save_game({"slot": "a"}, save_slot="slot_a")
        repo.save_game({"slot": "b"}, save_slot="slot_b")
        assert repo.load_game("slot_a") == {"slot": "a"}
        assert repo.load_game("slot_b") == {"slot": "b"}

    def test_overwrite_same_slot(self, repo: SQLiteRepository) -> None:
        repo.save_game({"version": 1})
        repo.save_game({"version": 2})
        loaded = repo.load_game()
        assert loaded == {"version": 2}

    def test_list_save_slots_empty(self, repo: SQLiteRepository) -> None:
        assert repo.list_save_slots() == []

    def test_list_save_slots_returns_all_slots(self, repo: SQLiteRepository) -> None:
        repo.save_game({"x": 1}, save_slot="alpha")
        repo.save_game({"x": 2}, save_slot="beta")
        repo.save_game({"x": 3}, save_slot="gamma")
        slots = repo.list_save_slots()
        assert set(slots) == {"alpha", "beta", "gamma"}
        assert len(slots) == 3


# ===========================================================================
# Question Bank (6 tests)
# ===========================================================================

class TestSQLiteQuestionBank:

    def test_seed_and_count(self, repo: SQLiteRepository) -> None:
        added = repo.seed_questions(SEED_QUESTIONS)
        assert added == len(SEED_QUESTIONS)
        counts = repo.get_question_count()
        assert counts["total"] == len(SEED_QUESTIONS)
        assert counts["asked"] == 0
        assert counts["remaining"] == len(SEED_QUESTIONS)

    def test_get_unused_question_returns_dict(self, repo: SQLiteRepository) -> None:
        repo.seed_questions(_make_questions(3))
        result = repo.get_unused_question()
        assert result is not None
        assert isinstance(result, dict)
        assert "prompt" in result
        assert "choices" in result
        assert "correct_answer" in result

    def test_get_unused_question_marks_as_asked(self, repo: SQLiteRepository) -> None:
        repo.seed_questions(_make_questions(5))
        repo.get_unused_question()
        counts = repo.get_question_count()
        assert counts["asked"] == 1
        assert counts["remaining"] == 4

    def test_seed_deduplication(self, repo: SQLiteRepository) -> None:
        first = repo.seed_questions(SEED_QUESTIONS)
        assert first == len(SEED_QUESTIONS)
        second = repo.seed_questions(SEED_QUESTIONS)
        assert second == 0
        assert repo.get_question_count()["total"] == len(SEED_QUESTIONS)

    def test_reset_questions(self, repo: SQLiteRepository) -> None:
        repo.seed_questions(_make_questions(4))
        for _ in range(4):
            repo.get_unused_question()
        assert repo.get_question_count()["remaining"] == 0
        repo.reset_questions()
        counts = repo.get_question_count()
        assert counts["asked"] == 0
        assert counts["remaining"] == 4
        assert repo.get_unused_question() is not None

    def test_get_unused_question_exhausted(self, repo: SQLiteRepository) -> None:
        repo.seed_questions(_make_questions(2))
        repo.get_unused_question()
        repo.get_unused_question()
        assert repo.get_unused_question() is None
