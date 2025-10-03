import os
from pathlib import Path
import pytest

from src.inventory.product_manager import ProductManager
from src.sales.transaction_manager import TransactionManager
from src.report_and_sreach import report


@pytest.fixture
def sample_setup(tmp_path):
    """
    Tạo ProductManager và TransactionManager với dữ liệu mẫu.
    Trả về: (pm, tm)
    """
    # Tạo thư mục data
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Tạo file CSV products với header
    products_file = data_dir / "products.csv"
    products_file.write_text(
        "product_id,product_name,category,price_in,price_out,stock,reorder_point,unit\n",
        encoding="utf-8"
    )

    # Tạo file CSV transactions với header
    transactions_file = data_dir / "transactions.csv"
    transactions_file.write_text(
        "transaction_id,product_id,trans_type,quantity,note\n",
        encoding="utf-8"
    )

    # Tạo ProductManager và TransactionManager
    pm = ProductManager(products_file)
    tm = TransactionManager(transactions_file, pm)

    # Thêm danh mục
    pm.category_mgr.add_category("Đồ uống")

    # Thêm sản phẩm mẫu với stock thấp để kích hoạt báo cáo low stock
    pm.add_product(
        "SP01", "Sữa Vinamilk", "Đồ uống",
        10000, 15000, 5, 20, "hộp"  # stock_quantity=5 < reorder_point=20
    )

    # Thêm một giao dịch mẫu
    tm.add_transaction("SP01", "EXPORT", 3, "Test transaction")

    return pm, tm


def test_export_transactions(sample_setup, tmp_path):
    pm, tm = sample_setup

    # Tạo thư mục xuất
    out_dir = tmp_path / "exports"
    out_dir.mkdir()

    csv_path = out_dir / "transactions.csv"
    json_path = out_dir / "transactions.json"

    # Xuất dữ liệu giao dịch
    tm.export_transactions(csv_path)
    tm.export_transactions(json_path)

    # Kiểm tra file đã được tạo
    assert csv_path.exists(), "File CSV transactions không được tạo"
    assert json_path.exists(), "File JSON transactions không được tạo"

    # Kiểm tra nội dung file
    csv_content = csv_path.read_text(encoding="utf-8")
    json_content = json_path.read_text(encoding="utf-8")

    assert "transaction_id" in csv_content, "CSV không chứa header transaction_id"
    assert "SP01" in csv_content, "CSV không chứa dữ liệu giao dịch SP01"

    assert '"transaction_id"' in json_content, "JSON không chứa trường transaction_id"
    assert "SP01" in json_content, "JSON không chứa dữ liệu giao dịch SP01"


def test_export_low_stock_report(sample_setup, tmp_path):
    pm, tm = sample_setup

    # Tạo thư mục xuất
    out_dir = tmp_path / "exports"
    out_dir.mkdir()

    txt_path = out_dir / "low_stock.txt"
    csv_path = out_dir / "low_stock.csv"
    xlsx_path = out_dir / "low_stock.xlsx"

    # Chạy báo cáo và lưu file
    alerts = report.run_and_persist(
        pm,
        transaction_mgr=tm,
        reorder_buffer=5,
        out_txt_path=txt_path,
        out_csv_path=csv_path,
        out_xlsx_path=xlsx_path,
    )

    # Kiểm tra file đã tạo
    assert txt_path.exists(), "File TXT báo cáo low stock không được tạo"
    assert csv_path.exists(), "File CSV báo cáo low stock không được tạo"
    assert xlsx_path.exists(), "File XLSX báo cáo low stock không được tạo"

    txt_content = txt_path.read_text(encoding="utf-8")
    csv_content = csv_path.read_text(encoding="utf-8")

    # Kiểm tra nội dung TXT báo cáo
    assert "CẢNH BÁO TỒN KHO" in txt_content, "TXT báo cáo không chứa tiêu đề cảnh báo tồn kho"
    assert "HẾT HÀNG" in txt_content or "SẮP HẾT HÀNG" in txt_content, "TXT báo cáo không chứa cảnh báo tồn kho"

    # Kiểm tra CSV báo cáo có sản phẩm low stock
    assert "SP01" in csv_content, "CSV báo cáo không chứa dữ liệu sản phẩm SP01"

    # Kiểm tra alerts trả về
    assert len(alerts) > 0, "Không có cảnh báo được trả về từ báo cáo"
