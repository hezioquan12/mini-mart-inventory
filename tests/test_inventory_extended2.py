import pytest
import json
from pathlib import Path
# ==============================
# Product Module
# ==============================

def test_add_product_invalid_price(temp_product_manager):
    pm = temp_product_manager
    with pytest.raises(ValueError):
        pm.add_product("SP100", "Táo", "Thực phẩm", -1000, 2000, 10, 1, "kg")


def test_update_product_invalid_data(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP101", "Cam", "Thực phẩm", 1000, 2000, 10, 1, "kg")
    with pytest.raises(ValueError):
        pm.update_product("SP101", gia_nhap=-500)


def test_delete_multiple_products(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP102", "Xoài", "Thực phẩm", 1000, 2000, 5, 1, "kg")
    pm.add_product("SP103", "Ổi", "Thực phẩm", 2000, 4000, 5, 1, "kg")
    pm.delete_product("SP102")
    pm.delete_product("SP103")
    assert not pm.search_products("Xoài")
    assert not pm.search_products("Ổi")


def test_search_product_partial_match(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP104", "Nước cam ép", "Thực phẩm", 5000, 10000, 5, 1, "chai")
    results = pm.search_products("cam")
    assert any("Nước cam" in p.name for p in results)


# ==============================
# Category Module
# ==============================

def test_add_category_special_characters(temp_category_manager):
    cm = temp_category_manager
    cm.add_category("Đồ uống @2025")
    assert "Đồ uống @2025" in cm.get_all_names()

def test_get_all_names_returns_copy(temp_category_manager):
    cm = temp_category_manager
    names1 = cm.get_all_names()
    names1.append("Fake")
    assert "Fake" not in cm.get_all_names()


# ==============================
# Sales Module
# ==============================

def test_sales_multiple_insufficient_stock(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP106", "Kẹo", "Thực phẩm", 500, 1000, 2, 1, "gói")
    pm.apply_stock_change("SP106", -1)
    pm.apply_stock_change("SP106", -1)
    with pytest.raises(ValueError):
        pm.apply_stock_change("SP106", -1)


# ==============================
# I/O & Utility
# ==============================

def test_load_invalid_json_format(tmp_path, temp_category_manager):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json}", encoding="utf-8")
    cm = temp_category_manager.__class__(bad_file)
    # Trường hợp này: file hỏng → categories reset thành rỗng/list mặc định
    assert isinstance(cm.get_all_names(), list)


def test_save_creates_file(tmp_path, temp_category_manager):
    file_path = tmp_path / "cats.json"
    cm = temp_category_manager.__class__(file_path)
    cm.add_category("Đặc sản")
    cm.save()
    assert file_path.exists()
    data = json.loads(file_path.read_text(encoding="utf-8"))
    assert "Đặc sản" in data
