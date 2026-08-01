import streamlit as st

from models.project import RoleMilestoneRating
from ui.shared import blocking_ui_error, editor_records, get_wizard, set_step_errors


SCALE = "0 Unrelated · 1 Minor convenience · 2 Helpful · 3 Important · 4 Blocks a major function · 5 Completely blocks the milestone"


def render() -> None:
    project = get_wizard().current_project
    st.subheader("Milestone criticality ratings")
    st.write("Rate how strongly each component role affects each milestone.")
    st.info(SCALE)
    milestones = sorted(project.milestones, key=lambda item: item.sequence_number)
    existing = {(item.component_role_id, item.milestone_id): item.rating for item in project.role_milestone_ratings}
    columns = {item.id: f"M{item.sequence_number}: {item.name}" for item in milestones}
    rows = []
    for role in project.component_roles:
        row = {"_role_id": role.id, "Component role": role.role_name}
        row.update({label: existing.get((role.id, milestone_id), 0) for milestone_id, label in columns.items()})
        rows.append(row)
    config = {
        "_role_id": None,
        "Component role": st.column_config.TextColumn(disabled=True),
        **{label: st.column_config.NumberColumn(min_value=0, max_value=5, step=1, required=True) for label in columns.values()},
    }
    edited = st.data_editor(rows, hide_index=True, width="stretch", key="ratings_editor", column_config=config)
    try:
        ratings = []
        for row in editor_records(edited):
            for milestone_id, label in columns.items():
                ratings.append(RoleMilestoneRating(component_role_id=row["_role_id"], milestone_id=milestone_id, rating=int(row[label])))
        project.role_milestone_ratings = ratings
        set_step_errors([])
    except Exception as error:
        set_step_errors([blocking_ui_error("invalid_rating", f"Every rating must be an integer from 0 to 5: {error}")])
        st.error(f"Fix the rating matrix: {error}")
