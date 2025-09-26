# transaction_manager.py (improved)
import csv
import logging
import uuid
import io
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Any, Dict

from src.sales.transaction import Transaction
from src.inventory.product_manager import ProductManager
from src.utils.io_utils import atomic_write_text

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class TransactionManager:
    DEFAULT_FIELDS = ["transaction_id", "product_id", "trans_type", "quantity", "date", "note"]

    def __init__(self, storage_file: str = "data/transactions.csv", product_mgr: Optional[ProductManager] = None):
        self.storage_file = Path(storage_file)
        self.transactions: List[Transaction] = []
        self.product_mgr = product_mgr or ProductManager()
        self._load_transactions()

    def _load_transactions(self):
        self.transactions = []
        if not self.storage_file.exists():
            return
        try:
            with self.storage_file.open(mode="r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader, start=1):
                    try:
                        t = Transaction.from_dict(row)
                        # ensure unique id
                        if any(existing.transaction_id == t.transaction_id for existing in self.transactions):
                            logger.warning("Duplicate transaction_id %s at row %s - generating new id", t.transaction_id, i)
                            t.transaction_id = self._generate_transaction_id()
                        self.transactions.append(t)
                    except Exception as e:
                        logger.exception("Skipping bad transaction row %s: %s. Row content: %s", i, e, row)
        except Exception:
            logger.exception("Failed to read transactions file %s", self.storage_file)

    def _save_transactions(self):
        rows = [t.to_dict() for t in self.transactions]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=self.DEFAULT_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        atomic_write_text(self.storage_file, buf.getvalue())

    def _generate_transaction_id(self) -> str:
        return f"T{uuid.uuid4().hex}"

    def add_transaction(self, product_id: str, trans_type: str, quantity: int, note: str = "") -> Transaction:
        trans_type = str(trans_type).upper()

        # --- Validate loại giao dịch ---
        if trans_type not in ("IMPORT", "EXPORT"):
            raise ValueError("Loại giao dịch phải là 'IMPORT' hoặc 'EXPORT'")

        # --- Validate số lượng ---
        try:
            qty = int(quantity)
        except (ValueError, TypeError):
            raise ValueError("Số lượng phải là số nguyên hợp lệ")
        if qty <= 0:
            raise ValueError("Số lượng phải > 0")

        # --- Validate sản phẩm tồn tại ---
        try:
            _ = self.product_mgr.get_product(product_id)
        except Exception as e:
            raise ValueError(f"Product '{product_id}' không tồn tại") from e

        # --- Tính thay đổi tồn kho ---
        delta = qty if trans_type == "IMPORT" else -qty

        try:
            self.product_mgr.apply_stock_change(product_id, delta)
        except Exception as e:
            logger.exception("Stock change failed for %s (delta=%s): %s", product_id, delta, e)
            raise

        # --- Tạo giao dịch ---
        tx = Transaction(
            transaction_id=self._generate_transaction_id(),
            product_id=product_id,
            trans_type=trans_type,
            quantity=qty,
            note=note or ""
        )

        self.transactions.append(tx)

        # --- Lưu giao dịch, rollback nếu thất bại ---
        try:
            self._save_transactions()
        except Exception as e:
            logger.error("Save failed after adding tx %s: %s. Rolling back.", tx.transaction_id, e)
            try:
                self.product_mgr.apply_stock_change(product_id, -delta)
                logger.info("Rollback succeeded for product %s", product_id)
            except Exception:
                logger.exception("Rollback failed for product %s", product_id)
            try:
                self.transactions.remove(tx)
            except Exception:
                logger.exception("Failed to remove transaction %s during rollback", tx.transaction_id)
            raise

        return tx

    def list_transactions(self) -> List[Transaction]:
        return list(self.transactions)

    def filter_transactions(self, product_id: Optional[str] = None, trans_type: Optional[str] = None,
                            date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> List[Transaction]:
        result = []
        for t in self.transactions:
            if product_id and t.product_id != product_id:
                continue
            if trans_type and t.trans_type.upper() != trans_type.upper():
                continue
            if date_from and t.date < date_from:
                continue
            if date_to and t.date > date_to:
                continue
            result.append(t)
        return result

    def export_transactions(self, out_path: str):
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        rows = [t.to_dict() for t in self.transactions]
        if out.suffix.lower() == ".json":
            atomic_write_text(out, json.dumps(rows, ensure_ascii=False, indent=2))
            return
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=self.DEFAULT_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        atomic_write_text(out, buf.getvalue())

    def generate_stock_report(self) -> List[Dict[str, Any]]:
        return [
            {
                "product_id": p.product_id,
                "name": p.name,
                "category": p.category,
                "stock_quantity": p.stock_quantity,
                "min_threshold": p.min_threshold,
            }
            for p in self.product_mgr.list_products()
        ]

