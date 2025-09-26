from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

@dataclass
class Transaction:
    transaction_id: str
    product_id: str
    type: str  # "IMPORT" hoặc "EXPORT"
    quantity: int
    date: datetime = field(default_factory=datetime.utcnow)
    note: str = ""

    def __post_init__(self):
        if self.type not in ("IMPORT", "EXPORT"):
            raise ValueError("Loại giao dịch phải là IMPORT hoặc EXPORT")
        if self.quantity <= 0:
            raise ValueError("Số lượng phải > 0")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "product_id": self.product_id,
            "type": self.type,
            "quantity": self.quantity,
            "date": self.date.isoformat(),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        return cls(
            transaction_id=data.get("transaction_id"),
            product_id=data.get("product_id"),
            type=data.get("type"),
            quantity=int(data.get("quantity")),
            date=datetime.fromisoformat(data.get("date")),
            note=data.get("note", ""),
        )
