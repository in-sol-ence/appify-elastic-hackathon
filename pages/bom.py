import streamlit as st

from models.enums import ReadinessStatus
from services.bom_calculator import bom_rows, calculate_bom_totals
from services.export_service import export_bom_csv, export_project_json
from ui.shared import get_wizard


def render(project, report) -> None:
    state = get_wizard(); st.subheader("Bill of materials")
    totals = calculate_bom_totals(project)
    st.caption("Estimated values use only manually stored project data.")
    st.write(f"**Expected total:** ${totals.expected_total_cost:,.2f} · **Mandatory:** ${totals.mandatory_cost:,.2f} · **Optional:** ${totals.optional_cost:,.2f} · **Remaining budget:** ${totals.remaining_budget:,.2f} · **Missing prices:** {totals.unresolved_prices}")
    view = st.radio("BOM view", ["Combined BOM", "Design requirements", "Product selections", "Procurement status"], horizontal=True, key="bom_view")
    filters = st.multiselect("Filters", ["Mandatory", "Conditional", "Optional", "Missing product", "Not ordered", "Unverified", "Blocked", "Current milestone"], key="bom_filters")
    categories = sorted({r.category for r in project.component_roles}); category = st.selectbox("Component category", [None, *categories], format_func=lambda x: x or "All", key="bom_category")
    rows = bom_rows(project, report)
    current = report.current_milestone_id
    filtered = []
    role_map = {r.id: r for r in project.component_roles}
    for row in rows:
        role = role_map[row["role_id"]]
        if category and role.category != category: continue
        if "Mandatory" in filters and role.requiredness.value != "Mandatory": continue
        if "Conditional" in filters and role.requiredness.value != "Conditional": continue
        if "Optional" in filters and role.requiredness.value != "Optional": continue
        if "Missing product" in filters and row["Selected product"] != "Not selected": continue
        if "Not ordered" in filters and row["Purchase status"] not in {"Not planned", "Planned"}: continue
        if "Unverified" in filters and row["Verification status"] != "Unverified": continue
        if "Blocked" in filters and row["Readiness status"] != "Blocked": continue
        if "Current milestone" in filters and role.first_required_milestone_id != current: continue
        filtered.append(row)
    columns = {
        "Design requirements": ["Component role", "Category", "Capability", "Required quantity", "Requiredness", "Required milestone", "Role status"],
        "Product selections": ["Component role", "Selected product", "Product quantity", "Expected unit price", "Expected total price", "Verification status"],
        "Procurement status": ["Component role", "Product quantity", "Purchase status", "Verification status", "Role status"],
    }.get(view, [key for key in rows[0] if key != "role_id"] if rows else [])
    st.dataframe([{key: row[key] for key in columns} for row in filtered], hide_index=True, use_container_width=True)
    if filtered:
        selected = st.selectbox("Select component", [r["role_id"] for r in filtered], format_func=lambda x: role_map[x].role_name, key="bom_selected_role")
        if st.button("Open component", key="bom_open_component"):
            state.selected_component_id = selected; st.rerun()
    action_cols = st.columns(4)
    if action_cols[0].button("Add component role", key="bom_add_role"):
        state.current_page = "wizard"; state.current_step = 5; state.editing_mode = True; st.rerun()
    action_cols[1].download_button("Export BOM CSV", export_bom_csv(project), "bom.csv", "text/csv", key="bom_csv")
    action_cols[2].download_button("Export project JSON", export_project_json(project), "project.json", "application/json", key="bom_json")
