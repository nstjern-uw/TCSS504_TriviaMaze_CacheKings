# RFC: Phase 3 Refactoring Proposal — Domain Architect Perspective

**Author:** Ryan B.  
**Role:** Domain Architect (`maze.py`)  
**Date:** March 2, 2026  
**Status:** Draft — For Architecture Sync Review

---

## 1. Executive Summary

This RFC proposes changes to `interfaces.md` and the test suite to support three Phase 3 requirements:

1. **SQLModel migration** — Replace flat JSON persistence with SQLModel + SQLite
2. **Fog of War** — Expand the maze beyond 3×3 and track player visibility
3. **Thematic design** — Apply the Nuovo Fresco plumber theme to all domain vocabulary

The guiding principle is **safe refactoring**: the existing module boundaries (`maze.py`, `db.py`, `main.py`) remain intact. SQLModel lives exclusively in `db.py`. Domain logic in `maze.py` stays pure Python. `main.py` continues to own the serialization boundary and all I/O.

> **Scope note:** This RFC is a **Part 1 deliverable** — it defines the new contracts (updated `interfaces.md`) and the updated test specifications. The tests written from this RFC should **fail** until each team member implements their Part 2 feature branch. This RFC does **not** cover implementation details; those belong to Part 2.

---

## 2. Theme Vocabulary

The game concept (see `docs/game_concept.md`) establishes the theme: a plumber navigating the sewer pipe network of Nuovo Fresco, a grimy neon metropolis. All domain language should reflect this.

### Vocabulary Mapping

| Walking Skeleton Term | Themed Term | Where Used | Who Is Affected |
|---|---|---|---|
| `Room` | `PipeSection` | `maze.py` dataclass | **ALL ROLES** — every module references this type |
| `Maze` | `PipeNetwork` | `maze.py` dataclass | **ALL ROLES** — every module references this type |
| `walls` (dict field) | `connections` | `PipeSection` field — `True` = sealed, `False` = open pipe | **ALL ROLES** — used in movement logic, rendering, and serialization |
| `has_clog` | `has_clog` | `PipeSection` field — **KEEPING** this name; it's already thematic | No change needed |
| `entrance` | `entry_valve` | `PipeNetwork` field | **ALL ROLES** — referenced in maze creation, game init, and serialization |
| `exit_pos` | `exit_drain` | `PipeNetwork` field | **ALL ROLES** — referenced in maze creation, win condition, and serialization |
| `clogs_cleared` | `clogs_cleared` | `Player` field — **KEEPING** for consistency with `has_clog` | No change needed |
| `phase_beam` | `hydro_blast` | `maze.py` function | ⚠️ **ENGINE ORCHESTRATOR** — must update command parsing in `main.py` |
| `energy` | `pressure` | `Player` field — water pressure as the plumber's resource | ⚠️ **ENGINE ORCHESTRATOR** — must update all UI text and serialization in `main.py` |
| `energy_change` | `pressure_change` | `AnswerResult` field | ⚠️ **ENGINE ORCHESTRATOR** — must update field access in `main.py` |
| `clog_cleared` | `clog_cleared` | `AnswerResult` field — **KEEPING** for consistency | No change needed |
| `GameStatus.WON` | `GameStatus.CLEARED` | Thematic: the pipes are cleared | **ALL ROLES** — used in win condition checks and serialization |
| `GameStatus.QUIT` | `GameStatus.QUIT` | **KEEPING** — universal | No change needed |
| `is_solved` | `is_network_clear` | `maze.py` function | ⚠️ **ENGINE ORCHESTRATOR** — must update function call in `main.py` |
| `MoveResult` | `MoveResult` | **KEEPING** — mechanically clear, not thematic | No change needed |
| `AnswerResult` | `AnswerResult` | **KEEPING** — mechanically clear | No change needed |
| `Question` | `Question` | **KEEPING** — generic enough for any theme | No change needed |
| `Direction` | `Direction` | **KEEPING** — NORTH/SOUTH/EAST/WEST are universal | No change needed |
| `Position` | `Position` | **KEEPING** — row/col is universal | No change needed |

### Themed Messages (for `main.py` / `view.py` to use)

> ⚠️ **ENGINE ORCHESTRATOR**: These messages replace the generic Walking Skeleton text. Your `main.py` (and `view.py` if applicable) must use themed language throughout the player experience.

