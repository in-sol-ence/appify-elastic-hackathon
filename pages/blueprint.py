import streamlit as st

from services.graph_builder import build_dependency_graph
from ui.shared import get_wizard


def render(project, report) -> None:
    state = get_wizard(); st.subheader("Project Blueprint")
    mode = st.radio("Display mode", ["Architecture", "Products", "Full project"], horizontal=True, key="blueprint_mode")
    milestones = {m.id: m.name for m in project.milestones}; caps = {c.id: c.name for c in project.capabilities}
    categories = sorted({r.category for r in project.component_roles}); requiredness = sorted({r.requiredness.value for r in project.component_roles}); statuses = sorted({r.current_status.value for r in project.component_roles})
    cols = st.columns(5)
    milestone = cols[0].selectbox("Milestone", [None, *milestones], format_func=lambda x: "All" if x is None else milestones[x], key="bp_m")
    capability = cols[1].selectbox("Capability", [None, *caps], format_func=lambda x: "All" if x is None else caps[x], key="bp_c")
    category = cols[2].selectbox("Category", [None, *categories], format_func=lambda x: x or "All", key="bp_cat")
    required = cols[3].selectbox("Requiredness", [None, *requiredness], format_func=lambda x: x or "All", key="bp_req")
    status = cols[4].selectbox("Status", [None, *statuses], format_func=lambda x: x or "All", key="bp_status")
    problems = st.checkbox("Show only problems", key="bp_problems")
    show_products = st.checkbox("Show products", value=mode != "Architecture", key="bp_products")
    graph = build_dependency_graph(project, mode, milestone, capability, category, required, status, problems, show_products, report)
    st.graphviz_chart(graph, use_container_width=True)
    visible_roles = [r for r in project.component_roles if (not category or r.category == category) and (not capability or r.capability_id == capability)]
    if visible_roles:
        role_id = st.selectbox("Inspect component node", [r.id for r in visible_roles], format_func=lambda x: next(r.role_name for r in visible_roles if r.id == x), key="bp_selected_role")
        if st.button("Open component details", key="bp_open_component"):
            state.selected_component_id = role_id; st.rerun()
