# Interface Acceptance Tests

Every test in this document is derived from the interface contracts in [interfaces.md](interfaces.md). A module is accepted when **all** tests in its section pass. Because `maze.py` and `db.py` never import each other, their test suites can run in complete isolation — only `main.py` tests touch both.

All tests use **pytest**. Fixtures and helpers referenced below (`make_room`, `make_maze`, `make_game_state`) are small factory functions that construct valid domain objects with sensible defaults so individual tests stay focused on the property under verification.

---

## Developer Workflow: Building in Isolation

This test spec is designed for a team of 3-4 developers who work independently and merge confidently. Each developer owns one module and runs only their test file during day-to-day development. The pieces snap together at integration time because every module is built against the same interface contracts.

### Team Assignment

| Developer | Module | Test File | Depends On |
|---|---|---|---|
| Dev 1 | `maze.py` | `tests/test_maze.py` | Nothing — pure Python, no external modules |
| Dev 2 | `db.py` | `tests/test_db.py` | Nothing — works with raw `dict[str, Any]` only |
| Dev 3 | `main.py` | `tests/test_main.py` | `maze.py` types + a `FakeRepository` stub (see below) |
| Dev 4 | View / UI | *(separate spec)* | `maze.py` types for display; `main.py` for orchestration |

### Phase 1: Independent Development

Each developer builds and tests their module in isolation:

- **Dev 1** implements all dataclasses, enums, and protocols in `maze.py`. Runs `pytest tests/test_maze.py` — all 27 tests must pass. No other module required.
- **Dev 2** implements `GameRepository` protocol and `JsonFileRepository` in `db.py`. Runs `pytest tests/test_db.py` — all 10 tests must pass. No other module required.
- **Dev 3** implements the serialization bridge (`_dict_to_state`, `_state_to_dict`) and game loop in `main.py`. Because `main.py` imports types from `maze.py`, **Dev 1 delivers the dataclass/protocol definitions first** — these are pure type definitions with no logic, so they can be committed as a thin initial PR before any behavior is implemented. For persistence, Dev 3 uses a `FakeRepository` (an in-memory stub defined in the test file) instead of the real `JsonFileRepository`. This lets Dev 3 run all Phase 1 tests without waiting for Dev 2.

### Phase 2: Integration

Once all three modules pass their individual test suites, the team runs the full test suite together:

```
pytest tests/
```

The **integration gate** is test **E-C1** (`test_full_pipeline_round_trip`) — the only test that wires all three real modules together through a real `JsonFileRepository` on disk. If E-C1 passes, the system works end-to-end.

### Delivery Order

```
1. Dev 1 commits maze.py type definitions (dataclasses + protocols, no logic)
        ↓
2. Dev 1, Dev 2, Dev 3 work in parallel
   ┌──────────────┬───────────────────┬─────────────────────────────┐
   │ Dev 1        │ Dev 2             │ Dev 3                       │
   │ maze.py      │ db.py             │ main.py                     │
   │ (algorithms, │ (JsonFileRepo,    │ (serialization bridge,      │
   │  generators) │  file I/O)        │  game loop, uses FakeRepo)  │
   └──────────────┴───────────────────┴─────────────────────────────┘
        ↓                 ↓                       ↓
3. Each passes their module tests independently
        ↓                 ↓                       ↓
4. Merge all → run full pytest suite → E-C1 (integration gate) passes
```

---

## Module 1: `maze.py` — Domain Logic

> **Test file:** `tests/test_maze.py`
>
> **Imports only from:** `maze.py`
>
> **No I/O, no filesystem, no JSON** — pure Python assertions.

### A. `Position` (frozen value object)

| ID | Test | Verify |
|---|---|---|
| M-A1 | `test_position_immutability` | Assigning `pos.row = 5` on a `Position` raises `dataclasses.FrozenInstanceError` |
| M-A2 | `test_position_equality` | `Position(0, 1) == Position(0, 1)` is `True` |
| M-A3 | `test_position_inequality` | `Position(0, 1) != Position(1, 0)` is `True` |
| M-A4 | `test_position_hashability` | `hash(Position(0, 1)) == hash(Position(0, 1))` is `True`; a `set` containing both has length 1 |
| M-A5 | `test_position_as_dict_key` | `Position` instances can be used as keys in a plain `dict` and retrieve the expected value |

