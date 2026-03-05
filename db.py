"""Persistence layer for Nuovo Fresco Pipe Network.

This module handles all database I/O using SQLModel + SQLite.
It must not import maze, main, or use print() / input().

Two tables:
  - SaveGame   : stores game state as a JSON blob, keyed by save slot name
  - QuestionBank: stores themed trivia questions with an asked/unanswered flag

Run with:  pytest tests/test_repo_contract.py -v
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func
from sqlmodel import Field, Session, SQLModel, create_engine, select


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

class RepositoryProtocol:
    """Interface contract for the persistence layer.

    db.py must implement all 8 methods below.
    main.py depends on this contract — never change signatures without
    updating interfaces.md and the test suite.
    """

    def save_game(self, state: dict[str, Any], save_slot: str = "default") -> bool: ...
    def load_game(self, save_slot: str = "default") -> dict[str, Any] | None: ...
    def delete_save(self, save_slot: str = "default") -> bool: ...
    def save_exists(self, save_slot: str = "default") -> bool: ...
    def get_unused_question(self) -> dict[str, Any] | None: ...
    def seed_questions(self, questions: list[dict[str, Any]]) -> int: ...
    def reset_questions(self) -> None: ...
    def get_question_count(self) -> dict[str, int]: ...


# ---------------------------------------------------------------------------
# SQLModel table definitions
# ---------------------------------------------------------------------------

class SaveGame(SQLModel, table=True):
    """One row per save slot.

    state_json holds the full GameState as a JSON string.
    main.py is responsible for converting dataclasses to/from dicts
    before calling save_game() or after calling load_game().
    """

    save_slot: str = Field(primary_key=True)
    state_json: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class QuestionBank(SQLModel, table=True):
    """One row per trivia question.

    prompt is unique — seeding the same question twice is a no-op.
    asked tracks whether this question has been served in the current game.
    Call reset_questions() at the start of each new game.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    prompt: str = Field(unique=True)
    choices_json: str          # JSON-encoded list[str]
    correct_answer: str
    asked: bool = False


# ---------------------------------------------------------------------------
# Thematic seed data — Nuovo Fresco Pipe Network
# ---------------------------------------------------------------------------
# Questions are designed to be fun and accessible — no specialist knowledge
# required. Players should feel clever when they get one right, not stumped.