| Scenario | Walking Skeleton Message | Themed Message |
|---|---|---|
| Move into sealed pipe | "Can't move north — there's a wall." | "That pipe's welded shut, pal. Try another route." |
| Correct answer | "Correct! The clog is cleared. +10 energy." | "Bingo! Clog's history. +10 pressure, baby." |
| Wrong answer | "Wrong! The correct answer was 'X'. -5 energy." | "Nah, that ain't it. Should've gone with 'X'. Pressure's dropping. -5." |
| Hydro blast success | "Phase beam used! Clog cleared. -50 energy." | "HYDRO BLAST! Stand back — clog's been vaporized. -50 pressure." |
| Insufficient pressure | "Not enough energy to use phase beam." | "Not enough juice in the tanks for a hydro blast. Answer some questions first." |
| No clog in section | "No clog in this room." | "Pipes are flowin' fine here. Save your tools for the real messes." |
| Win | "You cleared all clogs and won!" | "That's the last one! Nuovo Fresco's pipes are flowin' clean. Another day, another job well done." |
| Enter clogged section | *(no equivalent)* | "Whoa — nasty clog up ahead. Time to put the brain to work." |
| Game start | "=== Trivia Maze ===" | "Welcome to Nuovo Fresco's underground. The city's backed up and you're the only one who can fix it." |
| Quit | "Goodbye!" | "Hangin' up the wrench for now. The pipes'll be here when you get back." |
| Move success | "Moved north." | "Movin' through the north pipe. Smells about right." |

---

## 3. Proposed `interfaces.md` — Full Updated Draft

> This section is the **Master Contract** that the team will converge on at the Architecture Sync. Once agreed upon, it replaces the current `docs/interfaces.md`.

### 3.1 Dependency Rules

| Module | May Import | Must Never |
|---|---|---|
| `maze.py` | Python stdlib only (`random`, `enum`, `dataclasses`, `typing`) | `db`, `main`, `sqlmodel`, `print()`, `input()` |
| `db.py` | `sqlmodel`, `sqlite3`, Python stdlib (`os`, `typing`) | `maze`, `main`, `print()`, `input()` |
| `main.py` | `maze`, `db`, Python stdlib | No restrictions |
| `view.py` (if team of 4) | `maze` (for dataclass types only) | `db`, `print()` — receives data from `main.py` |

- Dataclasses and Enums are defined in `maze.py` (domain concepts).
- `db.py` never imports them — it only receives and returns plain dicts.
- `main.py` imports them from `maze.py` and owns all dataclass-to-dict conversion.
- **New:** `sqlmodel` is allowed **only** in `db.py`.

> ⚠️ **PERSISTENCE ENGINEER**: You may now import `sqlmodel` in `db.py`, but the boundary rule still holds — `db.py` must never import `maze` or `main`.

### 3.2 Shared Data Contracts

#### Enums

```python
class Direction(Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"

class GameStatus(Enum):
    IN_PROGRESS = "in_progress"
    CLEARED = "cleared"       # previously named WON
    QUIT = "quit"
```

> ⚠️ **ENGINE ORCHESTRATOR**: `GameStatus.WON` no longer exists. All references to `GameStatus.WON` in `main.py` must change to `GameStatus.CLEARED`.

#### Dataclasses

```python
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
class PipeSection:                    # previously named Room
    position: Position
    connections: dict[str, bool]      # previously named walls (True = sealed, False = open pipe)
    has_clog: bool
    is_entry_valve: bool              # previously named is_entrance
    is_exit_drain: bool               # previously named is_exit

@dataclass
class Player:
    position: Position
    pressure: int                     # previously named energy
    clogs_cleared: int
    current_level: int

@dataclass
class PipeNetwork:                    # previously named Maze
    rows: int
    cols: int
    grid: list[list[PipeSection]]
    entry_valve: Position             # previously named entrance
    exit_drain: Position              # previously named exit_pos

@dataclass
class GameState:
    player: Player
    pipe_network: PipeNetwork         # previously named maze
    status: GameStatus
    questions_answered: int
    questions_correct: int
    visited_positions: set[Position]  # NEW for Phase 3 — Fog of War tracking

@dataclass
class MoveResult:
    success: bool
    message: str
    new_position: Position | None

@dataclass
class AnswerResult:
    correct: bool
    clog_cleared: bool
    pressure_change: int              # previously named energy_change
    message: str

@dataclass
class SectionVisibility:              # NEW for Phase 3 — Fog of War output
    position: Position
    is_current: bool                  # player is here right now
    is_visited: bool                  # player has been here before
    is_visible: bool                  # adjacent to a visited section (revealed but unexplored)
    has_clog: bool | None             # None if not visible (hidden by fog)
    is_exit_drain: bool | None        # None if not visible
    is_entry_valve: bool | None       # None if not visible
    open_directions: list[str] | None # None if not visible; list of open direction names if visible
```

