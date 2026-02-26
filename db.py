from __future__ import annotations

import json
import os
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RepositoryProtocol(Protocol):
    def save_game(self, state: dict[str, Any], filepath: str) -> bool: ...
    def load_game(self, filepath: str) -> dict[str, Any] | None: ...
    def delete_save(self, filepath: str) -> bool: ...
    def save_exists(self, filepath: str) -> bool: ...


class JsonFileRepository:
    def save_game(self, state: dict[str, Any], filepath: str) -> bool:
        try:
            json.dumps(state)

            parent = os.path.dirname(filepath)
            if parent:
                os.makedirs(parent, exist_ok=True)

            tmp_path = filepath + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

            os.replace(tmp_path, filepath)
            return True
        except (TypeError, ValueError, OSError):
            return False

    def load_game(self, filepath: str) -> dict[str, Any] | None:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else None
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
            return None

    def delete_save(self, filepath: str) -> bool:
        try:
            os.remove(filepath)
            return True
        except FileNotFoundError:
            return False
        except OSError:
            return False

    def save_exists(self, filepath: str) -> bool:
        return os.path.exists(filepath)