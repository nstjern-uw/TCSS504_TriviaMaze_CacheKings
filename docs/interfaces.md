# interfaces.md — Nuovo Fresco Pipe Network

## 1. Dependency Rules

| Module | May Import | Must Never |
|---|---|---|
| `maze.py` | Python stdlib only (`random`, `enum`, `dataclasses`, `typing`) | `db`, `main`, `sqlmodel`, `print()`, `input()` |
| `db.py` | `sqlmodel`, `sqlalchemy`, Python stdlib (`json`, `typing`) | `maze`, `main`, `print()`, `input()` |
| `main.py` | `maze`, `db`, Python stdlib | No restrictions |

- Dataclasses and Enums are defined in `maze.py` (domain concepts).
- `db.py` never imports them — it only receives and returns plain dicts.
- `main.py` imports them from `maze.py` and owns all dataclass-to-dict conversion.
- `db.py` uses SQLModel + SQLite for persistence (not JSON files).

---

## 2. Shared Data Contracts

### Enums

```python
class Direction(Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"

class GameStatus(Enum):
    IN_PROGRESS = "in_progress"
    CLEARED = "cleared"
    QUIT = "quit"
```

Enums are stored as their `.value` string. Reconstructed via `Direction("north")`.

### Dataclasses

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
class PipeSection:
    position: Position
    connections: dict[str, bool]   # {"north": True, "south": False, ...}
    has_clog: bool                 # True = sealed, False = open pipe
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
class SectionVisibility:
    position: Position
    is_current: bool               # True if player is here
    is_visited: bool               # True if player has been here
    is_visible: bool               # True if within visibility range
    has_clog: bool | None          # None if hidden by fog
    open_directions: list[str] | None  # None if hidden by fog

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
```

---

## 3. Protocol Contracts

### PipeNetworkProtocol (`maze.py`)

```python
class PipeNetworkProtocol(Protocol):
    def create_pipe_network(self, rows: int, cols: int, seed: int | None = None) -> PipeNetwork:
        """Generate a solvable pipe network with clogs. Raises ValueError if rows/cols < 2."""

    def move_player(self, network: PipeNetwork, player: Player, direction: Direction) -> MoveResult:
        """Attempt a move. Returns result — never mutates player."""

    def get_section(self, network: PipeNetwork, position: Position) -> PipeSection:
        """Return section at position. Raises ValueError if out of bounds."""

    def has_clog(self, network: PipeNetwork, position: Position) -> bool:
        """Check if section has a clog. Raises ValueError if out of bounds."""

    def attempt_answer(self, network: PipeNetwork, position: Position, answer: str, question: Question) -> AnswerResult:
        """Submit an answer at a clog. Mutates section's has_clog on correct answer."""

    def hydro_blast(self, network: PipeNetwork, position: Position, player_pressure: int) -> AnswerResult:
        """Force-clear a clog by spending pressure. Returns result with pressure_change."""

    def is_network_clear(self, network: PipeNetwork) -> bool:
        """True if all blocking clogs are cleared."""

    def check_solvability(self, network: PipeNetwork, start: Position, end: Position) -> bool:
        """DFS from start to end. Returns True if path exists."""

    def get_visibility_map(self, network: PipeNetwork, visited: set[Position], current: Position) -> list[list[SectionVisibility]]:
        """Build a visibility grid for Fog of War rendering."""

    def update_visited(self, visited: set[Position], new_pos: Position) -> set[Position]:
        """Return a new set with new_pos added. Does not mutate input."""
```

### RepositoryProtocol (`db.py`)

```python
class RepositoryProtocol(Protocol):
    def save_game(self, state: dict, save_slot: str = "default") -> bool:
        """Save game state. Return True on success, False on error."""

    def load_game(self, save_slot: str = "default") -> dict | None:
        """Load game state. Return dict or None if not found."""

    def delete_save(self, save_slot: str = "default") -> bool:
        """Delete save slot. Return True if deleted, False if didn't exist."""

    def save_exists(self, save_slot: str = "default") -> bool:
        """Check if save slot exists."""

    def get_unused_question(self) -> dict | None:
        """Get next unused question, mark as asked. Return None if exhausted."""

    def seed_questions(self, questions: list[dict]) -> int:
        """Bulk-load questions. Return count of NEW questions added."""

    def reset_questions(self) -> None:
        """Clear asked flags for new game."""

    def get_question_count(self) -> dict:
        """Return {'total': int, 'asked': int, 'remaining': int}."""
