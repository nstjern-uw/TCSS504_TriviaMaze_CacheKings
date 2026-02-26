"""Contract tests for maze.py — Domain Owner acceptance suite.

Run with:  pytest tests/test_maze_contract.py -v
All tests must pass before maze.py is considered done (P0 requirement).
"""

import pytest

from maze import (
    Direction,
    GameStatus,
    Maze,
    MoveResult,
    Player,
    Position,
    Question,
    Room,
    attempt_answer,
    check_solvability,
    create_maze,
    get_question,
    get_room,
    has_clog,
    is_solved,
    move_player,
    phase_beam,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_maze() -> Maze:
    """A deterministic 3x3 maze built with seed=42."""
    return create_maze(3, 3, seed=42)


@pytest.fixture
def clog_room_position(seeded_maze: Maze) -> Position:
    """Return the position of the first room that has a clog."""
    for row in seeded_maze.grid:
        for room in row:
            if room.has_clog:
                return room.position
    pytest.skip("No clog room found in seeded maze — seed may need updating.")


@pytest.fixture
def sample_question() -> Question:
    """A known question for deterministic answer tests."""
    return Question(
        prompt="What is 2 + 2?",
        choices=["3", "4", "5", "6"],
        correct_answer="4",
    )


@pytest.fixture
def player_at_entrance() -> Player:
    """A fresh player sitting at the maze entrance."""
    return Player(
        position=Position(0, 0),
        energy=100,
        clogs_cleared=0,
        current_level=1,
    )


# ---------------------------------------------------------------------------
# create_maze
# ---------------------------------------------------------------------------

def test_create_maze_returns_maze(seeded_maze: Maze) -> None:
    assert seeded_maze.rows == 3
    assert seeded_maze.cols == 3
    assert isinstance(seeded_maze, Maze)


def test_create_maze_has_entrance_and_exit(seeded_maze: Maze) -> None:
    all_rooms = [room for row in seeded_maze.grid for room in row]
    assert sum(1 for r in all_rooms if r.is_entrance) == 1
    assert sum(1 for r in all_rooms if r.is_exit) == 1


def test_create_maze_is_solvable(seeded_maze: Maze) -> None:
    assert check_solvability(seeded_maze, seeded_maze.entrance, seeded_maze.exit_pos)


def test_create_maze_has_clogs(seeded_maze: Maze) -> None:
    all_rooms = [room for row in seeded_maze.grid for room in row]
    assert any(r.has_clog for r in all_rooms)


def test_create_maze_deterministic_with_seed() -> None:
    maze_a = create_maze(3, 3, seed=42)
    maze_b = create_maze(3, 3, seed=42)
    # Compare grid clog/wall state room by room
    for r in range(3):
        for c in range(3):
            room_a = maze_a.grid[r][c]
            room_b = maze_b.grid[r][c]
            assert room_a.walls == room_b.walls
            assert room_a.has_clog == room_b.has_clog
    # Also ensure entrance/exit and dimensions are identical
    assert maze_a.rows == maze_b.rows == 3
    assert maze_a.cols == maze_b.cols == 3
    assert maze_a.entrance == maze_b.entrance
    assert maze_a.exit_pos == maze_b.exit_pos


def test_create_maze_path_has_clog(seeded_maze: Maze) -> None:
    """Ensure at least one clogged room lies on some valid path from entrance to exit."""
    start = seeded_maze.entrance
    end = seeded_maze.exit_pos
    visited = set()
    parent: dict[tuple[int, int], tuple[int, int] | None] = {}
    stack = [start]
    parent[(start.row, start.col)] = None

    while stack:
        pos = stack.pop()
        if (pos.row, pos.col) in visited:
            continue
        visited.add((pos.row, pos.col))
        if pos == end:
            break
        room = get_room(seeded_maze, pos)
        for d, wall in room.walls.items():
            if wall:
                continue
            dr, dc = (-1, 0) if d == "north" else (1, 0) if d == "south" else (0, 1) if d == "east" else (0, -1)
            neighbour = Position(pos.row + dr, pos.col + dc)
            if (neighbour.row, neighbour.col) not in visited and 0 <= neighbour.row < seeded_maze.rows and 0 <= neighbour.col < seeded_maze.cols:
                parent[(neighbour.row, neighbour.col)] = (pos.row, pos.col)
                stack.append(neighbour)

    # Reconstruct path if end reached
    path = []
    cur = (end.row, end.col)
    if cur not in parent:
        pytest.skip("No path found in what should be a solvable maze.")
    while cur is not None:
        path.append(Position(cur[0], cur[1]))
        cur = parent.get(cur)

    # Verify at least one room on path has a clog
    assert any(get_room(seeded_maze, p).has_clog for p in path)


def test_create_maze_invalid_size() -> None:
    with pytest.raises(ValueError):
        create_maze(1, 1)


def test_create_maze_wall_symmetry(seeded_maze: Maze) -> None:
    """If room A's south wall is open, room B's north wall must also be open."""
    opposite = {
        "north": "south",
        "south": "north",
        "east": "west",
        "west": "east",
    }
    delta = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}

    for r in range(seeded_maze.rows):
        for c in range(seeded_maze.cols):
            room = seeded_maze.grid[r][c]
            for direction, wall_up in room.walls.items():
                if not wall_up:
                    dr, dc = delta[direction]
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < seeded_maze.rows and 0 <= nc < seeded_maze.cols:
                        neighbour = seeded_maze.grid[nr][nc]
                        assert not neighbour.walls[opposite[direction]], (
                            f"Wall asymmetry at ({r},{c}) direction={direction}"
                        )


