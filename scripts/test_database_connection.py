#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from repositories.database import get_connection  # noqa: E402


def main() -> int:
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    current_database() AS database_name,
                    current_user AS database_user,
                    version() AS postgres_version,
                    to_regclass('public.projects') IS NOT NULL AS projects_table_exists
                """
            ).fetchone()
        print(f"Connected database: {row['database_name']}")
        print(f"PostgreSQL user: {row['database_user']}")
        print(f"PostgreSQL version: {row['postgres_version']}")
        print(f"Projects table exists: {'yes' if row['projects_table_exists'] else 'no'}")
        return 0
    except Exception as error:
        print(f"PostgreSQL connection test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
