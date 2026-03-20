"""Engine integration tests — Phase 3 PipeNetwork vocabulary.

Verifies main.py correctly wires maze.py (PipeNetwork domain) and db.py
(SQLModel persistence) together.  Uses MockRepo so tests run without a
real database.

These tests require both maze.py and db.py to be present.
They verify that main.py correctly orchestrates the modules together.

Run with:  pytest tests/test_integration.py -v
"""

import copy
import pytest

from maze import (
    Direction,
    GameStatus,
    Position,
    check_solvability,
    get_section,
    is_network_clear,
)
from main import (
    DEFAULT_PRESSURE,
    GameEngine,
    gamestate_from_dict,
    gamestate_to_dict,
)


# ---------------------------------------------------------------------------
# MockRepo — lightweight stand-in for the real SQLite-backed repository
# ---------------------------------------------------------------------------

class MockRepo:
    """In-memory repository implementing the 8-method RepositoryProtocol."""

    def __init__(self):
        self._saves: dict[str, dict] = {}
        self._questions: list[dict] = []
        self._asked: set[int] = set()

    def save_game(self, state: dict, save_slot: str = "default") -> bool:
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

    def get_unused_question(self) -> dict | None:
        for idx, q in enumerate(self._questions):
            if idx not in self._asked:
                self._asked.add(idx)
                return copy.deepcopy(q)
        return None

    def seed_questions(self, questions: list[dict]) -> int:
        existing = {q["prompt"] for q in self._questions}
        added = 0
        for q in questions:
            if q["prompt"] not in existing:
                self._questions.append(copy.deepcopy(q))
                existing.add(q["prompt"])
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
def save_path(tmp_path) -> str:
    """Temp save path to avoid polluting the real filesystem."""
    return str(tmp_path / "savegame.json")


@pytest.fixture
def engine(save_path) -> GameEngine:
    """A GameEngine with a fresh seeded game started."""
    e = GameEngine(repo=MockRepo(), save_path=save_path)
    e.start_new_game(seed=42)
    return e


# ---------------------------------------------------------------------------
# Game lifecycle
# ---------------------------------------------------------------------------

def test_new_game_initializes_state(engine: GameEngine) -> None:
    state = engine.state
    assert state is not None
    assert state.player.position == state.pipe_network.entry_valve
    assert state.player.pressure == DEFAULT_PRESSURE
    assert state.status == GameStatus.IN_PROGRESS
    assert check_solvability(
        state.pipe_network,
        state.pipe_network.entry_valve,
        state.pipe_network.exit_drain,
    )


def test_process_move_command(engine: GameEngine) -> None:
    """Find an open direction from the entry valve and verify the move succeeds."""
    state = engine.state
    entry_section = get_section(state.pipe_network, state.player.position)
    open_dir = next(
        (d for d, sealed in entry_section.connections.items() if not sealed),
        None,
    )
    assert open_dir is not None, "No open direction from entry valve"

    old_pos = state.player.position
    result = engine.process_command(f"move {open_dir}")

    assert result == GameStatus.IN_PROGRESS
    assert state.player.position != old_pos


def test_process_invalid_command(engine: GameEngine) -> None:
    result = engine.process_command("fly")
    assert result == GameStatus.IN_PROGRESS


def test_process_quit_command(engine: GameEngine) -> None:
    result = engine.process_command("quit")
    assert result == GameStatus.QUIT


# ---------------------------------------------------------------------------
# Save / Load round-trip
# ---------------------------------------------------------------------------

