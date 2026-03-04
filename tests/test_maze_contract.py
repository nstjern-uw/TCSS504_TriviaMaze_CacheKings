"""Contract tests for maze.py — Domain Owner acceptance suite.

Run with:  pytest tests/test_maze_contract.py -v
All tests must pass before maze.py is considered done (P0 requirement).

Covers: PipeNetwork creation, movement, section queries, clog mechanics,
        answer attempts, solvability, hydro_blast, and fog-of-war visibility.
"""

import pytest

from maze import (
    Direction, GameStatus, PipeNetwork, MoveResult, Player, Position, Question, PipeSection, SectionVisibility,
    attempt_answer, check_solvability, create_pipe_network, get_section, has_clog, is_network_clear, move_player, hydro_blast, get_visibility_map, update_visited,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_network() -> PipeNetwork:
    """A deterministic 3x3 pipe network built with seed=42."""
    return create_pipe_network(3, 3, seed=42)


@pytest.fixture
def clog_section_position(seeded_network: PipeNetwork) -> Position:
    """Return the position of the first section that has a clog."""
    for row in seeded_network.grid:
        for section in row:
            if section.has_clog:
                return section.position
    pytest.skip("No clog section found in seeded network — seed may need updating.")


@pytest.fixture
def sample_question() -> Question:
    """A known question for deterministic answer tests."""
    return Question(
        prompt="What is 2 + 2?",
        choices=["3", "4", "5", "6"],
        correct_answer="4",
    )


@pytest.fixture
def player_at_entry() -> Player:
    """A fresh player sitting at the network entry valve."""
    return Player(
        position=Position(0, 0),
        pressure=100,
        clogs_cleared=0,
        current_level=1,
    )


# ---------------------------------------------------------------------------
# create_pipe_network
# ---------------------------------------------------------------------------

def test_create_pipe_network_returns_network(seeded_network: PipeNetwork) -> None:
    assert seeded_network.rows == 3
    assert seeded_network.cols == 3
    assert isinstance(seeded_network, PipeNetwork)


def test_create_pipe_network_has_entry_and_exit(seeded_network: PipeNetwork) -> None:
    all_sections = [s for row in seeded_network.grid for s in row]
    assert sum(1 for s in all_sections if s.is_entry_valve) == 1
    assert sum(1 for s in all_sections if s.is_exit_drain) == 1


def test_create_pipe_network_is_solvable(seeded_network: PipeNetwork) -> None:
    assert check_solvability(seeded_network, seeded_network.entry_valve, seeded_network.exit_drain)


def test_create_pipe_network_has_clogs(seeded_network: PipeNetwork) -> None:
    all_sections = [s for row in seeded_network.grid for s in row]
    assert any(s.has_clog for s in all_sections)


def test_create_pipe_network_deterministic_with_seed() -> None:
    net_a = create_pipe_network(3, 3, seed=42)
    net_b = create_pipe_network(3, 3, seed=42)
    for r in range(3):
        for c in range(3):
            sec_a = net_a.grid[r][c]
            sec_b = net_b.grid[r][c]
            assert sec_a.connections == sec_b.connections
            assert sec_a.has_clog == sec_b.has_clog
    assert net_a.rows == net_b.rows == 3
    assert net_a.cols == net_b.cols == 3
    assert net_a.entry_valve == net_b.entry_valve
    assert net_a.exit_drain == net_b.exit_drain


def test_create_pipe_network_path_has_clog(seeded_network: PipeNetwork) -> None:
    """Ensure at least one clogged section lies on some valid path from entry to exit."""
    start = seeded_network.entry_valve
    end = seeded_network.exit_drain
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
        section = get_section(seeded_network, pos)
        for d, conn in section.connections.items():
            if conn:
                continue
            dr, dc = (-1, 0) if d == "north" else (1, 0) if d == "south" else (0, 1) if d == "east" else (0, -1)
            neighbour = Position(pos.row + dr, pos.col + dc)
            if (neighbour.row, neighbour.col) not in visited and 0 <= neighbour.row < seeded_network.rows and 0 <= neighbour.col < seeded_network.cols:
                parent[(neighbour.row, neighbour.col)] = (pos.row, pos.col)
                stack.append(neighbour)

    path = []
    cur = (end.row, end.col)
    if cur not in parent:
        pytest.skip("No path found in what should be a solvable network.")
    while cur is not None:
        path.append(Position(cur[0], cur[1]))
        cur = parent.get(cur)

    assert any(get_section(seeded_network, p).has_clog for p in path)


def test_create_pipe_network_invalid_size() -> None:
    with pytest.raises(ValueError):
        create_pipe_network(1, 1)


def test_create_pipe_network_connection_symmetry(seeded_network: PipeNetwork) -> None:
    """If section A's south connection is open, section B's north connection must also be open."""
    opposite = {
        "north": "south",
        "south": "north",
        "east": "west",
        "west": "east",
    }
    delta = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}

    for r in range(seeded_network.rows):
        for c in range(seeded_network.cols):
            section = seeded_network.grid[r][c]
            for direction, conn_blocked in section.connections.items():
                if not conn_blocked:
                    dr, dc = delta[direction]
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < seeded_network.rows and 0 <= nc < seeded_network.cols:
                        neighbour = seeded_network.grid[nr][nc]
                        assert not neighbour.connections[opposite[direction]], (
                            f"Connection asymmetry at ({r},{c}) direction={direction}"
                        )


