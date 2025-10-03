from src.utils.time_zone import VN_TZ

def summary_for_month(pm, tm, year: int, month: int):
    """Tính toán báo cáo doanh thu theo tháng."""
    txs = [t for t in tm.list_transactions() if t.trans_type == "EXPORT"]

    def in_month(t):
        dt = getattr(t, "date", None)
        if not dt:
            return False
        try:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=VN_TZ)
            local = dt.astimezone(VN_TZ)
        except Exception:
            local = dt
        return local.year == year and local.month == month

    txs_m = [t for t in txs if in_month(t)]
    rev, cost = 0, 0
    per_prod = {}
    for t in txs_m:
        try:
            p = pm.get_product(t.product_id)
        except Exception:
            continue
        rev += int(p.sell_price) * t.quantity
        cost += int(p.cost_price) * t.quantity
        pr = per_prod.setdefault(p.product_id, {"name": p.name, "qty": 0})
        pr["qty"] += t.quantity

    return {
        "transactions": txs_m,
        "revenue": rev,
        "cost": cost,
        "profit": rev - cost,
        "per_prod": per_prod,
    }
