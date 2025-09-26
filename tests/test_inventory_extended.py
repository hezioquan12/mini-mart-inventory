import pytest
from src.inventory.product import Product


def test_add_product_duplicate_id(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP001", "Bánh mì", "Thực phẩm", 15000, 25000, 10, 5, "cái")
    with pytest.raises(ValueError):
        pm.add_product("SP001", "Bánh mì khác", "Thực phẩm", 15000, 25000, 10, 5, "cái")


def test_add_product_invalid_category(temp_product_manager):
    pm = temp_product_manager
    with pytest.raises(ValueError):
        pm.add_product("SP010", "Sản phẩm lạ", "Category không tồn tại", 10000, 20000, 5, 1, "cái")


def test_add_product_edge_values(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP011", "Sản phẩm biên", "Thực phẩm", 0, 0, 0, 0, "cái")
    p = pm.get_product("SP011")
    assert p.cost_price == 0
    assert p.sell_price == 0
    assert p.stock_quantity == 0
    assert p.min_threshold == 0


def test_category_normalize_case(tmp_path):
    from src.inventory.category_manager import CategoryManager
    cat_mgr = CategoryManager(storage_path=tmp_path / "categories.json")
    cat_mgr._names = ["Thực phẩm"]
    cat_mgr._rebuild_normalized_cache()

    assert cat_mgr.is_valid_name("thực phẩm")
    assert cat_mgr.is_valid_name("THỰC PHẨM")
    assert cat_mgr.is_valid_name("Thực phẩm")


def test_delete_nonexistent_product(temp_product_manager):
    pm = temp_product_manager
    with pytest.raises(ValueError):
        pm.delete_product("SP999")


def test_search_products_case_insensitive(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP012", "Nước suối", "Đồ uống", 5000, 10000, 20, 5, "chai")
    results = pm.search_products("nƯỚc")
    assert len(results) > 0
    assert any("Nước" in p.name for p in results)


def test_rename_category_collision(tmp_path):
    from src.inventory.category_manager import CategoryManager
    cat_mgr = CategoryManager(storage_path=tmp_path / "categories.json")
    cat_mgr._names = ["Thực phẩm", "Đồ uống"]
    cat_mgr._rebuild_normalized_cache()
    cat_mgr.save()

    with pytest.raises(ValueError):
        cat_mgr.rename_category("Thực phẩm", "Đồ uống")


def test_add_category_empty_name(tmp_path):
    from src.inventory.category_manager import CategoryManager
    cat_mgr = CategoryManager(storage_path=tmp_path / "categories.json")
    with pytest.raises(ValueError):
        cat_mgr.add_category("")


def test_io_error_on_save(monkeypatch, tmp_path):
    from src.inventory.category_manager import CategoryManager
    cat_mgr = CategoryManager(storage_path=tmp_path / "categories.json")
    cat_mgr._names = ["Thực phẩm"]
    cat_mgr._rebuild_normalized_cache()
    cat_mgr.save()

    def fail_write(*args, **kwargs):
        raise IOError("Simulated IO Error")

    monkeypatch.setattr(cat_mgr, "save", fail_write)
    with pytest.raises(IOError):
        cat_mgr.add_category("Đồ chơi")
