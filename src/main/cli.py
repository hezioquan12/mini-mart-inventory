from __future__ import annotations
#!/usr/bin/env python3
# src/report_and_sreach/report.py
from src.utils.time_zone import VN_TZ
from typing import Any, Dict, List, Optional, Iterable, Union
#!/usr/bin/env python3
# src/cli/cli_vn.py
"""
CLI tiếng Việt cho Mini-mart Inventory
- Menu chính theo yêu cầu (quản lý sản phẩm, nhập/xuất, báo cáo, xuất dữ liệu)
- Xuất 3 file: inventory_report.xlsx (hoặc .csv), sales_summary_MM_YYYY.csv, low_stock_alert.txt
- Không có phần biểu đồ (bỏ để tránh tính năng rỗng)
"""
try:
    from src.report_and_sreach.report import (
        compute_financial_summary,
        format_financial_summary_text,
    )
except Exception:
    compute_financial_summary = None
    format_financial_summary_text = None
import sys
import traceback
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

# -------- Robust imports (thân thiện với nhiều cấu trúc project) ----------
try:
    from src.inventory.product_manager import ProductManager
    from src.inventory.category_manager import CategoryManager
    from src.sales.transaction_manager import TransactionManager
    try:
        from src.report_and_sreach.report import generate_low_stock_alerts, export_alerts_xlsx, write_low_stock_alerts, format_alerts_text
    except Exception:
        # nếu module report không khớp, we'll compute inline
        generate_low_stock_alerts = None
        export_alerts_xlsx = None
        write_low_stock_alerts = None
        format_alerts_text = None

    try:
        from src.utils.time_zone import VN_TZ
    except Exception:
        import datetime as _dt
        VN_TZ = _dt.timezone.utc  # fallback

except Exception as e:
    print("Lỗi import module dự án. Hãy chạy script từ thư mục project root và kiểm tra PYTHONPATH.")
    print("Import error:", e)
    traceback.print_exc()
    sys.exit(1)

# Optional dependency
try:
    from openpyxl import Workbook
    HAS_OPENPYXL = True
except Exception:
    Workbook = None
    HAS_OPENPYXL = False

# -------- Helpers ----------
DATA_DIR = Path("data")
REPORTS_DIR = Path("reports")
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)


def fmt_vnd(x: Any) -> str:
    """Định dạng tiền VND (thô)."""
    try:
        v = Decimal(str(x))
    except Exception:
        return str(x)
    # no currency symbol to keep simple
    return f"{int(v):,}"


def status_for_product(p) -> str:
    if p.stock_quantity <= 0:
        return "HẾT HÀNG"
    if p.stock_quantity <= p.min_threshold:
        return "SẮP HẾT"
    return "BÌNH THƯỜNG"


def print_products_table(products: List[Any]) -> None:
    if not products:
        print("(Không có sản phẩm)")
        return
    print(f"{'Mã SP':8} {'Tên':30} {'Danh mục':12} {'Giá nhập':>10} {'Giá bán':>10} {'Tồn':>6} {'Ngưỡng':>7} {'Trạng thái':>12}")
    print("-" * 100)
    for p in products:
        print(f"{p.product_id:8} {p.name[:30]:30} {p.category[:12]:12} {fmt_vnd(p.cost_price):>10} {fmt_vnd(p.sell_price):>10} {p.stock_quantity:6} {p.min_threshold:7} {status_for_product(p):>12}")
    print()


# -------- Instantiate managers ----------
category_mgr = CategoryManager(str(DATA_DIR / "categories.json"))
product_mgr = ProductManager(str(DATA_DIR / "products.json"), category_mgr=category_mgr)
transaction_mgr = TransactionManager(str(DATA_DIR / "transactions.csv"), product_mgr)


