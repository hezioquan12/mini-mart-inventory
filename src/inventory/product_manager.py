
from typing import List, Optional, Any, Dict
from pathlib import Path
import json
import csv
from datetime import datetime,UTC
import os
import tempfile
import logging

from product import Product
from category_manager import CategoryManager
from src.utils.validators import normalize_name

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8"):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
            f.write(text)
        os.replace(tmp_path, str(path))  # atomic replace
    except (OSError, IOError) as e:   # 🔑 chỉ bắt lỗi liên quan file/IO
        try:
            os.remove(tmp_path)
        except OSError:
            pass  # ignore cleanup failure
        raise e


class ProductManager:
    DEFAULT_FIELDS = [
        "product_id",
        "name",
        "category",
        "cost_price",
        "sell_price",
        "stock_quantity",
        "min_threshold",
        "unit",
        "created_date",
        "last_updated",
    ]

    def __init__(self, storage_file: str = "products.json", category_mgr: Optional[CategoryManager] = None):
        self.storage_file = Path(storage_file)
        self._use_json = self.storage_file.suffix.lower() == ".json"
        self.category_mgr = category_mgr or CategoryManager()
        self.products: List[Product] = []
        self._load_products()

    # ---------------------------
    # Load / Save
    # ---------------------------
    def _load_products(self):
        if not self.storage_file.exists():
            self.products = []
            return

        if self._use_json:
            try:
                data = json.loads(self.storage_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.products = [Product.from_dict(d) for d in data]
                else:
                    self.products = []
            except (OSError, json.JSONDecodeError) as e:  # 🔑 chỉ bắt lỗi IO và parse JSON
                logger.exception("Failed to load products from json (%s). Starting with empty list.", e)
                self.products = []
        else:
            try:
                with self.storage_file.open(mode="r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    self.products = [Product.from_csv_row(r) for r in reader]
            except (OSError, csv.Error) as e:  # 🔑 chỉ bắt lỗi file hoặc CSV parse
                logger.exception("Failed to load products from csv (%s). Starting with empty list.", e)
                self.products = []

    def _save_products(self):
        if self._use_json:
            data = [p.to_dict() for p in self.products]
            text = json.dumps(data, ensure_ascii=False, indent=2)
            _atomic_write_text(self.storage_file, text)
        else:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            with self.storage_file.open(mode="w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.DEFAULT_FIELDS)
                writer.writeheader()
                for p in self.products:
                    writer.writerow(p.to_csv_row())

    # ---------------------------
    # Export / Import
    # ---------------------------
    def export_json(self, out_path: str):
        data = [p.to_dict() for p in self.products]
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(out, json.dumps(data, ensure_ascii=False, indent=2))

    def export_csv(self, out_path: str):
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open(mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.DEFAULT_FIELDS)
            writer.writeheader()
            for p in self.products:
                writer.writerow(p.to_csv_row())

    def import_json(self, in_path: str):
        data = json.loads(Path(in_path).read_text(encoding="utf-8"))
        self.products = [Product.from_dict(d) for d in data]
        self._save_products()

    def import_csv(self, in_path: str):
        with Path(in_path).open(mode="r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            self.products = [Product.from_csv_row(r) for r in reader]
        self._save_products()

    # ---------------------------
    # Internal helpers
    # ---------------------------
    def _find_index_by_id(self, product_id: str) -> Optional[int]:
        for i, p in enumerate(self.products):
            if p.product_id == product_id:
                return i
        return None

    def _assert_category_exists(self, category: str):
        if not self.category_mgr.is_valid_name(category):
            raise ValueError(f"Danh mục '{category}' không hợp lệ. Có thể dùng: {self.category_mgr.get_all_names()}")

    def _assert_unique_id(self, product_id: str, ignore_index: Optional[int] = None):
        for i, p in enumerate(self.products):
            if i == ignore_index:
                continue
            if p.product_id == product_id:
                raise ValueError("Product ID đã tồn tại")

    # ---------------------------
    # CRUD sản phẩm
    # ---------------------------
    def add_product(self, product_id: str, name: str, category: str,
                    cost_price: Any, sell_price: Any, stock_quantity: Any,
                    min_threshold: Any, unit: str) -> Product:
        """Thêm sản phẩm mới (chỉ dùng khi khởi tạo sản phẩm)."""
        if not product_id or not str(product_id).strip():
            raise ValueError("Product ID không được để trống")
        if not name or not str(name).strip():
            raise ValueError("Tên sản phẩm không được để trống")
        if not unit or not str(unit).strip():
            raise ValueError("Đơn vị không được để trống")
        product_id = str(product_id).strip()
        name = str(name).strip()
        category = str(category).strip()
        unit = str(unit).strip()

        self._assert_category_exists(category)
        self._assert_unique_id(product_id)
        product = Product(
            product_id=product_id,
            name=name,
            category=category,
            cost_price=cost_price,
            sell_price=sell_price,
            stock_quantity=stock_quantity,
            min_threshold=min_threshold,
            unit=unit,
            created_date=datetime.now(UTC),   # thời điểm tạo, timezone-aware UTC
            last_updated=datetime.now(UTC),   # thời điểm cập nhật cuối
        )
        self.products.append(product)
        self._save_products()
        return product

    def get_product(self, product_id: str) -> Product:
        idx = self._find_index_by_id(product_id)
        if idx is None:
            raise ValueError("Product không tồn tại")
        return self.products[idx]

    def delete_product(self, product_id: str) -> None:
        idx = self._find_index_by_id(product_id)
        if idx is None:
            raise ValueError("Product không tồn tại")
        del self.products[idx]
        self._save_products()

    def update_product(self, product_id: str, **changes) -> Product:
        """Cập nhật metadata sản phẩm (không dùng để nhập/xuất kho!)."""
        idx = self._find_index_by_id(product_id)
        if idx is None:
            raise ValueError("Product không tồn tại")
        old = self.products[idx]
        merged: Dict[str, Any] = {
            'product_id': old.product_id,
            'name': old.name,
            'category': old.category,
            'cost_price': old.cost_price,
            'sell_price': old.sell_price,
            'stock_quantity': old.stock_quantity,
            'min_threshold': old.min_threshold,
            'unit': old.unit,
            'created_date': old.created_date,
            'last_updated': datetime.now(UTC),
        }
        for k, v in changes.items():
            if k not in merged:
                raise ValueError(f"Trường không hợp lệ: {k}")
            if k in ('name', 'category', 'unit', 'product_id') and isinstance(v, str):
                merged[k] = v.strip()
            else:
                merged[k] = v
        if not merged['name'] or not str(merged['name']).strip():
            raise ValueError("Tên sản phẩm không được để trống")
        if normalize_name(merged['category']) != normalize_name(old.category):
            self._assert_category_exists(merged['category'])
        if merged['product_id'] != old.product_id:
            self._assert_unique_id(merged['product_id'], ignore_index=idx)
        new_product = Product(**merged)
        self.products[idx] = new_product
        self._save_products()
        return new_product

    def list_products(self) -> List[Product]:
        return list(self.products)

    # ---------------------------
    # CHỖ DỄ CHỒNG CHÉO: tồn kho
    # ---------------------------
    def apply_stock_change(self, product_id: str, delta: int) -> Product:
        """
        Cập nhật số lượng tồn kho bằng delta.
        - Dương = nhập thêm
        - Âm = xuất kho
        🚨 Chỉ được gọi từ TransactionManager (Luân).
        Các module khác (Tuyên, Lực) KHÔNG được gọi trực tiếp.
        """
        idx = self._find_index_by_id(product_id)
        if idx is None:
            raise ValueError("Product không tồn tại")
        product = self.products[idx]
        new_qty = product.stock_quantity + delta
        if new_qty < 0:
            raise ValueError("Số lượng tồn không đủ")
        return self.update_product(product_id, stock_quantity=new_qty, last_updated=datetime.now(UTC))

    # ---------------------------
    # Tìm kiếm hỗ trợ Tuyên
    # ---------------------------
    def search_products(self, keyword: str, field: str = "name") -> List[Product]:
        """
        Tìm kiếm sản phẩm theo trường (name/product_id/category).
        Dùng cho Tuyên (auto-complete, tìm kiếm linh hoạt).
        """
        keyword_norm = keyword.strip().lower()
        results = []
        for p in self.products:
            value = getattr(p, field, "")
            if keyword_norm in str(value).lower():
                results.append(p)
        return results

