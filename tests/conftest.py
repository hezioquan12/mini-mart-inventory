import pytest
import tempfile
import json
from pathlib import Path

from src.inventory.product_manager import ProductManager
from src.inventory.category_manager import CategoryManager

@pytest.fixture
def temp_product_manager(temp_category_manager):
    return ProductManager(category_mgr=temp_category_manager)
@pytest.fixture
def temp_category_manager():
    return CategoryManager()
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

    # Truyền storage_path đúng vào constructor
    category_mgr = CategoryManager(storage_path=str(categories_file))

    return ProductManager(storage_file=str(products_file), category_mgr=category_mgr)
