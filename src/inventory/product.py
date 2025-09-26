from dataclasses import dataclass, field
from datetime import datetime,UTC
from decimal import Decimal
from typing import Any, Optional, Dict

from src.utils.validators import to_decimal, parse_iso_datetime, ensure_int

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
    created_date: Optional[datetime] = field(default_factory=lambda: datetime.now(UTC))
    last_updated: Optional[datetime] = field(default_factory=lambda: datetime.now(UTC))

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
        self.created_date = parse_iso_datetime(self.created_date) if self.created_date is not None else datetime.now(
            UTC)
        self.last_updated = parse_iso_datetime(self.last_updated) if self.last_updated is not None else datetime.now(
            UTC)

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
        if not data.get("product_id"):
            raise ValueError("Thiếu product_id trong dữ liệu")

        return cls(
            product_id=str(data.get("product_id")),
            name=str(data.get("name") or ""),
            category=str(data.get("category") or ""),
            cost_price=to_decimal(data.get("cost_price") or 0),  # ép thành Decimal
            sell_price=to_decimal(data.get("sell_price") or 0),  # ép thành Decimal
            stock_quantity=ensure_int(data.get("stock_quantity") or 0),  # ép int
            min_threshold=ensure_int(data.get("min_threshold") or 0),  # ép int
            unit=str(data.get("unit") or ""),
            created_date=parse_iso_datetime(data.get("created_date")),
            last_updated=parse_iso_datetime(data.get("last_updated")),
        )

    def to_csv_row(self) -> Dict[str, Any]:
        return self.to_dict()

    @classmethod
    def from_csv_row(cls, row: Dict[str, Any]) -> "Product":
        return cls.from_dict({k: (v if v != "" else None) for k, v in row.items()})