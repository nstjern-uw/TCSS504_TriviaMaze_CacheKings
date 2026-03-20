# Pygame Maze Renderer — Design Document

**Author:** Nick  
**Date:** March 11, 2026  
**Status:** Proposal

---

## Overview

This document describes a plan to render the Nuovo Fresco Pipe Network maze using Pygame, replacing the current ASCII-based CLI view (`view.py`) with a graphical tile-based renderer. The existing separation of concerns makes this a clean view-layer swap — `maze.py`, `db.py`, and the core `GameEngine` logic in `main.py` remain unchanged.

---

## Architecture Impact

| Module | Changes Required | Rationale |
|--------|-----------------|-----------|
| `maze.py` | None | Pure domain logic. Already produces `SectionVisibility` grids — the exact data structure a graphical renderer needs. |
| `db.py` | None | Persistence is I/O-agnostic. |
| `view.py` | None (kept as-is) | CLI mode remains available. |
| `pygame_view.py` | **New file** | Implements the same public interface as `PipeView`, drawing to a Pygame surface instead of stdout. |
| `main.py` | **Modified** | Adds a `run_pygame()` loop and a `_key_to_command()` mapper. `GameEngine.__init__` accepts either view. |

### Dependency Graph (unchanged principle)

```
main.py ──imports──▶ maze.py     (domain logic, pure data)
   │                 
   ├──imports──▶ db.py        (persistence, SQLModel)
   │
   └──imports──▶ pygame_view.py OR view.py   (presentation)
```

`pygame_view.py` must NOT import `maze`, `db`, or `main`. It receives plain data (visibility grids, strings, integers) and renders it — identical boundary rules to `view.py`.

---

## `PygameView` Design

### Initialization

- `PygameView.__init__(rows, cols)` creates the Pygame window.
- Window dimensions: `cols * TILE_SIZE` wide, `rows * TILE_SIZE + HUD_HEIGHT` tall.
- Constants: `TILE_SIZE = 80`, `WALL_THICKNESS = 4`, `HUD_HEIGHT = 120`.

### Public Interface (mirrors `PipeView`)

The following methods must be implemented to satisfy the engine's expectations:

| Method | Purpose |
|--------|---------|
| `render_map(vis_grid, rows, cols, entry_valve, exit_drain)` | Draw the tile grid from `SectionVisibility` data |
| `render_status(row, col, pressure, clogs_cleared, level)` | Draw the HUD bar at the bottom of the window |
| `render_question(prompt, choices)` | Draw a semi-transparent overlay with the trivia question and choices |
| `render_message(msg)` | Display a transient message (e.g., "That pipe's sealed shut.") |
| `render_welcome()` | Splash screen at game start |
| `render_help()` | Command reference overlay |

### Tile Rendering (`render_map`)

Each cell in the `SectionVisibility` grid maps to a tile:

- **Fogged cells** (`is_visible=False`, `is_visited=False`): filled with a dark fog color.
- **Visible/Visited cells**: filled with a floor color. Walls are drawn as thick lines on edges where `open_directions` does NOT include that direction.
- **Sprites at cell center**:
  - `is_current=True` → green circle (player)
  - `has_clog=True` → red square (clog)
  - Entry valve position → upward triangle (blue)
  - Exit drain position → downward triangle (gold)
  - `is_visited=True` → small dot (breadcrumb)
  - `is_visible=True` (but not visited) → hollow circle

### Color Palette

```
Background:    (20, 20, 30)
Floor:         (60, 70, 90)
Walls:         (140, 140, 160)
Fog:           (30, 30, 40)
Player:        (0, 220, 120)
Clog:          (220, 60, 60)
Visited:       (50, 60, 75)
Entry Valve:   (80, 200, 255)
Exit Drain:    (255, 200, 50)
```

### Question Overlay (`render_question`)

When the engine is in `EnginePhase.BLOCKED`, a semi-transparent dark overlay covers the maze and renders:
- The question prompt text
- Four choices labeled 1–4 (mapped to a/b/c/d internally)
- A "blast" hint if pressure ≥ 50

### HUD (`render_status`)

Drawn in the bottom `HUD_HEIGHT` pixels:
- Current section coordinates
- Pressure gauge
- Clogs cleared count
- Current level

