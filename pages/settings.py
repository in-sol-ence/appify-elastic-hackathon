import streamlit as st

from models.enums import OperatingEnvironment, ProjectStage, RiskTolerance
from repositories.project_repository import ProjectRepository
from services.export_service import export_bom_csv, export_project_json
from services.project_operations import duplicate_project
from ui.persistence import save_wizard_project, show_repository_error
from ui.shared import enum_values, get_wizard


def render(project, repository: ProjectRepository) -> None:
    state = get_wizard(); st.subheader("Project settings")
    with st.form("settings_form"):
        name = st.text_input("Name", project.name); description = st.text_area("Description", project.short_description)
        c1, c2 = st.columns(2)
        budget = c1.number_input("Budget", min_value=0.0, value=float(project.total_budget)); deadline = c2.date_input("Deadline", project.final_deadline)
        stage = c1.selectbox("Current stage", enum_values(ProjectStage), index=enum_values(ProjectStage).index(project.current_stage.value))
        environment = c2.selectbox("Operating environment", enum_values(OperatingEnvironment), index=enum_values(OperatingEnvironment).index(project.operating_environment.value))
        location = c1.text_input("Location", project.location); platform = c2.text_input("Software platform", project.software_platform)
        team = c1.number_input("Team size", min_value=1, value=project.team_size); risk = c2.selectbox("Risk tolerance", enum_values(RiskTolerance), index=enum_values(RiskTolerance).index(project.risk_tolerance.value))
        if st.form_submit_button("Save changes"):
            project.name=name; project.short_description=description; project.total_budget=budget; project.final_deadline=deadline
            project.current_stage=ProjectStage(stage); project.operating_environment=OperatingEnvironment(environment); project.location=location; project.software_platform=platform; project.team_size=int(team); project.risk_tolerance=RiskTolerance(risk)
            try: save_wizard_project(state, repository, state.persistence_status if state.persistence_status in {"draft","active","archived"} else "active"); st.success("Project settings saved.")
            except Exception as error: show_repository_error(error, "saved")
    st.markdown("#### Project management")
    cols = st.columns(4)
    if cols[0].button("Edit Project Structure", key="settings_edit_structure"):
        state.current_page="wizard"; state.current_step=2; state.editing_mode=True; st.rerun()
    if cols[1].button("Duplicate project", key="settings_duplicate"):
        try:
            copy=duplicate_project(project); new_id=repository.create_project(copy,"draft"); st.success(f"Created {copy.name}: {new_id}")
        except Exception as error: show_repository_error(error,"duplicated")
    cols[2].download_button("Export JSON", export_project_json(project), "project.json", "application/json", key="settings_json")
    cols[3].download_button("Export BOM CSV", export_bom_csv(project), "bom.csv", "text/csv", key="settings_csv")
    archive, delete = st.columns(2)
    if archive.button("Archive project", key="settings_archive"):
        try: repository.set_project_status(state.project_id,"archived"); state.persistence_status="archived"; st.success("Project archived.")
        except Exception as error: show_repository_error(error,"archived")
    confirmed = delete.checkbox("Confirm permanent deletion", key="settings_confirm_delete")
    if delete.button("Delete project", key="settings_delete", disabled=not confirmed):
        try:
            repository.delete_project(state.project_id); st.query_params.clear(); state.current_page="home"; state.selected_project_id=None; state.selected_project=None; st.rerun()
        except Exception as error: show_repository_error(error,"deleted")
