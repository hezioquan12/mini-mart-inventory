from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Any, Optional

def normalize_name(name: Any) -> str:
    if name is None:
        return ""
    return str(name).strip().lower()

def to_decimal(value: Any) -> Decimal:
    try:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Giá nhập/giá bán phải là số hợp lệ.")

def parse_iso_datetime(value: Optional[Any]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))

def ensure_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError("Trường số phải là số nguyên hợp lệ.")