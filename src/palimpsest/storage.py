from dataclasses import dataclass
from pathlib import Path

from palimpsest.config import DATA_DIR


@dataclass()
class LocalStorage:
    base: Path = DATA_DIR

    def _path(self, key: str) -> Path:
        return self.base / key

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        path = self._path(key)
        with open(path, "rb") as f:
            content = f.read()
        return content
