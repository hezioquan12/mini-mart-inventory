# src/sales/transaction_manager.py
from __future__ import annotations

import csv
import io
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# relative imports (adjust if your package layout differs)
from transaction import Transaction
from src.inventory.product_manager import ProductManager

# utilities
from src.utils.validators import parse_iso_datetime  # moved to top to avoid inline imports
try:
    from src.utils.io_utils import atomic_write_text as _atomic_write_text  # prefer central helper
except Exception:
    _atomic_write_text = None  # fallback will be used

logger = logging.getLogger(__name__)
# NOTE: Do NOT call logging.basicConfig() inside library modules.


def _atomic_write_fallback(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Fallback atomic write implementation (write to temp file then replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
            f.write(text)
        os.replace(tmp_path, str(path))
    except (OSError, IOError):
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


# choose implementation
_atomic_write = _atomic_write_text if _atomic_write_text is not None else _atomic_write_fallback


class TransactionManager:
    """
    Manage transactions (CSV/JSON storage) and coordinate with ProductManager for stock changes.

    Notes:
      - This class is *not* multi-process safe. For concurrent writers use a file lock.
      - date comparisons assume transaction.date is timezone-aware (UTC). Bounds that are naive
        will be treated as UTC.
    """

    DEFAULT_FIELDS = ["transaction_id", "product_id", "trans_type", "quantity", "date", "note"]

    def __init__(self, storage_file: Union[str, Path] = "data/transactions.csv",
                 product_mgr: Optional[ProductManager] = None) -> None:
        self.storage_file = Path(storage_file)
        self.transactions: List[Transaction] = []
        self.product_mgr = product_mgr or ProductManager()
        self._load_transactions()

    def _load_transactions(self) -> None:
        """Load transactions from CSV (fallback to empty list on error)."""
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
                            logger.warning(
                                "Duplicate transaction_id %s at row %s - generating new id",
                                t.transaction_id, i
                            )
                            t.transaction_id = self._generate_transaction_id()
                        self.transactions.append(t)
                    except Exception:
                        logger.exception("Skipping bad transaction row %s. Row content: %s", i, row)
        except Exception:
            logger.exception("Failed to read transactions file %s", self.storage_file)

    def _save_transactions(self) -> None:
        """Serialize transactions to CSV and write atomically."""
        rows = [t.to_dict() for t in self.transactions]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=self.DEFAULT_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        _atomic_write(self.storage_file, buf.getvalue())

    def _generate_transaction_id(self) -> str:
        return f"T{uuid.uuid4().hex}"

    def add_transaction(self, product_id: str, trans_type: str, quantity: int, note: str = "") -> Transaction:
        """Add transaction and persist; rollback stock and memory if save fails."""
        trans_type_u = str(trans_type).upper()

        # validate trans_type
        if trans_type_u not in ("IMPORT", "EXPORT"):
            raise ValueError("Loại giao dịch phải là 'IMPORT' hoặc 'EXPORT'")

        # validate quantity
        try:
            qty = int(quantity)
        except (ValueError, TypeError):
            raise ValueError("Số lượng phải là số nguyên hợp lệ")
        if qty <= 0:
            raise ValueError("Số lượng phải > 0")

        # validate product existence
        try:
            _ = self.product_mgr.get_product(product_id)
        except Exception as exc:
            raise ValueError(f"Product '{product_id}' không tồn tại") from exc

        delta = qty if trans_type_u == "IMPORT" else -qty

        # apply stock change first
        try:
            self.product_mgr.apply_stock_change(product_id, delta)
        except Exception:
            logger.exception("Stock change failed for %s (delta=%s)", product_id, delta)
            raise

        tx = Transaction(
            transaction_id=self._generate_transaction_id(),
            product_id=product_id,
            trans_type=trans_type_u,
            quantity=qty,
            note=note or ""
        )

        self.transactions.append(tx)
        self.log_transaction(tx)

        # persist and rollback on failure
        try:
            self._save_transactions()
        except Exception:
            logger.error("Save failed after adding tx %s. Rolling back.", tx.transaction_id)
            # rollback stock
            try:
                self.product_mgr.apply_stock_change(product_id, -delta)
                logger.info("Rollback succeeded for product %s", product_id)
            except Exception:
                logger.exception("Rollback failed for product %s", product_id)
            # rollback in-memory
            try:
                self.transactions.remove(tx)
            except ValueError:
                logger.exception("Failed to remove transaction %s during rollback", tx.transaction_id)
            raise

        return tx

    def list_transactions(self) -> List[Transaction]:
        """Return a shallow copy of transactions list."""
        return list(self.transactions)

    def _normalize_bound_date(self, d: Optional[Any]) -> Optional[datetime]:
        """
        Normalize a bound (date_from/date_to) into timezone-aware datetime (UTC).
        Accepts datetime objects or ISO strings. Naive datetimes are assumed UTC.
        """
        if d is None:
            return None
        if isinstance(d, datetime):
            if d.tzinfo is None:
                return d.replace(tzinfo=timezone.utc)
            return d
        # parse ISO-like strings using shared validator
        parsed = parse_iso_datetime(d)
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    def filter_transactions(self,
                            product_id: Optional[str] = None,
                            trans_type: Optional[str] = None,
                            date_from: Optional[Any] = None,
                            date_to: Optional[Any] = None) -> List[Transaction]:
        """
        Filter transactions by optional product_id, trans_type, and date bounds.
        date_from/date_to can be datetime or ISO string. Naive datetimes/string results are treated as UTC.
        """
        date_from_n = self._normalize_bound_date(date_from)
        date_to_n = self._normalize_bound_date(date_to)

        result: List[Transaction] = []
        for t in self.transactions:
            if product_id and t.product_id != product_id:
                continue
            if trans_type and t.trans_type.upper() != trans_type.upper():
                continue
            if date_from_n and t.date < date_from_n:
                continue
            if date_to_n and t.date > date_to_n:
                continue
            result.append(t)
        return result

    def export_transactions(self, out_path: Union[str, Path]) -> None:
        """
        Export transactions to CSV or JSON depending on out_path suffix.
        """
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        rows = [t.to_dict() for t in self.transactions]
        if out.suffix.lower() == ".json":
            _atomic_write(out, json.dumps(rows, ensure_ascii=False, indent=2))
            return
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=self.DEFAULT_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        _atomic_write(out, buf.getvalue())

    def generate_stock_report(self) -> List[Dict[str, Any]]:
        """Return a simple stock report for all products."""
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
    def log_transaction(self, transaction: Transaction) -> None:
        """Ghi log chi tiết giao dịch vào file transaction_log.txt."""
        log_file = self.storage_file.parent / "transaction_log.txt"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_line = f"{datetime.now(timezone.utc).isoformat()} | {transaction.transaction_id} | {transaction.product_id} | {transaction.trans_type} | {transaction.quantity} | {transaction.date.isoformat()} | {transaction.note}\n"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            logger.exception("Không thể ghi log giao dịch: %s", transaction.transaction_id)

    def search_transactions(self, keyword: str) -> List[Transaction]:
        """Tìm kiếm giao dịch theo keyword (mã SP hoặc ghi chú)."""
        keyword_norm = keyword.strip().lower()
        return [
            t for t in self.transactions
            if keyword_norm in t.product_id.lower() or keyword_norm in t.note.lower()
        ]
    def export_transactions_filtered(self, out_path: Union[str, Path],
                                     product_id: Optional[str] = None,
                                     trans_type: Optional[str] = None,
                                     date_from: Optional[Any] = None,
                                     date_to: Optional[Any] = None) -> None:
        """Xuất transactions theo filter vào CSV/JSON."""
        filtered = self.filter_transactions(product_id, trans_type, date_from, date_to)
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        rows = [t.to_dict() for t in filtered]
        if out.suffix.lower() == ".json":
            _atomic_write(out, json.dumps(rows, ensure_ascii=False, indent=2))
            return
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=self.DEFAULT_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        _atomic_write(out, buf.getvalue())
    def get_stock(self, product_id: str) -> Optional[int]:
        """Lấy số lượng tồn kho của một sản phẩm."""
        try:
            product = self.product_mgr.get_product(product_id)
            return product.stock_quantity
        except Exception:
            logger.warning("Không tìm thấy sản phẩm %s để lấy tồn kho", product_id)
            return None

    def get_all_stock(self) -> Dict[str, int]:
        """Trả về dict {product_id: tồn kho}."""
        return {p.product_id: p.stock_quantity for p in self.product_mgr.list_products()}
