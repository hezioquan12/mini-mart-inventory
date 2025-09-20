from datetime import datetime

class Product:
    def __init__(self, product_id: str, name: str, category: str,
                 cost_price: float, sell_price: float,
                 stock_quantity: int, min_threshold: int, unit: str,
                 created_date: str = None, last_updated: str = None):
        self.product_id = product_id
        self.name = name
        self.category = category
        self.cost_price = cost_price
        self.sell_price = sell_price
        self.stock_quantity = stock_quantity
        self.min_threshold = min_threshold
        self.unit = unit
        self.created_date = created_date or datetime.now().strftime("%d/%m/%Y")
        self.last_updated = last_updated or datetime.now().strftime("%d/%m/%Y %H:%M")

    def update_stock(self, quantity: int, transaction_type: str):
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
        if self.stock_quantity == 0:
            return "🚨 Hết hàng"
        elif self.stock_quantity <= self.min_threshold:
            return "⚠️ Sắp hết"
        else:
            return "Bình thường"

    def to_dict(self):
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
