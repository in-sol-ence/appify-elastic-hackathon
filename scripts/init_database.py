#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from repositories.database import get_connection  # noqa: E402


def main() -> int:
    migrations = sorted((ROOT / "db" / "migrations").glob("*.sql"))
    try:
        with get_connection() as connection:
            for migration in migrations:
                connection.execute(migration.read_text(encoding="utf-8"))
        print(f"PostgreSQL initialized successfully ({len(migrations)} migration files applied).")
        return 0
    except Exception as error:
        # Error text is intentionally concise; never print DATABASE_URL.
        print(f"Database initialization failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
