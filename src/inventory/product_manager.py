import csv
import json
import re
from datetime import datetime
from typing import List, Optional

from inventory.product import Product


class CategoryManager:
    """Đọc/validate danh mục từ JSON."""
    def __init__(self, categories_file: str = "categories.json"):
        self.categories_file = categories_file
        self._categories = self._load_or_create_default()

    def _load_or_create_default(self) -> List[str]:
        default = ["Thực phẩm", "Đồ uống", "Gia dụng", "Mỹ phẩm", "Điện tử", "Khác"]
        try:
            with open(self.categories_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                # nếu file có cấu trúc lạ -> overwrite mặc định
        except FileNotFoundError:
            pass
        # tạo file mặc định
        with open(self.categories_file, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default

    def get_all(self) -> List[str]:
        return self._categories

    def is_valid(self, category: str) -> bool:
        return category in self._categories


class ProductManager:
    """
    Quản lý danh sách Product, đọc/ghi CSV, validation, API rõ ràng.
    """
    DEFAULT_PRODUCTS_FILE = "products.csv"

    def __init__(self, products_file: str = DEFAULT_PRODUCTS_FILE, categories_file: str = "categories.json"):
        self.products_file = products_file
        self.category_mgr = CategoryManager(categories_file)
        self.products: List[Product] = self._load_products()

    # ---------------- file IO ----------------
    def _load_products(self) -> List[Product]:
        products: List[Product] = []
        try:
            with open(self.products_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # chuyển kiểu cẩn thận, nếu thiếu trường thì set mặc định
                    pid = row.get("product_id") or ""
                    name = row.get("name") or ""
                    category = row.get("category") or ""
                    cost_price = float(row.get("cost_price") or 0.0)
                    sell_price = float(row.get("sell_price") or 0.0)
                    stock_quantity = int(row.get("stock_quantity") or 0)
                    min_threshold = int(row.get("min_threshold") or 0)
                    unit = row.get("unit") or ""
                    created_date = row.get("created_date") or None
                    last_updated = row.get("last_updated") or None

                    # nếu không có product_id thì bỏ qua (data xấu)
                    if not pid:
                        continue

                    products.append(Product(
                        product_id=pid,
                        name=name,
                        category=category,
                        cost_price=cost_price,
                        sell_price=sell_price,
                        stock_quantity=stock_quantity,
                        min_threshold=min_threshold,
                        unit=unit,
                        created_date=created_date,
                        last_updated=last_updated
                    ))
        except FileNotFoundError:
            # file chưa tồn tại → sẽ tạo khi save lần đầu
            pass
        return products

    def _save_products(self):
        fieldnames = [
            "product_id", "name", "category", "cost_price", "sell_price",
            "stock_quantity", "min_threshold", "unit", "created_date", "last_updated"
        ]
        with open(self.products_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in self.products:
                writer.writerow(p.to_dict())

    # ---------------- validation ----------------
    def _validate_product_fields(
        self,
        name: str,
        category: str,
        cost_price: float,
        sell_price: float,
        stock_quantity: int,
        min_threshold: int,
        unit: str,
    ):
        if not name or not name.strip():
            raise ValueError("Tên sản phẩm không được để trống")
        if cost_price <= 0:
            raise ValueError("Giá nhập phải > 0")
        if sell_price < cost_price:
            raise ValueError("Giá bán phải ≥ giá nhập")
        if not self.category_mgr.is_valid(category):
            raise ValueError(f"Danh mục '{category}' không hợp lệ. Có thể dùng: {self.category_mgr.get_all()}")
        if stock_quantity < 0:
            raise ValueError("Số lượng tồn không được âm")
        if min_threshold < 0:
            raise ValueError("Ngưỡng cảnh báo phải ≥ 0")
        if not unit or not unit.strip():
            raise ValueError("Đơn vị tính không được để trống")

    # ---------------- id generator ----------------
    def _next_numeric_suffix(self) -> int:
        """Tìm số lớn nhất trong các product_id có dạng SPxxx, trả về last+1."""
        max_n = 0
        for p in self.products:
            m = re.search(r"(\d+)$", p.product_id)
            if m:
                try:
                    n = int(m.group(1))
                    if n > max_n:
                        max_n = n
                except ValueError:
                    continue
        return max_n + 1

    def generate_product_id(self) -> str:
        n = self._next_numeric_suffix()
        return f"SP{str(n).zfill(3)}"

    # ---------------- API (rõ ràng) ----------------
    def add_product(
        self,
        name: str,
        category: str,
        cost_price: float,
        sell_price: float,
        stock_quantity: int,
        min_threshold: int,
        unit: str,
    ) -> Product:
        """Thêm sản phẩm mới (validate + auto id)."""
        # validate đầu vào
        self._validate_product_fields(name, category, cost_price, sell_price, stock_quantity, min_threshold, unit)
        new_id = self.generate_product_id()
        p = Product(
            product_id=new_id,
            name=name,
            category=category,
            cost_price=cost_price,
            sell_price=sell_price,
            stock_quantity=stock_quantity,
            min_threshold=min_threshold,
            unit=unit
        )
        self.products.append(p)
        self._save_products()
        return p

    def update_product(self, product_id: str, **kwargs) -> Product:
        """Sửa sản phẩm (cập nhật và validate lại)."""
        p = self.get_product_by_id(product_id)
        if not p:
            raise ValueError("Không tìm thấy sản phẩm")
        # set những thuộc tính cho phép
        allowed = {"name", "category", "cost_price", "sell_price", "stock_quantity", "min_threshold", "unit"}
        for k, v in kwargs.items():
            if k in allowed:
                # convert type nếu cần
                if k in {"cost_price", "sell_price"}:
                    setattr(p, k, float(v))
                elif k in {"stock_quantity", "min_threshold"}:
                    setattr(p, k, int(v))
                else:
                    setattr(p, k, v)
        # validate sau khi sửa
        self._validate_product_fields(p.name, p.category, p.cost_price, p.sell_price, p.stock_quantity, p.min_threshold, p.unit)
        p.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        return list(self.products)  # trả bản copy list

    def search_products(self, keyword: str) -> List[Product]:
        k = keyword.lower()
        return [p for p in self.products if k in p.name.lower() or k in p.category.lower() or k in p.product_id.lower()]

    def update_stock(self, product_id: str, quantity: int, transaction_type: str) -> Product:
        p = self.get_product_by_id(product_id)
        if not p:
            raise ValueError("Không tìm thấy sản phẩm")
        p.update_stock(quantity, transaction_type)
        p.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save_products()
        return p

    # ---------------- utilities ----------------
    def get_low_stock(self) -> List[Product]:
        return [p for p in self.products if p.stock_quantity <= p.min_threshold]

    def reload(self):
        """Tải lại products từ file (useful cho testing or GUI)."""
        self.products = self._load_products()
