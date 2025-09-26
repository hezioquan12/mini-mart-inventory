from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Any, Optional
import warnings


def normalize_name(name: Any, ascii_only: bool = False) -> str:
    """
    Chuẩn hóa chuỗi để so sánh/tìm kiếm.

    Args:
        name: Chuỗi hoặc giá trị cần chuẩn hóa.
        ascii_only: Nếu True sẽ loại bỏ dấu và ký tự đặc biệt.

    Returns:
        Chuỗi đã chuẩn hóa.
    """
    if name is None:
        return ""

    s = " ".join(str(name).strip().lower().split())  # loại bỏ khoảng trắng thừa

    if ascii_only:
        unidecode_func = lambda x: x  # fallback mặc định
        try:
            import unidecode
            unidecode_func = unidecode.unidecode
        except ImportError:
            warnings.warn("unidecode không được cài đặt, bỏ qua ascii_only.")

        s = unidecode_func(s)

    return s


def to_decimal(value: Any) -> Decimal:
    """
    Ép về Decimal, hỗ trợ cả input dạng str với dấu phẩy.

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
    Parse ISO datetime, trả về None hoặc thời điểm hiện tại nếu lỗi.

    Args:
        value: Chuỗi datetime hoặc datetime object.
        default_now: Nếu True trả về datetime hiện tại khi value None hoặc lỗi.

    Returns:
        datetime object (timezone-aware) hoặc None.

    Raises:
        ValueError: Nếu định dạng datetime không hợp lệ.
    """
    if value is None:
        return datetime.now(timezone.utc) if default_now else None

    if isinstance(value, datetime):
        # Nếu là naive datetime → convert thành timezone-aware UTC
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        if default_now:
            return datetime.now(timezone.utc)
        raise ValueError(f"Invalid datetime format: {value!r}")


def ensure_int(value: Any, must_be_positive: bool = False) -> int:
    """
    Ép về int, tùy chọn bắt buộc >0.

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
