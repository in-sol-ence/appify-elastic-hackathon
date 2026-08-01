from datetime import date, datetime

import streamlit as st

from models.enums import RoleRequiredness, RoleStatus
from models.project import ComponentRole, new_id
from ui.shared import blocking_ui_error, editor_records, enum_values, get_wizard, set_step_errors


NONE = "— Not assigned —"


def _optional_date(value):
    if value is None or str(value) in {"", "NaT", "nan"}:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def render() -> None:
    wizard = get_wizard()
    project = wizard.current_project
    st.subheader("Component roles")
    st.write("Define what the project needs before choosing specific products.")
    with st.expander("What is a component role?"):
        st.write("A component role is a functional placeholder such as “Motor driver.” A specific purchasable model is added later as a product selection.")
    capabilities = {item.id: item.name for item in project.capabilities}
    milestones = {item.id: item.name for item in project.milestones}
    capability_ids = {name: item_id for item_id, name in capabilities.items()}
    milestone_ids = {name: item_id for item_id, name in milestones.items()}
    rows = [{
        "ID": item.id, "Role name": item.role_name, "Category": item.category,
        "Purpose": item.purpose, "Capability enabled": capabilities.get(item.capability_id, NONE),
        "Quantity": item.required_quantity, "Requiredness": item.requiredness.value,
        "First required milestone": milestones.get(item.first_required_milestone_id, NONE),
        "Required by": item.required_by, "Necessity confidence": item.necessity_confidence,
        "Replacement difficulty": item.replacement_difficulty, "Integration risk": item.integration_risk,
        "Acceptance criteria": item.functional_acceptance_criteria, "Current status": item.current_status.value,
        "Condition description": item.condition_description or "",
    } for item in project.component_roles]
    edited = st.data_editor(
        rows, num_rows="dynamic", hide_index=True, width="stretch", key="roles_editor",
        column_config={
            "ID": st.column_config.TextColumn(disabled=True),
            "Capability enabled": st.column_config.SelectboxColumn(options=[NONE, *capability_ids]),
            "First required milestone": st.column_config.SelectboxColumn(options=[NONE, *milestone_ids]),
            "Requiredness": st.column_config.SelectboxColumn(options=enum_values(RoleRequiredness), required=True),
            "Current status": st.column_config.SelectboxColumn(options=enum_values(RoleStatus), required=True),
            "Quantity": st.column_config.NumberColumn(min_value=1, step=1),
            "Necessity confidence": st.column_config.NumberColumn(min_value=0, max_value=100, step=1),
            "Replacement difficulty": st.column_config.NumberColumn(min_value=1, max_value=5, step=1),
            "Integration risk": st.column_config.NumberColumn(min_value=1, max_value=5, step=1),
            "Required by": st.column_config.DateColumn(),
        },
    )
    try:
        parsed = []
        for row in editor_records(edited):
            if not str(row.get("Role name") or "").strip():
                continue
            parsed.append(ComponentRole(
                id=str(row.get("ID") or new_id()), role_name=str(row["Role name"]).strip(),
                category=str(row.get("Category") or "Uncategorized"), purpose=str(row.get("Purpose") or ""),
                capability_id=capability_ids.get(str(row.get("Capability enabled") or NONE)),
                required_quantity=int(row.get("Quantity") or 1),
                requiredness=RoleRequiredness(str(row.get("Requiredness") or RoleRequiredness.MANDATORY.value)),
                first_required_milestone_id=milestone_ids.get(str(row.get("First required milestone") or NONE)),
                required_by=_optional_date(row.get("Required by")),
                necessity_confidence=int(row.get("Necessity confidence") if row.get("Necessity confidence") is not None else 100),
                replacement_difficulty=int(row.get("Replacement difficulty") or 1),
                integration_risk=int(row.get("Integration risk") or 1),
                functional_acceptance_criteria=str(row.get("Acceptance criteria") or ""),
                current_status=RoleStatus(str(row.get("Current status") or RoleStatus.PROPOSED.value)),
                condition_description=str(row.get("Condition description") or "") or None,
            ))
        project.component_roles = parsed
        set_step_errors([])
    except Exception as error:
        set_step_errors([blocking_ui_error("invalid_role_row", f"Fix the component role table: {error}")])
        st.error(f"Fix the component role table: {error}")
    st.caption("Confidence is 0–100%. Replacement difficulty and integration risk use 1–5 scales. Conditional roles require a condition description.")
