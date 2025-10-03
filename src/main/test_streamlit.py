# test_streamlit.py
from __future__ import annotations
import sys, os
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import traceback

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ----------------------------
# Fix ModuleNotFoundError
# ----------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ----------------------------
# Import modules dự án
# ----------------------------
try:
    from src.inventory.category_manager import CategoryManager
    from src.inventory.product_manager import ProductManager
    from src.sales.transaction_manager import TransactionManager
    from src.report_and_sreach.sreach import SearchEngine
    from src.report_and_sreach.report import (
        generate_low_stock_alerts,
        format_alerts_text,
        run_and_persist,
        compute_financial_summary,
        format_financial_summary_text
    )
    from src.utils.time_zone import VN_TZ
except Exception as e:
    st.error("Không import được module dự án. Kiểm tra cấu trúc src / PYTHONPATH")
    st.exception(e)
    raise

# ----------------------------
# Paths & session managers
# ----------------------------
DATA_DIR = Path("data")
REPORTS_DIR = Path("reports")
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

def get_managers():
    if "category_mgr" not in st.session_state:
        st.session_state.category_mgr = CategoryManager(str(DATA_DIR / "categories.json"))
    if "product_mgr" not in st.session_state:
        st.session_state.product_mgr = ProductManager(str(DATA_DIR / "products.json"), category_mgr=st.session_state.category_mgr)
    if "transaction_mgr" not in st.session_state:
        st.session_state.transaction_mgr = TransactionManager(str(DATA_DIR / "transactions.csv"), product_mgr=st.session_state.product_mgr)
    if "search_engine" not in st.session_state:
        st.session_state.search_engine = SearchEngine(st.session_state.product_mgr, st.session_state.transaction_mgr)
    return st.session_state.category_mgr, st.session_state.product_mgr, st.session_state.transaction_mgr, st.session_state.search_engine

cm, pm, tm, se = get_managers()

# ----------------------------
# Helpers
# ----------------------------
def fmt_vnd(v):
    try:
        return f"{int(v):,}"
    except Exception:
        return str(v)

def normalize_search_results(results):
    normalized = []
    for p in results:
        if hasattr(p, "product_id"):
            normalized.append({
                "product_id": p.product_id,
                "name": p.name,
                "category": p.category,
                "cost_price": fmt_vnd(p.cost_price),
                "sell_price": fmt_vnd(p.sell_price),
                "stock_quantity": p.stock_quantity,
                "min_threshold": p.min_threshold,
                "unit": p.unit,
                "last_updated": getattr(p, "last_updated", ""),
            })
        elif isinstance(p, dict):
            normalized.append({
                "product_id": p.get("product_id", ""),
                "name": p.get("name", ""),
                "category": p.get("category", ""),
                "cost_price": fmt_vnd(p.get("cost_price", 0)),
                "sell_price": fmt_vnd(p.get("sell_price", 0)),
                "stock_quantity": p.get("stock_quantity", 0),
                "min_threshold": p.get("min_threshold", 0),
                "unit": p.get("unit", ""),
                "last_updated": p.get("last_updated", ""),
            })
    return normalized

def show_products_table(products):
    if not products:
        st.info("Không có sản phẩm.")
        return

    rows = normalize_search_results(products)
    df = pd.DataFrame(rows)

    # Đổi tên cột sang tiếng Việt
    rename_columns = {
        "product_id": "Mã SP",
        "name": "Tên sản phẩm",
        "category": "Danh mục",
        "cost_price": "Giá nhập (VND)",
        "sell_price": "Giá bán (VND)",
        "stock_quantity": "Tồn kho",
        "min_threshold": "Ngưỡng cảnh báo",
        "unit": "Đơn vị",
        "last_updated": "Cập nhật"
    }
    df.rename(columns=rename_columns, inplace=True)
    st.dataframe(df, use_container_width=True)
# ----------------------------
# Streamlit Layout
# ----------------------------
st.set_page_config(page_title="Quản Lý Siêu Thị Mini", layout="wide")
st.title("Quản Lý Kho Sản Phẩm")

menu = st.sidebar.selectbox("Chọn trang", ["Products", "Transactions", "Reports / Export", "Settings"])

