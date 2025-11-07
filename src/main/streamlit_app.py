# streamlit_app.py
from __future__ import annotations
import sys
import os
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt

# =================================================================================
# === KHẮC PHỤC LỖI MODULE NOT FOUND
# =================================================================================

try:
    PROJECT_ROOT_PATH = Path(__file__).parent.parent.parent.resolve()
    PROJECT_ROOT_STR = str(PROJECT_ROOT_PATH)
    if PROJECT_ROOT_STR not in sys.path:
        sys.path.insert(0, PROJECT_ROOT_STR)
except Exception as e:
    st.error(f"Không thể xác định thư mục gốc của dự án: {e}")
    if "." not in sys.path:
        sys.path.insert(0, ".")

# --- Import các module của dự án ---
try:
    from src.inventory.category_manager import CategoryManager
    from src.inventory.product_manager import ProductManager
    from src.sales.transaction_manager import TransactionManager
    from src.report_and_sreach.sreach import SearchEngine
    from src.report_and_sreach.report import (
        generate_low_stock_alerts,
        format_alerts_text,
        compute_financial_summary,
        write_low_stock_alerts,
        export_alerts_xlsx
    )
    from src.utils.time_zone import VN_TZ
except ImportError as e:
    st.error(
        "**Lỗi không tìm thấy module `src`!**\n\n"
        "Vui lòng đảm bảo rằng:\n"
        "1. Bạn đang chạy lệnh `streamlit run` từ thư mục gốc của dự án.\n"
        "2. Cấu trúc thư mục của bạn có dạng `project_root/src/`."
    )
    st.exception(e)
    st.stop()

# --- Cấu hình và khởi tạo các đối tượng quản lý ---
DATA_DIR = PROJECT_ROOT_PATH / "data"
REPORTS_DIR = PROJECT_ROOT_PATH / "reports"
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# TỪ ĐIỂN DỊCH TÊN CỘT ĐỂ VIỆT HÓA GIAO DIỆN
COLUMN_TRANSLATIONS = {
    "product_id": "Mã SP",
    "name": "Tên sản phẩm",
    "category": "Danh mục",
    "cost_price": "Giá nhập",
    "sell_price": "Giá bán",
    "stock_quantity": "Tồn kho",
    "min_threshold": "Ngưỡng",
    "unit": "Đơn vị",
    "created_date": "Ngày tạo",
    "last_updated": "Cập nhật lần cuối",
    "transaction_id": "Mã Giao dịch",
    "trans_type": "Loại Giao dịch",
    "quantity": "Số lượng",
    "date": "Ngày Giao dịch",
    "note": "Ghi chú",
    "revenue": "Doanh thu",
    "quantity_sold": "SL đã bán",
    "profit": "Lợi nhuận"
}


@st.cache_resource
def get_managers():
    category_mgr = CategoryManager(str(DATA_DIR / "categories.json"))
    product_mgr = ProductManager(str(DATA_DIR / "products.json"), category_mgr=category_mgr)
    transaction_mgr = TransactionManager(str(DATA_DIR / "transactions.csv"), product_mgr=product_mgr)
    # Khởi tạo SearchEngine và cache lại
    search_engine = SearchEngine(product_mgr, transaction_mgr)
    # Trả về 4 đối tượng thay vì 3
    return category_mgr, product_mgr, transaction_mgr, search_engine

cm, pm, tm, se = get_managers()


def fmt_vnd(v):
    try:
        return f"{int(v):,}"
    except:
        return str(v)


# =================================================================================
# === GIAO DIỆN STREAMLIT
# =================================================================================

st.set_page_config(page_title="Quản Lý Siêu Thị Mini", layout="wide", initial_sidebar_state="expanded")