def test_create_network_5x5() -> None:
    """A 5x5 network is valid and solvable."""
    net = create_pipe_network(5, 5, seed=99)
    assert net.rows == 5
    assert net.cols == 5
    assert isinstance(net, PipeNetwork)
    assert check_solvability(net, net.entry_valve, net.exit_drain)


def test_create_network_larger_has_clogs() -> None:
    """A 5x5 network has multiple clogged sections."""
    net = create_pipe_network(5, 5, seed=99)
    all_sections = [s for row in net.grid for s in row]
    clog_count = sum(1 for s in all_sections if s.has_clog)
    assert clog_count > 1


# ---------------------------------------------------------------------------
# move_player
# ---------------------------------------------------------------------------

def test_move_valid_direction(seeded_network: PipeNetwork, player_at_entry: Player) -> None:
    """Find an open direction from (0,0) and verify move succeeds."""
    entry_section = get_section(seeded_network, Position(0, 0))
    open_direction = next(
        (Direction(d) for d, conn in entry_section.connections.items() if not conn), None
    )
    assert open_direction is not None, "Entry section has no open connections — check network generation."
    result = move_player(seeded_network, player_at_entry, open_direction)
    assert result.success is True
    assert result.new_position is not None


def test_move_returns_expected_position(seeded_network: PipeNetwork, player_at_entry: Player) -> None:
    """Move in the first open direction and assert the returned Position is correct."""
    entry_section = get_section(seeded_network, Position(0, 0))
    open_direction = next((Direction(d) for d, conn in entry_section.connections.items() if not conn), None)
    assert open_direction is not None
    result = move_player(seeded_network, player_at_entry, open_direction)
    assert result.success is True
    assert result.new_position is not None
    delta = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}
    dr, dc = delta[open_direction.value]
    expected = Position(player_at_entry.position.row + dr, player_at_entry.position.col + dc)
    assert result.new_position == expected


def test_move_into_wall(seeded_network: PipeNetwork, player_at_entry: Player) -> None:
    """Find a blocked direction from (0,0) and verify move is blocked."""
    entry_section = get_section(seeded_network, Position(0, 0))
    blocked_direction = next(
        (Direction(d) for d, conn in entry_section.connections.items() if conn), None
    )
    assert blocked_direction is not None, "Entry section has no blocked connections — check network generation."
    result = move_player(seeded_network, player_at_entry, blocked_direction)
    assert result.success is False
    assert result.new_position is None


def test_move_out_of_bounds(seeded_network: PipeNetwork, player_at_entry: Player) -> None:
    """Moving north from row 0 is always out of bounds."""
    result = move_player(seeded_network, player_at_entry, Direction.NORTH)
    assert result.success is False
    assert result.new_position is None


