# io_utils.py
from pathlib import Path
import tempfile
import os
from typing import Union

def atomic_write_text(path: Union[str, Path], text: str, encoding: str = "utf-8"):
    """
    Write text to `path` atomically: write to a temp file in same dir then replace.
    Ensures file is never left half-written by a crashed process.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent))
    try:
        # Use os.fdopen to ensure atomic write to temp
        with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
            f.write(text)
        os.replace(tmp, str(p))
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass
        raise