### B. `Direction` (enum)

| ID | Test | Verify |
|---|---|---|
| M-B1 | `test_direction_members_exist` | `Direction.NORTH`, `Direction.SOUTH`, `Direction.EAST`, `Direction.WEST` are all accessible without error |
| M-B2 | `test_direction_members_distinct` | All four members have distinct `.value` attributes |

### C. `Question`

| ID | Test | Verify |
|---|---|---|
| M-C1 | `test_question_construction` | A `Question` can be constructed with `prompt`, `choices`, and `correct_index`; all attributes match the supplied values |
| M-C2 | `test_question_default_category` | When `category` is omitted, it defaults to `""` |
| M-C3 | `test_question_correct_index_in_bounds` | For a well-formed `Question`, `0 <= q.correct_index < len(q.choices)` is `True` |

### D. `Room`

| ID | Test | Verify |
|---|---|---|
| M-D1 | `test_room_defaults` | `Room(position=Position(0, 0))` has all boolean fields (`north_open`, `south_open`, `east_open`, `west_open`, `has_clog`, `is_entrance`, `is_exit`) equal to `False` |
| M-D2 | `test_room_wall_flags` | Setting `north_open=True` and `east_open=True` at construction; both are `True`, others remain `False` |
| M-D3 | `test_room_clog_flag` | A room constructed with `has_clog=True` reports `has_clog` as `True` |
| M-D4 | `test_room_entrance_exit_flags` | A room can be marked as entrance, exit, or both; flags reflect construction arguments |

### E. `Player`

| ID | Test | Verify |
|---|---|---|
| M-E1 | `test_player_construction` | `Player(name="Duke", position=Position(0, 0))` has `energy == 0` |
| M-E2 | `test_player_energy_default` | When `energy` is omitted, it defaults to `0` |
| M-E3 | `test_player_energy_negative` | Assigning `player.energy = -5` succeeds — the dataclass does not enforce a floor |

### F. `Maze`

| ID | Test | Verify |
|---|---|---|
| M-F1 | `test_maze_grid_dimensions` | `len(maze.grid) == maze.rows` and `len(maze.grid[0]) == maze.cols` |
| M-F2 | `test_maze_grid_access` | `maze.grid[r][c].position == Position(r, c)` for every cell |
| M-F3 | `test_maze_entrance_in_bounds` | `0 <= maze.entrance.row < maze.rows` and `0 <= maze.entrance.col < maze.cols` |
| M-F4 | `test_maze_exit_in_bounds` | `0 <= maze.exit_pos.row < maze.rows` and `0 <= maze.exit_pos.col < maze.cols` |

### G. `GameState`

| ID | Test | Verify |
|---|---|---|
| M-G1 | `test_game_state_construction` | `GameState(player=..., maze=...)` succeeds and holds the provided `Player` and `Maze` |
| M-G2 | `test_game_state_defaults` | `current_level == 1`, `total_levels == 3`, `clogs_cleared == 0`, `total_clogs == 0` when omitted |

### H. Protocol Conformance (structural subtyping)

> All domain protocols must be decorated `@runtime_checkable` for these tests to work with `isinstance`.

| ID | Test | Verify |
|---|---|---|
| M-H1 | `test_maze_generator_protocol` | A stub class with `def generate(self, rows: int, cols: int) -> Maze` passes `isinstance(stub, MazeGenerator)` |
| M-H2 | `test_solvability_checker_protocol` | A stub class with `def is_solvable(self, maze: Maze) -> bool` passes `isinstance(stub, SolvabilityChecker)` |
| M-H3 | `test_question_source_protocol` | A stub class with `def get_question(self) -> Question` passes `isinstance(stub, QuestionSource)` |
| M-H4 | `test_protocol_negative` | A class with no matching method fails `isinstance` for each of the three protocols |

---

## Module 2: `db.py` — Persistence

