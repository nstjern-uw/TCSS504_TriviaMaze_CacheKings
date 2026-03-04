# SQLModel Migration & Theme Alignment Plan

This document summarizes the changes needed to evolve `interfaces.md`, the domain model,
and the test suite from the current dataclass + JSON-file architecture to SQLModel + SQLite,
while aligning naming with the plumber/pipe/clog theme from `game_concept.md`.

---

## 1. Thematic Naming

The game concept establishes a plumber navigating a sewer pipe network in Nuovo Fresco.
The domain vocabulary should reflect that — not generic dungeon terms (Room/Door) and
not cybersecurity terms (Node/Firewall).

| Current (generic) | Themed name | Rationale |
|---|---|---|
| `Room` | **`Junction`** | Where pipes meet — the player stands at pipe junctions |
| *(no Door entity)* | **`Passage`** | An open connection between two junctions (currently implicit as `walls[dir] == False`) |
| `Maze` | **`PipeNetwork`** | The grid of connected pipe junctions |
| `Player` | **`Plumber`** | Matches the 80s action-hero plumber from the concept |
| `is_entrance` | **`is_intake`** | Where water (and the plumber) enters the system |
| `is_exit` | **`is_outflow`** | Where the system drains out |
| `has_clog` | **Keep** | Already perfectly themed |
| `walls` | **Keep** | Pipe walls are real and intuitive |
| `MoveResult` | **Keep** | Mechanical, not thematic — fine as-is |
| `AnswerResult` | **Keep** | Same reasoning |
| `Direction` | **Keep** | Neutral, universal |

### Function Renames

| Current | Themed |
|---|---|
| `create_maze()` | `create_network()` |
| `move_player()` | `move_plumber()` |
| `get_room()` | `get_junction()` |
| `has_clog()` | Keep |
| `is_solved()` | Keep |
| `check_solvability()` | Keep |
| `attempt_answer()` | Keep |
| `phase_beam()` | Keep |
| `get_question()` | Keep |

---

## 2. interfaces.md Changes for SQLModel

### §1 Dependency Rules

The current rule that `maze.py` imports "Python stdlib only" expands to allow `sqlmodel`.
The rule that `db.py` "only receives and returns plain dicts" goes away — SQLModel objects
are the persistence layer. A new `models.py` file holds all table definitions.

| Module | May Import | Must Never Import |
|---|---|---|
| `models.py` (new) | `sqlmodel`, `enum`, `typing` | `db`, `maze`, `main` |
| `maze.py` | `models`, `sqlmodel` (type hints), Python stdlib | `db`, `main`, `print()`, `input()` |
| `db.py` | `models`, `sqlmodel`, Python stdlib | `maze`, `main`, `print()`, `input()` |
| `main.py` | `maze`, `db`, `models`, Python stdlib | No restrictions |

### §2 Shared Data Contracts — SQLModel Tables

Dataclasses become SQLModel table classes. The recommended approach keeps walls as a
JSON column on `Junction` (simpler, closest to the current design).

```python
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum


class Direction(str, Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


class GameStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    WON = "won"
    QUIT = "quit"


class Junction(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    row: int
    col: int
    walls_json: str                # '{"north": true, "south": false, ...}'
    has_clog: bool = False
    is_intake: bool = False
    is_outflow: bool = False
    network_id: int = Field(foreign_key="pipe_network.id")


class PipeNetwork(SQLModel, table=True):
    __tablename__ = "pipe_network"
    id: int | None = Field(default=None, primary_key=True)
    rows: int
    cols: int
    intake_row: int = 0
    intake_col: int = 0
    outflow_row: int
    outflow_col: int
    game_id: int = Field(foreign_key="game_state.id")
    junctions: list[Junction] = Relationship()


class Plumber(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    row: int
    col: int
    energy: int = 100
    clogs_cleared: int = 0
    current_level: int = 1
    game_id: int = Field(foreign_key="game_state.id")


class Question(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    prompt: str
    choices_json: str              # '["London","Berlin","Paris","Madrid"]'
    correct_answer: str
    category: str | None = None


class GameState(SQLModel, table=True):
    __tablename__ = "game_state"
    id: int | None = Field(default=None, primary_key=True)
    status: str = GameStatus.IN_PROGRESS.value
    questions_answered: int = 0
    questions_correct: int = 0
    plumber: Plumber | None = Relationship()
    network: PipeNetwork | None = Relationship()
```

