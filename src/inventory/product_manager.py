import csv
import json
from datetime import datetime
from typing import List
from inventory.product import Product

class ProductManager:
    PRODUCTS_FILE = "products.csv"
    CATEGORIES_FILE = "categories.json"

    def __init__(self):
        self.products: List[Product] = self.load_products()
        self.categories = self.load_categories()

    def load_products(self) -> List[Product]:
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
        fieldnames = ["product_id", "name", "category", "cost_price", "sell_price",
                      "stock_quantity", "min_threshold", "unit", "created_date", "last_updated"]
        with open(self.PRODUCTS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in self.products:
                writer.writerow(p.to_dict())

    def load_categories(self):
        try:
            with open(self.CATEGORIES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            default = ["Thực phẩm", "Đồ uống", "Gia dụng", "Mỹ phẩm", "Điện tử", "Khác"]
            with open(self.CATEGORIES_FILE, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
            return default

    def generate_product_id(self):
        if not self.products:
            return "SP001"
        last_id = max(int(p.product_id[2:]) for p in self.products)
        return f"SP{str(last_id + 1).zfill(3)}"

    def add_product(self, name: str, category: str, cost_price: float,
                    sell_price: float, stock_quantity: int,
                    min_threshold: int, unit: str) -> Product:
        if not name:
            raise ValueError("Tên sản phẩm không được để trống!")
        if cost_price <= 0 or sell_price <= 0:
            raise ValueError("Giá nhập/bán phải > 0!")
        if stock_quantity < 0 or min_threshold < 0:
            raise ValueError("Số lượng/ngưỡng không hợp lệ!")

        new_id = self.generate_product_id()
        product = Product(new_id, name, category, cost_price, sell_price,
                          stock_quantity, min_threshold, unit)
        self.products.append(product)
        self.save_products()
        return product

    def update_product(self, product_id: str, **kwargs):
        product = self.find_product(product_id)
        if not product:
            raise ValueError("Không tìm thấy sản phẩm")
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        product.last_updated = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.save_products()
        return product

    def delete_product(self, product_id: str):
        product = self.find_product(product_id)
        if not product:
            raise ValueError("Không tìm thấy sản phẩm")
        self.products.remove(product)
        self.save_products()

    def find_product(self, product_id: str) -> Product:
        return next((p for p in self.products if p.product_id == product_id), None)

    def search_products(self, keyword: str) -> List[Product]:
        return [p for p in self.products if keyword.lower() in p.name.lower() or keyword.lower() in p.category.lower()]
