Final Maze with GUI — Design Proposal (PyQt6)
==============================================

**Based on:** Nick's Maze Renderer design doc (PR #22), team GUI proposal (`docs/gui-design-proposal.md`)  
**Date:** March 11, 2026  
**Status:** Proposal  
**Framework:** PyQt6 (replaces earlier Pygame references)

---

1. Overview
-----------

This document describes a plan to render the Nuovo Fresco Pipe Network maze using PyQt6, replacing the current ASCII-based CLI view (`view.py`) with a graphical tile-based renderer. The existing separation of concerns makes this a clean view-layer swap — `maze.py`, `db.py`, and the core `GameEngine` logic in `main.py` remain unchanged.

This proposal extends Nick's original rendering design with project-level concerns: engine API, team workflow, maze/database stability, documentation, and integration verification. All Pygame references from earlier proposals have been replaced with their PyQt6 equivalents.

---

2. Architecture Impact
----------------------

| Module       | Changes Required | Rationale                                                                                     |
|--------------|-----------------|-----------------------------------------------------------------------------------------------|
| `maze.py`    | None            | Pure domain logic. Already produces `SectionVisibility` grids — ideal for any graphical view. |
| `db.py`      | None            | Persistence is I/O-agnostic.                                                                  |
| `view.py`    | None            | CLI mode remains available.                                                                   |
| `qt_view.py` | **New file**    | Implements the same public interface as `PipeView`, drawing via `QWidget` + `QPainter`.       |
| `main.py`    | **Modified**    | Adds `run_qt()`, `_key_to_command()`, and `get_display_state()`. Qt owns the event loop.      |

### 2.1 Dependency graph

```text
main.py ──imports──▶ maze.py   (domain logic, pure data)
│
├──imports──▶ db.py            (persistence, SQLModel)
│
└──imports──▶ qt_view.py OR view.py   (presentation)
```

`qt_view.py` must NOT import `maze`, `db`, or `main`. It receives plain data (visibility grids, strings, integers) and renders it — identical boundary rules to `view.py`.

### 2.2 New dependency

Add to `requirements.txt`:

```text
PyQt6>=6.6.0
```

---

3. `QtView` design
-------------------

PyQt6 is widget-based, not frame-loop-based. The view is composed of two classes:

- **`MazeWidget(QWidget)`** — custom-painted tile grid.
- **`QtView(QMainWindow)`** — main window that composes `MazeWidget`, HUD labels, message label, and question panel.

### 3.1 `MazeWidget`

Subclasses `QWidget` and overrides `paintEvent()` to draw the maze with `QPainter`.

- `update_grid(vis_grid, entry_valve, exit_drain)` stores the latest visibility data and calls `self.update()` to schedule a repaint.
- `paintEvent(event)` iterates over the grid and delegates to `_draw_cell(painter, sv)`.
- Fixed size: `cols * TILE_SIZE` wide, `rows * TILE_SIZE` tall.
- Constants: `TILE_SIZE = 80`, `WALL_THICKNESS = 4`.

### 3.2 `QtView` (main window)

```text
┌──────────────────────────────────┐
│         MazeWidget               │  ← QPainter tile grid
├──────────────────────────────────┤
│  Status label (QLabel)           │  ← HUD: coords, pressure, clogs, level
├──────────────────────────────────┤
│  Message label (QLabel)          │  ← transient messages
├──────────────────────────────────┤
│  Question panel (QLabel, hidden) │  ← shown only during BLOCKED phase
└──────────────────────────────────┘
```

Initialization: `QtView.__init__(rows, cols, command_callback)`.

- `command_callback` is a function the engine provides; `keyPressEvent()` maps the key and calls it.
- The question panel is hidden by default and shown/hidden via `render_question()` / `clear_question()`.

### 3.3 Public interface (mirrors `PipeView`)

Methods the engine expects:

| Method                                                      | Qt Implementation                                      |
|-------------------------------------------------------------|--------------------------------------------------------|
| `render_map(vis_grid, rows, cols, entry_valve, exit_drain)` | Calls `MazeWidget.update_grid()` → triggers repaint    |
| `render_status(row, col, pressure, clogs_cleared, level)`   | `QLabel.setText()` on the status label                 |
| `render_question(prompt, choices)`                          | Shows question panel with HTML-formatted text           |
| `render_message(msg)`                                       | `QLabel.setText()` on the message label                |
| `render_welcome()`                                          | Sets welcome text on message label                     |
| `render_help()`                                             | Sets help/controls text on message label               |
| `clear_question()`                                          | Hides the question panel (Qt-specific addition)        |

