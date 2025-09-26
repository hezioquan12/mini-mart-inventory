# src/inventory/product.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional, Dict

from src.utils.validators import to_decimal, parse_iso_datetime, ensure_int


@dataclass
class Product:
    """
    Model cho một sản phẩm trong kho.
    created_date / last_updated luôn là timezone-aware (UTC).
    """
    product_id: str
    name: str
    category: str
    cost_price: Decimal
    sell_price: Decimal
    stock_quantity: int
    min_threshold: int
    unit: str
    created_date: Optional[datetime] = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: Optional[datetime] = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        # Basic normalize + validate product_id
        self.product_id = str(self.product_id).strip()
        if not self.product_id:
            raise ValueError("product_id không được để trống")

        self.name = str(self.name) if self.name is not None else ""
        self.category = str(self.category) if self.category is not None else ""
        self.unit = str(self.unit) if self.unit is not None else ""

        # Convert prices / ints
        self.cost_price = to_decimal(self.cost_price)
        self.sell_price = to_decimal(self.sell_price)
        self.stock_quantity = ensure_int(self.stock_quantity)
        self.min_threshold = ensure_int(self.min_threshold)

        # Validate ranges using Decimal("0") for clarity
        if self.stock_quantity < 0:
            raise ValueError("Số lượng tồn phải >= 0")
        if self.min_threshold < 0:
            raise ValueError("Ngưỡng cảnh báo phải >= 0")
        if self.cost_price < Decimal("0"):
            raise ValueError("Giá nhập phải >= 0")
        if self.sell_price < self.cost_price:
            raise ValueError("Giá bán phải >= giá nhập")

        # Ensure timezone-aware datetimes (use parse helper and default to now)
        self.created_date = parse_iso_datetime(self.created_date, default_now=True)
        self.last_updated = parse_iso_datetime(self.last_updated, default_now=True)

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
            cost_price=to_decimal(data.get("cost_price") or 0),
            sell_price=to_decimal(data.get("sell_price") or 0),
            stock_quantity=ensure_int(data.get("stock_quantity") or 0),
            min_threshold=ensure_int(data.get("min_threshold") or 0),
            unit=str(data.get("unit") or ""),
            created_date=parse_iso_datetime(data.get("created_date")),
            last_updated=parse_iso_datetime(data.get("last_updated")),
        )

    def to_csv_row(self) -> Dict[str, Any]:
        return self.to_dict()

    @classmethod
    def from_csv_row(cls, row: Dict[str, Any]) -> "Product":
        # map empty strings to None so from_dict can handle defaults
        cleaned = {k: (v if v != "" else None) for k, v in row.items()}
        return cls.from_dict(cleaned)

    # ---------- convenience mutators ----------
    def adjust_stock(self, delta: int) -> None:
        """
        Thêm/giảm tồn (delta có thể âm). Cập nhật last_updated.
        Raises:
            ValueError nếu kết quả dẫn đến stock < 0.
        """
        # accept delta as int-like
        try:
            delta_int = int(delta)
        except (TypeError, ValueError):
            raise ValueError("Delta phải là số nguyên hợp lệ")
        new_qty = self.stock_quantity + delta_int
        if new_qty < 0:
            raise ValueError("Thao tác này sẽ làm số lượng < 0")
        self.stock_quantity = new_qty
        self.last_updated = datetime.now(timezone.utc)

    def update_prices(self, cost_price: Any = None, sell_price: Any = None) -> None:
        """
        Cập nhật giá (cả hai hoặc một trong hai). Validate: sell_price >= cost_price.
        Accepts values that to_decimal can parse.
        """
        new_cost = self.cost_price
        new_sell = self.sell_price

        if cost_price is not None:
            new_cost = to_decimal(cost_price)
            if new_cost < Decimal("0"):
                raise ValueError("Giá nhập phải >= 0")
        if sell_price is not None:
            new_sell = to_decimal(sell_price)

        if new_sell < new_cost:
            raise ValueError("Giá bán phải >= giá nhập")

        self.cost_price = new_cost
        self.sell_price = new_sell
        self.last_updated = datetime.now(timezone.utc)