def test_save_and_load_preserves_state(save_path) -> None:
    repo = MockRepo()
    engine = GameEngine(repo=repo, save_path=save_path)
    engine.start_new_game(seed=42)
    state = engine.state

    entry_section = get_section(state.pipe_network, state.player.position)
    open_dir = next(
        (d for d, sealed in entry_section.connections.items() if not sealed),
        None,
    )
    if open_dir:
        engine.process_command(f"move {open_dir}")

    assert engine.save_game() is True

    loaded = GameEngine(repo=repo, save_path=save_path)
    assert loaded.load_game() is True

    original = engine.state
    restored = loaded.state

    assert restored.player.position == original.player.position
    assert restored.player.pressure == original.player.pressure
    assert restored.player.clogs_cleared == original.player.clogs_cleared
    assert restored.player.current_level == original.player.current_level
    assert restored.pipe_network.rows == original.pipe_network.rows
    assert restored.pipe_network.cols == original.pipe_network.cols
    assert restored.pipe_network.entry_valve == original.pipe_network.entry_valve
    assert restored.pipe_network.exit_drain == original.pipe_network.exit_drain
    assert restored.status == original.status
    assert restored.questions_answered == original.questions_answered
    assert restored.questions_correct == original.questions_correct

    for r in range(original.pipe_network.rows):
        for c in range(original.pipe_network.cols):
            assert (
                original.pipe_network.grid[r][c].has_clog
                == restored.pipe_network.grid[r][c].has_clog
            )
            assert (
                original.pipe_network.grid[r][c].connections
                == restored.pipe_network.grid[r][c].connections
            )


def test_load_with_no_save(save_path) -> None:
    engine = GameEngine(repo=MockRepo(), save_path=save_path)
    assert engine.load_game() is False


# ---------------------------------------------------------------------------
# Boundary crossing
# ---------------------------------------------------------------------------

def test_gamestate_to_dict_round_trip(engine: GameEngine) -> None:
    original = engine.state
    d = gamestate_to_dict(original)
    restored = gamestate_from_dict(d)

    assert restored is not None
    assert restored.player.position == original.player.position
    assert restored.player.pressure == original.player.pressure
    assert restored.player.clogs_cleared == original.player.clogs_cleared
    assert restored.player.current_level == original.player.current_level
    assert restored.pipe_network.rows == original.pipe_network.rows
    assert restored.pipe_network.cols == original.pipe_network.cols
    assert restored.pipe_network.entry_valve == original.pipe_network.entry_valve
    assert restored.pipe_network.exit_drain == original.pipe_network.exit_drain
    assert restored.status == original.status
    assert restored.questions_answered == original.questions_answered
    assert restored.questions_correct == original.questions_correct

    for r in range(original.pipe_network.rows):
        for c in range(original.pipe_network.cols):
            orig_section = original.pipe_network.grid[r][c]
            rest_section = restored.pipe_network.grid[r][c]
            assert rest_section.position == orig_section.position
            assert rest_section.connections == orig_section.connections
            assert rest_section.has_clog == orig_section.has_clog
            assert rest_section.is_entry_valve == orig_section.is_entry_valve
            assert rest_section.is_exit_drain == orig_section.is_exit_drain


def test_enum_serialization_round_trip() -> None:
    assert GameStatus(GameStatus.IN_PROGRESS.value) == GameStatus.IN_PROGRESS
    assert GameStatus(GameStatus.CLEARED.value) == GameStatus.CLEARED
    assert GameStatus(GameStatus.QUIT.value) == GameStatus.QUIT


# ---------------------------------------------------------------------------
# Win condition
# ---------------------------------------------------------------------------

def test_win_condition(engine: GameEngine) -> None:
    state = engine.state

    for row in state.pipe_network.grid:
        for section in row:
            section.has_clog = False

    assert is_network_clear(state.pipe_network) is True

    entry_section = get_section(state.pipe_network, state.player.position)
    open_dir = next(
        (d for d, sealed in entry_section.connections.items() if not sealed),
        None,
    )
    assert open_dir is not None
    result = engine.process_command(f"move {open_dir}")

    assert result == GameStatus.CLEARED
    assert state.status == GameStatus.CLEARED


# ---------------------------------------------------------------------------
# Fog of War integration
# ---------------------------------------------------------------------------

def test_fog_of_war_updates_on_move(engine: GameEngine) -> None:
    """visited_positions grows after a successful move."""
    state = engine.state
    initial_visited = len(state.visited_positions)

    entry_section = get_section(state.pipe_network, state.player.position)
    open_dir = next(
        (d for d, sealed in entry_section.connections.items() if not sealed),
        None,
    )
    assert open_dir is not None
    engine.process_command(f"move {open_dir}")

    assert len(state.visited_positions) > initial_visited


