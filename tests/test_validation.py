from models.enums import RoleStatus, SelectionStatus, VerificationStatus
from models.project import ProductSelection
from services.templates import build_rover_template, build_sample_project
from services.validation import has_blocking, validate_project


def codes(project) -> set[str]:
    return {item.code for item in validate_project(project)}


def test_missing_name_is_blocking() -> None:
    project = build_rover_template()
    findings = validate_project(project)
    assert "missing_project_name" in {item.code for item in findings}
    assert has_blocking(findings)


def test_deleted_capability_reference_is_detected() -> None:
    project = build_sample_project()
    deleted = project.component_roles[0].capability_id
    project.capabilities = [item for item in project.capabilities if item.id != deleted]
    assert "role_deleted_capability" in codes(project)


def test_selected_unverified_product_warns() -> None:
    project = build_sample_project()
    project.products.append(ProductSelection(
        component_role_id=project.component_roles[0].id,
        product_name="Example computer",
        selection_status=SelectionStatus.SELECTED,
        verification_status=VerificationStatus.UNVERIFIED,
    ))
    assert "selected_unverified" in codes(project)


def test_mobility_without_driver_is_blocked() -> None:
    project = build_sample_project()
    project.component_roles = [item for item in project.component_roles if "motor driver" not in item.role_name.lower()]
    assert "mobility_no_driver" in codes(project)


def test_self_reference_is_rejected_by_model() -> None:
    project = build_sample_project()
    relationship = project.relationships[0]
    relationship.target_id = relationship.source_id
    assert "self_dependency" in codes(project)