> ⚠️ **ALL ROLES**: The following field renames affect serialization in `main.py` and persistence in `db.py`:
> - `Room` → `PipeSection`
> - `Maze` → `PipeNetwork`
> - `walls` → `connections`
> - `energy` → `pressure`
> - `energy_change` → `pressure_change`
> - `entrance` → `entry_valve`
> - `exit_pos` → `exit_drain`
> - `maze` (in GameState) → `pipe_network`
>
> ⚠️ **ENGINE ORCHESTRATOR**: `GameState` now includes `visited_positions: set[Position]`. You must initialize this on new game, update it after every move, and serialize/deserialize it for save/load.
>
> ⚠️ **PERSISTENCE ENGINEER**: The save format changes (see Section 3.6). The schema version bumps from 1 to 2.

### 3.3 Protocol Contracts

#### PipeNetworkProtocol (`maze.py`)

```python
class PipeNetworkProtocol(Protocol):       # previously named MazeProtocol

    def create_pipe_network(self, rows: int, cols: int, seed: int | None = None) -> PipeNetwork:
        """Generate a solvable pipe network with clogs.
        Raises ValueError if rows/cols < 2."""

    def move_player(self, network: PipeNetwork, player: Player, direction: Direction) -> MoveResult:
        """Attempt a move. Returns result — never mutates player."""

    def get_section(self, network: PipeNetwork, position: Position) -> PipeSection:
        """Return pipe section at position. Raises ValueError if out of bounds."""

    def has_clog(self, network: PipeNetwork, position: Position) -> bool:
        """Check if section has a clog. Raises ValueError if out of bounds."""

    def attempt_answer(self, network: PipeNetwork, position: Position, answer: str, question: Question) -> AnswerResult:
        """Submit an answer at a clog. Mutates section's has_clog on correct answer."""

    def is_network_clear(self, network: PipeNetwork) -> bool:
        """True if all clogs are cleared."""

    def hydro_blast(self, network: PipeNetwork, position: Position, player_pressure: int) -> AnswerResult:
        """Spend pressure to clear a clog without answering. Requires >= 50 pressure."""

    def check_solvability(self, network: PipeNetwork, start: Position, end: Position) -> bool:
        """DFS from start to end. Returns True if path exists through open connections."""

    # --- NEW for Phase 3: Fog of War ---

    def get_visibility_map(self, network: PipeNetwork, visited: set[Position], current: Position) -> list[list[SectionVisibility]]:
        """Return a 2D grid of SectionVisibility for every section in the network.
        Pure data output. No I/O, no side effects."""

    def update_visited(self, visited: set[Position], new_position: Position) -> set[Position]:
        """Return a new set with new_position added. Does not mutate the input set."""
```

> ⚠️ **ENGINE ORCHESTRATOR**: `get_question()` has been **removed** from `maze.py`. You must now retrieve questions from `db.py` via `get_unused_question()` and convert the returned dict into a `Question` dataclass before passing it to `attempt_answer()`. See Section 3.4 for the new flow.
>
> ⚠️ **ENGINE ORCHESTRATOR**: Two new functions (`get_visibility_map`, `update_visited`) are added to `maze.py`. After each successful move, you must call `update_visited()` and then `get_visibility_map()` to get the data needed for rendering the Fog of War.

#### RepositoryProtocol (`db.py`)

> ⚠️ **PERSISTENCE ENGINEER**: This protocol has significant changes. The persistence layer migrates from JSON files to SQLModel + SQLite. Additionally, you now own question bank management — questions are no longer hardcoded in `maze.py`.

