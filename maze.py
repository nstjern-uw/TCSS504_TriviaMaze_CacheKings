"""Domain logic for the Trivia Maze walking skeleton.

This module contains all dataclasses, enums, and game logic.
It must not import db, main, or any project module.
It must not use print() or input().
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Direction(Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


class GameStatus(Enum):
    IN_PROGRESS = "in_progress"
    WON = "won"
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
class Room:
    position: Position
    walls: dict[str, bool]
    has_clog: bool
    is_entrance: bool
    is_exit: bool


@dataclass
class Player:
    position: Position
    energy: int
    clogs_cleared: int
    current_level: int


@dataclass
class Maze:
    rows: int
    cols: int
    grid: list[list[Room]]
    entrance: Position
    exit_pos: Position


@dataclass
class GameState:
    player: Player
    maze: Maze
    status: GameStatus
    questions_answered: int
    questions_correct: int


@dataclass
class MoveResult:
    success: bool
    message: str
    new_position: Position | None


@dataclass
class AnswerResult:
    correct: bool
    clog_cleared: bool
    energy_change: int
    message: str


# ---------------------------------------------------------------------------
# Direction helpers — lookup tables used by movement and maze generation
# ---------------------------------------------------------------------------

# Maps each direction to its opposite (used to keep walls consistent)
_OPPOSITE: dict[Direction, Direction] = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST,
}

# Maps each direction to a (row, col) offset for grid traversal
_DELTA: dict[Direction, tuple[int, int]] = {
    Direction.NORTH: (-1, 0),
    Direction.SOUTH: (1, 0),
    Direction.EAST: (0, 1),
    Direction.WEST: (0, -1),
}


# ---------------------------------------------------------------------------
# Maze generation — build grid, carve walls, verify solvability
# ---------------------------------------------------------------------------

# Helper: create a fresh wall dict with all four walls up
def _empty_walls() -> dict[str, bool]:
    """Return a wall dict with all four walls up (True = wall present)."""
    return {d.value: True for d in Direction}


# Wall carving: recursive-backtrack DFS that opens walls between rooms
def _carve_passages(
    grid: list[list[Room]],
    rows: int,
    cols: int,
    rng: random.Random,
) -> None:
    """Randomly carve passages using recursive-backtrack (DFS) wall carving.

    Modifies *grid* in place by setting wall entries to False for
    connected neighbours.
    """
    visited: set[tuple[int, int]] = set()

    def _dfs(r: int, c: int) -> None:
        visited.add((r, c))
        directions = list(Direction)
        rng.shuffle(directions)
        for d in directions:
            dr, dc = _DELTA[d]
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in visited:
                grid[r][c].walls[d.value] = False
                grid[nr][nc].walls[_OPPOSITE[d].value] = False
                _dfs(nr, nc)

    _dfs(0, 0)


# Solvability check: DFS from entrance to exit through open walls
def check_solvability(maze: Maze, start: Position, end: Position) -> bool:
    """Return True if a path exists from start to end through open walls."""
    visited: set[Position] = set()

    def _dfs(pos: Position) -> bool:
        if pos == end:
            return True
        visited.add(pos)
        room = maze.grid[pos.row][pos.col]
        for d in Direction:
            if room.walls[d.value]:
                continue
            dr, dc = _DELTA[d]
            neighbour = Position(pos.row + dr, pos.col + dc)
            if neighbour not in visited:
                if _dfs(neighbour):
                    return True
        return False

    return _dfs(start)


# Public entry point: build a complete, solvable maze
def create_maze(rows: int = 3, cols: int = 3, seed: int | None = None) -> Maze:
    """Build a solvable maze with randomised walls and clogs.

    Entrance is always top-left (0, 0); exit is bottom-right (rows-1, cols-1).
    Regenerates until the maze is solvable (fast for small grids).
    """
    if rows < 2 or cols < 2:
        raise ValueError("rows and cols must be >= 2")

    entrance = Position(0, 0)
    exit_pos = Position(rows - 1, cols - 1)
    rng = random.Random(seed)
    clog_chance = 0.5

    while True:
        grid: list[list[Room]] = []
        for r in range(rows):
            row_rooms: list[Room] = []
            for c in range(cols):
                pos = Position(r, c)
                is_entrance = pos == entrance
                is_exit = pos == exit_pos
                has_clog = (
                    not is_entrance
                    and not is_exit
                    and rng.random() < clog_chance
                )
                row_rooms.append(
                    Room(
                        position=pos,
                        walls=_empty_walls(),
                        has_clog=has_clog,
                        is_entrance=is_entrance,
                        is_exit=is_exit,
                    )
                )
            grid.append(row_rooms)

        # Ensure at least one clog exists (test contract requirement)
        if not any(room.has_clog for row in grid for room in row):
            candidates = [
                room for row in grid for room in row
                if not room.is_entrance and not room.is_exit
            ]
            if candidates:
                rng.choice(candidates).has_clog = True

        _carve_passages(grid, rows, cols, rng)

        maze = Maze(
            rows=rows,
            cols=cols,
            grid=grid,
            entrance=entrance,
            exit_pos=exit_pos,
        )

        if check_solvability(maze, entrance, exit_pos):
            return maze


# ---------------------------------------------------------------------------
# Room queries — read-only lookups into the maze grid
# ---------------------------------------------------------------------------

# Get the room at a specific position
def get_room(maze: Maze, position: Position) -> Room:
    """Return the Room at the given position."""
    if not (0 <= position.row < maze.rows and 0 <= position.col < maze.cols):
        raise ValueError(f"Position out of bounds: ({position.row}, {position.col})")
    return maze.grid[position.row][position.col]


# Check if a room has an uncleared clog
def has_clog(maze: Maze, position: Position) -> bool:
    """Return True if the room at position has a clog."""
    return get_room(maze, position).has_clog


# ---------------------------------------------------------------------------
# Movement logic — validate moves, return results (does NOT mutate player)
# ---------------------------------------------------------------------------

# Attempt to move the player in a direction
def move_player(maze: Maze, player: Player, direction: Direction) -> MoveResult:
    """Attempt to move player in the given direction.
    
    Returns MoveResult with success status, message, and new position if valid.
    Does NOT mutate the player — main.py is responsible for updating player.position.
    """
    current_room = get_room(maze, player.position)
    
    # Check if there's a wall blocking this direction
    if current_room.walls[direction.value]:
        return MoveResult(
            success=False,
            message=f"Can't move {direction.value} — there's a wall.",
            new_position=None,
        )
    
    # Calculate new position
    dr, dc = _DELTA[direction]
    new_pos = Position(
        row=player.position.row + dr,
        col=player.position.col + dc,
    )
    
    # Validate bounds (should never happen if walls are correct, but safety check)
    if not (0 <= new_pos.row < maze.rows and 0 <= new_pos.col < maze.cols):
        return MoveResult(
            success=False,
            message=f"Can't move {direction.value} — out of bounds.",
            new_position=None,
        )
    
    # Move is valid
    return MoveResult(
        success=True,
        message=f"Moved {direction.value}.",
        new_position=new_pos,
    )


# ---------------------------------------------------------------------------
# Trivia question logic — fetch questions and validate answers
# ---------------------------------------------------------------------------

# Hardcoded question pool for the walking skeleton
_QUESTION_POOL: list[Question] = [
    Question(
        prompt="What is the capital of France?",
        choices=["London", "Berlin", "Paris", "Madrid"],
        correct_answer="Paris",
    ),
    Question(
        prompt="What is 2 + 2?",
        choices=["3", "4", "5", "6"],
        correct_answer="4",
    ),
    Question(
        prompt="Which planet is known as the Red Planet?",
        choices=["Venus", "Mars", "Jupiter", "Saturn"],
        correct_answer="Mars",
    ),
    Question(
        prompt="What is the largest ocean on Earth?",
        choices=["Atlantic", "Indian", "Arctic", "Pacific"],
        correct_answer="Pacific",
    ),
    Question(
        prompt="Who wrote 'Romeo and Juliet'?",
        choices=["Dickens", "Shakespeare", "Hemingway", "Austen"],
        correct_answer="Shakespeare",
    ),
]


# Get a random trivia question
def get_question(seed: int | None = None) -> Question:
    """Return a random trivia question from the pool."""
    rng = random.Random(seed)
    return rng.choice(_QUESTION_POOL)


# Process a player's answer to a trivia question
def attempt_answer(
    maze: Maze,
    position: Position,
    answer: str,
    question: Question,
) -> AnswerResult:
    """Validate the player's answer and return result.
    
    If the room has no clog, answering is rejected (energy_change = 0).
    If the room has a clog and the answer is correct, this mutates the maze
    by clearing the clog (room.has_clog = False).
    """
    current_room = get_room(maze, position)

    if not current_room.has_clog:
        return AnswerResult(
            correct=False,
            clog_cleared=False,
            energy_change=0,
            message="No clog in this room.",
        )

    correct = answer == question.correct_answer
    
    if correct:
        current_room.has_clog = False
        clog_cleared = True
        energy_change = 10
        message = "Correct! The clog is cleared. +10 energy."
    else:
        clog_cleared = False
        energy_change = -5
        message = f"Wrong! The correct answer was '{question.correct_answer}'. -5 energy."
    
    return AnswerResult(
        correct=correct,
        clog_cleared=clog_cleared,
        energy_change=energy_change,
        message=message,
    )


# ---------------------------------------------------------------------------
# phase_beam — energy spend to clear a clog
# ---------------------------------------------------------------------------

# Use phase beam to clear a clog (no trivia required)
def phase_beam(maze: Maze, position: Position, player_energy: int) -> AnswerResult:
    """Attempt to clear a clog by spending energy.

    Requirements (interface-tests.md):
    - If player_energy >= 50 and room has a clog: clear clog, energy_change = -50
    - If player_energy < 50: reject, no clog cleared, energy_change = 0
    """
    room = get_room(maze, position)

    if not room.has_clog:
        return AnswerResult(
            correct=False,
            clog_cleared=False,
            energy_change=0,
            message="No clog in this room.",
        )

    if player_energy < 50:
        return AnswerResult(
            correct=False,
            clog_cleared=False,
            energy_change=0,
            message="Not enough energy to use phase beam.",
        )

    room.has_clog = False
    return AnswerResult(
        correct=True,
        clog_cleared=True,
        energy_change=-50,
        message="Phase beam used! Clog cleared. -50 energy.",
    )


# ---------------------------------------------------------------------------
# Win condition — solved only when all clogs are cleared
# ---------------------------------------------------------------------------

# Check if the maze is solved (all clogs cleared)
def is_solved(maze: Maze) -> bool:
    """Return True if no rooms have remaining clogs."""
    return not any(room.has_clog for row in maze.grid for room in row)
