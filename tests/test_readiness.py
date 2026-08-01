from models.enums import ReadinessStatus, RoleStatus
from services.readiness import evaluate_group
from services.templates import build_sample_project


def test_hard_group_is_blocked_when_roles_are_only_proposed() -> None:
    project = build_sample_project()
    group = next(item for item in project.requirement_groups if item.group_name == "Manual mobility subsystem")
    result = evaluate_group(project, group)
    assert result.status == ReadinessStatus.BLOCKED


def test_group_is_at_risk_when_all_members_selected_but_unverified() -> None:
    project = build_sample_project()
    group = next(item for item in project.requirement_groups if item.group_name == "Compute subsystem")
    role_ids = set(group.member_component_role_ids)
    for role in project.component_roles:
        if role.id in role_ids:
            role.current_status = RoleStatus.SELECTED
    assert evaluate_group(project, group).status == ReadinessStatus.AT_RISK


def test_group_is_ready_when_all_members_verified() -> None:
    project = build_sample_project()
    group = next(item for item in project.requirement_groups if item.group_name == "Compute subsystem")
    role_ids = set(group.member_component_role_ids)
    for role in project.component_roles:
        if role.id in role_ids:
            role.current_status = RoleStatus.VERIFIED
    assert evaluate_group(project, group).status == ReadinessStatus.READY
