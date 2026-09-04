"""Where the board keeps its own state: outside every project's working tree.

0.1 kept its store inside the project repository and lost it twice to a reset
of that tree. Needle's store lives under the XDG data directory, and `NEEDLE_DB`
points it elsewhere for a test or a second board.
"""

import os
from pathlib import Path


def data_dir() -> Path:
    override = os.environ.get("NEEDLE_DATA_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "needle"


def db_path() -> Path:
    override = os.environ.get("NEEDLE_DB")
    if override:
        return Path(override)
    return data_dir() / "needle.db"
