import csv
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict

from product_manager import ProductManager
from transaction import Transaction


class TransactionManager:
    DEFAULT_FIELDS = ["transaction_id", "product_id", "type", "quantity", "date", "note"]

    def __init__(self, storage_file: str = "transactions.csv", product_mgr: Optional[ProductManager] = None):
        self.storage_file = Path(storage_file)
        self.transactions: List[Transaction] = []
        self.product_mgr = product_mgr or ProductManager()
        self._load_transactions()

    # -----------------------------
    # Load / Save
    # -----------------------------
    def _load_transactions(self):
        if not self.storage_file.exists():
            self.transactions = []
            return
        with self.storage_file.open(mode="r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            self.transactions = []
            for row in reader:
                try:
                    self.transactions.append(Transaction.from_dict(row))
                except Exception as e:
                    print(f"⚠️ Bỏ qua dòng lỗi: {row} ({e})")

    def _save_transactions(self):
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        with self.storage_file.open(mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.DEFAULT_FIELDS)
            writer.writeheader()
            for t in self.transactions:
                writer.writerow(t.to_dict())

    # -----------------------------
    # Core functions
    # -----------------------------
    def _generate_transaction_id(self) -> str:
        return f"T{len(self.transactions) + 1:05d}"

    def add_transaction(self, product_id: str, type: str, quantity: int, note: str = "") -> Transaction:
        if type not in ("IMPORT", "EXPORT"):
            raise ValueError("Loại giao dịch phải là IMPORT hoặc EXPORT")
        if quantity <= 0:
            raise ValueError("Số lượng phải > 0")

        # cập nhật tồn kho qua ProductManager
        delta = quantity if type == "IMPORT" else -quantity
        self.product_mgr.apply_stock_change(product_id, delta)

        # tạo transaction
        transaction = Transaction(
            transaction_id=self._generate_transaction_id(),
            product_id=product_id,
            type=type,
            quantity=quantity,
            date=datetime.utcnow(),
            note=note,
        )
        self.transactions.append(transaction)
        self._save_transactions()
        return transaction

    def list_transactions(self) -> List[Transaction]:
        return list(self.transactions)

    def filter_transactions(self, product_id: Optional[str] = None, type: Optional[str] = None,
                            start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Transaction]:
        results = self.transactions
        if product_id:
            results = [t for t in results if t.product_id == product_id]
        if type:
            results = [t for t in results if t.type == type]
        if start_date:
            results = [t for t in results if t.date >= start_date]
        if end_date:
            results = [t for t in results if t.date <= end_date]
        return results

    # -----------------------------
    # Reports
    # -----------------------------
    def generate_stock_report(self) -> List[Dict[str, any]]:
        report = []
        for p in self.product_mgr.list_products():
            status = "OK"
            if p.stock_quantity <= 0:
                status = "OUT_OF_STOCK"
            elif p.stock_quantity <= p.min_threshold:
                status = "LOW_STOCK"
            report.append({
                "product_id": p.product_id,
                "name": p.name,
                "stock_quantity": p.stock_quantity,
                "min_threshold": p.min_threshold,
                "status": status
            })
        return report