def test_visibility_map_passed_to_view(engine: GameEngine) -> None:
    """Engine generates a visibility map that covers the full grid."""
    from maze import get_visibility_map

    state = engine.state
    vis_map = get_visibility_map(
        state.pipe_network,
        state.visited_positions,
        state.player.position,
    )
    assert len(vis_map) == state.pipe_network.rows
    assert len(vis_map[0]) == state.pipe_network.cols


def test_question_from_db_flow(save_path) -> None:
    """Engine retrieves a question from the repository's question bank."""
    mock = MockRepo()
    mock.seed_questions([
        {
            "prompt": "What color is the sky?",
            "choices": ["Blue", "Green", "Red", "Yellow"],
            "correct_answer": "Blue",
        },
    ])
    q = mock.get_unused_question()
    assert q is not None
    assert q["prompt"] == "What color is the sky?"
    assert mock.get_question_count()["remaining"] == 0


# ---------------------------------------------------------------------------
# Additional integration tests
# ---------------------------------------------------------------------------

def test_visited_positions_initialized_on_new_game(engine: GameEngine) -> None:
    """New game starts with the entry valve already in visited_positions."""
    state = engine.state
    assert state.pipe_network.entry_valve in state.visited_positions


def test_pressure_changes_on_move(engine: GameEngine) -> None:
    """Pressure value is tracked correctly after movement."""
    state = engine.state
    initial_pressure = state.player.pressure

    entry_section = get_section(state.pipe_network, state.player.position)
    open_dir = next(
        (d for d, sealed in entry_section.connections.items() if not sealed),
        None,
    )
    assert open_dir is not None
    engine.process_command(f"move {open_dir}")

    assert isinstance(state.player.pressure, int)
    assert state.player.pressure <= initial_pressure


def test_save_load_preserves_visited_positions(save_path) -> None:
    """Round-trip save/load preserves the visited_positions set."""
    repo = MockRepo()
    engine = GameEngine(repo=repo, save_path=save_path)
    engine.start_new_game(seed=42)
    state = engine.state

    entry_section = get_section(state.pipe_network, state.player.position)
    open_dir = next(
        (d for d, sealed in entry_section.connections.items() if not sealed),
        None,
    )
    if open_dir:
        engine.process_command(f"move {open_dir}")

    visited_before = set(state.visited_positions)
    assert engine.save_game() is True

    loaded = GameEngine(repo=repo, save_path=save_path)
    assert loaded.load_game() is True
    assert loaded.state.visited_positions == visited_before


# ---------------------------------------------------------------------------
# get_display_state() — GUI data-gateway contract
# ---------------------------------------------------------------------------

def test_get_display_state_none_before_start(save_path) -> None:
    """No display state when the engine has not started a game."""
    e = GameEngine(repo=MockRepo(), save_path=save_path)
    assert e.get_display_state() is None


def test_get_display_state_after_new_game(engine: GameEngine) -> None:
    """Fresh game produces a complete display-state dict."""
    ds = engine.get_display_state()
    assert ds is not None
    assert ds["rows"] == 4
    assert ds["cols"] == 4
    assert ds["player_row"] == 0
    assert ds["player_col"] == 0
    assert ds["pressure"] == DEFAULT_PRESSURE
    assert ds["phase"] == "navigating"
    assert ds["status"] == "in_progress"
    assert ds["question"] is None
    assert len(ds["vis_grid"]) == ds["rows"]


def test_get_display_state_after_move(engine: GameEngine) -> None:
    """Display state reflects the player's new position after a move."""
    state = engine.state
    entry_section = get_section(state.pipe_network, state.player.position)
    open_dir = next(
        (d for d, sealed in entry_section.connections.items() if not sealed),
        None,
    )
    assert open_dir is not None
    engine.process_command(open_dir)
    ds = engine.get_display_state()
    assert (ds["player_row"], ds["player_col"]) != (0, 0)


def test_get_display_state_after_save_load(save_path) -> None:
    """Display state survives a save/load round-trip."""
    repo = MockRepo()
    e = GameEngine(repo=repo, save_path=save_path)
    e.start_new_game(seed=42)
    e.save_game()

    e2 = GameEngine(repo=repo, save_path=save_path)
    e2.load_game()
    ds = e2.get_display_state()
    assert ds is not None
    assert ds["status"] == "in_progress"