# -------- Report calculators (in-code fallback) ----------
def sales_summary_month(year: int, month: int) -> Dict[str, Any]:
    """
    Tính doanh thu/lợi nhuận/top-seller cho tháng/year.
    Trả về dict bao gồm totals và breakdown.
    """
    # collect export transactions in target month
    txs = [t for t in transaction_mgr.list_transactions() if t.trans_type == "EXPORT"]
    # filter by month/year with timezone awareness
    def in_month(t):
        dt = getattr(t, "date", None)
        if dt is None:
            return False
        try:
            # convert to VN_TZ naive handling: if tzinfo none assume VN_TZ
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=VN_TZ)
            local = dt.astimezone(VN_TZ)
        except Exception:
            local = dt
        return local.year == year and local.month == month

    txs_month = [t for t in txs if in_month(t)]
    if not txs_month:
        return {"year": year, "month": month, "total_revenue": 0, "total_cost": 0, "profit": 0, "by_category": {}, "top_products": []}

    total_revenue = Decimal(0)
    total_cost = Decimal(0)
    by_cat: Dict[str, Decimal] = {}
    per_product: Dict[str, Dict[str, Any]] = {}

    for t in txs_month:
        pid = t.product_id
        qty = t.quantity
        try:
            p = product_mgr.get_product(pid)
        except Exception:
            # product missing -> skip / or handle
            continue
        revenue = Decimal(str(p.sell_price)) * Decimal(qty)
        cost = Decimal(str(p.cost_price)) * Decimal(qty)
        total_revenue += revenue
        total_cost += cost
        by_cat[p.category] = by_cat.get(p.category, Decimal(0)) + revenue
        pr = per_product.setdefault(pid, {"name": p.name, "qty": 0, "revenue": Decimal(0)})
        pr["qty"] += qty
        pr["revenue"] += revenue

    profit = total_revenue - total_cost
    # compute top 5 by qty
    top_products = sorted(per_product.items(), key=lambda kv: (-kv[1]["qty"], -int(kv[1]["revenue"])))[:5]
    top_products_formatted = [{"product_id": pid, "name": v["name"], "qty": v["qty"], "revenue": int(v["revenue"])} for pid, v in top_products]

    # format by category percentages
    total_rev_int = int(total_revenue) if total_revenue else 0
    by_cat_formatted = {}
    for cat, rev in by_cat.items():
        by_cat_formatted[cat] = {"revenue": int(rev), "pct": round((int(rev) / total_rev_int * 100), 1) if total_rev_int > 0 else 0.0}

    return {
        "year": year, "month": month,
        "total_revenue": int(total_revenue),
        "total_cost": int(total_cost),
        "profit": int(profit),
        "by_category": by_cat_formatted,
        "top_products": top_products_formatted,
        "transactions_count": len(txs_month),
    }


def inventory_report_export(out_path_xlsx: Path) -> Path:
    """
    Xuất báo cáo inventory. Nếu openpyxl có sẵn xuất xlsx, nếu không xuất CSV.
    Trả về Path đã ghi.
    """
    products = product_mgr.list_products()
    if not products:
        raise RuntimeError("Không có sản phẩm để xuất báo cáo tồn kho.")

    out_path_xlsx.parent.mkdir(parents=True, exist_ok=True)
    if HAS_OPENPYXL:
        wb = Workbook()
        ws = wb.active
        ws.title = "Inventory"
        headers = ["product_id", "name", "category", "cost_price", "sell_price", "stock_quantity", "min_threshold", "unit", "created_date", "last_updated"]
        ws.append(headers)
        for p in products:
            ws.append([
                p.product_id, p.name, p.category, float(p.cost_price), float(p.sell_price),
                p.stock_quantity, p.min_threshold, p.unit,
                getattr(p, "created_date", ""), getattr(p, "last_updated", "")
            ])
        wb.save(str(out_path_xlsx))
        return out_path_xlsx
    else:
        # fallback CSV
        out_csv = out_path_xlsx.with_suffix(".csv")
        import csv as _csv
        with out_csv.open("w", encoding="utf-8", newline="") as f:
            writer = _csv.writer(f)
            writer.writerow(["product_id", "name", "category", "cost_price", "sell_price", "stock_quantity", "min_threshold", "unit", "created_date", "last_updated"])
            for p in products:
                writer.writerow([p.product_id, p.name, p.category, p.cost_price, p.sell_price, p.stock_quantity, p.min_threshold, p.unit, getattr(p, "created_date", ""), getattr(p, "last_updated", "")])
        return out_csv


