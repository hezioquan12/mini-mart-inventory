# src/inventory/category_manager.py
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional, Union

from src.utils.validators import normalize_name
from src.utils.io_utils import atomic_write_text

logger = logging.getLogger(__name__)


class CategoryManager:
    """
    Quản lý danh mục đơn giản: load / save tên danh mục vào file JSON.
    - uniqueness được xác định bởi normalize_name(name).
    - lưu trữ tên gốc (không thay đổi case/dấu).
    """

    def __init__(self, storage_path: Optional[Union[str, Path]] = None) -> None:
        self._names: List[str] = []
        self._normalized_cache: Optional[set[str]] = None

        self.storage_path: Optional[Path] = Path(storage_path) if storage_path else None

        if self.storage_path:
            # Nếu path tồn tại và là file, load; nếu là thư mục hoặc không tồn tại thì bỏ qua
            try:
                if self.storage_path.exists():
                    if self.storage_path.is_file():
                        text = self.storage_path.read_text(encoding="utf-8")
                        data = json.loads(text)
                        if isinstance(data, list):
                            self._names = [str(n) for n in data]
                        else:
                            logger.warning("Categories file %s doesn't contain a list. Ignoring.", self.storage_path)
                    else:
                        logger.warning("storage_path %s exists but is not a file. Ignoring.", self.storage_path)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Failed to load categories from %s: %s. Resetting to empty.", self.storage_path, exc
                )
                self._names = []

            # build cache initially
            self._rebuild_normalized_cache()

    # ---------- internal helpers ----------
    def _rebuild_normalized_cache(self) -> None:
        self._normalized_cache = {normalize_name(n) for n in self._names}

    def _normalized_set(self) -> set:
        if self._normalized_cache is None:
            self._rebuild_normalized_cache()
        return set(self._normalized_cache)  # return a copy to avoid external mutation

    # ---------- public API ----------
    def save(self) -> None:
        """
        Ghi danh sách danh mục ra storage_path (bằng atomic_write_text).
        Raises:
            RuntimeError: nếu storage_path chưa được cấu hình.
            Exception: propagate lỗi IO từ atomic_write_text.
        """
        if not self.storage_path:
            raise RuntimeError("No storage_path configured for CategoryManager")

        # Ensure parent dir exists
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(self._names, ensure_ascii=False, indent=2)
            atomic_write_text(self.storage_path, text)
        except Exception:
            logger.exception("Failed to save categories to %s", self.storage_path)
            raise

    def get_all_names(self) -> List[str]:
        """Trả về bản sao danh sách tên (preserve original formatting)."""
        return list(self._names)

    def is_valid_name(self, name: str) -> bool:
        """Check existence by normalized name."""
        return normalize_name(name) in self._normalized_set()

    def add_category(self, name: str) -> None:
        """
        Thêm danh mục mới. Nếu storage_path được cấu hình, cố gắng lưu.
        Nếu lưu thất bại, rollback thay đổi trong memory.
        Raises:
            ValueError: nếu tên rỗng hoặc đã tồn tại.
            Exception: nếu lưu file lỗi (propagate).
        """
        if not name or not str(name).strip():
            raise ValueError("Tên danh mục không được để trống")

        name = str(name).strip()
        normalized = normalize_name(name)
        if normalized in self._normalized_set():
            raise ValueError("Danh mục đã tồn tại")

        # Thêm tạm thời vào memory
        self._names.append(name)
        # cập nhật cache ngay
        if self._normalized_cache is None:
            self._normalized_cache = set()
        self._normalized_cache.add(normalized)

        # Nếu có storage, cố gắng lưu; rollback nếu lỗi
        if self.storage_path:
            try:
                self.save()
            except Exception:
                # rollback in-memory
                try:
                    self._names.remove(name)
                except ValueError:
                    logger.exception("Failed to remove just-added category %s after save error.", name)
                # rebuild cache from remaining names
                self._rebuild_normalized_cache()
                raise

    def remove_category(self, name: str) -> bool:
        """
        Xóa category theo tên (so sánh normalize). Trả về True nếu xóa thành công.
        """
        normalized = normalize_name(name)
        for n in list(self._names):
            if normalize_name(n) == normalized:
                self._names.remove(n)
                self._rebuild_normalized_cache()
                if self.storage_path:
                    try:
                        self.save()
                    except Exception:
                        logger.exception("Failed to save after removing category %s", n)
                        # Nếu save thất bại, ta không rollback xóa (thường cần transaction, nhưng giữ đơn giản)
                        raise
                return True
        return False

    def rename_category(self, old_name: str, new_name: str) -> None:
        """
        Đổi tên category (validate trùng lặp với normalized).
        Raises ValueError nếu old_name không tồn tại hoặc new_name rỗng/đã tồn tại.
        """
        if not new_name or not str(new_name).strip():
            raise ValueError("Tên mới không được để trống")
        normalized_new = normalize_name(new_name)
        if normalized_new in self._normalized_set():
            raise ValueError("Tên mới đã tồn tại")

        normalized_old = normalize_name(old_name)
        for idx, n in enumerate(self._names):
            if normalize_name(n) == normalized_old:
                self._names[idx] = str(new_name).strip()
                self._rebuild_normalized_cache()
                if self.storage_path:
                    try:
                        self.save()
                    except Exception:
                        logger.exception("Failed to save after renaming category %s -> %s", old_name, new_name)
                        raise
                return

        raise ValueError(f"Category '{old_name}' không tồn tại")

