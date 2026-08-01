import streamlit as st

from models.enums import Requiredness
from models.project import Capability, new_id
from ui.shared import blocking_ui_error, editor_records, enum_values, get_wizard, set_step_errors


NONE = "— Not assigned —"


def render() -> None:
    wizard = get_wizard()
    project = wizard.current_project
    st.subheader("Required capabilities")
    st.write("Describe what the robot must be able to do, independently of the products used to achieve it.")
    milestone_names = {item.id: item.name for item in project.milestones}
    name_to_id = {name: item_id for item_id, name in milestone_names.items()}
    milestone_options = [NONE, *name_to_id]
    rows = [{
        "ID": item.id,
        "Name": item.name,
        "Description": item.description,
        "Requiredness": item.requiredness.value,
        "First relevant milestone": milestone_names.get(item.first_relevant_milestone_id, NONE),
        "Acceptance criteria": item.acceptance_criteria,
        "Condition description": item.condition_description or "",
    } for item in project.capabilities]
    edited = st.data_editor(
        rows,
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        key="capabilities_editor",
        column_config={
            "ID": st.column_config.TextColumn(disabled=True),
            "Name": st.column_config.TextColumn(required=True),
            "Requiredness": st.column_config.SelectboxColumn(options=enum_values(Requiredness), required=True),
            "First relevant milestone": st.column_config.SelectboxColumn(options=milestone_options),
        },
    )
    try:
        parsed = []
        for row in editor_records(edited):
            if not str(row.get("Name") or "").strip():
                continue
            milestone_name = str(row.get("First relevant milestone") or NONE)
            parsed.append(Capability(
                id=str(row.get("ID") or new_id()),
                name=str(row["Name"]).strip(),
                description=str(row.get("Description") or ""),
                requiredness=Requiredness(str(row.get("Requiredness") or Requiredness.MANDATORY.value)),
                first_relevant_milestone_id=name_to_id.get(milestone_name),
                acceptance_criteria=str(row.get("Acceptance criteria") or ""),
                condition_description=str(row.get("Condition description") or "") or None,
            ))
        project.capabilities = parsed
        set_step_errors([])
    except Exception as error:
        set_step_errors([blocking_ui_error("invalid_capability_row", f"Fix the capability table: {error}")])
        st.error(f"Fix the capability table: {error}")
    st.caption("Conditional capabilities require a condition description.")
