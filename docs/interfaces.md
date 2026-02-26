# interfaces.md — Trivia Maze Walking Skeleton

## 1. Dependency Rules

| Module | May Import | Must Never |
|---|---|---|
| `maze.py` | Python stdlib only (`random`, `enum`, `dataclasses`, `typing`) | `db`, `main`, `print()`, `input()` |
| `db.py` | Python stdlib only (`json`, `os`, `typing`) | `maze`, `main`, `print()`, `input()` |
| `main.py` | `maze`, `db`, Python stdlib | No restrictions |

- Dataclasses and Enums are defined in `maze.py` (domain concepts).
- `db.py` never imports them — it only receives and returns plain dicts.
- `main.py` imports them from `maze.py` and owns all dataclass-to-dict conversion.

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
    WON = "won"
    QUIT = "quit"
```

Enums are stored in JSON as their `.value` string. Reconstructed via `Direction("north")`.

### Dataclasses

```python
@dataclass
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
    walls: dict[str, bool]   # {"north": True, "south": False, ...}
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
```

---

## 3. Protocol Contracts

### MazeProtocol (`maze.py`)

```python
class MazeProtocol(Protocol):
    def create_maze(self, rows: int, cols: int, seed: int | None = None) -> Maze:
        """Generate a solvable maze with clogs. Raises ValueError if rows/cols < 2."""

    def move_player(self, maze: Maze, player: Player, direction: Direction) -> MoveResult:
        """Attempt a move. Returns result — never mutates player."""

    def get_room(self, maze: Maze, position: Position) -> Room:
        """Return room at position. Raises ValueError if out of bounds."""

    def has_clog(self, maze: Maze, position: Position) -> bool:
        """Check if room has a clog. Raises ValueError if out of bounds."""

    def attempt_answer(self, maze: Maze, position: Position, answer: str, question: Question) -> AnswerResult:
        """Submit an answer at a clog. Mutates room's has_clog on correct answer."""

    def is_solved(self, maze: Maze) -> bool:
        """True if all blocking clogs are cleared."""

    def get_question(self, seed: int | None = None) -> Question:
        """Return a trivia question."""

    def check_solvability(self, maze: Maze, start: Position, end: Position) -> bool:
        """DFS from start to end. Returns True if path exists."""
```

### RepositoryProtocol (`db.py`)

```python
class RepositoryProtocol(Protocol):
    def save_game(self, state: dict, filepath: str) -> bool:
        """Write dict to JSON file. Returns False on failure."""

    def load_game(self, filepath: str) -> dict | None:
        """Read JSON file to dict. Returns None if missing or corrupted."""

    def delete_save(self, filepath: str) -> bool:
        """Delete save file. Returns False if not found."""

    def save_exists(self, filepath: str) -> bool:
        """Check if save file exists."""
```

### GameEngineProtocol (`main.py`)

```python
class GameEngineProtocol(Protocol):
    def start_new_game(self) -> None:
        """Initialize maze and player."""

    def load_game(self) -> bool:
        """Restore from save. Returns False if no save or load fails."""

    def save_game(self) -> bool:
        """Persist current state to JSON."""

    def run(self) -> None:
        """Main game loop until WON or QUIT."""

    def process_command(self, command: str) -> GameStatus:
        """Parse and execute a command. Unknown commands print help."""
```

**Note:** `attempt_answer` is the only protocol method that mutates state (clears the clog in the maze grid). All other maze methods return new data without modifying inputs.

---

## 4. Boundary Crossing Strategy

`main.py` owns all conversion between rich objects and plain dicts.

**Saving:**
```python
state_dict = asdict(game_state)       # recursively flattens all dataclasses
state_dict["status"] = game_state.status.value  # enum → string
db.save_game(state_dict, "savegame.json")
```

**Loading:**
```python
data = db.load_game("savegame.json")  # returns plain dict
player = Player(
    position=Position(**data["player"]["position"]),
    energy=data["player"]["energy"],
    clogs_cleared=data["player"]["clogs_cleared"],
    current_level=data["player"]["current_level"]
)
# ... reconstruct Maze, Rooms, GameState similarly
```

`db.py` never sees a `Position` or any dataclass. It just reads and writes dicts.

---

## 5. JSON Save Format

Every save file includes `schema_version`. All fields are required.

```json
{
  "schema_version": 1,
  "status": "in_progress",
  "questions_answered": 5,
  "questions_correct": 3,
  "player": {
    "position": {"row": 0, "col": 1},
    "energy": 105,
    "clogs_cleared": 2,
    "current_level": 1
  },
  "maze": {
    "rows": 3,
    "cols": 3,
    "entrance": {"row": 0, "col": 0},
    "exit_pos": {"row": 2, "col": 2},
    "grid": [
      [
        {
          "position": {"row": 0, "col": 0},
          "walls": {"north": true, "south": false, "east": false, "west": true},
          "has_clog": false,
          "is_entrance": true,
          "is_exit": false
        }
      ]
    ]
  }
}
```

*Only first cell shown for brevity. All 9 rooms follow the same structure.*

---

## 6. Error Handling

**General rule:** Expected game situations return result objects. Programmer errors raise exceptions. I/O errors are caught internally by `db.py`.

| Scenario | Behavior |
|---|---|
| Move into wall | `MoveResult(success=False, ...)` |
| Move out of bounds | `MoveResult(success=False, ...)` |
| `get_room()` with invalid position | Raises `ValueError` |
| Answer on room without clog | `AnswerResult(correct=False, clog_cleared=False, energy_change=0, ...)` |
| `create_maze()` with rows < 2 | Raises `ValueError` |
| File not found on load | Returns `None` |
| Corrupted JSON on load | Returns `None` |
| Disk write failure | Returns `False` |
| Unrecognized player command | Prints help, returns `GameStatus.IN_PROGRESS` |

---

## 7. Shared Constants

| Constant | Value |
|---|---|
| `DEFAULT_MAZE_ROWS` | `3` |
| `DEFAULT_MAZE_COLS` | `3` |
| `DEFAULT_ENERGY` | `100` |
| `ENERGY_CORRECT_ANSWER` | `+10` |
| `ENERGY_WRONG_ANSWER` | `-5` |
| `ENERGY_PHASE_BEAM` | `-50` |
| `PHASE_BEAM_COST` | `50` |
| `DEFAULT_SAVE_PATH` | `"savegame.json"` |
| `SCHEMA_VERSION` | `1` |

---

## 8. Clarifications (Tightening)

- Invariant: Player position is always within `0 <= row < maze.rows` and `0 <= col < maze.cols`.
- Invariant: Every generated maze must pass DFS solvability from entrance to exit.
- Invariant: Exactly one entrance and exactly one exit exist in each maze.
- Invariant: Wall symmetry is preserved between adjacent rooms.
- Schema drift policy: If any required field is missing or has the wrong type during load, `load_game()` returns `None`.
- Ownership rule: After `move_player(...)`, `main.py` applies `MoveResult.new_position` to `player.position` only when `MoveResult.success` is `True`.
