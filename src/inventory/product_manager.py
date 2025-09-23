# inventory/product_manager.py
import csv
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any
from .product import Product, DATETIME_FORMAT, parse_date
from .category import CategoryManager


class ProductManager:
    DEFAULT_FIELDS = [
        "product_id", "name", "category", "cost_price", "sell_price",
        "stock_quantity", "min_threshold", "unit", "created_date", "last_updated"
    ]

    def __init__(self, products_file: str = "products.csv", categories_file: str = "categories.json"):
        self.products_file = Path(products_file)
        self.category_mgr = CategoryManager(categories_file)
        self.products: List[Product] = []
        self._load_products()
        # ensure next id is set based on existing products
        self._next_id = self._compute_next_id()

    def _compute_next_id(self) -> int:
        maxn = 0
        for p in self.products:
            # find numeric suffix
            suffix = "".join(ch for ch in p.product_id if ch.isdigit())
            if suffix:
                try:
                    n = int(suffix)
                    if n > maxn:
                        maxn = n
                except ValueError:
                    continue
        return maxn + 1

    def generate_product_id(self) -> str:
        pid = f"SP{self._next_id:03d}"
        self._next_id += 1
        return pid

    def _load_products(self):
        self.products = []
        if not self.products_file.exists():
            return
        with self.products_file.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # normalize row keys and parse
                    row_norm: Dict[str, Any] = {k: v for k, v in row.items()}
                    # Parse date fields if present
                    if row_norm.get("created_date"):
                        row_norm["created_date"] = parse_date(row_norm["created_date"])
                    if row_norm.get("last_updated"):
                        row_norm["last_updated"] = parse_date(row_norm["last_updated"])
                    p = Product.from_dict(row_norm)
                    self.products.append(p)
                except Exception as e:
                    # skip bad rows but print a helpful message
                    print(f"⚠️ Bỏ qua dòng products.csv vì lỗi parse: {e}")

    def _save_products(self):
        # ensure parent exists
        self.products_file.parent.mkdir(parents=True, exist_ok=True)
        with self.products_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.DEFAULT_FIELDS)
            writer.writeheader()
            for p in self.products:
                writer.writerow(p.to_csv_row())

    # ---------- validation ----------
    def _validate_fields(self, name: str, category: str, cost_price: Decimal, sell_price: Decimal,
                         stock_quantity: int, min_threshold: int, unit: str):
        if not name or not name.strip():
            raise ValueError("Tên sản phẩm không được để trống")
        if not self.category_mgr.is_valid_name(category):
            raise ValueError(f"Danh mục '{category}' không hợp lệ. Có thể dùng: {self.category_mgr.get_all_names()}")
        if Decimal(cost_price) < 0 or Decimal(sell_price) < 0:
            raise ValueError("Giá phải ≥ 0")
        if Decimal(sell_price) < Decimal(cost_price):
            raise ValueError("Giá bán phải ≥ giá nhập")
        if int(stock_quantity) < 0:
            raise ValueError("Số lượng tồn phải ≥ 0")
        if int(min_threshold) < 0:
            raise ValueError("Ngưỡng cảnh báo phải ≥ 0")
        if not unit or not unit.strip():
            raise ValueError("Đơn vị không được để trống")

    # ---------- API ----------
    def add_product(self, name: str, category: str, cost_price: Any,
                    sell_price: Any, stock_quantity: int, min_threshold: int, unit: str) -> Product:
        # normalize numeric types
        cost = Decimal(str(cost_price))
        sell = Decimal(str(sell_price))
        self._validate_fields(name, category, cost, sell, stock_quantity, min_threshold, unit)
        pid = self.generate_product_id()
        p = Product(
            product_id=pid,
            name=name.strip(),
            category=category.strip(),
            cost_price=cost,
            sell_price=sell,
            stock_quantity=int(stock_quantity),
            min_threshold=int(min_threshold),
            unit=unit.strip()
        )
        self.products.append(p)
        self._save_products()
        return p

    def update_product(self, product_id: str, **kwargs) -> Product:
        p = self.get_product_by_id(product_id)
        if not p:
            raise ValueError("Không tìm thấy sản phẩm")
        # allowed updates
        allowed = {"name", "category", "cost_price", "sell_price", "stock_quantity", "min_threshold", "unit"}
        for k, v in kwargs.items():
            if k not in allowed:
                continue
            if k in ("cost_price", "sell_price"):
                setattr(p, k, Decimal(str(v)))
            elif k in ("stock_quantity", "min_threshold"):
                setattr(p, k, int(v))
            else:
                setattr(p, k, v)
        # validate after changes
        self._validate_fields(p.name, p.category, p.cost_price, p.sell_price, p.stock_quantity, p.min_threshold, p.unit)
        p.last_updated = datetime.now()
        self._save_products()
        return p

    def delete_product(self, product_id: str):
        p = self.get_product_by_id(product_id)
        if not p:
            raise ValueError("Không tìm thấy sản phẩm")
        self.products.remove(p)
        self._save_products()

    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        return next((x for x in self.products if x.product_id == product_id), None)

    def get_all_products(self) -> List[Product]:
        return list(self.products)

    def search_products(self, keyword: str) -> List[Product]:
        k = keyword.lower()
        return [p for p in self.products if k in p.product_id.lower() or k in p.name.lower() or k in p.category.lower()]

    def update_stock(self, product_id: str, quantity: int, transaction_type: str = "nhập") -> Product:
        p = self.get_product_by_id(product_id)
        if not p:
            raise ValueError("Không tìm thấy sản phẩm")
        p.update_stock(quantity, transaction_type)
        self._save_products()
        return p

    def get_low_stock(self) -> List[Product]:
        return [p for p in self.products if p.stock_quantity <= p.min_threshold]

    def reload(self):
        self._load_products()
        self._next_id = self._compute_next_id()
