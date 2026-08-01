from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv
from psycopg import Connection
from psycopg.rows import dict_row

from .exceptions import DatabaseConnectionError

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def get_database_url(explicit_url: str | None = None) -> str:
    url = explicit_url or DATABASE_URL
    if not url:
        raise DatabaseConnectionError(
            "DATABASE_URL is missing. Add it to the project's .env file."
        )
    return url


@contextmanager
def get_connection(database_url: str | None = None) -> Iterator[Connection]:
    """Open a dict-row connection and own its transaction and lifecycle."""
    try:
        connection = psycopg.connect(
            get_database_url(database_url),
            row_factory=dict_row,
            connect_timeout=10,
        )
    except (psycopg.Error, ValueError) as error:
        raise DatabaseConnectionError("Unable to connect to PostgreSQL.") from error

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
