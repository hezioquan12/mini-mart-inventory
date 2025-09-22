import csv
import json
from datetime import datetime
from typing import List, Optional
from inventory.product import Product


class ProductManager:
    PRODUCTS_FILE = "products.csv"
    CATEGORIES_FILE = "categories.json"

    def __init__(self):
        self.categories = self.load_categories()
        self.products: List[Product] = self.load_products()

    # ---------- FILE HANDLING ----------
    def load_categories(self) -> List[str]:
        """Đọc danh mục từ JSON, nếu chưa có thì tạo mặc định"""
        try:
            with open(self.CATEGORIES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            default = ["Thực phẩm", "Đồ uống", "Gia dụng", "Mỹ phẩm", "Điện tử", "Khác"]
            with open(self.CATEGORIES_FILE, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
            return default

    def load_products(self) -> List[Product]:
        """Đọc danh sách sản phẩm từ CSV"""
        products = []
        try:
            with open(self.PRODUCTS_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    products.append(Product(
                        product_id=row["product_id"],
                        name=row["name"],
                        category=row["category"],
                        cost_price=float(row["cost_price"]),
                        sell_price=float(row["sell_price"]),
                        stock_quantity=int(row["stock_quantity"]),
                        min_threshold=int(row["min_threshold"]),
                        unit=row["unit"],
                        created_date=row["created_date"],
                        last_updated=row["last_updated"]
                    ))
        except FileNotFoundError:
            print("⚠️ Chưa có file products.csv, sẽ tạo mới sau.")
        return products

    def save_products(self):
        """Ghi danh sách sản phẩm ra CSV"""
        fieldnames = ["product_id", "name", "category", "cost_price", "sell_price",
                      "stock_quantity", "min_threshold", "unit", "created_date", "last_updated"]
        with open(self.PRODUCTS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in self.products:
                writer.writerow(p.to_dict())

    # ---------- VALIDATION ----------
    def validate_product(self, name: str, category: str,
                         cost_price: float, sell_price: float,
                         stock_quantity: int, min_threshold: int, unit: str):
        if not name.strip():
            raise ValueError("Tên sản phẩm không được để trống!")
        if cost_price <= 0:
            raise ValueError("Giá nhập phải > 0!")
        if sell_price < cost_price:
            raise ValueError("Giá bán phải ≥ giá nhập!")
        if category not in self.categories:
            raise ValueError(f"Danh mục '{category}' không hợp lệ!")
        if stock_quantity < 0 or min_threshold < 0:
            raise ValueError("Số lượng/ngưỡng phải ≥ 0!")

    # ---------- ID ----------
    def generate_product_id(self) -> str:
        """Sinh mã SP tự động: SP001, SP002..."""
        if not self.products:
            return "SP001"
        last_id = max(int(p.product_id[2:]) for p in self.products)
        return f"SP{str(last_id + 1).zfill(3)}"

    # ---------- API ----------
    def add_product(self, name: str, category: str, cost_price: float,
                    sell_price: float, stock_quantity: int,
                    min_threshold: int, unit: str) -> Product:
        self.validate_product(name, category, cost_price, sell_price,
                              stock_quantity, min_threshold, unit)
        new_id = self.generate_product_id()
        product = Product(new_id, name, category, cost_price, sell_price,
                          stock_quantity, min_threshold, unit)
        self.products.append(product)
        self.save_products()
        return product

    def update_product(self, product_id: str, **kwargs) -> Product:
        product = self.get_product_by_id(product_id)
        if not product:
            raise ValueError("Không tìm thấy sản phẩm")

        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)

        # validate lại sau update
        self.validate_product(
            product.name, product.category, product.cost_price,
            product.sell_price, product.stock_quantity,
            product.min_threshold, product.unit
        )

        product.last_updated = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.save_products()
        return product

    def delete_product(self, product_id: str):
        product = self.get_product_by_id(product_id)
        if not product:
            raise ValueError("Không tìm thấy sản phẩm")
        self.products.remove(product)
        self.save_products()

    # ---------- GETTERS ----------
    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        return next((p for p in self.products if p.product_id == product_id), None)

    def get_all_products(self) -> List[Product]:
        return self.products

    def search_products(self, keyword: str) -> List[Product]:
        return [p for p in self.products if keyword.lower() in p.name.lower()
                or keyword.lower() in p.category.lower()]

    def update_stock(self, product_id: str, quantity: int, transaction_type: str):
        product = self.get_product_by_id(product_id)
        if not product:
            raise ValueError("Không tìm thấy sản phẩm")
        product.update_stock(quantity, transaction_type)
        self.save_products()
        return product
