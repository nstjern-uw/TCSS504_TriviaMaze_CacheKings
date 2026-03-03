import pytest

from maze import GameStatus, check_solvability, get_fog_view
from db import SqlModelRepository
from main import GameEngine, DEFAULT_ENERGY


@pytest.fixture
def db_path(tmp_path) -> str:
    return str(tmp_path / "game.sqlite")


@pytest.fixture
def repo(db_path) -> SqlModelRepository:
    r = SqlModelRepository()
    r.init_db(db_path)
    r.seed_questions(db_path)
    return r


@pytest.fixture
def engine(repo: SqlModelRepository, db_path: str) -> GameEngine:
    e = GameEngine(repo=repo, db_path=db_path, slot="slot1")
    e.start_new_game(seed=42)
    return e


def test_new_game_initializes_state(engine: GameEngine) -> None:
    state = engine.state
    assert state is not None
    assert state.player.energy == DEFAULT_ENERGY
    assert state.status == GameStatus.IN_PROGRESS
    assert check_solvability(state.maze, state.maze.entrance, state.maze.exit_pos)

    fog = get_fog_view(state, sight_radius=1)
    assert len(fog) == state.maze.rows
    assert len(fog[0]) == state.maze.cols


def test_save_and_load_preserves_state(repo: SqlModelRepository, db_path: str) -> None:
    e1 = GameEngine(repo=repo, db_path=db_path, slot="slot1")
    e1.start_new_game(seed=42)

    s = e1.state
    start_pos = s.player.position
    for cmd in ["move north", "move south", "move east", "move west"]:
        e1.process_command(cmd)
        if s.player.position != start_pos:
            break

    assert e1.save_game() is True

    e2 = GameEngine(repo=repo, db_path=db_path, slot="slot1")
    assert e2.load_game() is True

    a = e1.state
    b = e2.state
    assert b.player.position == a.player.position
    assert b.player.energy == a.player.energy
    assert b.questions_answered == a.questions_answered
    assert b.questions_correct == a.questions_correct


def test_repo_has_question_available(repo: SqlModelRepository, db_path: str) -> None:
    q = repo.get_unused_question(db_path)
    assert q is not None
    assert "prompt" in q and q["prompt"]