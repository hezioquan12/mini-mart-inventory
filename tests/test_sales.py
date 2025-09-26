import pytest


def test_add_product(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP006", "Mì tôm", "Thực phẩm", 2000, 5000, 50, 10, "gói")
    assert pm.get_product("SP006") is not None


def test_update_product(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP007", "Sữa tươi", "Đồ uống", 12000, 20000, 30, 5, "chai")
    pm.update_product("SP007", sell_price=21000)
    assert pm.get_product("SP007").sell_price == 21000


def test_delete_product(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP008", "Kem đánh răng", "Mỹ phẩm", 15000, 25000, 10, 2, "tuýp")
    pm.delete_product("SP008")
    with pytest.raises(ValueError):
        pm.get_product("SP008")


def test_search_product(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP009", "Nước ngọt", "Đồ uống", 7000, 12000, 15, 3, "chai")
    results = pm.search_products("ngọt")
    assert any("Nước ngọt" in p.name for p in results)


def test_validators(temp_product_manager):
    pm = temp_product_manager
    with pytest.raises(ValueError):
        pm.add_product("SP010", " ", "Đồ uống", 5000, 8000, 10, 2, "chai")

