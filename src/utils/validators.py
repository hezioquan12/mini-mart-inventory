from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Any, Optional
import warnings


def normalize_name(name: Any, ascii_only: bool = False) -> str:
    """
    Chuẩn hóa chuỗi để so sánh/tìm kiếm.

    Loại bỏ khoảng trắng thừa, chuyển thành chữ thường.
    Nếu ascii_only=True sẽ loại bỏ dấu và ký tự đặc biệt.

    Args:
        name: Chuỗi hoặc giá trị cần chuẩn hóa.
        ascii_only: Nếu True loại bỏ dấu và ký tự đặc biệt.

    Returns:
        Chuỗi đã chuẩn hóa.
    """
    if name is None:
        return ""

    s = " ".join(str(name).strip().lower().split())  # loại bỏ khoảng trắng thừa

    if ascii_only:
        try:
            import unidecode  # noqa: F401
            s = unidecode.unidecode(s)
        except ImportError:
            warnings.warn("unidecode không được cài đặt, bỏ qua ascii_only.")

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
        return datetime.now(timezone.utc) if default_now else None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        if default_now:
            return datetime.now(timezone.utc)
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
