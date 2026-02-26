# RUNBOOK.md — Trivia Maze Walking Skeleton

## 1. Purpose

This runbook defines the module boundary rules and the critical (P0) acceptance tests for the Trivia Maze walking skeleton. The project is not releasable until all P0 tests pass and all dependency rules are verified.

---

## 2. Planned Implementation Targets

This repository currently contains design docs. During implementation, the target files are:

- `maze.py`
- `db.py`
- `main.py`
- `tests/test_maze_contract.py`
- `tests/test_repo_contract.py`
- `tests/test_engine_integration.py`
- `tests/test_module_isolation.py`

---

## 3. Non-Negotiable Dependency Rules

| Rule | Requirement |
|---|---|
| Domain isolation | `maze.py` imports no project modules. It must not import `db` or `main`. |
| Persistence isolation | `db.py` imports no project modules. It must not import `maze` or `main`. |
| Engine ownership | `main.py` is the only module allowed to import other project modules. |
| I/O boundary | Only `main.py` may use `print()` and `input()` for CLI interaction. |
| Domain purity | `maze.py` returns data only (no user I/O, no persistence I/O). |
| Persistence contract | `db.py` stores/loads JSON-safe primitives only. |
| Serialization boundary | `main.py` owns dataclass <-> dict conversion. |
| No God Objects | Keep responsibilities split across `maze.py`, `db.py`, and `main.py`. |

---

## 4. P0 (Critical) Tests — Required for "Done"

All P0 tests must pass for the project to be considered releasable. No exceptions.

### 4.1 Domain P0 (`tests/test_maze_contract.py`)

| ID | Test | Critical expectation |
|---|---|---|
| P0-M1 | `test_create_maze_is_solvable` | Generated maze must be solvable from entrance to exit. |
| P0-M2 | `test_create_maze_has_entrance_and_exit` | Exactly one entrance and one exit must exist. |
| P0-M3 | `test_move_valid_direction` | Valid movement updates position through `MoveResult`. |
| P0-M4 | `test_move_into_wall` | Invalid wall movement is blocked and returns failure result. |
| P0-M5 | `test_correct_answer_clears_clog` | Correct answer clears clog and applies expected reward. |
| P0-M6 | `test_wrong_answer_keeps_clog` | Incorrect answer keeps clog and applies expected penalty. |
| P0-M7 | `test_is_solved_true_all_cleared` | Win condition is true only after required clogs are cleared. |

### 4.2 Persistence P0 (`tests/test_repo_contract.py`)

| ID | Test | Critical expectation |
|---|---|---|
| P0-R1 | `test_save_returns_true` | Save operation succeeds on valid state. |
| P0-R2 | `test_save_then_load_matches` | Save/load round-trip preserves state exactly. |
| P0-R3 | `test_load_missing_file` | Missing file is handled safely (`None`), no crash. |
| P0-R4 | `test_load_corrupted_json` | Corrupted save is handled safely (`None`), no crash. |

### 4.3 Integration P0 (`tests/test_engine_integration.py`)

| ID | Test | Critical expectation |
|---|---|---|
| P0-I1 | `test_new_game_initializes_state` | Game can boot into a valid initial state. |
| P0-I2 | `test_save_and_load_preserves_state` | End-to-end save/load works across modules. |
| P0-I3 | `test_gamestate_to_dict_round_trip` | Dataclass-to-dict boundary crossing is lossless. |
| P0-I4 | `test_win_condition` | Full wired system can reach a win state. |

### 4.4 Isolation P0 (`tests/test_module_isolation.py`)

| ID | Test | Critical expectation |
|---|---|---|
| P0-S1 | `test_maze_imports_nothing` | Domain module imports are isolated correctly. |
| P0-S2 | `test_db_imports_nothing` | Persistence module imports are isolated correctly. |
| P0-S3 | `test_maze_no_print` | Domain module does not perform user I/O. |
| P0-S4 | `test_db_no_print` | Persistence module does not perform user I/O. |

**Total P0 tests:** 19

---

## 5. Validation Commands

Run critical checks as features are implemented:

```bash
pytest tests/test_module_isolation.py -v
pytest tests/test_maze_contract.py -v
pytest tests/test_repo_contract.py -v
pytest tests/test_engine_integration.py -v
```

Final gate before merge:

```bash
pytest tests/ -v
```

---

## 6. Definition of Done

The walking skeleton is releasable when all are true:

- all 19 P0 tests pass
- `tests/test_engine_integration.py` exists and runs via `pytest`
- dependency rules are not violated
- game boots from `main.py`, supports movement + trivia interaction, and save/load works
