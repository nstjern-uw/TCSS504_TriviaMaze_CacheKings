import json
from db import SqlModelRepository


def test_init_db_creates_db_file(tmp_path):
    repo = SqlModelRepository()
    db_path = tmp_path / "game.sqlite"
    repo.init_db(str(db_path))
    assert db_path.exists()


def test_seed_questions_and_get_unused_no_repeats(tmp_path):
    repo = SqlModelRepository()
    db_path = tmp_path / "game.sqlite"
    repo.init_db(str(db_path))
    repo.seed_questions(str(db_path))

    seen = set()
    for _ in range(100):
        q = repo.get_unused_question(str(db_path))
        if q is None:
            break

        assert isinstance(q["id"], int)
        assert isinstance(q["prompt"], str) and q["prompt"]
        assert isinstance(q["choices"], list) and len(q["choices"]) == 4
        assert isinstance(q["correct_answer"], str)
        assert q["correct_answer"] in q["choices"]
        assert q["id"] not in seen
        seen.add(q["id"])

    assert len(seen) >= 3
    assert repo.get_unused_question(str(db_path)) is None


def test_save_and_load_round_trip_slot(tmp_path):
    repo = SqlModelRepository()
    db_path = tmp_path / "game.sqlite"
    repo.init_db(str(db_path))

    snapshot = {"schema_version": 2, "player": {"row": 1, "col": 2}, "energy": 95}
    assert repo.save_game(str(db_path), "slot1", snapshot) is True
    assert repo.load_game(str(db_path), "slot1") == snapshot


def test_load_missing_slot_returns_none(tmp_path):
    repo = SqlModelRepository()
    db_path = tmp_path / "game.sqlite"
    repo.init_db(str(db_path))
    assert repo.load_game(str(db_path), "missing") is None


def test_save_non_serializable_returns_false(tmp_path):
    repo = SqlModelRepository()
    db_path = tmp_path / "game.sqlite"
    repo.init_db(str(db_path))
    assert repo.save_game(str(db_path), "slot1", {"bad": set([1, 2])}) is False