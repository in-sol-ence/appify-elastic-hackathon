import streamlit as st

from models.enums import ReadinessStatus
from services.project_summary import recommended_actions
from ui.persistence import save_wizard_project, show_repository_error
from ui.shared import get_wizard

SYMBOL = {ReadinessStatus.READY: "✓", ReadinessStatus.COMPLETED: "✓", ReadinessStatus.BLOCKED: "✕", ReadinessStatus.AT_RISK: "!", ReadinessStatus.INCOMPLETE: "○", ReadinessStatus.NOT_EVALUATED: "○"}


def render(project, report, repository) -> None:
    state = get_wizard(); names = project.entity_names()
    current = names.get(report.current_milestone_id, "Not evaluated")
    ready = sum(x.status in {ReadinessStatus.READY, ReadinessStatus.COMPLETED} for x in report.milestones.values())
    blocked = sum(x.status == ReadinessStatus.BLOCKED for x in report.milestones.values())
    unresolved = sum(x.status not in {ReadinessStatus.READY, ReadinessStatus.COMPLETED, ReadinessStatus.NOT_EVALUATED} for x in report.component_roles.values())
    st.subheader("Project overview")
    st.write(f"**Stage:** {project.current_stage.value} · **Current milestone:** {current} · **Overall readiness:** {report.status.value}")
    st.write(f"**Deadline:** {project.final_deadline or 'Not set'} · **Budget:** ${project.total_budget:,.2f} · **Milestones ready / blocked:** {ready} / {blocked} · **Unresolved roles:** {unresolved}")
    st.markdown("#### Milestones")
    caps_by_m = {m.id: [c for c in project.capabilities if c.first_relevant_milestone_id == m.id] for m in project.milestones}
    for milestone in sorted(project.milestones, key=lambda x: x.sequence_number):
        item = report.milestones[milestone.id]
        with st.expander(f"{SYMBOL[item.status]} {milestone.name} — {item.status.value}"):
            st.write(f"Target: {milestone.target_date} · Required capabilities: {len(caps_by_m[milestone.id])} · Satisfied: {item.satisfied_requirements} · Unresolved: {item.unresolved_requirements}")
            st.write(item.reasons[0] if item.reasons else "No explanation available.")
            if not milestone.completed and st.button("Confirm milestone completed", key=f"complete_milestone_{milestone.id}"):
                milestone.completed=True
                try:
                    save_wizard_project(state,repository,state.persistence_status if state.persistence_status in {"draft","active","archived"} else "active"); st.rerun()
                except Exception as error: show_repository_error(error,"saved")
    st.markdown("#### Current blockers")
    if not report.blockers: st.success("No deterministic blockers found.")
    for blocker in report.blockers[:10]:
        with st.container(border=True):
            st.write(f"**{blocker.name}**")
            st.write(blocker.main_blocker or "; ".join(blocker.reasons))
            if blocker.entity_id in report.component_roles and st.button("Open component", key=f"overview_component_{blocker.entity_id}"):
                state.selected_component_id = blocker.entity_id; st.rerun()
    st.markdown("#### Unresolved decisions")
    decisions = []
    for role in project.component_roles:
        item = report.component_roles[role.id]
        if role.requiredness.value in {"Optional", "Conditional"} and item.status == ReadinessStatus.NOT_EVALUATED: decisions.append(f"{role.role_name} remains optional or unevaluated")
    for rel in project.relationships:
        if rel.validation_status.value == "Unverified": decisions.append(f"{names.get(rel.source_id, 'Component')} → {names.get(rel.target_id, 'component')} compatibility is unverified")
    if decisions: st.markdown("\n".join(f"- {item}" for item in decisions[:8]))
    else: st.caption("No unresolved non-blocking decisions.")
    st.markdown("#### Recommended next actions")
    actions = recommended_actions(project, report)
    if actions: st.markdown("\n".join(f"{i}. {a.text}" for i, a in enumerate(actions[:8], 1)))
    else: st.success("No immediate actions are required.")