# --- Sidebar ---
with st.sidebar:
    st.title("🏪 Siêu Thị Mini")
    menu_options = [
        "📊 Tổng quan",
        "📦 Quản lý Sản phẩm",
        "🚚 Giao dịch & Lịch sử",
        "📈 Báo cáo Chi tiết",
        "📥 Xuất Báo cáo & Tải về",
        "⚙️ Cài đặt"
    ]
    captions = [
        "Dashboard",
        "Thêm, sửa, xóa sản phẩm",
        "Nhập/xuất kho",
        "Xem doanh thu và tồn kho",
        "Lưu file Excel, CSV, TXT",
        "Quản lý danh mục"
    ]
    menu = st.radio("Chức năng chính", options=menu_options, captions=captions)
    st.info(f"🗓️ Hôm nay: {datetime.now(VN_TZ).strftime('%d/%m/%Y')}")

# =================================================================================
# === TRANG TỔNG QUAN (DASHBOARD)
# =================================================================================
if menu == "📊 Tổng quan":
    st.title("📊 Dashboard Tổng Quan")

    total_products = len(pm.list_products())
    total_transactions_month = len([t for t in tm.list_transactions() if t.date.month == datetime.now().month])
    alerts = generate_low_stock_alerts(pm, tm)
    low_stock_count = len(alerts.get("low_stock", []))
    out_of_stock_count = len(alerts.get("out_of_stock", []))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tổng số sản phẩm", f"{total_products} SP")
    col2.metric("Giao dịch tháng này", f"{total_transactions_month} GD")
    col3.metric("Sắp hết hàng", f"{low_stock_count} SP", delta_color="inverse")
    col4.metric("Hết hàng", f"{out_of_stock_count} SP", delta_color="inverse")

    st.markdown("---")

    with st.container(border=True):
        st.subheader("⚠️ Cảnh báo tồn kho")
        if not low_stock_count and not out_of_stock_count:
            st.success("👍 Tồn kho đang ở mức an toàn.")
        else:
            st.text_area("Chi tiết", value=format_alerts_text(alerts), height=250, disabled=True)
# =================================================================================
# === TRANG QUẢN LÝ SẢN PHẨM
# =================================================================================
elif menu == "📦 Quản lý Sản phẩm":
    st.title("📦 Quản lý Sản phẩm")

    # Đổi tên tab đầu tiên để bao gồm cả Tìm kiếm
    tab_list_search, tab_add, tab_delete = st.tabs(["📜 Danh sách & Tìm kiếm", "➕ Thêm mới", "❌ Xóa"])

    with tab_list_search:
        st.subheader("Xem toàn bộ hoặc tìm kiếm sản phẩm")

        # Thêm ô tìm kiếm
        keyword = st.text_input(
            "Nhập Mã SP, Tên, hoặc Danh mục để tìm kiếm:",
            placeholder="Ví dụ: Bánh mì, SP001, Thực phẩm..."
        )

        # Logic hiển thị danh sách dựa trên từ khóa
        if keyword:
            # Sử dụng SearchEngine để có kết quả tốt nhất
            search_results = se.search_products(keyword, fuzzy=True)
            st.write(f"Tìm thấy **{search_results['total']}** kết quả cho từ khóa **'{keyword}'**.")
            products_to_display = search_results['results']
        else:
            # Nếu không có từ khóa, hiển thị toàn bộ
            products_to_display = pm.list_products()

        # Hiển thị bảng kết quả
        if products_to_display:
            # Cần chuẩn hóa vì kết quả từ search engine là dict, từ product manager là object
            products_as_dicts = [p if isinstance(p, dict) else p.to_dict() for p in products_to_display]
            products_df = pd.DataFrame(products_as_dicts)
            st.dataframe(products_df.rename(columns=COLUMN_TRANSLATIONS), use_container_width=True, hide_index=True)
        else:
            # Chỉ thông báo không có kết quả khi người dùng đã tìm kiếm
            if keyword:
                st.info("Không tìm thấy sản phẩm nào phù hợp.")
            else:
                st.info("Chưa có sản phẩm nào trong kho.")

    with tab_add:
        # ... (code của tab Thêm mới giữ nguyên)
        st.subheader("Thêm sản phẩm mới")
        with st.form("add_product_form"):
            pid = st.text_input("Mã SP (product_id)")
            name = st.text_input("Tên sản phẩm")
            cat = st.selectbox("Danh mục", options=(cm.get_all_names() or ["(chưa có)"]))
            unit = st.text_input("Đơn vị", value="cái")
            c1, c2 = st.columns(2)
            cost = c1.number_input("Giá nhập", min_value=0, step=1000)
            sell = c2.number_input("Giá bán", min_value=0, step=1000)
            c3, c4 = st.columns(2)
            qty = c3.number_input("Tồn kho ban đầu", min_value=0, step=1)
            thr = c4.number_input("Ngưỡng cảnh báo", min_value=0, step=1)
            submitted = st.form_submit_button("Thêm sản phẩm")
            if submitted:
                try:
                    pm.add_product(pid, name, cat, Decimal(cost), Decimal(sell), qty, thr, unit)
                    st.success(f"Thêm sản phẩm '{name}' thành công!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")

    with tab_delete:
        # ... (code của tab Xóa giữ nguyên)
        st.subheader("Xóa sản phẩm")
        all_pids = [p.product_id for p in pm.list_products()]
        pid_to_delete = st.selectbox("Chọn sản phẩm cần xóa", options=all_pids)
        if st.button("❌ Xóa sản phẩm đã chọn", type="primary"):
            try:
                pm.delete_product(pid_to_delete)
                st.success(f"Đã xóa sản phẩm {pid_to_delete}.")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi: {e}")

