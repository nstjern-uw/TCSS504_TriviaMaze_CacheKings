# Persistence Engineer Quickstart — test_repo_contract.py

**Role:** The Persistence Engineer (Part 2)  
**Your Tests:** `tests/test_repo_contract.py` (18 tests)  
**Your Module:** `db.py`  
**Prepared by:** Ryan Belmonte, Part 1 Domain Architect

---

## Your Mission

Implement `db.py` such that all 18 tests in `test_repo_contract.py` pass. The tests define the exact interface you must provide.

---

## The RepositoryProtocol (8 Methods)

Your implementation **must** provide these 8 methods:

### 1. Game State Persistence

```python
def save_game(self, state: dict, save_slot: str = "default") -> bool:
    """Save game state to database. Return True on success, False on error."""
    ...

def load_game(self, save_slot: str = "default") -> dict | None:
    """Load game state from database. Return dict or None if not found."""
    ...

def delete_save(self, save_slot: str = "default") -> bool:
    """Delete a save slot. Return True if deleted, False if didn't exist."""
    ...

def save_exists(self, save_slot: str = "default") -> bool:
    """Check if a save slot exists. Return True/False."""
    ...
```

**Contract Tests (5):**
- `test_save_returns_true` — `save_game()` succeeds
- `test_save_then_load_matches` — Round-trip preserves data
- `test_load_missing_slot` — Returns `None` for nonexistent slot
- `test_delete_and_exists` — Slot lifecycle works
- `test_save_non_serializable_returns_false` — Handles bad data

**Implementation Notes:**
- Use **SQLite** (Phase 3 requirement)
- Store state as **JSON blob** in a single column (per RFC)
- Support multiple save slots by column or separate rows
- Test data includes nested dicts and arrays: `{"x": 1, "nested": {"ok": True}, "items": [1, 2, None]}`

---

### 2. Question Bank Management

```python
def get_unused_question(self) -> dict | None:
    """Return next unused question as dict with keys:
    - "prompt": str
    - "choices": list[str]
    - "correct_answer": str
    
    Once returned, mark it as asked so it won't repeat in same game.
    Return None if all questions exhausted.
    """
    ...

def seed_questions(self, questions: list[dict]) -> int:
    """Bulk-load questions from list of dicts.
    Each dict has: {"prompt": str, "choices": list, "correct_answer": str}
    
    Skip duplicates (same prompt = duplicate).
    Return count of NEW questions added.
    """
    ...

def reset_questions(self) -> None:
    """Clear the 'asked' flag on all questions for new game."""
    ...

def get_question_count(self) -> dict:
    """Return stats: {"total": int, "asked": int, "remaining": int}"""
    ...
```

**Contract Tests (13):**
- `test_get_unused_question_returns_dict` — Shape is correct
- `test_get_unused_question_marks_as_asked` — No repeats in same game
- `test_get_unused_question_no_repeats` — 5-question bank exhausts properly
- `test_get_unused_question_exhausted` — Returns None when empty
- `test_reset_questions` — Flags cleared for new game
- `test_seed_questions_populates_bank` — Bulk-load works
- `test_seed_questions_skips_duplicates` — Deduplication by prompt
- `test_get_question_count` — Stats accurate

**Implementation Notes:**
- **SQLModel:** Use dataclass-like ORM mapping
- **Unique prompts:** Can reload same JSON file without duplication
- **State column:** Track "has_been_asked" per question in DB
- **Stateless API:** `reset_questions()` clears flags for new game session
- **Exhaustion:** Return `None` when `asked_count == total_count`

---

## Test File Structure

```python
# MockRepository (in test file)
# ├─ Implements all 8 methods
# ├─ Uses dict storage (not real SQLite)
# └─ Shows expected behavior

# Test suite
# ├─ test_save_*
# ├─ test_load_*
# ├─ test_delete_*
# ├─ test_save_exists*
# ├─ test_get_unused_question_*
# ├─ test_reset_questions
# ├─ test_seed_questions_*
# └─ test_get_question_count
```

---

## How to Run Your Tests

```bash
cd tcss504-quiz-game
python -m pytest tests/test_repo_contract.py -v
```

Expected output (after implementation):
```
tests/test_repo_contract.py::test_save_returns_true PASSED
tests/test_repo_contract.py::test_save_then_load_matches PASSED
tests/test_repo_contract.py::test_load_missing_slot PASSED
tests/test_repo_contract.py::test_save_non_serializable_returns_false PASSED
tests/test_repo_contract.py::test_delete_and_exists PASSED
tests/test_repo_contract.py::test_get_unused_question_returns_dict PASSED
tests/test_repo_contract.py::test_get_unused_question_marks_as_asked PASSED
tests/test_repo_contract.py::test_get_unused_question_no_repeats PASSED
tests/test_repo_contract.py::test_get_unused_question_exhausted PASSED
tests/test_repo_contract.py::test_reset_questions PASSED
tests/test_repo_contract.py::test_seed_questions_populates_bank PASSED
tests/test_repo_contract.py::test_seed_questions_skips_duplicates PASSED
tests/test_repo_contract.py::test_get_question_count PASSED

====== 13 passed in 0.42s ======
```

---

## Data Model Sketch

Suggested SQLite schema (using SQLModel):

```python
from sqlmodel import SQLModel, Field
from typing import Optional

class GameSave(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    save_slot: str = Field(unique=True)
    state_json: str  # JSON blob

class Question(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    prompt: str = Field(unique=True)
    choices_json: str  # Serialized list
    correct_answer: str
    has_been_asked: bool = False
```

---

## Integration Points

**Your db.py will be used by:**

1. **main.py** (GameEngine)
   - Calls `save_game(gamestate_dict, "default")`
   - Calls `load_game("default")`
   - Calls `get_unused_question()` during gameplay

2. **test_integration.py** (15 tests)
   - Verifies round-trip serialization
   - Confirms questions flow through engine

3. **test_module_isolation.py** (14 tests)
   - Verifies no `maze` imports in `db.py`
   - Confirms all 8 methods exist

---

## Key Constraints (From RUNBOOK.md)

✅ **DO:**
- Import `db` in `main.py` ✓
- Use SQLModel for ORM ✓
- Store state as JSON blob ✓
- Track question "asked" state ✓
- Dedup on prompt when seeding ✓
- Return `None` for missing data ✓

❌ **DON'T:**
- Import `maze.py` in `db.py` ✗ (tests catch this)
- Import `main.py` in `db.py` ✗ (tests catch this)
- Use `print()` in `db.py` ✗ (tests catch this)
- Serialize/deserialize dataclasses (main.py's job) ✗
- Mix game logic with persistence ✗

---

## Success Criteria

All 18 tests pass AND:
- ✅ Uses SQLite (not JSON files)
- ✅ Implements exact 8-method protocol
- ✅ No `print()` calls
- ✅ No imports from `maze.py` or `main.py`
- ✅ Handles `None` gracefully
- ✅ Deduplicates questions by prompt
- ✅ Supports multiple save slots

---

## References

- **Interface Spec:** `docs/interfaces.md` (RepositoryProtocol section)
- **Test Reference:** `tests/test_repo_contract.py`
- **RFC:** `docs/RFC-ryan-part1-design-contracts-domain-architect.md` (persistence strategy)
- **Module Rules:** `docs/RUNBOOK.md`

Good luck! 🚿💨