def export_sales_summary_csv(summary: Dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    import csv as _csv
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = _csv.writer(f)
        writer.writerow(["year", "month", "total_revenue", "total_cost", "profit", "transactions_count"])
        writer.writerow([summary["year"], summary["month"], summary["total_revenue"], summary["total_cost"], summary["profit"], summary["transactions_count"]])
        writer.writerow([])
        writer.writerow(["category", "revenue", "pct"])
        for cat, info in summary["by_category"].items():
            writer.writerow([cat, info["revenue"], info["pct"]])
        writer.writerow([])
        writer.writerow(["top_products (product_id, name, qty, revenue)"])
        for p in summary["top_products"]:
            writer.writerow([p["product_id"], p["name"], p["qty"], p["revenue"]])
    return out_path


def low_stock_alerts_and_export(out_txt: Path, out_csv: Optional[Path] = None, out_xlsx: Optional[Path] = None) -> Dict[str, Any]:
    """
    Sinh cảnh báo tồn (dựa vào product_mgr + transaction_mgr)
    Xuất file text + csv + xlsx (nếu yêu cầu)
    """
    # Prefer using generate_low_stock_alerts if exists (centralized logic)
    if generate_low_stock_alerts is not None:
        alerts = generate_low_stock_alerts(product_mgr, transaction_mgr, include_out_of_stock=True, include_low_stock=True)
    else:
        # fallback simple implementation
        out_of_stock = []
        low_stock = []
        total_needed = 0
        for p in product_mgr.list_products():
            need = max(0, p.min_threshold - p.stock_quantity) if p.stock_quantity < p.min_threshold else 0
            item = {"product_id": p.product_id, "name": p.name, "category": p.category, "stock_quantity": p.stock_quantity, "min_threshold": p.min_threshold, "needed": need}
            if p.stock_quantity <= 0:
                out_of_stock.append(item)
                total_needed += need
            elif p.stock_quantity <= p.min_threshold:
                low_stock.append(item)
                total_needed += need
        alerts = {"generated_at": datetime.now(VN_TZ).isoformat(), "out_of_stock": out_of_stock, "low_stock": low_stock, "total_needed": total_needed, "by_category": {}}

    # write txt
    txt = format_alerts_text(alerts) if format_alerts_text else _simple_alerts_text(alerts)
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text(txt, encoding="utf-8")

    # csv
    if out_csv:
        import csv as _csv
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["type", "product_id", "name", "category", "stock_quantity", "min_threshold", "needed"]
        with out_csv.open("w", encoding="utf-8", newline="") as f:
            w = _csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for item in alerts.get("out_of_stock", []):
                row = {"type": "OUT_OF_STOCK", **{k: item.get(k, "") for k in ("product_id","name","category","stock_quantity","min_threshold")}, "needed": item.get("needed",0)}
                w.writerow(row)
            for item in alerts.get("low_stock", []):
                row = {"type": "LOW_STOCK", **{k: item.get(k, "") for k in ("product_id","name","category","stock_quantity","min_threshold")}, "needed": item.get("needed",0)}
                w.writerow(row)

    # xlsx
    if out_xlsx and HAS_OPENPYXL:
        try:
            export_alerts_xlsx(alerts, str(out_xlsx))
        except Exception:
            pass

    return alerts


def _simple_alerts_text(alerts):
    lines = ["========== CẢNH BÁO TỒN KHO ==========", f"Generated at: {alerts.get('generated_at')}",""]
    def section(title, items):
        if not items:
            return [f"{title}: None", ""]
        s = [f"{title} ({len(items)}):"]
        for it in items:
            s.append(f"- {it['product_id']}: {it['name']} ({it['stock_quantity']}/{it['min_threshold']}) cần: {it.get('needed',0)}")
        s.append("")
        return s
    lines += section("HẾT HÀNG", alerts.get("out_of_stock", []))
    lines += section("SẮP HẾT", alerts.get("low_stock", []))
    lines.append(f"Tổng cần nhập: {alerts.get('total_needed', 0)}")
    return "\n".join(lines)


# -------- CLI Menus (the requested menu layout) ----------
def menu_quan_ly_san_pham():
    while True:
        print("\n=== 1. QUẢN LÝ SẢN PHẨM ===")
        print("1.1 Thêm sản phẩm mới")
        print("1.2 Sửa thông tin sản phẩm")
        print("1.3 Xóa sản phẩm")
        print("1.4 Tìm kiếm sản phẩm")
        print("1.5 Thêm danh mục mới")
        print("0 Quay lại")
        c = input("Chọn: ").strip()
        if c == "1.1":
            pid = input("Mã SP: ").strip()
            name = input("Tên sản phẩm: ").strip()
            cat = input("Danh mục: ").strip()
            try:
                cost = Decimal(input("Giá nhập: ").strip() or "0")
                sell = Decimal(input("Giá bán: ").strip() or "0")
                qty = int(input("Số lượng tồn: ").strip() or "0")
                thr = int(input("Ngưỡng cảnh báo: ").strip() or "0")
            except Exception as e:
                print("Dữ liệu số không hợp lệ:", e); continue
            unit = input("Đơn vị: ").strip() or "cái"
            try:
                product_mgr.add_product(pid, name, cat, cost, sell, qty, thr, unit)
                print("Thêm thành công.")
            except Exception as e:
                print("Lỗi:", e)
        elif c == "1.2":
            pid = input("Mã SP cần sửa: ").strip()
            try:
                p = product_mgr.get_product(pid)
            except Exception as e:
                print("Không tìm thấy:", e); continue
            print("Để trống để giữ nguyên.")
            name = input(f"Tên [{p.name}]: ").strip() or p.name
            cat = input(f"Danh mục [{p.category}]: ").strip() or p.category
            cost = input(f"Giá nhập [{p.cost_price}]: ").strip() or str(p.cost_price)
            sell = input(f"Giá bán [{p.sell_price}]: ").strip() or str(p.sell_price)
            qty = input(f"Tồn [{p.stock_quantity}]: ").strip() or str(p.stock_quantity)
            thr = input(f"Ngưỡng [{p.min_threshold}]: ").strip() or str(p.min_threshold)
            unit = input(f"Đơn vị [{p.unit}]: ").strip() or p.unit
            try:
                changes = {"name": name, "category": cat, "cost_price": cost, "sell_price": sell, "stock_quantity": int(qty), "min_threshold": int(thr), "unit": unit}
                product_mgr.update_product(pid, **changes)
                print("Cập nhật thành công.")
            except Exception as e:
                print("Lỗi:", e)
        elif c == "1.3":
            pid = input("Mã SP cần xóa: ").strip()
            try:
                product_mgr.delete_product(pid)
                print("Xóa thành công.")
            except Exception as e:
                print("Lỗi:", e)
        elif c == "1.4":
            kw = input("Tìm kiếm (mã/tên/danh mục): ").strip()
            field = input("Trường (product_id/name/category) [name]: ").strip() or "name"
            try:
                results = product_mgr.search_products(kw, field=field)
                print_products_table(results)
            except Exception as e:
                print("Lỗi:", e)
        elif c == "1.5":
            cat = input("Tên danh mục mới: ").strip()
            try:
                category_mgr.add_category(cat)
                print("Thêm danh mục thành công.")
            except Exception as e:
                print("Lỗi:", e)
        elif c == "0":
            break
        else:
            print("Lựa chọn không hợp lệ.")


def menu_nhap_xuat_kho():
    while True:
        print("\n=== 2. NHẬP/XUẤT KHO ===")
        print("2.1 Nhập kho")
        print("2.2 Xuất kho (bán hàng)")
        print("2.3 Lịch sử giao dịch")
        print("0 Quay lại")
        c = input("Chọn: ").strip()
        if c == "2.1":
            pid = input("Mã SP: ").strip()
            qty = int(input("Số lượng nhập: ").strip() or "0")
            note = input("Ghi chú: ").strip()
            try:
                transaction_mgr.add_transaction(pid, "IMPORT", qty, note=note)
                print("Nhập kho thành công.")
            except Exception as e:
                print("Lỗi:", e)
        elif c == "2.2":
            pid = input("Mã SP: ").strip()
            qty = int(input("Số lượng xuất: ").strip() or "0")
            note = input("Ghi chú: ").strip()
            try:
                transaction_mgr.add_transaction(pid, "EXPORT", qty, note=note)
                print("Xuất kho thành công.")
            except Exception as e:
                print("Lỗi:", e)
        elif c == "2.3":
            txs = transaction_mgr.list_transactions()
            if not txs:
                print("Không có giao dịch.")
            else:
                print("ID | SP | Loại | Số lượng | Ngày | Ghi chú")
                for t in txs:
                    print(f"{t.transaction_id} | {t.product_id} | {t.trans_type} | {t.quantity} | {getattr(t,'date','')} | {t.note}")
        elif c == "0":
            break
        else:
            print("Lựa chọn không hợp lệ.")


def menu_bao_cao_thong_ke():
    while True:
        print("\n=== 3. BÁO CÁO VÀ THỐNG KÊ ===")
        print("3.1 Danh sách tồn kho")
        print("3.2 Cảnh báo hết hàng")
        print("3.3 Báo cáo doanh thu (theo tháng)")
        print("3.4 Top sản phẩm bán chạy")
        print("0 Quay lại")
        c = input("Chọn: ").strip()
        if c == "3.1":
            prods = product_mgr.list_products()
            print_products_table(prods)
        elif c == "3.2":
            out_txt = REPORTS_DIR / "low_stock_alert.txt"
            out_csv = REPORTS_DIR / "low_stock_alert.csv"
            out_xlsx = REPORTS_DIR / "low_stock_alert.xlsx" if HAS_OPENPYXL else None
            alerts = low_stock_alerts_and_export(out_txt, out_csv, out_xlsx)
            print("Cảnh báo (tóm tắt):")
            if alerts.get("out_of_stock") or alerts.get("low_stock"):
                print((format_alerts_text(alerts) if format_alerts_text else _simple_alerts_text(alerts)))
            else:
                print("Không có sản phẩm dưới ngưỡng.")
            print("Files exported to:", out_txt, out_csv, out_xlsx)
        elif c == "3.3":
            y = int(input("Năm (YYYY): ").strip() or str(datetime.now().year))
            m = int(input("Tháng (1-12): ").strip() or str(datetime.now().month))
            if compute_financial_summary:
                summary = compute_financial_summary(product_mgr, transaction_mgr, month=m, year=y, out_dir=REPORTS_DIR,
                                                    currency="VND")
                print(format_financial_summary_text(summary))
                print(f"➡️ Đã xuất file: {REPORTS_DIR}/sales_summary_{m:02d}_{y}.csv")
            else:
                summary = sales_summary_month(y, m)
                print(f"Doanh thu: {fmt_vnd(summary['total_revenue'])} VND")

        elif c == "3.4":
            y = int(input("Năm (YYYY) [blank = hiện tại]: ") or datetime.now().year)
            m = int(input("Tháng (1-12) [blank = hiện tại]: ") or datetime.now().month)
            if compute_financial_summary:
                summary = compute_financial_summary(product_mgr, transaction_mgr, month=m, year=y, out_dir=REPORTS_DIR, currency="VND")
                if not summary["top_sellers"]:
                    print("Không có dữ liệu bán hàng.")
                else:
                    for i, p in enumerate(summary["top_sellers"], 1):
                        print(f"{i}. {p['name']} ({p['category']}) "
                            f"- SL {p['quantity_sold']} | Doanh thu {fmt_vnd(p['revenue'])} | Lợi nhuận {fmt_vnd(p['profit'])}")
            else:
                summary = sales_summary_month(y, m)
                for i, p in enumerate(summary.get("top_products", []), 1):
                    print(f"{i}. {p['name']} ({p['qty']} cái) - Doanh thu {fmt_vnd(p['revenue'])} VND")

        elif c == "0":
            break
        else:
            print("Lựa chọn không hợp lệ.")


def menu_xuat_du_lieu():
    print("\n=== 4. XUẤT DỮ LIỆU ===")
    p_out = input("Path xuất products (json/csv) [reports/products_export.json]: ").strip() or str(REPORTS_DIR / "products_export.json")
    t_out = input("Path xuất transactions (csv/json) [reports/transactions_export.csv]: ").strip() or str(REPORTS_DIR / "transactions_export.csv")
    try:
        product_mgr.export_json(p_out)
        transaction_mgr.export_transactions(t_out)
        print("Đã xuất files:", p_out, t_out)
    except Exception as e:
        print("Lỗi xuất dữ liệu:", e)


def main():
    while True:
        print("\n========== QUẢN LÝ KHO HÀNG ==========")
        print("1. Quản lý sản phẩm")
        print("2. Nhập/Xuất kho")
        print("3. Báo cáo và thống kê")
        print("4. Xuất dữ liệu")
        print("5. Thoát")
        ch = input("Chọn: ").strip()
        if ch == "1":
            menu_quan_ly_san_pham()
        elif ch == "2":
            menu_nhap_xuat_kho()
        elif ch == "3":
            menu_bao_cao_thong_ke()
        elif ch == "4":
            menu_xuat_du_lieu()
        elif ch == "5":
            print("Kết thúc.")
            break
        else:
            print("Lựa chọn không hợp lệ.")

if __name__ == "__main__":
    main()