### 3.4 Tile rendering (`paintEvent` via `_draw_cell`)

Each `SectionVisibility` cell maps to a tile:

- **Fogged** (`is_visible=False` and `is_visited=False`):
  `painter.fillRect()` with fog color.
- **Visible / visited**:
  `painter.fillRect()` with floor color. Walls drawn with `painter.drawLine()` using a `QPen` on edges where `open_directions` does NOT include that direction.
- **Center sprites** drawn with `QPainter`:
  - `is_current=True` → `drawEllipse()` green circle (player)
  - `has_clog=True` → `fillRect()` red square (clog)
  - Entry valve position → `drawPolygon()` blue upward triangle
  - Exit drain position → `drawPolygon()` gold downward triangle
  - `is_visited=True` → small `drawEllipse()` dot (breadcrumb)
  - `is_visible=True` and not visited → hollow `drawEllipse()` circle

### 3.5 Color palette

```text
Background:   QColor(20, 20, 30)
Floor:        QColor(60, 70, 90)
Walls:        QColor(140, 140, 160)
Fog:          QColor(30, 30, 40)
Player:       QColor(0, 220, 120)
Clog:         QColor(220, 60, 60)
Visited:      QColor(50, 60, 75)
Entry Valve:  QColor(80, 200, 255)
Exit Drain:   QColor(255, 200, 50)
```

### 3.6 Question panel (`render_question`)

When `EnginePhase.BLOCKED`:

- Show the question panel `QLabel`.
- Set HTML-formatted text with prompt and four choices labeled 1–4 (mapped to `a`/`b`/`c`/`d` internally).
- Include a "blast" hint line.

When the player answers or the phase changes back to `NAVIGATING`, call `clear_question()` to hide the panel.

### 3.7 HUD (`render_status`)

A `QLabel` below the maze widget, updated via `setText()`:

- Current section coordinates
- Pressure gauge
- Clogs cleared count
- Current level

---

4. Game loop and engine API changes (`main.py`)
------------------------------------------------

### 4.1 `run_qt()`

Qt owns the event loop — no manual `while True` or frame ticking required:

```python
def run_qt(self) -> None:
    from PyQt6.QtWidgets import QApplication
    import sys

    if self._state is None:
        self.start_new_game()

    app = QApplication(sys.argv)

    def on_command(cmd):
        self.process_command(cmd)
        if self._state.status != GameStatus.IN_PROGRESS:
            app.quit()
            return
        self._refresh_qt_view()

    self._view = QtView(
        DEFAULT_MAZE_ROWS, DEFAULT_MAZE_COLS,
        command_callback=on_command,
    )
    self._view.show()
    self._view.render_welcome()
    self._refresh_qt_view()
    app.exec()
```

### 4.2 `_refresh_qt_view()`

Called after every command to push fresh data to the view:

```python
def _refresh_qt_view(self):
    ds = self.get_display_state()
    if ds is None:
        return
    self._view.render_map(
        ds["vis_grid"], ds["rows"], ds["cols"],
        ds["entry_valve"], ds["exit_drain"],
    )
    self._view.render_status(
        ds["player_row"], ds["player_col"],
        ds["pressure"], ds["clogs_cleared"], ds["level"],
    )
    if ds["question"]:
        self._view.render_question(
            ds["question"]["prompt"], ds["question"]["choices"],
        )
    else:
        self._view.clear_question()
```

### 4.3 `_key_to_command(key)`

Pure mapping function using `Qt.Key` enum values — no side effects:

| Key               | Command   |
|-------------------|-----------|
| Arrow Up / W      | `"north"` |
| Arrow Down / S    | `"south"` |
| Arrow Left / A    | `"west"`  |
| Arrow Right / D   | `"east"`  |
| 1 / 2 / 3 / 4    | `"a"` / `"b"` / `"c"` / `"d"` |
| B                 | `"blast"` |
| Escape            | `"quit"`  |
| F5                | `"save"`  |
| F9                | `"load"`  |

