import pytest

import repositories.database as database
from repositories.exceptions import DatabaseConnectionError
from repositories.project_repository import ProjectRepository


def test_missing_database_url_has_clear_error(monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_URL", None)
    with pytest.raises(DatabaseConnectionError, match="DATABASE_URL is missing"):
        database.get_database_url()


def test_invalid_database_url_is_wrapped() -> None:
    repository = ProjectRepository("not-a-postgresql-url")
    with pytest.raises(DatabaseConnectionError, match="Unable to connect"):
        repository.list_projects()