```python
class RepositoryProtocol(Protocol):

    # --- Game state persistence (migrated from JSON files to SQLModel + SQLite) ---

    def save_game(self, state: dict, save_slot: str = "default") -> bool:
        """Persist game state dict to SQLite. Returns False on failure."""

    def load_game(self, save_slot: str = "default") -> dict | None:
        """Load game state dict from SQLite. Returns None if not found or corrupted."""

    def delete_save(self, save_slot: str = "default") -> bool:
        """Delete a saved game. Returns False if not found."""

    def save_exists(self, save_slot: str = "default") -> bool:
        """Check if a save slot has data."""

    # --- NEW for Phase 3: Question bank management ---
    # Previously, questions were hardcoded in maze.py. They now live in the DB.

    def get_unused_question(self) -> dict | None:
        """Return a random question that has not been asked yet as a plain dict.
        Returns None if all questions have been asked.
        Dict format: {"prompt": str, "choices": list[str], "correct_answer": str}
        Marks the question as asked (has_been_asked = True) upon retrieval."""

    def reset_questions(self) -> None:
        """Reset all questions to has_been_asked = False. Called on new game."""

    def get_question_count(self) -> dict:
        """Return {"total": int, "asked": int, "remaining": int}."""

    def seed_questions(self, questions: list[dict]) -> int:
        """Insert questions into the bank. Returns count of questions inserted.
        Skips duplicates (matched by prompt text).
        Dict format: {"prompt": str, "choices": list[str], "correct_answer": str}"""
```

#### GameEngineProtocol (`main.py`)

> ⚠️ **ENGINE ORCHESTRATOR**: The engine must now coordinate question retrieval from `db.py`, Fog of War tracking via `maze.py`, and use the new themed vocabulary throughout.

```python
class GameEngineProtocol(Protocol):

    def start_new_game(self) -> None:
        """Initialize pipe network, player, reset question bank, seed visited_positions with entry_valve."""

    def load_game(self) -> bool:
        """Restore from save. Returns False if no save or load fails."""

    def save_game(self) -> bool:
        """Persist current state to SQLite via repository."""

    def run(self) -> None:
        """Main game loop until CLEARED or QUIT."""

    def process_command(self, command: str) -> GameStatus:
        """Parse and execute a command. Unknown commands print help."""
```

### 3.4 Boundary Crossing Strategy

`main.py` owns all conversion between rich domain objects and plain dicts.

> ⚠️ **ENGINE ORCHESTRATOR**: The serialization boundary now includes `visited_positions` and uses all renamed fields. The question retrieval flow is entirely new.

**Saving:**
```python
state_dict = asdict(game_state)
state_dict["status"] = game_state.status.value
state_dict["visited_positions"] = [
    {"row": p.row, "col": p.col} for p in game_state.visited_positions
]
state_dict["schema_version"] = SCHEMA_VERSION
db.save_game(state_dict, "default")
```

**Loading:**
```python
data = db.load_game("default")
player = Player(
    position=Position(**data["player"]["position"]),
    pressure=data["player"]["pressure"],
    clogs_cleared=data["player"]["clogs_cleared"],
    current_level=data["player"]["current_level"],
)
# ... reconstruct PipeNetwork, PipeSections, GameState similarly
visited = {Position(**p) for p in data.get("visited_positions", [])}
```

**Question retrieval (new flow — replaces `get_question()` from `maze.py`):**

> ⚠️ **ENGINE ORCHESTRATOR + PERSISTENCE ENGINEER**: This is a new cross-module flow. `db.py` returns a plain dict. `main.py` converts it to a `Question` dataclass. `maze.py`'s `attempt_answer()` receives the `Question` as before.

```python
q_dict = db.get_unused_question()       # db.py returns plain dict or None
if q_dict is None:
    # all questions asked — handle gracefully (e.g., reset or end game)
    ...
question = Question(                    # main.py converts dict → domain dataclass
    prompt=q_dict["prompt"],
    choices=q_dict["choices"],
    correct_answer=q_dict["correct_answer"],
)
# then pass question to maze.attempt_answer() as before
```

`db.py` never sees a `Position`, `PipeSection`, or any domain dataclass. It reads and writes dicts and manages SQLModel tables internally.

### 3.5 Save Format

> ⚠️ **PERSISTENCE ENGINEER**: The save format field names have changed. Schema version is bumped to 2.
>
> ⚠️ **ENGINE ORCHESTRATOR**: You must update `gamestate_to_dict()` and `gamestate_from_dict()` to use the new field names and include `visited_positions`.

```json
{
  "schema_version": 2,
  "status": "in_progress",
  "questions_answered": 5,
  "questions_correct": 3,
  "visited_positions": [
    {"row": 0, "col": 0},
    {"row": 0, "col": 1},
    {"row": 1, "col": 1}
  ],
  "player": {
    "position": {"row": 1, "col": 1},
    "pressure": 105,
    "clogs_cleared": 2,
    "current_level": 1
  },
  "pipe_network": {
    "rows": 5,
    "cols": 5,
    "entry_valve": {"row": 0, "col": 0},
    "exit_drain": {"row": 4, "col": 4},
    "grid": [
      [
        {
          "position": {"row": 0, "col": 0},
          "connections": {"north": true, "south": false, "east": false, "west": true},
          "has_clog": false,
          "is_entry_valve": true,
          "is_exit_drain": false
        }
      ]
    ]
  }
}
```

