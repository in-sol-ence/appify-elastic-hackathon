from datetime import datetime, timezone

from pydantic import ValidationError

from models.project import Project, new_id

MAX_IMPORT_BYTES = 5 * 1024 * 1024


class ProjectImportError(ValueError):
    """Raised when an uploaded JSON document is not a valid Project."""


def import_project_json(data: bytes | str) -> Project:
    size = len(data.encode("utf-8")) if isinstance(data, str) else len(data)
    if size == 0:
        raise ProjectImportError("The uploaded JSON file is empty.")
    if size > MAX_IMPORT_BYTES:
        raise ProjectImportError("The uploaded JSON file exceeds the 5 MB limit.")
    try:
        project = Project.model_validate_json(data)
    except ValidationError as error:
        first = error.errors()[0]
        location = ".".join(str(part) for part in first.get("loc", ())) or "project"
        raise ProjectImportError(
            f"Invalid project JSON at {location}: {first.get('msg', 'validation failed')}."
        ) from error

    # An imported document is an unsaved copy, not authority to overwrite a row
    # that may already use the exported UUID.
    now = datetime.now(timezone.utc)
    project.id = new_id()
    project.created_at = now
    project.updated_at = now
    return project
