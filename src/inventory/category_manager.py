from typing import List
from pathlib import Path
import json

from validators import normalize_name

class CategoryManager:
    def __init__(self, storage_path: str = None):
        self._names: List[str] = []
        self.storage_path = Path(storage_path) if storage_path else None
        if self.storage_path and self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self._names = [str(n) for n in data]
            except Exception:
                self._names = []

    def save(self):
        if not self.storage_path:
            raise RuntimeError("No storage_path configured for CategoryManager")
        self.storage_path.write_text(json.dumps(self._names, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_all_names(self) -> List[str]:
        return list(self._names)

    def _normalized_set(self):
        return {normalize_name(n) for n in self._names}

    def is_valid_name(self, name: str) -> bool:
        return normalize_name(name) in self._normalized_set()

    def add_category(self, name: str):
        if not name or not str(name).strip():
            raise ValueError("Tên danh mục không được để trống")
        if normalize_name(name) in self._normalized_set():
            raise ValueError("Danh mục đã tồn tại")
        self._names.append(str(name).strip())
        if self.storage_path:
            self.save()

    def remove_category(self, name: str):
        nn = normalize_name(name)
        for n in list(self._names):
            if normalize_name(n) == nn:
                self._names.remove(n)
                if self.storage_path:
                    self.save()
                return
        raise ValueError("Danh mục không tồn tại")