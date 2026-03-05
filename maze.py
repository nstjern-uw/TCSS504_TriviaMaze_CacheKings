"""Domain logic for the Trivia Maze refactor (Phase 3).

Rules:
- Do NOT import db.py or main.py
- Do NOT use print() or input()
- Pure data in/out only
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Direction(str, Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


class GameStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    CLEARED = "cleared"
    QUIT = "quit"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Position:
    row: int
    col: int


@dataclass
class Question:
    prompt: str
    choices: list[str]
    correct_answer: str


@dataclass
class PipeSection:
    position: Position
    connections: dict[str, bool]  # True = sealed, False = open pipe
    has_clog: bool
    is_entry_valve: bool
    is_exit_drain: bool


@dataclass
class Player:
    position: Position
    pressure: int
    clogs_cleared: int
    current_level: int


@dataclass
class PipeNetwork:
    rows: int
    cols: int
    grid: list[list[PipeSection]]
    entry_valve: Position
    exit_drain: Position


@dataclass
class GameState:
    player: Player
    pipe_network: PipeNetwork
    status: GameStatus
    questions_answered: int
    questions_correct: int
    visited_positions: set[Position]


@dataclass
class MoveResult:
    success: bool
    message: str
    new_position: Position | None


@dataclass
class AnswerResult:
    correct: bool
    clog_cleared: bool
    pressure_change: int
    message: str


@dataclass
class SectionVisibility:
    position: Position
    is_current: bool
    is_visited: bool
    is_visible: bool
    has_clog: bool | None
    open_directions: list[str] | None


# ---------------------------------------------------------------------------
# Direction helpers
# ---------------------------------------------------------------------------

_DELTA: dict[Direction, tuple[int, int]] = {
    Direction.NORTH: (-1, 0),
    Direction.SOUTH: (1, 0),
    Direction.EAST: (0, 1),
    Direction.WEST: (0, -1),
}

_OPPOSITE: dict[Direction, Direction] = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST,
}


def _sealed_connections() -> dict[str, bool]:
    return {d.value: True for d in Direction}


def _neighbors_in_bounds(rows: int, cols: int, pos: Position) -> list[Position]:
    out: list[Position] = []
    for d in Direction:
        dr, dc = _DELTA[d]
        nr, nc = pos.row + dr, pos.col + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            out.append(Position(nr, nc))
    return out


# ---------------------------------------------------------------------------
# Network generation / solvability
# ---------------------------------------------------------------------------

def _carve_passages(grid: list[list[PipeSection]], rows: int, cols: int, rng: random.Random) -> None:
    visited: set[tuple[int, int]] = set()

    def dfs(r: int, c: int) -> None:
        visited.add((r, c))
        dirs = list(Direction)
        rng.shuffle(dirs)
        for d in dirs:
            dr, dc = _DELTA[d]
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in visited:
                # open connection both ways
                grid[r][c].connections[d.value] = False
                grid[nr][nc].connections[_OPPOSITE[d].value] = False
                dfs(nr, nc)

    dfs(0, 0)


def check_solvability(network: PipeNetwork, start: Position, end: Position) -> bool:
    visited: set[Position] = set()

    def dfs(pos: Position) -> bool:
        if pos == end:
            return True
        visited.add(pos)
        section = network.grid[pos.row][pos.col]
        for d in Direction:
            if section.connections[d.value]:
                continue  # sealed
            dr, dc = _DELTA[d]
            nxt = Position(pos.row + dr, pos.col + dc)
            if nxt not in visited and 0 <= nxt.row < network.rows and 0 <= nxt.col < network.cols:
                if dfs(nxt):
                    return True
        return False

    return dfs(start)


def create_pipe_network(rows: int = 5, cols: int = 5, seed: int | None = None) -> PipeNetwork:
    if rows < 2 or cols < 2:
        raise ValueError("rows and cols must be >= 2")

    rng = random.Random(seed)
    entry = Position(0, 0)
    exit_ = Position(rows - 1, cols - 1)

    clog_chance = 0.40 if (rows * cols) >= 16 else 0.50
    min_clogs = 2 if (rows * cols) >= 16 else 1

    while True:
        grid: list[list[PipeSection]] = []
        for r in range(rows):
            row_list: list[PipeSection] = []
            for c in range(cols):
                pos = Position(r, c)
                is_entry = pos == entry
                is_exit = pos == exit_
                has_clog = (not is_entry and not is_exit and rng.random() < clog_chance)
                row_list.append(
                    PipeSection(
                        position=pos,
                        connections=_sealed_connections(),
                        has_clog=has_clog,
                        is_entry_valve=is_entry,
                        is_exit_drain=is_exit,
                    )
                )
            grid.append(row_list)

        # ensure at least min_clogs exist
        clogs = [s for row in grid for s in row if s.has_clog]
        if len(clogs) < min_clogs:
            candidates = [s for row in grid for s in row if (not s.is_entry_valve and not s.is_exit_drain)]
            rng.shuffle(candidates)
            for s in candidates[: (min_clogs - len(clogs))]:
                s.has_clog = True

        _carve_passages(grid, rows, cols, rng)

        network = PipeNetwork(rows=rows, cols=cols, grid=grid, entry_valve=entry, exit_drain=exit_)
        if check_solvability(network, entry, exit_):
            return network


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_section(network: PipeNetwork, position: Position) -> PipeSection:
    if not (0 <= position.row < network.rows and 0 <= position.col < network.cols):
        raise ValueError(f"Position out of bounds: ({position.row}, {position.col})")
    return network.grid[position.row][position.col]


def has_clog(network: PipeNetwork, position: Position) -> bool:
    return get_section(network, position).has_clog


# ---------------------------------------------------------------------------
# Movement (does not mutate player)
# ---------------------------------------------------------------------------

def move_player(network: PipeNetwork, player: Player, direction: Direction) -> MoveResult:
    cur = get_section(network, player.position)

    # sealed pipe blocks
    if cur.connections[direction.value]:
        return MoveResult(False, "That pipe's sealed shut.", None)

    dr, dc = _DELTA[direction]
    new_pos = Position(player.position.row + dr, player.position.col + dc)

    # safety bounds check
    if not (0 <= new_pos.row < network.rows and 0 <= new_pos.col < network.cols):
        return MoveResult(False, "Can't go that way (out of bounds).", None)

    return MoveResult(True, f"Moved {direction.value}.", new_pos)


# ---------------------------------------------------------------------------
# Clog trivia resolution + hydro blast
# ---------------------------------------------------------------------------

def attempt_answer(network: PipeNetwork, position: Position, answer: str, question: Question) -> AnswerResult:
    section = get_section(network, position)

    if not section.has_clog:
        return AnswerResult(False, False, 0, "No clog here.")

    if answer == question.correct_answer:
        section.has_clog = False
        return AnswerResult(True, True, +10, "Correct — clog cleared. +10 pressure.")

    return AnswerResult(False, False, -5, f"Wrong — correct was '{question.correct_answer}'. -5 pressure.")


def hydro_blast(network: PipeNetwork, position: Position, player_pressure: int) -> AnswerResult:
    section = get_section(network, position)

    if not section.has_clog:
        return AnswerResult(False, False, 0, "No clog here.")

    if player_pressure < 50:
        return AnswerResult(False, False, 0, "Not enough pressure for hydro blast.")

    section.has_clog = False
    return AnswerResult(True, True, -50, "HYDRO BLAST! Clog cleared. -50 pressure.")


# ---------------------------------------------------------------------------
# Win condition
# ---------------------------------------------------------------------------

def is_network_clear(network: PipeNetwork) -> bool:
    return not any(s.has_clog for row in network.grid for s in row)


# ---------------------------------------------------------------------------
# Fog of War
# ---------------------------------------------------------------------------

def _normalize_visited(visited_raw: Iterable[object]) -> set[Position]:
    """Accepts visited as Positions OR (row,col) tuples/lists; returns set[Position]."""
    out: set[Position] = set()
    for item in visited_raw:
        if isinstance(item, Position):
            out.add(item)
        elif isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], int) and isinstance(item[1], int):
            out.add(Position(item[0], item[1]))
        elif isinstance(item, list) and len(item) == 2 and isinstance(item[0], int) and isinstance(item[1], int):
            out.add(Position(item[0], item[1]))
    return out


def update_visited(visited, new_pos: Position):
    """Return a NEW set/frozenset-like collection, preserving tuple-style inputs."""
    items = list(visited)

    # If caller is already using Position objects, stay in Position-mode
    if any(isinstance(v, Position) for v in items):
        out = _normalize_visited(items)
        out.add(new_pos)
        return out

    # Otherwise, tuple-mode: {(row,col), ...}
    out: set[tuple[int, int]] = set()
    for v in items:
        if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], int) and isinstance(v[1], int):
            out.add((v[0], v[1]))
        elif isinstance(v, list) and len(v) == 2 and isinstance(v[0], int) and isinstance(v[1], int):
            out.add((v[0], v[1]))
        elif isinstance(v, Position):
            out.add((v.row, v.col))

    out.add((new_pos.row, new_pos.col))
    return out


def _visible_positions(network: PipeNetwork, visited_pos: set[Position], current: Position) -> set[Position]:
    vis = set(visited_pos)
    vis.add(current)
    for p in list(vis):
        section = network.grid[p.row][p.col]
        for d in Direction:
            if not section.connections[d.value]:  # open connection only
                dr, dc = _DELTA[d]
                nr, nc = p.row + dr, p.col + dc
                if 0 <= nr < network.rows and 0 <= nc < network.cols:
                    vis.add(Position(nr, nc))
    return vis


def get_visibility_map(
    network: PipeNetwork,
    arg2: Position | Iterable[object],
    arg3: Iterable[object] | Position,
) -> list[list[SectionVisibility]]:
    """
    Supports both call orders:
      - get_visibility_map(network, current_pos, visited_set)
      - get_visibility_map(network, visited_set, current_pos)
    visited_set may contain Position OR (row,col) tuples.
    """
    if isinstance(arg2, Position):
        current = arg2
        visited_raw = arg3
    else:
        visited_raw = arg2
        current = arg3  # type: ignore[assignment]

    visited_pos = _normalize_visited(visited_raw)  # set[Position]
    visible = _visible_positions(network, visited_pos, current)

    out: list[list[SectionVisibility]] = []
    for r in range(network.rows):
        row_vis: list[SectionVisibility] = []
        for c in range(network.cols):
            pos = Position(r, c)
            section = network.grid[r][c]
            is_vis = pos in visible

            if is_vis:
                open_dirs = [d for d, sealed in section.connections.items() if not sealed]
                hc: bool | None = section.has_clog
                od: list[str] | None = open_dirs
            else:
                hc = None
                od = None

            row_vis.append(
                SectionVisibility(
                    position=pos,
                    is_current=(pos == current),
                    is_visited=(pos in visited_pos),
                    is_visible=is_vis,
                    has_clog=hc,
                    open_directions=od,
                )
            )
        out.append(row_vis)

    return out