def test_move_does_not_mutate_player(seeded_network: PipeNetwork, player_at_entry: Player) -> None:
    original_position = player_at_entry.position
    move_player(seeded_network, player_at_entry, Direction.SOUTH)
    assert player_at_entry.position == original_position


# ---------------------------------------------------------------------------
# get_section / has_clog
# ---------------------------------------------------------------------------

def test_get_section_valid(seeded_network: PipeNetwork) -> None:
    section = get_section(seeded_network, Position(0, 0))
    assert isinstance(section, PipeSection)
    assert section.position == Position(0, 0)


def test_get_section_invalid(seeded_network: PipeNetwork) -> None:
    with pytest.raises(ValueError):
        get_section(seeded_network, Position(99, 99))


def test_has_clog_true(seeded_network: PipeNetwork, clog_section_position: Position) -> None:
    assert has_clog(seeded_network, clog_section_position) is True


def test_has_clog_false(seeded_network: PipeNetwork) -> None:
    assert has_clog(seeded_network, seeded_network.entry_valve) is False


# ---------------------------------------------------------------------------
# attempt_answer
# ---------------------------------------------------------------------------

def test_correct_answer_clears_clog(
    seeded_network: PipeNetwork,
    clog_section_position: Position,
    sample_question: Question,
) -> None:
    result = attempt_answer(
        seeded_network, clog_section_position, sample_question.correct_answer, sample_question
    )
    assert result.correct is True
    assert result.clog_cleared is True
    assert result.pressure_change == 10


def test_correct_answer_updates_section(
    seeded_network: PipeNetwork,
    clog_section_position: Position,
    sample_question: Question,
) -> None:
    attempt_answer(
        seeded_network, clog_section_position, sample_question.correct_answer, sample_question
    )
    assert has_clog(seeded_network, clog_section_position) is False


def test_wrong_answer_keeps_clog(
    seeded_network: PipeNetwork,
    clog_section_position: Position,
    sample_question: Question,
) -> None:
    result = attempt_answer(
        seeded_network, clog_section_position, "wrong_answer", sample_question
    )
    assert result.correct is False
    assert result.clog_cleared is False
    assert result.pressure_change == -5
    assert has_clog(seeded_network, clog_section_position) is True


def test_answer_no_clog_section(seeded_network: PipeNetwork, sample_question: Question) -> None:
    result = attempt_answer(
        seeded_network, seeded_network.entry_valve, sample_question.correct_answer, sample_question
    )
    assert result.correct is False
    assert result.clog_cleared is False
    assert result.pressure_change == 0


# ---------------------------------------------------------------------------
# is_network_clear / check_solvability
# ---------------------------------------------------------------------------

def test_is_network_clear_false_with_clogs(seeded_network: PipeNetwork) -> None:
    assert is_network_clear(seeded_network) is False


def test_is_network_clear_true_all_cleared(seeded_network: PipeNetwork) -> None:
    for row in seeded_network.grid:
        for section in row:
            section.has_clog = False
    assert is_network_clear(seeded_network) is True


def test_solvability_true(seeded_network: PipeNetwork) -> None:
    assert check_solvability(seeded_network, seeded_network.entry_valve, seeded_network.exit_drain) is True


def test_solvability_false() -> None:
    """Manually construct a 2x2 network with all connections blocked — unsolvable."""
    def _blocked_section(r: int, c: int) -> PipeSection:
        return PipeSection(
            position=Position(r, c),
            connections={"north": True, "south": True, "east": True, "west": True},
            has_clog=False,
            is_entry_valve=(r == 0 and c == 0),
            is_exit_drain=(r == 1 and c == 1),
        )

    grid = [[_blocked_section(r, c) for c in range(2)] for r in range(2)]
    net = PipeNetwork(rows=2, cols=2, grid=grid, entry_valve=Position(0, 0), exit_drain=Position(1, 1))
    assert check_solvability(net, net.entry_valve, net.exit_drain) is False


# ---------------------------------------------------------------------------
# hydro_blast
# ---------------------------------------------------------------------------

def test_hydro_blast_sufficient_pressure(
    seeded_network: PipeNetwork, clog_section_position: Position
) -> None:
    result = hydro_blast(seeded_network, clog_section_position, player_pressure=100)
    assert result.clog_cleared is True
    assert result.pressure_change == -50
    assert has_clog(seeded_network, clog_section_position) is False


