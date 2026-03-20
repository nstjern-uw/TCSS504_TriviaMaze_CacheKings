from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class VisibleCell:
    """
    GUI-safe cell representation derived from maze.SectionVisibility.

    This is intentionally presentation-only. The Qt layer should render these
    values, not compute maze rules from scratch.
    """

    row: int
    col: int
    is_current: bool
    is_visited: bool
    is_visible: bool
    is_entry_valve: bool
    is_exit_drain: bool
    has_clog: bool | None
    north_open: bool | None
    south_open: bool | None
    east_open: bool | None
    west_open: bool | None


@dataclass(frozen=True)
class QuestionState:
    prompt: str
    choices: list[str]


@dataclass(frozen=True)
class GameViewState:
    """
    Single renderable UI state for the Qt window.

    Chunk 1 does not build the controller yet, but defining this model now
    keeps the GUI layer clean and testable.
    """

    title: str
    status_message: str
    rows: int
    cols: int
    cells: list[list[VisibleCell]]
    player_row: int
    player_col: int
    pressure: int
    clogs_cleared: int
    current_level: int
    questions_answered: int
    questions_correct: int
    phase: str
    game_status: str
    can_move_north: bool
    can_move_south: bool
    can_move_east: bool
    can_move_west: bool
    can_answer: bool
    can_blast: bool
    can_save: bool
    can_load: bool
    question: Optional[QuestionState] = None