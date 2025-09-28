# src/report/report.py
from __future__ import annotations

from src.utils.time_zone import VN_TZ
from typing import Any, Dict, List, Optional, Iterable, Union
from pathlib import Path
from datetime import datetime, timedelta
import csv
import json
import logging
from collections import defaultdict

from src.utils.validators import parse_iso_datetime

# Optional dependency cho Excel export
try:
    from openpyxl import Workbook
    _HAS_OPENPYXL = True
except ImportError:
    Workbook = None
    _HAS_OPENPYXL = False

# Logger riêng cho module
logger = logging.getLogger(__name__)

# Hằng số
DEFAULT_ENCODING = "utf-8"
DEFAULT_LOOKBACK_DAYS = 30
PREDICT_SOON_DAYS = 7  # số ngày coi như "sắp hết hàng"

# Types
AlertProduct = Dict[str, Any]
Alerts = Dict[str, Any]


# ==============================
# 🔧 Helper Functions
# ==============================

def safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    """Truy cập attr từ object hoặc dict an toàn."""
    if obj is None:
        return default
    return obj.get(attr, default) if isinstance(obj, dict) else getattr(obj, attr, default)


def compute_sale_rates(
    transactions: Iterable[Dict[str, Any]],
    product_ids: Optional[Union[str, Iterable[str]]] = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> Union[float, Dict[str, float]]:
    """
    Tính tốc độ bán trung bình (số lượng/ngày).

    - product_ids = None → trả về dict cho tất cả
    - product_ids = str  → trả về float cho sản phẩm đó
    - product_ids = list → trả về dict {pid: rate}
    """
    now = datetime.now(VN_TZ)
    start = now - timedelta(days=lookback_days)
    totals: Dict[str, float] = defaultdict(float)

    # Chuẩn hóa product_ids
    single_mode = isinstance(product_ids, str)
    pid_set = {product_ids} if single_mode else (set(product_ids) if product_ids else None)

    for t in transactions:
        if str(safe_get(t, "type", "OUT")).upper() not in ("OUT", "EXPORT"):
            continue

        pid = str(safe_get(t, "product_id") or "").strip()
        if not pid or (pid_set and pid not in pid_set):
            continue

        dt = parse_iso_datetime(safe_get(t, "date"), default_now=False)
        if not dt:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=VN_TZ)

        if dt >= start:
            totals[pid] += float(safe_get(t, "quantity", 0) or 0)

    rates = {pid: round(total / max(1.0, lookback_days), 2) for pid, total in totals.items()}

    return rates.get(product_ids, 0.0) if single_mode else rates


# ==============================
# 📊 Generate Alerts
# ==============================

