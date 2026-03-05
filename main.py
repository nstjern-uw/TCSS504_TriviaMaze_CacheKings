"""Game engine for the Nuovo Fresco Pipe Network.

This module is the orchestrator: it initializes the maze, handles
persistence through db.py, runs the CLI loop via view.py, and owns
all dataclass <-> dict conversion.

Dependency rules (RUNBOOK.md / interfaces.md):
- Only module allowed to import other project modules (maze, db, view).
- Owns the serialization boundary (dataclass <-> dict).
- All user I/O is delegated to view.py (PipeView).
"""

from __future__ import annotations

from dataclasses import asdict
from enum import Enum
from typing import Any

from maze import (
    Direction,
    GameState,
    GameStatus,
    PipeNetwork,
    PipeSection,
    Player,
    Position,
    Question,
    SectionVisibility,
    attempt_answer,
    create_pipe_network,
    get_section,
    get_visibility_map,
    has_clog,
    hydro_blast,
    is_network_clear,
    move_player,
)
from db import SQLiteRepository, SEED_QUESTIONS
from view import PipeView

# ---------------------------------------------------------------------------
# Constants (interfaces.md §7)
# ---------------------------------------------------------------------------

DEFAULT_MAZE_ROWS = 4
DEFAULT_MAZE_COLS = 4
DEFAULT_PRESSURE = 100
DEFAULT_SAVE_SLOT = "default"
SCHEMA_VERSION = 2


# ---------------------------------------------------------------------------
# Engine phase — explicit state machine for the game loop
# ---------------------------------------------------------------------------

class EnginePhase(Enum):
    """Controls which commands the engine accepts at any moment.

    NAVIGATING: player can move, save, load.
    BLOCKED:    player hit a clog and must answer or blast.
    """
    NAVIGATING = "navigating"
    BLOCKED = "blocked"


# ---------------------------------------------------------------------------
# Serialization boundary — dataclass <-> dict (interfaces.md §4)
# ---------------------------------------------------------------------------

def gamestate_to_dict(state: GameState) -> dict[str, Any]:
    """Convert a GameState to a JSON-safe dict for persistence.

    visited_positions (a set) is converted to a list of dicts since
    dataclasses.asdict does not recurse into sets.
    """
    d = asdict(state)
    d["status"] = state.status.value
    d["schema_version"] = SCHEMA_VERSION
    d["visited_positions"] = [
        {"row": p.row, "col": p.col} for p in state.visited_positions
    ]
    return d


