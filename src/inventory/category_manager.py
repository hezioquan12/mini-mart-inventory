from typing import List
from pathlib import Path
import json

from src.utils.validators import normalize_name
from src.utils.io_utils import atomic_write_text

class CategoryManager:
    def __init__(self, storage_path: str = None):
        self._names: List[str] = []
        self.storage_path = Path(storage_path) if storage_path else None

        if self.storage_path and self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self._names = [str(n) for n in data]
            except (OSError, json.JSONDecodeError) as e:   # 🔑 chỉ bắt IO + JSON
                # log lỗi thay vì nuốt luôn
                import logging
                logging.getLogger(__name__).warning(
                    "Failed to load categories from %s: %s. Resetting to empty.",
                    self.storage_path, e
                )
                self._names = []

    def save(self):
        if not self.storage_path:
            raise RuntimeError("No storage_path configured for CategoryManager")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        # atomic write
        text = json.dumps(self._names, ensure_ascii=False, indent=2)
        atomic_write_text(self.storage_path, text)  # bạn cần import helper hoặc copy nó vào file này

    def get_all_names(self) -> List[str]:
        return list(self._names)

    def _normalized_set(self):
        return {normalize_name(n) for n in self._names}

    def is_valid_name(self, name: str) -> bool:
        return normalize_name(name) in self._normalized_set()

    def add_category(self, name: str):
        if not name or not str(name).strip():
            raise ValueError("Tên danh mục không được để trống")
        name = str(name).strip()  # strip trước
        if normalize_name(name) in self._normalized_set():
            raise ValueError("Danh mục đã tồn tại")
        self._names.append(name)
        if self.storage_path:
            self.save()