```python
def _key_to_command(key):
    from PyQt6.QtCore import Qt
    mapping = {
        Qt.Key.Key_Up: "north",    Qt.Key.Key_W: "north",
        Qt.Key.Key_Down: "south",  Qt.Key.Key_S: "south",
        Qt.Key.Key_Left: "west",   Qt.Key.Key_A: "west",
        Qt.Key.Key_Right: "east",  Qt.Key.Key_D: "east",
        Qt.Key.Key_1: "a",  Qt.Key.Key_2: "b",
        Qt.Key.Key_3: "c",  Qt.Key.Key_4: "d",
        Qt.Key.Key_B: "blast",
        Qt.Key.Key_Escape: "quit",
        Qt.Key.Key_F5: "save",
        Qt.Key.Key_F9: "load",
    }
    return mapping.get(key)
```

This function lives in `qt_view.py` and is called from `QtView.keyPressEvent()`. The mapped command string is passed to the engine via the `command_callback`.

### 4.4 Entry point

```python
if __name__ == "__main__":
    import sys
    if "--qt" in sys.argv:
        engine = GameEngine()
        engine.run_qt()
    else:
        engine = GameEngine()
        engine.run()
```

### 4.5 `get_display_state()` (engine driver API)

Bundles everything the view needs into a single dict, keeping the view decoupled from engine internals:

```python
def get_display_state(self) -> dict | None:
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

---

5. Mock engine for parallel development
----------------------------------------

Only needed if engine work and GUI work are done by different people.

`MockEngine` mimics the engine's API so the view can be developed and tested before the real engine changes land:

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
--------------------------------------

The GUI leaves `maze.py` and `db.py` unchanged. One teammate still owns their behavior and any enhancements.

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

### 7.1 Existing tests (unchanged)

- `tests/test_maze_contract.py` — domain logic.
- `tests/test_repo_contract.py` — persistence contract.
- `tests/test_integration.py` — engine wiring via `MockRepo`.

These do not touch the view layer, so adding the Qt GUI has zero impact on them.

### 7.2 New tests: view and input

**Module isolation — `test_module_isolation.py`:**

- `test_qt_view_no_maze_import` — `qt_view.py` must not import `maze`.
- `test_qt_view_no_db_import` — `qt_view.py` must not import `db`.
- `test_qt_view_no_main_import` — `qt_view.py` must not import `main`.

**View interface conformance — `test_module_isolation.py`:**

- `test_qt_view_matches_pipe_view_interface`
  - Confirms `QtView` implements: `render_map`, `render_status`, `render_question`, `render_message`, `render_welcome`, `render_help`.

**Key-to-command mapping — `test_integration.py`:**

- `test_key_to_command_directions` — Arrow keys and WASD map to directions.
- `test_key_to_command_answers` — Keys 1–4 map to `"a"`–`"d"`.
- `test_key_to_command_actions` — B → `"blast"`, Escape → `"quit"`, F5 → `"save"`, F9 → `"load"`.
- `test_key_to_command_unknown_returns_none` — Unmapped keys return `None`.

### 7.3 New tests: engine driver API

**Engine driver API — `test_integration.py`:**

- `test_get_display_state_after_new_game`
- `test_get_display_state_after_move`
- `test_get_display_state_after_save_load`
- `test_get_display_state_none_before_start`

### 7.4 Headless Qt testing

PyQt6 supports headless testing via the `offscreen` platform plugin. Tests that need to instantiate `QtView` can run without a display server:

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_qt_view.py -v
```

This is an advantage over Pygame, which requires a display or virtual framebuffer.

### 7.5 What NOT to test

- **Pixel-level rendering** — Do not assert on colors, coordinates, or paint output. Visual correctness is verified by running the app.
- **Qt's own event loop** — Do not test that `QApplication.exec()` works. That's Qt's responsibility.

### Test summary

| Test Area                       | File                       | Tests | Priority |
|---------------------------------|----------------------------|-------|----------|
| Module isolation for `qt_view.py` | `test_module_isolation.py` | 3     | High     |
| View interface conformance      | `test_module_isolation.py` | 1     | High     |
| Key-to-command mapping          | `test_integration.py`      | 4     | Medium   |
| Engine driver API               | `test_integration.py`      | 4     | Medium   |
| Pixel rendering                 | —                          | Skip  | —        |

**Total new tests: ~12**, all lightweight and fast.

---

8. Integration verification checklist
--------------------------------------

After all work is merged, run these checks on the final codebase.

### 8.1 Automated

- `pytest tests/ -v` — all tests pass.

### 8.2 GUI manual walkthrough