SEED_QUESTIONS: list[dict[str, Any]] = [
    {
        "prompt": "What is the main job of a plumber in Nuovo Fresco?",
        "choices": ["Fixing broken pipes", "Painting walls", "Installing windows", "Rewiring electricity"],
        "correct_answer": "Fixing broken pipes",
    },
    {
        "prompt": "What does a clog in a pipe do to water flow?",
        "choices": ["Blocks it", "Speeds it up", "Heats it up", "Filters it"],
        "correct_answer": "Blocks it",
    },
    {
        "prompt": "Which direction does water naturally flow?",
        "choices": ["Downhill", "Uphill", "Sideways", "In circles"],
        "correct_answer": "Downhill",
    },
    {
        "prompt": "What tool do plumbers use to blast through a stubborn clog?",
        "choices": ["Hydro jet", "Hammer", "Screwdriver", "Wrench"],
        "correct_answer": "Hydro jet",
    },
    {
        "prompt": "What is water pressure measured in?",
        "choices": ["PSI (pounds per square inch)", "MPH (miles per hour)", "Watts", "Decibels"],
        "correct_answer": "PSI (pounds per square inch)",
    },
    {
        "prompt": "In Nuovo Fresco, what is the entry point to the pipe network called?",
        "choices": ["Entry valve", "Start door", "Open gate", "Flow switch"],
        "correct_answer": "Entry valve",
    },
    {
        "prompt": "What happens to water pressure when a pipe is clogged?",
        "choices": ["It drops", "It rises", "It stays the same", "It disappears"],
        "correct_answer": "It drops",
    },
    {
        "prompt": "What material are most modern water pipes made from?",
        "choices": ["PVC plastic or copper", "Wood", "Glass", "Rubber"],
        "correct_answer": "PVC plastic or copper",
    },
    {
        "prompt": "What is the exit point of the Nuovo Fresco pipe network called?",
        "choices": ["Exit drain", "End pipe", "Finish valve", "Out gate"],
        "correct_answer": "Exit drain",
    },
    {
        "prompt": "What does a valve do in a pipe system?",
        "choices": ["Controls water flow", "Heats the water", "Filters the water", "Measures the water"],
        "correct_answer": "Controls water flow",
    },
    {
        "prompt": "Which city is the setting of the Nuovo Fresco Pipe Network game?",
        "choices": ["Nuovo Fresco", "New York", "Pipe City", "Drain Town"],
        "correct_answer": "Nuovo Fresco",
    },
    {
        "prompt": "What is the name of the plumber's special high-pressure move?",
        "choices": ["Hydro blast", "Power surge", "Pipe punch", "Drain dash"],
        "correct_answer": "Hydro blast",
    },
    {
        "prompt": "What does 'Fog of War' mean in the pipe network?",
        "choices": ["Unexplored sections are hidden", "The pipes are full of steam", "The map is broken", "The lights are off"],
        "correct_answer": "Unexplored sections are hidden",
    },
    {
        "prompt": "What is a 'section' in the Nuovo Fresco pipe network?",
        "choices": ["One cell of the pipe grid", "A type of wrench", "A plumbing permit", "A water tank"],
        "correct_answer": "One cell of the pipe grid",
    },
    {
        "prompt": "What resource does the plumber spend to use a hydro blast?",
        "choices": ["Pressure", "Gold", "Energy drinks", "Time"],
        "correct_answer": "Pressure",
    },
    {
        "prompt": "What happens when all clogs in the network are cleared?",
        "choices": ["The network is cleared and you win", "The game resets", "A new clog appears", "The plumber retires"],
        "correct_answer": "The network is cleared and you win",
    },
    {
        "prompt": "What does answering a trivia question correctly do in the game?",
        "choices": ["Clears the clog and adds pressure", "Removes a pipe section", "Ends the game", "Adds a new clog"],
        "correct_answer": "Clears the clog and adds pressure",
    },
    {
        "prompt": "What is the penalty for answering a trivia question incorrectly?",
        "choices": ["You lose pressure", "You lose a life", "The game ends", "You go back to the start"],
        "correct_answer": "You lose pressure",
    },
    {
        "prompt": "What does a drain do at the end of a pipe system?",
        "choices": ["Removes water from the system", "Adds water to the system", "Blocks water flow", "Heats the water"],
        "correct_answer": "Removes water from the system",
    },
    {
        "prompt": "In plumbing, what does 'open connection' mean?",
        "choices": ["Water can flow through", "The pipe is broken", "The valve is locked", "The pipe is empty"],
        "correct_answer": "Water can flow through",
    },
]


# ---------------------------------------------------------------------------
# Repository implementation
# ---------------------------------------------------------------------------

