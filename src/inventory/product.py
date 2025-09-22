from datetime import datetime
from typing import Optional


class Product:
    """Model cho 1 sản phẩm."""
    def __init__(
        self,
        product_id: str,
        name: str,
        category: str,
        cost_price: float,
        sell_price: float,
        stock_quantity: int,
        min_threshold: int,
        unit: str,
        created_date: Optional[str] = None,
        last_updated: Optional[str] = None,
    ):
        self.product_id = product_id
        self.name = name
        self.category = category
        self.cost_price = float(cost_price)
        self.sell_price = float(sell_price)
        self.stock_quantity = int(stock_quantity)
        self.min_threshold = int(min_threshold)
        self.unit = unit
        self.created_date = created_date or datetime.now().strftime("%Y-%m-%d")
        self.last_updated = last_updated or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def update_stock(self, quantity: int, transaction_type: str):
        """
        Cập nhật tồn kho.
        transaction_type: "nhập" hoặc "xuất"
        """
        quantity = int(quantity)
        if transaction_type == "nhập":
            self.stock_quantity += quantity
        elif transaction_type == "xuất":
            if quantity > self.stock_quantity:
                raise ValueError(f"Không đủ hàng: tồn hiện tại {self.stock_quantity}")
            self.stock_quantity -= quantity
        else:
            raise ValueError("transaction_type phải là 'nhập' hoặc 'xuất'")
        self.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_stock_status(self) -> str:
        if self.stock_quantity == 0:
            return "🚨 Hết hàng"
        if self.stock_quantity <= self.min_threshold:
            return "⚠️ Sắp hết"
        return "Bình thường"

    def profit_margin_percent(self) -> float:
        """Tính tỷ lệ lợi nhuận theo cost_price."""
        if self.cost_price == 0:
            return 0.0
        return (self.sell_price - self.cost_price) / self.cost_price * 100.0

    def to_dict(self) -> dict:
        """Chuyển object sang dict để ghi CSV."""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "category": self.category,
            "cost_price": f"{self.cost_price:.2f}",
            "sell_price": f"{self.sell_price:.2f}",
            "stock_quantity": str(self.stock_quantity),
            "min_threshold": str(self.min_threshold),
            "unit": self.unit,
            "created_date": self.created_date,
            "last_updated": self.last_updated,
        }

    def __repr__(self) -> str:
        return f"<Product {self.product_id} {self.name} ({self.category}) SL={self.stock_quantity}>"
