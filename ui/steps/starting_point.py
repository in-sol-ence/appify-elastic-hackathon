import streamlit as st

from repositories.project_repository import ProjectRepository
from services.project_import import ProjectImportError, import_project_json
from services.templates import build_rover_template
from ui.persistence import show_repository_error
from ui.shared import get_wizard, set_step_errors


OPTIONS = ["Autonomous rover template", "Robotic arm template", "Start from scratch"]


def _clear_other_widget_state(keep_template: bool = True) -> None:
    keep = {"wizard_state"}
    if keep_template:
        keep.add("step1_template")
    for key in list(st.session_state):
        if key not in keep:
            del st.session_state[key]


def render(repository: ProjectRepository) -> None:
    wizard = get_wizard()
    st.subheader("Choose a starting point")
    st.write("Templates provide editable suggestions. Nothing in a template is permanently required.")
    choice = st.radio(
        "Starting point",
        OPTIONS,
        index=OPTIONS.index(wizard.selected_template),
        key="step1_template",
    )
    if choice != wizard.selected_template:
        wizard.selected_template = choice
        _clear_other_widget_state()
        wizard.project_id = None
        wizard.persistence_status = "unsaved"
        wizard.last_saved_at = None
        if choice == "Autonomous rover template":
            wizard.project = build_rover_template()
        else:
            wizard.project = type(wizard.project)()
    elif choice == "Autonomous rover template" and not wizard.project.milestones:
        wizard.project = build_rover_template()

    if choice == "Autonomous rover template":
        st.success("Loaded editable suggestions for compute, power, mobility, communication, localization, obstacle detection, and autonomous navigation.")
    elif choice == "Robotic arm template":
        st.info("The robotic arm template starts empty in this version. Add your own milestones and capabilities in the following steps.")
    else:
        st.info("A blank structured project will be created.")

    with st.expander("Import an existing project from JSON"):
        st.write("Upload a JSON file previously exported by Robotics BOM Guardian. It will be validated and loaded as a new unsaved copy.")
        uploaded = st.file_uploader(
            "Project JSON file",
            type=["json"],
            key="step1_json_upload",
        )
        if st.button(
            "Import JSON project",
            key="step1_import_json",
            disabled=uploaded is None,
        ):
            try:
                imported = import_project_json(uploaded.getvalue())
                _clear_other_widget_state(keep_template=False)
                wizard.project = imported
                wizard.project_id = None
                wizard.current_step = 2
                wizard.validation_findings = []
                wizard.editing_state = {
                    "notice": "Project imported successfully as a new unsaved copy."
                }
                wizard.last_saved_at = None
                wizard.persistence_status = "imported"
                wizard.selected_template = "Start from scratch"
                st.rerun()
            except ProjectImportError as error:
                st.error(str(error))

    with st.expander("Load or delete a saved PostgreSQL project"):
        try:
            records = repository.list_projects()
        except Exception as error:
            wizard.persistence_status = "error"
            show_repository_error(error, "listed")
            records = []
        if not records:
            st.caption("No saved projects are available, or PostgreSQL is not configured.")
        else:
            summaries = {item.project_id: item for item in records}
            selected = st.selectbox(
                "Saved project",
                list(summaries),
                format_func=lambda item: (
                    f"{summaries[item].project_name} — {summaries[item].status} — "
                    f"{summaries[item].updated_at:%Y-%m-%d %H:%M UTC}"
                ),
                key="step1_saved_project",
            )
            load_col, delete_col = st.columns(2)
            if load_col.button("Load selected", key="step1_load"):
                try:
                    loaded = repository.get_project(selected)
                    if loaded is None:
                        st.error("Selected project no longer exists.")
                    else:
                        summary = summaries[selected]
                        _clear_other_widget_state(keep_template=False)
                        wizard.project = loaded
                        wizard.project_id = selected
                        wizard.current_step = 2
                        wizard.validation_findings = []
                        wizard.editing_state = {}
                        wizard.last_saved_at = summary.updated_at
                        wizard.persistence_status = summary.status
                        wizard.selected_template = "Start from scratch"
                        st.rerun()
                except Exception as error:
                    wizard.persistence_status = "error"
                    show_repository_error(error, "loaded")

            confirmed = delete_col.checkbox(
                "Confirm deletion",
                key=f"step1_confirm_delete_{selected}",
            )
            if delete_col.button(
                "Delete selected",
                key="step1_delete",
                disabled=not confirmed,
            ):
                try:
                    deleted = repository.delete_project(selected)
                    if deleted:
                        if wizard.project_id == selected:
                            wizard.project_id = None
                            wizard.persistence_status = "unsaved"
                        st.success("Project deleted.")
                        st.rerun()
                    else:
                        st.error("Selected project no longer exists.")
                except Exception as error:
                    wizard.persistence_status = "error"
                    show_repository_error(error, "deleted")
    set_step_errors([])
