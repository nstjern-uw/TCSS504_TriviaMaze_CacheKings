# interfaces.md
## Quiz Maze Skeleton - Liam's Version

## Modules
- `maze.py` (domain logic)
- `db.py` (JSON persistence)
- `main.py` (CLI engine / wiring)

## Walking Skeleton Scope
- CLI loop
- 3x3 maze
- WASD movement (`w/a/s/d`)
- `i` interact command
- One required clog blocks movement until cleared
- Multiple-choice Mario trivia to clear clog
- Energy updates: `+10` correct, `-5` wrong
- Save/load JSON
- Strict module boundaries

## Dependency Rules
- `main.py` may import `maze.py` and `db.py`
- `maze.py` must not import `db.py` or `main.py`
- `db.py` must not import `maze.py` or `main.py`
- Only `main.py` may use `print()` and `input()`

## Coordinate Convention
Use `row, col` everywhere.
- Top-left is `(0,0)`

## Fixed 3x3 Skeleton Map
- Start: `(0,0)`
- Required clog: `(1,1)`
- Exit: `(2,2)`
- Walls: `(0,2)`, `(1,0)`, `(2,0)`, `(2,1)`

```text
row\col   0   1   2
0         P   .   #
1         #   C   .
2         #   #   E