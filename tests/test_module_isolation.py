"""Module isolation tests — P0 boundary enforcement suite.

These tests statically inspect source files to verify that module
boundary rules defined in docs/RUNBOOK.md are not violated.

Only non-comment, non-docstring lines are checked to avoid false
positives from documentation text that mentions forbidden patterns.

Run with: pytest tests/test_module_isolation.py -v
"""

import ast
from pathlib import Path

# Project root is two levels up from this file (tests/ -> repo root)
ROOT = Path(__file__).resolve().parents[1]
MAZE_PY = ROOT / "maze.py"
DB_PY = ROOT / "db.py"


def _code_lines(path: Path) -> list[str]:
    """Return only executable code lines — strips comments and docstrings.

    Uses the AST to identify string literals used as docstrings, then
    falls back to stripping lines that start with '#'.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Collect line numbers that are pure docstring literals
    docstring_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                ds_node = node.body[0]
                for lineno in range(ds_node.lineno, ds_node.end_lineno + 1):
                    docstring_lines.add(lineno)

    result = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if lineno in docstring_lines:
            continue
        if stripped.startswith("#"):
            continue
        result.append(line)
    return result


# ---------------------------------------------------------------------------
# maze.py isolation
# ---------------------------------------------------------------------------

def test_maze_imports_nothing() -> None:
    """maze.py must not import db or main (project modules)."""
    lines = _code_lines(MAZE_PY)
    for line in lines:
        stripped = line.strip()
        assert not (stripped.startswith("import db") or stripped.startswith("import main")), \
            f"maze.py must not import project modules: {stripped!r}"
        assert not (stripped.startswith("from db ") or stripped.startswith("from main ")), \
            f"maze.py must not import from project modules: {stripped!r}"


def test_maze_no_print() -> None:
    """maze.py must not use print() — output is data, not text."""
    lines = _code_lines(MAZE_PY)
    for line in lines:
        assert "print(" not in line, \
            f"maze.py must not call print() — found in: {line.strip()!r}"


# ---------------------------------------------------------------------------
# db.py isolation (skipped gracefully if db.py not yet implemented)
# ---------------------------------------------------------------------------

def test_db_imports_nothing() -> None:
    """db.py must not import maze or main (project modules)."""
    if not DB_PY.exists():
        import pytest
        pytest.skip("db.py not yet implemented — skipping isolation check.")
    lines = _code_lines(DB_PY)
    for line in lines:
        stripped = line.strip()
        assert not (stripped.startswith("import maze") or stripped.startswith("import main")), \
            f"db.py must not import project modules: {stripped!r}"
        assert not (stripped.startswith("from maze ") or stripped.startswith("from main ")), \
            f"db.py must not import from project modules: {stripped!r}"


def test_db_no_print() -> None:
    """db.py must not use print() — I/O belongs to main.py only."""
    if not DB_PY.exists():
        import pytest
        pytest.skip("db.py not yet implemented — skipping isolation check.")
    lines = _code_lines(DB_PY)
    for line in lines:
        assert "print(" not in line, \
            f"db.py must not call print() — found in: {line.strip()!r}"
