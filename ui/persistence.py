from datetime import datetime, timezone

import streamlit as st

from models.project import Project
from repositories.exceptions import (
    DatabaseConnectionError, ProjectNotFoundError, RepositoryError,
)
from repositories.project_repository import ProjectRepository
from ui.shared import WizardState


def save_wizard_project(
    wizard: WizardState,
    repository: ProjectRepository,
    status: str,
) -> str:
    validated = Project.model_validate(wizard.project.model_dump(mode="python"))
    if wizard.project_id:
        validated.id = wizard.project_id
        repository.update_project(wizard.project_id, validated, status=status)
        project_id = wizard.project_id
    else:
        project_id = repository.create_project(validated, status=status)
    wizard.project = validated
    wizard.project_id = project_id
    wizard.selected_project = validated
    wizard.selected_project_id = project_id
    wizard.last_saved_at = datetime.now(timezone.utc)
    wizard.persistence_status = status
    return project_id


def show_repository_error(error: Exception, action: str) -> None:
    if isinstance(error, DatabaseConnectionError):
        st.error("Unable to connect to PostgreSQL. Check DATABASE_URL and confirm PostgreSQL is running.")
    elif isinstance(error, ProjectNotFoundError):
        st.error("Selected project no longer exists. Reload the saved-project list.")
    elif isinstance(error, RepositoryError):
        st.error(str(error))
    else:
        st.error(f"Project could not be {action}. Check the project data and try again.")
