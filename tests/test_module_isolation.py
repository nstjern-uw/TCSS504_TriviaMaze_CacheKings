"""Module isolation tests — P0 boundary enforcement suite (Phase 3).

These tests statically inspect source files to verify that module
boundary rules defined in docs/RUNBOOK.md are not violated.

Phase 3 additions enforce SQLModel boundary checks:
  - maze.py stays persistence-agnostic (no sqlmodel imports).
  - db.py avoids circular dependencies (no maze imports).
  - main.py is the only orchestrator that may import both maze and db.
  - Serialization helpers (to_dict / from_dict) live in main.py, not maze.py.
  - db.py exposes all 8 RepositoryProtocol methods.

Only non-comment, non-docstring lines are checked to avoid false
positives from documentation text that mentions forbidden patterns.

Run with:  pytest tests/test_module_isolation.py -v
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAZE_PY = ROOT / "maze.py"
DB_PY = ROOT / "db.py"
MAIN_PY = ROOT / "main.py"


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


def test_maze_no_sqlmodel() -> None:
    """maze.py must not import sqlmodel — stays persistence-agnostic."""
    lines = _code_lines(MAZE_PY)
    for line in lines:
        assert "sqlmodel" not in line.lower(), \
            f"maze.py must not reference sqlmodel: {line.strip()!r}"


def test_maze_has_no_to_dict() -> None:
    """maze.py must not define to_dict or from_dict — serialization is main.py's job."""
    lines = _code_lines(MAZE_PY)
    for line in lines:
        assert "def to_dict" not in line, \
            f"maze.py must not define to_dict(): {line.strip()!r}"
        assert "def from_dict" not in line, \
            f"maze.py must not define from_dict(): {line.strip()!r}"


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


def test_db_no_maze_import() -> None:
    """db.py must not import maze — avoids circular dependency."""
    if not DB_PY.exists():
        import pytest
        pytest.skip("db.py not yet implemented — skipping isolation check.")
    lines = _code_lines(DB_PY)
    for line in lines:
        stripped = line.strip()
        assert not stripped.startswith("import maze"), \
            f"db.py must not import maze: {stripped!r}"
        assert not stripped.startswith("from maze"), \
            f"db.py must not import from maze: {stripped!r}"
        assert "maze" not in stripped.split("import ")[-1] if "import " in stripped else True, \
            f"db.py must not import maze indirectly: {stripped!r}"


def test_db_provides_repository_protocol() -> None:
    """db.py should implement all 8 methods of RepositoryProtocol."""
    if not DB_PY.exists():
        import pytest
        pytest.skip("db.py not yet implemented — skipping protocol check.")

    required_methods = [
        "save_game",
        "load_game",
        "delete_save",
        "save_exists",
        "get_unused_question",
        "seed_questions",
        "reset_questions",
        "get_question_count",
    ]

    lines = _code_lines(DB_PY)
    source_text = "\n".join(lines)

    missing = [m for m in required_methods if f"def {m}" not in source_text]
    assert not missing, (
        f"db.py is missing RepositoryProtocol methods: {', '.join(missing)}"
    )


# ---------------------------------------------------------------------------
# main.py orchestration (skipped gracefully if main.py not yet implemented)
# ---------------------------------------------------------------------------

def test_main_may_import_maze() -> None:
    """main.py may import maze — it orchestrates game logic."""
    if not MAIN_PY.exists():
        import pytest
        pytest.skip("main.py not yet implemented — skipping orchestration check.")

    lines = _code_lines(MAIN_PY)
    found = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("import maze") or stripped.startswith("from maze"):
            found = True
            break
    assert found, "main.py should import maze (it orchestrates game logic)."


def test_main_may_import_db() -> None:
    """main.py may import db — it orchestrates persistence."""
    if not MAIN_PY.exists():
        import pytest
        pytest.skip("main.py not yet implemented — skipping orchestration check.")

    lines = _code_lines(MAIN_PY)
    found = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("import db") or stripped.startswith("from db"):
            found = True
            break
    assert found, "main.py should import db (it orchestrates persistence)."