> **Test file:** `tests/test_db.py`
>
> **Imports only from:** `db.py`
>
> Uses pytest's `tmp_path` fixture for all file operations — no real filesystem side effects.

### A. Protocol Conformance

| ID | Test | Verify |
|---|---|---|
| D-A1 | `test_json_file_repository_satisfies_protocol` | `isinstance(JsonFileRepository(path), GameRepository)` is `True` (requires `@runtime_checkable` on `GameRepository`) |

### B. Save / Load Round-Trip (dict level)

| ID | Test | Verify |
|---|---|---|
| D-B1 | `test_save_load_flat_dict` | `save({"key": "value"})` then `load()` returns `{"key": "value"}` |
| D-B2 | `test_save_load_nested_dict` | A dict with nested dicts, lists, strings, ints, bools, and `None` survives a save/load round-trip with full equality |

### C. `exists()` Behavior

| ID | Test | Verify |
|---|---|---|
| D-C1 | `test_exists_false_before_save` | `exists()` returns `False` on a fresh `JsonFileRepository` |
| D-C2 | `test_exists_true_after_save` | After calling `save(data)`, `exists()` returns `True` |

### D. Overwrite Semantics

| ID | Test | Verify |
|---|---|---|
| D-D1 | `test_save_overwrites_previous` | `save(data_1)` then `save(data_2)` then `load()` returns `data_2`, not `data_1` |

### E. Corrupt File Handling

| ID | Test | Verify |
|---|---|---|
| D-E1 | `test_load_invalid_json` | Writing `"not {valid json"` to the save path then calling `load()` raises `json.JSONDecodeError` |
| D-E2 | `test_load_empty_file` | Writing an empty string to the save path then calling `load()` raises `json.JSONDecodeError` |

### F. Missing File Handling

| ID | Test | Verify |
|---|---|---|
| D-F1 | `test_load_missing_file` | Calling `load()` when no file exists at the path raises `FileNotFoundError` |

### G. Import Isolation

| ID | Test | Verify |
|---|---|---|
| D-G1 | `test_db_does_not_import_maze` | Parse `db.py` with `ast.parse`; walk all `Import` and `ImportFrom` nodes; none reference `maze` |

---

## Module 3: `main.py` — Engine (Mapping & Orchestration)

> **Test file:** `tests/test_main.py`
>
> **Phase 1 imports:** `maze.py` and `main.py` only (Dev 3 can run these before `db.py` is delivered)
>
> **Phase 2 imports:** adds `db.py` for the full integration test (E-C1)

### Stubs for Independent Development

Dev 3 uses this in-memory stub instead of `JsonFileRepository` during Phase 1. It satisfies the `GameRepository` protocol without touching the filesystem or importing `db.py`:

```python
class FakeRepository:
    """In-memory GameRepository stub for Phase 1 testing."""
    def __init__(self):
        self._data = None

    def save(self, data: dict[str, Any]) -> None:
        self._data = json.loads(json.dumps(data))  # deep copy via JSON round-trip

    def load(self) -> dict[str, Any]:
        if self._data is None:
            raise FileNotFoundError("No save data")
        return json.loads(json.dumps(self._data))

    def exists(self) -> bool:
        return self._data is not None
```

The `json.loads(json.dumps(...))` round-trip inside `FakeRepository` is intentional — it simulates the same serialization boundary that `JsonFileRepository` creates on disk, so any type that sneaks through `asdict()` unconverted (e.g., an enum value) will fail here the same way it would fail in production.

### Shared Test Fixture

Tests in this section rely on a helper that builds a complete, valid `GameState`:

```python
def make_game_state() -> GameState:
    """Build a minimal 2x2 maze with one clog for testing."""
    rooms = [
        [
            Room(position=Position(r, c), east_open=(c == 0), south_open=(r == 0))
            for c in range(2)
        ]
        for r in range(2)
    ]
    rooms[0][0].is_entrance = True
    rooms[1][1].is_exit = True
    rooms[0][1].has_clog = True
    maze = Maze(rows=2, cols=2, grid=rooms,
                entrance=Position(0, 0), exit_pos=Position(1, 1))
    player = Player(name="Duke", position=Position(0, 0), energy=30)
    return GameState(player=player, maze=maze,
                     current_level=2, total_levels=3, clogs_cleared=1, total_clogs=3)
```

