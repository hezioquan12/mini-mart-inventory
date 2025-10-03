from pathlib import Path
from src.report_and_sreach.report import export_full_report_txt

def test_export_full_report_real_file():
    """
    Test xuất báo cáo nâng cao ra file thật (không dùng tmp_path).
    File sẽ nằm trong thư mục reports/ để mở ra xem trực tiếp.
    """
    # 1. Data giả lập
    products = [
        {"id": "SP001", "name": "Bánh mì sandwich", "category": "Thực phẩm",
         "cost": 15000, "price": 25000, "stock": 45, "threshold": 10, "status": "BÌNH THƯỜNG"},
        {"id": "SP002", "name": "Coca Cola 330ml", "category": "Đồ uống",
         "cost": 8000, "price": 12000, "stock": 5, "threshold": 20, "status": "SẮP HẾT"},
        {"id": "SP003", "name": "Dầu gội Head&S", "category": "Mỹ phẩm",
         "cost": 80000, "price": 120000, "stock": 0, "threshold": 5, "status": "HẾT HÀNG"},
    ]

    stock_alerts = {
        "out_of_stock": [products[2]],
        "low_stock": [products[1]],
        "total_reorder": 2,
    }

    revenue_summary = {
        "revenue": 45680000,
        "cost": 32150000,
        "profit": 13530000,
        "margin": 29.6,
        "by_category": {
            "Thực phẩm": 18500000,
            "Đồ uống": 12300000,
            "Gia dụng": 8750000,
            "Mỹ phẩm": 6130000,
        },
    }

    top_sellers = [
        {"name": "Bánh mì sandwich", "quantity": 1250, "unit": "cái", "revenue": 31250000},
        {"name": "Nước suối 500ml", "quantity": 890, "unit": "chai", "revenue": 8900000},
        {"name": "Mì tôm Hảo Hảo", "quantity": 450, "unit": "gói", "revenue": 6750000},
    ]

    # 2. Xuất file thực tế
    out_file = export_full_report_txt(
        products, stock_alerts, revenue_summary, top_sellers,
        filename="bao_cao_nang_cao_test.txt"
    )

    # 3. Kiểm tra file tồn tại
    out_path = Path(out_file)
    assert out_path.exists(), f"File không tồn tại: {out_path}"

    # 4. In nội dung ra console để dễ xem khi pytest -s
    print("\n=== Nội dung file báo cáo ===\n")
    print(out_path.read_text(encoding="utf-8"))
    print("\n=== Hết ===\n")

    # 5. Check vài thông tin chính
    content = out_path.read_text(encoding="utf-8")
    assert "BÁO CÁO NÂNG CAO" in content
    assert "DANH SÁCH SẢN PHẨM" in content
    assert "CẢNH BÁO TỒN KHO" in content
    assert "BÁO CÁO DOANH THU" in content
    assert "TOP SẢN PHẨM BÁN CHẠY" in content

