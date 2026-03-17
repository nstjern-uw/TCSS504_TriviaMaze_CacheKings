from __future__ import annotations

from typing import Any


class QtPipeView:
    """
    Qt-friendly view bridge for GameEngine.

    This mirrors the same public presentation methods the engine already uses
    with PipeView, but instead of printing to the terminal it stores the latest
    display data so the Qt controller/window can read it.

    Important:
    - no imports from maze.py
    - no imports from db.py
    - no GUI rendering here
    """

    def __init__(self) -> None:
        self.last_message: str = (
            "NUOVO FRESCO ALERT: city pressure is unstable. Time to hit the pipes."
        )
        self.last_help_text: str = self._build_help_text()
        self.last_question_prompt: str | None = None
        self.last_question_choices: list[str] = []
        self.last_rendered_map: dict[str, Any] | None = None
        self.last_status: dict[str, int] = {
            "row": 0,
            "col": 0,
            "pressure": 0,
            "clogs_cleared": 0,
            "current_level": 0,
        }

    def prompt_command(self) -> str:
        """
        Unused in the Qt flow.
        The Qt controller will call GameEngine directly instead of asking for
        terminal input.
        """
        return ""

    def render_map(
        self,
        vis_grid,
        rows: int,
        cols: int,
        entry_valve=None,
        exit_drain=None,
    ) -> None:
        self.last_rendered_map = {
            "vis_grid": vis_grid,
            "rows": rows,
            "cols": cols,
            "entry_valve": entry_valve,
            "exit_drain": exit_drain,
        }

    def render_status(
        self,
        row: int,
        col: int,
        pressure: int,
        clogs_cleared: int,
        level: int,
    ) -> None:
        self.last_status = {
            "row": row,
            "col": col,
            "pressure": pressure,
            "clogs_cleared": clogs_cleared,
            "current_level": level,
        }

    def render_question(self, prompt: str, choices: list[str]) -> None:
        self.last_question_prompt = prompt
        self.last_question_choices = list(choices)

    def render_message(self, msg: str) -> None:
        self.last_message = msg

    def render_welcome(self) -> None:
        self.last_message = (
            "The city's pipes are clogged. You're the best plumber in town. "
            "Suit up and keep Nuovo Fresco flowing."
        )

    def render_help(self) -> None:
        self.last_help_text = self._build_help_text()

    def clear_question(self) -> None:
        self.last_question_prompt = None
        self.last_question_choices = []

    def _build_help_text(self) -> str:
        return (
            "PIPE COMMANDS\n"
            "Move: Arrow keys\n"
            "Clog answers: 1 / 2 / 3 / 4\n"
            "Special: B — hydro blast  (-50 pressure)\n"
            "System: save / load / help / quit"
        )