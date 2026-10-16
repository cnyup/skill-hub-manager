"""Filesystem helpers shared by state-writing modules.

atomic_write_text guarantees readers never observe a partially written file:
content lands in a sibling tmp file first, then becomes visible via a single
os.replace (atomic on POSIX). A crash anywhere before the replace leaves the
original untouched.
"""

import os
from pathlib import Path


def atomic_write_text(path: Path, content: str) -> Path:
    """Atomically write text content to *path*.

    - Creates parent directories as needed.
    - Writes to a uniquely named tmp sibling, then os.replace()s into place.
    - On any failure the tmp file is removed and the original is untouched.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    try:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, path)
    except BaseException:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return path