# =================================================================================
# === TRANG GIAO DỊCH
# =================================================================================
elif menu == "🚚 Giao dịch & Lịch sử":
    st.title("🚚 Nhập/Xuất kho")
    c1, c2 = st.columns([1, 2])

    with c1:
        with st.container(border=True):
            st.subheader("Tạo giao dịch mới")
            all_pids = [p.product_id for p in pm.list_products()]
            pid = st.selectbox("Sản phẩm", options=all_pids)
            ttype = st.radio("Loại giao dịch", ["IMPORT", "EXPORT"], horizontal=True, captions=["Nhập kho", "Xuất kho"])
            qty = st.number_input("Số lượng", min_value=1, step=1)
            note = st.text_area("Ghi chú")

            if st.button("Thực hiện giao dịch", type="primary", use_container_width=True):
                try:
                    tx = tm.add_transaction(pid, ttype, qty, note)
                    st.success(f"Giao dịch {tx.transaction_id} thành công!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")

    with c2:
        st.subheader("Lịch sử giao dịch gần đây")
        transactions_df = pd.DataFrame([t.to_dict() for t in tm.list_transactions()])
        # Áp dụng Việt hóa trước khi hiển thị
        st.dataframe(
            transactions_df.sort_values(by="date", ascending=False).rename(columns=COLUMN_TRANSLATIONS),
            use_container_width=True,
            hide_index=True
        )

