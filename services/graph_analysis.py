from collections import defaultdict

from models.project import Project


def dependency_centrality(project: Project) -> dict[str, float]:
    degree: dict[str, int] = defaultdict(int)
    for relationship in project.relationships:
        degree[relationship.source_id] += 1
        degree[relationship.target_id] += 1
    for group in project.requirement_groups:
        degree[group.owner_id] += len(group.member_component_role_ids)
        for member in group.member_component_role_ids:
            degree[member] += 1
    maximum = max(degree.values(), default=1)
    return {role.id: round(degree[role.id] / maximum, 2) for role in project.component_roles}


def component_impact(project: Project, role_id: str) -> dict[str, list[str]]:
    names = project.entity_names()
    role = next((r for r in project.component_roles if r.id == role_id), None)
    milestones = {names[r.milestone_id] for r in project.role_milestone_ratings if r.component_role_id == role_id and r.rating >= 3}
    if role and role.first_required_milestone_id:
        milestones.add(names.get(role.first_required_milestone_id, "Deleted milestone"))
    capabilities = {names.get(role.capability_id, "Unassigned")} if role and role.capability_id else set()
    groups = {g.group_name for g in project.requirement_groups if role_id in g.member_component_role_ids}
    return {"milestones": sorted(milestones), "capabilities": sorted(capabilities), "subsystems": sorted(groups)}
