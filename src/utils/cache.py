from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Optional


class DiskCache:
    def __init__(self, cache_dir: str = ".cache"):
        self._dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        hashed = hashlib.sha256(key.encode()).hexdigest()
        return os.path.join(self._dir, f"{hashed}.json")

    def get(self, key: str) -> Optional[Any]:
        path = self._path(key)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f)

    def set(self, key: str, value: Any) -> None:
        with open(self._path(key), "w") as f:
            json.dump(value, f)

    def has(self, key: str) -> bool:
        return os.path.exists(self._path(key))
