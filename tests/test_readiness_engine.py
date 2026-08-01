import pytest

from models.enums import (
    EntityType, LogicType, ReadinessStatus, RelationshipType,
    RoleRequiredness, RoleStatus, SelectionStatus, VerificationStatus,
)
from models.project import ProductSelection, Relationship, RequirementGroup
from services.readiness import evaluate_project_readiness
from services.templates import build_sample_project


def make_roles_ready(project):
    for role in project.component_roles:
        role.current_status=RoleStatus.VERIFIED
        role.condition_active=True
        project.products.append(ProductSelection(component_role_id=role.id,product_name=f"{role.role_name} product",primary_product=True,selection_status=SelectionStatus.SELECTED,verification_status=VerificationStatus.SPEC_REVIEWED))


def test_mandatory_role_without_product_is_blocked_and_optional_is_not() -> None:
    project=build_sample_project(); project.component_roles[-1].requiredness=RoleRequiredness.OPTIONAL
    report=evaluate_project_readiness(project)
    assert report.component_roles[project.component_roles[0].id].status==ReadinessStatus.BLOCKED
    assert report.component_roles[project.component_roles[-1].id].status==ReadinessStatus.NOT_EVALUATED


def test_unverified_selected_product_is_at_risk() -> None:
    project=build_sample_project(); role=project.component_roles[0]; role.current_status=RoleStatus.VERIFIED
    project.products=[ProductSelection(component_role_id=role.id,product_name="Computer",primary_product=True,selection_status=SelectionStatus.SELECTED)]
    assert evaluate_project_readiness(project).component_roles[role.id].status==ReadinessStatus.AT_RISK


def test_ready_all_of_any_of_and_n_of_m() -> None:
    project=build_sample_project(); make_roles_ready(project)
    owner=project.capabilities[0].id; ids=[r.id for r in project.component_roles[:3]]
    project.requirement_groups.extend([
        RequirementGroup(group_name="Any",owner_id=owner,owner_type=EntityType.CAPABILITY,logic_type=LogicType.ANY_OF,member_component_role_ids=ids),
        RequirementGroup(group_name="Two",owner_id=owner,owner_type=EntityType.CAPABILITY,logic_type=LogicType.N_OF_M,member_component_role_ids=ids,minimum_required_count=2),
    ])
    report=evaluate_project_readiness(project)
    assert all(report.requirement_groups[g.id].status==ReadinessStatus.READY for g in project.requirement_groups)
    assert report.milestones[project.milestones[0].id].status==ReadinessStatus.READY


def test_incomplete_all_of_and_failed_any_of_are_blocked() -> None:
    project=build_sample_project(); report=evaluate_project_readiness(project)
    assert report.requirement_groups[project.requirement_groups[0].id].status==ReadinessStatus.BLOCKED
    assert report.requirement_groups[project.requirement_groups[2].id].status==ReadinessStatus.BLOCKED
    assert report.milestones[project.milestones[0].id].status==ReadinessStatus.BLOCKED


def test_conditional_group_disabled_is_not_evaluated() -> None:
    project=build_sample_project(); group=project.requirement_groups[-1]; group.condition_active=False
    assert evaluate_project_readiness(project).requirement_groups[group.id].status==ReadinessStatus.NOT_EVALUATED


def test_incompatible_selected_products_block_role() -> None:
    project=build_sample_project(); a,b=project.component_roles[:2]
    for role in [a,b]:
        role.current_status=RoleStatus.VERIFIED
        project.products.append(ProductSelection(component_role_id=role.id,product_name=role.role_name,primary_product=True,selection_status=SelectionStatus.SELECTED,verification_status=VerificationStatus.SPEC_REVIEWED))
    pa,pb=project.products
    project.relationships.append(Relationship(source_id=pa.id,source_type=EntityType.PRODUCT,relationship_type=RelationshipType.INCOMPATIBLE_WITH,target_id=pb.id,target_type=EntityType.PRODUCT))
    assert evaluate_project_readiness(project).component_roles[a.id].status==ReadinessStatus.BLOCKED
