import csv
import json
from datetime import datetime
from typing import List


class Product:
    def __init__(self, product_id: str, name: str, category: str,
                 cost_price: float, sell_price: float,
                 stock_quantity: int, min_threshold: int, unit: str,
                 created_date: str = None, last_updated: str = None):
        self.product_id = product_id  # Mã sản phẩm
        self.name = name  # Tên sản phẩm
        self.category = category  # Danh mục sản phẩm
        self.cost_price = cost_price  # Giá vốn (giá nhập)
        self.sell_price = sell_price  # Giá bán
        self.stock_quantity = stock_quantity  # Số lượng tồn kho
        self.min_threshold = min_threshold  # Ngưỡng tồn kho tối thiểu (để cảnh báo khi sắp hết hàng)
        self.unit = unit  # Đơn vị tính (cái, kg, hộp…)
        self.created_date = created_date or datetime.now().strftime("%d/%m/%Y")
        # Ngày tạo sản phẩm (nếu không truyền vào thì lấy ngày hiện tại)

        self.last_updated = last_updated or datetime.now().strftime("%d/%m/%Y %H:%M")
        # Ngày/giờ cập nhật gần nhất (nếu không truyền thì lấy thời điểm hiện tại)

    def update_stock(self, quantity: int, transaction_type: str):
        """Cập nhật số lượng tồn kho"""
        if transaction_type == "nhập":
            self.stock_quantity += quantity
        elif transaction_type == "xuất":
            if quantity > self.stock_quantity:
                raise ValueError(f"Không đủ hàng! Tồn kho: {self.stock_quantity}")
            self.stock_quantity -= quantity
        else:
            raise ValueError("transaction_type phải là 'nhập' hoặc 'xuất'")
        self.last_updated = datetime.now().strftime("%d/%m/%Y %H:%M")

    def get_stock_status(self):
        """Trả về trạng thái tồn kho"""
        if self.stock_quantity == 0:
            return "🚨 Hết hàng"
        elif self.stock_quantity <= self.min_threshold:
            return "⚠️ Sắp hết"
        else:
            return "Bình thường"

    def to_dict(self):
        """Chuyển object thành dictionary để ghi CSV"""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "category": self.category,
            "cost_price": self.cost_price,
            "sell_price": self.sell_price,
            "stock_quantity": self.stock_quantity,
            "min_threshold": self.min_threshold,
            "unit": self.unit,
            "created_date": self.created_date,
            "last_updated": self.last_updated
        }


class ProductManager:
    PRODUCTS_FILE = "products.csv"
    CATEGORIES_FILE = "categories.json"

    def __init__(self):
        self.products: List[Product] = self.load_products()
        self.categories = self.load_categories()

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

    def load_categories(self):
        """Đọc danh mục sản phẩm từ JSON"""
        try:
            with open(self.CATEGORIES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            default = ["Thực phẩm", "Đồ uống", "Gia dụng", "Mỹ phẩm", "Điện tử", "Khác"]
            with open(self.CATEGORIES_FILE, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
            return default

    def generate_product_id(self):
        """Sinh mã SP tự động"""
        if not self.products:
            return "SP001"
        last_id = max(int(p.product_id[2:]) for p in self.products)
        return f"SP{str(last_id + 1).zfill(3)}"

    # CRUD Sản phẩm
    def add_product(self, name: str, category: str, cost_price: float,
                    sell_price: float, stock_quantity: int,
                    min_threshold: int, unit: str) -> Product:
        """Thêm sản phẩm mới"""
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
        """Sửa thông tin sản phẩm"""
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
        """Xóa sản phẩm"""
        product = self.find_product(product_id)
        if not product:
            raise ValueError("Không tìm thấy sản phẩm")
        self.products.remove(product)
        self.save_products()

    def find_product(self, product_id: str) -> Product:
        """Tìm sản phẩm theo mã"""
        return next((p for p in self.products if p.product_id == product_id), None)

    def search_products(self, keyword: str) -> List[Product]:
        """Tìm kiếm theo tên hoặc danh mục"""
        return [p for p in self.products if keyword.lower() in p.name.lower() or keyword.lower() in p.category.lower()]