### Phase 1 Tests (no `db.py` required)

#### Stub Validation

| ID | Test | Verify |
|---|---|---|
| E-S1 | `test_fake_repository_save_load` | `FakeRepository.save(data)` then `load()` returns an equal dict |
| E-S2 | `test_fake_repository_exists` | `exists()` returns `False` before save, `True` after |
| E-S3 | `test_fake_repository_rejects_non_serializable` | `FakeRepository.save({"bad": Position(0, 0)})` raises `TypeError` — confirms the stub catches the same serialization errors as the real repository |

These tests verify that `FakeRepository` is a faithful stand-in for `JsonFileRepository`, so all Phase 1 results remain valid after integration.

### A. Serialization: `GameState` to dict

| ID | Test | Verify |
|---|---|---|
| E-A1 | `test_asdict_is_json_serializable` | `json.dumps(dataclasses.asdict(make_game_state()))` does not raise |
| E-A2 | `test_asdict_position_structure` | The `"position"` key inside the first room of the serialized grid is `{"row": 0, "col": 0}` |
| E-A3 | `test_asdict_preserves_room_booleans` | The room at `[0][1]` in the serialized grid has `"has_clog": True` and `"east_open": False` |

### B. Deserialization: dict to `GameState`

| ID | Test | Verify |
|---|---|---|
| E-B1 | `test_round_trip_player` | After `GameState` -> `asdict` -> `_dict_to_state`, the reconstructed `player.name`, `player.position`, and `player.energy` match the original |
| E-B2 | `test_round_trip_maze_dimensions` | After round-trip, `maze.rows` and `maze.cols` match the original |
| E-B3 | `test_round_trip_grid_contents` | After round-trip, every `Room` in the grid has the same `position`, wall flags, `has_clog`, `is_entrance`, and `is_exit` as the original |
| E-B4 | `test_round_trip_maze_entrance_exit` | After round-trip, `maze.entrance` and `maze.exit_pos` match the original |
| E-B5 | `test_round_trip_game_metadata` | After round-trip, `current_level`, `total_levels`, `clogs_cleared`, and `total_clogs` match the original |

### C. Full Pipeline Round-Trip

| ID | Test | Verify |
|---|---|---|
| E-C0 | `test_pipeline_with_fake_repository` | **Phase 1.** `GameState` -> `asdict` -> `FakeRepository.save` -> `FakeRepository.load` -> `_dict_to_state` produces an equivalent `GameState`. Dev 3 can run this without `db.py` |
| E-C1 | `test_full_pipeline_round_trip` | **Phase 2 (integration gate).** Same pipeline but using a real `JsonFileRepository` on a `tmp_path` file. Requires `db.py`. This is the single most critical acceptance test — if it passes, the serialization contract across all three modules is fulfilled |

### D. Corrupt Save File Recovery

| ID | Test | Verify |
|---|---|---|
| E-D1 | `test_corrupt_save_falls_back_to_new_game` | Write invalid JSON to the save path. When the engine attempts to load, it catches `json.JSONDecodeError` and returns a fresh `GameState` instead of crashing |

### E. Missing Keys Resilience

| ID | Test | Verify |
|---|---|---|
| E-E1 | `test_missing_optional_keys_use_defaults` | Call `_dict_to_state` with a dict that omits `current_level`, `total_levels`, `clogs_cleared`, and `total_clogs`. The result has `current_level == 1`, `total_levels == 3`, `clogs_cleared == 0`, `total_clogs == 0` — no `KeyError` raised |

### F. Import Isolation

| ID | Test | Verify |
|---|---|---|
| E-F1 | `test_maze_does_not_import_db` | Parse `maze.py` with `ast.parse`; walk all `Import` and `ImportFrom` nodes; none reference `db` |

---

## Gameplay Behavior Tests