`MoveResult` and `AnswerResult` remain plain dataclasses — they are ephemeral return
values, not persisted entities.

### §3 Protocol Contracts

**RepositoryProtocol** changes from JSON file I/O to database operations:

```python
class RepositoryProtocol(Protocol):
    def save_game(self, session: Session, state: GameState) -> bool: ...
    def load_game(self, session: Session, game_id: int) -> GameState | None: ...
    def delete_save(self, session: Session, game_id: int) -> bool: ...
    def list_saves(self, session: Session) -> list[GameState]: ...
```

**Domain functions** stay similar but accept/return SQLModel objects:

```python
def create_network(rows: int, cols: int, seed: int | None = None) -> PipeNetwork: ...
def move_plumber(network: PipeNetwork, plumber: Plumber, direction: Direction) -> MoveResult: ...
def get_junction(network: PipeNetwork, row: int, col: int) -> Junction: ...
def attempt_answer(network: PipeNetwork, junction: Junction, answer: str, question: Question) -> AnswerResult: ...
```

### §4 Boundary Crossing Strategy

This section shrinks dramatically. The current `main.py` has ~50 lines of manual
`asdict()` → dict → reconstruction. With SQLModel, that goes away:

```python
# Saving
session.add(game_state)
session.commit()

# Loading
game_state = session.get(GameState, game_id)
```

The new boundary section should document:
- How `Session` scope is managed (one session per command? per game lifecycle?)
- How `walls_json` is serialized/deserialized (a `@property` on `Junction`)
- That `MoveResult` and `AnswerResult` remain plain dataclasses

### §5 JSON Save Format → Database Schema

The JSON save format section is replaced by a database schema section documenting the
tables, columns, foreign keys, and cascade rules. `schema_version` can become a column
on `GameState` or a separate metadata table.

### §7 Shared Constants

Add database constants:

| Constant | Value |
|---|---|
| `DATABASE_URL` | `"sqlite:///trivia_maze.db"` |
| `SCHEMA_VERSION` | `1` |

---

## 3. Test Suite Changes

All four test files exist and are well-implemented against the current architecture.
The migration requires targeted changes in each file, not a rewrite.

### 3.1 test_maze_contract.py — Mostly Renames

All ~28 tests survive structurally. Changes are mechanical renames:

| Current symbol | Themed symbol |
|---|---|
| `Room` | `Junction` |
| `Maze` | `PipeNetwork` |
| `Player` | `Plumber` |
| `create_maze` | `create_network` |
| `move_player` | `move_plumber` |
| `get_room` | `get_junction` |
| `seeded_maze` (fixture) | `seeded_network` |
| `clog_room_position` (fixture) | `clog_junction_pos` |
| `player_at_entrance` (fixture) | `plumber_at_intake` |
| `r.is_entrance` | `j.is_intake` |
| `r.is_exit` | `j.is_outflow` |

**New tests to add** (SQLModel-specific):

| Test | Why |
|---|---|
| `test_junction_walls_property_round_trips` | Verify `walls_json` ↔ dict `@property` is lossless |
| `test_junction_default_field_values` | Verify SQLModel field defaults match interface constants |

Domain logic tests do not need a database session — SQLModel objects work as plain
in-memory objects when not being persisted.

### 3.2 test_repo_contract.py — Most Significant Changes

The entire persistence model changes from JSON files to SQLite.

**Tests that transform:**

| Current test | SQLModel equivalent |
|---|---|
| `test_save_returns_true` | `test_save_game_commits` — `session.add()` + `commit()` succeeds |
| `test_save_then_load_matches` | `test_save_and_load_round_trip` — full `GameState` with relationships survives save/load |
| `test_load_missing_file` | `test_load_nonexistent_id` — `load_game(session, 9999)` returns `None` |
| `test_delete_and_exists` | Stays conceptually — delete by ID, verify cascade removes children |