# ---------------------------------------------------------------------------
# move_player
# ---------------------------------------------------------------------------

def test_move_valid_direction(seeded_maze: Maze, player_at_entrance: Player) -> None:
    """Find an open direction from (0,0) and verify move succeeds."""
    entrance_room = get_room(seeded_maze, Position(0, 0))
    open_direction = next(
        (Direction(d) for d, wall in entrance_room.walls.items() if not wall), None
    )
    assert open_direction is not None, "Entrance room has no open walls — check maze generation."
    result = move_player(seeded_maze, player_at_entrance, open_direction)
    assert result.success is True
    assert result.new_position is not None


def test_move_returns_expected_position(seeded_maze: Maze, player_at_entrance: Player) -> None:
    """Move in the first open direction and assert the returned Position is correct."""
    entrance_room = get_room(seeded_maze, Position(0, 0))
    open_direction = next((Direction(d) for d, wall in entrance_room.walls.items() if not wall), None)
    assert open_direction is not None
    result = move_player(seeded_maze, player_at_entrance, open_direction)
    assert result.success is True
    assert result.new_position is not None
    delta = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}
    dr, dc = delta[open_direction.value]
    expected = Position(player_at_entrance.position.row + dr, player_at_entrance.position.col + dc)
    assert result.new_position == expected


def test_move_into_wall(seeded_maze: Maze, player_at_entrance: Player) -> None:
    """Find a walled direction from (0,0) and verify move is blocked."""
    entrance_room = get_room(seeded_maze, Position(0, 0))
    walled_direction = next(
        (Direction(d) for d, wall in entrance_room.walls.items() if wall), None
    )
    assert walled_direction is not None, "Entrance room has no walls — check maze generation."
    result = move_player(seeded_maze, player_at_entrance, walled_direction)
    assert result.success is False
    assert result.new_position is None


def test_move_out_of_bounds(seeded_maze: Maze, player_at_entrance: Player) -> None:
    """Moving north from row 0 is always out of bounds."""
    # Ensure north wall is up (it always is at row 0 by construction)
    result = move_player(seeded_maze, player_at_entrance, Direction.NORTH)
    assert result.success is False
    assert result.new_position is None


def test_move_does_not_mutate_player(seeded_maze: Maze, player_at_entrance: Player) -> None:
    original_position = player_at_entrance.position
    move_player(seeded_maze, player_at_entrance, Direction.SOUTH)
    assert player_at_entrance.position == original_position


# ---------------------------------------------------------------------------
# get_room / has_clog
# ---------------------------------------------------------------------------

def test_get_room_valid(seeded_maze: Maze) -> None:
    room = get_room(seeded_maze, Position(0, 0))
    assert isinstance(room, Room)
    assert room.position == Position(0, 0)


def test_get_room_invalid(seeded_maze: Maze) -> None:
    with pytest.raises(ValueError):
        get_room(seeded_maze, Position(99, 99))


def test_has_clog_true(seeded_maze: Maze, clog_room_position: Position) -> None:
    assert has_clog(seeded_maze, clog_room_position) is True


