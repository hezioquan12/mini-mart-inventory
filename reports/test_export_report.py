from pathlib import Path
import csv
import json
from datetime import datetime
from openpyxl import Workbook

# Import các class từ project của bạn
from src.inventory.product_manager import ProductManager
from src.sales.transaction_manager import TransactionManager
from src.report_and_sreach import report


def export_transactions(transaction_mgr, out_csv_path, out_json_path):
    transactions = transaction_mgr.transactions  # lấy danh sách giao dịch

    import csv
    import json

    # Xuất CSV
    with open(out_csv_path, "w", encoding="utf-8", newline="") as f_csv:
        writer = csv.writer(f_csv)
        writer.writerow(["transaction_id", "product_id", "trans_type", "quantity", "note"])
        for t in transactions:
            writer.writerow([t.transaction_id, t.product_id, t.trans_type, t.quantity, t.note])

    # Xuất JSON
    json_data = [
        {
            "transaction_id": t.transaction_id,
            "product_id": t.product_id,
            "trans_type": t.trans_type,
            "quantity": t.quantity,
            "note": t.note,
        }
        for t in transactions
    ]
    with open(out_json_path, "w", encoding="utf-8") as f_json:
        json.dump(json_data, f_json, indent=4, ensure_ascii=False)

    print(f"Export transactions done:\n- CSV: {out_csv_path}\n- JSON: {out_json_path}")



def export_low_stock_report(pm, transaction_mgr, reorder_buffer, out_txt_path, out_csv_path, out_xlsx_path):
    alerts = report.run_and_persist(
        pm,
        transaction_mgr=transaction_mgr,
        reorder_buffer=reorder_buffer,
        out_txt_path=str(out_txt_path),
        out_csv_path=str(out_csv_path),
        out_xlsx_path=str(out_xlsx_path)
    )
    print(f"Low stock report done:\n- TXT: {out_txt_path}\n- CSV: {out_csv_path}\n- XLSX: {out_xlsx_path}")
    return alerts



def run_export_test(pm, tm):
    out_dir = Path("test_exports")
    out_dir.mkdir(exist_ok=True)

    csv_path = out_dir / "transactions.csv"
    json_path = out_dir / "transactions.json"

    txt_path = out_dir / "low_stock.txt"
    low_csv_path = out_dir / "low_stock.csv"
    xlsx_path = out_dir / "low_stock.xlsx"

    export_transactions(tm, csv_path, json_path)
    alerts = export_low_stock_report(pm, tm, reorder_buffer=5, out_txt_path=txt_path, out_csv_path=low_csv_path, out_xlsx_path=xlsx_path)

    print("Alerts:", alerts)


if __name__ == "__main__":
    # Tạo ProductManager và TransactionManager
    data_dir = Path("data_test")
    data_dir.mkdir(exist_ok=True)

    products_file = data_dir / "products.csv"
    transactions_file = data_dir / "transactions.csv"

    # Ghi header cho file products
    products_file.write_text(
        "product_id,product_name,category,price_in,price_out,stock,reorder_point,unit\n",
        encoding="utf-8"
    )

    # Ghi header cho file transactions
    transactions_file.write_text(
        "transaction_id,product_id,trans_type,quantity,note\n",
        encoding="utf-8"
    )

    pm = ProductManager(products_file)
    tm = TransactionManager(transactions_file, pm)

    # Thêm dữ liệu mẫu
    pm.category_mgr.add_category("Đồ uống")
    pm.add_product("SP01", "Sữa Vinamilk", "Đồ uống", 10000, 15000, 5, 20, "hộp")
    tm.add_transaction("SP01", "EXPORT", 3, "Test transaction")

    # Chạy export test
    run_export_test(pm, tm)
