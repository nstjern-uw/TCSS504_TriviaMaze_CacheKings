"""Game engine for the Trivia Maze walking skeleton.

This module is the orchestrator: it initializes the maze, handles
persistence through db.py, runs the CLI input/output loop, and owns
all dataclass <-> dict conversion.

Dependency rules (RUNBOOK.md):
- Only module allowed to import other project modules (maze, db).
- Only module allowed to use print() and input().
- Owns the serialization boundary (dataclass <-> dict).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from maze import (
    Direction,
    GameState,
    GameStatus,
    Maze,
    Player,
    Position,
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
from db import JsonFileRepository

# ---------------------------------------------------------------------------
# Constants (interfaces.md §7)
# ---------------------------------------------------------------------------

DEFAULT_MAZE_ROWS = 3
DEFAULT_MAZE_COLS = 3
DEFAULT_ENERGY = 100
ENERGY_CORRECT_ANSWER = 10
ENERGY_WRONG_ANSWER = -5
ENERGY_PHASE_BEAM = -50
PHASE_BEAM_COST = 50
DEFAULT_SAVE_PATH = "savegame.json"
SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Serialization boundary — dataclass <-> dict (interfaces.md §4)
# ---------------------------------------------------------------------------

def gamestate_to_dict(state: GameState) -> dict[str, Any]:
    """Convert a GameState to a JSON-safe dict for persistence."""
    d = asdict(state)
    d["status"] = state.status.value
    d["schema_version"] = SCHEMA_VERSION
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
            energy=player_data["energy"],
            clogs_cleared=player_data["clogs_cleared"],
            current_level=player_data["current_level"],
        )

        maze_data = data["maze"]
        grid: list[list[Room]] = []
        for row_data in maze_data["grid"]:
            row_rooms: list[Room] = []
            for room_data in row_data:
                row_rooms.append(Room(
                    position=Position(**room_data["position"]),
                    walls=room_data["walls"],
                    has_clog=room_data["has_clog"],
                    is_entrance=room_data["is_entrance"],
                    is_exit=room_data["is_exit"],
                ))
            grid.append(row_rooms)

        maze_obj = Maze(
            rows=maze_data["rows"],
            cols=maze_data["cols"],
            grid=grid,
            entrance=Position(**maze_data["entrance"]),
            exit_pos=Position(**maze_data["exit_pos"]),
        )

        status_raw = data["status"]
        status = (
            status_raw if isinstance(status_raw, GameStatus)
            else GameStatus(status_raw)
        )

        return GameState(
            player=player,
            maze=maze_obj,
            status=status,
            questions_answered=data["questions_answered"],
            questions_correct=data["questions_correct"],
        )
    except (KeyError, TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Game Engine (interfaces.md §3 — GameEngineProtocol)
# ---------------------------------------------------------------------------

class GameEngine:
    """Orchestrates the game lifecycle: init, commands, save/load, win check."""

    def __init__(
        self,
        repo: JsonFileRepository | None = None,
        save_path: str = DEFAULT_SAVE_PATH,
    ) -> None:
        self._repo = repo or JsonFileRepository()
        self._save_path = save_path
        self._state: GameState | None = None
        self._current_question = None

    @property
    def state(self) -> GameState | None:
        return self._state

    # -- lifecycle -----------------------------------------------------------

    def start_new_game(self, seed: int | None = None) -> None:
        """Initialize a fresh maze and player."""
        m = create_maze(DEFAULT_MAZE_ROWS, DEFAULT_MAZE_COLS, seed=seed)
        self._state = GameState(
            player=Player(
                position=m.entrance,
                energy=DEFAULT_ENERGY,
                clogs_cleared=0,
                current_level=1,
            ),
            maze=m,
            status=GameStatus.IN_PROGRESS,
            questions_answered=0,
            questions_correct=0,
        )

    def save_game(self) -> bool:
        """Persist current game state to JSON via the repository."""
        if self._state is None:
            return False
        return self._repo.save_game(
            gamestate_to_dict(self._state), self._save_path
        )

    def load_game(self) -> bool:
        """Restore game state from a save file.

        Returns False if the file doesn't exist, is corrupted, or fails
        schema validation.
        """
        data = self._repo.load_game(self._save_path)
        if data is None:
            return False
        restored = gamestate_from_dict(data)
        if restored is None:
            return False
        self._state = restored
        return True

    def process_command(self, command: str) -> GameStatus:
        """Parse and execute a player command. Returns current game status.

        Unknown commands print help and return GameStatus.IN_PROGRESS.
        """
        if self._state is None:
            return GameStatus.IN_PROGRESS

        parts = command.strip().lower().split()
        if not parts:
            print("Type 'help' for available commands.")
            return self._state.status

        verb = parts[0]

        if verb in ("north", "south", "east", "west"):
            return self._handle_move(verb)

        if verb in ("a", "b", "c", "d") and self._current_question:
            return self._handle_answer(verb)

        if verb == "quit":
            self._state.status = GameStatus.QUIT
            return GameStatus.QUIT

        if verb == "move" and len(parts) >= 2:
            return self._handle_move(parts[1])

        if verb == "answer" and len(parts) >= 2:
            return self._handle_answer(" ".join(parts[1:]))

        if verb == "beam":
            return self._handle_beam()

        if verb == "save":
            print("Game saved." if self.save_game() else "Save failed.")
            return self._state.status

        if verb == "load":
            print("Game loaded." if self.load_game() else "Load failed.")
            return self._state.status

        if verb == "help":
            self._print_help()
            return self._state.status

        print(f"Unknown command: {command}")
        self._print_help()
        return self._state.status

    def run(self) -> None:
        """Main game loop — runs until WON or QUIT."""
        if self._state is None:
            self.start_new_game()

        print("=== Trivia Maze ===")
        print("Navigate the maze and clear all clogs to win!")
        print(f"Energy: {self._state.player.energy}\n")
        self._print_help()
        print()

        while self._state.status == GameStatus.IN_PROGRESS:
            pos = self._state.player.position
            room = get_room(self._state.maze, pos)
            open_dirs = [d for d, wall in room.walls.items() if not wall]

            if self._current_question and room.has_clog:
                print("\nClog detected! Answer this question:")
            print(f"\n[Room ({pos.row}, {pos.col})] Energy: {self._state.player.energy}")
            if self._current_question and room.has_clog:
                print(f"  {self._current_question.prompt}")
                for letter, choice in zip("abcd", self._current_question.choices):
                    print(f"  {letter}) {choice}")
                print("Use 'answer <letter>' or 'beam' to clear it.")
            else:
                print(f"Open passages: {', '.join(open_dirs) if open_dirs else 'none'}")
                if room.has_clog:
                    print("This room has a clog!")

            try:
                cmd = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nQuitting...")
                self._state.status = GameStatus.QUIT
                break

            if cmd:
                self.process_command(cmd)

        if self._state.status == GameStatus.WON:
            print("\nYou cleared all clogs and won!")
        elif self._state.status == GameStatus.QUIT:
            print("\nGoodbye!")

    # -- private handlers ----------------------------------------------------

    def _handle_move(self, direction_str: str) -> GameStatus:
        try:
            direction = Direction(direction_str)
        except ValueError:
            print(f"Invalid direction: {direction_str}. Use north/south/east/west.")
            return self._state.status

        result = move_player(self._state.maze, self._state.player, direction)
        print(result.message)

        if result.success and result.new_position is not None:
            self._state.player.position = result.new_position
            if has_clog(self._state.maze, result.new_position):
                self._current_question = get_question()

        return self._check_win()

    def _handle_answer(self, answer_text: str) -> GameStatus:
        if self._current_question is None:
            self._current_question = get_question()

        letter_map = {l: c for l, c in zip("abcd", self._current_question.choices)}
        resolved = letter_map.get(answer_text, answer_text)

        result = attempt_answer(
            self._state.maze,
            self._state.player.position,
            resolved,
            self._current_question,
        )
        print(result.message)

        self._state.player.energy += result.energy_change
        self._state.questions_answered += 1

        if result.correct:
            self._state.questions_correct += 1
            if result.clog_cleared:
                self._state.player.clogs_cleared += 1
            self._current_question = None
        else:
            self._current_question = get_question()
            self._present_question()

        return self._check_win()

    def _handle_beam(self) -> GameStatus:
        result = phase_beam(
            self._state.maze,
            self._state.player.position,
            self._state.player.energy,
        )
        print(result.message)

        self._state.player.energy += result.energy_change
        if result.clog_cleared:
            self._state.player.clogs_cleared += 1
            self._current_question = None

        return self._check_win()

    def _check_win(self) -> GameStatus:
        if self._state and is_solved(self._state.maze):
            self._state.status = GameStatus.WON
        return self._state.status

    def _present_question(self) -> None:
        if self._current_question is None:
            self._current_question = get_question()
        print(f"\nClog detected! Answer this question:")
        print(f"  {self._current_question.prompt}")
        for letter, choice in zip("abcd", self._current_question.choices):
            print(f"  {letter}) {choice}")
        print("Use 'answer <letter>' or 'beam' to clear it.")

    def _print_help(self) -> None:
        print("Commands:")
        print("  move <north|south|east|west>  - Move in a direction")
        print("  answer <choice>               - Answer the current question")
        print("  beam                          - Use phase beam (-50 energy)")
        print("  save                          - Save game")
        print("  load                          - Load game")
        print("  quit                          - Quit game")
        print("  help                          - Show this help")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = GameEngine()
    engine.run()
