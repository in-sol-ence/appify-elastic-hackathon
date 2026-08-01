import streamlit as st

from repositories.project_repository import ProjectRepository
from services.graph_builder import build_dependency_graph
from services.readiness import evaluate_readiness
from services.validation import has_blocking, validate_project
from ui.persistence import save_wizard_project, show_repository_error
from ui.shared import get_wizard, reset_wizard, show_findings


def _table(items, fields):
    return [{label: getter(item) for label, getter in fields} for item in items]


def render(repository: ProjectRepository) -> None:
    wizard = get_wizard()
    project = wizard.current_project
    findings = validate_project(project)
    wizard.validation_findings = findings
    names = project.entity_names()

    st.subheader("Review and validation")
    st.write("Review the complete dependency model, resolve blocking errors, and save the project.")

    st.markdown("#### Validation findings")
    show_findings(findings)

    st.markdown("#### Readiness")
    readiness = evaluate_readiness(project)
    st.dataframe([
        {"Capability or milestone": item.owner_name, "Status": item.status.value, "Reason": item.reason}
        for item in readiness
    ], hide_index=True, width="stretch")

    st.markdown("#### Project basics")
    st.write({
        "Name": project.name, "Description": project.short_description,
        "Budget": f"${project.total_budget:,.2f}", "Deadline": str(project.final_deadline or "Not set"),
        "Stage": project.current_stage.value, "Environment": project.operating_environment.value,
        "Location": project.location, "Software platform": project.software_platform,
        "Team size": project.team_size, "Risk tolerance": project.risk_tolerance.value,
    })

    sections = [
        ("Milestones", _table(sorted(project.milestones, key=lambda x: x.sequence_number), [
            ("Sequence", lambda x: x.sequence_number), ("Name", lambda x: x.name),
            ("Target date", lambda x: x.target_date), ("Mandatory", lambda x: x.mandatory),
        ])),
        ("Capabilities", _table(project.capabilities, [
            ("Name", lambda x: x.name), ("Requiredness", lambda x: x.requiredness.value),
            ("First milestone", lambda x: names.get(x.first_relevant_milestone_id, "Not assigned")),
        ])),
        ("Component roles", _table(project.component_roles, [
            ("Role", lambda x: x.role_name), ("Category", lambda x: x.category),
            ("Capability", lambda x: names.get(x.capability_id, "Not assigned")),
            ("Requiredness", lambda x: x.requiredness.value), ("Status", lambda x: x.current_status.value),
        ])),
        ("Criticality ratings", _table(project.role_milestone_ratings, [
            ("Role", lambda x: names.get(x.component_role_id, "Deleted")),
            ("Milestone", lambda x: names.get(x.milestone_id, "Deleted")), ("Rating", lambda x: x.rating),
        ])),
        ("Direct dependencies", _table(project.relationships, [
            ("Source", lambda x: names.get(x.source_id, "Deleted")),
            ("Relationship", lambda x: x.relationship_type.value),
            ("Target", lambda x: names.get(x.target_id, "Deleted")),
            ("Strength", lambda x: x.strength.value), ("Validation", lambda x: x.validation_status.value),
        ])),
        ("Requirement groups", _table(project.requirement_groups, [
            ("Group", lambda x: x.group_name), ("Owner", lambda x: names.get(x.owner_id, "Deleted")),
            ("Logic", lambda x: x.logic_type.value),
            ("Members", lambda x: ", ".join(names.get(item, "Deleted") for item in x.member_component_role_ids)),
            ("Strength", lambda x: x.requirement_strength.value),
        ])),
        ("Product selections", _table(project.products, [
            ("Product", lambda x: x.product_name), ("Role", lambda x: names.get(x.component_role_id, "Deleted")),
            ("Selection", lambda x: x.selection_status.value), ("Purchase", lambda x: x.purchase_status.value),
            ("Verification", lambda x: x.verification_status.value), ("Primary", lambda x: x.primary_product),
        ])),
    ]
    for title, rows in sections:
        with st.expander(f"{title} ({len(rows)})"):
            if rows:
                st.dataframe(rows, hide_index=True, width="stretch")
            else:
                st.caption("None defined.")

    st.markdown("#### Dependency preview")
    st.caption("Shapes distinguish projects, milestones, capabilities, component roles, products, and requirement groups.")
    st.graphviz_chart(build_dependency_graph(project), width="stretch")

    st.markdown("#### Final actions")
    save, draft, export, reset = st.columns(4)
    if save.button("Save Project", key="review_save_project", type="primary", width="stretch"):
        if has_blocking(findings):
            st.error("Resolve all blocking errors before saving the project.")
        else:
            try:
                project_id = save_wizard_project(wizard, repository, "active")
                wizard.current_page = "workspace"
                wizard.current_project_tab = "Overview"
                wizard.editing_mode = False
                st.query_params["project"] = project_id
                st.success(f"Project saved successfully. Project ID: {project_id}")
                st.rerun()
            except Exception as error:
                wizard.persistence_status = "error"
                show_repository_error(error, "saved")
    if draft.button("Save Draft", key="review_save_draft", width="stretch"):
        try:
            project_id = save_wizard_project(wizard, repository, "draft")
            st.success(
                f"Draft {project_id} saved at "
                f"{wizard.last_saved_at.strftime('%Y-%m-%d %H:%M:%S UTC')}."
            )
        except Exception as error:
            wizard.persistence_status = "error"
            show_repository_error(error, "saved")
    export.download_button(
        "Export JSON", data=project.model_dump_json(indent=2),
        file_name=f"{(project.name or 'robotics-project').lower().replace(' ', '-')}.json",
        mime="application/json", key="review_export", width="stretch",
    )
    if reset.button("Reset Wizard", key="review_reset", width="stretch"):
        reset_wizard()
        st.rerun()
