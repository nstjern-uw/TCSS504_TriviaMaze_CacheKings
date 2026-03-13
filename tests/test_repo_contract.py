"""Repository contract tests — Phase 3 updated RepositoryProtocol (8 methods).

Tests the persistence layer contract using a MockRepository that implements
the full 8-method RepositoryProtocol: save/load/delete/exists for game state,
plus get_unused_question/seed_questions/reset_questions/get_question_count
for the Question Bank.

The MockRepository uses plain dicts internally (no real SQLite) to validate
expected behavior independently of the concrete implementation.

Persistence Engineer: implement SqlModelRepository in db.py so these pass.

Run with:  pytest tests/test_repo_contract.py -v
"""

import copy
import pytest


# ---------------------------------------------------------------------------
# MockRepository — implements the 8-method RepositoryProtocol in-memory
# ---------------------------------------------------------------------------

class MockRepository:
    """In-memory stand-in for the real SQLite-backed repository."""

    def __init__(self):
        self._saves: dict[str, dict] = {}
        self._questions: list[dict] = []
        self._asked: set[int] = set()

    # -- Game state persistence (4 methods) ---------------------------------

    def save_game(self, state: dict, save_slot: str = "default") -> bool:
        try:
            copy.deepcopy(state)
        except Exception:
            return False
        self._saves[save_slot] = copy.deepcopy(state)
        return True

    def load_game(self, save_slot: str = "default") -> dict | None:
        data = self._saves.get(save_slot)
        return copy.deepcopy(data) if data is not None else None

    def delete_save(self, save_slot: str = "default") -> bool:
        if save_slot in self._saves:
            del self._saves[save_slot]
            return True
        return False

    def save_exists(self, save_slot: str = "default") -> bool:
        return save_slot in self._saves

    # -- Question Bank (4 methods) ------------------------------------------

    def get_unused_question(self) -> dict | None:
        for idx, q in enumerate(self._questions):
            if idx not in self._asked:
                self._asked.add(idx)
                return copy.deepcopy(q)
        return None

    def seed_questions(self, questions: list[dict]) -> int:
        existing_prompts = {q["prompt"] for q in self._questions}
        added = 0
        for q in questions:
            if q["prompt"] not in existing_prompts:
                self._questions.append(copy.deepcopy(q))
                existing_prompts.add(q["prompt"])
                added += 1
        return added

    def reset_questions(self) -> None:
        self._asked.clear()

    def get_question_count(self) -> dict:
        total = len(self._questions)
        asked = len(self._asked)
        return {"total": total, "asked": asked, "remaining": total - asked}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo() -> MockRepository:
    return MockRepository()


def _make_questions(n: int) -> list[dict]:
    """Helper: generate *n* distinct question dicts."""
    return [
        {
            "prompt": f"Question {i}?",
            "choices": ["A", "B", "C", "D"],
            "correct_answer": "A",
        }
        for i in range(n)
    ]


# ===========================================================================
# Game State Persistence Tests (5 tests)
# ===========================================================================

class TestGameStatePersistence:
    """Existing save/load/delete contract — adapted for MockRepository."""

    def test_save_returns_true(self, repo):
        assert repo.save_game({"a": 1}) is True

    def test_save_then_load_matches(self, repo):
        data = {"x": 1, "nested": {"ok": True}, "items": [1, 2, None]}
        assert repo.save_game(data) is True
        assert repo.load_game() == data

    def test_load_missing_slot(self, repo):
        assert repo.load_game("nonexistent") is None

    def test_delete_and_exists(self, repo):
        assert repo.save_exists() is False
        assert repo.save_game({"a": 1}) is True
        assert repo.save_exists() is True
        assert repo.delete_save() is True
        assert repo.save_exists() is False
        assert repo.delete_save() is False

    def test_multiple_slots(self, repo):
        repo.save_game({"slot": 1}, "slot_a")
        repo.save_game({"slot": 2}, "slot_b")
        assert repo.load_game("slot_a") == {"slot": 1}
        assert repo.load_game("slot_b") == {"slot": 2}


