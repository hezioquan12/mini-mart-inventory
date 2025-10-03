import io
import sys
from contextlib import redirect_stdout
from src.main.cli import main  # giả sử hàm main() là entrypoint CLI của bạn


def run_cli_with_inputs(monkeypatch, inputs):
    """
    Giả lập nhập dữ liệu cho CLI và trả về toàn bộ output in ra.
    :param monkeypatch: fixture pytest
    :param inputs: danh sách các chuỗi nhập
    """
    input_iter = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda _: next(input_iter))

    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            main()
        except SystemExit:
            # CLI có thể gọi sys.exit -> mình catch để không làm vỡ test
            pass
    return buf.getvalue()