*Only first cell shown for brevity. All 25 sections follow the same structure.*

### 3.6 Error Handling

| Scenario | Behavior |
|---|---|
| Move into sealed pipe | `MoveResult(success=False, ...)` |
| Move out of bounds | `MoveResult(success=False, ...)` |
| `get_section()` with invalid position | Raises `ValueError` |
| Answer on section without clog | `AnswerResult(correct=False, clog_cleared=False, pressure_change=0, ...)` |
| `create_pipe_network()` with rows < 2 | Raises `ValueError` |
| Save slot not found on load | Returns `None` |
| Corrupted state in DB | Returns `None` |
| DB write failure | Returns `False` |
| All questions asked | `get_unused_question()` returns `None`; `main.py` handles gracefully |
| Unrecognized player command | Prints help, returns `GameStatus.IN_PROGRESS` |

### 3.7 Shared Constants

| Constant | Old Value | New Value | Notes |
|---|---|---|---|
| `DEFAULT_NETWORK_ROWS` | `3` | `5` | Previously named `DEFAULT_MAZE_ROWS`; expanded from 3×3 |
| `DEFAULT_NETWORK_COLS` | `3` | `5` | Previously named `DEFAULT_MAZE_COLS`; expanded from 3×3 |
| `DEFAULT_PRESSURE` | `100` | `100` | Previously named `DEFAULT_ENERGY` |
| `PRESSURE_CORRECT_ANSWER` | `+10` | `+10` | Previously named `ENERGY_CORRECT_ANSWER` |
| `PRESSURE_WRONG_ANSWER` | `-5` | `-5` | Previously named `ENERGY_WRONG_ANSWER` |
| `PRESSURE_HYDRO_BLAST` | `-50` | `-50` | Previously named `ENERGY_PHASE_BEAM` |
| `HYDRO_BLAST_COST` | `50` | `50` | Previously named `PHASE_BEAM_COST` |
| `DEFAULT_DB_PATH` | `"savegame.json"` | `"game_data.db"` | Previously named `DEFAULT_SAVE_PATH`; now SQLite file |
| `SCHEMA_VERSION` | `1` | `2` | Bumped for new format |
| `CLOG_CHANCE` | `0.5` | `0.4` | Previously unnamed (hardcoded); slightly lower for larger grid |

> ⚠️ **ENGINE ORCHESTRATOR**: All constant names have changed. You must update every reference in `main.py`.

### 3.8 Clarifications & Invariants

- **Invariant:** Player position is always within `0 <= row < network.rows` and `0 <= col < network.cols`.
- **Invariant:** Every generated pipe network must pass DFS solvability from entry valve to exit drain.
- **Invariant:** Exactly one entry valve and exactly one exit drain exist in each network.
- **Invariant:** Connection symmetry is preserved between adjacent sections.
- **Invariant (new):** `visited_positions` always contains at least the entry valve position.
- **Invariant (new):** `visited_positions` is updated by `main.py` after every successful move.
- **Schema drift policy:** If any required field is missing or has the wrong type during load, `load_game()` returns `None`.
- **Ownership rule:** After `move_player(...)`, `main.py` applies `MoveResult.new_position` to `player.position` only when `MoveResult.success` is `True`, then calls `update_visited()`.
- **Question ownership (new):** `maze.py` no longer stores or retrieves questions. All question data flows through `db.py` → `main.py` → `maze.py` (as a `Question` dataclass passed to `attempt_answer`).

> ⚠️ **PERSISTENCE ENGINEER**: The question ownership change means you must implement `seed_questions()` with themed content and `get_unused_question()` with `has_been_asked` tracking.
>
> ⚠️ **ENGINE ORCHESTRATOR**: You are now responsible for calling `db.seed_questions()` on first run and `db.reset_questions()` on new game.

---

## 4. Fog of War — Contract Specification

### 4.1 Concept

