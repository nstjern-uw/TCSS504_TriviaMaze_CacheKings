# interface-tests.md — Contract Test Specifications

## How to Run

```bash
pytest tests/ -v
```

| Test File | Role | Can Run Standalone? |
|---|---|---|
| `tests/test_maze_contract.py` | Domain Owner (`maze.py`) | Yes |
| `tests/test_repo_contract.py` | Persistence Owner (`db.py`) | Yes |
| `tests/test_engine_integration.py` | Engine Owner (`main.py`) | No — requires `maze.py` and `db.py` |
| `tests/test_module_isolation.py` | All / QA Lead | Yes |

---

## 1. Maze Contract Tests (`test_maze_contract.py`)

### create_maze

| Test | Description | Expected |
|---|---|---|
| `test_create_maze_returns_maze` | `create_maze(3, 3, seed=42)` returns a `Maze` with correct `rows`, `cols` | `maze.rows == 3`, `maze.cols == 3` |
| `test_create_maze_has_entrance_and_exit` | Generated maze has exactly one entrance and one exit | `is_entrance` count == 1, `is_exit` count == 1 |
| `test_create_maze_is_solvable` | DFS from entrance to exit succeeds | `check_solvability(maze, entrance, exit_pos)` returns `True` |
| `test_create_maze_has_clogs` | At least one clog exists on the path | Any room in grid has `has_clog == True` |
| `test_create_maze_deterministic_with_seed` | Same seed produces identical maze | `create_maze(3, 3, seed=42) == create_maze(3, 3, seed=42)` |
| `test_create_maze_invalid_size` | `create_maze(1, 1)` raises `ValueError` | `pytest.raises(ValueError)` |
| `test_create_maze_wall_symmetry` | If room(0,0) has `walls["south"] == False`, then room(1,0) has `walls["north"] == False` | Symmetry holds for all adjacent pairs |

### move_player

| Test | Description | Expected |
|---|---|---|
| `test_move_valid_direction` | Move south from (0,0) where no wall exists | `MoveResult(success=True, new_position=Position(1,0))` |
| `test_move_into_wall` | Move into a direction with a wall | `MoveResult(success=False, new_position=None)` |
| `test_move_out_of_bounds` | Move north from row 0 | `MoveResult(success=False, new_position=None)` |
| `test_move_does_not_mutate_player` | Player object unchanged after call | `player.position` is same before and after |

### get_room / has_clog

| Test | Description | Expected |
|---|---|---|
| `test_get_room_valid` | `get_room(maze, Position(0,0))` returns a `Room` | Room's `position == Position(0,0)` |
| `test_get_room_invalid` | `get_room(maze, Position(99,99))` | Raises `ValueError` |
| `test_has_clog_true` | Check a room that was generated with a clog | Returns `True` |
| `test_has_clog_false` | Check entrance room (never has a clog) | Returns `False` |

### attempt_answer

| Test | Description | Expected |
|---|---|---|
| `test_correct_answer_clears_clog` | Answer correctly at a clog room | `AnswerResult(correct=True, clog_cleared=True, energy_change=10, ...)` |
| `test_correct_answer_updates_room` | After correct answer, `has_clog(maze, position)` is `False` | Room's clog is cleared |
| `test_wrong_answer_keeps_clog` | Answer incorrectly at a clog room | `AnswerResult(correct=False, clog_cleared=False, energy_change=-5, ...)` |
| `test_answer_no_clog_room` | `attempt_answer` on a room without a clog | `AnswerResult(correct=False, clog_cleared=False, energy_change=0, ...)` |

### is_solved / check_solvability

| Test | Description | Expected |
|---|---|---|
| `test_is_solved_false_with_clogs` | Fresh maze with clogs remaining | Returns `False` |
| `test_is_solved_true_all_cleared` | Clear all clogs, then check | Returns `True` |
| `test_solvability_true` | DFS on a solvable maze | Returns `True` |
| `test_solvability_false` | Manually construct an unsolvable maze (all walls) | Returns `False` |

