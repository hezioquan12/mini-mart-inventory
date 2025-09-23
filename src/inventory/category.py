from dataclasses import dataclass, asdict
from pathlib import Path
import json
from typing import List, Union


@dataclass
class Category:
    """Simple Category model."""
    id: str
    name: str

    @classmethod
    def from_raw(cls, raw: Union[str, dict]):
        """Create Category from either a string or dict like {'id': 'C01', 'name': 'Thực phẩm'}"""
        if isinstance(raw, str):
            return cls(id=raw, name=raw)
        return cls(id=str(raw.get("id", raw.get("name", ""))), name=str(raw.get("name", raw.get("id", ""))))


class CategoryManager:
    """Load / validate categories.json and provide helper methods."""
    DEFAULTS = [
        {"id": "C01", "name": "Thực phẩm"},
        {"id": "C02", "name": "Đồ uống"},
        {"id": "C03", "name": "Gia dụng"},
        {"id": "C04", "name": "Mỹ phẩm"},
        {"id": "C05", "name": "Điện tử"},
        {"id": "C99", "name": "Khác"},
    ]

    def __init__(self, filepath: str = "categories.json"):
        self.filepath = Path(filepath)
        self.categories: List[Category] = self._load_or_create()

    def _load_or_create(self) -> List[Category]:
        if not self.filepath.exists():
            # write defaults
            self.filepath.write_text(json.dumps(self.DEFAULTS, ensure_ascii=False, indent=2), encoding="utf-8")
            return [Category.from_raw(r) for r in self.DEFAULTS]
        try:
            raw = json.loads(self.filepath.read_text(encoding="utf-8"))
            # support either list of strings or list of dicts
            return [Category.from_raw(item) for item in raw]
        except Exception:
            # if file corrupted, overwrite defaults
            self.filepath.write_text(json.dumps(self.DEFAULTS, ensure_ascii=False, indent=2), encoding="utf-8")
            return [Category.from_raw(r) for r in self.DEFAULTS]

    def get_all(self) -> List[Category]:
        return list(self.categories)

    def get_all_names(self) -> List[str]:
        return [c.name for c in self.categories]

    def is_valid_name(self, name: str) -> bool:
        return any(name == c.name for c in self.categories)

    def find_by_name(self, name: str) -> Category:
        for c in self.categories:
            if c.name == name:
                return c
        return None

    def add_category(self, cat_id: str, name: str):
        if self.is_valid_name(name):
            raise ValueError(f"Category '{name}' already exists")
        self.categories.append(Category(id=cat_id, name=name))
        self._save()

    def _save(self):
        data = [asdict(c) for c in self.categories]
        self.filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
