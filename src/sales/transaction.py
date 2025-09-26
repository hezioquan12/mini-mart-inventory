# transaction.py
from dataclasses import dataclass, field
from datetime import datetime,UTC
from typing import Any, Dict
import uuid

from src.utils.validators import ensure_int, parse_iso_datetime


@dataclass
class Transaction:
    transaction_id: str
    product_id: str
    trans_type: str  # expected "IMPORT" or "EXPORT"
    quantity: int
    date: datetime = field(default_factory=lambda: datetime.now(UTC))
    note: str = ""

    def __post_init__(self):
        if not self.transaction_id:
            self.transaction_id = f"T{uuid.uuid4().hex}"

        self.product_id = str(self.product_id).strip()
        self.trans_type = str(self.trans_type).upper()
        if self.trans_type not in ("IMPORT", "EXPORT"):
            raise ValueError("Loại giao dịch phải là 'IMPORT' hoặc 'EXPORT'")

        self.quantity = ensure_int(self.quantity)
        if self.quantity <= 0:
            raise ValueError("Số lượng giao dịch phải > 0")

        self.date = parse_iso_datetime(self.date) or datetime.now(UTC)
        if self.note is None:
            self.note = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "product_id": self.product_id,
            "trans_type": self.trans_type,
            "quantity": self.quantity,  # giữ int, để JSON chuẩn hơn
            "date": self.date.isoformat(),
            "note": self.note or "",
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        tid = data.get("transaction_id") or f"T{uuid.uuid4().hex}"
        pid = data.get("product_id")
        ttype = data.get("trans_type") or data.get("type") or data.get("Type")
        qty_raw = data.get("quantity") or data.get("qty") or data.get("Quantity")
        date_raw = data.get("date")
        note = data.get("note", "")

        if not pid or str(pid).strip() == "":
            raise ValueError("Missing product_id in transaction row")
        if not ttype:
            raise ValueError("Missing transaction type in transaction row")

        qty = ensure_int(qty_raw)
        if qty <= 0:
            raise ValueError(f"Quantity must be > 0, got {qty}")

        dt = parse_iso_datetime(date_raw) or datetime.now(UTC)

        return cls(
            transaction_id=str(tid),
            product_id=str(pid),
            trans_type=str(ttype).upper(),
            quantity=qty,
            date=dt,
            note=str(note),
        )

