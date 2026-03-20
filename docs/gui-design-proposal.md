Final Maze with GUI — Design Proposal
=====================================

**Based on:** Nick's Pygame Maze Renderer design doc (`docs/3d-design-nick.md`, PR #22)  
**Date:** March 9, 2026  
**Submission:** GitHub repository link (must show PR history)

---

1. Overview
-----------

*From Nick's design doc.*

This document describes a plan to render the Nuovo Fresco Pipe Network maze using Pygame, replacing the current ASCII-based CLI view (`view.py`) with a graphical tile-based renderer. The existing separation of concerns makes this a clean view-layer swap — `maze.py`, `db.py`, and the core `GameEngine` logic in `main.py` remain unchanged.

This proposal extends Nick's design with project-level concerns: engine API, team workflow, maze/database stability, documentation, and integration verification.

---

2. Architecture Impact
----------------------

*From Nick's design doc.*

| Module          | Changes Required | Rationale                                                                                      |
|-----------------|-----------------|------------------------------------------------------------------------------------------------|
| `maze.py`       | None            | Pure domain logic. Already produces `SectionVisibility` grids — ideal for a graphical view.   |
| `db.py`         | None            | Persistence is I/O-agnostic.                                                                  |
| `view.py`       | None            | CLI mode remains available.                                                                   |
| `pygame_view.py`| **New file**    | Implements the same public interface as `PipeView`, drawing to a Pygame surface instead.      |
| `main.py`       | **Modified**    | Adds a `run_pygame()` loop and a `_key_to_command()` mapper. `GameEngine.__init__` accepts either view. |

### 2.1 Dependency graph

```text
main.py ──imports──▶ maze.py   (domain logic, pure data)
│
├──imports──▶ db.py            (persistence, SQLModel)
│
└──imports──▶ pygame_view.py OR view.py   (presentation)
```

`pygame_view.py` must NOT import `maze`, `db`, or `main`. It receives plain data (visibility grids, strings, integers) and renders it — identical boundary rules to `view.py`.

### 2.2 New dependency

Add to `requirements.txt`:

```text
pygame>=2.5.0
```

---

3. `PygameView` design
----------------------

*From Nick's design doc.*

### 3.1 Initialization

- `PygameView.__init__(rows, cols)` creates the Pygame window.
- Window dimensions: `cols * TILE_SIZE` wide, `rows * TILE_SIZE + HUD_HEIGHT` tall.
- Constants: `TILE_SIZE = 80`, `WALL_THICKNESS = 4`, `HUD_HEIGHT = 120`.

### 3.2 Public interface (mirrors `PipeView`)

Methods the engine expects:

| Method                                                    | Purpose                                                     |
|-----------------------------------------------------------|-------------------------------------------------------------|
| `render_map(vis_grid, rows, cols, entry_valve, exit_drain)` | Draw the tile grid from `SectionVisibility` data           |
| `render_status(row, col, pressure, clogs_cleared, level)`  | Draw the HUD bar at the bottom of the window               |
| `render_question(prompt, choices)`                          | Draw a semi-transparent overlay with the trivia question   |
| `render_message(msg)`                                      | Display a transient message line                           |
| `render_welcome()`                                         | Splash screen at game start                                |
| `render_help()`                                            | Command reference overlay                                  |

### 3.3 Tile rendering (`render_map`)

Each `SectionVisibility` cell maps to a tile:

- **Fogged** (`is_visible=False` and `is_visited=False`):  
  Filled with a dark fog color.
- **Visible / visited**:  
  Filled with a floor color. Walls are drawn as thick lines on edges where `open_directions` does NOT include that direction.
- **Center sprites**:
  - `is_current=True` → green circle (player)
  - `has_clog=True` → red square (clog)
  - Entry valve position → blue upward triangle
  - Exit drain position → gold downward triangle
  - `is_visited=True` → small dot (breadcrumb)
  - `is_visible=True` and not visited → hollow circle

### 3.4 Color palette

```text
Background:   (20, 20, 30)
Floor:        (60, 70, 90)
Walls:        (140, 140, 160)
Fog:          (30, 30, 40)
Player:       (0, 220, 120)
Clog:         (220, 60, 60)
Visited:      (50, 60, 75)
Entry Valve:  (80, 200, 255)
Exit Drain:   (255, 200, 50)
```

### 3.5 Question overlay (`render_question`)

When `EnginePhase.BLOCKED`:

- Draw a semi-transparent dark overlay over the maze.
- Render:
  - Question prompt text
  - Four choices labeled 1–4 (mapped to `a`/`b`/`c`/`d` internally)
  - A "blast" hint if pressure ≥ 50

### 3.6 HUD (`render_status`)

Drawn in the bottom `HUD_HEIGHT` pixels:

