# interfaces.md — Quiz Maze MVP (SQLModel + Fog of War)
Theme: Nuovo Fresco Pipe Maze (Plumber / Clogs / Outflow)

## 1. Dependency Rules

| Module | May Import | Must Never |
|---|---|---|
| `maze.py` | Python stdlib only (`random`, `enum`, `dataclasses`, `typing`) | `db`, `main`, `sqlmodel`, `print()`, `input()` |
| `db.py` | Python stdlib + SQLModel (`sqlmodel`, `sqlalchemy`, `typing`, `random`, `json`, `os`) | `maze`, `main`, `print()`, `input()` |
| `main.py` | `maze`, `db`, Python stdlib | — |

- Domain dataclasses/enums live in `maze.py`.
- `db.py` never imports domain types — it accepts/returns plain dicts only.
- `main.py` owns dataclass <-> dict conversion and orchestration.

---

## 2. Shared Data Contracts (Types in `maze.py`)

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

class Visibility(Enum):
    UNKNOWN = "unknown"
    KNOWN = "known"
    VISIBLE = "visible"

@dataclass(frozen=True)
class Position:
    row: int
    col: int

@dataclass
class Question:
    prompt: str
    choices: list[str]         # len == 4
    correct_answer: str        # must be one of choices

@dataclass
class Room:
    position: Position
    walls: dict[str, bool]     # True = wall present; False = open
    has_clog: bool             # themed blocker
    is_entrance: bool
    is_exit: bool              # themed outflow

@dataclass
class Player:
    position: Position
    energy: int
    clogs_cleared: int
    current_level: int
    visited: list[Position]    # fog-of-war memory (JSON-friendly)

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

@dataclass
class FogCell:
    position: Position
    visibility: Visibility
    tile: str                  # "UNKNOWN","EMPTY","PLAYER","CLOG","EXIT","WALL"