- Start new game — maze and player appear in Qt window.
- Move in each direction — movement updates the painted canvas.
- Move into walls — blocked with appropriate message in status label.
- Hit a clog — question panel appears.
- Answer correctly — clog clears, question panel hides.
- Answer incorrectly — pressure drops, new question appears.
- Use blast (B key) — clog clears, pressure drops 50.
- Save (F5) — no error.
- Load (F9) — state restored.
- Clear all clogs — win message shown.
- Quit (Escape) — app exits cleanly.

### 8.3 Persistence via GUI

- Save, close program, restart, load — game state restored.
- Trivia questions shown are pulled from SQLite via `SQLiteRepository`.

### 8.4 CLI still works

- `python main.py` — text-based game remains fully functional.

---

9. Documentation tasks
----------------------

**README.md:**

- Project title and short description.
- How to install dependencies (`pip install -r requirements.txt`, which now includes PyQt6).
- How to run:
  - CLI: `python main.py`
  - GUI: `python main.py --qt`
- Architecture overview (modules and dependencies).
- Work split (who owned engine, maze/DB, GUI).
- Key design decisions and known limitations.
- How to run tests: `pytest tests/ -v`.

**Docs:**

- `docs/interfaces.md`:
  - Add `get_display_state()` return schema and `QtView` interface details.
- `docs/RUNBOOK.md`:
  - Add GUI entry point (`--qt` flag) and test commands.

---

10. Team workflow and branch plan
----------------------------------

**Step 0 — Approve this design (whole team)**

- Branch: `design/gui-proposal`
- Merge this doc into `docs/`.
- Everyone reviews and agrees.

**Step 1 — Engine enhancements (Person A)**

- Branch: `feature/gui-engine`
- Implement `run_qt()`, `_key_to_command()`, `get_display_state()`, `_refresh_qt_view()`.
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
- Implement `qt_view.py` (`MazeWidget` + `QtView`) to the interface spec above.
- Use `MockEngine` if engine work isn't merged yet.
- Add isolation and interface tests.
- Merge.

**Step 4 — Integration (whole team)**

- Branch: `feature/gui-integration`
- Wire real `GameEngine` into the Qt entry point.
- Run automated tests and manual checklist.
- Merge.

**Step 5 — Documentation**

- Branch: `docs/gui-readme`
- Update README and docs as described in section 9.
- Merge.

**Step 6 — Final validation**

- Pull `main`.
- Run all tests and full manual walkthrough.
- Submit repo link.

---

11. One-line role summary
--------------------------

- **Engine:** Add `run_qt()`, `_key_to_command()`, `get_display_state()`, and `_refresh_qt_view()`, while keeping the CLI intact and adding tests.
- **Maze & DB:** Keep domain and persistence correct and stable; implement any small enhancements and maintain tests.
- **GUI:** Implement `qt_view.py` (`MazeWidget` + `QtView`) exactly to the interface and rendering spec; use a mock engine if needed; add isolation/interface tests.

---

12. PyQt6 vs Pygame — rationale for framework choice
-----------------------------------------------------

| Aspect             | Pygame                                       | PyQt6                                                        |
|--------------------|----------------------------------------------|--------------------------------------------------------------|
| Event loop         | Manual `while True` + `clock.tick()`         | Qt owns it via `app.exec()` — less code, no frame management |
| Question UI        | Manually render text onto surfaces           | Real `QLabel` widgets with HTML styling and accessibility     |
| HUD                | Manually blit font surfaces every frame      | `QLabel.setText()` — trivial                                 |
| Layout             | Manual pixel math for all positioning        | Qt layouts handle resize and positioning                      |
| Headless testing   | Requires virtual framebuffer                 | `QT_QPA_PLATFORM=offscreen` works out of the box             |
| Dependency size    | ~30 MB                                       | ~60–80 MB                                                    |
| License            | LGPL                                         | GPL (PyQt6) — use PySide6 for LGPL if needed                 |

---

13. Open questions
------------------

1. **Mouse support?** Clickable answer buttons would improve UX and are natural in Qt (real `QPushButton` widgets). Deferred for MVP — keyboard-only matches the CLI experience.
2. **Animations?** Smooth player movement between tiles, clog-clearing effects. `QPropertyAnimation` makes this straightforward in Qt. Nice-to-have, not MVP.
3. **Scaling/resolution?** Fixed tile size works for 4×4 and 5×5 grids. Larger grids may benefit from `QScrollArea` or dynamic tile sizing.
4. **PySide6 instead of PyQt6?** Near-identical API, LGPL-licensed. Drop-in replacement if GPL is a concern.
