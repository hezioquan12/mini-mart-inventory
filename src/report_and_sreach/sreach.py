# src/utils/search.py
from __future__ import annotations

import unicodedata
import difflib
from datetime import datetime, timedelta
from collections import Counter
from typing import List, Dict, Any, Optional

try:
    from rapidfuzz import fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    fuzz = None
    _HAS_RAPIDFUZZ = False

from src.inventory.product_manager import ProductManager
from src.sales.transaction_manager import TransactionManager
from src.inventory.product import Product

import logging
logger = logging.getLogger(__name__)

# ------------------------
# Constants / Defaults
# ------------------------
DEFAULT_PER_PAGE = 20
DEFAULT_AUTOCOMPLETE_LIMIT = 8
DEFAULT_FUZZY_THRESHOLD = 70

# ==============================
# 🔧 Helper Functions
# ==============================
def _norm(s: Optional[str]) -> str:
    """Chuẩn hóa chuỗi: lower + strip, chịu None."""
    if not s:
        return ""
    return str(s).strip().lower()

def _remove_accents(s: Optional[str]) -> str:
    """Bỏ dấu tiếng Việt để hỗ trợ tìm kiếm không phân biệt dấu."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(s))
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()

def _stock_status_for_product(p: Product) -> str:
    """Trả về trạng thái tồn theo sản phẩm."""
    if p.stock_quantity > 0:
        if p.stock_quantity <= p.min_threshold:
            return "SẮP HẾT"
        return "BÌNH THƯỜNG"
    return "HẾT HÀNG"

# ==============================
# 🔎 SearchEngine
# ==============================

class SearchEngine:
    """
    SearchEngine 2.0:
      - Tìm sản phẩm (prefix, substring, fuzzy, không dấu, nhiều filter).
      - Autocomplete (index-based, có invalidation).
      - Cảnh báo tồn kho + gợi ý nhập hàng thông minh (reorder point).
      - Xếp hạng thông minh (prefix > substring > fuzzy + popularity boost).
      - Faceted search + pagination.
    """
    def __init__(self, product_mgr: ProductManager, trans_mgr: Optional[TransactionManager] = None) -> None:
        self.product_mgr = product_mgr
        self.trans_mgr = trans_mgr
        self._index = None
        self._index_version = None

    # ------------------------
    # INDEX MANAGEMENT
    # ------------------------
    def _ensure_index(self) -> None:
        """Xây dựng lại index nếu dữ liệu thay đổi."""
        version = getattr(self.product_mgr, "version", None)
        if self._index is None or self._index_version != version:
            self._build_index()
            self._index_version = version

    def _build_index(self) -> None:
        """Xây index đơn giản cho tìm kiếm non-inverted (in-memory)."""
        products = self.product_mgr.list_products()
        self._index = []
        for p in products:
            self._index.append({
                "product": p,
                "product_id_norm": _norm(p.product_id),
                "name_norm": _norm(p.name),
                "category_norm": _norm(p.category),
                "product_id_plain": _remove_accents(p.product_id),
                "name_plain": _remove_accents(p.name),
                "category_plain": _remove_accents(p.category),
            })

    # ------------------------
    # PRODUCT SEARCH
    # ------------------------
    def search_products(
        self,
        keyword: str,
        field: Optional[str] = None,
        category: Optional[str] = None,
        fuzzy: bool = True,
        page: int = 1,
        per_page: int = DEFAULT_PER_PAGE,
    ) -> Dict[str, Any]:
        """Tìm kiếm sản phẩm nâng cao."""
        if not keyword:
            return {"results": [], "total": 0, "facets": {}}

        self._ensure_index()

        kw_norm = _norm(keyword)
        kw_plain = _remove_accents(keyword)
        allowed = {"product_id", "name", "category"}
        if field and field not in allowed:
            raise ValueError(f"Field '{field}' không hợp lệ. Hỗ trợ: {allowed}")

        results = []
        for entry in self._index:
            p = entry["product"]

            if category and _norm(p.category) != _norm(category):
                continue

            fields_to_check = [field] if field else list(allowed)
            for f in fields_to_check:
                norm_val = entry.get(f + "_norm", "")
                plain_val = entry.get(f + "_plain", "")

                if norm_val.startswith(kw_norm) or plain_val.startswith(kw_plain):
                    score, match_type = 300, "prefix"
                elif kw_norm in norm_val or kw_plain in plain_val:
                    score, match_type = 200, "substring"
                elif fuzzy and self._fuzzy_match(kw_norm, norm_val, kw_plain, plain_val):
                    score, match_type = 100, "fuzzy"
                else:
                    continue

                # Popularity boost (sản phẩm bán chạy hơn → + điểm)
                popularity = self._get_product_popularity(p.product_id)
                score += min(50, popularity)

                results.append({
                    **p.to_dict(),
                    "matched_field": f,
                    "match_type": match_type,
                    "search_score": score,
                    "stock_status": _stock_status_for_product(p),
                })
                break

        results_sorted = sorted(results, key=lambda r: (-r["search_score"], r["product_id"]))

        # Faceted counts (theo category)
        facets = Counter(r["category"] for r in results_sorted)

        # Pagination
        total = len(results_sorted)
        start, end = (page - 1) * per_page, (page - 1) * per_page + per_page
        paginated = results_sorted[start:end]

        return {"results": paginated, "total": total, "facets": dict(facets)}

    @staticmethod
    def _fuzzy_match(kw_norm: str, val_norm: str, kw_plain: str, val_plain: str, threshold: int = DEFAULT_FUZZY_THRESHOLD) -> bool:
        """Wrapper cho fuzzy match: rapidfuzz nếu có, fallback sang difflib."""
        if _HAS_RAPIDFUZZ and fuzz is not None:
            try:
                return (
                        fuzz.partial_ratio(kw_norm, val_norm) >= threshold
                        or fuzz.partial_ratio(kw_plain, val_plain) >= threshold
                )
            except Exception:
                # Nếu rapidfuzz gặp lỗi lạ, fallback an toàn
                logger.exception("rapidfuzz error during fuzzy match; falling back to difflib.")
                return difflib.SequenceMatcher(None, kw_norm, val_norm).ratio() >= threshold / 100
        return difflib.SequenceMatcher(None, kw_norm, val_norm).ratio() >= threshold / 100

    def _get_product_popularity(self, product_id: str) -> int:
        """Độ phổ biến sản phẩm dựa trên số lần bán (EXPORT)."""
        if not self.trans_mgr:
            return 0
        return sum(1 for t in self.trans_mgr.list_transactions() if t.product_id == product_id and t.trans_type == "EXPORT")

    # ------------------------
    # AUTOCOMPLETE
    # ------------------------
    def autocomplete_products(self, prefix: str, field: str = "name", limit: int = DEFAULT_AUTOCOMPLETE_LIMIT) -> List[str]:
        """Autocomplete dựa trên index."""
        if not prefix:
            return []

        self._ensure_index()
        allowed = {"product_id", "name", "category"}
        if field not in allowed:
            raise ValueError(f"Field '{field}' không hợp lệ.")

        pref_norm = _remove_accents(prefix)
        seen, suggestions = set(), []

        for entry in self._index:
            val = getattr(entry["product"], field, "")
            if not val:
                continue
            if _remove_accents(val).startswith(pref_norm):
                if val not in seen:
                    seen.add(val)
                    suggestions.append(val)
                if len(suggestions) >= limit:
                    break
        return suggestions

    # ------------------------
    # TRANSACTION SEARCH
    # ------------------------
    def search_transactions(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Tìm kiếm nhanh trong transaction (theo mã SP/ghi chú)."""
        if not self.trans_mgr:
            raise RuntimeError("TransactionManager chưa được gắn.")
        return [t.to_dict() for t in self.trans_mgr.search_transactions(keyword)[:limit]]

    # ------------------------
    # STOCK ALERTS & SMART ORDER
    # ------------------------
    def get_stock_alerts(self, suggest_order: bool = True) -> Dict[str, Any]:
        """Sinh alerts tồn kho và gợi ý đơn hàng nếu cần."""
        self._ensure_index()
        products = [entry["product"] for entry in self._index]
        alerts = {"out_of_stock": [], "low_stock": [], "total_to_order": 0}

        for p in products:
            need = max(0, p.min_threshold - p.stock_quantity)
            pdata = p.to_dict()
            pdata.update({
                "stock_status": _stock_status_for_product(p),
                "need_to_order": need,
            })

            if p.stock_quantity <= 0:
                alerts["out_of_stock"].append(pdata)
            elif p.stock_quantity <= p.min_threshold:
                alerts["low_stock"].append(pdata)

            alerts["total_to_order"] += need

            if suggest_order and self.trans_mgr:
                pdata["suggested_order"] = self._suggest_order_quantity(p)

        return alerts

    def _suggest_order_quantity(self, p: Product, days: int = 30, lead_time_days: int = 7) -> int:
        """
        Gợi ý số lượng đặt hàng dựa trên doanh số thực tế trong `days`.
        Luôn trả về >= 0.
        """
        if not self.trans_mgr:
            return max(0, p.min_threshold - p.stock_quantity)

        now = datetime.now()
        cutoff = now - timedelta(days=days)
        txs = [
            t for t in self.trans_mgr.list_transactions()
            if t.product_id == p.product_id and t.trans_type == "EXPORT"
            and getattr(t, "date", None) and t.date >= cutoff
        ]
        if not txs:
            return max(0, p.min_threshold - p.stock_quantity)

        total_sold = sum(t.quantity for t in txs)
        actual_days = max(1, (now - min(t.date for t in txs)).days)
        avg_per_day = total_sold / actual_days

        safety = max(1, int(0.2 * avg_per_day * lead_time_days))
        reorder_point = int(avg_per_day * lead_time_days + safety)
        suggested = reorder_point - p.stock_quantity
        return max(0, suggested)