# ------------------ Products ------------------
if menu == "Products":
    st.header("Quản lý sản phẩm")
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Danh sách sản phẩm")
        show_products_table(pm.list_products())
    with col2:
        st.subheader("Thêm / Cập nhật sản phẩm")
        mode = st.selectbox("Chọn", ["Thêm mới", "Cập nhật"])
        pid = st.text_input("Mã SP (product_id)")
        name = st.text_input("Tên sản phẩm")
        cat = st.selectbox("Danh mục", options=(cm.get_all_names() or ["(chưa có danh mục)"]))
        cost = st.text_input("Giá nhập")
        sell = st.text_input("Giá bán")
        qty = st.number_input("Tồn kho", min_value=0, value=0, step=1)
        thr = st.number_input("Ngưỡng cảnh báo", min_value=0, value=0, step=1)
        unit = st.text_input("Đơn vị", value="cái")

        if st.button("Thực hiện"):
            try:
                if mode == "Thêm mới":
                    pm.add_product(pid, name, cat, Decimal(cost or "0"), Decimal(sell or "0"), int(qty), int(thr), unit)
                    st.success("Thêm sản phẩm thành công")
                else:
                    pm.update_product(pid, name=name, category=cat, cost_price=Decimal(cost or "0"), sell_price=Decimal(sell or "0"), stock_quantity=int(qty), min_threshold=int(thr), unit=unit)
                    st.success("Cập nhật thành công")
            except Exception as e:
                st.error(f"Lỗi: {e}")
                st.exception(traceback.format_exc())

        st.markdown("---")
        st.subheader("Xóa sản phẩm")
        pid_del = st.text_input("Mã SP cần xóa", key="pid_del")
        if st.button("Xóa"):
            try:
                pm.delete_product(pid_del)
                st.success("Xóa thành công")
            except Exception as e:
                st.error(f"Lỗi: {e}")

        st.markdown("---")
        st.subheader("Tìm kiếm sản phẩm")
        kw = st.text_input("Từ khoá tìm kiếm")
        if st.button("Search"):
            try:
                if se:
                    res = se.search_products(kw)
                    st.write(f"Tìm thấy {res['total']} kết quả (hiển thị {len(res['results'])})")
                    show_products_table(res['results'])
                else:
                    results = pm.search_products(kw)
                    show_products_table(results)
            except Exception as e:
                st.error(e)
                st.exception(traceback.format_exc())

# ------------------ Transactions ------------------
elif menu == "Transactions":
    st.header("Nhập / Xuất / Lịch sử giao dịch")
    pid = st.text_input("Mã SP")
    ttype = st.selectbox("Loại", ["IMPORT", "EXPORT"])
    qty = st.number_input("Số lượng", min_value=1, value=1)
    note = st.text_input("Ghi chú")
    if st.button("Thêm giao dịch"):
        try:
            tx = tm.add_transaction(pid, ttype, int(qty), note=note)
            st.success(f"Thêm giao dịch {tx.transaction_id}")
        except Exception as e:
            st.error(e)
            st.exception(traceback.format_exc())

    st.subheader("Lịch sử giao dịch")
    tlist = tm.list_transactions()
    if not tlist:
        st.info("Không có giao dịch")
    else:
        rows = []
        for t in tlist:
            rows.append({
                "tx_id": t.transaction_id,
                "product_id": t.product_id,
                "type": t.trans_type,
                "qty": t.quantity,
                "date": getattr(t, "date", ""),
                "note": t.note
            })
        st.table(rows)

