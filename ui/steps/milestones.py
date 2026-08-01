from datetime import date, datetime

import streamlit as st

from models.project import Milestone, new_id
from ui.shared import blocking_ui_error, editor_records, get_wizard, set_step_errors


def _date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def render() -> None:
    wizard = get_wizard()
    project = wizard.current_project
    st.subheader("Milestones")
    st.write("Add, edit, remove, or reorder the outcomes that define project progress.")
    rows = [
        {
            "ID": item.id,
            "Sequence": item.sequence_number,
            "Name": item.name,
            "Description": item.description,
            "Target date": item.target_date,
            "Mandatory": item.mandatory,
            "Completion criteria": item.completion_criteria,
            "Completed": item.completed,
        }
        for item in sorted(project.milestones, key=lambda value: value.sequence_number)
    ]
    edited = st.data_editor(
        rows,
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        key="milestones_editor",
        column_config={
            "ID": st.column_config.TextColumn(disabled=True),
            "Sequence": st.column_config.NumberColumn(min_value=1, step=1, required=True),
            "Name": st.column_config.TextColumn(required=True),
            "Target date": st.column_config.DateColumn(required=True),
            "Mandatory": st.column_config.CheckboxColumn(),
            "Completed": st.column_config.CheckboxColumn(),
        },
    )
    try:
        parsed = []
        for row in editor_records(edited):
            if not str(row.get("Name") or "").strip() and not row.get("Sequence"):
                continue
            parsed.append(Milestone(
                id=str(row.get("ID") or new_id()),
                name=str(row.get("Name") or "").strip(),
                description=str(row.get("Description") or ""),
                sequence_number=int(row.get("Sequence")),
                target_date=_date(row.get("Target date")),
                mandatory=bool(row.get("Mandatory", True)),
                completion_criteria=str(row.get("Completion criteria") or ""),
                completed=bool(row.get("Completed", False)),
            ))
        project.milestones = parsed
        set_step_errors([])
    except Exception as error:
        set_step_errors([blocking_ui_error("invalid_milestone_row", f"Fix the milestone table: {error}")])
        st.error(f"Fix the milestone table: {error}")
