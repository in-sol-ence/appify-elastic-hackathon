import streamlit as st

from repositories.project_repository import ProjectRepository
from services.validation import has_blocking, validate_step
from ui.persistence import save_wizard_project, show_repository_error
from ui.shared import STEPS, get_wizard, show_findings, step_errors


def render_navigation(repository: ProjectRepository) -> None:
    wizard = get_wizard()
    st.divider()
    previous, spacer, draft, continue_column = st.columns([1, 4, 1.4, 1.4])
    with previous:
        if st.button("Previous", key="nav_previous", disabled=wizard.current_step == 1, width="stretch"):
            wizard.current_step -= 1
            wizard.editing_state["step_errors"] = []
            st.rerun()
    with draft:
        if st.button("Save Draft", key="nav_save_draft", width="stretch"):
            try:
                project_id = save_wizard_project(wizard, repository, "draft")
                st.success(
                    f"Draft {project_id} saved at "
                    f"{wizard.last_saved_at.strftime('%Y-%m-%d %H:%M:%S UTC')}."
                )
            except Exception as error:
                wizard.persistence_status = "error"
                show_repository_error(error, "saved")
    with continue_column:
        if wizard.current_step < len(STEPS):
            if st.button("Continue", key="nav_continue", type="primary", width="stretch"):
                findings = [*step_errors(), *validate_step(wizard.current_project, wizard.current_step)]
                wizard.validation_findings = findings
                if has_blocking(findings):
                    show_findings(findings)
                else:
                    wizard.current_step += 1
                    wizard.editing_state["step_errors"] = []
                    st.rerun()
