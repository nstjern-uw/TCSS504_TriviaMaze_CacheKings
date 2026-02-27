import json
from db import JsonFileRepository


def test_save_returns_true(tmp_path):
    repo = JsonFileRepository()
    path = tmp_path / "save.json"
    assert repo.save_game({"a": 1}, str(path)) is True


def test_save_then_load_matches(tmp_path):
    repo = JsonFileRepository()
    path = tmp_path / "save.json"
    data = {"x": 1, "nested": {"ok": True}, "items": [1, 2, None]}
    assert repo.save_game(data, str(path)) is True
    assert repo.load_game(str(path)) == data


def test_load_missing_file(tmp_path):
    repo = JsonFileRepository()
    path = tmp_path / "missing.json"
    assert repo.load_game(str(path)) is None


def test_load_corrupted_json(tmp_path):
    repo = JsonFileRepository()
    path = tmp_path / "corrupt.json"
    path.write_text("not valid json", encoding="utf-8")
    assert repo.load_game(str(path)) is None


def test_save_non_serializable_returns_false(tmp_path):
    repo = JsonFileRepository()
    path = tmp_path / "bad.json"
    assert repo.save_game({"bad": set([1, 2])}, str(path)) is False


def test_delete_and_exists(tmp_path):
    repo = JsonFileRepository()
    path = tmp_path / "save.json"

    assert repo.save_exists(str(path)) is False
    assert repo.save_game({"a": 1}, str(path)) is True
    assert repo.save_exists(str(path)) is True

    assert repo.delete_save(str(path)) is True
    assert repo.save_exists(str(path)) is False
    assert repo.delete_save(str(path)) is False