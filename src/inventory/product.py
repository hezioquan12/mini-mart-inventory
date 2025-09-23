from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_date(value) -> datetime:
    if value is None:
        return datetime.now()
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        # treat as timestamp
        return datetime.fromtimestamp(value)
    if isinstance(value, str):
        s = value.strip()
        # try a few common formats
        fmts = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y/%m/%d")
        for f in fmts:
            try:
                return datetime.strptime(s, f)
            except Exception:
                continue
    raise ValueError(f"Không thể parse ngày từ: {value!r}")


def format_date(dt: datetime) -> str:
    return dt.strftime(DATETIME_FORMAT)


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
    created_date: datetime = field(default_factory=lambda: datetime.now())
    last_updated: datetime = field(default_factory=lambda: datetime.now())

    def __post_init__(self):
        # enforce types and basic invariants
        try:
            # Decimal conversion if needed
            if not isinstance(self.cost_price, Decimal):
                self.cost_price = Decimal(str(self.cost_price))
            if not isinstance(self.sell_price, Decimal):
                self.sell_price = Decimal(str(self.sell_price))
        except (InvalidOperation, ValueError) as e:
            raise ValueError("Giá nhập/giá bán phải là số hợp lệ.") from e

        # ints
        self.stock_quantity = int(self.stock_quantity)
        self.min_threshold = int(self.min_threshold)

        if self.min_threshold < 0:
            raise ValueError("Ngưỡng cảnh báo phải ≥ 0")
        if self.cost_price < 0:
            raise ValueError("Giá nhập phải ≥ 0")
        if self.sell_price < 0:
            raise ValueError("Giá bán phải ≥ 0")
        # Note: sell_price >= cost_price validation can be done here or in ProductManager.
        # We prefer to enforce it here to make Product objects always valid:
        if self.sell_price < self.cost_price:
            raise ValueError("Giá bán phải ≥ giá nhập.")

        # Ensure created_date/last_updated are datetime
        if not isinstance(self.created_date, datetime):
            self.created_date = parse_date(self.created_date)
        if not isinstance(self.last_updated, datetime):
            self.last_updated = parse_date(self.last_updated)

    # ---------- factory + serialization ----------
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Product":
        """Create Product from a CSV/DB row (dict). Accepts strings and converts."""
        return cls(
            product_id=str(d.get("product_id", "")).strip(),
            name=str(d.get("name", "")).strip(),
            category=str(d.get("category", "")).strip(),
            cost_price=Decimal(str(d.get("cost_price", "0"))),
            sell_price=Decimal(str(d.get("sell_price", "0"))),
            stock_quantity=int(d.get("stock_quantity", 0)),
            min_threshold=int(d.get("min_threshold", 0)),
            unit=str(d.get("unit", "")).strip(),
            created_date=d.get("created_date") or datetime.now(),
            last_updated=d.get("last_updated") or datetime.now(),
        )

    def to_csv_row(self) -> Dict[str, str]:
        """Return a dict with strings suitable for csv.DictWriter."""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "category": self.category,
            "cost_price": f"{self.cost_price:.2f}",
            "sell_price": f"{self.sell_price:.2f}",
            "stock_quantity": str(self.stock_quantity),
            "min_threshold": str(self.min_threshold),
            "unit": self.unit,
            "created_date": format_date(self.created_date),
            "last_updated": format_date(self.last_updated),
        }

    # ---------- business logic ----------
    def update_stock(self, quantity: int, transaction_type: str = "nhập"):
        """Update stock. transaction_type: 'nhập' or 'xuất'."""
        qty = int(quantity)
        tt = transaction_type.strip().lower()
        if tt in ("nhập", "nhap", "in"):
            self.stock_quantity += qty
        elif tt in ("xuất", "xuat", "out"):
            if qty > self.stock_quantity:
                raise ValueError(f"Không đủ hàng: tồn hiện tại {self.stock_quantity}")
            self.stock_quantity -= qty
        else:
            raise ValueError("transaction_type phải là 'nhập' hoặc 'xuất'")
        self.last_updated = datetime.now()

    def get_stock_status(self) -> str:
        if self.stock_quantity == 0:
            return "🚨 Hết hàng"
        if self.stock_quantity <= self.min_threshold:
            return "⚠️ Sắp hết"
        return "Bình thường"

    def profit_margin_percent(self) -> float:
        if self.cost_price == 0:
            return 0.0
        return float((self.sell_price - self.cost_price) / self.cost_price * Decimal("100"))

    def __repr__(self) -> str:
        return f"<Product {self.product_id} {self.name} ({self.category}) SL={self.stock_quantity}>"
