# src/utils/io_utils.py
from pathlib import Path
import tempfile
import os
from typing import Union

PathLike = Union[str, Path]


def atomic_write_text(path: PathLike, text: str, encoding: str = "utf-8") -> None:
    """
    Atomically write `text` to `path`.

    Behavior:
      - Creates parent directories if needed.
      - Writes to a temporary file in the same directory, fsyncs the file,
        then atomically replaces the target with `os.replace`.
      - Ensures temporary file is removed on failure.

    Args:
        path: destination path (str or Path).
        text: content to write.
        encoding: text encoding (default "utf-8").

    Raises:
        OSError (or subclass): Propagates I/O related errors.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    # create temp file in same directory to ensure os.replace is atomic on same filesystem
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp", dir=str(p.parent))
    try:
        # write via fdopen to ensure we control the file descriptor
        with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
            f.write(text)
            f.flush()
            # ensure data is persisted to disk before rename
            try:
                os.fsync(f.fileno())
            except (AttributeError, OSError):
                # on some platforms fsync may not be available or may fail; ignore but continue
                pass

        # atomic replace (overwrite if exists)
        os.replace(tmp_path, str(p))
    except OSError:
        # cleanup temp file on failure; ignore cleanup errors
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        # re-raise original exception to let caller handle/report it
        raise
