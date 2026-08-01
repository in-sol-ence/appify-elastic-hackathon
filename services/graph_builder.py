from graphviz import Digraph

from models.enums import ReadinessStatus, RoleRequiredness
from models.project import Project
from models.readiness import ReadinessReport


def build_dependency_graph(
    project: Project,
    mode: str = "Full project",
    milestone_id: str | None = None,
    capability_id: str | None = None,
    category: str | None = None,
    requiredness: str | None = None,
    role_status: str | None = None,
    problems_only: bool = False,
    show_products: bool = True,
    readiness: ReadinessReport | None = None,
) -> Digraph:
    graph = Digraph("robotics_bom", graph_attr={"rankdir": "LR", "splines": "spline"})
    graph.attr("node", fontname="Arial", fontsize="10")
    roles = []
    for role in project.component_roles:
        state = readiness.component_roles.get(role.id) if readiness else None
        if capability_id and role.capability_id != capability_id: continue
        if category and role.category != category: continue
        if requiredness and role.requiredness.value != requiredness: continue
        if role_status and role.current_status.value != role_status: continue
        if milestone_id and role.first_required_milestone_id != milestone_id and not any(r.component_role_id == role.id and r.milestone_id == milestone_id and r.rating > 0 for r in project.role_milestone_ratings): continue
        if problems_only and state and state.status not in {ReadinessStatus.BLOCKED, ReadinessStatus.AT_RISK, ReadinessStatus.INCOMPLETE}: continue
        roles.append(role)
    role_ids = {role.id for role in roles}
    capability_ids = {role.capability_id for role in roles if role.capability_id}
    if capability_id: capability_ids.add(capability_id)
    milestone_ids = {m.id for m in project.milestones if not milestone_id or m.id == milestone_id}

    for milestone in project.milestones:
        if mode != "Products" and milestone.id in milestone_ids:
            graph.node(milestone.id, f"M{milestone.sequence_number}: {milestone.name}\n[MILESTONE]", shape="box")
    for capability in project.capabilities:
        if mode != "Products" and (capability.id in capability_ids or not roles):
            graph.node(capability.id, f"{capability.name}\n[CAPABILITY]", shape="ellipse")
            if capability.first_relevant_milestone_id in milestone_ids:
                graph.edge(capability.first_relevant_milestone_id, capability.id, label="REQUIRES")
    for role in roles:
        state = readiness.component_roles.get(role.id) if readiness else None
        status = state.status.value if state else role.current_status.value
        optional = " OPTIONAL" if role.requiredness == RoleRequiredness.OPTIONAL else ""
        style = "dashed" if optional else "solid"
        penwidth = "2" if state and state.status == ReadinessStatus.BLOCKED else "1"
        graph.node(role.id, f"{role.role_name}\n[ROLE{optional} · {status}]", shape="component", style=style, penwidth=penwidth)
        if mode != "Products" and role.capability_id:
            graph.edge(role.capability_id, role.id, label="ENABLED_BY")
    if mode in {"Products", "Full project"} and show_products:
        for product in project.products:
            if product.component_role_id in role_ids:
                graph.node(product.id, f"{product.product_name}\n[PRODUCT · {product.verification_status.value}]", shape="note")
                graph.edge(product.component_role_id, product.id, label="SELECTED" if product.primary_product else "CANDIDATE")
    if mode == "Full project":
        for group in project.requirement_groups:
            members = [item for item in group.member_component_role_ids if item in role_ids]
            if not members: continue
            state = readiness.requirement_groups.get(group.id) if readiness else None
            graph.node(group.id, f"{group.group_name}\n[GROUP {group.logic_type.value} · {state.status.value if state else 'Unknown'}]", shape="diamond", penwidth="2" if state and state.status == ReadinessStatus.BLOCKED else "1")
            for member in members: graph.edge(member, group.id, label="MEMBER")
        for relationship in project.relationships:
            if relationship.source_id in role_ids or relationship.target_id in role_ids:
                style = "dashed" if relationship.validation_status.value == "Unverified" else "solid"
                graph.edge(relationship.source_id, relationship.target_id, label=relationship.relationship_type.value.upper().replace(" ", "_"), style=style)
    return graph
