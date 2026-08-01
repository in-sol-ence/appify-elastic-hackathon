import pytest

from services.project_import import ProjectImportError, import_project_json
from services.templates import build_sample_project


def test_exported_project_can_be_imported_as_new_copy() -> None:
    original = build_sample_project()
    imported = import_project_json(original.model_dump_json())
    assert imported.id != original.id
    assert imported.name == original.name
    assert len(imported.milestones) == len(original.milestones)
    assert len(imported.capabilities) == len(original.capabilities)
    assert len(imported.relationships) == len(original.relationships)
    assert imported.milestones[0].target_date == original.milestones[0].target_date


def test_malformed_json_is_rejected() -> None:
    with pytest.raises(ProjectImportError, match="Invalid project JSON"):
        import_project_json(b"{not valid json")


def test_empty_json_file_is_rejected() -> None:
    with pytest.raises(ProjectImportError, match="empty"):
        import_project_json(b"")
