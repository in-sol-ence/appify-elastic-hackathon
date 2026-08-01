import streamlit as st

from pages import home, project_workspace
from repositories.project_repository import ProjectRepository
from ui.navigation import render_navigation
from ui.shared import get_wizard, project_summary, step_indicator
from ui.steps import (
    capabilities, component_roles, dependencies, milestones, products,
    project_basics, ratings, requirement_groups, review, starting_point,
)

st.set_page_config(page_title="Robotics BOM Guardian", page_icon="⚙️", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1500px; padding-top: 2rem; padding-bottom: 3rem;}
h1, h2, h3 {letter-spacing: -0.015em;}
[data-testid="stMetric"] {display: none;}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def repository() -> ProjectRepository:
    return ProjectRepository()


repo = repository()
state = get_wizard()
query_project_id = st.query_params.get("project")
if query_project_id and not state.selected_project_id:
    state.selected_project_id = query_project_id
    state.project_id = query_project_id
    state.current_page = "workspace"

if state.current_page == "home":
    home.render(repo)
elif state.current_page == "workspace":
    project_workspace.render(repo)
else:
    if st.button("← Cancel editing", key="wizard_cancel"):
        state.current_page = "workspace" if state.project_id else "home"
        st.rerun()
    st.title("New Project Wizard" if not state.editing_mode else f"Edit {state.project.name or 'Project'}")
    st.write("Define milestones, capabilities, component roles, dependencies, requirement groups, and manual product selections.")
    step_indicator(state.current_step)
    project_summary(state.project)
    if state.project_id:
        saved_at = state.last_saved_at.strftime("%Y-%m-%d %H:%M:%S UTC") if state.last_saved_at else "unknown"
        st.caption(f"PostgreSQL ID: {state.project_id} · Status: {state.persistence_status} · Last saved: {saved_at}")
    st.divider()
    renderers = {
        1: lambda: starting_point.render(repo), 2: project_basics.render, 3: milestones.render,
        4: capabilities.render, 5: component_roles.render, 6: ratings.render,
        7: dependencies.render, 8: requirement_groups.render, 9: products.render,
        10: lambda: review.render(repo),
    }
    renderers[state.current_step]()
    render_navigation(repo)
