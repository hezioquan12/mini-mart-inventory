# src/inventory/transaction.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
import uuid
import logging
from src.utils.time_zone import VN_TZ
from src.utils.validators import ensure_int, parse_iso_datetime

logger = logging.getLogger(__name__)


@dataclass
class Transaction:
    """
    Model cho một giao dịch nhập/xuất.
    - trans_type: "IMPORT" hoặc "EXPORT"
    - date: timezone-aware datetime (UTC)
    """
    transaction_id: str
    product_id: str
    trans_type: str  # expected "IMPORT" or "EXPORT"
    quantity: int
    date: Optional[datetime] = field(default_factory=lambda: datetime.now(VN_TZ))
    note: str = ""

    def __post_init__(self) -> None:
        # ensure transaction_id exists
        if not self.transaction_id:
            self.transaction_id = f"T{uuid.uuid4().hex}"

        # normalize / validate fields
        self.product_id = str(self.product_id).strip()
        if not self.product_id:
            raise ValueError("product_id không được để trống")

        self.trans_type = str(self.trans_type).upper()
        if self.trans_type not in ("IMPORT", "EXPORT"):
            raise ValueError("Loại giao dịch phải là 'IMPORT' hoặc 'EXPORT'")

        # validate quantity
        self.quantity = ensure_int(self.quantity)
        if self.quantity <= 0:
            raise ValueError("Số lượng giao dịch phải > 0")

        # parse/normalize date to timezone-aware datetime (UTC)
        # parse_iso_datetime(..., default_now=True) đảm bảo trả về timezone-aware datetime
        dt = parse_iso_datetime(self.date, default_now=True)
        if dt is None:
            raise ValueError("date must not be None")
        self.date = dt

        # ensure note is string
        self.note = str(self.note or "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "product_id": self.product_id,
            "trans_type": self.trans_type,
            "quantity": self.quantity,
            "date": self.date.isoformat() if self.date else None,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        """
        Tạo Transaction từ dict (hỗ trợ nhiều tên trường cho backward-compat).
        """
        tid = data.get("transaction_id") or f"T{uuid.uuid4().hex}"
        pid = data.get("product_id") or data.get("product") or data.get("productId")
        ttype = data.get("trans_type") or data.get("type") or data.get("Type")
        qty_raw = data.get("quantity") or data.get("qty") or data.get("Quantity")
        date_raw = data.get("date") or data.get("created_at") or data.get("datetime")
        note = data.get("note", "")

        if not pid or str(pid).strip() == "":
            raise ValueError("Missing product_id in transaction data")
        if not ttype:
            raise ValueError("Missing transaction type in transaction data")

        qty = ensure_int(qty_raw)
        if qty <= 0:
            raise ValueError(f"Quantity must be > 0, got {qty}")

        # parse datetime — use default_now=True to get timezone-aware now if missing/invalid
        dt = parse_iso_datetime(date_raw, default_now=True)

        return cls(
            transaction_id=str(tid),
            product_id=str(pid).strip(),
            trans_type=str(ttype).upper(),
            quantity=qty,
            date=dt,
            note=str(note or ""),
        )
