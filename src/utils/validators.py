from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Any, Optional
from src.utils.time_zone import VN_TZ
import unicodedata
import re

def normalize_name(name: Any, ascii_only: bool = False) -> str:
    """
    Chuẩn hóa chuỗi để so sánh/tìm kiếm.
    - Chuyển thường
    - Loại bỏ khoảng trắng thừa
    """
    if name is None:
        return ""

    s = " ".join(str(name).strip().lower().split())  # loại bỏ khoảng trắng thừa

    if ascii_only:
        # Loại bỏ dấu tiếng Việt bằng Unicode normalization
        nfkd = unicodedata.normalize("NFKD", s)
        s = "".join([c for c in nfkd if not unicodedata.combining(c)])
        # Giữ lại chữ, số, khoảng trắng
        s = re.sub(r"[^a-z0-9\s]", "", s)

    return s

def to_decimal(value: Any) -> Decimal:
    """
    Ép value về Decimal, hỗ trợ cả input dạng str với dấu phẩy.

    Args:
        value: Giá trị số hoặc chuỗi cần chuyển.

    Returns:
        Decimal của giá trị.

    Raises:
        ValueError: Nếu không thể chuyển về Decimal.
    """
    try:
        if isinstance(value, Decimal):
            return value
        s = str(value).strip().replace(",", ".")
        return Decimal(s)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"Giá trị không hợp lệ cho Decimal: {value!r}")


def parse_iso_datetime(value: Optional[Any], default_now: bool = False) -> Optional[datetime]:
    """
    Parse ISO datetime thành datetime object timezone-aware (UTC).

    Nếu parsing lỗi hoặc value=None:
      - trả về None nếu default_now=False
      - trả về datetime.now(timezone.utc) nếu default_now=True

    Args:
        value: Chuỗi datetime hoặc datetime object.
        default_now: Nếu True trả về datetime hiện tại khi value None hoặc lỗi.

    Returns:
        datetime object (timezone-aware) hoặc None.

    Raises:
        ValueError: Nếu định dạng datetime không hợp lệ.
    """
    if value is None:
        return datetime.now(VN_TZ) if default_now else None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=VN_TZ)

    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=VN_TZ)
    except Exception:
        if default_now:
            return datetime.now(VN_TZ)
        raise ValueError(f"Invalid datetime format: {value!r}")


def ensure_int(value: Any, must_be_positive: bool = False) -> int:
    """
    Ép value về int.

    Args:
        value: Giá trị cần ép về int.
        must_be_positive: Nếu True bắt buộc >0.

    Returns:
        int đã ép.

    Raises:
        ValueError: Nếu không thể chuyển hoặc không thỏa điều kiện.
    """
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"Trường số phải là số nguyên hợp lệ: {value!r}")

    if must_be_positive and n <= 0:
        raise ValueError(f"Giá trị phải >0, got {n}")
    return n
