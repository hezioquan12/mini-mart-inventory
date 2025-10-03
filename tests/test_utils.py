import tempfile
from src.utils.io_utils import atomic_write_text


def test_atomic_write_text():
    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        path = tmp.name
    atomic_write_text(path, "Hello World")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert content == "Hello World"
