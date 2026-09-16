"""Explicit operator command for adding Learning Center seed data."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studio.db import connect, init_db
from studio.data.learning_seed import seed_learning_center


if __name__ == "__main__":
    init_db()
    print(seed_learning_center(connect()))
