import os
import json
from pathlib import Path
from src.main import cli  # hoặc hàm run_cli nếu bạn đã export
from src.utils.run_cli_with_input import run_cli_with_inputs   # giả sử bạn đã có sẵn hàm này
DATA_DIR = Path("data")

def reset_data():
    """Xóa sạch categories, products, transactions trước mỗi test"""
    files = ["categories.json", "products.json", "transactions.json"]
    for f in files:
        path = DATA_DIR / f
        if path.exists():
            with open(path, "w", encoding="utf-8") as fp:
                json.dump([], fp)

def test_add_and_search_product(monkeypatch):
    inputs = [
        "1",       # vào menu quản lý sản phẩm
        "1.1",     # thêm sản phẩm
        "T1", "Test Product", "Misc", "100", "120", "10", "2", "cái",
        "1.4",     # tìm sản phẩm
        "Test", "name",
        "0",       # quay lại menu chính
        "5"        # thoát
    ]
    out = run_cli_with_inputs(monkeypatch, inputs)
    # Check sản phẩm có trong output
    assert "Test Product" in out
    assert "T1" in out


def test_transaction_flow(monkeypatch):
    inputs = [
        "1", "1.5", "Drinks",                      # thêm category Drinks
        "1.1", "T2", "Milk", "Drinks", "50", "80", "5", "2", "hộp", "0",
        "2", "2.1", "T2", "10", "test nhập",       # nhập kho
        "2.2", "T2", "3", "bán lẻ",                # xuất kho
        "2.3",                                     # xem lịch sử
        "0", "5"
    ]
    out = run_cli_with_inputs(monkeypatch, inputs)

    # Kiểm tra giao dịch thực sự được log
    assert "T2" in out                # product_id phải xuất hiện
    assert "IMPORT" in out            # có giao dịch nhập
    assert "EXPORT" in out            # có giao dịch xuất
    assert "test nhập" in out or "bán lẻ" in out   # ghi chú có trong log