# =================================================================================
# === TRANG BÁO CÁO CHI TIẾT
# =================================================================================
elif menu == "📈 Báo cáo Chi tiết":
    st.title("📈 Báo cáo Doanh thu & Tồn kho")
    now = datetime.now(VN_TZ)
    c1, c2 = st.columns(2)
    year = c1.number_input("Năm", value=now.year, step=1)
    month = c2.number_input("Tháng", min_value=1, max_value=12, value=now.month)

    if st.button("Xem báo cáo", type="primary"):
        try:
            summary = compute_financial_summary(pm, tm, month=month, year=year)

            st.subheader(f"Báo cáo tài chính tháng {month}/{year}")

            m1, m2, m3 = st.columns(3)
            m1.metric("Tổng doanh thu", f"{fmt_vnd(summary.get('total_revenue', 0))} VND")
            m2.metric("Tổng vốn", f"{fmt_vnd(summary.get('total_cost', 0))} VND")
            m3.metric("Lợi nhuận", f"{fmt_vnd(summary.get('total_profit', 0))} VND")

            st.markdown("---")

            by_cat = summary.get("by_category", {})
            top_sellers = summary.get("top_sellers", [])

            if not by_cat:
                st.warning("Không có dữ liệu doanh thu trong tháng này để vẽ biểu đồ.")
            else:
                # Chuẩn bị DataFrame và Việt hóa cột
                df_cat = pd.DataFrame(
                    [{"category": k, "revenue": float(v.get("revenue", 0))} for k, v in by_cat.items()])
                df_cat_display = df_cat.rename(columns=COLUMN_TRANSLATIONS)

                df_top = pd.DataFrame(top_sellers)
                if not df_top.empty:
                    df_top["revenue"] = pd.to_numeric(df_top["revenue"])
                df_top_display = df_top.rename(columns=COLUMN_TRANSLATIONS)

                # Biểu đồ Doanh thu theo danh mục
                chart_cat = alt.Chart(df_cat_display).mark_bar().encode(
                    x=alt.X('Danh mục:N', sort='-y', title='Danh mục'),
                    y=alt.Y('Doanh thu:Q', title='Doanh thu (VND)'),
                    tooltip=['Danh mục', 'Doanh thu']
                ).properties(title=f'Doanh thu theo danh mục - Tháng {month}/{year}')

                # Biểu đồ Top sản phẩm bán chạy
                chart_top = alt.Chart(df_top_display).mark_bar().encode(
                    x=alt.X('Doanh thu:Q', title='Doanh thu (VND)'),
                    y=alt.Y('Tên sản phẩm:N', sort='-x', title='Sản phẩm'),
                    tooltip=['Tên sản phẩm', 'Doanh thu', 'SL đã bán']
                ).properties(title=f'Top sản phẩm bán chạy - Tháng {month}/{year}')

                st.altair_chart(chart_cat, use_container_width=True)
                st.altair_chart(chart_top, use_container_width=True)

        except Exception as e:
            st.error("Lỗi khi tạo báo cáo")
            st.exception(e)

