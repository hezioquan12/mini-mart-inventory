from dataclasses import dataclass
from pathlib import Path
from src.report_and_sreach.report import compute_financial_summary
from decimal import Decimal

@dataclass
class ProdMock:
    product_id: str
    name: str
    category: str
    sell_price: str
    cost_price: str

@dataclass
class TxMock:
    product_id: str
    trans_type: str
    quantity: int
    date: str  # ISO string or datetime accepted by compute_financial_summary

class PMMock:
    def __init__(self, products):
        self._products = products
    def list_products(self):
        return list(self._products)

class TMMock:
    def __init__(self, transactions):
        self._transactions = transactions
    def list_transactions(self):
        return list(self._transactions)

def test_demo_generate_and_export_sales_summary():
    tmp_path = Path("../reports/")  # Change to desired output directory
    """
    Demo test that generates a sales_summary_MM_YYYY.csv in tmp_path.
    Run with: pytest -q tests/test_financial_report_demo.py -s
    """
    # demo products
    p1 = ProdMock("P1", "Prod A", "Misc", sell_price="200", cost_price="120")
    p2 = ProdMock("P2", "Prod B", "Drinks", sell_price="150", cost_price="80")
    p3 = ProdMock("P3", "Prod C", "Misc", sell_price="50", cost_price="20")
    pm = PMMock([p1, p2, p3])

    # demo transactions (October 2025)
    txs = [
        TxMock("P1", "EXPORT", 3, "2025-10-02T09:00:00+07:00"),
        TxMock("P2", "EXPORT", 5, "2025-10-05T10:00:00+07:00"),
        TxMock("P3", "IMPORT", 10, "2025-10-06T11:00:00+07:00"),  # import counts as cost only
        TxMock("P999", "EXPORT", 2, "2025-10-07T12:00:00+07:00"), # unknown product
    ]
    tm = TMMock(txs)

    # generate summary and export CSV
    summary = compute_financial_summary(pm, tm, month=10, year=2025, out_dir=tmp_path, top_k=5, currency="VND")

    csv_path = Path(tmp_path / "sales_summary_10_2025.csv")
    assert csv_path.exists(), f"CSV not found: {csv_path}"

    content = csv_path.read_text(encoding="utf-8")
    # Print so you can inspect output when running pytest -s
    print("\n=== sales_summary_10_2025.csv ===\n")
    print(content)
    print("=== end of CSV ===\n")

    # basic sanity checks
    # expected revenue = P1:200*3 + P2:150*5 + P999:0*2 = 600 + 750 = 1350
    assert str(Decimal("200") * 3 + Decimal("150") * 5) in content
    assert "Top Sellers" in content
    assert "By Category" in content