---

## Game Loop Changes (`main.py`)

### New Method: `run_pygame()`

Replaces the blocking `input()` loop with a Pygame event-driven loop:

1. Pump `pygame.event.get()` each frame.
2. Map `KEYDOWN` events to command strings via `_key_to_command()`.
3. Call the existing `process_command()` method (unchanged).
4. Re-render the map, status, and question overlay each frame.
5. Call `pygame.display.flip()` and tick at 30 FPS.

### New Method: `_key_to_command(key)`

Pure mapping function — no side effects:

| Key | Command |
|-----|---------|
| Arrow Up / W | `"north"` |
| Arrow Down / S | `"south"` |
| Arrow Left / A | `"west"` |
| Arrow Right / D | `"east"` |
| 1 / 2 / 3 / 4 | `"a"` / `"b"` / `"c"` / `"d"` |
| H | `"blast"` |
| Escape | `"quit"` |
| F5 | `"save"` |
| F9 | `"load"` |

### Entry Point

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

---

## Test Recommendations

### Existing Tests (No Changes)

All existing tests remain valid and should continue to pass without modification:

- `test_maze_contract.py` — 20+ tests covering domain logic
- `test_repo_contract.py` — 18 tests covering persistence contract
- `test_integration.py` — 12+ tests covering engine wiring via `MockRepo`

These tests never touch the view layer, so the Pygame addition has zero impact on them.

### New Tests Required

#### 1. Module Isolation — `pygame_view.py` (add to `test_module_isolation.py`)

Enforce the same boundary rules as `view.py`:

- `test_pygame_view_no_maze_import` — `pygame_view.py` must not import `maze`.
- `test_pygame_view_no_db_import` — `pygame_view.py` must not import `db`.
- `test_pygame_view_no_main_import` — `pygame_view.py` must not import `main`.

**Priority:** High. Prevents architectural drift.

#### 2. View Interface Conformance (new test or add to `test_module_isolation.py`)

Verify that `PygameView` implements all the public methods the engine calls:

- `test_pygame_view_matches_pipe_view_interface` — Checks that `PygameView` has `render_map`, `render_status`, `render_question`, `render_message`, `render_welcome`, and `render_help`.

**Priority:** High. A missing method causes a runtime crash.

#### 3. Key-to-Command Mapping (add to `test_integration.py`)

Unit tests for `_key_to_command()`:

- `test_key_to_command_directions` — Arrow keys and WASD map to `"north"`, `"south"`, `"east"`, `"west"`.
- `test_key_to_command_answers` — Keys 1–4 map to `"a"`–`"d"`.
- `test_key_to_command_actions` — H → `"blast"`, Escape → `"quit"`, F5 → `"save"`, F9 → `"load"`.
- `test_key_to_command_unknown_returns_none` — Unmapped keys return `None`.

**Priority:** Medium. Pure function, easy to test, prevents input bugs.

#### 4. What NOT to Test

- **Pixel-level rendering** — Do not assert on colors, coordinates, or surface contents. This tests Pygame's drawing API, not game logic. Visual correctness is verified by running the game.
- **Pygame event loop mechanics** — Do not test that `pygame.event.get()` returns events. That's Pygame's responsibility.

### Test Summary

| Test Area | File | Tests | Priority |
|-----------|------|-------|----------|
| Module isolation for `pygame_view.py` | `test_module_isolation.py` | 3 | High |
| View interface conformance | `test_module_isolation.py` | 1 | High |
| Key-to-command mapping | `test_integration.py` | 4 | Medium |
| Pixel rendering | — | Skip | — |

**Total new tests: ~8**, all lightweight and fast (no Pygame display required).

---

## Dependencies

Add to `requirements.txt`:

```
pygame>=2.5.0
```

No other new dependencies are needed.

---

## Open Questions

1. **Mouse support?** Clickable answer buttons would improve UX but add complexity. Deferred for now — keyboard-only matches the CLI experience.
2. **Animations?** Smooth player movement between tiles, clog-clearing effects. Nice-to-have, not MVP.
3. **Scaling/resolution?** Fixed tile size works for 4×4 and 5×5 grids. Larger grids may need dynamic scaling or scrolling.
