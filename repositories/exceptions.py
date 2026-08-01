class RepositoryError(Exception):
    """Base exception for persistence failures safe to handle in the UI."""


class ProjectNotFoundError(RepositoryError):
    """Raised when an update targets a project that no longer exists."""


class DatabaseConnectionError(RepositoryError):
    """Raised when PostgreSQL cannot be reached or configured."""
