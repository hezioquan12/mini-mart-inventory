from typing import List, Optional, Any, Dict
from pathlib import Path
import json
import csv
from datetime import datetime

from product import Product
from category_manager import CategoryManager
from validators import normalize_name

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

    def _load_products(self):
        if not self.storage_file.exists():
            self.products = []
            return
        if self._use_json:
            try:
                data = json.loads(self.storage_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.products = [Product.from_dict(d) for d in data]
            except Exception:
                self.products = []
        else:
            try:
                with self.storage_file.open(mode="r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    self.products = [Product.from_csv_row(r) for r in reader]
            except Exception:
                self.products = []

    def _save_products(self):
        if self._use_json:
            data = [p.to_dict() for p in self.products]
            self.storage_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            with self.storage_file.open(mode="w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.DEFAULT_FIELDS)
                writer.writeheader()
                for p in self.products:
                    writer.writerow(p.to_csv_row())

    def export_json(self, out_path: str):
        data = [p.to_dict() for p in self.products]
        Path(out_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def export_csv(self, out_path: str):
        with Path(out_path).open(mode="w", encoding="utf-8", newline="") as f:
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

    def add_product(self, product_id: str, name: str, category: str,
                    cost_price: Any, sell_price: Any, stock_quantity: Any,
                    min_threshold: Any, unit: str) -> Product:
        if not name or not str(name).strip():
            raise ValueError("Tên sản phẩm không được để trống")
        if not unit or not str(unit).strip():
            raise ValueError("Đơn vị không được để trống")
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
            created_date=datetime.utcnow().