elif menu == "Reports / Export":
    st.header("Báo cáo & Xuất dữ liệu")

    if st.button("Sinh cảnh báo tồn kho"):
        try:
            txt_path = REPORTS_DIR / "low_stock.txt"
            csv_path = REPORTS_DIR / "low_stock.csv"
            xlsx_path = REPORTS_DIR / "low_stock.xlsx"

            alerts = run_and_persist(pm, tm,
                                     out_txt_path=str(txt_path),
                                     out_csv_path=str(csv_path),
                                     out_xlsx_path=str(xlsx_path))

            st.text(format_alerts_text(alerts))
            st.success("✅ Đã sinh cảnh báo và xuất file")
            st.write(f"📂 File đã lưu trong thư mục: `{REPORTS_DIR.resolve()}`")

            # Nút tải CSV
            if csv_path.exists():
                with open(csv_path, "rb") as f_csv:
                    st.download_button(
                        label="📥 Tải file CSV",
                        data=f_csv,
                        file_name="low_stock.csv",
                        mime="text/csv"
                    )

            # Nút tải Excel
            if xlsx_path.exists():
                with open(xlsx_path, "rb") as f_xlsx:
                    st.download_button(
                        label="📥 Tải file Excel",
                        data=f_xlsx,
                        file_name="low_stock.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            # Nút tải TXT
            if txt_path.exists():
                with open(txt_path, "rb") as f_txt:
                    st.download_button(
                        label="📥 Tải file TXT",
                        data=f_txt,
                        file_name="low_stock.txt",
                        mime="text/plain"
                    )

        except Exception as e:
            st.error(e)
            st.exception(traceback.format_exc())

    st.markdown("---")
    st.subheader("Báo cáo doanh thu theo tháng")

    coly, colm = st.columns(2)
    with coly:
        year = st.number_input("Năm", value=datetime.now().year, step=1)
    with colm:
        month = st.number_input("Tháng", min_value=1, max_value=12, value=datetime.now().month)

    if st.button("Tạo báo cáo & biểu đồ"):
        try:
            summary = compute_financial_summary(pm, tm, month=month, year=year)

            st.subheader(f"Báo cáo tài chính tháng {month}/{year}")

            # Tổng hợp
            st.write(f"**Tổng doanh thu:** {fmt_vnd(summary.get('total_revenue', 0))} VND")
            st.write(f"**Tổng chi phí:** {fmt_vnd(summary.get('total_cost', 0))} VND")
            st.write(f"**Tổng lợi nhuận:** {fmt_vnd(summary.get('total_profit', 0))} VND")

            # -------- Biểu đồ 1: Bar chart Doanh thu & Lợi nhuận theo danh mục --------
            by_cat = summary.get("by_category") or {}
            if by_cat:
                df_cat = pd.DataFrame([
                    {"Danh mục": k,
                     "Doanh thu": float(v.get("revenue", 0)),
                     "Lợi nhuận": float(v.get("profit", 0))}
                    for k, v in by_cat.items()
                ])
                st.subheader("📊 Doanh thu & Lợi nhuận theo danh mục")
                fig, ax = plt.subplots(figsize=(8, 4))
                df_cat.plot(kind="bar", x="Danh mục", y=["Doanh thu", "Lợi nhuận"], ax=ax)
                ax.set_ylabel("VND")
                ax.set_title(f"Doanh thu & Lợi nhuận tháng {month}/{year}")
                st.pyplot(fig)

            # -------- Biểu đồ 2: Line chart Xu hướng doanh thu theo ngày --------
            st.subheader("📈 Xu hướng doanh thu & lợi nhuận theo ngày")
            revenue_by_day = summary.get("revenue_by_day") or []
            if revenue_by_day:
                df_day = pd.DataFrame(revenue_by_day)
                fig2, ax2 = plt.subplots(figsize=(10, 4))
                df_day.plot(x="Ngày", y=["Doanh thu", "Lợi nhuận"], kind="line", marker="o", ax=ax2)
                ax2.set_ylabel("VND")
                ax2.set_title(f"Xu hướng doanh thu & lợi nhuận tháng {month}/{year}")
                st.pyplot(fig2)
            else:
                st.info("Không có dữ liệu xu hướng ngày.")

            # -------- Biểu đồ 3: Pie chart Tỉ lệ doanh thu theo danh mục --------
            st.subheader("🥧 Tỉ lệ doanh thu theo danh mục")
            if by_cat:
                fig3, ax3 = plt.subplots(figsize=(6, 6))
                ax3.pie(df_cat["Doanh thu"], labels=df_cat["Danh mục"], autopct="%1.1f%%", startangle=90)
                ax3.set_title("Tỉ lệ doanh thu theo danh mục")
                st.pyplot(fig3)

            # -------- Biểu đồ 4: Horizontal bar chart Top sản phẩm --------
            st.subheader("🏆 Top sản phẩm bán chạy")
            try:
                top_sellers = summary.get("top_sellers") or []
                st.write("🔍 Dữ liệu Top Sellers:", top_sellers)

                if top_sellers:
                    df_top = pd.DataFrame(top_sellers)
                    st.write("📊 DataFrame Top Sellers:", df_top.head())

                    if not df_top.empty and "revenue" in df_top.columns:
                        if "name" not in df_top.columns:
                            possible_name_cols = ["product_name", "Tên sản phẩm", "name_product"]
                            for col in possible_name_cols:
                                if col in df_top.columns:
                                    df_top.rename(columns={col: "name"}, inplace=True)
                                    break

                        df_top["revenue"] = pd.to_numeric(df_top["revenue"], errors="coerce").fillna(0)

                        if not df_top["revenue"].empty and df_top["revenue"].sum() > 0:
                            fig4, ax4 = plt.subplots(figsize=(8, 4))
                            df_top.sort_values("revenue", ascending=True).plot(
                                kind="barh", x="name", y="revenue", ax=ax4, color="skyblue"
                            )
                            ax4.set_xlabel("Doanh thu (VND)")
                            ax4.set_title("Top sản phẩm bán chạy nhất")
                            st.pyplot(fig4)
                        else:
                            st.info("Không có dữ liệu doanh thu hợp lệ để vẽ biểu đồ.")
                    else:
                        st.info("Không có dữ liệu doanh thu để vẽ biểu đồ.")
                else:
                    st.info("Không có dữ liệu sản phẩm bán chạy.")
            except Exception as e:
                st.error("Lỗi khi vẽ biểu đồ Top Sellers")
                st.exception(traceback.format_exc())

        except Exception as e:
            st.error("Lỗi khi tạo báo cáo & biểu đồ")
            st.exception(traceback.format_exc())


# ------------------ Settings ------------------
elif menu == "Settings":
    st.header("Cài đặt")
    st.subheader("Danh mục hiện có")
    st.write(cm.get_all_names())
    new_cat = st.text_input("Thêm danh mục mới")
    if st.button("Thêm danh mục"):
        try:
            cm.add_category(new_cat)
            st.success("Đã thêm danh mục")
        except Exception as e:
            st.error(e)