# =================================================================================
# === TRANG XUẤT BÁO CÁO & TẢI VỀ
# =================================================================================
elif menu == "📥 Xuất Báo cáo & Tải về":
    st.title("📥 Xuất Báo cáo & Tải về")
    st.info("Tại đây bạn có thể tạo và tải các file báo cáo quan trọng về máy tính.")

    # --- 1. Báo cáo Cảnh báo Tồn kho ---
    with st.container(border=True):
        st.subheader("1. Báo cáo Cảnh báo Tồn kho")
        st.markdown("Xuất danh sách các sản phẩm đã hết hàng hoặc sắp hết hàng.")
        if st.button("🚨 Tạo & Tải file Cảnh báo"):
            try:
                alerts = generate_low_stock_alerts(pm, tm)

                # Tạo các file trên server
                txt_path = REPORTS_DIR / "low_stock_alert.txt"
                csv_path = REPORTS_DIR / "low_stock_alert.csv"
                xlsx_path = REPORTS_DIR / "low_stock_alert.xlsx"

                write_low_stock_alerts(alerts, out_txt_path=str(txt_path), out_csv_path=str(csv_path))
                export_alerts_xlsx(alerts, out_xlsx_path=str(xlsx_path))

                st.success("✅ Đã tạo thành công các file báo cáo cảnh báo!")

                # Hiển thị các nút tải về
                c1, c2, c3 = st.columns(3)
                with c1, open(txt_path, "rb") as f:
                    st.download_button("📥 Tải file .txt", f, file_name="low_stock_alert.txt")
                with c2, open(csv_path, "rb") as f:
                    st.download_button("📥 Tải file .csv", f, file_name="low_stock_alert.csv", mime="text/csv")
                with c3, open(xlsx_path, "rb") as f:
                    st.download_button("📥 Tải file .xlsx", f, file_name="low_stock_alert.xlsx")

            except Exception as e:
                st.error("Lỗi khi tạo báo cáo cảnh báo.")
                st.exception(e)

    # --- 2. Báo cáo Doanh thu theo Tháng ---
    with st.container(border=True):
        st.subheader("2. Báo cáo Doanh thu theo Tháng")
        st.markdown("Xuất file CSV chi tiết doanh thu, chi phí, lợi nhuận trong một tháng cụ thể.")

        # SỬA LỖI Ở ĐÂY: Dùng st.session_state để quản lý trạng thái

        # Khởi tạo session_state nếu chưa có
        if 'sales_report_path' not in st.session_state:
            st.session_state.sales_report_path = None

        with st.form("sales_report_form"):
            now = datetime.now(VN_TZ)
            c1, c2 = st.columns(2)
            year = c1.number_input("Chọn Năm", value=now.year, step=1)
            month = c2.number_input("Chọn Tháng", min_value=1, max_value=12, value=now.month)

            submitted = st.form_submit_button("📈 Tạo Báo cáo Doanh thu")
            if submitted:
                try:
                    # Khi nhấn nút, ta chỉ tạo file và LƯU ĐƯỜNG DẪN vào session_state
                    summary = compute_financial_summary(pm, tm, month=month, year=year, out_dir=REPORTS_DIR)
                    file_name = f"sales_summary_{month:02d}_{year}.csv"
                    file_path = REPORTS_DIR / file_name

                    st.session_state.sales_report_path = str(file_path)  # Lưu đường dẫn
                    st.success(f"✅ Đã tạo thành công báo cáo cho tháng {month}/{year}! Nhấn nút 'Tải về' bên dưới.")
                except Exception as e:
                    st.error("Lỗi khi tạo báo cáo doanh thu.")
                    st.exception(e)
                    st.session_state.sales_report_path = None  # Xóa trạng thái nếu có lỗi

        # ĐẶT NÚT DOWNLOAD BÊN NGOÀI FORM
        # Nút này chỉ hiển thị nếu có một báo cáo hợp lệ đã được tạo
        if st.session_state.sales_report_path and Path(st.session_state.sales_report_path).exists():
            file_path = Path(st.session_state.sales_report_path)
            with open(file_path, "rb") as f:
                st.download_button(
                    label=f"📥 Tải về báo cáo tháng {file_path.stem.split('_')[-2]}/{file_path.stem.split('_')[-1]} (.csv)",
                    data=f,
                    file_name=file_path.name,
                    mime="text/csv"
                )

# =================================================================================
# === TRANG CÀI ĐẶT
# =================================================================================
elif menu == "⚙️ Cài đặt":
    st.title("⚙️ Cài đặt hệ thống")
    with st.container(border=True):
        st.subheader("Quản lý danh mục")

        current_cats = cm.get_all_names()
        st.write("Các danh mục hiện có:", ", ".join(current_cats) if current_cats else "Chưa có danh mục nào.")

        c1, c2 = st.columns(2)
        with c1:
            new_cat = st.text_input("Tên danh mục mới")
            if st.button("Thêm danh mục"):
                if new_cat:
                    try:
                        cm.add_category(new_cat)
                        st.success(f"Đã thêm '{new_cat}'")
                        st.rerun()
                    except Exception as e:
                        st.error(e)
        with c2:
            cat_to_del = st.selectbox("Chọn danh mục để xóa", options=current_cats)
            if st.button("Xóa danh mục", type="primary"):
                try:
                    cm.remove_category(cat_to_del)
                    st.success(f"Đã xóa '{cat_to_del}'")
                    st.rerun()
                except Exception as e:
                    st.error(e)