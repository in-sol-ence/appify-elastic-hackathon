from services.export_service import export_bom_csv, export_project_json
from services.project_operations import duplicate_project
from services.templates import build_sample_project
from ui.shared import WizardState


def test_duplicate_regenerates_project_and_nested_ids() -> None:
    project=build_sample_project(); copy=duplicate_project(project)
    assert copy.id != project.id
    assert {x.id for x in copy.milestones}.isdisjoint({x.id for x in project.milestones})
    assert copy.capabilities[0].first_relevant_milestone_id in {x.id for x in copy.milestones}
    assert copy.relationships[0].source_id in copy.entity_names()


def test_json_and_csv_exports() -> None:
    project=build_sample_project()
    assert '"Autonomous Target Rover"' in export_project_json(project)
    assert "Component role" in export_bom_csv(project)


def test_structured_state_preserves_selection_and_component() -> None:
    project=build_sample_project(); state=WizardState(selected_project_id=project.id,selected_project=project,current_page="workspace",current_project_tab="BOM",selected_component_id=project.component_roles[0].id)
    assert state.selected_project.id==project.id
    assert state.current_project_tab=="BOM"
    assert state.selected_component_id==project.component_roles[0].id
