# tcss504-quiz-game

**Team Name:** Cache Kings  
**Team Members:** Liam Sipp, Nick Stjern, Ryan Belmonte

---

## Project Overview

Nuovo Fresco Pipe Network is a trivia maze game built in Python. Players navigate a procedurally generated pipe network, answering trivia questions to clear clogs and restore water flow to the city. The game features a Fog of War visibility system, a hydro-blast ability, save/load persistence, and a question bank backed by SQLite.

---

## Running the Game

CLI:
```bash
python3 main.py
```

Qt GUI:
```bash
python3 qt_main.py
```

---

## Running the Tests

```bash
pytest tests/ -v
```

**Current test count: 116 passing, 0 warnings.**

| Test file | What it covers |
|---|---|
| `tests/test_maze_contract.py` | Full contract coverage for `maze.py` — movement, clogs, solvability, fog of war, boundary conditions |
| `tests/test_repo_contract.py` | Contract coverage for `RepositoryProtocol` via `MockRepository` + `SEED_QUESTIONS` structural integrity |
| `tests/test_sqlite_repo.py` | Integration tests against a real in-memory `SQLiteRepository` — save/load, question bank, `list_save_slots()` |
| `tests/test_module_isolation.py` | Enforces dependency rules — `maze.py` and `db.py` must not import each other or project modules |
| `tests/test_integration.py` | End-to-end engine integration tests |

---

## Architecture

The project enforces strict module boundaries:

| Module | Responsibility |
|---|---|
| `maze.py` | Pure domain logic — pipe network generation, movement, clog/answer mechanics, fog of war. No I/O, no persistence. |
| `db.py` | Persistence only — SQLite-backed save/load game state and question bank via `SQLiteRepository`. |
| `main.py` | Engine orchestration — wires `maze.py` and `db.py` together, owns CLI I/O and dataclass serialization. |
| `view.py` | CLI rendering — displays the maze and game state to the terminal. |
| `qt_main.py` | Qt GUI main window and entry point. |
| `qt_controller.py` | Controller bridging the engine and Qt view. |
| `qt_bridge_view.py` | Qt-compatible view bridge — stores display data for the GUI. |
| `qt_models.py` | View state dataclasses for the Qt layer. |
| `widgets/maze_canvas.py` | Custom-painted maze tile renderer using `QPainter`. |

See `docs/interfaces.md` for the full `PipeNetworkProtocol` and `RepositoryProtocol` contracts.

---

## Notable Features

- **PyQt6 graphical interface** — full Qt GUI with a custom-painted maze canvas, arcade-style visuals, keyboard controls (arrow keys, 1–4 for answers, B for hydro blast), clickable answer buttons, and a tactical HUD. The CLI remains fully functional as an alternative.
- **38-question bank** — seed questions covering Italian vocabulary, plumbing facts, and general water trivia.
- **`list_save_slots()`** — `SQLiteRepository` method that returns all save slot names ordered by most recently updated; designed for GUI load-game menus.
- **`datetime` deprecation fix** — all `datetime.utcnow()` calls replaced with `datetime.now(timezone.utc)`.
- **Boundary-value test coverage** — full four-direction boundary movement tests, `hydro_blast` threshold tests (at/below/no-clog), and fog-of-war edge case tests.

---

## Work Split

| Member | Role | Owned |
|---|---|---|
| Ryan Belmonte | Maze, Database & Architecture | `maze.py`, `db.py`; 38-question seed bank and `list_save_slots()` in `db.py`; protocol contracts and module boundary rules (`docs/interfaces.md`, `tests/test_module_isolation.py`); test suites for domain, persistence, and SQLite integration (`test_maze_contract.py`, `test_repo_contract.py`, `test_sqlite_repo.py`); architecture RFC (`docs/RFC-ryan-part1-design-contracts-domain-architect.md`); extended Nick's renderer design into a full PyQt6 project proposal (`docs/gui-design-proposal-qt.md`) |
| Liam Sipp | *(to be filled in)* | *(to be filled in)* |
| Nick Stjern | Engine & Integration | `run_qt()`, `_key_to_command()`, `get_display_state()`, `_refresh_qt_view()` in `main.py`; Qt integration wiring (`qt_main.py`, `qt_controller.py`, `qt_bridge_view.py`, `qt_models.py`, `widgets/maze_canvas.py`); automated + manual integration verification |

---

## Part 4: AI Code Review & The Final Arbiter

Our team used Claude Opus 4.6 Max to audit the Nuovo Fresco Pipe Network codebase for separation of concerns by prompting it to act as a Senior Staff Engineer with the instruction: "Review this Python codebase for strict separation of concerns. Did any database logic leak into the maze logic? Suggest one concrete refactoring improvement." The AI found no database logic leaks into the maze logic and came back with two refactoring suggestions. The first was about moving `SEED_QUESTIONS` out of `db.py` and into `main.py` (or a dedicated `questions.py`/`config.py` module), calling it a "subtle violation" of separation of concerns since the persistence layer should be content-agnostic and not own game data. The second flagged the `hasattr` guards in `main.py` as undermining the `RepositoryProtocol` contract, suggesting that any conforming repository should just implement the full protocol instead of relying on runtime duck-typing fallbacks.

We looked at both suggestions and decided to pass on them. Neither change would actually affect how the game runs — and the AI itself admitted these are architectural preferences, not real bugs. A big part of our decision came down to the grading rubric: making changes that drift from what the assignment explicitly asked for is a risk we weren't willing to take. The assignment spec for the Persistence Engineer role literally says "implement a Question Bank table and populate it with seed data," so `db.py` is a perfectly reasonable and intentional place for that content in a 4-file project — and one that directly satisfies the rubric. The `hasattr` guards are also intentional — they let the engine fail gracefully when a lightweight test mock is injected, which is a smart and practical design choice. Invoking the Final Arbiter Rule, we used our own engineering judgment here: these kinds of suggestions matter a lot in large, multi-contributor codebases, but at this scale, they're nitpicks that would just create unnecessary churn without any real payoff.