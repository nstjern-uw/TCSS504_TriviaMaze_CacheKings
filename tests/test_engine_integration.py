"""Engine integration tests — verifies main.py correctly wires maze.py and db.py.

These tests require both maze.py and db.py to be present.
They verify that main.py correctly orchestrates the modules together.

Run with:  pytest tests/test_engine_integration.py -v
"""

import pytest

from maze import (
    Direction,
    GameStatus,
    Position,
    check_solvability,
    get_room,
    is_solved,
)
from db import JsonFileRepository
from main import (
    DEFAULT_ENERGY,
    GameEngine,
    gamestate_from_dict,
    gamestate_to_dict,
)


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
    e = GameEngine(repo=JsonFileRepository(), save_path=save_path)
    e.start_new_game(seed=42)
    return e


# ---------------------------------------------------------------------------
# Game lifecycle
# ---------------------------------------------------------------------------

def test_new_game_initializes_state(engine: GameEngine) -> None:
    state = engine.state
    assert state is not None
    assert state.player.position == state.maze.entrance
    assert state.player.energy == DEFAULT_ENERGY
    assert state.status == GameStatus.IN_PROGRESS
    assert check_solvability(state.maze, state.maze.entrance, state.maze.exit_pos)


def test_process_move_command(engine: GameEngine) -> None:
    """Find an open direction from the entrance and verify the move succeeds."""
    state = engine.state
    entrance_room = get_room(state.maze, state.player.position)
    open_dir = next(
        (d for d, wall in entrance_room.walls.items() if not wall), None
    )
    assert open_dir is not None, "No open direction from entrance"

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
    engine = GameEngine(repo=JsonFileRepository(), save_path=save_path)
    engine.start_new_game(seed=42)
    state = engine.state

    entrance_room = get_room(state.maze, state.player.position)
    open_dir = next(
        (d for d, wall in entrance_room.walls.items() if not wall), None
    )
    if open_dir:
        engine.process_command(f"move {open_dir}")

    assert engine.save_game() is True

    loaded = GameEngine(repo=JsonFileRepository(), save_path=save_path)
    assert loaded.load_game() is True

    original = engine.state
    restored = loaded.state

    assert restored.player.position == original.player.position
    assert restored.player.energy == original.player.energy
    assert restored.player.clogs_cleared == original.player.clogs_cleared
    assert restored.player.current_level == original.player.current_level
    assert restored.maze.rows == original.maze.rows
    assert restored.maze.cols == original.maze.cols
    assert restored.maze.entrance == original.maze.entrance
    assert restored.maze.exit_pos == original.maze.exit_pos
    assert restored.status == original.status
    assert restored.questions_answered == original.questions_answered
    assert restored.questions_correct == original.questions_correct

    for r in range(original.maze.rows):
        for c in range(original.maze.cols):
            assert (
                original.maze.grid[r][c].has_clog
                == restored.maze.grid[r][c].has_clog
            )
            assert (
                original.maze.grid[r][c].walls
                == restored.maze.grid[r][c].walls
            )


def test_load_with_no_save(save_path) -> None:
    engine = GameEngine(repo=JsonFileRepository(), save_path=save_path)
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
    assert restored.player.energy == original.player.energy
    assert restored.player.clogs_cleared == original.player.clogs_cleared
    assert restored.player.current_level == original.player.current_level
    assert restored.maze.rows == original.maze.rows
    assert restored.maze.cols == original.maze.cols
    assert restored.maze.entrance == original.maze.entrance
    assert restored.maze.exit_pos == original.maze.exit_pos
    assert restored.status == original.status
    assert restored.questions_answered == original.questions_answered
    assert restored.questions_correct == original.questions_correct

    for r in range(original.maze.rows):
        for c in range(original.maze.cols):
            orig_room = original.maze.grid[r][c]
            rest_room = restored.maze.grid[r][c]
            assert rest_room.position == orig_room.position
            assert rest_room.walls == orig_room.walls
            assert rest_room.has_clog == orig_room.has_clog
            assert rest_room.is_entrance == orig_room.is_entrance
            assert rest_room.is_exit == orig_room.is_exit


def test_enum_serialization_round_trip() -> None:
    assert GameStatus(GameStatus.IN_PROGRESS.value) == GameStatus.IN_PROGRESS
    assert GameStatus(GameStatus.WON.value) == GameStatus.WON
    assert GameStatus(GameStatus.QUIT.value) == GameStatus.QUIT


# ---------------------------------------------------------------------------
# Win condition
# ---------------------------------------------------------------------------

def test_win_condition(engine: GameEngine) -> None:
    state = engine.state

    for row in state.maze.grid:
        for room in row:
            room.has_clog = False

    assert is_solved(state.maze) is True

    entrance_room = get_room(state.maze, state.player.position)
    open_dir = next(
        (d for d, wall in entrance_room.walls.items() if not wall), None
    )
    assert open_dir is not None
    result = engine.process_command(f"move {open_dir}")

    assert result == GameStatus.WON
    assert state.status == GameStatus.WON