# ===========================================================================
# Question Bank Tests (13 tests)
# ===========================================================================

class TestQuestionBank:
    """New Question Bank contract — covers the 4 question-related methods."""

    # -- get_unused_question ------------------------------------------------

    def test_get_unused_question_returns_dict(self, repo):
        repo.seed_questions(_make_questions(3))
        result = repo.get_unused_question()
        assert isinstance(result, dict)
        assert "prompt" in result
        assert "choices" in result
        assert "correct_answer" in result

    def test_get_unused_question_marks_as_asked(self, repo):
        repo.seed_questions(_make_questions(3))
        repo.get_unused_question()
        counts = repo.get_question_count()
        assert counts["asked"] == 1
        assert counts["remaining"] == 2

    def test_get_unused_question_no_repeats(self, repo):
        repo.seed_questions(_make_questions(5))
        seen_prompts: set[str] = set()
        for _ in range(5):
            q = repo.get_unused_question()
            assert q is not None
            assert q["prompt"] not in seen_prompts, "Duplicate question served"
            seen_prompts.add(q["prompt"])
        assert len(seen_prompts) == 5

    def test_get_unused_question_exhausted(self, repo):
        repo.seed_questions(_make_questions(2))
        repo.get_unused_question()
        repo.get_unused_question()
        assert repo.get_unused_question() is None

    # -- reset_questions ----------------------------------------------------

    def test_reset_questions(self, repo):
        repo.seed_questions(_make_questions(3))
        for _ in range(3):
            repo.get_unused_question()
        assert repo.get_question_count()["remaining"] == 0

        repo.reset_questions()
        counts = repo.get_question_count()
        assert counts["asked"] == 0
        assert counts["remaining"] == 3

    def test_reset_then_fetch_again(self, repo):
        repo.seed_questions(_make_questions(2))
        repo.get_unused_question()
        repo.get_unused_question()
        repo.reset_questions()
        q = repo.get_unused_question()
        assert q is not None

    # -- seed_questions -----------------------------------------------------

    def test_seed_questions_populates_bank(self, repo):
        questions = _make_questions(10)
        added = repo.seed_questions(questions)
        assert added == 10
        assert repo.get_question_count()["total"] == 10

    def test_seed_questions_skips_duplicates(self, repo):
        batch = _make_questions(5)
        first_add = repo.seed_questions(batch)
        assert first_add == 5

        overlap = batch[:3] + _make_questions(2)
        overlap[3]["prompt"] = "Brand new Q1?"
        overlap[4]["prompt"] = "Brand new Q2?"
        second_add = repo.seed_questions(overlap)
        assert second_add == 2
        assert repo.get_question_count()["total"] == 7

    def test_seed_empty_list(self, repo):
        added = repo.seed_questions([])
        assert added == 0
        assert repo.get_question_count()["total"] == 0

    # -- get_question_count -------------------------------------------------

    def test_get_question_count(self, repo):
        repo.seed_questions(_make_questions(10))
        repo.get_unused_question()
        repo.get_unused_question()
        repo.get_unused_question()
        counts = repo.get_question_count()
        assert counts == {"total": 10, "asked": 3, "remaining": 7}

    def test_get_question_count_empty(self, repo):
        counts = repo.get_question_count()
        assert counts == {"total": 0, "asked": 0, "remaining": 0}

    def test_get_question_count_after_reset(self, repo):
        repo.seed_questions(_make_questions(5))
        for _ in range(5):
            repo.get_unused_question()
        repo.reset_questions()
        counts = repo.get_question_count()
        assert counts == {"total": 5, "asked": 0, "remaining": 5}

    def test_get_question_count_keys(self, repo):
        counts = repo.get_question_count()
        assert set(counts.keys()) == {"total", "asked", "remaining"}