**Tests that go away:**

| Current test | Why |
|---|---|
| `test_load_corrupted_json` | SQLite handles data integrity; corruption is infrastructure, not app-level |
| `test_save_non_serializable_returns_false` | SQLModel/Pydantic validates types at the model layer |

**New tests to add:**

| Test | Why |
|---|---|
| `test_cascade_delete_removes_children` | Deleting `GameState` should cascade to `Plumber`, `PipeNetwork`, `Junction` |
| `test_question_bank_query` | Questions can be queried from the DB after seeding |
| `test_save_preserves_junction_relationships` | `PipeNetwork.junctions` has correct count and data after round-trip |
| `test_plumber_foreign_key_constraint` | A `Plumber` cannot reference a nonexistent `GameState` |

**Fixture change:**

```python
# Current
def test_save_returns_true(tmp_path):
    repo = JsonFileRepository()
    path = tmp_path / "save.json"

# SQLModel
@pytest.fixture
def session():
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
```

### 3.3 test_integration.py — Moderate Changes

| Current test | Change needed |
|---|---|
| `test_new_game_initializes_state` | Renames only |
| `test_process_move_command` | Renames only |
| `test_process_invalid_command` | No change |
| `test_process_quit_command` | No change |
| `test_save_and_load_preserves_state` | Structural — `save_path` fixture → `session` fixture; assertions stay similar |
| `test_load_with_no_save` | Becomes `test_load_with_no_saved_games` — returns `False` when DB is empty |
| `test_gamestate_to_dict_round_trip` | **Transforms** into `test_gamestate_session_round_trip` — the manual dict boundary disappears |
| `test_enum_serialization_round_trip` | Stays — enums stored as strings in DB columns still need round-trip verification |
| `test_win_condition` | Renames only |

**GameEngine constructor changes:**

```python
# Current
e = GameEngine(repo=JsonFileRepository(), save_path=save_path)

# SQLModel
e = GameEngine(session=session)
```

**New integration tests to consider:**

| Test | Why |
|---|---|
| `test_question_served_from_db` | `get_question()` pulls from the `Question` table, not a hardcoded list |
| `test_phase_beam_change_persisted` | After phase beam clears a clog, the change is committed to the database |

### 3.4 test_module_isolation.py — New Module, Updated Rules

The AST-based `_code_lines` helper is excellent and stays unchanged.

**New tests to add:**

| Test | What it checks |
|---|---|
| `test_models_imports_no_project_modules` | `models.py` does not import `maze`, `db`, or `main` |
| `test_models_no_print` | `models.py` does not perform I/O |

**Existing tests to update:**

- `test_maze_imports_nothing` → rename to `test_maze_imports_no_infra` and allow
  `from models import ...` while still forbidding `from db` and `from main`.
- `test_db_imports_nothing` → same treatment: allow `from models import ...`,
  forbid `from maze` and `from main`.

Updated dependency rules enforced by isolation tests:

```
models.py  →  sqlmodel only (no project modules)
maze.py    →  models, sqlmodel, stdlib (not db, not main)
db.py      →  models, sqlmodel, stdlib (not maze, not main)
main.py    →  everything
```

---

## 4. Architectural Summary

| Aspect | Current | After Migration |
|---|---|---|
| Domain language | `Room`, `Maze`, `Player` | `Junction`, `PipeNetwork`, `Plumber` |
| Data definitions | `dataclass` in `maze.py` | `SQLModel` tables in `models.py` |
| Persistence | JSON files via `db.py` | SQLite via SQLModel sessions in `db.py` |
| Serialization boundary | Manual `asdict()` + reconstruction in `main.py` | Disappears — SQLModel handles it |
| Question storage | Hardcoded `_QUESTION_POOL` list | `Question` table seeded in the database |
| Test DB | `tmp_path` + JSON files | In-memory `sqlite://` per test |

The fundamental insight is that SQLModel collapses the serialization boundary — domain
objects are database rows. This simplifies `main.py` but means `models.py` becomes a
critical shared dependency that both `maze.py` and `db.py` import, which is a new node
in the dependency graph that `interfaces.md` §1 must account for.
