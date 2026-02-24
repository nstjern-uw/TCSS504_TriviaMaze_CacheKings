# interface-tests.md
## Quiz Maze Skeleton - Liam's Version

## Purpose
Defines the contract tests each module must pass before merge so teammates can build in parallel and still integrate cleanly.

## Test Files (recommended)
- `tests/test_maze_contract.py`
- `tests/test_repo_contract.py`
- `tests/test_engine_integration.py`

---

## A) `maze.py` Contract Tests (Domain Logic)

### `new_game()` / initial state
- Creates valid fixed 3x3 state
- `player_pos == (0,0)`
- `required_clog_pos == (1,1)`
- `exit_pos == (2,2)`
- `required_clog_cleared == False`
- `energy == 100`
- `move_count == 0`
- `is_finished == False`

### Movement rules
- `w/a/s/d` mapping is handled by engine, but domain movement accepts `N/S/E/W`
- Out of bounds returns `BLOCKED_BOUNDS`
- Wall move returns `BLOCKED_WALL`
- Uncleared clog tile returns `BLOCKED_CLOG`
- Valid move returns `MOVED`
- Valid move updates position and increments move count

### Clog interaction rules
- `interact_with_clog(state)` returns:
  - `TOO_FAR` if not orthogonally adjacent
  - `READY_FOR_QUESTION` if adjacent and clog uncleared
  - `ALREADY_CLEARED` if clog already cleared

### Trivia resolution rules
- `resolve_clog_trivia_answer(state, True)`
  - clears clog
  - `energy += 10`
- `resolve_clog_trivia_answer(state, False)`
  - clog remains
  - `energy -= 5`

### Win rule
- Player wins only when:
  - clog is cleared, and
  - player reaches exit

### Isolation checks
- `maze.py` does not import `db.py` or `main.py`
- `maze.py` does not use `print()` / `input()`

---

## B) `db.py` Contract Tests (Persistence)

### Save/load behavior
- `save(slot, snapshot)` writes JSON-safe dict
- `load(slot)` returns same dict after save (round trip)
- Missing save returns `None`
- Overwrite same slot is allowed

### Corrupt save behavior
- Corrupted JSON is handled safely (recommended: raise `ValueError`)

### Boundary checks
- `db.py` stores JSON-safe primitives only
- `db.py` does not import `maze.py` or `main.py`

---

## C) `main.py` Integration Tests (Engine / Wiring)

### Boot and loop
- Engine starts CLI loop without crashing
- Invalid command does not crash loop

### WASD command handling
- `w/a/s/d` map to north/west/south/east
- Movement results are shown/handled

### Interact + trivia flow
- `i` when too far does not start trivia
- `i` when adjacent starts Mario multiple-choice trivia
- Correct answer clears clog and updates energy `+10`
- Wrong answer keeps clog and updates energy `-5`

### Clog blocking behavior through engine
- Player cannot move into clog tile before clear
- Player can move into clog tile after correct trivia answer

### Win path integration
- Happy path works:
  - move adjacent
  - interact
  - answer correctly
  - move to exit
- Win triggers only after clog clear + exit

### Save/load integration
- `save` writes snapshot
- `load` restores state (position, energy, clog cleared state, move_count)
- Missing/corrupt save handled safely by engine (no crash)

---

## P0 Acceptance Tests (Release-Critical)
- CLI boots
- WASD movement works
- Bounds/walls block correctly
- Clog blocks until cleared
- `i` adjacency rule works
- Trivia correct/wrong outcomes work
- Energy updates correctly (`+10` / `-5`)
- Win requires clog clear + exit
- Save/load works
- Corrupt save handled safely
- Module isolation rules are respected