def test_hydro_blast_insufficient_pressure(
    seeded_network: PipeNetwork, clog_section_position: Position
) -> None:
    result = hydro_blast(seeded_network, clog_section_position, player_pressure=30)
    assert result.clog_cleared is False
    assert result.pressure_change == 0
    assert has_clog(seeded_network, clog_section_position) is True


# ---------------------------------------------------------------------------
# Fog of War — get_visibility_map / update_visited
# ---------------------------------------------------------------------------

def test_get_visibility_map_start_position(seeded_network: PipeNetwork) -> None:
    """At game start, entry valve is_current=True, is_visited=True, is_visible=True."""
    entry = seeded_network.entry_valve
    visited = frozenset({(entry.row, entry.col)})
    vis_map = get_visibility_map(seeded_network, entry, visited)
    entry_vis = vis_map[entry.row][entry.col]
    assert entry_vis.is_current is True
    assert entry_vis.is_visited is True
    assert entry_vis.is_visible is True


def test_get_visibility_map_after_move(seeded_network: PipeNetwork) -> None:
    """After moving, both the old and new positions show as visited."""
    entry = seeded_network.entry_valve
    entry_section = get_section(seeded_network, entry)
    open_dir = next(
        (Direction(d) for d, conn in entry_section.connections.items() if not conn), None
    )
    assert open_dir is not None, "Entry section has no open connections."
    delta = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}
    dr, dc = delta[open_dir.value]
    new_pos = Position(entry.row + dr, entry.col + dc)
    visited = frozenset({(entry.row, entry.col), (new_pos.row, new_pos.col)})
    vis_map = get_visibility_map(seeded_network, new_pos, visited)
    assert vis_map[entry.row][entry.col].is_visited is True
    assert vis_map[new_pos.row][new_pos.col].is_visited is True
    assert vis_map[new_pos.row][new_pos.col].is_current is True


def test_get_visibility_map_fog_hides_details(seeded_network: PipeNetwork) -> None:
    """Sections in fog have None for has_clog and open_directions."""
    entry = seeded_network.entry_valve
    visited = frozenset({(entry.row, entry.col)})
    vis_map = get_visibility_map(seeded_network, entry, visited)
    for r in range(seeded_network.rows):
        for c in range(seeded_network.cols):
            sv = vis_map[r][c]
            if not sv.is_visible:
                assert sv.has_clog is None
                assert sv.open_directions is None


def test_get_visibility_map_returns_full_grid(seeded_network: PipeNetwork) -> None:
    """Output dimensions match the network dimensions."""
    entry = seeded_network.entry_valve
    visited = frozenset({(entry.row, entry.col)})
    vis_map = get_visibility_map(seeded_network, entry, visited)
    assert len(vis_map) == seeded_network.rows
    for row in vis_map:
        assert len(row) == seeded_network.cols


def test_get_visibility_map_pure_function(seeded_network: PipeNetwork) -> None:
    """get_visibility_map doesn't mutate the network or the visited set."""
    entry = seeded_network.entry_valve
    visited = frozenset({(entry.row, entry.col)})
    grid_snapshot = [
        [(s.has_clog, s.connections.copy()) for s in row]
        for row in seeded_network.grid
    ]
    get_visibility_map(seeded_network, entry, visited)
    for r in range(seeded_network.rows):
        for c in range(seeded_network.cols):
            s = seeded_network.grid[r][c]
            assert s.has_clog == grid_snapshot[r][c][0]
            assert s.connections == grid_snapshot[r][c][1]


def test_update_visited_returns_new_set() -> None:
    """update_visited returns a new set and doesn't mutate the input."""
    original = frozenset({(0, 0)})
    result = update_visited(original, Position(1, 1))
    assert result is not original
    assert (0, 0) in original
    assert len(original) == 1


def test_update_visited_contains_new_position() -> None:
    """The returned set includes the newly visited position."""
    original = frozenset({(0, 0)})
    result = update_visited(original, Position(1, 1))
    assert (1, 1) in result
    assert (0, 0) in result
