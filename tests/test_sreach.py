import pytest
from datetime import datetime, timedelta
from src.utils.time_zone import VN_TZ

from src.inventory.product_manager import ProductManager
from src.sales.transaction_manager import TransactionManager
from src.report_and_sreach.sreach import SearchEngine
from src.inventory.category_manager import CategoryManager


@pytest.fixture
def setup_env(tmp_path):
    """Tạo ProductManager + TransactionManager + SearchEngine với dữ liệu mẫu."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Category setup
    cm = CategoryManager(data_dir / "categories.json")
    cm.add_category("Đồ uống")

    pm = ProductManager(data_dir / "products.csv", category_mgr=cm)
    tm = TransactionManager(data_dir / "transactions.csv", pm)
    se = SearchEngine(pm, tm)

    # Add sample products
    pm.add_product("SP01", "Sữa Vinamilk", "Đồ uống", 10000, 15000, 50, 20, "hộp")
    pm.add_product("SP02", "Coca Cola", "Đồ uống", 8000, 12000, 100, 30, "lon")
    pm.add_product("SP03", "Pepsi", "Đồ uống", 7500, 11000, 10, 30, "lon")

    # Add some transactions
    now = datetime.now(VN_TZ)
    tm.add_transaction("SP01", "EXPORT", 5, note="Khách mua Vinamilk")
    tm.transactions[-1].date = now - timedelta(days=2)  # chỉnh ngày
    tm.add_transaction("SP02", "EXPORT", 20, note="Bán Coca")
    tm.transactions[-1].date = now - timedelta(days=1)

    return pm, tm, se


def test_search_exact_match(setup_env):
    _, _, se = setup_env
    res = se.search_products("Vinamilk")
    assert res["total"] == 1
    assert res["results"][0]["product_id"] == "SP01"


def test_search_fuzzy_match(setup_env):
    _, _, se = setup_env
    res = se.search_products("Vinalmilk")  # gõ sai
    assert res["total"] >= 1
    ids = [r["product_id"] for r in res["results"]]
    assert "SP01" in ids


def test_autocomplete_name(setup_env):
    _, _, se = setup_env
    suggestions = se.autocomplete_products("sư")
    assert any("Vinamilk" in s for s in suggestions), f"Got {suggestions}"


def test_facets_category(setup_env):
    _, _, se = setup_env
    res = se.search_products("Co")
    assert "Đồ uống" in res["facets"]


def test_search_transactions(setup_env):
    _, tm, se = setup_env
    results = se.search_transactions("Vinamilk")
    assert any("SP01" in r["product_id"] for r in results)


def test_stock_alerts(setup_env):
    _, _, se = setup_env
    alerts = se.get_stock_alerts()
    # SP03 chỉ có 10, min_threshold=30 → phải cảnh báo low_stock
    low_ids = [p["product_id"] for p in alerts["low_stock"]]
    assert "SP03" in low_ids
def test_suggest_order_quantity(setup_env):
    _, _, se = setup_env
    p = se.product_mgr.get_product("SP01")
    q = se._suggest_order_quantity(p, days=10, lead_time_days=3)
    assert isinstance(q, int)
    assert q >= 0
# ========================
# 🔎 TEST PRODUCT VERSION
# ========================

def test_version_increment_on_add(setup_env):
    pm, _, _ = setup_env
    v0 = pm.version
    pm.add_product("SP99", "Nước Cam", "Đồ uống", 5000, 8000, 20, 5, "chai")
    assert pm.version == v0 + 1


def test_version_increment_on_update(setup_env):
    pm, _, _ = setup_env
    pm.add_product("SP98", "Bia Hà Nội", "Đồ uống", 7000, 10000, 30, 10, "lon")
    v1 = pm.version
    pm.update_product("SP98", name="Bia Hà Nội Premium")
    assert pm.version == v1 + 1


def test_version_increment_on_delete(setup_env):
    pm, _, _ = setup_env
    pm.add_product("SP97", "Sting", "Đồ uống", 6000, 9000, 25, 8, "chai")
    v1 = pm.version
    pm.delete_product("SP97")
    assert pm.version == v1 + 1


def test_search_engine_rebuilds_on_version_change(setup_env):
    pm, _, se = setup_env

    # index ban đầu không có sản phẩm test
    results1 = se.search_products("Trà Xanh")
    assert results1["total"] == 0

    # thêm sản phẩm mới
    pm.add_product("SP96", "Trà Xanh Không Độ", "Đồ uống", 4000, 7000, 40, 15, "chai")

    # SearchEngine phải rebuild index nhờ version mới
    results2 = se.search_products("Trà Xanh")
    assert results2["total"] == 1

