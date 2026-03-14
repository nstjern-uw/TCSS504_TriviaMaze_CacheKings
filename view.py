"""View layer for the Nuovo Fresco Pipe Network.

Owns all print() and input() calls for the CLI. Receives pure data
from the engine and renders themed output.

This module is stdlib-only — it does not import maze or db.
SectionVisibility objects are received by duck-typing from the engine.
"""

from __future__ import annotations

import sys
from typing import Any

_ARROW_MAP = {"[A": "north", "[B": "south", "[C": "east", "[D": "west"}


class PipeView:
    """CLI renderer for the Nuovo Fresco sewer system."""

    def prompt_command(self) -> str:
        """Read player input. Arrow keys map to directions instantly;
        typed commands are accumulated until Enter."""
        sys.stdout.write("> ")
        sys.stdout.flush()
        try:
            return self._read_raw()
        except (ImportError, OSError, ValueError):
            # Non-TTY (tests, pipes) — fall back to plain input
            try:
                return input("").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return "quit"

    def _read_raw(self) -> str:
        """cbreak-mode reader: instant arrow keys, buffered text."""
        import tty
        import termios

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            ch = sys.stdin.read(1)

            if ch == "\x1b":
                seq = sys.stdin.read(2)
                direction = _ARROW_MAP.get(seq, "")
                if direction:
                    print(direction)
                return direction

            if ch in ("\r", "\n"):
                print()
                return ""

            if ch == "\x03":
                print()
                return "quit"

            buf = ch
            sys.stdout.write(ch)
            sys.stdout.flush()
            while True:
                c = sys.stdin.read(1)
                if c in ("\r", "\n"):
                    print()
                    return buf.strip()
                if c == "\x1b":
                    sys.stdin.read(2)
                    continue
                if c in ("\x7f", "\b"):
                    if buf:
                        buf = buf[:-1]
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                elif c == "\x03":
                    print()
                    return "quit"
                else:
                    buf += c
                    sys.stdout.write(c)
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def render_map(
        self,
        vis_grid: list[list[Any]],
        rows: int,
        cols: int,
        entry_valve: Any = None,
        exit_drain: Any = None,
    ) -> None:
        """Draw the ASCII pipe network map from fog-of-war data."""

        def _is_open(sv: Any, direction: str) -> bool:
            if not sv.is_visible and not sv.is_visited:
                return False
            if sv.open_directions is None:
                return False
            return direction in sv.open_directions

        def _h_segment(r: int, c: int) -> str:
            """Horizontal border segment above row r, at column c."""
            if r == 0 or r == rows:
                return "───"
            above = vis_grid[r - 1][c]
            below = vis_grid[r][c]
            if _is_open(above, "south") or _is_open(below, "north"):
                return "   "
            return "───"

        def _v_separator(r: int, c: int) -> str:
            """Vertical separator left of column c in row r."""
            if c == 0 or c == cols:
                return "│"
            left = vis_grid[r][c - 1]
            right = vis_grid[r][c]
            if _is_open(left, "east") or _is_open(right, "west"):
                return " "
            return "│"

        print()
        print("  ┌─── NUOVO FRESCO PIPE NETWORK ───┐")
        print()

        col_header = "     "
        for c in range(cols):
            col_header += f" {c}  "
        print(col_header)

        for r in range(rows):
            border = "     "
            for c in range(cols):
                border += "┼" + _h_segment(r, c)
            border += "┼"
            print(border)

            line = f"  {r}  "
            for c in range(cols):
                line += _v_separator(r, c)
                sv = vis_grid[r][c]
                if not sv.is_visible and not sv.is_visited:
                    line += "░░░"
                else:
                    line += f" {self._cell_glyph(sv, entry_valve, exit_drain)} "
            line += "│"
            print(line)

        bottom = "     "
        for c in range(cols):
            bottom += "┼───"
        bottom += "┼"
        print(bottom)

        print()
        print("  ◉ You  ▓ Clog  · Clear  ○ Visible  ░ Unknown")
        print("  ▲ Valve (start)   ▼ Drain (exit)")
        print()

    def render_status(
        self,
        row: int,
        col: int,
        pressure: int,
        clogs_cleared: int,
        level: int,
    ) -> None:
        """Show the plumber's current status bar."""
        print(
            f"  Section ({row},{col})"
            f"  |  Pressure: {pressure}"
            f"  |  Clogs cleared: {clogs_cleared}"
            f"  |  Level {level}"
        )

    def render_question(self, prompt: str, choices: list[str]) -> None:
        """Display a clog encounter and the trivia question."""
        print()
        print("  ╔══════════════════════════════════════╗")
        print("  ║   CLOG DETECTED — ANSWER TO CLEAR    ║")
        print("  ╚══════════════════════════════════════╝")
        print()
        print(f"  {prompt}")
        print()
        for letter, choice in zip("abcd", choices):
            print(f"    {letter}) {choice}")
        print()
        print("  Answer with a/b/c/d, or 'blast' to force-clear.")

    def render_message(self, msg: str) -> None:
        """Display a single themed message line."""
        print(f"  {msg}")

    def render_welcome(self) -> None:
        """Splash screen for game start."""
        print()
        print("  ╔══════════════════════════════════════════════╗")
        print("  ║                                              ║")
        print("  ║   ══╗ NUOVO FRESCO PIPE NETWORK  ╔══         ║")
        print("  ║     ║  ▓ ▓ ▓ ▓ ▓ ▓ ▓ ▓ ▓ ▓ ▓ ▓   ║           ║")
        print("  ║     ╚════════════════════════════╝           ║")
        print("  ║                                              ║")
        print("  ║   The city's pipes are clogged.              ║")
        print("  ║   You're the best plumber in town.           ║")
        print("  ║   Navigate the sewers, clear the clogs,      ║")
        print("  ║   and keep Nuovo Fresco flowing.             ║")
        print("  ║                                              ║")
        print("  ╚══════════════════════════════════════════════╝")
        print()

    def render_help(self) -> None:
        """Command reference."""
        print()
        print("  Commands:")
        print("    Arrow keys or n/s/e/w        Move through the pipes")
        print("    a / b / c / d                Answer the current question")
        print("    blast                        Hydro-blast a clog (-50 pressure)")
        print("    save                         Save your progress")
        print("    load                         Load saved game")
        print("    quit                         Quit game")
        print("    help                         Show this help")
        print()

    def _cell_glyph(
        self,
        sv: Any,
        entry_valve: Any = None,
        exit_drain: Any = None,
    ) -> str:
        """Pick the display glyph for a visible/visited section."""
        if sv.is_current:
            return "◉"
        if sv.has_clog:
            return "▓"
        if exit_drain is not None and sv.position == exit_drain:
            return "▼"
        if entry_valve is not None and sv.position == entry_valve:
            return "▲"
        if sv.is_visited:
            return "·"
        if sv.is_visible:
            return "○"
        return "░"
