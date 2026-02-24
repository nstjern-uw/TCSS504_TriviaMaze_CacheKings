# RUNBOOK.md
## Quiz Maze Skeleton - Liam's Version

## Branch
- Work on: `design/liam`

## Required Docs for Part 1
- `docs/interfaces.md`
- `docs/RUNBOOK.md`

## Architecture (Walking Skeleton)
- `maze.py` = Domain logic
- `db.py` = JSON persistence
- `main.py` = CLI engine / wiring

## Dependency Rules (Must Follow)
- `main.py` may import `maze.py`
- `main.py` may import `db.py`
- `maze.py` must not import `db.py` or `main.py`
- `db.py` must not import `maze.py` or `main.py`

## CLI Ownership Rule
- Only `main.py` may use:
  - `print()`
  - `input()`

## Persistence Boundary Rule
- `db.py` stores JSON-safe primitives only
- `main.py` converts domain state <-> JSON snapshot
- Do not pass domain objects directly into `db.py`

## Walking Skeleton Scope (P0)
Must work:
- CLI game loop starts
- WASD movement works (`w/a/s/d`)
- 3x3 maze layout
- walls block movement
- required clog blocks movement until cleared
- `i` interact works only when adjacent to clog
- trivia gate clears clog on correct answer
- energy updates (`+10` correct / `-5` wrong)
- save/load JSON works
- win requires:
  - clog cleared
  - then reach exit

## Fixed Map (Deterministic for Testing)
- Start: `(0,0)`
- Clog: `(1,1)`
- Exit: `(2,2)`
- Walls: `(0,2)`, `(1,0)`, `(2,0)`, `(2,1)`

```text
row\col   0   1   2
0         P   .   #
1         #   C   .
2         #   #   E