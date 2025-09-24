from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Dict

from validators import to_decimal, parse_iso_datetime, ensure_int

@dataclass
class Product:
    product_id: str
    name: str
    category: str
    cost_price: Decimal
    sell_price: Decimal
    stock_quantity: int
    min_threshold: int
    unit: str
    created_date: Optional[datetime] = field(default_factory=datetime.utcnow)
    last_updated: Optional[datetime] = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        self.name = str(self.name) if self.name is not None else ""
        self.category = str(self.category) if self.category is not None else ""
        self.unit = str(self.unit) if self.unit is not None else ""
        self.cost_price = to_decimal(self.cost_price)
        self.sell_price = to_decimal(self.sell_price)
        self.stock_quantity = ensure_int(self.stock_quantity)
        self.min_threshold = ensure_int(self.min_threshold)
        if self.stock_quantity < 0:
            raise ValueError("Số lượng tồn phải >= 0")
        if self.min_threshold < 0:
            raise ValueError("Ngưỡng cảnh báo phải >= 0")
        if self.cost_price < 0:
            raise ValueError("Giá nhập phải >= 0")
        if self.sell_price < self.cost_price:
            raise ValueError("Giá bán phải >= giá nhập")
        self.created_date = parse_iso_datetime(self.created_date) if self.created_date is not None else datetime.utcnow()
        self.last_updated = parse_iso_datetime(self.last_updated) if self.last_updated is not None else datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "category": self.category,
            "cost_price": str(self.cost_price),
            "sell_price": str(self.sell_price),
            "stock_quantity": self.stock_quantity,
            "min_threshold": self.min_threshold,
            "unit": self.unit,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Product":
        return cls(
            product_id=data.get("product_id"),
            name=data.get("name", ""),
            category=data.get("category", ""),
            cost_price=data.get("cost_price", "0"),
            sell_price=data.get("sell_price", "0"),
            stock_quantity=data.get("stock_quantity", 0),
            min_threshold=data.get("min_threshold", 0),
            unit=data.get("unit", ""),
            created_date=data.get("created_date"),
            last_updated=data.get("last_updated"),
        )

    def to_csv_row(self) -> Dict[str, Any]:
        return self.to_dict()

    @classmethod
    def from_csv_row(cls, row: Dict[str, Any]) -> "Product":
        return cls.from_dict({k: (v if v != "" else None) for k, v in row.items()})