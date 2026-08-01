import streamlit as st

from pages import blueprint, bom, component_detail, find_products, live_products, overview, settings
from repositories.project_repository import ProjectRepository
from services.readiness import evaluate_project_readiness
from services.validation import validate_project
from ui.persistence import show_repository_error
from ui.shared import get_wizard

TABS = ["Overview", "Blueprint", "BOM", "Find Products", "Live Products", "Settings"]


def render(repository: ProjectRepository) -> None:
    state = get_wizard()
    if st.button("← All Projects", key="workspace_home"):
        st.query_params.clear(); state.current_page="home"; state.selected_component_id=None; state.selected_project_id=None; state.selected_project=None; st.rerun()
    project = state.selected_project
    project_id = state.selected_project_id or state.project_id
    if project is None and project_id:
        try:
            project=repository.get_project(project_id)
            summary=repository.get_project_summary(project_id)
            if summary:
                state.persistence_status=summary.status; state.last_saved_at=summary.updated_at
        except Exception as error: show_repository_error(error,"loaded"); return
    if project is None and state.project_id:
        project = state.project
    if not project:
        st.error("No project is selected.")
        if st.button("Return home"): state.current_page="home"; st.rerun()
        return
    state.project=project; state.selected_project=project; state.project_id=project_id; state.selected_project_id=project_id
    report=evaluate_project_readiness(project); state.readiness_result=report; state.validation_findings=validate_project(project)
    st.title(project.name or "Untitled project")
    saved=state.last_saved_at.strftime("%Y-%m-%d %H:%M UTC") if state.last_saved_at else "not saved this session"
    st.caption(f"{project.current_stage.value} · Updated {saved}")
    tab=st.radio("Project workspace",TABS,index=TABS.index(state.current_project_tab) if state.current_project_tab in TABS else 0,horizontal=True,key="workspace_tab")
    state.current_project_tab=tab
    st.divider()
    if state.selected_component_id:
        component_detail.render(project,report,repository)
        st.divider()
    if tab=="Overview": overview.render(project,report,repository)
    elif tab=="Blueprint": blueprint.render(project,report)
    elif tab=="BOM": bom.render(project,report)
    elif tab=="Find Products": find_products.render(project,report,repository)
    elif tab=="Live Products": live_products.render(project,report,repository)
    else: settings.render(project,repository)