The player starts at the entry valve and can only see:
- Their current position (full details)
- Previously visited sections (full details)
- Sections adjacent to any visited section (partial details — they know a pipe exists but haven't explored it)

Everything else is hidden ("fog"). As the player moves, the fog lifts permanently.

### 4.2 Visibility Rules

| Category | `is_current` | `is_visited` | `is_visible` | Detail Fields |
|---|---|---|---|---|
| Current position | `True` | `True` | `True` | All revealed |
| Previously visited | `False` | `True` | `True` | All revealed |
| Adjacent to visited | `False` | `False` | `True` | `has_clog`, `open_directions`, `is_exit_drain`, `is_entry_valve` revealed |
| Unknown (fog) | `False` | `False` | `False` | All `None` |

### 4.3 Contract Notes

- `get_visibility_map()` is a **pure function** — it takes inputs and returns output without mutating anything.
- `update_visited()` is also pure — it returns a new set rather than mutating the input.
- **The `visited_positions` set lives in `GameState`**, which is owned by `main.py`.

> ⚠️ **ENGINE ORCHESTRATOR**: After each successful move, you must call:
> 1. `update_visited()` to add the new position to the visited set
> 2. `get_visibility_map()` to get the current visibility state
> 3. Pass the visibility data to the view layer for rendering the ASCII map

### 4.4 Expanded Network Size

The default network expands from 3×3 to 5×5. The maze generation algorithm (recursive-backtrack DFS) already supports any grid size. The `CLOG_CHANCE` is reduced from 0.5 to 0.4 to keep the number of clogs manageable on a larger grid.

---

## 5. Question Retrieval Migration

### 5.1 Current State

`maze.py` contains a hardcoded `_QUESTION_POOL` list and a `get_question(seed)` function. This violates the spirit of domain purity — trivia content is not domain logic.

### 5.2 What Changes and Who Is Affected

| What | From | To | Who Is Affected |
|---|---|---|---|
| Question storage | `_QUESTION_POOL` in `maze.py` | `question_bank` table in SQLite via `db.py` | ⚠️ **PERSISTENCE ENGINEER** — must create table and seed data |
| Question retrieval | `get_question()` in `maze.py` | `get_unused_question()` in `db.py` (returns dict) | ⚠️ **PERSISTENCE ENGINEER** — must implement; ⚠️ **ENGINE ORCHESTRATOR** — must wire into game loop |
| Question dataclass | `Question` stays in `maze.py` | `main.py` converts dict → `Question` | ⚠️ **ENGINE ORCHESTRATOR** — must add conversion code |
| Question seeding | N/A (hardcoded) | `db.seed_questions()` called by `main.py` on first run | ⚠️ **ENGINE ORCHESTRATOR** — must call on startup |
| Repeat prevention | None (random with replacement) | `has_been_asked` boolean in DB | ⚠️ **PERSISTENCE ENGINEER** — must implement tracking |
| `attempt_answer()` | Stays in `maze.py` | Unchanged — still receives `Question` as parameter | No change needed |
| `_QUESTION_POOL` | Exists in `maze.py` | **REMOVED** from `maze.py` | ⚠️ **DOMAIN ARCHITECT (me)** — must delete from `maze.py` |
| `get_question()` | Exists in `maze.py` | **REMOVED** from `maze.py` | ⚠️ **DOMAIN ARCHITECT (me)** — must delete from `maze.py` |

### 5.3 Seed Data

> ⚠️ **PERSISTENCE ENGINEER**: You should populate the question bank with **themed questions** that align with the Nuovo Fresco plumber narrative. The team should agree on a minimum question count (suggested: 30+ to avoid exhaustion in a 5×5 maze with ~10 clogs).

---

## 6. Test Specification Updates

> **Part 1 scope reminder:** The updated tests should be committed alongside the new `interfaces.md` in the Design PR. These tests define the contracts and should **fail** until Part 2 implementation is complete.

### 6.1 Existing Tests → Updated Tests

#### `test_maze_contract.py` — Domain Architect's Responsibility

| Existing Test | Change Required | New Name |
|---|---|---|
| `test_create_maze_returns_maze` | Rename types, update to 5×5 default | `test_create_pipe_network_returns_network` |
| `test_create_maze_has_entrance_and_exit` | Rename fields to `is_entry_valve`, `is_exit_drain` | `test_create_network_has_valve_and_drain` |
| `test_create_maze_is_solvable` | Rename types | `test_create_network_is_solvable` |
| `test_create_maze_has_clogs` | Rename type only (field `has_clog` unchanged) | `test_create_network_has_clogs` |
| `test_create_maze_deterministic_with_seed` | Rename types, update grid size | `test_create_network_deterministic_with_seed` |
| `test_create_maze_path_has_clog` | Rename types | `test_create_network_path_has_clog` |
| `test_create_maze_invalid_size` | Rename function | `test_create_network_invalid_size` |
| `test_create_maze_wall_symmetry` | Rename `walls` → `connections` | `test_create_network_connection_symmetry` |
| `test_move_valid_direction` | Update type names only | Same name |
| `test_move_returns_expected_position` | Update type names only | Same name |
| `test_move_into_wall` | Update type names only | Same name |
| `test_move_out_of_bounds` | Update type names only | Same name |
| `test_move_does_not_mutate_player` | Update type names only | Same name |
| `test_get_room_valid` | Rename function to `get_section` | `test_get_section_valid` |
| `test_get_room_invalid` | Rename function to `get_section` | `test_get_section_invalid` |
| `test_has_clog_true` | Update type names only (field name unchanged) | Same name |
| `test_has_clog_false` | Update type names only | Same name |
| `test_correct_answer_clears_clog` | Rename `energy_change` → `pressure_change` | Same name |
| `test_correct_answer_updates_room` | Rename to reference section | `test_correct_answer_updates_section` |
| `test_wrong_answer_keeps_clog` | Rename `energy_change` → `pressure_change` | Same name |
| `test_answer_no_clog_room` | Rename to reference section | `test_answer_no_clog_section` |
| `test_is_solved_false_with_clogs` | Rename function | `test_is_network_clear_false_with_clogs` |
| `test_is_solved_true_all_cleared` | Rename function | `test_is_network_clear_true_all_cleared` |
| `test_solvability_true` | Update type names only | Same name |
| `test_solvability_false` | Update type names only | Same name |
| `test_question_has_required_fields` | **REMOVE** — questions now come from DB | *(moved to `test_repo_contract.py`)* |
| `test_question_deterministic_with_seed` | **REMOVE** — no longer applicable | *(DB-backed questions aren't seed-deterministic)* |
| `test_phase_beam_sufficient_energy` | Rename function + field | `test_hydro_blast_sufficient_pressure` |
| `test_phase_beam_insufficient_energy` | Rename function + field | `test_hydro_blast_insufficient_pressure` |

#### New Tests for `test_maze_contract.py` — Fog of War

| New Test | Description | Expected |
|---|---|---|
| `test_get_visibility_map_start_position` | At game start, only entry valve and its neighbors are revealed | Entry valve: `is_current=True, is_visited=True`; adjacent: `is_visible=True`; all others: all fields `None` |
| `test_get_visibility_map_after_move` | After moving one step, both positions show as visited | Both positions: `is_visited=True`; their combined neighbors: `is_visible=True` |
| `test_get_visibility_map_fog_hides_details` | Sections in fog have `None` for all detail fields | `has_clog is None`, `open_directions is None`, etc. |
| `test_get_visibility_map_returns_full_grid` | Output is same dimensions as network | `len(result) == network.rows`, `len(result[0]) == network.cols` |
| `test_get_visibility_map_pure_function` | Calling it does not mutate network or visited set | Assert network and visited unchanged after call |
| `test_update_visited_returns_new_set` | `update_visited` returns a new set, does not mutate input | Original set unchanged, new set contains new position |
| `test_update_visited_contains_new_position` | Returned set includes the new position | `new_position in result` |
| `test_create_network_5x5` | `create_pipe_network(5, 5)` produces valid 5×5 network | `network.rows == 5`, `network.cols == 5`, solvable |
| `test_create_network_larger_has_clogs` | 5×5 network has multiple clogs | `sum(has_clog) >= 2` |

#### `test_repo_contract.py` — Persistence Engineer's Responsibility

> ⚠️ **PERSISTENCE ENGINEER**: Your test file has the most new tests. The existing tests need updating for SQLModel, and the question bank tests are entirely new.

| Existing Test | Change Required |
|---|---|
| `test_save_returns_true` | Update to use SQLModel repo instead of JSON file |
| `test_save_then_load_matches` | Update to use SQLModel repo |
| `test_load_missing_file` | Becomes `test_load_missing_slot` — test missing save slot |
| `test_load_corrupted_json` | Becomes `test_load_corrupted_state` — test corrupted DB data |
| `test_save_non_serializable_returns_false` | Still relevant |
| `test_delete_and_exists` | Update to use save slots instead of file paths |

| New Test | Description |
|---|---|
| `test_get_unused_question_returns_dict` | Returns a dict with `prompt`, `choices`, `correct_answer` |
| `test_get_unused_question_marks_as_asked` | After retrieval, same question not returned again |
| `test_get_unused_question_no_repeats` | Fetching N questions returns N unique prompts |
| `test_get_unused_question_exhausted` | Returns `None` when all questions asked |
| `test_reset_questions` | After reset, previously asked questions are available again |
| `test_seed_questions_populates_bank` | Seeding N questions results in N records |
| `test_seed_questions_skips_duplicates` | Seeding same question twice only inserts once |
| `test_get_question_count` | Returns correct total/asked/remaining counts |

#### `test_integration.py` — Engine Orchestrator's Responsibility

> ⚠️ **ENGINE ORCHESTRATOR**: Integration tests need the most field name updates since they touch all modules.

| Existing Test | Change Required |
|---|---|
| `test_new_game_initializes_state` | Update field names; verify `visited_positions` initialized with entry valve |
| `test_process_move_command` | Update field names |
| `test_process_invalid_command` | Minimal change |
| `test_process_quit_command` | Minimal change |
| `test_save_and_load_preserves_state` | Update for SQLModel; verify `visited_positions` round-trip |
| `test_load_with_no_save` | Update for SQLModel |
| `test_gamestate_to_dict_round_trip` | Update all field names; add `visited_positions` |
| `test_enum_serialization_round_trip` | Update `WON` → `CLEARED` |
| `test_win_condition` | Update `WON` → `CLEARED`; update field names |

| New Test | Description |
|---|---|
| `test_question_from_db_flow` | Engine retrieves question from DB, passes to `attempt_answer` |
| `test_fog_of_war_updates_on_move` | After move, `visited_positions` grows |
| `test_visibility_map_passed_to_view` | Engine generates visibility map after each move |

#### `test_module_isolation.py` — Shared Responsibility

| Existing Test | Change Required |
|---|---|
| `test_maze_imports_nothing` | No change |
| `test_db_imports_nothing` | No change (still checks for `maze`, `main`) |
| `test_maze_no_print` | No change |
| `test_db_no_print` | No change |

| New Test | Description | Who Is Affected |
|---|---|---|
| `test_maze_no_sqlmodel` | `maze.py` must not import `sqlmodel` | ⚠️ **DOMAIN ARCHITECT (me)** |
| `test_maze_no_input` | `maze.py` must not use `input()` | ⚠️ **DOMAIN ARCHITECT (me)** |
| `test_db_no_input` | `db.py` must not use `input()` | ⚠️ **PERSISTENCE ENGINEER** |

---

## 7. Open Questions for Architecture Sync

1. **Theme vocabulary finalization** — Does the team agree with `PipeSection`, `PipeNetwork`, `pressure`, `hydro_blast`, etc.? Or do teammates prefer different terms?

2. **`visited_positions` storage type** — I proposed `set[Position]` in `GameState`. Since `Position` is frozen, it's hashable and works in sets. But sets aren't JSON-serializable, so `main.py` must convert to/from a list of dicts for persistence. Is this acceptable, or should we use `list[Position]` everywhere?

3. **Question count minimum** — How many themed questions should we seed? I suggest 30+ to avoid exhaustion in a 5×5 maze with ~10 clogs.

4. **`GameStatus.WON` → `GameStatus.CLEARED`** — Is the team comfortable with this rename? It's thematic but changes a widely-used enum value.

5. **`view.py` separation** — If we have a 4th team member, should `view.py` be responsible for rendering the Fog of War ASCII map? If so, it needs to import `SectionVisibility` from `maze.py`.

6. **Backward compatibility** — Should `db.py` support migrating old JSON saves to the new SQLite format, or do we start fresh?

---

## 8. Part 1 Deliverables Checklist

These are the specific items that should be committed in the **Design PR** (Part 1):

- [ ] Updated `docs/interfaces.md` (the Master Contract agreed upon at Architecture Sync)
- [ ] Updated `tests/test_maze_contract.py` with renamed tests + new Fog of War tests
- [ ] Updated `tests/test_repo_contract.py` with SQLModel tests + question bank tests
- [ ] Updated `tests/test_integration.py` with renamed fields + new integration tests
- [ ] Updated `tests/test_module_isolation.py` with new isolation checks
- [ ] Updated `tests/conftest.py` if shared fixtures need changes

> **All of these tests should FAIL after the Design PR is merged.** They define the contracts that Part 2 feature branches will implement against.
