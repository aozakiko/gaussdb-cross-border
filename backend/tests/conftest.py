"""Pytest configuration to ensure local testing defaults."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# During pytest runs we force SQLAlchemy to use a local sqlite database so that tests
# do not require a running GaussDB cluster.
default_sqlite_url = f"sqlite:///{(BACKEND_DIR / 'tests' / 'test_records.db').resolve().as_posix()}"
os.environ.setdefault("DATABASE_URL", default_sqlite_url)