def gamestate_from_dict(data: dict[str, Any]) -> GameState | None:
    """Reconstruct a GameState from a plain dict.

    Returns None if any required field is missing or has the wrong type
    (schema drift policy — interfaces.md §8).
    """
    try:
        player_data = data["player"]
        player = Player(
            position=Position(**player_data["position"]),
            pressure=player_data["pressure"],
            clogs_cleared=player_data["clogs_cleared"],
            current_level=player_data["current_level"],
        )

        net_data = data["pipe_network"]
        grid: list[list[PipeSection]] = []
        for row_data in net_data["grid"]:
            row_sections: list[PipeSection] = []
            for sec_data in row_data:
                row_sections.append(PipeSection(
                    position=Position(**sec_data["position"]),
                    connections=sec_data["connections"],
                    has_clog=sec_data["has_clog"],
                    is_entry_valve=sec_data["is_entry_valve"],
                    is_exit_drain=sec_data["is_exit_drain"],
                ))
            grid.append(row_sections)

        pipe_network = PipeNetwork(
            rows=net_data["rows"],
            cols=net_data["cols"],
            grid=grid,
            entry_valve=Position(**net_data["entry_valve"]),
            exit_drain=Position(**net_data["exit_drain"]),
        )

        status_raw = data["status"]
        status = (
            status_raw if isinstance(status_raw, GameStatus)
            else GameStatus(status_raw)
        )

        visited_raw = data.get("visited_positions", [])
        visited = {Position(**p) for p in visited_raw}
        if not visited:
            visited = {player.position}

        return GameState(
            player=player,
            pipe_network=pipe_network,
            status=status,
            questions_answered=data["questions_answered"],
            questions_correct=data["questions_correct"],
            visited_positions=visited,
        )
    except (KeyError, TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Game Engine (interfaces.md §3 — GameEngineProtocol)
# ---------------------------------------------------------------------------

class GameEngine:
    """Orchestrates the game lifecycle: init, commands, save/load, win check.

    Uses an explicit EnginePhase state machine:
    - NAVIGATING: movement, save, load allowed.
    - BLOCKED: answer / blast only (plus universal: quit, save, help).
    """

    def __init__(
        self,
        repo=None,
        save_path: str = DEFAULT_SAVE_SLOT,
        view: PipeView | None = None,
    ) -> None:
        self._repo = repo or SQLiteRepository()
        self._save_path = save_path
        self._view = view or PipeView()
        self._state: GameState | None = None
        self._phase = EnginePhase.NAVIGATING
        self._current_question: Question | None = None

    # -- public properties ---------------------------------------------------

    @property
    def state(self) -> GameState | None:
        return self._state

    @property
    def phase(self) -> EnginePhase:
        return self._phase

    # -- lifecycle -----------------------------------------------------------

    def start_new_game(self, seed: int | None = None) -> None:
        """Initialize a fresh pipe network and player."""
        net = create_pipe_network(DEFAULT_MAZE_ROWS, DEFAULT_MAZE_COLS, seed=seed)
        self._state = GameState(
            player=Player(
                position=net.entry_valve,
                pressure=DEFAULT_PRESSURE,
                clogs_cleared=0,
                current_level=1,
            ),
            pipe_network=net,
            status=GameStatus.IN_PROGRESS,
            questions_answered=0,
            questions_correct=0,
            visited_positions={net.entry_valve},
        )
        self._phase = EnginePhase.NAVIGATING
        self._current_question = None

        if hasattr(self._repo, "seed_questions"):
            self._repo.seed_questions(SEED_QUESTIONS)
        if hasattr(self._repo, "reset_questions"):
            self._repo.reset_questions()

    def save_game(self) -> bool:
        """Persist current game state via the repository."""
        if self._state is None:
            return False
        return self._repo.save_game(
            gamestate_to_dict(self._state),
            self._save_path,
        )

    def load_game(self) -> bool:
        """Restore game state from a save file.

        Reconstructs the engine phase from the player's position:
        if the player is on a clog, re-enter BLOCKED phase.
        """
        data = self._repo.load_game(self._save_path)
        if data is None:
            return False
        restored = gamestate_from_dict(data)
        if restored is None:
            return False

        self._state = restored
        self._current_question = None

        if has_clog(self._state.pipe_network, self._state.player.position):
            self._enter_blocked_phase()
        else:
            self._phase = EnginePhase.NAVIGATING

        return True

    # -- command dispatch (phase-gated) --------------------------------------

    def process_command(self, command: str) -> GameStatus:
        """Parse and execute a player command.

        Commands are gated by EnginePhase:
        - Universal (any phase): quit, save, help
        - NAVIGATING: directional movement, load
        - BLOCKED: answer (a/b/c/d), blast
        """
        if self._state is None:
            return GameStatus.IN_PROGRESS

        raw_parts = command.strip().split()
        if not raw_parts:
            self._view.render_message("Type 'help' for available commands.")
            return self._state.status

        verb = raw_parts[0].lower()

        # --- universal commands (any phase) ---
        if verb == "quit":
            self._state.status = GameStatus.QUIT
            return GameStatus.QUIT
        if verb == "save":
            self._view.render_message(
                "Game saved." if self.save_game() else "Save failed."
            )
            return self._state.status
        if verb == "help":
            self._view.render_help()
            return self._state.status

        _SHORT = {"n": "north", "s": "south", "e": "east", "w": "west"}

        # --- NAVIGATING phase ---
        if self._phase == EnginePhase.NAVIGATING:
            if verb in ("north", "south", "east", "west"):
                return self._handle_move(verb)
            if verb in _SHORT:
                return self._handle_move(_SHORT[verb])
            if verb == "move" and len(raw_parts) >= 2:
                return self._handle_move(raw_parts[1].lower())
            if verb == "load":
                self._view.render_message(
                    "Game loaded." if self.load_game() else "Load failed."
                )
                return self._state.status

        # --- BLOCKED phase ---
        elif self._phase == EnginePhase.BLOCKED:
            if verb in ("a", "b", "c", "d"):
                return self._handle_answer(verb)
            if verb == "answer" and len(raw_parts) >= 2:
                return self._handle_answer(" ".join(raw_parts[1:]))
            if verb == "blast":
                return self._handle_blast()

        self._view.render_message("Can't do that right now. Type 'help'.")
        return self._state.status

    # -- main game loop ------------------------------------------------------

    def run(self) -> None:
        """Main game loop — runs until CLEARED or QUIT."""
        if self._state is None:
            self.start_new_game()

        self._view.render_welcome()
        self._view.render_help()

        while self._state.status == GameStatus.IN_PROGRESS:
            vis_map = get_visibility_map(
                self._state.pipe_network,
                self._state.player.position,
                self._state.visited_positions,
            )
            self._view.render_map(
                vis_map,
                self._state.pipe_network.rows,
                self._state.pipe_network.cols,
                self._state.pipe_network.entry_valve,
                self._state.pipe_network.exit_drain,
            )
            self._view.render_status(
                self._state.player.position.row,
                self._state.player.position.col,
                self._state.player.pressure,
                self._state.player.clogs_cleared,
                self._state.player.current_level,
            )

            if self._phase == EnginePhase.BLOCKED and self._current_question:
                self._view.render_question(
                    self._current_question.prompt,
                    self._current_question.choices,
                )

            cmd = self._view.prompt_command()
            if cmd:
                self.process_command(cmd)

        if self._state.status == GameStatus.CLEARED:
            self._view.render_message(
                "\nAll clogs cleared! Nuovo Fresco flows again. Great work, plumber."
            )
        elif self._state.status == GameStatus.QUIT:
            self._view.render_message(
                "\nThe pipes will wait. Goodbye, plumber."
            )

    # -- private handlers ----------------------------------------------------

    def _handle_move(self, direction_str: str) -> GameStatus:
        try:
            direction = Direction(direction_str)
        except ValueError:
            self._view.render_message(
                f"Invalid direction: {direction_str}. Use north/south/east/west."
            )
            return self._state.status

        result = move_player(self._state.pipe_network, self._state.player, direction)
        self._view.render_message(result.message)

        if result.success and result.new_position is not None:
            self._state.player.position = result.new_position
            self._state.visited_positions = self._state.visited_positions | {result.new_position}

            if has_clog(self._state.pipe_network, result.new_position):
                self._enter_blocked_phase()

        return self._check_win()

    def _enter_blocked_phase(self) -> None:
        """Transition to BLOCKED and fetch a question."""
        self._phase = EnginePhase.BLOCKED
        self._fetch_question()

        if self._current_question is None:
            self._view.render_message(
                "No questions remain — pressure surge clears the clog!"
            )
            section = get_section(self._state.pipe_network, self._state.player.position)
            section.has_clog = False
            self._phase = EnginePhase.NAVIGATING

    def _handle_answer(self, answer_text: str) -> GameStatus:
        if self._current_question is None:
            self._fetch_question()
            if self._current_question is None:
                return self._state.status

        letter_map = {
            l: c for l, c in zip("abcd", self._current_question.choices)
        }
        resolved = letter_map.get(answer_text.lower(), answer_text)

        result = attempt_answer(
            self._state.pipe_network,
            self._state.player.position,
            resolved,
            self._current_question,
        )
        self._view.render_message(result.message)

        self._state.player.pressure += result.pressure_change
        self._state.questions_answered += 1

        if result.correct:
            self._state.questions_correct += 1
            if result.clog_cleared:
                self._state.player.clogs_cleared += 1
            self._current_question = None
            self._phase = EnginePhase.NAVIGATING
        else:
            self._fetch_question()

        return self._check_win()

    def _handle_blast(self) -> GameStatus:
        result = hydro_blast(
            self._state.pipe_network,
            self._state.player.position,
            self._state.player.pressure,
        )
        self._view.render_message(result.message)

        self._state.player.pressure += result.pressure_change
        if result.clog_cleared:
            self._state.player.clogs_cleared += 1
            self._current_question = None
            self._phase = EnginePhase.NAVIGATING

        return self._check_win()

    def _fetch_question(self) -> None:
        """Get an unused question from the repo. Falls back to None
        (triggering auto-clear) if the repo has no question bank or
        all questions are exhausted."""
        if hasattr(self._repo, "get_unused_question"):
            q_dict = self._repo.get_unused_question()
            if q_dict is not None:
                self._current_question = Question(
                    prompt=q_dict["prompt"],
                    choices=q_dict["choices"],
                    correct_answer=q_dict["correct_answer"],
                )
                return
        self._current_question = None

    def _check_win(self) -> GameStatus:
        if self._state and is_network_clear(self._state.pipe_network):
            self._state.status = GameStatus.CLEARED
        return self._state.status


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = GameEngine()
    engine.run()