> **Test file:** `tests/test_gameplay.py`
>
> **Imports from:** `maze.py` (domain types + protocols) and `main.py` (engine logic)
>
> These tests verify the **game rules** described in [game_concept.md](game_concept.md) Section B. While the module tests above prove data shapes and serialization contracts, these tests prove the game actually *works* — that answering a question clears a clog, that the phase beam costs energy, and that the victory condition triggers.

### A. Maze Generation & Structural Validity

| ID | Test | Verify |
|---|---|---|
| G-A1 | `test_generated_maze_has_valid_grid` | A `MazeGenerator` implementation produces a `Maze` where `len(grid) == rows`, `len(grid[0]) == cols`, and every cell's `position` matches its index |
| G-A2 | `test_generated_maze_is_solvable` | Generate a maze, run `SolvabilityChecker.is_solvable()` — returns `True`. If `False`, regenerate (up to a retry limit) and confirm at least one generation succeeds |
| G-A3 | `test_generated_maze_wall_consistency` | For every adjacent pair of rooms in a generated maze, wall openings are symmetric: if room `(r, c)` has `east_open=True` then `(r, c+1)` has `west_open=True`, and if `(r, c)` has `south_open=True` then `(r+1, c)` has `north_open=True` |
| G-A4 | `test_generated_maze_has_clogs` | A generated maze contains at least one room with `has_clog=True` |

### B. Movement

| ID | Test | Verify |
|---|---|---|
| G-B1 | `test_move_through_open_passage` | Player at `(0, 0)` with `east_open=True` moves east; player position becomes `(0, 1)` |
| G-B2 | `test_move_blocked_by_wall` | Player at `(0, 0)` with `east_open=False` attempts to move east; player position remains `(0, 0)` |
| G-B3 | `test_move_blocked_by_clog` | Player at `(0, 0)` with `east_open=True` but room `(0, 1)` has `has_clog=True`; moving east without interacting is blocked, player stays at `(0, 0)` |
| G-B4 | `test_move_out_of_bounds_blocked` | Player at `(0, 0)` attempts to move north (out of grid); position remains `(0, 0)` |

### C. Clog Interaction & Questions

| ID | Test | Verify |
|---|---|---|
| G-C1 | `test_interact_with_clog_receives_question` | Player adjacent to a clogged room and choosing to interact triggers `QuestionSource.get_question()`; a `Question` is returned with a non-empty `prompt` and at least 2 `choices` |
| G-C2 | `test_correct_answer_clears_clog` | Player answers correctly (`answer_index == question.correct_index`); the room's `has_clog` becomes `False` and `clogs_cleared` increments by 1 |
| G-C3 | `test_correct_answer_grants_energy` | After a correct answer, `player.energy` increases by 10 |
| G-C4 | `test_incorrect_answer_clog_persists` | Player answers incorrectly; the room's `has_clog` remains `True` and `clogs_cleared` is unchanged |
| G-C5 | `test_incorrect_answer_costs_energy` | After an incorrect answer, `player.energy` decreases by 5 |
| G-C6 | `test_incorrect_answer_new_question` | After an incorrect answer, the next interaction with the same clog calls `get_question()` again and may return a different `Question` |

### D. Phase Beam

| ID | Test | Verify |
|---|---|---|
| G-D1 | `test_phase_beam_clears_clog` | Player with `energy >= 50` activates phase beam on a clogged room; `has_clog` becomes `False` and `clogs_cleared` increments by 1 |
| G-D2 | `test_phase_beam_costs_50_energy` | After phase beam activation, `player.energy` decreases by exactly 50 |
| G-D3 | `test_phase_beam_denied_insufficient_energy` | Player with `energy == 49` attempts phase beam; activation is denied, `has_clog` remains `True`, energy is unchanged |
| G-D4 | `test_phase_beam_allowed_at_exactly_50` | Player with `energy == 50` activates phase beam; succeeds, energy becomes 0 |

### E. Level Completion

| ID | Test | Verify |
|---|---|---|
| G-E1 | `test_level_complete_when_blocking_clogs_cleared` | All rooms with `has_clog=True` that block the path from entrance to exit are cleared; the level-complete condition triggers |
| G-E2 | `test_perfect_level_bonus` | If all clogs are cleared without any incorrect answers, player receives +25 energy bonus |
| G-E3 | `test_imperfect_level_bonus` | If at least one incorrect answer was given during the level, player receives +15 energy bonus instead of +25 |
| G-E4 | `test_level_advance_increments_current_level` | After level completion, `current_level` increments by 1 and a new maze is generated for the next level |

