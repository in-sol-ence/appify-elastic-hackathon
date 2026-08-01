from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

import pytest

from models.enums import PurchaseStatus, SelectionStatus, VerificationStatus
from models.project import ProductSelection
from repositories.database import get_connection
from repositories.exceptions import DatabaseConnectionError, RepositoryError
from repositories.project_repository import ProjectRepository
from services.templates import build_sample_project

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is not configured; PostgreSQL integration tests skipped.",
)


@pytest.fixture(scope="session")
def test_database_url() -> str:
    assert TEST_DATABASE_URL is not None
    database_name = urlparse(TEST_DATABASE_URL).path.lstrip("/")
    if not database_name.endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must point to a database whose name ends in '_test'.")
    migration = Path("db/migrations/001_create_projects.sql").read_text(encoding="utf-8")
    with get_connection(TEST_DATABASE_URL) as connection:
        connection.execute(migration)
    return TEST_DATABASE_URL


@pytest.fixture
def repository(test_database_url: str):
    repo = ProjectRepository(test_database_url)
    with get_connection(test_database_url) as connection:
        connection.execute("DELETE FROM projects WHERE name LIKE %s", ("pytest-%",))
    yield repo
    with get_connection(test_database_url) as connection:
        connection.execute("DELETE FROM projects WHERE name LIKE %s", ("pytest-%",))


def project_with_nested_data():
    project = build_sample_project()
    project.name = f"pytest-{project.id}"
    project.products.append(ProductSelection(
        component_role_id=project.component_roles[0].id,
        manufacturer="Example Robotics",
        product_name="Compute Module",
        model="CM-1",
        selection_status=SelectionStatus.SELECTED,
        purchase_status=PurchaseStatus.ORDERED,
        verification_status=VerificationStatus.SPEC_REVIEWED,
        primary_product=True,
    ))
    return project


def test_create_load_and_jsonb_round_trip(repository: ProjectRepository) -> None:
    project = project_with_nested_data()
    project_id = repository.create_project(project, "draft")
    loaded = repository.get_project(project_id)

    assert loaded is not None
    assert loaded.model_dump(mode="json") == project.model_dump(mode="json")
    assert loaded.milestones[0].name == "Compute setup"
    assert loaded.capabilities[0].name == "Compute"
    assert loaded.relationships[0].source_id == project.relationships[0].source_id
    assert loaded.products[0].product_name == "Compute Module"


def test_update_existing_project(repository: ProjectRepository) -> None:
    project = project_with_nested_data()
    project_id = repository.create_project(project)
    project.short_description = "Updated through PostgreSQL"
    repository.update_project(project_id, project, status="active")
    loaded = repository.get_project(project_id)
    assert loaded is not None
    assert loaded.short_description == "Updated through PostgreSQL"
    assert repository.list_projects(status="active")[0].project_id == project_id


def test_list_and_filter_projects(repository: ProjectRepository) -> None:
    draft = project_with_nested_data()
    active = project_with_nested_data()
    repository.create_project(draft, "draft")
    repository.create_project(active, "active")

    all_ids = {item.project_id for item in repository.list_projects()}
    draft_ids = {item.project_id for item in repository.list_projects("draft")}
    active_ids = {item.project_id for item in repository.list_projects("active")}
    assert {draft.id, active.id} <= all_ids
    assert draft.id in draft_ids and active.id not in draft_ids
    assert active.id in active_ids and draft.id not in active_ids


def test_delete_and_load_missing_project(repository: ProjectRepository) -> None:
    project = project_with_nested_data()
    project_id = repository.create_project(project)
    assert repository.project_exists(project_id)
    assert repository.delete_project(project_id) is True
    assert repository.delete_project(project_id) is False
    assert repository.get_project(project_id) is None


def test_duplicate_uuid_is_rejected(repository: ProjectRepository) -> None:
    project = project_with_nested_data()
    repository.create_project(project)
    with pytest.raises(RepositoryError, match="already exists"):
        repository.create_project(project)
