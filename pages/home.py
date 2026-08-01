from datetime import datetime, timezone

import streamlit as st

from repositories.project_repository import ProjectRepository
from services.project_operations import duplicate_project
from services.readiness import evaluate_project_readiness
from ui.persistence import show_repository_error
from ui.shared import get_wizard, reset_wizard


def _ago(value):
    seconds = max(0, int((datetime.now(timezone.utc) - value).total_seconds()))
    if seconds < 60: return "just now"
    if seconds < 3600: return f"{seconds // 60} minutes ago"
    if seconds < 86400: return f"{seconds // 3600} hours ago"
    return f"{seconds // 86400} days ago"


def render(repository: ProjectRepository) -> None:
    state = get_wizard()
    st.title("Robotics BOM Guardian")
    st.write("Create, understand, and evaluate robotics projects and their bills of materials.")
    if st.button("New Project", type="primary", key="home_new"):
        st.query_params.clear(); reset_wizard(); get_wizard().current_page = "wizard"; st.rerun()
    try:
        summaries = repository.list_projects()
    except Exception as error:
        show_repository_error(error, "listed")
        summaries = []
    if not summaries:
        st.subheader("No projects yet")
        st.write("Create a project, define its milestones and component requirements, and build its bill of materials.")
        if st.button("Create Project", key="home_create_empty"):
            st.query_params.clear(); reset_wizard(); get_wizard().current_page = "wizard"; st.rerun()
        return
    st.subheader("Saved projects")
    for summary in summaries:
        try:
            project = repository.get_project(summary.project_id)
        except Exception as error:
            show_repository_error(error, "loaded"); continue
        if not project: continue
        report = evaluate_project_readiness(project)
        current = project.entity_names().get(report.current_milestone_id, "Not evaluated")
        blocker = report.blockers[0].main_blocker if report.blockers else "None"
        selected_products = sum(p.primary_product or p.selection_status.value == "Selected" for p in project.products)
        with st.container(border=True):
            st.markdown(f"### {project.name}")
            st.write(f"{project.current_stage.value} · **{summary.status}**")
            st.write(f"Current milestone: **{current}**  \nReadiness: **{report.status.value}**  \nMain blocker: {blocker}")
            st.caption(f"{len(project.component_roles)} component roles · {selected_products} selected products · Updated {_ago(summary.updated_at)}")
            open_col, duplicate_col, archive_col, delete_col = st.columns(4)
            if open_col.button("Open Project", key=f"open_{summary.project_id}"):
                state.selected_project_id = summary.project_id; state.selected_project = project
                state.project_id = summary.project_id; state.project = project; state.current_page = "workspace"; state.current_project_tab = "Overview"
                state.persistence_status = summary.status; state.last_saved_at = summary.updated_at
                st.query_params["project"] = summary.project_id; st.rerun()
            if duplicate_col.button("Duplicate", key=f"duplicate_{summary.project_id}"):
                try:
                    copy = duplicate_project(project); new_id = repository.create_project(copy, "draft")
                    st.success(f"Duplicated as {copy.name} ({new_id})."); st.rerun()
                except Exception as error: show_repository_error(error, "duplicated")
            if archive_col.button("Archive", key=f"archive_{summary.project_id}", disabled=summary.status == "archived"):
                try: repository.set_project_status(summary.project_id, "archived"); st.rerun()
                except Exception as error: show_repository_error(error, "archived")
            confirmed = delete_col.checkbox("Confirm", key=f"home_confirm_{summary.project_id}")
            if delete_col.button("Delete", key=f"home_delete_{summary.project_id}", disabled=not confirmed):
                try: repository.delete_project(summary.project_id); st.rerun()
                except Exception as error: show_repository_error(error, "deleted")
