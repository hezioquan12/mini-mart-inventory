import pytest
import tempfile
import json
from pathlib import Path

from src.inventory.product_manager import ProductManager
from src.inventory.category_manager import CategoryManager
from src.utils.io_utils import atomic_write_text


# ---------- Fixture tạo ProductManager tạm thời với file JSON ----------
@pytest.fixture
def temp_product_manager():
    tmp_dir = tempfile.mkdtemp()

    # Tạo file products.json trống
    products_file = Path(tmp_dir) / "products.json"
    products_file.write_text("[]", encoding="utf-8")

    # Tạo file categories.json mẫu
    categories_file = Path(tmp_dir) / "categories.json"
    categories = [
        {"id": "C01", "name": "Thực phẩm"},
        {"id": "C02", "name": "Đồ uống"},
        {"id": "C03", "name": "Gia dụng"},
        {"id": "C04", "name": "Mỹ phẩm"},
        {"id": "C05", "name": "Điện tử"}
    ]
    categories_file.write_text(json.dumps(categories, ensure_ascii=False, indent=2), encoding="utf-8")

    # Khởi tạo CategoryManager và ProductManager
    category_mgr = CategoryManager(storage_path=str(categories_file))
    category_mgr._rebuild_normalized_cache()  # đảm bảo cache được build

    return ProductManager(storage_file=str(products_file), category_mgr=category_mgr)


# ===================== Product Module =====================
def test_add_product(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP001", "Bánh mì", "Thực phẩm", 1000, 1200, 10, 2, "cái")
    products = pm.get_all_products()
    assert any(p.id == "SP001" for p in products)


def test_update_product(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP002", "Sữa tươi", "Đồ uống", 2000, 2500, 5, 2, "chai")
    pm.update_product("SP002", price_sale=2600)
    updated = next(p for p in pm.get_all_products() if p.id == "SP002")
    assert updated.price_sale == 2600


def test_delete_product(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP003", "Dầu gội", "Mỹ phẩm", 80000, 120000, 0, 3, "chai")
    pm.delete_product("SP003")
    assert not any(p.id == "SP003" for p in pm.get_all_products())


def test_search_product(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP004", "Nước ngọt", "Đồ uống", 5000, 8000, 20, 1, "chai")
    results = pm.search_products("ngọt")
    assert any("ngọt" in p.name for p in results)


# ===================== Category Module =====================
def test_add_category_duplicate_name(temp_product_manager):
    pm = temp_product_manager
    with pytest.raises(ValueError):
        pm.category_mgr.add_category("Thực phẩm")


def test_add_category_special_characters(temp_product_manager):
    pm = temp_product_manager
    pm.category_mgr.add_category("Đồ_ăn@123")
    assert pm.category_mgr.is_valid_name("Đồ_ăn@123")


def test_remove_category_with_products(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP005", "Bánh kẹo", "Thực phẩm", 1000, 1200, 10, 2, "cái")
    with pytest.raises(Exception):
        pm.category_mgr.remove_category("Thực phẩm")  # có sản phẩm -> fail


def test_rename_category_to_existing_name(temp_product_manager):
    pm = temp_product_manager
    with pytest.raises(ValueError):
        pm.category_mgr.rename_category("Đồ uống", "Thực phẩm")


def test_get_all_names_returns_copy(temp_product_manager):
    pm = temp_product_manager
    names = pm.category_mgr.get_all_names()
    names.append("FakeCategory")
    assert "FakeCategory" not in pm.category_mgr.get_all_names()


# ===================== Validation =====================
def test_validate_category_empty_string(temp_product_manager):
    pm = temp_product_manager
    with pytest.raises(ValueError):
        pm.category_mgr.add_category("")


def test_validate_category_none(temp_product_manager):
    pm = temp_product_manager
    with pytest.raises(ValueError):
        pm.category_mgr.add_category(None)


def test_validate_product_id_format(temp_product_manager):
    pm = temp_product_manager
    with pytest.raises(ValueError):
        pm.add_product("001", "Bánh", "Thực phẩm", 1000, 1200, 5, 1, "cái")


def test_validate_product_quantity_negative(temp_product_manager):
    pm = temp_product_manager
    with pytest.raises(ValueError):
        pm.add_product("SP006", "Bánh", "Thực phẩm", 1000, 1200, -5, 1, "cái")


def test_validate_product_unit_empty(temp_product_manager):
    pm = temp_product_manager
    with pytest.raises(ValueError):
        pm.add_product("SP007", "Bánh", "Thực phẩm", 1000, 1200, 5, 1, "")


# ===================== Sales Module =====================
def test_sales_add_product_insufficient_stock(temp_product_manager):
    pm = temp_product_manager
    pm.add_product("SP022", "Test", "Thực phẩm", 1000, 2000, 0, 1, "cái")
    with pytest.raises(ValueError):
        pm.sell_product("SP022", 1)


def test_sales_delete_nonexistent_product(temp_product_manager):
    pm = temp_product_manager
    with pytest.raises(ValueError):
        pm.delete_product("NONEXIST")


def test_sales_validation_category(temp_product_manager):
    pm = temp_product_manager
    with pytest.raises(ValueError):
        pm.add_product("SP008", "Test", "Không tồn tại", 1000, 2000, 5, 1, "cái")


# ===================== I/O & Utility =====================
def test_atomic_write_text_permission_error(tmp_path):
    file_path = tmp_path / "categories.json"
    file_path.write_text("[]")
    file_path.chmod(0o000)  # remove read/write permission
    with pytest.raises(PermissionError):
        atomic_write_text(file_path, "test")