```

### GameEngineProtocol (`main.py`)

```python
class GameEngineProtocol(Protocol):
    def start_new_game(self) -> None:
        """Initialize pipe network and player."""

    def load_game(self) -> bool:
        """Restore from save. Returns False if no save or load fails."""

    def save_game(self) -> bool:
        """Persist current state via db.py."""

    def run(self) -> None:
        """Main game loop until CLEARED or QUIT."""

    def process_command(self, command: str) -> GameStatus:
        """Parse and execute a command. Unknown commands print help."""
```

**Note:** `attempt_answer` is the only protocol method that mutates state (clears the clog in the network grid). All other maze methods return new data without modifying inputs.

---

## 4. Boundary Crossing Strategy

`main.py` owns all conversion between rich objects and plain dicts.

**Saving:**
```python
state_dict = asdict(game_state)       # recursively flattens all dataclasses
state_dict["status"] = game_state.status.value  # enum → string
state_dict["visited_positions"] = [
    {"row": p.row, "col": p.col} for p in game_state.visited_positions
]
db.save_game(state_dict, "default")
```

**Loading:**
```python
data = db.load_game("default")  # returns plain dict
player = Player(
    position=Position(**data["player"]["position"]),
    pressure=data["player"]["pressure"],
    clogs_cleared=data["player"]["clogs_cleared"],
    current_level=data["player"]["current_level"]
)
visited = {Position(**p) for p in data["visited_positions"]}
# ... reconstruct PipeNetwork, PipeSections, GameState similarly
```

`db.py` never sees a `Position` or any dataclass. It just reads and writes dicts via SQLModel + SQLite.

---

## 5. Database Schema

`db.py` uses SQLModel + SQLite. Game state is stored as a JSON blob keyed by save slot. Questions are stored as individual rows with an `asked` flag.

**SaveGame table:**

| Column | Type | Notes |
|---|---|---|
| `save_slot` | `str` (PK) | Unique save identifier |
| `state_json` | `str` | Full game state as JSON blob |
| `updated_at` | `datetime` | Last save timestamp |

**QuestionBank table:**

| Column | Type | Notes |
|---|---|---|
| `id` | `int` (PK) | Auto-increment |
| `prompt` | `str` (unique) | Question text, used for deduplication |
| `choices_json` | `str` | JSON-encoded list of choices |
| `correct_answer` | `str` | Correct answer string |
| `asked` | `bool` | True if served this session |

All fields are required. Schema drift policy: if any required field is missing or has the wrong type during load, `load_game()` returns `None`.

---

## 6. Error Handling

**General rule:** Expected game situations return result objects. Programmer errors raise exceptions. I/O errors are caught internally by `db.py`.

| Scenario | Behavior |
|---|---|
| Move into sealed connection | `MoveResult(success=False, ...)` |
| Move out of bounds | `MoveResult(success=False, ...)` |
| `get_section()` with invalid position | Raises `ValueError` |
| Answer on section without clog | `AnswerResult(correct=False, clog_cleared=False, pressure_change=0, ...)` |
| `create_pipe_network()` with rows < 2 | Raises `ValueError` |
| Save slot not found on load | Returns `None` |
| Corrupted data on load | Returns `None` |
| Database write failure | Returns `False` |
| Questions exhausted | `get_unused_question()` returns `None` |
| Unrecognized player command | Prints help, returns `GameStatus.IN_PROGRESS` |

---

## 7. Shared Constants

| Constant | Value |
|---|---|
| `DEFAULT_NETWORK_ROWS` | `4` |
| `DEFAULT_NETWORK_COLS` | `4` |
| `DEFAULT_PRESSURE` | `100` |
| `PRESSURE_CORRECT_ANSWER` | `+10` |
| `PRESSURE_WRONG_ANSWER` | `-5` |
| `PRESSURE_HYDRO_BLAST` | `-50` |
| `HYDRO_BLAST_COST` | `50` |
| `DEFAULT_SAVE_SLOT` | `"default"` |
| `SCHEMA_VERSION` | `2` |

---

## 8. Clarifications (Tightening)

- Invariant: Player position is always within `0 <= row < network.rows` and `0 <= col < network.cols`.
- Invariant: Every generated pipe network must pass DFS solvability from entry_valve to exit_drain.
- Invariant: Exactly one entry_valve and exactly one exit_drain exist in each pipe network.
- Invariant: Connection symmetry is preserved between adjacent sections.
- Invariant: `visited_positions` always contains the player's current position.
- Schema drift policy: If any required field is missing or has the wrong type during load, `load_game()` returns `None`.
- Ownership rule: After `move_player(...)`, `main.py` applies `MoveResult.new_position` to `player.position` only when `MoveResult.success` is `True`.
- Serialization boundary: Only `main.py` converts between dataclasses and dicts. No other module performs this conversion.
- Question deduplication: Same prompt = same question (case-sensitive match on `prompt` field).