### F. Victory Condition

| ID | Test | Verify |
|---|---|---|
| G-F1 | `test_victory_after_final_level` | When `current_level > total_levels` after completing the last level, the game-victory condition triggers |
| G-F2 | `test_no_victory_before_final_level` | When `current_level <= total_levels`, the game-victory condition does not trigger even if all clogs on the current level are cleared |

---

## Assembly Sequence

When all modules are ready to merge, follow this sequence to confirm the system works as a whole.

### Step 1: Verify Each Module in Isolation

```bash
pytest tests/test_maze.py     # 27 tests — Dev 1
pytest tests/test_db.py       # 10 tests — Dev 2
pytest tests/test_main.py -k "not full_pipeline_round_trip"  # 15 Phase 1 tests — Dev 3
```

All three commands must pass independently before proceeding. If any fail, the owning developer fixes their module — no cross-module debugging needed.

### Step 2: Integration

```bash
pytest tests/test_main.py -k "full_pipeline_round_trip"  # E-C1 only
```

This wires the real `JsonFileRepository` from `db.py` to the real dataclasses from `maze.py` through the real `_dict_to_state` bridge in `main.py`. If it passes, the system is integrated.

### Step 3: Full Suite

```bash
pytest tests/
```

Run the complete suite to confirm nothing regressed. All 77 tests must pass.

### Troubleshooting Integration Failures

If E-C1 fails but all individual module tests pass, the problem is at a module boundary. Likely causes:

| Symptom | Likely Cause | Who Investigates |
|---|---|---|
| `TypeError` during `json.dumps` | A domain type survived `asdict()` unconverted (e.g., an enum value as a dict key) | Dev 1 + Dev 3 |
| `KeyError` during `_dict_to_state` | Field name mismatch between `asdict()` output and reconstruction logic | Dev 3 |
| Data mismatch after round-trip | `JsonFileRepository` alters types (e.g., int keys become strings) | Dev 2 + Dev 3 |

---

## Summary Matrix

| Module | Test Count | Phase | Key Risk Mitigated |
|---|---|---|---|
| `maze.py` | 27 | 1 | Dataclass contracts, value object semantics, structural subtyping |
| `db.py` | 10 | 1 | Persistence reliability, corrupt/missing file handling, import isolation |
| `main.py` (stubs) | 3 | 1 | FakeRepository fidelity, early pipeline validation without `db.py` |
| `main.py` (domain) | 12 | 1 | Serialization fidelity, graceful degradation, missing key resilience |
| `main.py` (integration) | 1 | 2 | Full pipeline integrity across all three real modules |
| Gameplay behavior | 24 | 2 | Game rules, energy economy, movement, clog interaction, phase beam, level/victory conditions |
| **Total** | **77** | | |

---

## Guiding Principles

- **Module isolation:** `maze.py` tests import nothing from `db.py` and vice versa. Only `main.py` tests bridge both.
- **Protocol-first:** Conformance tests use `isinstance` with `@runtime_checkable` protocols and lightweight stubs, proving any compliant implementation will integrate.
- **Stubs before integration:** Dev 3 uses `FakeRepository` (a JSON-round-tripping in-memory stub) during Phase 1, then swaps to the real `JsonFileRepository` at integration. The stub is validated by its own tests (E-S1 through E-S3) to ensure it catches the same errors as the real thing.
- **Round-trip as the acceptance gate:** Test E-C1 (full pipeline round-trip) is the single highest-priority integration test. If it passes, the serialization contract is fulfilled end-to-end.
- **Defensive edge cases:** Corrupt files, empty files, missing files, and missing dict keys are tested explicitly — per the game concept's failure state: *"Save file is corrupted -> Game catches exception -> Loads default new game."*
- **Troubleshooting is scoped:** The integration troubleshooting table maps symptoms to responsible developers, so no one wastes time debugging code they don't own.