def generate_low_stock_alerts(
    product_mgr,
    transaction_mgr: Optional[Any] = None,
    *,
    include_out_of_stock: bool = True,
    include_low_stock: bool = True,
    reorder_buffer: int = 0,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> Alerts:
    """Sinh cảnh báo tồn kho + dự báo."""
    now_iso = datetime.now(VN_TZ).isoformat()
    out_of_stock, low_stock = [], []
    total_needed = 0
    category_summary: Dict[str, Dict[str, int]] = {}

    # Lấy transactions nếu có
    transactions_all: List[Dict[str, Any]] = []
    if transaction_mgr:
        try:
            if hasattr(transaction_mgr, "list_transactions"):
                transactions_all = list(transaction_mgr.list_transactions())
            elif hasattr(transaction_mgr, "transactions"):
                transactions_all = list(transaction_mgr.transactions)
        except Exception as e:
            logger.warning("Không thể lấy transactions: %s", e)

    sale_rates = compute_sale_rates(transactions_all, lookback_days=lookback_days) if transactions_all else {}

    # Duyệt sản phẩm
    for p in product_mgr.list_products():
        pid = str(safe_get(p, "product_id"))
        qty = int(safe_get(p, "stock_quantity", 0) or 0)
        min_thr = int(safe_get(p, "min_threshold", 0) or 0)

        item: AlertProduct = {
            "product_id": pid,
            "name": safe_get(p, "name", ""),
            "category": safe_get(p, "category", "UNCATEGORIZED"),
            "stock_quantity": qty,
            "min_threshold": min_thr,
            "unit": safe_get(p, "unit", ""),
            "needed": max(0, (min_thr - qty) + max(0, reorder_buffer)) if qty < min_thr else 0,
        }

        # Thêm dự báo
        rate = sale_rates.get(pid)
        if rate:
            item["daily_sale_rate"] = rate
            days_left = qty / rate if rate > 0 else None
            if days_left:
                item["days_until_stockout"] = round(days_left, 2)
                item["predicted_out_soon"] = days_left <= PREDICT_SOON_DAYS

        # Phân loại
        cs = category_summary.setdefault(item["category"], {"out_of_stock": 0, "low_stock": 0})
        if qty == 0 and include_out_of_stock:
            out_of_stock.append(item)
            total_needed += item["needed"]
            cs["out_of_stock"] += 1
        elif 0 < qty <= min_thr and include_low_stock:
            low_stock.append(item)
            total_needed += item["needed"]
            cs["low_stock"] += 1

    return {
        "generated_at": now_iso,
        "out_of_stock": out_of_stock,
        "low_stock": low_stock,
        "total_needed": total_needed,
        "by_category": category_summary,
    }


# ==============================
# 📝 Format Reports
# ==============================

def format_alerts_text(alerts: Alerts) -> str:
    """Xuất cảnh báo tồn kho dạng text."""
    lines: List[str] = [
        "========== CẢNH BÁO TỒN KHO ==========",
        f"Thời điểm tạo báo cáo: {alerts.get('generated_at')}",
        "",
    ]

    def _section(title: str, items: List[AlertProduct], icon: str) -> List[str]:
        if not items:
            return [f"{icon} {title}: Không có.", ""]
        section = [f"{icon} {title} ({len(items)} sản phẩm):"]
        for p in items:
            base = f"- {p['product_id']}: {p['name']} ({p['stock_quantity']}/{p['min_threshold']} {p.get('unit','')}) - Cần nhập: {p['needed']}"
            extras = []
            if "daily_sale_rate" in p:
                extras.append(f"bán/ngày={p['daily_sale_rate']}")
            if "days_until_stockout" in p:
                extras.append(f"dự báo hết={p['days_until_stockout']} ngày")
            if extras:
                base += " | " + "; ".join(extras)
            section.append(base)
        return section + [""]

    lines.extend(_section("HẾT HÀNG", alerts.get("out_of_stock", []), "🚨"))
    lines.extend(_section("SẮP HẾT HÀNG", alerts.get("low_stock", []), "⚠️"))

    lines.append(f"Tổng cần nhập (tất cả sản phẩm): {alerts.get('total_needed', 0)}")
    lines.append("")

    if alerts.get("by_category"):
        lines.append("📂 Thống kê theo danh mục:")
        for cat, stats in alerts["by_category"].items():
            lines.append(f"- {cat}: Hết hàng={stats.get('out_of_stock',0)}; Sắp hết={stats.get('low_stock',0)}")

    return "\n".join(lines)


# ==============================
# 💾 Export Functions
# ==============================

def write_low_stock_alerts(
    alerts: Alerts,
    *,
    out_txt_path: Optional[str] = "data/low_stock_alert.txt",
    out_csv_path: Optional[str] = None,
    encoding: str = DEFAULT_ENCODING,
) -> None:
    """Ghi báo cáo ra TXT và CSV."""
    if out_txt_path:
        path = Path(out_txt_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(format_alerts_text(alerts), encoding=encoding)

    if out_csv_path:
        path = Path(out_csv_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "product_id", "name", "category", "stock_quantity", "min_threshold",
            "unit", "needed", "type", "daily_sale_rate", "days_until_stockout", "predicted_out_soon"
        ]
        with path.open("w", encoding=encoding, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for label, items in (("OUT_OF_STOCK", alerts.get("out_of_stock", [])),
                                 ("LOW_STOCK", alerts.get("low_stock", []))):
                for item in items:
                    row = {k: item.get(k, "") for k in fieldnames}
                    row["type"] = label
                    writer.writerow(row)


def alerts_to_json(alerts: Alerts, *, ensure_ascii: bool = False) -> str:
    """Trả về chuỗi JSON (phục vụ API/web)."""
    return json.dumps(alerts, ensure_ascii=ensure_ascii, indent=2, default=str)


def export_alerts_xlsx(alerts: Alerts, out_xlsx_path: str = "data/low_stock_alert.xlsx") -> None:
    """Xuất alerts sang Excel (3 sheet)."""
    if not _HAS_OPENPYXL:
        raise RuntimeError("openpyxl chưa được cài.")

    wb = Workbook()
    headers = ["product_id", "name", "category", "stock_quantity", "min_threshold",
               "unit", "needed", "daily_sale_rate", "days_until_stockout", "predicted_out_soon"]

    # Out of stock
    ws_oos = wb.active
    ws_oos.title = "OutOfStock"
    ws_oos.append(headers)
    for item in alerts.get("out_of_stock", []):
        ws_oos.append([item.get(h, "") for h in headers])

    # Low stock
    ws_low = wb.create_sheet("LowStock")
    ws_low.append(headers)
    for item in alerts.get("low_stock", []):
        ws_low.append([item.get(h, "") for h in headers])

    # By category
    ws_cat = wb.create_sheet("ByCategory")
    ws_cat.append(["category", "out_of_stock", "low_stock"])
    for cat, stats in alerts.get("by_category", {}).items():
        ws_cat.append([cat, stats.get("out_of_stock", 0), stats.get("low_stock", 0)])

    Path(out_xlsx_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out_xlsx_path))


# ==============================
# 🚀 Main Entry
# ==============================

def run_and_persist(
    product_mgr,
    transaction_mgr: Optional[Any] = None,
    *,
    reorder_buffer: int = 0,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    out_txt_path: str = "data/low_stock_alert.txt",
    out_csv_path: Optional[str] = "data/low_stock_alert.csv",
    out_xlsx_path: Optional[str] = "data/low_stock_alert.xlsx",
) -> Alerts:
    """Hàm chính: sinh cảnh báo và ghi ra file .txt, .csv, .xlsx."""
    alerts = generate_low_stock_alerts(
        product_mgr,
        transaction_mgr=transaction_mgr,
        reorder_buffer=reorder_buffer,
        lookback_days=lookback_days,
    )
    write_low_stock_alerts(alerts, out_txt_path=out_txt_path, out_csv_path=out_csv_path)
    if out_xlsx_path:
        try:
            export_alerts_xlsx(alerts, out_xlsx_path)
        except Exception as e:
            logger.warning("Không thể export Excel: %s", e)
    return alerts