- Current coordinates
- Pressure gauge
- Clogs cleared
- Current level

---

4. Game loop and engine API changes (`main.py`)
----------------------------------------------

### 4.1 `run_pygame()`  *(from Nick's design doc)*

Event-driven loop:

1. Pump `pygame.event.get()` each frame.
2. Map `KEYDOWN` events to command strings via `_key_to_command()`.
3. Call `process_command()` (existing engine method).
4. Re-render map, status, and question overlay each frame.
5. Call `pygame.display.flip()` and tick at 30 FPS.

### 4.2 `_key_to_command(key)`  *(from Nick's design doc)*

Pure mapping, no side effects:

| Key               | Command  |
|-------------------|----------|
| Arrow Up / W      | `"north"`|
| Arrow Down / S    | `"south"`|
| Arrow Left / A    | `"west"` |
| Arrow Right / D   | `"east"` |
| 1 / 2 / 3 / 4     | `"a"` / `"b"` / `"c"` / `"d"` |
| B                 | `"blast"`|
| Escape            | `"quit"` |
| F5                | `"save"` |
| F9                | `"load"` |

### 4.3 Entry point  *(from Nick's design doc)*

```python
if __name__ == "__main__":
    import sys
    if "--pygame" in sys.argv:
        from pygame_view import PygameView
        view = PygameView(DEFAULT_MAZE_ROWS, DEFAULT_MAZE_COLS)
        engine = GameEngine(view=view)
        engine.run_pygame()
    else:
        engine = GameEngine()
        engine.run()
```

### 4.4 `get_display_state()` (engine driver API)

To keep the view layer from reaching into private engine fields (`self._state`, `self._phase`, `self._current_question`), the engine exposes a single method that bundles everything the view needs:

```python
def get_display_state(self) -> dict | None:
    """Return everything the view layer needs to render one frame."""
    if self._state is None:
        return None

    vis_map = get_visibility_map(
        self._state.pipe_network,
        self._state.player.position,
        self._state.visited_positions,
    )

    return {
        "vis_grid": vis_map,
        "rows": self._state.pipe_network.rows,
        "cols": self._state.pipe_network.cols,
        "entry_valve": self._state.pipe_network.entry_valve,
        "exit_drain": self._state.pipe_network.exit_drain,
        "player_row": self._state.player.position.row,
        "player_col": self._state.player.position.col,
        "pressure": self._state.player.pressure,
        "clogs_cleared": self._state.player.clogs_cleared,
        "level": self._state.player.current_level,
        "phase": self._phase.value,
        "status": self._state.status.value,
        "question": {
            "prompt": self._current_question.prompt,
            "choices": self._current_question.choices,
        } if self._current_question else None,
    }
```

`run_pygame()` calls `get_display_state()` once per frame and passes its fields into `render_map()`, `render_status()`, and `render_question()`. Nick’s rendering design stays exactly the same; this simply centralizes the data source and keeps the view decoupled from engine internals.

---

5. Mock engine for parallel development
---------------------------------------

Only needed if engine work and GUI work are done by different people.

`MockEngine` mimics the engine’s API so the view can be developed and tested before the real engine changes land:

```python
class MockEngine:
    """Stub engine for GUI development."""

    def get_display_state(self):
        return {
            "vis_grid": _STUB_GRID,
            "rows": 4, "cols": 4,
            "entry_valve": {"row": 0, "col": 0},
            "exit_drain": {"row": 3, "col": 3},
            "player_row": 1, "player_col": 1,
            "pressure": 85,
            "clogs_cleared": 2,
            "level": 1,
            "phase": "navigating",
            "status": "in_progress",
            "question": None,
        }

    def process_command(self, cmd):
        return "in_progress"

    def start_new_game(self, seed=None):
        pass

    def save_game(self):
        return True

    def load_game(self):
        return True
```

When the real `GameEngine` is ready, `MockEngine` can be swapped out without changing the view.

---

6. Maze and database responsibilities
-------------------------------------

Nick’s design leaves `maze.py` and `db.py` unchanged for the GUI. One teammate still owns their behavior and any enhancements.

**Responsibilities for the maze/persistence owner:**

- Keep `maze.py` and `db.py` stable:
  - No regressions to public behavior or signatures.
  - No imports of `main`; no `print()` or `input()`.
- If needed, implement enhancements such as:
  - Multiple save slots.
  - Extra stats (e.g. high scores, play time).
- Ensure the question bank content is sufficient and on-theme.
- Run and maintain:
  - `pytest tests/test_maze_contract.py -v`
  - `pytest tests/test_repo_contract.py -v`
  - `pytest tests/test_module_isolation.py -v`
- Add tests for any new persistence or domain behavior.

---

7. Test plan
------------

### 7.1 Existing tests (unchanged)  *(from Nick's design doc)*

