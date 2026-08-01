from datetime import datetime, timezone

from models.project import Project, new_id


def duplicate_project(project: Project, name: str | None = None) -> Project:
    copy = project.model_copy(deep=True)
    mapping: dict[str, str] = {project.id: new_id()}
    for collection in [copy.milestones, copy.capabilities, copy.component_roles, copy.products, copy.relationships, copy.requirement_groups]:
        for item in collection:
            mapping[item.id] = new_id()
    copy.id = mapping[project.id]
    copy.name = name or f"{project.name} (Copy)"
    for item in copy.milestones + copy.capabilities + copy.component_roles + copy.products + copy.relationships + copy.requirement_groups:
        item.id = mapping[item.id]
    for capability in copy.capabilities:
        capability.first_relevant_milestone_id = mapping.get(capability.first_relevant_milestone_id, capability.first_relevant_milestone_id)
    for role in copy.component_roles:
        role.capability_id = mapping.get(role.capability_id, role.capability_id)
        role.first_required_milestone_id = mapping.get(role.first_required_milestone_id, role.first_required_milestone_id)
    for rating in copy.role_milestone_ratings:
        rating.component_role_id = mapping.get(rating.component_role_id, rating.component_role_id)
        rating.milestone_id = mapping.get(rating.milestone_id, rating.milestone_id)
    for product in copy.products:
        product.component_role_id = mapping.get(product.component_role_id, product.component_role_id)
    for rel in copy.relationships:
        rel.source_id = mapping.get(rel.source_id, rel.source_id)
        rel.target_id = mapping.get(rel.target_id, rel.target_id)
        rel.relevant_milestone_id = mapping.get(rel.relevant_milestone_id, rel.relevant_milestone_id)
    for group in copy.requirement_groups:
        group.owner_id = mapping.get(group.owner_id, group.owner_id)
        group.member_component_role_ids = [mapping.get(item, item) for item in group.member_component_role_ids]
        group.relevant_milestone_id = mapping.get(group.relevant_milestone_id, group.relevant_milestone_id)
    now = datetime.now(timezone.utc)
    copy.created_at = copy.updated_at = now
    return Project.model_validate(copy.model_dump(mode="python"))