### get_question

| Test | Description | Expected |
|---|---|---|
| `test_question_has_required_fields` | `get_question()` returns a `Question` | `prompt` is non-empty, `len(choices) >= 2`, `correct_answer in choices` |
| `test_question_deterministic_with_seed` | Same seed returns same question | `get_question(seed=42) == get_question(seed=42)` |

### phase_beam

| Test | Description | Expected |
|---|---|---|
| `test_phase_beam_sufficient_energy` | Player has >= 50 energy, uses phase beam at clog | Clog cleared, `energy_change == -50` |
| `test_phase_beam_insufficient_energy` | Player has < 50 energy, attempts phase beam | Attempt rejected, no clog cleared, no energy change |

---

## 2. Repository Contract Tests (`test_repo_contract.py`)

All tests use a temporary directory (`tmp_path` fixture) to avoid touching real save files.

### save_game / load_game round-trip

| Test | Description | Expected |
|---|---|---|
| `test_save_returns_true` | Save a valid dict | Returns `True` |
| `test_save_then_load_matches` | Save a dict, load it back | Loaded dict == original dict |
| `test_load_missing_file` | Load from a path that doesn't exist | Returns `None` |
| `test_load_corrupted_json` | Write garbage text to a file, then load | Returns `None` |
| `test_save_non_serializable` | Save a dict containing a non-JSON-safe object | Returns `False` |

### delete_save / save_exists

| Test | Description | Expected |
|---|---|---|
| `test_delete_existing_save` | Save a file, then delete it | Returns `True`, file no longer exists |
| `test_delete_nonexistent` | Delete a file that doesn't exist | Returns `False` |
| `test_save_exists_true` | Save a file, check existence | Returns `True` |
| `test_save_exists_false` | Check a path with no file | Returns `False` |

---

## 3. Engine Integration Tests (`test_engine_integration.py`)

These tests require both `maze.py` and `db.py` to be present. They verify that `main.py` correctly wires the modules together.

### Game lifecycle

| Test | Description | Expected |
|---|---|---|
| `test_new_game_initializes_state` | `start_new_game()` creates a valid maze and player | Player at entrance, energy == 100, maze is solvable |
| `test_process_move_command` | `process_command("move north")` on a valid move | Player position updates, returns `GameStatus.IN_PROGRESS` |
| `test_process_invalid_command` | `process_command("fly")` | Returns `GameStatus.IN_PROGRESS` (help printed) |
| `test_process_quit_command` | `process_command("quit")` | Returns `GameStatus.QUIT` |

### Save/Load round-trip

| Test | Description | Expected |
|---|---|---|
| `test_save_and_load_preserves_state` | Start game, make moves, save, load | All state matches: player position, energy, maze grid, clogs |
| `test_load_with_no_save` | `load_game()` when no save file exists | Returns `False` |

### Boundary crossing

| Test | Description | Expected |
|---|---|---|
| `test_gamestate_to_dict_round_trip` | `from_dict(asdict(game_state)) == game_state` | All fields match including nested Position objects |
| `test_enum_serialization_round_trip` | `GameStatus(GameStatus.IN_PROGRESS.value) == GameStatus.IN_PROGRESS` | Enum survives conversion |

### Win condition

| Test | Description | Expected |
|---|---|---|
| `test_win_condition` | Clear all clogs, verify game status | `is_solved()` returns `True`, status becomes `GameStatus.WON` |

---

## 4. Module Isolation Tests (`test_module_isolation.py`)

These can be run statically or as simple import/source checks.

| Test | Description | Expected |
|---|---|---|
| `test_maze_imports_nothing` | Inspect `maze.py` source for `import db` or `import main` | No project imports found |
| `test_db_imports_nothing` | Inspect `db.py` source for `import maze` or `import main` | No project imports found |
| `test_maze_no_print` | Inspect `maze.py` source for `print(` | No print calls found |
| `test_db_no_print` | Inspect `db.py` source for `print(` | No print calls found |