- `tests/test_maze_contract.py` — domain logic.
- `tests/test_repo_contract.py` — persistence contract.
- `tests/test_integration.py` — engine wiring via `MockRepo`.

These do not touch the view layer, so adding the graphical view will not break them if boundaries are respected.

### 7.2 New tests: view and input  *(from Nick's design doc)*

**Module isolation — `test_module_isolation.py`:**

- `test_pygame_view_no_maze_import`
- `test_pygame_view_no_db_import`
- `test_pygame_view_no_main_import`

**View interface conformance — `test_module_isolation.py`:**

- `test_pygame_view_matches_pipe_view_interface`
  - Confirms `PygameView` implements: `render_map`, `render_status`, `render_question`, `render_message`, `render_welcome`, `render_help`.

**Key-to-command mapping — `test_integration.py`:**

- `test_key_to_command_directions`
- `test_key_to_command_answers`
- `test_key_to_command_actions`
- `test_key_to_command_unknown_returns_none`

### 7.3 New tests: engine driver API

**Engine driver API — `test_integration.py`:**

- `test_get_display_state_after_new_game`
- `test_get_display_state_after_move`
- `test_get_display_state_after_save_load`
- `test_get_display_state_none_before_start`

### 7.4 What NOT to test  *(from Nick's design doc)*

- Pixel-level rendering (colors/coordinates).
- Pygame’s own event loop mechanics.

These are better validated by running the app manually.

---

8. Integration verification checklist
-------------------------------------

After all work is merged, run these checks on the final codebase.

### 8.1 Automated

- `pytest tests/ -v` — all tests pass.

### 8.2 GUI manual walkthrough

- Start new game — maze and player appear.
- Move in each direction — movement updates canvas.
- Move into walls — blocked with appropriate message.
- Hit a clog — question overlay appears.
- Answer correctly — clog clears.
- Answer incorrectly — pressure drops, new question appears.
- Use blast — clog clears, pressure drops 50.
- Save (F5) — no error.
- Load (F9) — state restored.
- Clear all clogs — win message is shown.
- Quit (Escape) — app exits cleanly.

### 8.3 Persistence via GUI

- Save, close program, restart, load — game state restored.
- Trivia questions shown are pulled from SQLite via `SQLiteRepository`.

### 8.4 CLI still works

- `python main.py` — text-based game remains functional.

---

9. Documentation tasks
----------------------

To satisfy documentation and communication expectations:

**README.md:**

- Project title and short description.
- How to install dependencies (including Pygame).
- How to run:
  - CLI: `python main.py`
  - GUI: `python main.py --pygame`
- Architecture overview (modules and dependencies).
- Work split (who owned engine, maze/DB, GUI).
- Key design decisions and known limitations.
- How to run tests: `pytest tests/ -v`.

**Docs:**

- `docs/interfaces.md`:
  - Add `get_display_state()` and view interface details.
- `docs/RUNBOOK.md`:
  - Add GUI entry point and test commands.

---

10. Team workflow and branch plan
---------------------------------

**Step 0 — Approve this design (whole team)**

- Branch: `design/gui-proposal`
- Merge this doc into `docs/`.
- Everyone reviews and agrees.

**Step 1 — Engine enhancements (Person A)**

- Branch: `feature/gui-engine`
- Implement `run_pygame()`, `_key_to_command()`, `get_display_state()`.
- Add tests for key mapping and driver API.
- Keep CLI `run()` working.
- Merge after tests pass.

**Step 2 — Maze & DB (Person B)**

- Branch: `feature/maze-db-maintenance`
- Keep domain and persistence stable; add any needed features.
- Ensure related tests pass.
- Merge.

**Step 3 — GUI & canvas (Person C)**

- Branch: `feature/gui-view`
- Implement `pygame_view.py` using the design above.
- Use `MockEngine` if engine work isn’t merged yet.
- Add isolation and interface tests.
- Merge.

**Step 4 — Integration (whole team)**

- Branch: `feature/gui-integration`
- Wire real `GameEngine` into GUI entry point.
- Run automated tests and manual checklist.
- Merge.

**Step 5 — Documentation**

- Branch: `docs/gui-readme`
- Update README and docs as above.
- Merge.

**Step 6 — Final validation**

- Pull `main`.
- Run all tests and full manual walkthrough.
- Submit repo link.

---

11. One-line role summary
-------------------------

- **Engine:** Add `run_pygame()`, `_key_to_command()`, and `get_display_state()`, while keeping the CLI intact and adding tests.
- **Maze & DB:** Keep domain and persistence correct and stable; implement any small enhancements and maintain tests.
- **GUI:** Implement `pygame_view.py` exactly to Nick’s interface and rendering design; use a mock engine if needed; add isolation/interface tests.

