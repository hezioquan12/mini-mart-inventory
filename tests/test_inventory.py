import pytest


def test_add_product(temp_product_manager):
    pm = temp_product_manager
    pm.add_product(
        product_id="SP001",
        name="Bánh mì sandwich",
        category="Thực phẩm",
        cost_price=15000,
        sell_price=25000,
        stock_quantity=45,
        min_threshold=5,
        unit="cái"
    )
    assert len(pm.products) == 1

def test_update_product(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP002", "Coca Cola", "Đồ uống", 8000, 12000, 5, 2, "chai")
    pm.update_product("SP002", name="Coca Cola 330ml", sell_price=13000)
    updated = pm.get_product("SP002")
    assert updated.name == "Coca Cola 330ml"
    assert updated.sell_price == 13000


def test_delete_product(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP003", "Dầu gội", "Mỹ phẩm", 80000, 120000, 0, 3, "chai")
    pm.delete_product("SP003")
    with pytest.raises(ValueError):
        pm.get_product("SP003")


def test_search_product(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP004", "Nước suối", "Đồ uống", 5000, 10000, 20, 5, "chai")
    results = pm.search_products("nước")
    assert any("Nước suối" in p.name for p in results)


def test_validators(temp_product_manager):
    pm = temp_product_manager
    with pytest.raises(ValueError):
        pm.add_product("SP005", "", "Thực phẩm", 5000, 8000, 10, 2, "gói")

