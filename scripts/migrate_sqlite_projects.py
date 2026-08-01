#!/usr/bin/env python3
"""Optional one-time migration from the former SQLite JSON-row repository."""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.project import Project  # noqa: E402
from repositories.project_repository import ProjectRepository  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sqlite_file", nargs="?", default="data/robotics_bom_guardian.db")
    args = parser.parse_args()
    source = Path(args.sqlite_file)
    if not source.exists():
        print(f"SQLite source does not exist: {source}", file=sys.stderr)
        return 1

    repository = ProjectRepository()
    migrated = 0
    try:
        with sqlite3.connect(source) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("SELECT project_json, status FROM projects").fetchall()
        for row in rows:
            project = Project.model_validate_json(row["project_json"])
            legacy_status = str(row["status"]).lower()
            status = "draft" if legacy_status == "draft" else "active"
            if repository.project_exists(project.id):
                repository.update_project(project.id, project, status)
            else:
                repository.create_project(project, status)
            migrated += 1
        print(f"Migrated {migrated} project(s) from SQLite to PostgreSQL.")
        return 0
    except Exception as error:
        print(f"SQLite migration failed after {migrated} project(s): {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