class SQLiteRepository:
    """SQLModel-backed repository using SQLite.

    All game state is stored as a JSON blob in the SaveGame table.
    Questions are stored as individual rows in the QuestionBank table.

    Usage:
        repo = SQLiteRepository()                  # real game — uses savegame.db
        repo = SQLiteRepository(":memory:")        # tests — in-memory, no file created
    """

    def __init__(self, db_path: str = "savegame.db") -> None:
        # create_engine connects to (or creates) the SQLite file.
        # ":memory:" is a special SQLite database that lives only in RAM.
        # Note: in-memory databases are tied to a connection; because we reuse
        # one engine instance, this works well for local/testing scenarios.
        connect_args = {"check_same_thread": False}
        url = "sqlite:///:memory:" if db_path == ":memory:" else f"sqlite:///{db_path}"
        self._engine = create_engine(
            url,
            connect_args=connect_args,
        )
        # SQLModel.metadata.create_all creates the tables if they don't exist yet.
        # Running it multiple times is safe — it skips tables that already exist.
        SQLModel.metadata.create_all(self._engine)

    # ------------------------------------------------------------------
    # Game state persistence
    # ------------------------------------------------------------------

    def save_game(self, state: dict[str, Any], save_slot: str = "default") -> bool:
        """Serialize state dict to JSON and upsert into SaveGame table.

        An upsert means: insert if the slot doesn't exist, update if it does.
        Returns True on success, False if serialization or DB write fails.
        """
        try:
            state_json = json.dumps(state)
        except (TypeError, ValueError):
            return False

        try:
            with Session(self._engine) as session:
                existing = session.get(SaveGame, save_slot)
                if existing:
                    # Update the existing row
                    existing.state_json = state_json
                    existing.updated_at = datetime.utcnow()
                    session.add(existing)
                else:
                    # Insert a new row
                    session.add(SaveGame(
                        save_slot=save_slot,
                        state_json=state_json,
                        updated_at=datetime.utcnow(),
                    ))
                session.commit()
            return True
        except Exception:
            return False

    def load_game(self, save_slot: str = "default") -> dict[str, Any] | None:
        """Fetch and deserialize the JSON blob for the given save slot.

        Returns a plain dict, or None if the slot doesn't exist or data is corrupt.
        """
        try:
            with Session(self._engine) as session:
                row = session.get(SaveGame, save_slot)
                if row is None:
                    return None
                data = json.loads(row.state_json)
                return data if isinstance(data, dict) else None
        except Exception:
            return None

    def delete_save(self, save_slot: str = "default") -> bool:
        """Delete the save slot row. Returns True if deleted, False if not found."""
        try:
            with Session(self._engine) as session:
                row = session.get(SaveGame, save_slot)
                if row is None:
                    return False
                session.delete(row)
                session.commit()
            return True
        except Exception:
            return False

    def save_exists(self, save_slot: str = "default") -> bool:
        """Return True if the save slot exists in the database."""
        try:
            with Session(self._engine) as session:
                return session.get(SaveGame, save_slot) is not None
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Question bank management
    # ------------------------------------------------------------------

    def get_unused_question(self) -> dict[str, Any] | None:
        """Return a random unused question and mark it as asked.

        Returns a plain dict with keys: prompt, choices, correct_answer.
        Returns None if all questions have been asked — call reset_questions()
        to start a new game cycle.
        """
        try:
            with Session(self._engine) as session:
                # Let SQLite pick a random unused question without loading all rows.
                question = session.exec(
                    select(QuestionBank)
                    .where(QuestionBank.asked == False)  # noqa: E712
                    .order_by(func.random())
                    .limit(1)
                ).first()
                if question is None:
                    return None
                question.asked = True
                session.add(question)
                session.commit()
                return {
                    "prompt": question.prompt,
                    "choices": json.loads(question.choices_json),
                    "correct_answer": question.correct_answer,
                }
        except Exception:
            return None

    def seed_questions(self, questions: list[dict[str, Any]]) -> int:
        """Bulk-load questions into the QuestionBank table.

        Skips any question whose prompt already exists (deduplication).
        Returns the count of NEW questions actually inserted.

        Safe to call multiple times with the same data — idempotent.
        """
        added = 0
        try:
            with Session(self._engine) as session:
                for q in questions:
                    prompt = q.get("prompt", "")
                    existing = session.exec(
                        select(QuestionBank).where(QuestionBank.prompt == prompt)
                    ).first()
                    if existing:
                        continue
                    session.add(QuestionBank(
                        prompt=prompt,
                        choices_json=json.dumps(q.get("choices", [])),
                        correct_answer=q.get("correct_answer", ""),
                        asked=False,
                    ))
                    added += 1
                session.commit()
        except Exception:
            pass
        return added

    def reset_questions(self) -> None:
        """Clear the asked flag on all questions — call at the start of a new game."""
        try:
            with Session(self._engine) as session:
                statement = select(QuestionBank).where(QuestionBank.asked == True)  # noqa: E712
                asked_questions = session.exec(statement).all()
                for q in asked_questions:
                    q.asked = False
                    session.add(q)
                session.commit()
        except Exception:
            pass

    def get_question_count(self) -> dict[str, int]:
        """Return question usage statistics.

        Returns: {"total": int, "asked": int, "remaining": int}
        """
        try:
            with Session(self._engine) as session:
                all_questions = session.exec(select(QuestionBank)).all()
                total = len(all_questions)
                asked = sum(1 for q in all_questions if q.asked)
                return {
                    "total": total,
                    "asked": asked,
                    "remaining": total - asked,
                }
        except Exception:
            return {"total": 0, "asked": 0, "remaining": 0}
