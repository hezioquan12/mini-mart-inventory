#!/usr/bin/env python3
# src/cli/cli_vn.py
"""
Giao diện dòng lệnh (CLI) tiếng Việt cho Hệ thống Quản lý Kho Mini-Mart.

Phiên bản cải tiến:
- Xử lý input an toàn, chống crash chương trình.
- Tái cấu trúc code theo từng chức năng, dễ đọc, dễ bảo trì.
- Thống nhất logic, chỉ sử dụng các hàm từ module lõi của dự án.
- Cải thiện hiển thị output cho các bảng dữ liệu.
- Loại bỏ các cảnh báo từ linter.
"""

import sys
import traceback
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Any
import os


def run_cli_app():
    """
    Hàm chính chứa toàn bộ logic của ứng dụng.
    Hàm này chỉ được gọi khi tất cả các module cần thiết đã được import thành công.
    """
    # --- Các import phụ thuộc được đặt bên trong để đảm bảo an toàn ---
    from src.inventory.product_manager import ProductManager
    from src.inventory.category_manager import CategoryManager
    from src.sales.transaction_manager import TransactionManager
    from src.report_and_sreach.report import (
        generate_low_stock_alerts,
        export_alerts_xlsx,
        format_alerts_text,
        compute_financial_summary,
        format_financial_summary_text,
        calculate_import_quantity
    )
    from src.report_and_sreach.sreach import SearchEngine
    from src.utils.time_zone import VN_TZ

    try:
        from openpyxl import Workbook
        HAS_OPENPYXL = True
    except ImportError:
        HAS_OPENPYXL = False

    # --- Cấu hình đường dẫn ---
    current_file_path = Path(__file__).resolve()
    # Lấy thư mục gốc của dự án (đi lên 3 cấp từ file .py hiện tại)
    # Path(__file__) -> .../project_root/main/app.py
    # .parent        -> .../project_root/main
    # .parent        -> .../project_root
    project_root = current_file_path.parent.parent.parent

    # Định nghĩa đường dẫn dựa trên thư mục gốc
    DATA_DIR = project_root / "data"
    REPORTS_DIR = project_root / "reports"

    # Tạo thư mục (nếu chưa có)
    DATA_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)

    # ===============================================
    # === CÁC HÀM PHỤ TRỢ (HELPERS)
    # ===============================================

    def prompt_for_text(prompt: str, default: Optional[str] = None) -> str:
        """Hỏi người dùng và trả về chuỗi text đã được làm sạch (strip)."""
        display_prompt = f"{prompt} [{default}]" if default is not None else prompt
        value = input(f"{display_prompt}: ").strip()
        if not value and default is not None:
            return default
        return value

    def prompt_for_int(prompt: str, default: Optional[int] = None) -> int:
        """Hỏi người dùng cho đến khi nhập vào một số nguyên hợp lệ."""
        while True:
            try:
                default_val = str(default) if default is not None else None
                value_str = prompt_for_text(prompt, default=default_val)
                if not value_str:
                    if default is not None: return default
                    raise ValueError("Giá trị không được để trống.")
                return int(value_str)
            except (ValueError, TypeError):
                print("❌ Vui lòng nhập một số nguyên hợp lệ.")

    def prompt_for_decimal(prompt: str, default: Optional[Decimal] = None) -> Decimal:
        """Hỏi người dùng cho đến khi nhập vào một số Decimal hợp lệ."""
        while True:
            try:
                default_val = str(default) if default is not None else None
                value_str = prompt_for_text(prompt, default=default_val)
                if not value_str:
                    if default is not None: return default
                    raise ValueError("Giá trị không được để trống.")
                return Decimal(value_str.replace(",", "."))
            except (InvalidOperation, ValueError):
                print("❌ Vui lòng nhập một số hợp lệ (ví dụ: 50000.5).")

    def fmt_vnd(x: Any) -> str:
        """Định dạng số thành chuỗi tiền tệ VND."""
        try:
            return f"{int(Decimal(str(x))):,}"
        except Exception:
            return str(x)

    def status_for_product(p) -> str:
        """Trả về trạng thái tồn kho của sản phẩm."""
        if p.stock_quantity <= 0: return "HẾT HÀNG"
        if p.stock_quantity <= p.min_threshold: return "SẮP HẾT"
        return "BÌNH THƯỜNG"

    def print_products_table(products: List[Any]) -> None:
        """In danh sách sản phẩm ra console dưới dạng bảng."""
        if not products:
            print("\n(Không có sản phẩm nào)")
            return
        print(
            f"\n{'Mã SP':<10} {'Tên':<30} {'Danh mục':<15} {'Giá nhập':>12} {'Giá bán':>12} {'Tồn':>6} {'Ngưỡng':>7} {'Trạng thái':>12}")
        print("-" * 110)
        for p in products:
            print(
                f"{p.product_id:<10} {p.name[:30]:<30} {p.category[:15]:<15} {fmt_vnd(p.cost_price):>12} {fmt_vnd(p.sell_price):>12} {p.stock_quantity:>6} {p.min_threshold:>7} {status_for_product(p):>12}")
        print()

    def print_transactions_table(transactions: List[Any]) -> None:
        """In danh sách giao dịch ra console dưới dạng bảng."""
        if not transactions:
            print("\n(Không có giao dịch nào)")
            return
        print(f"\n{'ID Giao dịch':<38} {'Mã SP':<10} {'Loại':<8} {'Số lượng':>10} {'Ngày':<28} {'Ghi chú'}")
        print("-" * 120)
        # Sắp xếp giao dịch theo ngày mới nhất lên đầu
        for t in sorted(transactions, key=lambda x: x.date, reverse=True):
            date_str = t.date.astimezone(VN_TZ).strftime('%Y-%m-%d %H:%M:%S') if t.date else 'N/A'
            print(
                f"{t.transaction_id:<38} {t.product_id:<10} {t.trans_type:<8} {t.quantity:>10} {date_str:<28} {t.note}")
        print()

    # ===============================================
    # === KHỞI TẠO CÁC ĐỐI TƯỢNG QUẢN LÝ (MANAGERS)
    # ===============================================
    category_mgr = CategoryManager(str(DATA_DIR / "categories.json"))
    product_mgr = ProductManager(str(DATA_DIR / "products.json"), category_mgr=category_mgr)
    transaction_mgr = TransactionManager(str(DATA_DIR / "transactions.csv"), product_mgr=product_mgr)
    search_engine = SearchEngine(product_mgr, transaction_mgr)
    # ===============================================
    # === CÁC HÀM XỬ LÝ TÁC VỤ (ACTION HANDLERS)
    # ===============================================

    def _handle_add_product():
        print("\n--- 1.1 Thêm sản phẩm mới ---")
        try:
            pid = prompt_for_text("Mã SP")
            if not pid:
                print("❗️ Mã SP không được để trống.")
                return
            name = prompt_for_text("Tên sản phẩm")
            cat = prompt_for_text("Danh mục")
            cost = prompt_for_decimal("Giá nhập", default=Decimal("0"))
            sell = prompt_for_decimal("Giá bán", default=cost)
            qty = prompt_for_int("Số lượng tồn", default=0)
            thr = prompt_for_int("Ngưỡng cảnh báo", default=0)
            unit = prompt_for_text("Đơn vị", default="cái")

            product_mgr.add_product(pid, name, cat, cost, sell, qty, thr, unit)
            print("✅ Thêm sản phẩm thành công.")
        except (ValueError, InvalidOperation) as e:
            print(f"❌ Lỗi: {e}")

    def _handle_suggest_reorder():
        """
        Gợi ý số lượng nhập hàng thông minh cho một sản phẩm.
        Sử dụng hàm calculate_import_quantity từ report.py.
        """
        print("\n--- 1.6 Gợi ý số lượng nhập hàng---")
        pid = prompt_for_text("Mã SP cần gợi ý")
        if not pid: return

        try:
            product = product_mgr.get_product(pid)
            transactions = transaction_mgr.list_transactions()
            print("...Đang phân tích lịch sử bán hàng...")
            days_history = 30  # Phân tích 30 ngày qua
            lead_time = 7  # Thời gian chờ hàng về là 7 ngày

            suggested_qty = calculate_import_quantity(
                product,
                transactions,
                days=days_history,
                lead_time=lead_time
            )

            print("\n--- 💡 KẾT QUẢ GỢI Ý 💡 ---")
            print(f"Sản phẩm: {product.name} (ID: {product.product_id})")
            print(f"Tồn kho hiện tại: {product.stock_quantity}")
            print(f"Ngưỡng tối thiểu: {product.min_threshold}")
            print(f"Phân tích dựa trên: {days_history} ngày qua, Thời gian chờ hàng: {lead_time} ngày.")
            print("-" * 30)
            print(f"👉 Số lượng gợi ý nhập: {suggested_qty} {product.unit}")
            print("\n(Lưu ý: Con số này dựa trên TB bán hàng và độ lệch chuẩn, "
                  "để đảm bảo 95% không hết hàng trong 7 ngày tới.)")

        except ValueError as e:
            print(f"❌ Lỗi: {e} (Không tìm thấy sản phẩm?)")
        except Exception as e:
            print(f"❌ Lỗi bất ngờ khi tính toán: {e}")
    def _handle_update_product():
        print("\n--- 1.2 Sửa thông tin sản phẩm ---")
        pid = prompt_for_text("Mã SP cần sửa")
        if not pid: return
        try:
            p = product_mgr.get_product(pid)
            print("💡 Để trống và nhấn Enter để giữ nguyên giá trị cũ.")

            changes = {
                "name": prompt_for_text("Tên", default=p.name),
                "category": prompt_for_text("Danh mục", default=p.category),
                "cost_price": prompt_for_decimal("Giá nhập", default=p.cost_price),
                "sell_price": prompt_for_decimal("Giá bán", default=p.sell_price),
                "stock_quantity": prompt_for_int("Số lượng tồn", default=p.stock_quantity),
                "min_threshold": prompt_for_int("Ngưỡng", default=p.min_threshold),
                "unit": prompt_for_text("Đơn vị", default=p.unit)
            }
            product_mgr.update_product(pid, **changes)
            print("✅ Cập nhật thành công.")
        except (ValueError, InvalidOperation) as e:
            print(f"❌ Lỗi: {e}")

    def _handle_delete_product():
        print("\n--- 1.3 Xóa sản phẩm ---")
        pid = prompt_for_text("Mã SP cần xóa")
        if not pid: return
        try:
            # Thêm bước xác nhận để an toàn
            confirm = prompt_for_text(f"Bạn có chắc muốn xóa sản phẩm '{pid}'? (y/n)", default='n')
            if confirm.lower() == 'y':
                product_mgr.delete_product(pid)
                print(f"✅ Đã xóa sản phẩm '{pid}'.")
            else:
                print("Hủy thao tác xóa.")
        except ValueError as e:
            print(f"❌ Lỗi: {e}")

    def _handle_search_product():
        print("\n--- 1.4 Tìm kiếm sản phẩm---")
        kw = prompt_for_text("Nhập từ khóa (mã/tên/danh mục)")
        if not kw: return
        field = prompt_for_text("Tìm theo trường (product_id/name/category/all)", "all")
        field_lookup = None if field.lower() == "all" else field
        try:
            # Sử dụng SearchEngine
            response = search_engine.search_products(
                keyword=kw,
                field=field_lookup,
                page=1,
                per_page=50  # Hiển thị 50 kết quả đầu tiên
            )
            product_ids = [p['product_id'] for p in response.get("results", [])]
            products_list = [product_mgr.get_product(pid) for pid in product_ids if product_mgr.product_exists(pid)]
            print_products_table(products_list)  # Dùng hàm in bảng cũ
            print(f"\n--- (Tìm thấy tổng cộng {response.get('total', 0)} kết quả) ---")

            facets = response.get("facets", {})
            if facets:
                print("Phân loại theo danh mục (trong kết quả):")
                for cat, count in facets.items():
                    print(f"  - {cat}: {count} SP")

        except ValueError as e:
            print(f"❌ Lỗi: {e}")

    def _handle_add_category():
        print("\n--- 1.5 Thêm danh mục mới ---")
        cat_name = prompt_for_text("Tên danh mục mới")
        if not cat_name: return
        try:
            category_mgr.add_category(cat_name)
            print(f"✅ Thêm danh mục '{cat_name}' thành công.")
        except ValueError as e:
            print(f"❌ Lỗi: {e}")

    def _handle_transaction(trans_type: str):
        is_import = trans_type.upper() == "IMPORT"
        action_text = "nhập" if is_import else "xuất"
        print(f"\n--- 2.{1 if is_import else 2} {action_text.capitalize()} kho ---")
        pid = prompt_for_text("Mã SP")
        if not pid: return
        try:
            product_mgr.get_product(pid)  # Kiểm tra SP tồn tại
            qty = prompt_for_int(f"Số lượng {action_text}")
            if qty <= 0:
                print("❗️ Số lượng phải lớn hơn 0.")
                return
            note = prompt_for_text("Ghi chú (tùy chọn)", default="")
            transaction_mgr.add_transaction(pid, trans_type.upper(), qty, note=note)
            print(f"✅ {action_text.capitalize()} kho thành công.")
        except ValueError as e:
            print(f"❌ Lỗi: {e}")

    # ===============================================
    # === CÁC MENU CHỨC NĂNG
    # ===============================================

    def menu_quan_ly_san_pham():
        menu_map = {
            "1": ("Thêm sản phẩm mới", _handle_add_product),
            "2": ("Sửa thông tin sản phẩm", _handle_update_product),
            "3": ("Xóa sản phẩm", _handle_delete_product),
            "4": ("Tìm kiếm sản phẩm", _handle_search_product),
            "5": ("Thêm danh mục mới", _handle_add_category),
            "6": ("Gợi ý nhập hàng", _handle_suggest_reorder),
            "0": ("Quay lại", None)
        }
        while True:
            print("\n=== 1. QUẢN LÝ SẢN PHẨM ===")
            for key, (text, _) in menu_map.items(): print(f"{key}. {text}")
            choice = input("Chọn: ").strip()
            if choice == "0": break
            action = menu_map.get(choice)
            if action and action[1]:
                action[1]()
            else:
                print("❗️ Lựa chọn không hợp lệ.")

    def menu_nhap_xuat_kho():
        while True:
            print("\n=== 2. NHẬP/XUẤT KHO ===")
            print("1. Nhập kho")
            print("2. Xuất kho (bán hàng)")
            print("3. Lịch sử giao dịch")
            print("0. Quay lại")
            c = input("Chọn: ").strip()
            if c == "1":
                _handle_transaction("IMPORT")
            elif c == "2":
                _handle_transaction("EXPORT")
            elif c == "3":
                print_transactions_table(transaction_mgr.list_transactions())
            elif c == "0":
                break
            else:
                print("❗️ Lựa chọn không hợp lệ.")

    def menu_bao_cao_thong_ke():
        while True:
            print("\n=== 3. BÁO CÁO VÀ THỐNG KÊ ===")
            print("1. Xem danh sách tồn kho")
            print("2. Xem cảnh báo hết hàng/sắp hết hàng")
            print("3. Xem báo cáo doanh thu theo tháng và top bán chạy")
            print("0. Quay lại")
            c = input("Chọn: ").strip()
            if c == "1":
                print_products_table(product_mgr.list_products())
            elif c == "2":
                alerts = generate_low_stock_alerts(product_mgr, transaction_mgr)
                formatted_text = format_alerts_text(alerts)
                print(formatted_text)
                try:
                    # Tạo tên file duy nhất (thêm cả giờ phút giây)
                    now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                    out_txt_path = REPORTS_DIR / f"low_stock_alert_{now_str}.txt"

                    # Đảm bảo thư mục reports tồn tại (an toàn hơn)
                    REPORTS_DIR.mkdir(exist_ok=True)

                    # Ghi file với encoding UTF-8
                    with open(out_txt_path, "w", encoding="utf-8") as f:
                        f.write(formatted_text)
                    print(f"✅ Đã tự động lưu báo cáo (TXT) ra file: {out_txt_path}")
                except Exception as e:
                    print(f"❌ Lỗi khi xuất file TXT: {e}")
                if HAS_OPENPYXL and input("Bạn có muốn xuất file Excel chi tiết không? (y/n): ").lower() == 'y':
                    try:
                        # Sử dụng cùng timestamp để 2 file (txt, xlsx) khớp tên nhau
                        out_path = REPORTS_DIR / f"low_stock_alert_{now_str}.xlsx"
                        export_alerts_xlsx(alerts, str(out_path))
                        print(f"✅ Đã xuất báo cáo (Excel) ra file: {out_path}")
                    except Exception as e:
                        print(f"❌ Lỗi khi xuất file Excel: {e}")
            elif c == "3":
                now = datetime.now(VN_TZ)
                y = prompt_for_int("Nhập năm (YYYY)", default=now.year)
                m = prompt_for_int("Nhập tháng (1-12)", default=now.month)
                try:
                    summary = compute_financial_summary(
                        product_mgr,
                        transaction_mgr,
                        month=m,
                        year=y,
                        out_dir=REPORTS_DIR,
                        top_k=5
                    )
                    print(format_financial_summary_text(summary))
                    # 2. Lấy timestamp (chuỗi ngày-giờ-phút-giây)
                    now_str = now.strftime('%Y%m%d_%H%M%S')

                    # 3. Đây là tên file chuẩn mà hàm vừa tạo ra
                    standard_file_name = f"sales_summary_{m:02d}_{y}.csv"
                    standard_path = REPORTS_DIR / standard_file_name

                    # 4. Đây là tên file mới bạn muốn
                    new_file_name = f"sales_summary_{m:02d}_{y}_{now_str}.csv"
                    new_path = REPORTS_DIR / new_file_name
                    # 5. Dùng 'os.rename' để đổi tên file
                    if standard_path.exists():
                        os.rename(standard_path, new_path)
                        print(f"✅ Đã xuất file chi tiết: {new_path}")
                    else:
                        print(f"❓ Đã tạo báo cáo, nhưng không tìm thấy file '{standard_path}' để đổi tên.")
                except Exception as e:
                    print(f"❌ Lỗi khi tạo báo cáo: {e}")
    def menu_xuat_du_lieu():
        print("\n=== 4. XUẤT DỮ LIỆU ===")
        try:
            p_out = prompt_for_text("Đường dẫn xuất file sản phẩm (json/csv)",
                                    str(REPORTS_DIR / "products_export.json"))

            # === DÒNG QUAN TRỌNG: Đảm bảo thư mục tồn tại ===
            Path(p_out).parent.mkdir(parents=True, exist_ok=True)

            if Path(p_out).suffix == '.csv':
                product_mgr.export_csv(p_out)
            else:
                product_mgr.export_json(p_out)

            t_out = prompt_for_text("Đường dẫn xuất file giao dịch (csv)", str(REPORTS_DIR / "transactions_export.csv"))

            # === DÒNG QUAN TRỌNG: Đảm bảo thư mục tồn tại ===
            Path(t_out).parent.mkdir(parents=True, exist_ok=True)

            transaction_mgr.export_transactions(t_out)

            print(f"✅ Đã xuất dữ liệu ra các file:\n- {p_out}\n- {t_out}")
        except Exception as e:
            print(f"❌ Lỗi xuất dữ liệu: {e}")

    # ===============================================
    # === HÀM MAIN (ĐIỂM BẮT ĐẦU CỦA APP)
    # ===============================================
    def main():
        menu_map = {
            "1": ("Quản lý sản phẩm", menu_quan_ly_san_pham),
            "2": ("Nhập/Xuất kho", menu_nhap_xuat_kho),
            "3": ("Báo cáo và thống kê", menu_bao_cao_thong_ke),
            "4": ("Xuất dữ liệu", menu_xuat_du_lieu),
            "5": ("Thoát", None)
        }
        while True:
            print("\n========== 📦 QUẢN LÝ KHO HÀNG MINI-MART 📦 ==========")
            for key, (text, _) in menu_map.items():
                print(f"{key}. {text}")

            choice = input("Chọn chức năng: ").strip()

            if choice == "5":
                print("👋 Tạm biệt!")
                break

            action = menu_map.get(choice)
            if action and action[1]:
                action[1]()
            else:
                print("❗️ Lựa chọn không hợp lệ. Vui lòng chọn từ 1 đến 5.")

    # --- Chạy ứng dụng ---
    main()


# ===============================================
# === ENTRY POINT CỦA SCRIPT
# ===============================================
if __name__ == "__main__":
    try:
        # Bước 1: Kiểm tra các module cần thiết có thể được import không
        from src.inventory.product_manager import ProductManager
        from src.inventory.category_manager import CategoryManager
        from src.sales.transaction_manager import TransactionManager
        from src.report_and_sreach.report import generate_low_stock_alerts
        from src.utils.time_zone import VN_TZ

        # Bước 2: Nếu tất cả import thành công, gọi hàm để chạy toàn bộ ứng dụng
        run_cli_app()

    except ImportError:
        print("❌ LỖI NGHIÊM TRỌNG: KHÔNG TÌM THẤY MODULE CỦA DỰ ÁN.")
        print("Vui lòng đảm bảo bạn đang chạy script này từ thư mục gốc (root) của dự án.")
        print("Ví dụ: python -m src.cli.cli_vn")
        # In ra lỗi chi tiết để gỡ lỗi
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"💥 Đã xảy ra một lỗi không mong muốn: {e}")
        traceback.print_exc()
        sys.exit(1)