def test_has_clog_false(seeded_maze: Maze) -> None:
    # Entrance room never has a clog by construction
    assert has_clog(seeded_maze, seeded_maze.entrance) is False


# ---------------------------------------------------------------------------
# attempt_answer
# ---------------------------------------------------------------------------

def test_correct_answer_clears_clog(
    seeded_maze: Maze,
    clog_room_position: Position,
    sample_question: Question,
) -> None:
    result = attempt_answer(
        seeded_maze, clog_room_position, sample_question.correct_answer, sample_question
    )
    assert result.correct is True
    assert result.clog_cleared is True
    assert result.energy_change == 10


def test_correct_answer_updates_room(
    seeded_maze: Maze,
    clog_room_position: Position,
    sample_question: Question,
) -> None:
    attempt_answer(
        seeded_maze, clog_room_position, sample_question.correct_answer, sample_question
    )
    assert has_clog(seeded_maze, clog_room_position) is False


def test_wrong_answer_keeps_clog(
    seeded_maze: Maze,
    clog_room_position: Position,
    sample_question: Question,
) -> None:
    result = attempt_answer(
        seeded_maze, clog_room_position, "wrong_answer", sample_question
    )
    assert result.correct is False
    assert result.clog_cleared is False
    assert result.energy_change == -5
    assert has_clog(seeded_maze, clog_room_position) is True


def test_answer_no_clog_room(seeded_maze: Maze, sample_question: Question) -> None:
    # Entrance room never has a clog
    result = attempt_answer(
        seeded_maze, seeded_maze.entrance, sample_question.correct_answer, sample_question
    )
    assert result.correct is False
    assert result.clog_cleared is False
    assert result.energy_change == 0


# ---------------------------------------------------------------------------
# is_solved / check_solvability
# ---------------------------------------------------------------------------

def test_is_solved_false_with_clogs(seeded_maze: Maze) -> None:
    # Fresh maze has at least one clog (guaranteed by create_maze)
    assert is_solved(seeded_maze) is False


def test_is_solved_true_all_cleared(seeded_maze: Maze) -> None:
    for row in seeded_maze.grid:
        for room in row:
            room.has_clog = False
    assert is_solved(seeded_maze) is True


def test_solvability_true(seeded_maze: Maze) -> None:
    assert check_solvability(seeded_maze, seeded_maze.entrance, seeded_maze.exit_pos) is True


def test_solvability_false() -> None:
    """Manually construct a 2x2 maze with all walls up — unsolvable."""
    def _walled_room(r: int, c: int) -> Room:
        return Room(
            position=Position(r, c),
            walls={"north": True, "south": True, "east": True, "west": True},
            has_clog=False,
            is_entrance=(r == 0 and c == 0),
            is_exit=(r == 1 and c == 1),
        )

    grid = [[_walled_room(r, c) for c in range(2)] for r in range(2)]
    maze = Maze(rows=2, cols=2, grid=grid, entrance=Position(0, 0), exit_pos=Position(1, 1))
    assert check_solvability(maze, maze.entrance, maze.exit_pos) is False


# ---------------------------------------------------------------------------
# get_question
# ---------------------------------------------------------------------------

def test_question_has_required_fields() -> None:
    q = get_question()
    assert len(q.prompt) > 0
    assert len(q.choices) >= 2
    assert q.correct_answer in q.choices


def test_question_deterministic_with_seed() -> None:
    q1 = get_question(seed=42)
    q2 = get_question(seed=42)
    assert q1 == q2


# ---------------------------------------------------------------------------
# phase_beam
# ---------------------------------------------------------------------------

def test_phase_beam_sufficient_energy(
    seeded_maze: Maze, clog_room_position: Position
) -> None:
    result = phase_beam(seeded_maze, clog_room_position, player_energy=100)
    assert result.clog_cleared is True
    assert result.energy_change == -50
    assert has_clog(seeded_maze, clog_room_position) is False


def test_phase_beam_insufficient_energy(
    seeded_maze: Maze, clog_room_position: Position
) -> None:
    result = phase_beam(seeded_maze, clog_room_position, player_energy=30)
    assert result.clog_cleared is False
    assert result.energy_change == 0
    assert has_clog(seeded_maze, clog_room_position) is True
