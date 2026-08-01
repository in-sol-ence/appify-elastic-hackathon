from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from models.persistence import ProjectSummary
from models.project import Project
from .database import get_connection
from .exceptions import DatabaseConnectionError, ProjectNotFoundError, RepositoryError

VALID_STATUSES = {"draft", "active", "archived"}


class ProjectRepository:
    """PostgreSQL JSONB repository for complete Project aggregates."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url

    @staticmethod
    def _status(status: str) -> str:
        normalized = status.lower()
        if normalized not in VALID_STATUSES:
            raise RepositoryError(f"Invalid project status: {status}")
        return normalized

    @staticmethod
    def _uuid(project_id: str) -> UUID:
        try:
            return UUID(str(project_id))
        except (TypeError, ValueError) as error:
            raise RepositoryError("Project ID is not a valid UUID.") from error

    @staticmethod
    def _validated(project: Project) -> Project:
        try:
            validated = Project.model_validate(project.model_dump(mode="python"))
        except Exception as error:
            raise RepositoryError("Project data failed model validation.") from error
        if not validated.id:
            validated.id = str(uuid4())
        validated.updated_at = datetime.now(timezone.utc)
        return validated

    @staticmethod
    def _raise_query_error(error: psycopg.Error, action: str) -> None:
        if isinstance(error, psycopg.errors.UndefinedTable):
            raise RepositoryError(
                "Database table has not been initialized. Run python scripts/init_database.py."
            ) from error
        raise RepositoryError(f"Project could not be {action}.") from error

    def create_project(self, project: Project, status: str = "draft") -> str:
        validated = self._validated(project)
        normalized_status = self._status(status)
        project_id = self._uuid(validated.id)
        document = validated.model_dump(mode="json")
        try:
            with get_connection(self.database_url) as connection:
                connection.execute(
                    """
                    INSERT INTO projects (id, name, status, project_data)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (project_id, validated.name, normalized_status, Jsonb(document)),
                )
        except DatabaseConnectionError:
            raise
        except psycopg.errors.UniqueViolation as error:
            raise RepositoryError(
                f"A project with ID {validated.id} already exists."
            ) from error
        except psycopg.Error as error:
            self._raise_query_error(error, "created")
        project.updated_at = validated.updated_at
        return validated.id

    def update_project(
        self,
        project_id: str,
        project: Project,
        status: str | None = None,
    ) -> None:
        validated = self._validated(project)
        normalized_status = self._status(status) if status is not None else None
        try:
            with get_connection(self.database_url) as connection:
                cursor = connection.execute(
                    """
                    UPDATE projects
                    SET
                        name = %s,
                        project_data = %s,
                        status = COALESCE(%s, status),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        validated.name,
                        Jsonb(validated.model_dump(mode="json")),
                        normalized_status,
                        self._uuid(project_id),
                    ),
                )
                if cursor.rowcount == 0:
                    raise ProjectNotFoundError(
                        "Selected project no longer exists."
                    )
        except (DatabaseConnectionError, ProjectNotFoundError):
            raise
        except psycopg.Error as error:
            self._raise_query_error(error, "updated")
        project.updated_at = validated.updated_at

    def get_project(self, project_id: str) -> Project | None:
        try:
            with get_connection(self.database_url) as connection:
                row = connection.execute(
                    "SELECT project_data FROM projects WHERE id = %s",
                    (self._uuid(project_id),),
                ).fetchone()
        except DatabaseConnectionError:
            raise
        except psycopg.Error as error:
            self._raise_query_error(error, "loaded")
        if row is None:
            return None
        try:
            return Project.model_validate(row["project_data"])
        except Exception as error:
            raise RepositoryError(
                "Stored project data is invalid and could not be loaded."
            ) from error

    def get_project_summary(self, project_id: str) -> ProjectSummary | None:
        try:
            with get_connection(self.database_url) as connection:
                row = connection.execute(
                    "SELECT id, name, status, created_at, updated_at FROM projects WHERE id = %s",
                    (self._uuid(project_id),),
                ).fetchone()
        except DatabaseConnectionError:
            raise
        except psycopg.Error as error:
            self._raise_query_error(error, "loaded")
        if row is None:
            return None
        return ProjectSummary(project_id=str(row["id"]), project_name=row["name"], status=row["status"], created_at=row["created_at"], updated_at=row["updated_at"])

    def list_projects(self, status: str | None = None) -> list[ProjectSummary]:
        normalized_status = self._status(status) if status is not None else None
        sql = """
            SELECT id, name, status, created_at, updated_at
            FROM projects
        """
        parameters: tuple[str, ...] = ()
        if normalized_status is not None:
            sql += " WHERE status = %s"
            parameters = (normalized_status,)
        sql += " ORDER BY updated_at DESC"
        try:
            with get_connection(self.database_url) as connection:
                rows = connection.execute(sql, parameters).fetchall()
        except DatabaseConnectionError:
            raise
        except psycopg.Error as error:
            self._raise_query_error(error, "listed")
        return [
            ProjectSummary(
                project_id=str(row["id"]),
                project_name=row["name"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def set_project_status(self, project_id: str, status: str) -> None:
        normalized = self._status(status)
        try:
            with get_connection(self.database_url) as connection:
                cursor = connection.execute(
                    "UPDATE projects SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (normalized, self._uuid(project_id)),
                )
                if cursor.rowcount == 0:
                    raise ProjectNotFoundError("Selected project no longer exists.")
        except (DatabaseConnectionError, ProjectNotFoundError):
            raise
        except psycopg.Error as error:
            self._raise_query_error(error, "updated")

    def delete_project(self, project_id: str) -> bool:
        try:
            with get_connection(self.database_url) as connection:
                cursor = connection.execute(
                    "DELETE FROM projects WHERE id = %s",
                    (self._uuid(project_id),),
                )
                return cursor.rowcount > 0
        except DatabaseConnectionError:
            raise
        except psycopg.Error as error:
            self._raise_query_error(error, "deleted")

    def project_exists(self, project_id: str) -> bool:
        try:
            with get_connection(self.database_url) as connection:
                row = connection.execute(
                    "SELECT EXISTS(SELECT 1 FROM projects WHERE id = %s) AS exists",
                    (self._uuid(project_id),),
                ).fetchone()
        except DatabaseConnectionError:
            raise
        except psycopg.Error as error:
            self._raise_query_error(error, "checked")
        return bool(row["exists"])

    # Compatibility aliases for callers migrating from the SQLite repository.
    def create(self, project: Project, status: str = "draft") -> str:
        return self.create_project(project, status)

    def update(self, project: Project, status: str = "draft") -> str:
        if self.project_exists(project.id):
            self.update_project(project.id, project, status)
            return project.id
        return self.create_project(project, status)

    def load(self, project_id: str) -> Project | None:
        return self.get_project(project_id)

    def delete(self, project_id: str) -> bool:
        return self.delete_project(project_id)
